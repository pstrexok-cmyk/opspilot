"""add aggregate AI request usage counter

Revision ID: 3d1ce6a94710
Revises: 700454291bd4
Create Date: 2026-11-06 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3d1ce6a94710"
down_revision: Union[str, None] = "700454291bd4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_monthly_usage",
        sa.Column("month_key", sa.String(length=7), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("request_count >= 0", name="ck_ai_monthly_usage_request_count_nonnegative"),
        sa.PrimaryKeyConstraint("month_key"),
    )


def downgrade() -> None:
    op.drop_table("ai_monthly_usage")
