from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ContentItemOut(ORMModel):
    id: UUID
    brand_id: UUID
    campaign_id: UUID | None
    task_id: UUID | None
    artifact_id: UUID | None
    approval_id: UUID | None
    created_by_agent_id: UUID | None
    kind: str
    channel: str
    title: str
    body: str
    status: str
    scheduled_for: datetime | None
    published_at: datetime | None
    extra: dict
    created_at: datetime


class CalendarOut(BaseModel):
    items: list[ContentItemOut]
    counts: dict[str, int]


class NotificationOut(ORMModel):
    id: UUID
    brand_id: UUID
    kind: str
    title: str
    body: str
    href: str
    subject_type: str
    subject_id: UUID | None
    read_at: datetime | None
    created_at: datetime
