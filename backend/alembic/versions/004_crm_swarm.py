"""crm tables

Revision ID: 004
Revises: 003
Create Date: 2026-09-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False, server_default=""),
        sa.Column("industry", sa.String(120), nullable=False, server_default=""),
        sa.Column("size", sa.String(64), nullable=False, server_default=""),
        sa.Column("website", sa.String(500), nullable=False, server_default=""),
        sa.Column("signal_score", sa.Integer(), nullable=False, server_default="40"),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_crm_accounts_brand_id", "crm_accounts", ["brand_id"])

    op.create_table(
        "crm_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_accounts.id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, server_default=""),
        sa.Column("phone", sa.String(64), nullable=False, server_default=""),
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
        sa.Column("company", sa.String(200), nullable=False, server_default=""),
        sa.Column("channel", sa.String(64), nullable=False, server_default="web"),
        sa.Column("status", sa.String(32), nullable=False, server_default="lead"),
        sa.Column("temperature", sa.String(16), nullable=False, server_default="cool"),
        sa.Column("signal_score", sa.Integer(), nullable=False, server_default="35"),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("source", sa.String(120), nullable=False, server_default=""),
        sa.Column("next_action", sa.String(400), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_touch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_crm_contacts_brand_id", "crm_contacts", ["brand_id"])
    op.create_index("ix_crm_contacts_account_id", "crm_contacts", ["account_id"])

    op.create_table(
        "crm_deals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_accounts.id"), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_contacts.id"), nullable=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("owner_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False, server_default="signal"),
        sa.Column("value_usd", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("probability", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("close_date", sa.String(32), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_crm_deals_brand_id", "crm_deals", ["brand_id"])
    op.create_index("ix_crm_deals_stage", "crm_deals", ["stage"])
    op.create_index("ix_crm_deals_account_id", "crm_deals", ["account_id"])
    op.create_index("ix_crm_deals_contact_id", "crm_deals", ["contact_id"])

    op.create_table(
        "crm_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_contacts.id"), nullable=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_accounts.id"), nullable=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_deals.id"), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False, server_default="note"),
        sa.Column("title", sa.String(240), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_crm_activities_brand_id", "crm_activities", ["brand_id"])
    op.create_index("ix_crm_activities_contact_id", "crm_activities", ["contact_id"])
    op.create_index("ix_crm_activities_deal_id", "crm_activities", ["deal_id"])


def downgrade() -> None:
    op.drop_table("crm_activities")
    op.drop_table("crm_deals")
    op.drop_table("crm_contacts")
    op.drop_table("crm_accounts")
