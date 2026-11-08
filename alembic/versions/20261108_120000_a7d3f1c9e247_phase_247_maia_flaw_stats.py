"""phase 247 maia flaw stats

Phase 247 (D-01, D-02, D-07): adds eight nullable Maia per-flaw stat columns to
``game_flaws`` and the per-game completion stamp ``games.maia_flaws_completed_at``.

Columns (all NULL = not scored): maia_played_prob / maia_played_rank,
maia_best_prob / maia_best_rank, maia_second_prob / maia_second_rank,
maia_top_prob, maia_effective_moves. No ``maia_elo`` column on purpose (D-02).

Deliberately metadata-only: no server_default, no CHECK constraint, no index and no
data UPDATE. On the 7.6M-row ``game_flaws`` table a nullable ADD COLUMN without a
default is a catalog-only change in PostgreSQL, so the migration is instant. The
stamp is not indexed because the backfill selector scans per user and the
population of unstamped games is small relative to the cost of maintaining a
partial index on a hot table.

Revision ID: a7d3f1c9e247
Revises: e2a7c4f9b244
Create Date: 2026-11-08 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7d3f1c9e247"
down_revision: Union[str, Sequence[str], None] = "e2a7c4f9b244"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("game_flaws", sa.Column("maia_played_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_played_rank", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_best_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_best_rank", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_second_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_second_rank", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_top_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_effective_moves", sa.REAL(), nullable=True))
    op.add_column(
        "games",
        sa.Column("maia_flaws_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("games", "maia_flaws_completed_at")
    op.drop_column("game_flaws", "maia_effective_moves")
    op.drop_column("game_flaws", "maia_top_prob")
    op.drop_column("game_flaws", "maia_second_rank")
    op.drop_column("game_flaws", "maia_second_prob")
    op.drop_column("game_flaws", "maia_best_rank")
    op.drop_column("game_flaws", "maia_best_prob")
    op.drop_column("game_flaws", "maia_played_rank")
    op.drop_column("game_flaws", "maia_played_prob")
