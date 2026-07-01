import asyncio
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4

try:
    import settings
except Exception:
    settings = None


class ImageGenerationError(Exception):
    pass


def _read_api_key_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return ""
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("DASHSCOPE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
        if line.startswith("sk-"):
            return line
    return content


def _load_dashscope_api_key() -> str:
    env_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if env_key:
        return env_key

    settings_key = str(getattr(settings, "DASHSCOPE_API_KEY", "") or "").strip() if settings else ""
    if settings_key:
        return settings_key

    configured_file = str(getattr(settings, "DASHSCOPE_CONFIG_FILE", "") or "").strip() if settings else ""
    candidates = []
    if configured_file:
        candidates.append(Path(configured_file))
    backend_dir = Path(__file__).resolve().parents[1]
    project_dir = backend_dir.parent
    candidates.extend([
        project_dir / "dashscope",
        project_dir / "dashscope.txt",
        backend_dir / "settings" / "dashscope.txt",
        backend_dir / "dashscope",
        backend_dir / "dashscope.txt",
        Path.home() / "Desktop" / "dashscope.txt",
    ])
    for candidate in candidates:
        key = _read_api_key_file(candidate)
        if key:
            return key
    return ""


class DashScopeImageProvider:
    def __init__(self):
        self.api_key = _load_dashscope_api_key()
        self.model = os.getenv("ALIYUN_IMAGE_MODEL", "wanx2.1-t2i-turbo").strip()
        self.base_url = os.getenv("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com").rstrip("/")
        self.poll_interval_seconds = float(os.getenv("ALIYUN_IMAGE_POLL_INTERVAL", "2"))
        self.max_poll_attempts = int(os.getenv("ALIYUN_IMAGE_MAX_POLLS", "30"))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _request_json(self, url: str, *, method: str = "GET", payload: dict | None = None) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if payload is not None:
            headers["X-DashScope-Async"] = "enable"

        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise ImageGenerationError(f"DashScope HTTP {error.code}: {detail}") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ImageGenerationError(f"DashScope request failed: {error}") from error

    def _download_image(self, image_url: str, output_dir: Path) -> str:
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(urllib.parse.urlparse(image_url).path).suffix or ".png"
        filename = f"logo-{int(time.time())}-{uuid4().hex[:10]}{suffix}"
        output_path = output_dir / filename
        try:
            with urllib.request.urlopen(image_url, timeout=60) as response:
                output_path.write_bytes(response.read())
        except (urllib.error.URLError, TimeoutError) as error:
            raise ImageGenerationError(f"DashScope image download failed: {error}") from error
        return f"/uploads/visuals/{filename}"

    def _create_task(self, prompt: str) -> str:
        url = f"{self.base_url}/api/v1/services/aigc/text2image/image-synthesis"
        payload = {
            "model": self.model,
            "input": {"prompt": prompt},
            "parameters": {
                "size": "1024*1024",
                "n": 1,
            },
        }
        data = self._request_json(url, method="POST", payload=payload)
        task_id = (data.get("output") or {}).get("task_id")
        if not task_id:
            raise ImageGenerationError(f"DashScope task_id missing: {data}")
        return task_id

    def _query_task(self, task_id: str) -> dict:
        url = f"{self.base_url}/api/v1/tasks/{task_id}"
        return self._request_json(url)

    def _generate_sync(self, prompt: str, output_dir: Path) -> str:
        if not self.enabled:
            raise ImageGenerationError("DASHSCOPE_API_KEY is not configured")

        task_id = self._create_task(prompt)
        last_response = None
        for _ in range(self.max_poll_attempts):
            time.sleep(self.poll_interval_seconds)
            last_response = self._query_task(task_id)
            output = last_response.get("output") or {}
            status = output.get("task_status")
            if status in {"SUCCEEDED", "SUCCESS"}:
                results = output.get("results") or []
                image_url = (results[0] or {}).get("url") if results else None
                if not image_url:
                    raise ImageGenerationError(f"DashScope image URL missing: {last_response}")
                return self._download_image(image_url, output_dir)
            if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                raise ImageGenerationError(f"DashScope task failed: {last_response}")

        raise ImageGenerationError(f"DashScope task timeout: {last_response}")

    async def generate_logo(self, prompt: str, output_dir: Path) -> str:
        return await asyncio.to_thread(self._generate_sync, prompt, output_dir)
