from __future__ import annotations

from typing import Any


def strip_nuls(value: str, limit: int | None = None) -> str:
    cleaned = value.replace("\x00", "")
    if limit is not None:
        return cleaned[:limit]
    return cleaned


def text_from_content(content: Any, limit: int = 4000) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return strip_nuls(content, limit)
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                if part.get("type") == "text":
                    parts.append(str(part.get("text") or ""))
                elif "text" in part:
                    parts.append(str(part.get("text") or ""))
        return strip_nuls("".join(parts), limit)
    return strip_nuls(str(content), limit)


def sanitize_json(value: Any, *, depth: int = 0) -> Any:
    if depth > 12:
        return None
    if isinstance(value, str):
        if value.startswith("data:") and len(value) > 200:
            return f"[omitted data-url {len(value)} chars]"
        return strip_nuls(value, 20_000)
    if isinstance(value, bytes):
        return f"[bytes {len(value)}]"
    if isinstance(value, dict):
        return {str(k)[:200]: sanitize_json(v, depth=depth + 1) for k, v in list(value.items())[:80]}
    if isinstance(value, list):
        return [sanitize_json(item, depth=depth + 1) for item in value[:80]]
    return value
