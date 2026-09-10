"""m1 core loop: brand memory, kill switch, content calendar, notifications

Revision ID: 006
Revises: 005
Create Date: 2026-09-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, Sequence[str], None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("brands", sa.Column("audience", sa.Text(), nullable=False, server_default=""))
    op.add_column("brands", sa.Column("guidelines", sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "brands",
        sa.Column("agents_paused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_table(
        "content_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("artifacts.id"), nullable=True),
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("approvals.id"), nullable=True),
        sa.Column("created_by_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False, server_default="social-copy"),
        sa.Column("channel", sa.String(length=64), nullable=False, server_default="linkedin"),
        sa.Column("title", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_content_items_brand_id", "content_items", ["brand_id"])
    op.create_index("ix_content_items_campaign_id", "content_items", ["campaign_id"])
    op.create_index("ix_content_items_status", "content_items", ["status"])
    op.create_index("ix_content_items_scheduled_for", "content_items", ["scheduled_for"])
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False, server_default="approval"),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("href", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("subject_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_brand_id", "notifications", ["brand_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_brand_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_content_items_scheduled_for", table_name="content_items")
    op.drop_index("ix_content_items_status", table_name="content_items")
    op.drop_index("ix_content_items_campaign_id", table_name="content_items")
    op.drop_index("ix_content_items_brand_id", table_name="content_items")
    op.drop_table("content_items")
    op.drop_column("brands", "agents_paused")
    op.drop_column("brands", "guidelines")
    op.drop_column("brands", "audience")
