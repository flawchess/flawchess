"""quick gj7: index opening_cache_audit.sample_game_id, drop ix_games_full_pv_pending

Revision ID: c3a9e1f70003
Revises: 7d6bb75aae54
Create Date: 2026-09-16 12:00:00

Two follow-ups from reports/db-stats/db-report-prod-2026-09-16.md:

1. `opening_cache_audit.sample_game_id` carries an `ON DELETE SET NULL` FK to
   `games` (Phase 220 CACHEFIX-01) with no supporting index, so every user
   delete / re-import batch seq-scanned the 2.5M-row audit table once per
   deleted-games batch (prod: 3,266 scans x 158 ms, 9B tuples read). Add a
   partial index on the non-NULL rows (roughly a third of the table) so the
   FK's SET NULL action becomes an index lookup.

2. `ix_games_full_pv_pending` (Phase 117, `games(id) WHERE full_pv_completed_at
   IS NULL`, ~30 MB) has had zero scans in 12 weeks. Every live PV-pending
   pick in `app/services/eval_queue_service.py` also filters
   `lichess_evals_at IS NOT NULL`, which `ix_games_lichess_pv_backfill_pending`
   (Phase 174-07) already covers. Drop it; it was dead write overhead on a
   hot table. The model never declared it (migration-only index), so no model
   change accompanies the drop.

Both indexes are created/dropped non-concurrently, following the project's
other partial-index migrations: migrations run against a quiescent backend at
container startup, and CONCURRENTLY cannot run inside a transaction.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a9e1f70003"
down_revision: Union[str, Sequence[str], None] = "7d6bb75aae54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_opening_cache_audit_sample_game_id",
        "opening_cache_audit",
        ["sample_game_id"],
        unique=False,
        postgresql_where=sa.text("sample_game_id IS NOT NULL"),
    )
    op.drop_index(
        "ix_games_full_pv_pending",
        table_name="games",
        postgresql_where=sa.text("full_pv_completed_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index(
        "ix_games_full_pv_pending",
        "games",
        ["id"],
        unique=False,
        postgresql_where=sa.text("full_pv_completed_at IS NULL"),
    )
    op.drop_index(
        "ix_opening_cache_audit_sample_game_id",
        table_name="opening_cache_audit",
        postgresql_where=sa.text("sample_game_id IS NOT NULL"),
    )
