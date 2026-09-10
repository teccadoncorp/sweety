from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AccountIn(BaseModel):
    name: str
    domain: str = ""
    industry: str = ""
    size: str = ""
    website: str = ""
    signal_score: int = Field(default=40, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class AccountUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    industry: str | None = None
    size: str | None = None
    website: str | None = None
    signal_score: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] | None = None
    notes: str | None = None


class AccountOut(ORMModel):
    id: UUID
    brand_id: UUID
    name: str
    domain: str
    industry: str
    size: str
    website: str
    signal_score: int
    tags: list[str]
    notes: str
    created_at: datetime


class ContactIn(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    title: str = ""
    company: str = ""
    account_id: UUID | None = None
    channel: str = "web"
    status: str = "lead"
    temperature: str = "cool"
    signal_score: int = Field(default=35, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    source: str = ""
    next_action: str = ""
    notes: str = ""


class ContactUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    company: str | None = None
    account_id: UUID | None = None
    channel: str | None = None
    status: str | None = None
    temperature: str | None = None
    signal_score: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] | None = None
    source: str | None = None
    next_action: str | None = None
    notes: str | None = None


class ContactOut(ORMModel):
    id: UUID
    brand_id: UUID
    account_id: UUID | None
    name: str
    email: str
    phone: str
    title: str
    company: str
    channel: str
    status: str
    temperature: str
    signal_score: int
    tags: list[str]
    source: str
    next_action: str
    notes: str
    last_touch_at: datetime | None
    created_at: datetime
    account_name: str = ""


class DealIn(BaseModel):
    name: str
    account_id: UUID | None = None
    contact_id: UUID | None = None
    campaign_id: UUID | None = None
    owner_agent_id: UUID | None = None
    stage: str = "signal"
    value_usd: Decimal = Decimal("0")
    probability: int = Field(default=20, ge=0, le=100)
    close_date: str = ""
    notes: str = ""
    lost_reason: str = ""
    sort_order: int = 0


class DealUpdate(BaseModel):
    name: str | None = None
    account_id: UUID | None = None
    contact_id: UUID | None = None
    campaign_id: UUID | None = None
    owner_agent_id: UUID | None = None
    stage: str | None = None
    value_usd: Decimal | None = None
    probability: int | None = Field(default=None, ge=0, le=100)
    close_date: str | None = None
    notes: str | None = None
    lost_reason: str | None = None
    sort_order: int | None = None


class DealOut(ORMModel):
    id: UUID
    brand_id: UUID
    account_id: UUID | None
    contact_id: UUID | None
    campaign_id: UUID | None
    owner_agent_id: UUID | None
    name: str
    stage: str
    value_usd: Decimal
    probability: int
    close_date: str
    notes: str
    lost_reason: str = ""
    sort_order: int = 0
    contact_name: str = ""
    account_name: str = ""
    created_at: datetime
    updated_at: datetime | None = None


class ActivityIn(BaseModel):
    kind: str = "note"
    title: str = ""
    body: str = ""
    due_at: datetime | None = None
    contact_id: UUID | None = None
    account_id: UUID | None = None
    deal_id: UUID | None = None
    agent_id: UUID | None = None


class ActivityOut(ORMModel):
    id: UUID
    brand_id: UUID
    contact_id: UUID | None
    account_id: UUID | None
    deal_id: UUID | None
    agent_id: UUID | None
    kind: str
    title: str
    body: str
    due_at: datetime | None = None
    created_at: datetime


class CrmBoardOut(BaseModel):
    contacts: int
    accounts: int
    open_deals: int
    pipeline_usd: Decimal
    weighted_pipeline_usd: Decimal
    won_usd: Decimal
    avg_deal_usd: Decimal
    hot_leads: int
    overdue: int
    stages: dict[str, int]
    avg_signal: float


class SwarmQueued(BaseModel):
    queued: int
    agent_ids: list[UUID]
    reason: str = "Swarm queued"


class ActivityUpdate(BaseModel):
    kind: str | None = None
    title: str | None = None
    body: str | None = None
    due_at: datetime | None = None


class LineItemIn(BaseModel):
    deal_id: UUID
    name: str
    sku: str = ""
    qty: int = Field(default=1, ge=1)
    unit_price_usd: Decimal = Decimal("0")
    notes: str = ""


class LineItemUpdate(BaseModel):
    name: str | None = None
    sku: str | None = None
    qty: int | None = Field(default=None, ge=1)
    unit_price_usd: Decimal | None = None
    notes: str | None = None
    deal_id: UUID | None = None


class LineItemOut(ORMModel):
    id: UUID
    brand_id: UUID
    deal_id: UUID
    name: str
    sku: str
    qty: int
    unit_price_usd: Decimal
    notes: str
    deal_name: str = ""
    created_at: datetime
    updated_at: datetime | None = None
