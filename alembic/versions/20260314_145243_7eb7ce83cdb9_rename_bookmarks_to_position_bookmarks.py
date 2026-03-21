"""rename bookmarks to position_bookmarks

Revision ID: 7eb7ce83cdb9
Revises: f10322cb88b3
Create Date: 2026-03-14 14:52:43.367580

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7eb7ce83cdb9'
down_revision: Union[str, Sequence[str], None] = 'f10322cb88b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename bookmarks table and its index to position_bookmarks."""
    op.rename_table('bookmarks', 'position_bookmarks')
    op.execute('ALTER INDEX ix_bookmarks_user_id RENAME TO ix_position_bookmarks_user_id')


def downgrade() -> None:
    """Revert rename: position_bookmarks back to bookmarks."""
    op.execute('ALTER INDEX ix_position_bookmarks_user_id RENAME TO ix_bookmarks_user_id')
    op.rename_table('position_bookmarks', 'bookmarks')
