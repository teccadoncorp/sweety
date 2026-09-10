"""CRM cart line items, PM presence and subtickets

Revision ID: 008
Revises: 007
Create Date: 2026-09-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, Sequence[str], None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crm_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("crm_deals.id"), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price_usd", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_crm_line_items_brand_id", "crm_line_items", ["brand_id"])
    op.create_index("ix_crm_line_items_deal_id", "crm_line_items", ["deal_id"])

    op.add_column("users", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True), schema="pm")
    op.add_column(
        "issues",
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="pm",
    )
    op.create_foreign_key(
        "fk_pm_issues_parent",
        "issues",
        "issues",
        ["parent_id"],
        ["id"],
        source_schema="pm",
        referent_schema="pm",
    )
    op.create_index("ix_pm_issues_parent_id", "issues", ["parent_id"], schema="pm")


def downgrade() -> None:
    op.drop_index("ix_pm_issues_parent_id", table_name="issues", schema="pm")
    op.drop_constraint("fk_pm_issues_parent", "issues", schema="pm", type_="foreignkey")
    op.drop_column("issues", "parent_id", schema="pm")
    op.drop_column("users", "last_seen_at", schema="pm")
    op.drop_index("ix_crm_line_items_deal_id", table_name="crm_line_items")
    op.drop_index("ix_crm_line_items_brand_id", table_name="crm_line_items")
    op.drop_table("crm_line_items")
