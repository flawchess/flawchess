"""add persona_id to games

Phase 185 Plan 01 (T-185-01): adds a nullable persona_id column to `games` for
per-persona win tracking. Client-supplied on POST /bots/games, persisted only
for persona-mode bot games (custom-mode games and every pre-existing row stay
NULL — no backfill, no retroactive persona identity).

Metadata-only ADD COLUMN: no default value and no row-by-row backfill. Stays a
fast operation even at ~718k prod rows (contrast with the 60d9b72c0eaa
migration's full-table rewrite, which this migration deliberately avoids —
Pitfall 4).

Revision ID: 411a8de89c4b
Revises: 60d9b72c0eaa
Create Date: 2026-07-22 16:02:46.224111+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "411a8de89c4b"
down_revision: Union[str, Sequence[str], None] = "60d9b72c0eaa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable persona_id column. No default, no backfill (Pitfall 4)."""
    op.add_column("games", sa.Column("persona_id", sa.String(30), nullable=True))


def downgrade() -> None:
    """Drop persona_id column."""
    op.drop_column("games", "persona_id")
