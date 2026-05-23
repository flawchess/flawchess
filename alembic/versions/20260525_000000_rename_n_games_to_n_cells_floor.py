"""Rename user_benchmark_percentiles.n_games to n_cells_floor.

Phase 94.1 Plan 11 (gap-closure for REVIEW.md CR-01).

The column was originally named ``n_games`` in plan 94.1-04 (revision
``82a2b6d4888f``) and documented as "Number of canonical-slice games that
contributed to ``value``". But the service writes
``n_games=n_cells_floor``: the count of (elo_bucket, tc_bucket) cells that
pass the per-metric HAVING inclusion floor at compute time, NOT a game
count. The two diverge by roughly 25x for a typical user (1 game can
contribute to multiple cells, and the floor filters most cells out). See
``app/services/user_benchmark_percentiles_service.py`` and
``.planning/phases/94.1-canonical-slice-user-percentile-materialisation/94.1-REVIEW.md``
CR-01 for the full rationale.

This rename is reversible. The upgrade renames the column and updates the
column COMMENT to explain the semantics. The downgrade reverts both. The
table is non-empty by the time this migration ships (plan 94.1-09 wrote
real rows during HUMAN-UAT); the rename preserves data because Postgres
RENAME COLUMN is a metadata-only DDL operation.

Revision ID: 74c5d42318a1
Revises: 82a2b6d4888f
Create Date: 2026-05-23 15:24:04.461022+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "74c5d42318a1"
down_revision: str | Sequence[str] | None = "82a2b6d4888f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename n_games to n_cells_floor and set an explanatory COMMENT."""
    op.alter_column(
        "user_benchmark_percentiles",
        "n_games",
        new_column_name="n_cells_floor",
    )
    op.execute(
        "COMMENT ON COLUMN user_benchmark_percentiles.n_cells_floor IS "
        "'Count of (elo_bucket, tc_bucket) cells that passed the per-metric HAVING "
        "inclusion floor at compute time. NOT a game count. See Phase 94.1 "
        "REVIEW.md CR-01 for the rename rationale.'"
    )


def downgrade() -> None:
    """Revert n_cells_floor back to n_games and clear the COMMENT."""
    op.execute("COMMENT ON COLUMN user_benchmark_percentiles.n_cells_floor IS NULL")
    op.alter_column(
        "user_benchmark_percentiles",
        "n_cells_floor",
        new_column_name="n_games",
    )
