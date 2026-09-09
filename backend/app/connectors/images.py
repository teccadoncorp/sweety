from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from app.connectors.frames import frame_for, normalize_platform
from app.core.config import get_settings, model_map


def _save_b64(data_url: str) -> str:
    settings = get_settings()
    folder = Path(settings.media_dir)
    folder.mkdir(parents=True, exist_ok=True)
    match = re.match(r"data:(image/[\w+.-]+);base64,(.+)", data_url, re.S)
    if match:
        ext = match.group(1).split("/")[-1].replace("jpeg", "jpg")
        raw = base64.b64decode(match.group(2))
    else:
        ext = "png"
        raw = base64.b64decode(data_url)
    name = f"{uuid4()}.{ext}"
    path = folder / name
    path.write_bytes(raw)
    return f"{settings.sweety_api_public_url.rstrip('/')}/media/{name}"


def generate_image(
    prompt: str,
    model: str | None = None,
    platform: str | None = None,
    aspect_ratio: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openrouter_api_key:
        return {"ok": False, "error": "OPENROUTER_API_KEY required for image generation"}
    chosen = model or model_map()["image"]
    frame = frame_for(platform)
    ratio = aspect_ratio or frame["ratio"]
    size = frame["size"]
    label = frame["label"]
    framed_prompt = (
        f"Create a single still for {label}. Aspect ratio {ratio} ({size}). "
        f"Fill the full frame, keep safe margins, no watermarks, no fake UI chrome.\n\n{prompt}"
    )
    payload: dict[str, Any] = {
        "model": chosen,
        "messages": [{"role": "user", "content": framed_prompt}],
        "modalities": ["image", "text"],
        "image_config": {"aspect_ratio": ratio},
    }
    response = httpx.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "HTTP-Referer": settings.sweety_public_url,
            "X-Title": "Sweety",
        },
        json=payload,
        timeout=120,
    )
    if response.status_code >= 400:
        return {"ok": False, "error": f"Image gen {response.status_code}: {response.text[:500]}"}
    message = ((response.json().get("choices") or [{}])[0].get("message") or {})
    images = message.get("images") or []
    urls: list[str] = []
    for image in images:
        url = None
        if isinstance(image, dict):
            url = (image.get("image_url") or {}).get("url") or image.get("url")
        if url and url.startswith("data:"):
            urls.append(_save_b64(url))
        elif url:
            urls.append(url)
    content = message.get("content")
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                url = (part.get("image_url") or {}).get("url")
                if url and url.startswith("data:"):
                    urls.append(_save_b64(url))
                elif url:
                    urls.append(url)
    if not urls:
        return {
            "ok": False,
            "error": "Model returned no image. Check SWEETY_IMAGE_MODEL supports image output.",
            "text": message.get("content") if isinstance(message.get("content"), str) else None,
        }
    return {
        "ok": True,
        "provider": "openrouter",
        "model": chosen,
        "urls": urls,
        "prompt": prompt,
        "platform": normalize_platform(platform) or None,
        "aspect_ratio": ratio,
        "size": size,
        "frame_label": label,
    }
