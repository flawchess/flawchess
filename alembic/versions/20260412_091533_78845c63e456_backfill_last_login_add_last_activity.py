"""backfill last_login add last_activity

Revision ID: 78845c63e456
Revises: 3e4018d62102
Create Date: 2026-04-12 09:15:33.575473+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78845c63e456'
down_revision: Union[str, Sequence[str], None] = '3e4018d62102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backfill existing users: set last_login = created_at where NULL.
    # This is a permanent data correction — not undone in downgrade.
    op.execute(
        "UPDATE users SET last_login = created_at WHERE last_login IS NULL"
    )

    op.add_column('users', sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True))

    # Seed last_activity from last_login so existing users don't start at NULL
    op.execute("UPDATE users SET last_activity = last_login")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'last_activity')
