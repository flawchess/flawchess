"""Phase 118: add ix_eval_jobs_user_active partial index for in-flight count queries.

D-118-12 / Pitfall 7: count_in_flight_evals and count_tier2_in_flight both filter
eval_jobs by user_id WHERE status IN ('pending', 'leased'). Without an index, these
counts require a full table scan at 3-second polling intervals — O(n) per poll at
scale. The partial index restricts the index to only active (in-flight) rows, keeping
it small at steady state (completed/failed rows are excluded).

Both D-118-12 count queries benefit from a single index on (user_id) WHERE status IN
('pending', 'leased') — the user_id equality filter is the primary predicate, and the
partial WHERE clause eliminates completed/failed rows from the index entirely.

Revision ID: 20260614140000
Revises: 20260614130000 (Phase 117.2 wipe-eval-only-residue)
Create Date: 2026-06-14 14:00:00
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260614140000"
down_revision: Union[str, None] = "20260614130000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_eval_jobs_user_active",
        "eval_jobs",
        ["user_id"],
        unique=False,
        postgresql_where="status IN ('pending', 'leased')",
    )


def downgrade() -> None:
    op.drop_index("ix_eval_jobs_user_active", table_name="eval_jobs")
