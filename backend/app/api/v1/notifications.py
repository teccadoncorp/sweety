from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.loop import NotificationOut
from app.services.access import get_brand_for_user

router = APIRouter(prefix="/brands/{brand_id}/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    brand_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    unread: bool = Query(default=False),
) -> list[Notification]:
    get_brand_for_user(db, brand_id, user.id)
    stmt = select(Notification).where(Notification.brand_id == brand_id)
    if unread:
        stmt = stmt.where(Notification.read_at.is_(None))
    return list(db.scalars(stmt.order_by(Notification.created_at.desc()).limit(50)).all())


@router.post("/read-all", response_model=list[NotificationOut])
def mark_all_read(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Notification]:
    get_brand_for_user(db, brand_id, user.id)
    rows = list(
        db.scalars(
            select(Notification).where(Notification.brand_id == brand_id, Notification.read_at.is_(None))
        ).all()
    )
    now = datetime.now(UTC)
    for row in rows:
        row.read_at = now
    db.commit()
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.brand_id == brand_id)
            .order_by(Notification.created_at.desc())
            .limit(50)
        ).all()
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    brand_id: UUID,
    notification_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Notification:
    get_brand_for_user(db, brand_id, user.id)
    row = db.get(Notification, notification_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    return row
