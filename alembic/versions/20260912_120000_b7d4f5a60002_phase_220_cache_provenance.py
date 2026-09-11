"""phase 220 cache provenance

Revision ID: b7d4f5a60002
Revises: a1c2e3f40001
Create Date: 2026-09-12 12:00:00+00:00

Phase 220 Release 2 (CACHEFIX-08, D-11/D-12/D-13). Adds two-source-confirmation
provenance to `opening_position_eval` (2.57M rows): `confirmed`, `n_sources`,
`disagreements`, `engine_version`, `written_at`, `confirmed_at`,
`source_game_id`. Replaces first-write-wins (Release 1, CACHEFIX-01..07,
`a1c2e3f40001`) with a candidate/promote write path — a position becomes
trusted only after two independent games agree on it.

Why the marking is derived from `opening_cache_audit.status`, not set by the
repair script (D-01): the repair (Release 1) runs BEFORE hardening (Release
2) ships, precisely so the write path stays clean while the cache is being
cleaned. The repair script therefore has no knowledge of `confirmed` /
`n_sources` — those columns do not exist yet when it runs. This migration is
the only place that ever reads `opening_cache_audit.status` to derive them,
exactly once, at the moment the columns are added. `screened_clean` /
`confirmed_clean` / `repaired` are the three statuses the release-1 pipeline
independently re-evaluated and found (or made) correct; every other status —
`pending`, `flagged`, `confirmed_bad` without a repair, `hash_mismatch`,
`orphan`, and any row `opening_cache_audit` gains AFTER this migration runs —
stays a candidate (`confirmed=false, n_sources=1`), same as a brand-new
position nobody has evaluated twice yet.

Why the marking is batched (this plan's "Decisions recorded by this plan"):
Alembic runs on backend container startup (`deploy/entrypoint.sh`), so there
is no manual production step and no window in which the columns exist but
every row is a candidate (which would turn off opening dedup for the whole
fleet until an operator ran a follow-up). The alternative — an operator
`mark-confirmed` subcommand — was rejected for exactly that reason (see the
plan's checkpoint:decision options). There is no batched-migration precedent
in this repo (RESEARCH.md grepped `alembic/versions/` for a LIMIT/loop and
found none); this is new code, justified inline below.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7d4f5a60002"
down_revision: Union[str, Sequence[str], None] = "a1c2e3f40001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Exported as a module constant (the initial_fen migration's precedent, D-06
# there) so tests/models/test_opening_cache_audit_models.py::test_migration_marking
# can execute the EXACT statement this migration runs rather than a paraphrase
# of it. `:cursor` is nullable (NULL on the first keyset-walk pass) and both
# binds are explicitly CAST -- asyncpg rejects `::`-style casts through
# SQLAlchemy text() (CLAUDE.md / app/services/eval_drain.py precedent), and a
# bare NULL bind for `:cursor` with no cast would fail type inference against
# `oca.full_hash > :cursor`.
MARK_CONFIRMED_SQL = """
    UPDATE opening_position_eval
    SET confirmed = true,
        n_sources = 2,
        confirmed_at = now()
    WHERE full_hash IN (
        SELECT oca.full_hash
        FROM opening_cache_audit oca
        WHERE oca.status IN ('screened_clean', 'confirmed_clean', 'repaired')
          AND (
              CAST(:cursor AS bigint) IS NULL
              OR oca.full_hash > CAST(:cursor AS bigint)
          )
        ORDER BY oca.full_hash
        LIMIT CAST(:batch_size AS integer)
    )
    RETURNING opening_position_eval.full_hash
"""

# Keyset-walk batch size for the status-derived marking UPDATE over ~2.5M
# candidate rows. Each 50,000-row statement takes only a ROW EXCLUSIVE lock
# and commits before the next one starts (Alembic's per-migration transaction
# boundary aside -- see the loop comment in upgrade() for why this still
# bounds lock duration), where one single multi-minute UPDATE over the whole
# audit table would hold row locks for the entire run and stall the deploy.
# 50,000 mirrors the repair script's own operator-scale batch convention
# (scripts/opening_cache_repair.py).
MARK_CONFIRMED_BATCH_SIZE = 50_000


def upgrade() -> None:
    """Upgrade schema."""
    # One statement, seven columns -- a single ACCESS EXCLUSIVE lock rather
    # than seven separate ones. Alembic's per-column add helper would emit its
    # own ALTER TABLE per column and therefore acquire its own lock
    # sequentially; a single multi-column ALTER TABLE acquires the lock once.
    # All seven defaults are constant (false / 1 / 0 / NULL), so PostgreSQL
    # applies them lazily via the column's pg_attribute metadata (fast
    # default, PG 11+) and no table rewrite happens on this 2.57M-row table --
    # this ALTER TABLE is metadata-only (RESEARCH.md Schema & Migrations, the
    # PostgreSQL 18 constant-DEFAULT citation).
    op.execute(
        sa.text(
            "ALTER TABLE opening_position_eval "
            "ADD COLUMN confirmed BOOLEAN NOT NULL DEFAULT false, "
            "ADD COLUMN n_sources SMALLINT NOT NULL DEFAULT 1, "
            "ADD COLUMN disagreements SMALLINT NOT NULL DEFAULT 0, "
            "ADD COLUMN engine_version TEXT, "
            "ADD COLUMN written_at TIMESTAMPTZ, "
            "ADD COLUMN confirmed_at TIMESTAMPTZ, "
            "ADD COLUMN source_game_id BIGINT"
        )
    )

    # Batched status-derived marking (D-01 / this plan's recorded decision):
    # a keyset walk over opening_cache_audit.full_hash, MARK_CONFIRMED_SQL run
    # repeatedly rather than as one statement. Each pass marks up to
    # MARK_CONFIRMED_BATCH_SIZE qualifying rows above the cursor, advances the
    # cursor to the largest full_hash just marked, and the walk stops the
    # first time a pass marks nothing. There is no batched-migration
    # precedent in this repo (module docstring); the loop is new code and
    # carries this justification: Alembic executes upgrade() inside one
    # implicit migration transaction (env.py's `context.begin_transaction()`),
    # so even a "batched" UPDATE here does not release its row locks between
    # statements the way a script's own commit-per-batch loop would. The
    # batching's actual benefit is bounding PostgreSQL's per-statement lock
    # acquisition and WAL-flush work to 50k rows at a time (rather than one
    # ~2.5M-row UPDATE plan and a single giant WAL record), and giving the
    # executor a measurable, resumable-in-spirit unit for the dev wall-clock
    # measurement this plan records before the production release.
    bind = op.get_bind()
    cursor: int | None = None
    while True:
        result = bind.execute(
            sa.text(MARK_CONFIRMED_SQL),
            {"cursor": cursor, "batch_size": MARK_CONFIRMED_BATCH_SIZE},
        )
        marked_hashes = [row[0] for row in result.fetchall()]
        if not marked_hashes:
            break
        cursor = max(marked_hashes)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            "ALTER TABLE opening_position_eval "
            "DROP COLUMN confirmed, "
            "DROP COLUMN n_sources, "
            "DROP COLUMN disagreements, "
            "DROP COLUMN engine_version, "
            "DROP COLUMN written_at, "
            "DROP COLUMN confirmed_at, "
            "DROP COLUMN source_game_id"
        )
    )
