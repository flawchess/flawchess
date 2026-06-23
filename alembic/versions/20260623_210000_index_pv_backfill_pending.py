"""Add ix_games_pv_backfill_pending — partial index for the tier-3 residual-fallback pick.

The tier-3 residual fallback in eval_queue_service._claim_tier3_derived picks a
PV-backfill-only game via:
    WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL
          AND u.is_guest = false
    ORDER BY -ln(random()) / game_weight LIMIT 1

No index matched this predicate, so every remote-worker idle poll ran a parallel
seq scan over the whole games table (~230k buffers, ~300 ms) — even when the
candidate set is empty (the common steady state, since needs-engine games are
guest-owned and excluded). Several workers polling ~1/s made this the single
dominant query by total exec time and the main driver of the low buffer
cache-hit ratio (it churned ~1.8 GB through shared_buffers every second).

This partial index turns that scan into an index scan over only the matching
rows (near-instant when empty), mirroring ix_games_needs_engine_full_evals which
backs the Step-1/Step-2 needs-engine path. The ORDER BY is a random ES key so no
index can serve the ordering, but the cost was the candidate gather, not the
small sort. Rows leave the index as full_evals_completed_at is set, so it stays
small.

Created non-concurrently (inside transaction) following the project's other
partial-index migrations (ix_games_user_evals_pending, ix_games_full_pv_pending,
ix_games_needs_engine_full_evals): migrations run against a quiescent backend at
container startup, and CONCURRENTLY cannot run in a transaction.

Revision ID: 20260623210000
Revises: b8fddd63bd95
Create Date: 2026-06-23 21:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260623210000"
down_revision: Union[str, None] = "b8fddd63bd95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_games_pv_backfill_pending",
        "games",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text(
            "full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("ix_games_pv_backfill_pending", table_name="games")
