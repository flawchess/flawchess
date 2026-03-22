"""fix time_control_bucket for 600s games

Revision ID: b5b8170c0f72
Revises: 9549c5e62259
Create Date: 2026-03-22 13:58:25.838144+00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b5b8170c0f72'
down_revision: Union[str, Sequence[str], None] = '9549c5e62259'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Recalculate all time_control_bucket values from time_control_str using the
# corrected thresholds: <180 bullet, <600 blitz, <=1800 rapid, else classical.
# This applies the same formula as parse_time_control() in normalization.py:
#   estimated = base + increment * 40
_RECALCULATE_SQL = """
UPDATE games
SET time_control_bucket = sub.new_bucket
FROM (
    SELECT id,
        CASE
            WHEN time_control_str IS NULL THEN NULL
            WHEN time_control_str LIKE '%%/%%' THEN 'classical'
            WHEN time_control_str LIKE '%%+%%' THEN
                CASE
                    WHEN SPLIT_PART(time_control_str, '+', 1)::int
                       + SPLIT_PART(time_control_str, '+', 2)::int * 40 < 180
                        THEN 'bullet'
                    WHEN SPLIT_PART(time_control_str, '+', 1)::int
                       + SPLIT_PART(time_control_str, '+', 2)::int * 40 < 600
                        THEN 'blitz'
                    WHEN SPLIT_PART(time_control_str, '+', 1)::int
                       + SPLIT_PART(time_control_str, '+', 2)::int * 40 <= 1800
                        THEN 'rapid'
                    ELSE 'classical'
                END
            ELSE
                CASE
                    WHEN time_control_str::int < 180 THEN 'bullet'
                    WHEN time_control_str::int < 600 THEN 'blitz'
                    WHEN time_control_str::int <= 1800 THEN 'rapid'
                    ELSE 'classical'
                END
        END AS new_bucket
    FROM games
    WHERE time_control_str IS NOT NULL
) sub
WHERE games.id = sub.id
  AND (games.time_control_bucket IS DISTINCT FROM sub.new_bucket)
"""


def upgrade() -> None:
    """Recalculate all time_control_bucket values using corrected thresholds."""
    op.execute(_RECALCULATE_SQL)


def downgrade() -> None:
    """No safe downgrade — the old bucketing logic was incorrect."""
    pass
