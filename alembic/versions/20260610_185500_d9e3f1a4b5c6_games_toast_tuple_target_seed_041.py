"""games heap densification: toast_tuple_target = 256 (SEED-041 item 6)

Revision ID: d9e3f1a4b5c6
Revises: c8d2e0f3a4b5
Create Date: 2026-06-10 18:55:00.000000+00:00

SEED-041 §C1: the avg PGN is ~2.6 KB and stays INLINE under the default 2 KB
TOAST threshold, so the games hot heap is ~1,275 MB at ~3.6 rows/page — and every
per-game lookup (the openings explorer's probes, endgame joins, WDL dedups, none
of which read pgn) drags ~2.2 KB rows through the buffer cache.

Lowering toast_tuple_target to 256 pushes the PGN out-of-line for effectively all
rows; the hot heap shrinks to ~150-250 MB (~25 rows/page) and becomes
cache-resident on the 16 GB host. Queries that DO read pgn (game detail, reclassify
scripts) pay one extra TOAST fetch — rare paths.

  *** MANUAL PROD OPS STEP REQUIRED (NOT in this migration) ***
The reloption alone only affects rows written AFTER it is set. To apply it to
EXISTING rows the table must be rewritten:

    VACUUM FULL games;   -- ~1.4 GB table, ACCESS EXCLUSIVE lock ~1-2 min
                         -- (or `pg_repack -t games` for a no-lock rewrite)

VACUUM cannot run inside a transaction block, so it CANNOT live in an Alembic
migration. Run it manually on prod against the live DB after this migration
deploys (acceptable downtime per the user decision 2026-06-10). On dev the table
is tiny, so the reloption suffices and no rewrite is needed.

Plain transactional DDL — no autocommit_block needed (SET reloption is fast and
takes only a brief lock).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9e3f1a4b5c6"
down_revision: str | None = "c8d2e0f3a4b5"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Set toast_tuple_target so future PGNs move out-of-line (existing rows: manual VACUUM FULL)."""
    op.execute("ALTER TABLE games SET (toast_tuple_target = 256)")


def downgrade() -> None:
    """Reset toast_tuple_target to the default (affects only newly written rows)."""
    op.execute("ALTER TABLE games RESET (toast_tuple_target)")
