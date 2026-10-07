"""drill_solves recheck

Revision ID: c5e8a2d7b914
Revises: f4b9d2c7e815
Create Date: 2026-10-07 12:00:00+00:00

SEED-192 / Phase 235 (D-17/D-18): one row per phone disagreement re-check
(outcome, both expected-score pairs, search depths, and the server's `accepted`
flag) so answer-key quality can be judged from prod solves per source. It is a
separate column from `telemetry` because it feeds grading (D-14), and Phase 233
D-05 forbids telemetry as a grading input. Written once per solve (a plain set,
never merged).

No backfill: existing rows stay NULL, which reads as "no re-check ran". Adding a
nullable column without a default is metadata-only in Postgres, so this is
instant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c5e8a2d7b914'
down_revision: Union[str, Sequence[str], None] = 'f4b9d2c7e815'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('drill_solves', sa.Column('recheck', postgresql.JSONB(none_as_null=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('drill_solves', 'recheck')
