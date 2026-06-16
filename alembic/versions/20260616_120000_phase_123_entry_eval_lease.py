"""phase 123 entry eval lease columns

Phase 123 SEED-051: add entry-ply (import-time) lease columns to games so the
in-process server drain and remote eval workers can partition entry-ply evaluation
via SKIP-LOCKED LIFO claims.

Two nullable columns:
  entry_eval_lease_expiry  — when the current lease expires (TTL-based reclaim).
  entry_eval_leased_by     — worker-identifier label (VARCHAR(16), not TEXT — D-09).

NULL = unclaimed, which is the correct default. No backfill is needed or wanted:
pre-phase games with evals_completed_at IS NOT NULL are already out of the queue
predicate; games with evals_completed_at IS NULL that are mid-flight on the
server drain will simply be claimed again by the new lease predicate on the next
drain tick.

No new index: ix_games_evals_pending (on id, WHERE evals_completed_at IS NULL)
already backs both the LIFO ORDER BY id DESC claim and the D-5 OFFSET existence
probe. Adding a composite index on the lease columns is deferred until a measured
plan regression appears (RESEARCH Assumption A2 / Claude's Discretion).

Revision ID: 20260616_120000
Revises: 7d5a4aa09a47
Create Date: 2026-06-16 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260616_120000"
down_revision: Union[str, None] = "7d5a4aa09a47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add two nullable entry-eval lease columns to games (no backfill, no new index)."""
    op.add_column(
        "games",
        sa.Column("entry_eval_lease_expiry", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "games",
        # D-09: VARCHAR(16) not TEXT — fits "remote-worker" (13) and ~8-char worker IDs.
        sa.Column("entry_eval_leased_by", sa.String(16), nullable=True),
    )


def downgrade() -> None:
    """Drop entry-eval lease columns in reverse order."""
    op.drop_column("games", "entry_eval_leased_by")
    op.drop_column("games", "entry_eval_lease_expiry")
