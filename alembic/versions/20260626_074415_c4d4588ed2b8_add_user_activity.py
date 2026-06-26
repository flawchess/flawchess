"""Add user_activity table — forward-only daily activity calendar.

One row per (user_id, UTC activity_date). Populated via ON CONFLICT upsert in
LastActivityMiddleware, which is hour-throttled, so activity_count tracks distinct
active hours per day (1-24). Collection-only; no query layer or endpoint.

Revision ID: c4d4588ed2b8
Revises: 20260623210000
Create Date: 2026-06-26 07:44:15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d4588ed2b8"
down_revision: Union[str, None] = "20260623210000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_activity",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column(
            "activity_count",
            sa.SmallInteger(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "activity_date", name="uq_user_activity_user_date"),
    )
    op.create_index(
        "ix_user_activity_activity_date", "user_activity", ["activity_date"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_user_activity_activity_date", table_name="user_activity")
    op.drop_table("user_activity")
