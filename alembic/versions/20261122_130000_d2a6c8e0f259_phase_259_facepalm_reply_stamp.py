"""phase 259 facepalm reply stamp

Phase 259 (D-07, D-11): adds the per-game checkpoint of the best-reply backfill pass.

``games.facepalm_reply_completed_at`` TIMESTAMPTZ NULL marks the games whose blunders (both
sides, D-10) have had ``game_flaws.maia_best_reply_prob`` filled by ``scripts/backfill_maia_flaws.py
--mode reply``. It lets the pass resume after an interruption (the 02:15 UTC prod reboot) and
lets a second run select nothing. Same lifecycle and no-index reasoning as the four earlier
facepalm stamps: cleared by a reclassification, set by the full-mode hook.

Why this is instant: a nullable ADD COLUMN without a default is a catalog-only change in
PostgreSQL, so no table scan or rewrite happens on the large ``games`` table.

Revision ID: d2a6c8e0f259
Revises: d1e5f7a9c259
Create Date: 2026-11-22 13:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2a6c8e0f259"
down_revision: Union[str, Sequence[str], None] = "d1e5f7a9c259"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "games",
        sa.Column("facepalm_reply_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("games", "facepalm_reply_completed_at")
