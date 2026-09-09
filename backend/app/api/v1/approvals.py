from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.approval import Approval
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.common import ApprovalDecideIn, ApprovalOut
from app.services.access import get_brand_for_user
from app.services.publish import maybe_execute_publish_approval

router = APIRouter(prefix="/brands/{brand_id}/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
def list_approvals(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Approval]:
    get_brand_for_user(db, brand_id, user.id)
    return list(
        db.scalars(
            select(Approval).where(Approval.brand_id == brand_id).order_by(Approval.created_at.desc())
        ).all()
    )


@router.post("/{approval_id}/decide", response_model=ApprovalOut)
def decide(
    brand_id: UUID,
    approval_id: UUID,
    payload: ApprovalDecideIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Approval:
    get_brand_for_user(db, brand_id, user.id)
    approval = db.get(Approval, approval_id)
    if approval is None or approval.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval.status = payload.status
    approval.decided_at = datetime.now(UTC)
    if payload.status == "approved" and approval.subject_type == "campaign" and approval.subject_id:
        campaign = db.get(Campaign, approval.subject_id)
        if campaign:
            campaign.status = "active"
    if payload.status == "approved":
        maybe_execute_publish_approval(db, approval)
    db.commit()
    db.refresh(approval)
    return approval
