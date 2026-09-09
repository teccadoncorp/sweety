from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.task import Task
from app.models.user import User
from app.schemas.common import TaskIn, TaskOut, TaskUpdate
from app.services.access import get_brand_for_user, get_task_in_brand

router = APIRouter(prefix="/brands/{brand_id}/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(
    brand_id: UUID,
    campaign_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Task]:
    get_brand_for_user(db, brand_id, user.id)
    stmt = select(Task).where(Task.brand_id == brand_id)
    if campaign_id:
        stmt = stmt.where(Task.campaign_id == campaign_id)
    return list(db.scalars(stmt.order_by(Task.created_at.desc())).all())


@router.post("", response_model=TaskOut)
def create_task(
    brand_id: UUID,
    payload: TaskIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    get_brand_for_user(db, brand_id, user.id)
    task = Task(brand_id=brand_id, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    brand_id: UUID,
    task_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    get_brand_for_user(db, brand_id, user.id)
    return get_task_in_brand(db, brand_id, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    brand_id: UUID,
    task_id: UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    get_brand_for_user(db, brand_id, user.id)
    task = get_task_in_brand(db, brand_id, task_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/checkout", response_model=TaskOut)
def human_checkout(
    brand_id: UUID,
    task_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    get_brand_for_user(db, brand_id, user.id)
    task = get_task_in_brand(db, brand_id, task_id)
    task.status = "checked_out"
    task.checked_out_by = None
    task.lease_expires_at = None
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/release", response_model=TaskOut)
def human_release(
    brand_id: UUID,
    task_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    get_brand_for_user(db, brand_id, user.id)
    task = get_task_in_brand(db, brand_id, task_id)
    task.status = "ready"
    task.checked_out_by = None
    task.lease_expires_at = None
    task.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(task)
    return task
