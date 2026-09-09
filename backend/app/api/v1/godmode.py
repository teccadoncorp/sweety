from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.access import get_brand_for_user
from app.services.godmode import _image_urls_from_trace, list_messages, reply

router = APIRouter(prefix="/brands/{brand_id}/godmode", tags=["godmode"])


class ChatIn(BaseModel):
    content: str


@router.get("/messages")
def get_messages(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    get_brand_for_user(db, brand_id, user.id)
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "trace": m.trace,
            "images": _image_urls_from_trace(m.trace or []),
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in list_messages(db, brand_id)
    ]


@router.post("/messages")
def post_message(
    brand_id: UUID,
    payload: ChatIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    brand = get_brand_for_user(db, brand_id, user.id)
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Write a brief first")
    message = reply(db, brand, payload.content.strip())
    return {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "trace": message.trace,
        "images": _image_urls_from_trace(message.trace or []),
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


@router.post("/logo")
async def upload_logo(
    brand_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    brand = get_brand_for_user(db, brand_id, user.id)
    suffix = Path(file.filename or "logo.png").suffix.lower() or ".png"
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}:
        raise HTTPException(status_code=400, detail="Use png, jpg, webp, gif, or svg")
    folder = Path(get_settings().media_dir)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"logo-{brand_id}-{uuid4().hex[:8]}{suffix}"
    dest = folder / name
    dest.write_bytes(await file.read())
    brand.logo_url = f"{get_settings().sweety_api_public_url.rstrip('/')}/media/{name}"
    db.commit()
    return {"logo_url": brand.logo_url}
