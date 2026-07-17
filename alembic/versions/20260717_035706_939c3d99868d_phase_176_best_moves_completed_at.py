"""phase 176 best_moves_completed_at

Phase 176 BACK-01 (D-01/D-02/D-04): adds the best-move-pass completion marker
`games.best_moves_completed_at`, one-time-stamps it for games that already have
`game_best_moves` coverage (D-04 — avoids needlessly re-draining the small
go-forward/174-07-covered population), and adds the partial index backing the
new tier-4b spare-capacity lottery predicate in
`eval_queue_service._claim_tier4_bestmove`.

Revision ID: 939c3d99868d
Revises: 1eda5daba951
Create Date: 2026-07-17 03:57:06.256906+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "939c3d99868d"
down_revision: Union[str, Sequence[str], None] = "1eda5daba951"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "games",
        sa.Column("best_moves_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # D-04: one-time stamp for games that already have COMPLETE best-move coverage
    # (the ~go-forward + 174-07-covered population) so they aren't needlessly
    # re-drained by the new tier-4b lottery. Ordered BEFORE create_index so the
    # index is built on already-stamped data.
    #
    # WR-01 (Phase 176 code review): the `game_best_moves` upsert in
    # `eval_apply._upsert_best_move_rows` runs unconditionally on every eval pass,
    # including Path B (holes remain, full_pv_completed_at still NULL). Gating only
    # on EXISTS(game_best_moves) would prematurely stamp such partially-covered,
    # not-yet-full_pv-complete games — violating the "stamped ⇒ best-move pass
    # complete" invariant. Require full_pv_completed_at IS NOT NULL so the stamp
    # targets exactly the lottery's population, and use that timestamp directly
    # (no now() fallback needed once the predicate guarantees it is non-NULL).
    op.execute(
        sa.text("""
            UPDATE games g
            SET best_moves_completed_at = g.full_pv_completed_at
            WHERE g.full_pv_completed_at IS NOT NULL
              AND EXISTS (
                SELECT 1 FROM game_best_moves gbm WHERE gbm.game_id = g.id
            )
        """)
    )
    op.create_index(
        "ix_games_bestmove_backfill_pending",
        "games",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text(
            "full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL"
            " AND lichess_evals_at IS NULL"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_games_bestmove_backfill_pending", table_name="games")
    op.drop_column("games", "best_moves_completed_at")
