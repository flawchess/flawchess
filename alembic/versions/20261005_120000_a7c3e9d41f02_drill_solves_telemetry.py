"""drill_solves telemetry

Revision ID: a7c3e9d41f02
Revises: e3a8c5f17b20
Create Date: 2026-10-05 12:00:00+00:00

SEED-190 / Phase 233 (D-01): record HOW each Train puzzle was solved (think
time, review time, reveal engagement, device class) in one nullable JSONB
column instead of individual columns. The table is small (~8k rows, ~300 new
rows/day), new counters then need no migration, and the behavioral data stays
separate from the grading fields. Written only by merging
(`coalesce(telemetry, '{}') || patch`), never overwritten.

No backfill: existing rows stay NULL, which reads as "pre-feature or a client
that sent none". Adding a nullable column without a default is metadata-only
in Postgres, so this is instant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a7c3e9d41f02'
down_revision: Union[str, Sequence[str], None] = 'e3a8c5f17b20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('drill_solves', sa.Column('telemetry', postgresql.JSONB(none_as_null=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('drill_solves', 'telemetry')
