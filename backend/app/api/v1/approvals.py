from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.agent import Agent
from app.models.approval import Approval
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.common import ApprovalDecideIn, ApprovalOut
from app.services.access import get_brand_for_user
from app.services.loop import apply_content_decision, queue_launch_heartbeats
from app.services.publish import maybe_execute_publish_approval

router = APIRouter(prefix="/brands/{brand_id}/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
def list_approvals(
    brand_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = Query(default=None),
) -> list[Approval]:
    get_brand_for_user(db, brand_id, user.id)
    stmt = select(Approval).where(Approval.brand_id == brand_id)
    if status:
        stmt = stmt.where(Approval.status == status)
    return list(db.scalars(stmt.order_by(Approval.created_at.desc())).all())


@router.post("/{approval_id}/decide", response_model=ApprovalOut)
def decide(
    brand_id: UUID,
    approval_id: UUID,
    payload: ApprovalDecideIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Approval:
    brand = get_brand_for_user(db, brand_id, user.id)
    approval = db.get(Approval, approval_id)
    if approval is None or approval.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval.status = payload.status
    approval.decided_at = datetime.now(UTC)
    apply_content_decision(
        db,
        approval,
        status=payload.status,
        text=payload.text,
        title=payload.title,
        scheduled_for=payload.scheduled_for,
    )
    if payload.status == "approved":
        maybe_execute_publish_approval(db, approval)
    wake_ids: list[UUID] = []
    if payload.status == "approved" and approval.subject_type == "campaign" and approval.subject_id:
        campaign = db.get(Campaign, approval.subject_id)
        if campaign:
            campaign.status = "active"
            copywriter = db.scalar(
                select(Agent).where(
                    Agent.brand_id == brand_id,
                    Agent.role.in_(["copywriter", "social"]),
                )
            )
            if copywriter and not brand.agents_paused:
                wake_ids.append(copywriter.id)
    db.commit()
    db.refresh(approval)
    if wake_ids:
        queue_launch_heartbeats(wake_ids, "approved")
    return approval
