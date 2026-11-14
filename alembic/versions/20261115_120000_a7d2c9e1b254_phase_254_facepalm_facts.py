"""phase 254 facepalm facts

Phase 254 (D-09): adds the stored facts of the missed-gains facepalm score to ``game_flaws``
and the checkpoint stamp of the pre-blunder Maia pass to ``games``. This is release R1 of the
three-release rollout: the facts are stored for every new blunder before any reader switches
to the query-time expression.

``game_flaws`` (all nullable, NULL = not scored):

- ``played_line_material`` SMALLINT[9]: signed material along the played line, slot N = the
  material balance after N plies of the refutation line (``game_positions.pv`` at ply + 1).
  Positive = the blunderer is up, negative = down. Even slots are mid-exchange snapshots and
  may be NULL (D-17); a NULL slot means the line is too short to tell.
- ``best_line_material`` SMALLINT[9]: the same signed array along the engine's best line from
  the decision position (``game_positions.pv`` at ply). Slot 3 is the gain the blunderer left
  on the table; NULL array = the best line is unknown (D-18).
- ``best_line_mate_ply`` SMALLINT: the ply at which the best line mates the opponent, counting
  the best move as ply 0; NULL = no mate in the stored best line.
- ``maia_best_prob`` REAL: Maia's probability for the best move at the blunderer's pinned Elo.
- ``maia_pre_spread`` REAL: effective number of replies (``2 ** entropy`` of the Maia policy)
  of the position BEFORE the blunder, at the blunderer's pinned Elo.

``games``: ``facepalm_pre_completed_at``, the checkpoint of the pre-blunder Maia pass (D-08).

Two CHECK constraints keep a stored array well formed: ``ck_game_flaws_played_line_material_shape``
and ``ck_game_flaws_best_line_material_shape`` require the column to be NULL or a
one-dimensional 9-slot array whose lower bound is 1 (the SQL twin reads slot 3 with one-based
indexing, so a ``[0:8]`` array would silently read the wrong slot).

Why this is instant on the ~12 GB ``game_flaws`` table: a nullable ADD COLUMN without a default
is a catalog-only change in PostgreSQL, and the CHECKs are added NOT VALID, which skips the table
scan (every existing row is NULL in these columns anyway, so the constraints would hold). NOT
VALID still enforces the check on every row written afterwards. There is no data UPDATE.

The sign-flipped copy of the existing ``line_loss_*`` columns into ``played_line_material`` runs
as an operator tool, not here: migrations run at backend startup and a 7M-row copy would block
the container.

Revision ID: a7d2c9e1b254
Revises: f9c4d7e3a250
Create Date: 2026-11-15 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a7d2c9e1b254"
down_revision: Union[str, Sequence[str], None] = "f9c4d7e3a250"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ARRAY_COLUMNS: tuple[str, ...] = ("played_line_material", "best_line_material")


def _shape_check(column: str) -> str:
    """The NULL-or-9-slot-one-dimensional-from-1 predicate of a stored material array."""
    return (
        f"{column} IS NULL OR (cardinality({column}) = 9 "
        f"AND array_lower({column}, 1) = 1 AND array_ndims({column}) = 1)"
    )


def upgrade() -> None:
    """Upgrade schema."""
    for column in _ARRAY_COLUMNS:
        op.add_column(
            "game_flaws",
            sa.Column(column, postgresql.ARRAY(sa.SmallInteger()), nullable=True),
        )
    op.add_column("game_flaws", sa.Column("best_line_mate_ply", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_best_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_pre_spread", sa.REAL(), nullable=True))
    op.add_column(
        "games",
        sa.Column("facepalm_pre_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # NOT VALID: no table scan, enforced on every row written from now on.
    for column in _ARRAY_COLUMNS:
        op.execute(
            f"ALTER TABLE game_flaws ADD CONSTRAINT ck_game_flaws_{column}_shape "
            f"CHECK ({_shape_check(column)}) NOT VALID"
        )


def downgrade() -> None:
    """Downgrade schema."""
    for column in _ARRAY_COLUMNS:
        op.execute(f"ALTER TABLE game_flaws DROP CONSTRAINT IF EXISTS ck_game_flaws_{column}_shape")
    op.drop_column("games", "facepalm_pre_completed_at")
    op.drop_column("game_flaws", "maia_pre_spread")
    op.drop_column("game_flaws", "maia_best_prob")
    op.drop_column("game_flaws", "best_line_mate_ply")
    for column in reversed(_ARRAY_COLUMNS):
        op.drop_column("game_flaws", column)
