"""drill_solves phone_grade

Revision ID: d3a7f1c9e246
Revises: c5e8a2d7b914
Create Date: 2026-10-08 12:00:00+00:00

SEED-193 / Phase 236 (D-01): the phone's own 1.5 s grading reading for each
keyed solve (tier, key and played expected scores, both search depths) so phone
grading accuracy (phone tier vs the effective `move_quality`, phone vs a
depth-18 spot check) becomes a query instead of a Stockfish re-run. It is a
separate column from `telemetry` (Phase 233 D-05) and from `recheck` (one
meaning per column, D-04: this is always the 1.5 s reading, never the 3 s
re-check reading). Written once: by the solve claim UPDATE (D-13) or by the
review route via coalesce (D-12).

No backfill (go-forward only): existing rows stay NULL, which reads as "no
phone reading recorded". Adding a nullable column without a default is
metadata-only in Postgres, so this is instant on prod.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd3a7f1c9e246'
down_revision: Union[str, Sequence[str], None] = 'c5e8a2d7b914'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('drill_solves', sa.Column('phone_grade', postgresql.JSONB(none_as_null=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('drill_solves', 'phone_grade')
