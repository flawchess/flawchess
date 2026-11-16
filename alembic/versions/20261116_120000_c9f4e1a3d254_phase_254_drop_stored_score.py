"""phase 254 drop stored score

Phase 254 (D-02, D-19): the final, human-gated drop of the stored facepalm score and the five
legacy line-loss columns from ``game_flaws``. This is release R3 of the three-release rollout.

Dropped from ``game_flaws`` (all nullable):

- ``facepalm_score`` REAL: the stored score. It is computed at query time from the stored facts
  by ``facepalm_expr(FACEPALM_LIBRARY_LAMBDA)`` (254 D-01), so a refit or a new lambda never
  rewrites rows.
- ``line_loss_1`` / ``line_loss_3`` / ``line_loss_5`` / ``line_loss_7`` / ``line_loss_9``
  SMALLINT: the legacy line-loss snapshots. The signed ``played_line_material`` array (254 D-09)
  replaces them; the R1 to R2 copy was verified and its tool is deleted.

Kept: ``line_mate_ply``, ``maia_played_prob``, ``maia_reply_spread`` and the Phase 254 fact
columns (``played_line_material``, ``best_line_material``, ``best_line_mate_ply``,
``maia_best_prob``, ``maia_pre_spread``), plus the ``games`` stamps.

Data loss is by design (owner decision in 254-CONTEXT, D-02). The downgrade re-adds the six
columns EMPTY; the line-loss values are recomputable from ``played_line_material`` and the score
from the facts.

DROP COLUMN is a catalog-only change in PostgreSQL: no table rewrite on the ~7.6M-row
``game_flaws`` table, the dead column space is reclaimed lazily by later row rewrites.

Deploy rule: no operator script (the Maia backfill, the blunder-check calibration, the
facepalm features builder) may be running while this migration executes, because an old-model
process selecting a dropped column would fail the moment the column is gone.

Revision ID: c9f4e1a3d254
Revises: c3f8e2a6d255
Create Date: 2026-11-16 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9f4e1a3d254"
down_revision: Union[str, Sequence[str], None] = "c3f8e2a6d255"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("game_flaws", "facepalm_score")
    op.drop_column("game_flaws", "line_loss_9")
    op.drop_column("game_flaws", "line_loss_7")
    op.drop_column("game_flaws", "line_loss_5")
    op.drop_column("game_flaws", "line_loss_3")
    op.drop_column("game_flaws", "line_loss_1")


def downgrade() -> None:
    """Downgrade schema (re-adds the columns empty)."""
    op.add_column("game_flaws", sa.Column("line_loss_1", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_loss_3", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_loss_5", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_loss_7", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("line_loss_9", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("facepalm_score", sa.REAL(), nullable=True))
