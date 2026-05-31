"""Rename benchmark_metric ENUM values: drop ``section2_`` prefix.

Renames two values in the ``benchmark_metric`` Postgres ENUM:

- ``section2_score_gap_conv``   → ``score_gap_conv``
- ``section2_score_gap_parity`` → ``score_gap_parity``

The prefix was historical from when the conv/parity metrics lived under
"Section 2" of the endgame analytics page. The naming was inconsistent
with the third bucket (``recovery_score_gap``, prefix-free) and with the
rest of the metric family. Dropping the prefix gives a clean
``score_gap_{conv,parity,recov}`` triad. No collisions: ``score_gap``
and ``score_gap_*`` did not exist as ENUM values before this migration.

PostgreSQL's ``ALTER TYPE ... RENAME VALUE`` is non-destructive and
preserves all existing rows referencing these values.

Revision ID: 4c42ebc87b7f
Revises: 1945ae56aa20
Create Date: 2026-05-27 08:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c42ebc87b7f"
down_revision: Union[str, Sequence[str], None] = "1945ae56aa20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE benchmark_metric RENAME VALUE 'section2_score_gap_conv' TO 'score_gap_conv'"
    )
    op.execute(
        "ALTER TYPE benchmark_metric RENAME VALUE 'section2_score_gap_parity' TO 'score_gap_parity'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TYPE benchmark_metric RENAME VALUE 'score_gap_parity' TO 'section2_score_gap_parity'"
    )
    op.execute(
        "ALTER TYPE benchmark_metric RENAME VALUE 'score_gap_conv' TO 'section2_score_gap_conv'"
    )
