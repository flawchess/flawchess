"""SEED-055 drop write-only intermediate columns from game_positions

Revision ID: b8fddd63bd95
Revises: b6e2978df54f
Create Date: 2026-06-19 20:15:08.994736+00:00

Drops 7 columns of game_positions that were computed at import and written but
never read by any serving query:
  material_count, material_imbalance, has_opposite_color_bishops,
  material_signature, piece_count, backrank_sparse, mixedness.

The derived columns endgame_class and phase (which ARE read) are still computed
in-memory at import time from these same values (position_classifier.py); only
the persisted copies are dropped.

NOTE: DROP COLUMN does not reclaim disk on existing rows — Postgres only flags
the attributes as dropped and the bytes remain in every existing tuple.
game_positions is append-only, so no natural churn reclaims them. To realize the
~1.6 GB on prod's existing ~46.7M rows a full rewrite is required (pg_repack
online, or VACUUM FULL with an ACCESS EXCLUSIVE lock). That rewrite is a separate
operational step, intentionally NOT part of this migration. Forward-going the
benefit is automatic: every new import row is 34 bytes smaller.

The downgrade re-adds the columns as nullable but cannot restore dropped data.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8fddd63bd95"
down_revision: Union[str, Sequence[str], None] = "b6e2978df54f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("game_positions", "mixedness")
    op.drop_column("game_positions", "backrank_sparse")
    op.drop_column("game_positions", "material_imbalance")
    op.drop_column("game_positions", "has_opposite_color_bishops")
    op.drop_column("game_positions", "piece_count")
    op.drop_column("game_positions", "material_signature")
    op.drop_column("game_positions", "material_count")


def downgrade() -> None:
    """Downgrade schema. Re-adds the columns as nullable; dropped data is not restored."""
    op.add_column(
        "game_positions",
        sa.Column("material_count", sa.SMALLINT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "game_positions",
        sa.Column("material_signature", sa.VARCHAR(length=65), autoincrement=False, nullable=True),
    )
    op.add_column(
        "game_positions",
        sa.Column("piece_count", sa.SMALLINT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "game_positions",
        sa.Column("has_opposite_color_bishops", sa.BOOLEAN(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "game_positions",
        sa.Column("material_imbalance", sa.SMALLINT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "game_positions",
        sa.Column("backrank_sparse", sa.BOOLEAN(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "game_positions", sa.Column("mixedness", sa.SMALLINT(), autoincrement=False, nullable=True)
    )
