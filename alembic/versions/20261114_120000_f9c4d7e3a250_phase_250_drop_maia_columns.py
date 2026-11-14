"""phase 250 drop maia columns

Phase 250 (D-11): the facepalm selection no longer reads the Phase 247 / 248 per-flaw Maia
values below, so they are dropped together with the code that computed them.

Dropped from ``game_flaws`` (all nullable REAL / SMALLINT):

- ``maia_played_rank``, ``maia_best_prob``, ``maia_best_rank``, ``maia_second_prob``,
  ``maia_second_rank``, ``maia_top_prob``, ``maia_effective_moves`` (Phase 247)
- ``maia_refutation_prob``, ``maia_refutation_rank`` (Phase 248)

Dropped from ``games``: ``maia_refutation_completed_at`` (Phase 248 stamp).

Kept: ``game_flaws.maia_played_prob`` (still a facepalm input), ``maia_reply_spread`` and the
other Phase 250 columns, and the stamps ``games.maia_flaws_completed_at``,
``games.facepalm_spread_completed_at`` and ``games.facepalm_line_completed_at``.

Data loss is by design (owner decision recorded in 250-09, ``d11_go: yes``). The downgrade
re-adds the columns EMPTY; the values are recomputable at the parent revision with the
Phase 247 / 248 backfill (``scripts/backfill_maia_flaws.py``, about half a day of Maia work).

DROP COLUMN is a catalog-only change in PostgreSQL: no table rewrite on the ~7.6M-row
``game_flaws`` table, the dead column space is reclaimed lazily by later row rewrites.

Deploy rule: no operator script (the Maia backfill, the blunder-check calibration, the
facepalm features builder) may be running while this migration executes, because an old-model
process selecting a dropped column would fail the moment the column is gone.

Revision ID: f9c4d7e3a250
Revises: e8b3c6d2f250
Create Date: 2026-11-14 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f9c4d7e3a250"
down_revision: Union[str, Sequence[str], None] = "e8b3c6d2f250"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("games", "maia_refutation_completed_at")
    op.drop_column("game_flaws", "maia_refutation_rank")
    op.drop_column("game_flaws", "maia_refutation_prob")
    op.drop_column("game_flaws", "maia_effective_moves")
    op.drop_column("game_flaws", "maia_top_prob")
    op.drop_column("game_flaws", "maia_second_rank")
    op.drop_column("game_flaws", "maia_second_prob")
    op.drop_column("game_flaws", "maia_best_rank")
    op.drop_column("game_flaws", "maia_best_prob")
    op.drop_column("game_flaws", "maia_played_rank")


def downgrade() -> None:
    """Downgrade schema (re-adds the columns empty)."""
    op.add_column("game_flaws", sa.Column("maia_played_rank", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_best_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_best_rank", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_second_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_second_rank", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_top_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_effective_moves", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_refutation_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_refutation_rank", sa.SmallInteger(), nullable=True))
    op.add_column(
        "games",
        sa.Column("maia_refutation_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
