from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.heartbeat_run import HeartbeatRun
from app.models.user import User
from app.schemas.common import RunOut
from app.services.access import get_brand_for_user

router = APIRouter(prefix="/brands/{brand_id}/runs", tags=["runs"])


@router.get("", response_model=list[RunOut])
def list_runs(
    brand_id: UUID,
    agent_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[HeartbeatRun]:
    get_brand_for_user(db, brand_id, user.id)
    stmt = select(HeartbeatRun).where(HeartbeatRun.brand_id == brand_id)
    if agent_id:
        stmt = stmt.where(HeartbeatRun.agent_id == agent_id)
    return list(db.scalars(stmt.order_by(HeartbeatRun.created_at.desc()).limit(100)).all())


@router.get("/{run_id}", response_model=RunOut)
def get_run(
    brand_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HeartbeatRun:
    get_brand_for_user(db, brand_id, user.id)
    run = db.get(HeartbeatRun, run_id)
    if run is None or run.brand_id != brand_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Run not found")
    return run
