"""drill_sessions entered_at

Revision ID: 3b7e2f9c41a6
Revises: d6e4bcc06b45
Create Date: 2026-09-27 14:00:00+00:00

Stamp the first Start/Resume press on a Train session. /train composes a
session on page mount as a status read, so the activity dashboard's
"first session, zero solved" share counted landing-page visitors who never
started. No backfill: pre-existing rows stay NULL, and the dashboard only
counts first sessions composed on or after the earliest stamp.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b7e2f9c41a6'
down_revision: Union[str, Sequence[str], None] = 'd6e4bcc06b45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'drill_sessions', sa.Column('entered_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('drill_sessions', 'entered_at')
