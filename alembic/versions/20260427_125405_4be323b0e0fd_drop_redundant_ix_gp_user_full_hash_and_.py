"""drop redundant ix_gp_user_full_hash and unused ix_gp_user_endgame_class

Prod usage analysis (pg_stat_user_indexes):

- ix_gp_user_full_hash (user_id, full_hash): 132 idx_scans, 571 MB.
  Fully covered by ix_gp_user_full_hash_move_san as a B-tree prefix —
  PostgreSQL can serve any (user_id, full_hash) lookup from the wider
  composite index. The 132 scans currently hitting the narrow index will
  re-route to the wider one with negligible overhead.

- ix_gp_user_endgame_class (user_id, endgame_class) WHERE endgame_class
  IS NOT NULL: 0 idx_scans, 48 MB. Genuinely unused — endgame queries
  go through ix_gp_user_endgame_game instead.

Reclaims ~620 MB on prod, ~365 MB on dev.

Revision ID: 4be323b0e0fd
Revises: d7f960830d54
Create Date: 2026-04-27 12:54:05.436562+00:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = '4be323b0e0fd'
down_revision: Union[str, Sequence[str], None] = 'd7f960830d54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_gp_user_full_hash', table_name='game_positions')
    op.drop_index(
        'ix_gp_user_endgame_class',
        table_name='game_positions',
        postgresql_where='endgame_class IS NOT NULL',
    )


def downgrade() -> None:
    op.create_index(
        'ix_gp_user_endgame_class',
        'game_positions',
        ['user_id', 'endgame_class'],
        unique=False,
        postgresql_where='endgame_class IS NOT NULL',
    )
    op.create_index(
        'ix_gp_user_full_hash',
        'game_positions',
        ['user_id', 'full_hash'],
        unique=False,
    )
