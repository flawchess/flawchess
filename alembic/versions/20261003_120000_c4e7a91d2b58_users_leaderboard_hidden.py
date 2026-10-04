"""users leaderboard_hidden

Revision ID: c4e7a91d2b58
Revises: 3b7e2f9c41a6
Create Date: 2026-10-03 12:00:00+00:00

Phase 230 weekly Train leaderboards: a server-persisted opt-out flag. Default
false so every registered user appears on the boards until they opt out.
Also adds a partial solved_at index on drill_solves for the weekly window
scan, which runs on every Train landing view.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e7a91d2b58'
down_revision: Union[str, Sequence[str], None] = '3b7e2f9c41a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('leaderboard_hidden', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.create_index(
        'ix_drill_solves_solved_at',
        'drill_solves',
        ['solved_at'],
        unique=False,
        postgresql_where=sa.text('solved_at IS NOT NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_drill_solves_solved_at',
        table_name='drill_solves',
        postgresql_where=sa.text('solved_at IS NOT NULL'),
    )
    op.drop_column('users', 'leaderboard_hidden')
