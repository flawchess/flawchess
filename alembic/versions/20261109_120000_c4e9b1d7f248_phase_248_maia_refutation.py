"""phase 248 maia refutation

Phase 248 (D-01, D-09, D-22): adds the blunder-check refutation pair to ``game_flaws``
(``maia_refutation_prob`` REAL, ``maia_refutation_rank`` SMALLINT) and the per-game
completion stamp ``games.maia_refutation_completed_at``.

Definition (D-20): the refutation is Stockfish's best reply in the position after the
user's blunder, i.e. ``COALESCE(game_positions.best_move, first pv token)`` at
``ply = game_flaws.ply + 1`` (opponent to move). The pair is Maia's probability and rank
for that reply at the blunderer's rating. Only user-side blunders (severity 2, user
parity) are scored; every other row keeps NULL.

Deliberately metadata-only: no server_default, no CHECK constraint, no index and no
data UPDATE. A nullable ADD COLUMN without a default is a catalog-only change in
PostgreSQL, so the migration is instant on the 7.6M-row ``game_flaws`` table. The stamp
is not indexed (no partial index, D-22): the backfill selector runs once per shard at
start, and an index on a nearly-all-NULL column would need CREATE INDEX CONCURRENTLY
outside the migration transaction for no gain.

Revision ID: c4e9b1d7f248
Revises: a7d3f1c9e247
Create Date: 2026-11-09 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4e9b1d7f248"
down_revision: Union[str, Sequence[str], None] = "a7d3f1c9e247"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("game_flaws", sa.Column("maia_refutation_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_refutation_rank", sa.SmallInteger(), nullable=True))
    op.add_column(
        "games",
        sa.Column("maia_refutation_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("games", "maia_refutation_completed_at")
    op.drop_column("game_flaws", "maia_refutation_rank")
    op.drop_column("game_flaws", "maia_refutation_prob")
