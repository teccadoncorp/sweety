from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, load_only

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
    status: str | None = Query(default=None),
    include_heavy: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[HeartbeatRun] | list[RunOut]:
    get_brand_for_user(db, brand_id, user.id)
    stmt = select(HeartbeatRun).where(HeartbeatRun.brand_id == brand_id)
    if agent_id:
        stmt = stmt.where(HeartbeatRun.agent_id == agent_id)
    if status:
        stmt = stmt.where(HeartbeatRun.status == status)
    if not include_heavy:
        stmt = stmt.options(
            load_only(
                HeartbeatRun.id,
                HeartbeatRun.brand_id,
                HeartbeatRun.agent_id,
                HeartbeatRun.trigger,
                HeartbeatRun.adapter,
                HeartbeatRun.status,
                HeartbeatRun.result_summary,
                HeartbeatRun.tokens_in,
                HeartbeatRun.tokens_out,
                HeartbeatRun.cost_usd,
                HeartbeatRun.created_at,
            )
        )
    cap = 20 if status == "running" else 40 if not include_heavy else 80
    rows = list(db.scalars(stmt.order_by(HeartbeatRun.created_at.desc()).limit(cap)).all())
    if include_heavy:
        return rows
    return [
        RunOut(
            id=row.id,
            brand_id=row.brand_id,
            agent_id=row.agent_id,
            trigger=row.trigger,
            adapter=row.adapter,
            status=row.status,
            prompt_snapshot="",
            result_summary=row.result_summary or "",
            tokens_in=row.tokens_in,
            tokens_out=row.tokens_out,
            cost_usd=row.cost_usd,
            trace=[],
            created_at=row.created_at,
        )
        for row in rows
    ]


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
