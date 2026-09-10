"""PostgreSQL pm schema for the standalone task console

Revision ID: 007
Revises: 006
Create Date: 2026-09-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, Sequence[str], None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS pm")
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="pm",
    )
    op.create_index("ix_pm_users_email", "users", ["email"], unique=True, schema="pm")

    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="pm",
    )
    op.create_index("ix_pm_workspaces_slug", "workspaces", ["slug"], unique=True, schema="pm")

    op.create_table(
        "workspace_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["pm.workspaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["pm.users.id"]),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_pm_workspace_member"),
        schema="pm",
    )
    op.create_index("ix_pm_workspace_members_workspace_id", "workspace_members", ["workspace_id"], schema="pm")
    op.create_index("ix_pm_workspace_members_user_id", "workspace_members", ["user_id"], schema="pm")

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key", sa.String(length=12), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("sweety_brand_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["pm.workspaces.id"]),
        sa.UniqueConstraint("workspace_id", "key", name="uq_pm_project_key"),
        schema="pm",
    )
    op.create_index("ix_pm_projects_workspace_id", "projects", ["workspace_id"], schema="pm")
    op.create_index("ix_pm_projects_sweety_brand_id", "projects", ["sweety_brand_id"], schema="pm")

    op.create_table(
        "features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="backlog"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="human"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["pm.projects.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["pm.users.id"]),
        schema="pm",
    )
    op.create_index("ix_pm_features_project_id", "features", ["project_id"], schema="pm")

    op.create_table(
        "issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="task"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="backlog"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["pm.projects.id"]),
        sa.ForeignKeyConstraint(["feature_id"], ["pm.features.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["pm.users.id"]),
        sa.ForeignKeyConstraint(["reporter_id"], ["pm.users.id"]),
        schema="pm",
    )
    op.create_index("ix_pm_issues_project_id", "issues", ["project_id"], schema="pm")
    op.create_index("ix_pm_issues_feature_id", "issues", ["feature_id"], schema="pm")
    op.create_index("ix_pm_issues_status", "issues", ["status"], schema="pm")
    op.create_index("ix_pm_issues_assignee_id", "issues", ["assignee_id"], schema="pm")

    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["pm.issues.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["pm.users.id"]),
        schema="pm",
    )
    op.create_index("ix_pm_comments_issue_id", "comments", ["issue_id"], schema="pm")

    op.create_table(
        "godmode_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("trace", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["pm.workspaces.id"]),
        schema="pm",
    )
    op.create_index("ix_pm_godmode_messages_workspace_id", "godmode_messages", ["workspace_id"], schema="pm")


def downgrade() -> None:
    op.drop_table("godmode_messages", schema="pm")
    op.drop_table("comments", schema="pm")
    op.drop_table("issues", schema="pm")
    op.drop_table("features", schema="pm")
    op.drop_table("projects", schema="pm")
    op.drop_table("workspace_members", schema="pm")
    op.drop_table("workspaces", schema="pm")
    op.drop_table("users", schema="pm")
    op.execute("DROP SCHEMA IF EXISTS pm")
