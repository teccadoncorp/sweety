from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PmRegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=4)
    display_name: str = ""


class PmLoginIn(BaseModel):
    email: str
    password: str


class PmWorkspaceSummary(ORMModel):
    id: UUID
    name: str
    slug: str
    role: str
    can_create_features: bool = False


class PmUserOut(ORMModel):
    id: UUID
    email: str
    display_name: str
    created_at: datetime
    workspaces: list[PmWorkspaceSummary] = Field(default_factory=list)


class PmWorkspaceIn(BaseModel):
    name: str
    slug: str = ""


class PmMemberIn(BaseModel):
    email: str
    role: str = "member"
    display_name: str = ""
    password: str = ""


class PmMemberUpdate(BaseModel):
    role: str | None = None
    display_name: str | None = None


class PmMemberOut(ORMModel):
    id: UUID
    user_id: UUID
    email: str
    display_name: str
    role: str
    online: bool = False
    last_seen_at: datetime | None = None
    created_at: datetime
    temporary_password: str | None = None


class PmWorkspaceOut(ORMModel):
    id: UUID
    name: str
    slug: str
    role: str
    can_create_features: bool = False
    created_at: datetime
    members: list[PmMemberOut] = Field(default_factory=list)


class PmProjectIn(BaseModel):
    name: str
    key: str = ""
    description: str = ""


class PmProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class PmProjectOut(ORMModel):
    id: UUID
    workspace_id: UUID
    name: str
    key: str
    description: str
    sweety_brand_id: UUID | None
    created_at: datetime
    feature_count: int = 0
    issue_count: int = 0


class PmFeatureIn(BaseModel):
    title: str
    description: str = ""
    status: str = "backlog"
    stories: list[str] = Field(default_factory=list)


class PmFeatureUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None


class PmFeatureOut(ORMModel):
    id: UUID
    project_id: UUID
    key: str
    number: int
    title: str
    description: str
    status: str
    source: str
    created_by_user_id: UUID | None
    issue_count: int = 0
    created_at: datetime
    updated_at: datetime


class PmIssueIn(BaseModel):
    title: str
    description: str = ""
    kind: str = "task"
    status: str = "backlog"
    priority: int = 2
    feature_id: UUID | None = None
    parent_id: UUID | None = None
    assignee_id: UUID | None = None
    due_date: date | None = None


class PmIssueUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    kind: str | None = None
    status: str | None = None
    priority: int | None = None
    feature_id: UUID | None = None
    parent_id: UUID | None = None
    assignee_id: UUID | None = None
    due_date: date | None = None
    sort_order: int | None = None


class PmIssueOut(ORMModel):
    id: UUID
    project_id: UUID
    feature_id: UUID | None
    parent_id: UUID | None = None
    parent_key: str = ""
    subticket_count: int = 0
    key: str
    number: int
    title: str
    description: str
    kind: str
    status: str
    priority: int
    assignee_id: UUID | None
    reporter_id: UUID | None
    assignee_name: str = ""
    reporter_name: str = ""
    feature_title: str = ""
    feature_key: str = ""
    due_date: date | None
    overdue: bool = False
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PmCommentIn(BaseModel):
    body: str


class PmCommentOut(ORMModel):
    id: UUID
    issue_id: UUID
    user_id: UUID
    author_name: str = ""
    body: str
    created_at: datetime


class PmBoardOut(BaseModel):
    project: PmProjectOut
    features: list[PmFeatureOut]
    columns: dict[str, list[PmIssueOut]]
    members: list[PmMemberOut]
    role: str = "member"
    can_create_features: bool = False


class PmChatIn(BaseModel):
    content: str


class PmWorkspaceUpdate(BaseModel):
    name: str | None = None


class PmCommentUpdate(BaseModel):
    body: str


class PmReportOut(BaseModel):
    totals: dict
    by_status: dict[str, int]
    by_kind: dict[str, int]
    by_assignee: list[dict]
    by_epic: list[dict]
    overdue: list[PmIssueOut]
