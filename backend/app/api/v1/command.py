from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.ops import CommandOut
from app.services.access import get_brand_for_user
from app.services.loop import ensure_launch_campaign
from app.services.ops import command_snapshot

router = APIRouter(prefix="/brands/{brand_id}/command", tags=["command"])


@router.get("", response_model=CommandOut)
def get_command(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CommandOut:
    brand = get_brand_for_user(db, brand_id, user.id)
    ensure_launch_campaign(db, brand)
    db.commit()
    return CommandOut(**command_snapshot(db, brand_id))
