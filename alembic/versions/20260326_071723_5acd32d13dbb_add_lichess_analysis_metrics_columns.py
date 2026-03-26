"""add lichess analysis metrics columns

Revision ID: 5acd32d13dbb
Revises: cf839d2edbf8
Create Date: 2026-03-26 07:17:23.194253+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5acd32d13dbb'
down_revision: Union[str, Sequence[str], None] = 'cf839d2edbf8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('games', sa.Column('white_acpl', sa.SmallInteger(), nullable=True))
    op.add_column('games', sa.Column('black_acpl', sa.SmallInteger(), nullable=True))
    op.add_column('games', sa.Column('white_inaccuracies', sa.SmallInteger(), nullable=True))
    op.add_column('games', sa.Column('black_inaccuracies', sa.SmallInteger(), nullable=True))
    op.add_column('games', sa.Column('white_mistakes', sa.SmallInteger(), nullable=True))
    op.add_column('games', sa.Column('black_mistakes', sa.SmallInteger(), nullable=True))
    op.add_column('games', sa.Column('white_blunders', sa.SmallInteger(), nullable=True))
    op.add_column('games', sa.Column('black_blunders', sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('games', 'black_blunders')
    op.drop_column('games', 'white_blunders')
    op.drop_column('games', 'black_mistakes')
    op.drop_column('games', 'white_mistakes')
    op.drop_column('games', 'black_inaccuracies')
    op.drop_column('games', 'white_inaccuracies')
    op.drop_column('games', 'black_acpl')
    op.drop_column('games', 'white_acpl')
