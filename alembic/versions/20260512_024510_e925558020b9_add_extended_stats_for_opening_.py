"""add extended statistics for opening insights planner

The opening insights endpoint (`POST /api/insights/openings`) timed out
in prod for users in a specific cardinality band (e.g. user 84, 718 games,
~50k game_positions). EXPLAIN ANALYZE showed the PostgreSQL planner
estimating `rows=1` for `(user_id=X, ply BETWEEN 0 AND 17)` predicates
because column-level stats treat `user_id` and `ply` as independent. The
mis-estimate cascaded into Nested Loop joins at every level of the
opening transitions query, blowing up to 137s wall time / 400M buffer
hits on a 12k-row CTE × 271-game outer join.

The Phase 71 / PR #89 JOIN-over-EXISTS fix solved the *index choice*
aspect of the standard-start subquery for a 499-game test user, but the
*Nested-Loop-cascade* in the outer query is a distinct planner issue
that only surfaces on certain user shapes.

Multi-column extended statistics on `(user_id, ply)` and
`(user_id, user_color)` give the planner correct cardinality (12,834
rows estimated vs the previous `rows=1`), which flips Nested Loops to
Index Scans on the primary key. Same user goes from 137s → 36ms.

Revision ID: e925558020b9
Revises: 9083c5eedb02
Create Date: 2026-05-12 02:45:10.000000+00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e925558020b9"
down_revision: Union[str, None] = "9083c5eedb02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create extended statistics for opening-insights planner mis-estimates.

    `dependencies` captures functional dependencies (e.g. how strongly
    `ply` constrains `user_id`), `ndistinct` captures the distinct count
    of the combined column tuple, and `mcv` captures the most-common
    multi-column values. All three help PG produce realistic row
    estimates for `WHERE user_id = X AND ply BETWEEN 0 AND 17` and
    `WHERE user_id = X AND user_color = 'white'`.

    ANALYZE is run inline so the stats are populated immediately rather
    than waiting for the next autovacuum cycle (which on 24M-row
    `game_positions` may be hours away in prod).
    """
    op.execute(
        "CREATE STATISTICS IF NOT EXISTS stat_gp_user_ply "
        "(dependencies, ndistinct, mcv) "
        "ON user_id, ply FROM game_positions"
    )
    op.execute(
        "CREATE STATISTICS IF NOT EXISTS stat_games_user_color "
        "(dependencies, ndistinct, mcv) "
        "ON user_id, user_color FROM games"
    )
    op.execute("ANALYZE game_positions")
    op.execute("ANALYZE games")


def downgrade() -> None:
    """Drop the extended statistics. Planner will fall back to per-column stats."""
    op.execute("DROP STATISTICS IF EXISTS stat_games_user_color")
    op.execute("DROP STATISTICS IF EXISTS stat_gp_user_ply")
