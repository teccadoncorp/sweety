"""crm board fields

Revision ID: 005
Revises: 004
Create Date: 2026-09-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, Sequence[str], None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crm_deals", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("crm_deals", sa.Column("lost_reason", sa.String(length=400), nullable=False, server_default=""))
    op.add_column("crm_activities", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("crm_activities", "due_at")
    op.drop_column("crm_deals", "lost_reason")
    op.drop_column("crm_deals", "sort_order")
