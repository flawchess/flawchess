"""Phase 119: full_eval_attempts column + ix_games_needs_engine_full_evals + drop dead index.

This single migration owns the whole Phase 119 schema:
1. games.full_eval_attempts SmallInteger (SEED-045 bounded-retry hole-filling counter).
2. ix_games_needs_engine_full_evals partial index (SEED-046 lottery candidate-pool index).
3. Drop ix_eval_jobs_user_active (dead after plan 03 removes count_in_flight_evals).

Plans 02 and 03 depend on this migration but do not edit it.

Revision ID: 20260614150000
Revises: 20260614140000 (Phase 118 ix_eval_jobs_user_active)
Create Date: 2026-06-14 15:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260614150000"
down_revision: Union[str, None] = "20260614140000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add games.full_eval_attempts — SmallInteger, NOT NULL, server_default '0'.
    #    Server default backfills existing rows to 0 without a separate UPDATE.
    #    Per-game counter of drain ticks that left a non-terminal hole (SEED-045).
    op.add_column(
        "games",
        sa.Column(
            "full_eval_attempts",
            sa.SmallInteger(),
            nullable=False,
            server_default="0",
        ),
    )

    # 2. Create ix_games_needs_engine_full_evals — SEED-046 lottery candidate-pool index.
    #    Predicate matches needs_engine_full_evals exactly:
    #      full_evals_completed_at IS NULL AND lichess_evals_at IS NULL
    #    Created non-concurrently (inside transaction) — correct for migrations run against
    #    a quiescent backend at container startup. CONCURRENTLY cannot run in a transaction
    #    and the project's other partial indexes use the same non-concurrent pattern
    #    (ix_games_user_evals_pending, ix_games_full_pv_pending).
    op.create_index(
        "ix_games_needs_engine_full_evals",
        "games",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text(
            "full_evals_completed_at IS NULL AND lichess_evals_at IS NULL"
        ),
    )

    # 3. Drop ix_eval_jobs_user_active — dead after plan 03 removes count_in_flight_evals.
    #    Dropping before the reader is removed is safe: at worst, one in-flight count poll
    #    runs a full table scan during the deploy window (acceptable per plan rationale).
    op.drop_index("ix_eval_jobs_user_active", table_name="eval_jobs")


def downgrade() -> None:
    # Reverse all three ops in reverse order.

    # 3 reversed: re-create ix_eval_jobs_user_active with its original predicate.
    op.create_index(
        "ix_eval_jobs_user_active",
        "eval_jobs",
        ["user_id"],
        unique=False,
        postgresql_where="status IN ('pending', 'leased')",
    )

    # 2 reversed: drop the SEED-046 candidate-pool partial index.
    op.drop_index("ix_games_needs_engine_full_evals", table_name="games")

    # 1 reversed: drop the full_eval_attempts column.
    op.drop_column("games", "full_eval_attempts")
