"""add covering index for endgame queries

Revision ID: befacc0fce23
Revises: b7198d53627c
Create Date: 2026-03-27 09:32:52.655937+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'befacc0fce23'
down_revision: Union[str, Sequence[str], None] = 'b7198d53627c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Float(precision=24) vs REAL alter_column noise removed — semantically equivalent in PostgreSQL.
    op.create_index('ix_gp_user_endgame_game', 'game_positions', ['user_id', 'game_id', 'endgame_class', 'ply'], unique=False, postgresql_where=sa.text('endgame_class IS NOT NULL'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_gp_user_endgame_game', table_name='game_positions', postgresql_where=sa.text('endgame_class IS NOT NULL'))
