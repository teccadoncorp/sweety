from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.connectors.social import PublishError, publish
from app.core.config import get_settings
from app.models.approval import Approval


def execute_social_payload(db: Session, brand_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return publish(
            db,
            brand_id,
            payload.get("platform") or "",
            text=payload.get("text") or "",
            title=payload.get("title"),
            image_url=payload.get("image_url"),
            subreddit=payload.get("subreddit"),
            caption=payload.get("caption"),
        )
    except PublishError as exc:
        return {"ok": False, "error": str(exc)}


def maybe_execute_publish_approval(db: Session, approval: Approval) -> dict[str, Any] | None:
    if approval.kind != "publish" or approval.status != "approved":
        return None
    payload = approval.payload or {}
    if not payload.get("platform"):
        return None
    if payload.get("publish_result") or payload.get("content_item_id"):
        return payload.get("publish_result")
    result = execute_social_payload(db, approval.brand_id, payload)
    payload = dict(payload)
    payload["publish_result"] = result
    approval.payload = payload
    db.add(approval)
    return result
