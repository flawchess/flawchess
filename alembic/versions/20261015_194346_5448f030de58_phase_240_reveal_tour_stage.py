"""phase 240 reveal tour stage

Revision ID: 5448f030de58
Revises: 778c806092fb
Create Date: 2026-10-15 19:43:46.000000+00:00

Phase 240 (D-09/D-10): the Phase 222 single "reveal walkthrough seen" timestamp
becomes a forward-only reveal-tour stage counter, because the reveal tour is
split into three parts spread over consecutive reveals (D-06/D-07).

- Adds `reveal_tour_stage` SmallInteger NOT NULL DEFAULT 0 with a CHECK
  (0..3): the number of completed tour parts, 3 meaning the whole tour is done.
- Backfills stage 3 for every row whose Phase 222 walkthrough timestamp was
  non-null (the user finished the old single tour), leaving everyone else on 0
  so a user mid-onboarding at deploy starts the split tour at part 1 (D-12).
- Drops the Phase 222 walkthrough timestamp column.

One-way data note (owner accepted in discuss, D-10): the instant at which a
user completed the old walkthrough is lost; the stage only keeps "finished or
not". The downgrade restores the column schema-wise and stamps an approximate
`now()` for every stage-3 row.

The CHECK bound is a literal (3), not derived from
`app.services.train_scheduler.REVEAL_TOUR_STAGE_MAX`: a migration is a frozen
artifact that must stand on its own forever (same reasoning as the Phase 193
shield_level CHECK). The model derives the same bound from the constant.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5448f030de58"
down_revision: Union[str, Sequence[str], None] = "778c806092fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "train_settings",
        sa.Column("reveal_tour_stage", sa.SmallInteger(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        "ck_train_settings_reveal_tour_stage",
        "train_settings",
        "reveal_tour_stage BETWEEN 0 AND 3",
    )
    # D-10/D-12: a non-null Phase 222 timestamp means the user finished the old
    # single tour, so they have seen the whole split tour's content (stage 3).
    op.execute(
        "UPDATE train_settings SET reveal_tour_stage = 3 "
        "WHERE reveal_walkthrough_seen_at IS NOT NULL"
    )
    op.drop_column("train_settings", "reveal_walkthrough_seen_at")


def downgrade() -> None:
    """Downgrade schema.

    Schema-reversible; the data half is approximate. The original completion
    instants are gone, so every stage-3 row gets `now()` as a stand-in and every
    other row lands on NULL ("not finished"). Stages 1 and 2 (a partly done
    split tour) collapse to NULL: the old single tour replays from the start.
    """
    op.add_column(
        "train_settings",
        sa.Column("reveal_walkthrough_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Approximate instant: the real completion time was dropped by the upgrade.
    op.execute(
        "UPDATE train_settings SET reveal_walkthrough_seen_at = now() WHERE reveal_tour_stage = 3"
    )
    op.drop_constraint("ck_train_settings_reveal_tour_stage", "train_settings", type_="check")
    op.drop_column("train_settings", "reveal_tour_stage")
