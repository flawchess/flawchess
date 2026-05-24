"""Add n_games column to user_benchmark_percentiles (re-add).

Phase 94.2 (D-9-amend, correction to D-9). The history of this column:

- 94.1-04 added ``n_games`` to ``user_benchmark_percentiles`` (per-cell count).
- 94.1-11 renamed ``n_games`` → ``n_cells_floor`` (semantic clarification —
  the value was actually the count of floor-passing cells, not games).
- 94.1-13 dropped ``n_cells_floor`` entirely once row existence became the
  above-floor signal (see ``20260525_010000_drop_n_cells_floor.py``).

Under the pooled-per-user methodology adopted in 94.2, ``n_games`` is again
semantically meaningful: one integer per ``(user_id, metric)`` row carrying
the binding inclusion-floor count on the pooled set:

- ``score_gap`` → endgame-games count (the binding floor; paired
  non-endgame count goes in the backfill summary log, not the table).
- ``achievable_score_gap`` → count of endgame-entry games with non-null
  ``d_i`` on the pool.
- ``section2_score_gap_conv`` → conversion-bucket span count on the pool.
- ``section2_score_gap_parity`` → parity-bucket span count on the pool.

``server_default='0'`` lets existing rows backfill to 0 atomically at upgrade
time; Plan 06's backfill rerun populates the correct values across the deploy
window. Plan 03's service rewrite threads ``n_games`` through every new write
so default-0 rows only persist for the deploy-to-backfill-completion gap.

Revision ID: b8f4d92c1e25
Revises: a7f3c9b82e14
Create Date: 2026-05-26 00:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8f4d92c1e25"
down_revision: str | Sequence[str] | None = "a7f3c9b82e14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the ``n_games`` INT NOT NULL DEFAULT 0 column.

    The server-side default backfills existing rows atomically to 0. Plan 06's
    backfill rerun replaces those with correct per-user pooled counts; the
    code path written in 94.2-03 unconditionally supplies ``n_games`` on every
    UPSERT.
    """
    op.add_column(
        "user_benchmark_percentiles",
        sa.Column("n_games", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Drop the ``n_games`` column.

    Data-lossy: stored ``n_games`` values cannot be reconstructed from the
    remaining columns. Acceptable because the upstream backfill always
    repopulates this column from the pooled CTE.
    """
    op.drop_column("user_benchmark_percentiles", "n_games")
