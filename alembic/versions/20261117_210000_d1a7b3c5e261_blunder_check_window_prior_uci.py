"""blunder check window prior uci

Quick task 261117-sfh follow-up: the Ready gate shows a window's start position before any
window move is played, so the board needs the game move that led to that position for the usual
last-move highlight. ``blunder_check_windows.prior_uci`` stores it at composition.

Nullable, no backfill: NULL means the window starts at the game's first position, or was composed
before this column existed (those windows show the gate without a highlight).

ADD COLUMN of a nullable column without a default is a catalog-only change in PostgreSQL.

Revision ID: d1a7b3c5e261
Revises: c9f4e1a3d254
Create Date: 2026-11-17 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1a7b3c5e261"
down_revision: Union[str, Sequence[str], None] = "c9f4e1a3d254"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "blunder_check_windows", sa.Column("prior_uci", sa.String(length=5), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("blunder_check_windows", "prior_uci")
