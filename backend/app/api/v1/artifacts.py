from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.artifact import Artifact
from app.models.user import User
from app.schemas.common import ArtifactIn, ArtifactOut
from app.services.access import get_brand_for_user

router = APIRouter(prefix="/brands/{brand_id}/artifacts", tags=["artifacts"])


@router.get("", response_model=list[ArtifactOut])
def list_artifacts(
    brand_id: UUID,
    task_id: UUID | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Artifact]:
    get_brand_for_user(db, brand_id, user.id)
    stmt = select(Artifact).where(Artifact.brand_id == brand_id)
    if task_id:
        stmt = stmt.where(Artifact.task_id == task_id)
    if campaign_id:
        stmt = stmt.where(Artifact.campaign_id == campaign_id)
    return list(db.scalars(stmt.order_by(Artifact.created_at.desc())).all())


@router.post("", response_model=ArtifactOut)
def create_artifact(
    brand_id: UUID,
    payload: ArtifactIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Artifact:
    get_brand_for_user(db, brand_id, user.id)
    artifact = Artifact(brand_id=brand_id, **payload.model_dump())
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact
