"""phase 259 facepalm scalars

Phase 259 (D-05, D-07): adds the stored scalar inputs of the first-principles facepalm score to
``game_flaws``. This is release R1 of the rollout: the scalars are written for every new blunder
(both sides, D-10) before any reader switches to them (D-11).

``game_flaws`` (all nullable, NULL = not scored or not computed yet):

- ``material_loss`` REAL: the decaying-mean material the blunderer loses along the played line,
  read at quiet points (D-02 to D-04).
- ``material_missed`` REAL: the decaying-mean material gain the blunderer left on the table
  along the engine's best line, under the same quiet rule.
- ``maia_best_reply_prob`` REAL: Maia's probability of the first token of the stored refutation
  line (the opponent's punishing reply) at the blunderer's pinned Elo (D-07).

Three CHECK constraints keep the scalars well formed: the two material columns are NULL together
(``ck_game_flaws_material_pair``) and each is non-negative.

Why this is instant on the ~12 GB ``game_flaws`` table: a nullable ADD COLUMN without a default
is a catalog-only change in PostgreSQL, and the CHECKs are added NOT VALID, which skips the table
scan (every existing row is NULL in these columns anyway, so the constraints would hold). NOT
VALID still enforces the check on every row written afterwards. There is no data UPDATE: the line
pass (operator tool) fills the existing rows.

Revision ID: d1e5f7a9c259
Revises: 80050899e337
Create Date: 2026-11-22 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1e5f7a9c259"
down_revision: Union[str, Sequence[str], None] = "80050899e337"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("game_flaws", sa.Column("material_loss", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("material_missed", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_best_reply_prob", sa.REAL(), nullable=True))
    # NOT VALID: no table scan, enforced on every row written from now on.
    op.execute(
        "ALTER TABLE game_flaws ADD CONSTRAINT ck_game_flaws_material_pair "
        "CHECK ((material_loss IS NULL) = (material_missed IS NULL)) NOT VALID"
    )
    op.execute(
        "ALTER TABLE game_flaws ADD CONSTRAINT ck_game_flaws_material_loss_nonneg "
        "CHECK (material_loss >= 0) NOT VALID"
    )
    op.execute(
        "ALTER TABLE game_flaws ADD CONSTRAINT ck_game_flaws_material_missed_nonneg "
        "CHECK (material_missed >= 0) NOT VALID"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TABLE game_flaws DROP CONSTRAINT IF EXISTS ck_game_flaws_material_missed_nonneg"
    )
    op.execute(
        "ALTER TABLE game_flaws DROP CONSTRAINT IF EXISTS ck_game_flaws_material_loss_nonneg"
    )
    op.execute("ALTER TABLE game_flaws DROP CONSTRAINT IF EXISTS ck_game_flaws_material_pair")
    op.drop_column("game_flaws", "maia_best_reply_prob")
    op.drop_column("game_flaws", "material_missed")
    op.drop_column("game_flaws", "material_loss")
