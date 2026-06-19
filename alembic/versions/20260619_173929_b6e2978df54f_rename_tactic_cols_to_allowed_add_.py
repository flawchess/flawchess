"""rename tactic cols to allowed, add missed tactic cols

Revision ID: b6e2978df54f
Revises: 9be5294cfe3c
Create Date: 2026-06-19 17:39:29.409903+00:00

Phase 128 — D-01/D-02:
- Rename the 4 existing tactic_* columns to allowed_tactic_* (data-preserving ALTER RENAME).
  The 4 allowed_* columns carry all Phase 124/125/127 tags unchanged — no data loss.
- Add 4 new nullable missed_tactic_* columns (NULL on pre-existing rows until the Phase 128
  missed-pass backfill runs, per D-11).

upgrade():  4 ALTER RENAME (data-preserving) + 4 ADD COLUMN (nullable)
downgrade(): DROP the 4 missed_* columns + ALTER RENAME the 4 allowed_* back to tactic_*
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6e2978df54f'
down_revision: Union[str, Sequence[str], None] = '9be5294cfe3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Data-preserving rename of 4 tactic_* → allowed_tactic_* + 4 new missed_tactic_* columns."""
    # Rename existing columns — data is preserved; no DROP/ADD (T-128-01 mitigation).
    op.alter_column('game_flaws', 'tactic_motif', new_column_name='allowed_tactic_motif')
    op.alter_column('game_flaws', 'tactic_piece', new_column_name='allowed_tactic_piece')
    op.alter_column('game_flaws', 'tactic_confidence', new_column_name='allowed_tactic_confidence')
    op.alter_column('game_flaws', 'tactic_depth', new_column_name='allowed_tactic_depth')
    # Add 4 new missed_tactic_* columns — all nullable, NULL until the Phase 128 missed pass runs.
    op.add_column('game_flaws', sa.Column('missed_tactic_motif', sa.SmallInteger(), nullable=True))
    op.add_column('game_flaws', sa.Column('missed_tactic_piece', sa.SmallInteger(), nullable=True))
    op.add_column('game_flaws', sa.Column('missed_tactic_confidence', sa.SmallInteger(), nullable=True))
    op.add_column('game_flaws', sa.Column('missed_tactic_depth', sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    """Drop the 4 missed_tactic_* columns + rename allowed_tactic_* back to tactic_*."""
    # Drop the 4 new missed_* columns added in upgrade.
    op.drop_column('game_flaws', 'missed_tactic_depth')
    op.drop_column('game_flaws', 'missed_tactic_confidence')
    op.drop_column('game_flaws', 'missed_tactic_piece')
    op.drop_column('game_flaws', 'missed_tactic_motif')
    # Rename allowed_* back to original tactic_* names (reverse the data-preserving renames).
    op.alter_column('game_flaws', 'allowed_tactic_depth', new_column_name='tactic_depth')
    op.alter_column('game_flaws', 'allowed_tactic_confidence', new_column_name='tactic_confidence')
    op.alter_column('game_flaws', 'allowed_tactic_piece', new_column_name='tactic_piece')
    op.alter_column('game_flaws', 'allowed_tactic_motif', new_column_name='tactic_motif')
