import asyncio
import re

try:
    from pypinyin import lazy_pinyin, Style
except ImportError:  # pragma: no cover - optional local dependency fallback
    lazy_pinyin = None
    Style = None

async def check_com_domain(domain: str) -> str:
    """
    异步工具：向全球.com 根服务器查询域名是否可用
    """
    # 容错处理：确保查询的是.com 域名
    if not domain.endswith('.com'):
        if '.' not in domain:
            domain += '.com'
        else:
            return "⚠仅支持.com校验"
    try:
        # 1. 建立与whois.verisign-grs.com 的43 端口异步TCP 连接
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection('whois.verisign-grs.com', 43),
            timeout=3.0  # 限制3 秒超时，防止卡死
        )
        # 2. 发送查询指令(域名+ 回车换行)
        writer.write((domain + "\r\n").encode('utf-8'))
        await writer.drain()
        # 3. 读取服务器返回的数据
        response = await asyncio.wait_for(reader.read(), timeout=3.0)
        # 4. 释放连接
        writer.close()
        await writer.wait_closed()
        result = response.decode('utf-8', errors='ignore')
        # 5. 核心逻辑：如果服务器返回"No match for "，说明没人注册！
        if "No match for " in result:
            return "✅ 未注册(可买)"
        else:
            return "❌ 已被抢注"
    except asyncio.TimeoutError:
        return "⚠ 查询超时"
    except Exception as e:
        return f"⚠ 查询失败: {str(e)}"


def _normalize_domain(domain: str) -> str:
    value = (domain or "").strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = value.split("/")[0]
    if not value:
        return ""
    if "." not in value:
        value = f"{value}.com"
    if not value.endswith(".com"):
        return ""
    label = value[:-4]
    label = re.sub(r"[^a-z0-9-]", "", label)
    label = label.strip("-")
    if not label:
        return ""
    return f"{label}.com"


def _slugify_ascii(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "", text or "").lower()
    return value[:40]


def _pinyin_full(text: str) -> str:
    if lazy_pinyin:
        return "".join(lazy_pinyin(text, errors="ignore"))[:40]
    return _slugify_ascii(text)


def _pinyin_initials(text: str) -> str:
    if lazy_pinyin and Style:
        return "".join(lazy_pinyin(text, style=Style.FIRST_LETTER, errors="ignore"))[:20]
    return _slugify_ascii(text)[:20]


def build_domain_candidates(name: str, suggested_domain: str = "", limit: int = 3) -> list[str]:
    candidates = []
    for value in (
        suggested_domain,
        f"{_pinyin_full(name)}.com",
        f"{_pinyin_initials(name)}.com",
    ):
        normalized = _normalize_domain(value)
        if normalized and normalized not in candidates:
            candidates.append(normalized)
        if len(candidates) >= limit:
            break
    return candidates


async def check_com_domain_detail(domain: str) -> dict:
    normalized = _normalize_domain(domain)
    if not normalized:
        return {
            "domain": domain,
            "available": None,
            "status": "unsupported",
            "message": "仅支持 .com 域名校验",
        }

    message = await check_com_domain(normalized)
    if "超时" in message or "查询失败" in message:
        await asyncio.sleep(0.2)
        message = await check_com_domain(normalized)
    if "未注册" in message or "可买" in message:
        available = True
        status = "available"
    elif "已被" in message or "抢注" in message:
        available = False
        status = "taken"
    elif "超时" in message:
        available = None
        status = "timeout"
    else:
        available = None
        status = "error"

    return {
        "domain": normalized,
        "available": available,
        "status": status,
        "message": message,
    }


async def check_name_domains(name: str, suggested_domain: str = "", limit: int = 3) -> list[dict]:
    candidates = build_domain_candidates(name, suggested_domain=suggested_domain, limit=limit)
    if not candidates:
        return []
    results = await asyncio.gather(*(check_com_domain_detail(domain) for domain in candidates))
    return [item for item in results if item["status"] in {"available", "taken"}]
