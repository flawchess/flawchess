"""add backrank_sparse and mixedness columns

Revision ID: 798b9ccff13f
Revises: 265efff85685
Create Date: 2026-03-26 13:43:28.173814+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '798b9ccff13f'
down_revision: Union[str, Sequence[str], None] = '265efff85685'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('game_positions', sa.Column('backrank_sparse', sa.Boolean(), nullable=True))
    op.add_column('game_positions', sa.Column('mixedness', sa.SmallInteger(), nullable=True))
    # No backfill — user will run reimport_games.py manually.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('game_positions', 'mixedness')
    op.drop_column('game_positions', 'backrank_sparse')
