from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.connectors.store import get_connector, secrets_of
from app.core.config import get_settings

BASE = "https://api.heygen.com"


def _key(db: Session | None = None, brand_id: UUID | None = None) -> dict[str, str]:
    settings = get_settings()
    key = settings.heygen_api_key
    avatar = settings.heygen_default_avatar_id
    voice = settings.heygen_default_voice_id
    if db is not None and brand_id is not None:
        row = get_connector(db, brand_id, "heygen")
        if row and row.status == "connected":
            secrets = secrets_of(row)
            key = secrets.get("api_key") or key
            avatar = secrets.get("avatar_id") or (row.extra or {}).get("avatar_id") or avatar
            voice = secrets.get("voice_id") or (row.extra or {}).get("voice_id") or voice
    return {"api_key": key or "", "avatar_id": avatar or "", "voice_id": voice or ""}


def heygen_headers(api_key: str) -> dict[str, str]:
    return {"X-Api-Key": api_key, "Accept": "application/json"}


def list_avatars(db: Session | None = None, brand_id: UUID | None = None) -> dict[str, Any]:
    creds = _key(db, brand_id)
    if not creds["api_key"]:
        return {"ok": False, "error": "HeyGen API key not configured"}
    response = httpx.get(f"{BASE}/v2/avatars", headers=heygen_headers(creds["api_key"]), timeout=30)
    if response.status_code >= 400:
        return {"ok": False, "error": f"HeyGen {response.status_code}: {response.text[:400]}"}
    return {"ok": True, "avatars": (response.json().get("data") or {}).get("avatars") or response.json()}


def generate_video(
    script: str,
    db: Session | None = None,
    brand_id: UUID | None = None,
    avatar_id: str | None = None,
    voice_id: str | None = None,
) -> dict[str, Any]:
    creds = _key(db, brand_id)
    if not creds["api_key"]:
        return {"ok": False, "error": "Connect HeyGen or set HEYGEN_API_KEY"}
    avatar = avatar_id or creds["avatar_id"]
    voice = voice_id or creds["voice_id"]
    if not avatar or not voice:
        return {
            "ok": False,
            "error": "HeyGen needs avatar_id and voice_id. List avatars in Settings or set HEYGEN_DEFAULT_AVATAR_ID / HEYGEN_DEFAULT_VOICE_ID.",
        }
    payload = {
        "video_inputs": [
            {
                "character": {"type": "avatar", "avatar_id": avatar, "avatar_style": "normal"},
                "voice": {"type": "text", "input_text": script[:4000], "voice_id": voice},
            }
        ],
        "dimension": {"width": 1280, "height": 720},
    }
    response = httpx.post(
        f"{BASE}/v2/video/generate",
        headers={**heygen_headers(creds["api_key"]), "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if response.status_code >= 400:
        return {"ok": False, "error": f"HeyGen generate {response.status_code}: {response.text[:500]}"}
    data = response.json()
    video_id = (data.get("data") or {}).get("video_id") or data.get("video_id")
    return {"ok": True, "provider": "heygen", "video_id": video_id, "raw": data}


def video_status(video_id: str, db: Session | None = None, brand_id: UUID | None = None) -> dict[str, Any]:
    creds = _key(db, brand_id)
    if not creds["api_key"]:
        return {"ok": False, "error": "HeyGen API key not configured"}
    response = httpx.get(
        f"{BASE}/v1/video_status.get",
        params={"video_id": video_id},
        headers=heygen_headers(creds["api_key"]),
        timeout=30,
    )
    if response.status_code >= 400:
        return {"ok": False, "error": f"HeyGen status {response.status_code}: {response.text[:400]}"}
    return {"ok": True, "status": response.json()}
