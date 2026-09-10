import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

PM_SCHEMA = "pm"
GOD_ROLES = frozenset({"owner", "admin"})
MEMBER_ROLES = frozenset({"owner", "admin", "member"})
ISSUE_STATUSES = ("backlog", "todo", "in_progress", "review", "done")
FEATURE_STATUSES = ("backlog", "planned", "in_progress", "done")
ISSUE_KINDS = ("story", "task", "bug")


class PmUser(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": PM_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    memberships = relationship("PmWorkspaceMember", back_populates="user")


class PmWorkspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = {"schema": PM_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members = relationship("PmWorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    projects = relationship("PmProject", back_populates="workspace", cascade="all, delete-orphan")
    godmode_messages = relationship(
        "PmGodModeMessage", back_populates="workspace", cascade="all, delete-orphan"
    )


class PmWorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_pm_workspace_member"),
        {"schema": PM_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pm.workspaces.id"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pm.users.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("PmWorkspace", back_populates="members")
    user = relationship("PmUser", back_populates="memberships")


class PmProject(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "key", name="uq_pm_project_key"),
        {"schema": PM_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pm.workspaces.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    key: Mapped[str] = mapped_column(String(12))
    description: Mapped[str] = mapped_column(Text, default="")
    sweety_brand_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("PmWorkspace", back_populates="projects")
    features = relationship("PmFeature", back_populates="project", cascade="all, delete-orphan")
    issues = relationship("PmIssue", back_populates="project", cascade="all, delete-orphan")


class PmFeature(Base):
    __tablename__ = "features"
    __table_args__ = {"schema": PM_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pm.projects.id"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="backlog")
    source: Mapped[str] = mapped_column(String(32), default="human")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pm.users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project = relationship("PmProject", back_populates="features")
    issues = relationship("PmIssue", back_populates="feature")
    created_by = relationship("PmUser")


class PmIssue(Base):
    __tablename__ = "issues"
    __table_args__ = {"schema": PM_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pm.projects.id"), index=True
    )
    feature_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pm.features.id"), nullable=True, index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(32), default="task")
    status: Mapped[str] = mapped_column(String(32), default="backlog", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pm.users.id"), nullable=True, index=True
    )
    reporter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pm.users.id"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project = relationship("PmProject", back_populates="issues")
    feature = relationship("PmFeature", back_populates="issues")
    assignee = relationship("PmUser", foreign_keys=[assignee_id])
    reporter = relationship("PmUser", foreign_keys=[reporter_id])
    comments = relationship("PmComment", back_populates="issue", cascade="all, delete-orphan")


class PmComment(Base):
    __tablename__ = "comments"
    __table_args__ = {"schema": PM_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pm.issues.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pm.users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    issue = relationship("PmIssue", back_populates="comments")
    user = relationship("PmUser")


class PmGodModeMessage(Base):
    __tablename__ = "godmode_messages"
    __table_args__ = {"schema": PM_SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pm.workspaces.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text, default="")
    trace: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("PmWorkspace", back_populates="godmode_messages")
