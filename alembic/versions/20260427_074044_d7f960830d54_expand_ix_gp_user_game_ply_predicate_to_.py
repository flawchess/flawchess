"""expand ix_gp_user_game_ply predicate to include ply 0 (#71 hotfix)

Phase 71 surfaced a Phase 70 SQL bug: the opening-insights query needs
GamePosition.move_san at ply 0 (the very first move of the game) to be in
the partition window so entry_san_sequence can be replayed without
chess.IllegalMoveError. The repository SQL now filters
`ply BETWEEN 0 AND OPENING_INSIGHTS_MAX_ENTRY_PLY + 1` (= 0..17), so the
partial index predicate must also include ply 0 to keep the Index Only Scan
plan that the original Phase 70 perf work depends on.

Revision ID: d7f960830d54
Revises: 80e22b38993a
Create Date: 2026-04-27 07:40:44.372009+00:00

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd7f960830d54'
down_revision: Union[str, Sequence[str], None] = '80e22b38993a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Recreate ix_gp_user_game_ply with predicate `ply BETWEEN 0 AND 17`."""
    op.drop_index('ix_gp_user_game_ply', table_name='game_positions')
    op.create_index(
        'ix_gp_user_game_ply',
        'game_positions',
        ['user_id', 'game_id', 'ply'],
        unique=False,
        postgresql_where='ply BETWEEN 0 AND 17',
        postgresql_include=['full_hash', 'move_san'],
    )


def downgrade() -> None:
    """Restore the original `ply BETWEEN 1 AND 17` predicate."""
    op.drop_index('ix_gp_user_game_ply', table_name='game_positions')
    op.create_index(
        'ix_gp_user_game_ply',
        'game_positions',
        ['user_id', 'game_id', 'ply'],
        unique=False,
        postgresql_where='ply BETWEEN 1 AND 17',
        postgresql_include=['full_hash', 'move_san'],
    )
