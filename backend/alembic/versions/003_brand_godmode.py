"""brand profile + godmode messages

Revision ID: 003
Revises: 002
Create Date: 2026-09-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("brands", sa.Column("logo_url", sa.Text(), nullable=False, server_default=""))
    op.add_column("brands", sa.Column("website_url", sa.String(500), nullable=False, server_default=""))
    op.add_column("brands", sa.Column("app_url", sa.String(500), nullable=False, server_default=""))

    op.create_table(
        "godmode_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("trace", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_godmode_messages_brand_id", "godmode_messages", ["brand_id"])


def downgrade() -> None:
    op.drop_table("godmode_messages")
    op.drop_column("brands", "app_url")
    op.drop_column("brands", "website_url")
    op.drop_column("brands", "logo_url")
