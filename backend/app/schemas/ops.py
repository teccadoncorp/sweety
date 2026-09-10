from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CommandAgentOut(BaseModel):
    id: UUID
    role: str
    title: str
    status: str
    model: str
    last_heartbeat_at: datetime | None
    inbox: int
    live: bool
    last_run_status: str = ""
    last_summary: str = ""
    skill_count: int = 0
    spent_usd: str = "0"


class CommandOut(BaseModel):
    live_runs: int
    ready_tasks: int
    pending_approvals: int
    crm_hot: int
    agents_paused: bool = False
    agents: list[CommandAgentOut]


class ModelBroadcastIn(BaseModel):
    model: str


class OrgPresetOut(BaseModel):
    role: str
    title: str
    skills: list[str]
    prompt: str
