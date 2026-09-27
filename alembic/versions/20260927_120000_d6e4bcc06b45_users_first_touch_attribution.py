"""users first-touch attribution

Revision ID: d6e4bcc06b45
Revises: feab8324235d
Create Date: 2026-09-27 12:00:00+00:00

Growth report 2026-09-15, item 16: record where each account's browser first
arrived from (external referrer host, utm_source/medium/campaign, landing
path) in one nullable JSONB column, so signup and retention cohorts can be
split by acquisition source. No backfill: pre-existing accounts stay NULL,
which reads as "never recorded".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd6e4bcc06b45'
down_revision: Union[str, Sequence[str], None] = 'feab8324235d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('first_touch', postgresql.JSONB(none_as_null=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'first_touch')
