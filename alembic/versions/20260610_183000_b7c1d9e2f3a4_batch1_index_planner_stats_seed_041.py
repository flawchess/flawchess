"""batch-1 index + planner-stats tuning (SEED-041 items 1a, 2, 3, 4)

Revision ID: b7c1d9e2f3a4
Revises: f8a2d1c9b345
Create Date: 2026-06-10 18:30:00.000000+00:00

SEED-041 batch 1, backed by reports/db-stats/db-schema-analysis-2026-06-10.md.

ITEMS:
  1a (§A1) full_hash planner statistics: SET STATISTICS 2000. Already applied in
     prod on 2026-06-10; this rides in the migration purely for dev/test parity.
     Idempotent (re-setting the same target is a no-op catalog write). Note the
     stats raise alone did NOT flip the openings-explorer plan in prod (the
     openings_dedup DISTINCT ON blocks MCV propagation); the query-side fallback
     lives in stats_repository.query_top_openings_sql_wdl(), not here.
  4  (§C2) game_positions autovacuum insert tuning. Also already applied in prod
     on 2026-06-10 (+ a one-time catch-up VACUUM (ANALYZE) run manually there);
     rides here for dev/test parity. Idempotent.
  2  (§A2) replace ix_games_user_id with (user_id, played_at DESC): lets the
     recent-games WindowAgg run-condition early-terminate instead of scanning the
     user's full game history. The new index serves every user_id-prefix lookup
     too, so dropping ix_games_user_id is safe.
  3  (§A3) partial (user_id) WHERE evals_completed_at IS NULL: makes the
     per-import-batch pending-evals gate sub-millisecond. Keep ix_games_evals_pending
     (on id) for the id-ordered drain poll.

CONCURRENTLY: CREATE/DROP INDEX CONCURRENTLY cannot run inside a transaction, so
the index swaps (items 2, 3) run in op.get_context().autocommit_block() (raw
connection, no surrounding BEGIN, each statement auto-commits). Prior art:
20260601_154355_84fd28051d7d and 20260603_153628_f4d88c3659c6. IF NOT EXISTS /
IF EXISTS guards make an interrupted prod run safe to retry. The plain-DDL items
(1a, 4) run first in the migration's own transaction (committed when the
autocommit_block opens).

Literal values only — migrations are version-pinned snapshots and must not import
live app constants (project rule).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c1d9e2f3a4"
down_revision: str | None = "f8a2d1c9b345"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Apply planner-stats/autovacuum settings (idempotent) and swap games indexes."""
    # Items 1a + 4 — plain, transactional, idempotent DDL (prod already has these).
    op.execute("ALTER TABLE game_positions ALTER COLUMN full_hash SET STATISTICS 2000")
    op.execute(
        "ALTER TABLE game_positions SET ("
        "autovacuum_vacuum_insert_scale_factor = 0.05, "
        "autovacuum_vacuum_insert_threshold = 100000)"
    )

    # Items 2 + 3 — CONCURRENTLY index swaps (must be outside a transaction).
    with op.get_context().autocommit_block():
        # Item 2: build the (user_id, played_at DESC) index, then drop the old one.
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_games_user_played_at "
            "ON games (user_id, played_at DESC)"
        )
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_games_user_id")
        # Item 3: partial index keyed by user for the pending-evals gate.
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_games_user_evals_pending "
            "ON games (user_id) WHERE evals_completed_at IS NULL"
        )


def downgrade() -> None:
    """Reverse the index swaps and reset the planner-stats/autovacuum settings (dev escape hatch)."""
    with op.get_context().autocommit_block():
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_games_user_id ON games (user_id)")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_games_user_evals_pending")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_games_user_played_at")

    op.execute("ALTER TABLE game_positions ALTER COLUMN full_hash SET STATISTICS -1")
    op.execute(
        "ALTER TABLE game_positions RESET ("
        "autovacuum_vacuum_insert_scale_factor, autovacuum_vacuum_insert_threshold)"
    )
