from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=4)


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(ORMModel):
    id: UUID
    email: str
    created_at: datetime


class BrandIn(BaseModel):
    name: str
    mission: str = ""
    voice_notes: str = ""
    audience: str = ""
    guidelines: str = ""
    logo_url: str = ""
    website_url: str = ""
    app_url: str = ""
    monthly_budget_usd: Decimal = Decimal("50")
    seed_org: bool = True


class BrandUpdate(BaseModel):
    name: str | None = None
    mission: str | None = None
    voice_notes: str | None = None
    audience: str | None = None
    guidelines: str | None = None
    logo_url: str | None = None
    website_url: str | None = None
    app_url: str | None = None
    monthly_budget_usd: Decimal | None = None


class BrandOut(ORMModel):
    id: UUID
    owner_id: UUID
    name: str
    mission: str
    voice_notes: str
    audience: str = ""
    guidelines: str = ""
    agents_paused: bool = False
    logo_url: str = ""
    website_url: str = ""
    app_url: str = ""
    monthly_budget_usd: Decimal
    created_at: datetime
    spent_usd: Decimal = Decimal("0")
    campaigns_count: int = 0
    launch_campaign: str = ""


class KillSwitchIn(BaseModel):
    paused: bool


class AgentIn(BaseModel):
    role: str
    title: str
    reports_to_id: UUID | None = None
    adapter: str = "openrouter"
    model: str = "openai/gpt-4o-mini"
    system_prompt: str = ""
    skill_slugs: list[str] = Field(default_factory=list)
    monthly_budget_usd: Decimal = Decimal("15")
    heartbeat_interval_minutes: int = 10


class AgentUpdate(BaseModel):
    title: str | None = None
    reports_to_id: UUID | None = None
    adapter: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    skill_slugs: list[str] | None = None
    monthly_budget_usd: Decimal | None = None
    status: str | None = None
    heartbeat_interval_minutes: int | None = None


class AgentOut(ORMModel):
    id: UUID
    brand_id: UUID
    role: str
    title: str
    reports_to_id: UUID | None
    adapter: str
    model: str
    system_prompt: str
    skill_slugs: list[str]
    monthly_budget_usd: Decimal
    status: str
    heartbeat_interval_minutes: int
    last_heartbeat_at: datetime | None
    created_at: datetime
    spent_usd: Decimal = Decimal("0")


class CampaignIn(BaseModel):
    name: str
    goal: str
    brief: str = ""
    budget_cap_usd: Decimal = Decimal("25")


class CampaignUpdate(BaseModel):
    name: str | None = None
    goal: str | None = None
    brief: str | None = None
    status: str | None = None
    budget_cap_usd: Decimal | None = None


class CampaignOut(ORMModel):
    id: UUID
    brand_id: UUID
    name: str
    goal: str
    brief: str
    status: str
    budget_cap_usd: Decimal
    created_at: datetime
    spent_usd: Decimal = Decimal("0")


class TaskIn(BaseModel):
    campaign_id: UUID
    title: str
    description: str = ""
    assignee_agent_id: UUID | None = None
    parent_id: UUID | None = None
    priority: int = 2
    status: str = "backlog"


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_agent_id: UUID | None = None
    status: str | None = None
    priority: int | None = None


class TaskOut(ORMModel):
    id: UUID
    brand_id: UUID
    campaign_id: UUID
    parent_id: UUID | None
    assignee_agent_id: UUID | None
    title: str
    description: str
    priority: int
    status: str
    checked_out_by: UUID | None
    lease_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ArtifactIn(BaseModel):
    campaign_id: UUID | None = None
    task_id: UUID | None = None
    kind: str = "markdown"
    title: str
    content: str = ""


class ArtifactOut(ORMModel):
    id: UUID
    brand_id: UUID
    campaign_id: UUID | None
    task_id: UUID | None
    created_by_agent_id: UUID | None
    kind: str
    title: str
    content: str
    created_at: datetime


class RunOut(ORMModel):
    id: UUID
    brand_id: UUID
    agent_id: UUID
    trigger: str
    adapter: str
    status: str
    prompt_snapshot: str
    result_summary: str
    tokens_in: int
    tokens_out: int
    cost_usd: Decimal
    trace: list
    created_at: datetime


class ApprovalOut(ORMModel):
    id: UUID
    brand_id: UUID
    kind: str
    status: str
    subject_type: str
    subject_id: UUID | None
    requested_by_agent_id: UUID | None
    payload: dict
    created_at: datetime
    decided_at: datetime | None


class ApprovalDecideIn(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    text: str | None = None
    title: str | None = None
    scheduled_for: datetime | None = None


class UsageOut(BaseModel):
    brand_spent_usd: Decimal
    brand_budget_usd: Decimal
    by_agent: list[dict]


class SkillOut(BaseModel):
    slug: str
    name: str
    version: str
    allowed_roles: list[str]
    description: str


class AdapterHealthOut(BaseModel):
    name: str
    status: str
    detail: str


class HeartbeatQueued(BaseModel):
    queued: bool
    run_id: UUID | None = None
    reason: str = ""
