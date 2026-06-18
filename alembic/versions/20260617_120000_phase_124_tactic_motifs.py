"""Phase 124: Add tactic_motif, tactic_piece, tactic_confidence to game_flaws.

Three nullable SmallInteger columns. Adding nullable columns to PostgreSQL 18
is a pure catalog update — no table rewrite, no extended lock on the game_flaws
table. Safe to run inline at deploy time via deploy/entrypoint.sh.

Existing rows carry NULL in all three columns after migration (no backfill needed
or wanted — Phase 125 backfill script will populate tactic fields for
full_evals_completed_at games).

Revision ID: 20260617_120000_phase_124
Revises: 20260617_130000
Create Date: 2026-06-17 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260617_120000_phase_124"
down_revision: Union[str, None] = "20260617_130000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tactic_motif, tactic_piece, tactic_confidence to game_flaws (no backfill)."""
    op.add_column("game_flaws", sa.Column("tactic_motif", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("tactic_piece", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("tactic_confidence", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    """Drop tactic columns in reverse order."""
    op.drop_column("game_flaws", "tactic_confidence")
    op.drop_column("game_flaws", "tactic_piece")
    op.drop_column("game_flaws", "tactic_motif")
