import json
import re
from pathlib import Path
from typing import Any

from core.image_provider import DashScopeImageProvider
from core.workflow import llm
from schemas.visual import VisualGenerateIn, VisualGenerateOut


PLACEHOLDER_LOGO_URL = "/static/logo-placeholder.svg"
VISUAL_UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads" / "visuals"


def _extract_json_object(text: str) -> dict | None:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S)
    raw = fenced.group(1) if fenced else text
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return None


def _list(value: Any, fallback: list[str], limit: int = 6) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items[:limit] or fallback
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback


def _fallback_visual(data: VisualGenerateIn) -> VisualGenerateOut:
    tone = data.brand_tone or "简洁专业"
    prompt = (
        f"Logo concept for Chinese brand '{data.name}', tone: {tone}, "
        "minimal vector mark, clean typography, white background"
    )
    return VisualGenerateOut(
        name=data.name,
        slogans=[f"{data.name}，让价值被看见"],
        visual_keywords=[tone, "简洁", "可信赖", "现代"],
        color_palette=["#165DFF", "#111827", "#F9FAFB"],
        logo_images=[{"url": PLACEHOLDER_LOGO_URL, "prompt": prompt}],
        design_note=f"建议以{tone}为核心，使用简洁图形和清晰字体，先建立易识别的品牌第一印象。",
    )


def _logo_prompt(data: VisualGenerateIn, prompt: str) -> str:
    tone = data.brand_tone or "clean professional"
    return (
        f"{prompt}. Create a clean abstract brand symbol for a Chinese enterprise named {data.name}. "
        f"Brand tone: {tone}. No readable text, no letters, no mockup, no business card. "
        "Minimal vector logo mark, simple geometric composition, balanced spacing, white background."
    )


async def _build_logo_images(data: VisualGenerateIn, logo_prompt: str) -> list[dict[str, str]]:
    prompt = _logo_prompt(data, logo_prompt)
    provider = DashScopeImageProvider()
    try:
        image_url = await provider.generate_logo(prompt, VISUAL_UPLOAD_DIR)
        return [{"url": image_url, "prompt": prompt}]
    except Exception as e:
        print(f"企业 Logo 图片生成失败，使用占位图: {e}")
        return [{"url": PLACEHOLDER_LOGO_URL, "prompt": prompt}]


async def generate_enterprise_visual(data: VisualGenerateIn) -> VisualGenerateOut:
    prompt = f"""
你是一位品牌视觉顾问。请只为企业名生成品牌视觉冷启动方案。

【企业名】{data.name}
【品牌调性】{data.brand_tone or "未指定"}
【企业名寓意】{data.moral or "未提供"}
【补充要求】{data.other or "无"}

请只返回严格 JSON，不要输出 Markdown。格式：
{{
  "slogans": ["一句中文品牌 Slogan"],
  "visual_keywords": ["关键词1", "关键词2", "关键词3", "关键词4"],
  "color_palette": ["#165DFF", "#111827", "#F9FAFB"],
  "logo_prompt": "用于后续图片模型的英文 Logo prompt",
  "design_note": "简短设计说明"
}}
"""
    fallback = _fallback_visual(data)
    try:
        response = await llm.ainvoke(prompt)
        parsed = _extract_json_object(str(getattr(response, "content", response)))
        if not parsed:
            fallback.logo_images = await _build_logo_images(data, fallback.logo_images[0].prompt)
            return fallback

        logo_prompt = str(parsed.get("logo_prompt") or fallback.logo_images[0].prompt).strip()
        logo_images = await _build_logo_images(data, logo_prompt)
        return VisualGenerateOut(
            name=data.name,
            slogans=_list(parsed.get("slogans"), fallback.slogans, limit=3),
            visual_keywords=_list(parsed.get("visual_keywords"), fallback.visual_keywords, limit=6),
            color_palette=_list(parsed.get("color_palette"), fallback.color_palette, limit=5),
            logo_images=logo_images,
            design_note=str(parsed.get("design_note") or fallback.design_note).strip(),
        )
    except Exception as e:
        print(f"企业视觉生成失败，使用占位结果: {e}")
        fallback.logo_images = await _build_logo_images(data, fallback.logo_images[0].prompt)
        return fallback
