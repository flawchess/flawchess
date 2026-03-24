"""add foreign key constraints on user_id columns

Revision ID: c2989a16a11e
Revises: 1fac8294077e
Create Date: 2026-03-24 18:53:35.611003+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2989a16a11e'
down_revision: Union[str, Sequence[str], None] = '1fac8294077e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Cleans up orphaned rows (from prior missing FK constraints) before adding
    foreign key constraints. Deletion order respects dependencies:
    game_positions -> games -> import_jobs/position_bookmarks.
    """
    # Clean up orphaned rows before adding FK constraints
    op.execute(
        "DELETE FROM game_positions WHERE user_id NOT IN (SELECT id FROM users)"
    )
    op.execute(
        "DELETE FROM games WHERE user_id NOT IN (SELECT id FROM users)"
    )
    op.execute(
        "DELETE FROM import_jobs WHERE user_id NOT IN (SELECT id FROM users)"
    )
    op.execute(
        "DELETE FROM position_bookmarks WHERE user_id NOT IN (SELECT id FROM users)"
    )

    # Add FK constraints with explicit names
    op.create_foreign_key(
        'fk_game_positions_user_id', 'game_positions', 'users',
        ['user_id'], ['id'], ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_games_user_id', 'games', 'users',
        ['user_id'], ['id'], ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_import_jobs_user_id', 'import_jobs', 'users',
        ['user_id'], ['id'], ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_position_bookmarks_user_id', 'position_bookmarks', 'users',
        ['user_id'], ['id'], ondelete='CASCADE',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_position_bookmarks_user_id', 'position_bookmarks', type_='foreignkey')
    op.drop_constraint('fk_import_jobs_user_id', 'import_jobs', type_='foreignkey')
    op.drop_constraint('fk_games_user_id', 'games', type_='foreignkey')
    op.drop_constraint('fk_game_positions_user_id', 'game_positions', type_='foreignkey')
