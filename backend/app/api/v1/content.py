from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.content import ContentItem
from app.models.user import User
from app.schemas.loop import CalendarOut, ContentItemOut
from app.services.access import get_brand_for_user
from app.services.loop import reporting_counts

router = APIRouter(prefix="/brands/{brand_id}", tags=["content"])


@router.get("/calendar", response_model=CalendarOut)
def get_calendar(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CalendarOut:
    get_brand_for_user(db, brand_id, user.id)
    rows = list(
        db.scalars(
            select(ContentItem)
            .where(ContentItem.brand_id == brand_id)
            .order_by(ContentItem.created_at.desc())
        ).all()
    )
    return CalendarOut(items=[ContentItemOut.model_validate(r) for r in rows], counts=reporting_counts(db, brand_id))


@router.get("/content", response_model=list[ContentItemOut])
def list_content(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ContentItemOut]:
    get_brand_for_user(db, brand_id, user.id)
    rows = db.scalars(
        select(ContentItem).where(ContentItem.brand_id == brand_id).order_by(ContentItem.created_at.desc())
    ).all()
    return [ContentItemOut.model_validate(r) for r in rows]
