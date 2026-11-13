"""phase 250 facepalm

Phase 250 (D-05): adds the facepalm-score facts to ``game_flaws`` and the two per-game
checkpoint stamps to ``games``.

``game_flaws`` (all nullable, NULL = not scored):

- ``maia_reply_spread`` REAL: effective number of opponent replies after the blunder
  (``2 ** entropy`` of the full Maia policy at ply + 1, at the blunderer's pinned Elo).
- ``line_loss_1`` / ``line_loss_3`` / ``line_loss_5`` / ``line_loss_7`` / ``line_loss_9``
  SMALLINT: net material the blunderer is down after following the stored refutation
  line (``game_positions.pv`` at ply + 1) for N plies. NULL = the line is too short to tell.
- ``line_mate_ply`` SMALLINT: first line ply after which the blunderer is checkmated,
  NULL = no mate in the stored line.
- ``facepalm_score`` REAL in [0, 1]: derived from ``maia_played_prob``, the reply spread
  and the line facts; NULL when any input is missing.

``games``: ``facepalm_spread_completed_at`` (Maia pass checkpoint) and
``facepalm_line_completed_at`` (line pass checkpoint, re-runnable with a cutoff, D-18).

Deliberately metadata-only: no server_default, no CHECK constraint, no index and no data
UPDATE. A nullable ADD COLUMN without a default is a catalog-only change in PostgreSQL, so
the migration is instant on the ~7.6M-row ``game_flaws`` table. The score range is
covered by tests instead of a CHECK so the ALTER stays instant.

Revision ID: e8b3c6d2f250
Revises: d5b8e2f1a249
Create Date: 2026-11-13 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8b3c6d2f250"
down_revision: Union[str, Sequence[str], None] = "d5b8e2f1a249"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("game_flaws", sa.Column("maia_reply_spread", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_loss_1", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_loss_3", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_loss_5", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_loss_7", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_loss_9", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_mate_ply", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("facepalm_score", sa.REAL(), nullable=True))
    op.add_column(
        "games",
        sa.Column("facepalm_spread_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "games",
        sa.Column("facepalm_line_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("games", "facepalm_line_completed_at")
    op.drop_column("games", "facepalm_spread_completed_at")
    op.drop_column("game_flaws", "facepalm_score")
    op.drop_column("game_flaws", "line_mate_ply")
    op.drop_column("game_flaws", "line_loss_9")
    op.drop_column("game_flaws", "line_loss_7")
    op.drop_column("game_flaws", "line_loss_5")
    op.drop_column("game_flaws", "line_loss_3")
    op.drop_column("game_flaws", "line_loss_1")
    op.drop_column("game_flaws", "maia_reply_spread")
