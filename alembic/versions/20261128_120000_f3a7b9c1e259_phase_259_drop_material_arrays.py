"""Drop the 9-slot material arrays, their shape CHECKs and the old covering index.

Phase 259 D-05 / D-06 / D-17. The first-principles facepalm score reads five stored scalars
(material_loss, material_missed, maia_played_prob, maia_best_prob, maia_best_reply_prob) through
ix_game_flaws_facepalm_inputs, and since the switch release nothing reads the two 9-slot
SMALLINT[] material arrays (played_line_material, best_line_material). This is the drop release:

1. DROP INDEX CONCURRENTLY IF EXISTS ix_game_flaws_blunder_facts, first, in an autocommit block
   (the index is ~741 MB on prod and carries both arrays; CONCURRENTLY keeps the lock short, D-17).
2. DROP CONSTRAINT IF EXISTS for the two NOT VALID shape CHECKs (ck_game_flaws_played_line_material_shape
   and ck_game_flaws_best_line_material_shape).
3. DROP COLUMN for both arrays (catalog-only in PostgreSQL; the space returns on the next rewrite).

PostgreSQL would drop the index and the CHECKs together with the columns; the explicit statements
keep the lock short and make the downgrade a clean mirror.

ONE-WAY IN PRACTICE (D-06): the downgrade re-adds the two columns empty (nullable, no values), the
two NOT VALID shape CHECKs exactly as a7d2c9e1b254 wrote them, and the old index with
b7e4a1c9d257's literal definition (non-concurrently). The array values are not restored: a line
pass with the previous rule from git history would be needed to refill them. This migration ships
only after phase 259 plan 15's blocking owner decision, and no operator script may run during the
deploy (the migration runs at container start against a live backend).

Literal values only: migrations are version-pinned snapshots and must not import live app
constants.

Revision ID: f3a7b9c1e259
Revises: e2f6a8b0d259
Create Date: 2026-11-28 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f3a7b9c1e259"
down_revision: Union[str, None] = "e2f6a8b0d259"
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
    """Drop the old covering index first (CONCURRENTLY), then the CHECKs, then the columns."""
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_game_flaws_blunder_facts")
    for column in _ARRAY_COLUMNS:
        op.execute(f"ALTER TABLE game_flaws DROP CONSTRAINT IF EXISTS ck_game_flaws_{column}_shape")
    for column in _ARRAY_COLUMNS:
        op.drop_column("game_flaws", column)


def downgrade() -> None:
    """Re-add the empty columns, their NOT VALID shape CHECKs and the old index (values are lost)."""
    for column in _ARRAY_COLUMNS:
        op.add_column(
            "game_flaws",
            sa.Column(column, postgresql.ARRAY(sa.SmallInteger()), nullable=True),
        )
    for column in _ARRAY_COLUMNS:
        op.execute(
            f"ALTER TABLE game_flaws ADD CONSTRAINT ck_game_flaws_{column}_shape "
            f"CHECK ({_shape_check(column)}) NOT VALID"
        )
    op.create_index(
        "ix_game_flaws_blunder_facts",
        "game_flaws",
        ["user_id", "game_id"],
        unique=False,
        postgresql_include=[
            "ply",
            "maia_played_prob",
            "maia_reply_spread",
            "played_line_material",
            "line_mate_ply",
            "best_line_material",
            "best_line_mate_ply",
            "maia_best_prob",
            "maia_pre_spread",
        ],
        postgresql_where=sa.text("severity = 2"),
    )
