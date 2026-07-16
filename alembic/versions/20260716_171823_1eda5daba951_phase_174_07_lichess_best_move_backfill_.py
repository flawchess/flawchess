"""phase 174-07 lichess best-move backfill index

Adds ix_games_lichess_pv_backfill_pending — a partial index backing the
174-07/SEED-109 broadened residual fallback in
eval_queue_service._claim_tier3_derived:
    WHERE lichess_evals_at IS NOT NULL AND full_pv_completed_at IS NULL
          AND u.is_guest = false
    ORDER BY -ln(random()) / game_weight LIMIT 1

Mirrors ix_games_needs_engine_full_evals (Phase 119) and the migration this
one supersedes, ix_games_pv_backfill_pending (20260623210000): that earlier
index backed the OLD residual-fallback predicate
(full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL), which the
174-07 broadening replaces with full_pv_completed_at IS NULL. The old index's
predicate no longer matches any query in the codebase — it is dropped here
rather than left as permanent dead weight, since every lichess-eval game
already stamped full_evals_completed_at (the common case; often set at
import) would have made the old index a poor match for the query it was
built for anyway.

Created non-concurrently (inside transaction), following the project's other
partial-index migrations (ix_games_user_evals_pending, ix_games_full_pv_pending,
ix_games_needs_engine_full_evals, ix_games_pv_backfill_pending): migrations run
against a quiescent backend at container startup, and CONCURRENTLY cannot run
in a transaction.

Revision ID: 1eda5daba951
Revises: 903b54b77161
Create Date: 2026-07-16 17:18:23.958030+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1eda5daba951"
down_revision: Union[str, Sequence[str], None] = "903b54b77161"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the superseded index first (its predicate no longer matches any query).
    op.drop_index(
        "ix_games_pv_backfill_pending",
        table_name="games",
        postgresql_where=sa.text(
            "full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL"
        ),
    )

    # New partial index backing the broadened residual fallback (174-07/SEED-109).
    op.create_index(
        "ix_games_lichess_pv_backfill_pending",
        "games",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text("lichess_evals_at IS NOT NULL AND full_pv_completed_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_games_lichess_pv_backfill_pending",
        table_name="games",
        postgresql_where=sa.text("lichess_evals_at IS NOT NULL AND full_pv_completed_at IS NULL"),
    )

    op.create_index(
        "ix_games_pv_backfill_pending",
        "games",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text(
            "full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL"
        ),
    )
