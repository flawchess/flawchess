"""phase 222 train onboarding seen

Revision ID: 7d6bb75aae54
Revises: b7d4f5a60002
Create Date: 2026-09-13 14:47:12.032849+00:00

TRAINBOT-05 (D-11/D-12/D-13): adds three nullable `DateTime(timezone=True)`
"explanation seen" watermarks on `train_settings` -- `intro_seen_at`,
`reveal_walkthrough_seen_at`, `sr_explained_at` -- stamped by a dedicated
POST /train/onboarding/{step} endpoint on stepper completion. Response-only
(D-12): these never appear on `TrainSettingsUpdate`.

No backfill, no data migration: every existing row lands on NULL on all
three columns, meaning "this explanation has never been completed" --
regulars, one-timers and never-finishers all see each stepper once.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d6bb75aae54'
down_revision: Union[str, Sequence[str], None] = 'b7d4f5a60002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "train_settings", sa.Column("intro_seen_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "train_settings",
        sa.Column("reveal_walkthrough_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "train_settings", sa.Column("sr_explained_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("train_settings", "sr_explained_at")
    op.drop_column("train_settings", "reveal_walkthrough_seen_at")
    op.drop_column("train_settings", "intro_seen_at")
