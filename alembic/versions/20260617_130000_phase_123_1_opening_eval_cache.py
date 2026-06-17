"""phase 123.1 opening_position_eval cache table

Phase 123.1 SEED-053: create the opening-eval dedup cache table. One row per
distinct full_hash in the opening region (ply <= DEDUP_MAX_PLY). Populated by
scripts/backfill_opening_eval_cache.py (NOT this migration — see D-123.1-06).

The table is keyed by full_hash (BIGINT PK). Columns match game_positions
exactly: SmallInteger eval_cp/eval_mate, String(5) best_move. No FK, no cascade,
no invalidation logic — the cached value is position-intrinsic and immutable.

Revision ID: 20260617_130000
Revises: 20260616_120000
Create Date: 2026-06-17 13:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260617_130000"
down_revision: Union[str, None] = "20260616_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create opening_position_eval table."""
    op.create_table(
        "opening_position_eval",
        sa.Column("full_hash", sa.BigInteger(), nullable=False),
        sa.Column("eval_cp", sa.SmallInteger(), nullable=True),
        sa.Column("eval_mate", sa.SmallInteger(), nullable=True),
        sa.Column("best_move", sa.String(length=5), nullable=True),
        sa.PrimaryKeyConstraint("full_hash"),
    )


def downgrade() -> None:
    """Drop opening_position_eval table."""
    op.drop_table("opening_position_eval")
