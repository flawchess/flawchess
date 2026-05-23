"""Drop n_cells_floor column from user_benchmark_percentiles.

Phase 94.1 Plan 13 (gap-closure for Plan 11 HUMAN-UAT correctness bugs).

The ``n_cells_floor`` column was introduced in plan 94.1-04 (as ``n_games``),
renamed in plan 94.1-11. It was used solely as a binary gate (``== 0``) to
decide whether to set ``percentile=NULL``. With plan 94.1-13, the
``_compute_metric_for_user`` helper switches to a single CTE query with
``apply_floor=True``, meaning:

- If the user has zero floor-passing cells, the CTE returns no rows → no row is
  written to ``user_benchmark_percentiles`` at all. The chip suppresses naturally.
- If the user has ≥1 floor-passing cells, a row IS written. The existence of a
  row now implies above-floor.

The column is therefore write-only from production code's perspective and
provides no read value. This migration drops it.

**Downgrade is data-lossy**: the original ``n_cells_floor`` values cannot be
restored from the remaining columns. The downgrade recreates the column as
NULLable so existing rows are not blocked, but the values will be NULL for all
rows that existed before the downgrade. This is acceptable because:

1. The below-floor row semantics are being dropped entirely in Plan 13 — no
   row is written for below-floor users, so the column would be meaningless.
2. Re-running the backfill script after a downgrade would re-populate the table
   without the ``n_cells_floor`` column anyway (it is removed from the service).

Revision ID: a7f3c9b82e14
Revises: 74c5d42318a1
Create Date: 2026-05-25 01:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7f3c9b82e14"
down_revision: str | Sequence[str] | None = "74c5d42318a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the n_cells_floor column from user_benchmark_percentiles.

    Below-floor users no longer have rows in this table — the column was the
    only signal used to set percentile=NULL and is now redundant. Row existence
    is the new floor indicator (no row = below floor).
    """
    op.drop_column("user_benchmark_percentiles", "n_cells_floor")


def downgrade() -> None:
    """Recreate n_cells_floor as NULLable (data-lossy downgrade).

    WARNING: This downgrade is data-lossy. The original n_cells_floor values
    cannot be restored. All existing rows will have n_cells_floor = NULL after
    this downgrade. To restore meaningful values, re-run the Plan 13 backfill
    script after reverting the application code to Plan 11.

    The column is recreated as NULLable to avoid blocking existing rows, and
    to match the behavior of the original Plan 11 code when it writes new rows
    (which would re-populate the column).
    """
    op.add_column(
        "user_benchmark_percentiles",
        sa.Column("n_cells_floor", sa.Integer(), nullable=True),
    )
