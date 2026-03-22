"""fix time_control_bucket for 600s games

Revision ID: b5b8170c0f72
Revises: 9549c5e62259
Create Date: 2026-03-22 13:58:25.838144+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5b8170c0f72'
down_revision: Union[str, Sequence[str], None] = '9549c5e62259'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All time_control_str patterns where estimated = base + increment*40 = 600.
# These were bucketed as 'blitz' under the old <= 600 threshold but should be
# 'rapid' under the corrected < 600 threshold.
_AFFECTED_PATTERNS = [
    "600",      # 600+0 = 600
    "560+1",    # 560 + 1*40 = 600
    "520+2",    # 520 + 2*40 = 600
    "480+3",    # 480 + 3*40 = 600
    "440+4",    # 440 + 4*40 = 600
    "400+5",    # 400 + 5*40 = 600
    "360+6",    # 360 + 6*40 = 600
    "320+7",    # 320 + 7*40 = 600
    "280+8",    # 280 + 8*40 = 600
    "240+9",    # 240 + 9*40 = 600
    "200+10",   # 200 + 10*40 = 600
]


def upgrade() -> None:
    """Fix games where estimated duration is exactly 600s from blitz -> rapid."""
    placeholders = ", ".join(f"'{p}'" for p in _AFFECTED_PATTERNS)
    op.execute(
        f"UPDATE games SET time_control_bucket = 'rapid' "
        f"WHERE time_control_str IN ({placeholders}) AND time_control_bucket = 'blitz'"
    )


def downgrade() -> None:
    """Revert: set affected games back to blitz (restores original incorrect behavior)."""
    placeholders = ", ".join(f"'{p}'" for p in reversed(_AFFECTED_PATTERNS))
    op.execute(
        f"UPDATE games SET time_control_bucket = 'blitz' "
        f"WHERE time_control_str IN ({placeholders}) AND time_control_bucket = 'rapid'"
    )
