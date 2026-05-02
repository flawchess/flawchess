"""add phase column to game_positions

Revision ID: 1efcc66a7695
Revises: c92af8282d1a
Create Date: 2026-05-02 20:39:48.590428+00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "1efcc66a7695"
down_revision: Union[str, None] = "c92af8282d1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable phase SmallInteger column to game_positions.

    Phase 79 SCHEMA-01: nullable because existing rows are populated by
    scripts/backfill_eval.py (PHASE-FILL-01), not by this migration. New rows
    inserted by the import path (after this migration deploys) are populated
    at insert time via classify_position(board).phase.

    Idempotent (IF NOT EXISTS) so the column may be created manually in prod
    ahead of deploy to allow the backfill to run before the new code ships;
    the migration then no-ops on container startup.
    """
    op.execute("ALTER TABLE game_positions ADD COLUMN IF NOT EXISTS phase SMALLINT")


def downgrade() -> None:
    """Drop the phase column."""
    op.execute("ALTER TABLE game_positions DROP COLUMN IF EXISTS phase")
