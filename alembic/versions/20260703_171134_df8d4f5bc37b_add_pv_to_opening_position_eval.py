"""add pv to opening_position_eval

Revision ID: df8d4f5bc37b
Revises: eb341e836ee9
Create Date: 2026-07-03 17:11:34.265143+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df8d4f5bc37b'
down_revision: Union[str, Sequence[str], None] = 'eb341e836ee9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('opening_position_eval', sa.Column('pv', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('opening_position_eval', 'pv')
