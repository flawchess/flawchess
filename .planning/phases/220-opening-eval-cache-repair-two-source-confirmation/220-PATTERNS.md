# Phase 220: Opening Eval Cache Repair & Two-Source Confirmation - Pattern Map

**Mapped:** 2026-09-09
**Files analyzed:** 14 (5 new, 9 modified)
**Analogs found:** 13 / 14

All analog paths below were verified git-tracked (`git ls-files`, 2026-09-09). No
gitignored mirror paths are emitted.

RESEARCH.md already carries file:line ground truth for the *service/router* edit sites
(`_upsert_opening_cache`, `_apply_atomic_submit`, `_classify_and_fill_oracle`, the advisory
lock, the propagate SQL). This file does not repeat that; it assigns each **new or modified
file** its closest existing analog and the excerpts to copy, and points at RESEARCH.md for
the already-extracted in-place edit anatomy.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/opening_cache_repair.py` (new) | operator script / batch pipeline | batch + engine transform | `scripts/gen_red_herring_pool.py` (structure, injectable pool) + `scripts/benchmark_lane.py` (subcommands, report) | exact (split across two) |
| `alembic/versions/<new>_phase_220_opening_cache_audit.py` (new) | migration | DDL, create_table | `alembic/versions/20260727_214735_03df30e3c008_phase_192_herring_pool_and_drill_solve_link.py` | exact |
| `alembic/versions/<new>_phase_220_cache_provenance.py` (new, R2) | migration | DDL + data backfill | `alembic/versions/20260815_084711_0ac0176294fd_phase_210_games_initial_fen.py` | exact |
| `app/models/opening_cache_audit.py` (new, +3 tables) | model | CRUD | `app/models/herring_pool.py` (constraints/CHECK-heavy) + `app/models/opening_position_eval.py` (hash-keyed, no FK) | exact |
| `alembic/env.py` (modified) | config | — | its own existing `# noqa: F401` import block | exact |
| `app/models/__init__.py` (modified) | config | — | its own existing export list | exact |
| `app/services/eval_drain.py` (modified) | service | batch write | in-file: `_upsert_opening_cache`, `OPENING_CACHE_BACKFILL_SQL` (RESEARCH §Write-Path Anatomy) | in-place |
| `app/routers/eval_remote.py` (modified) | router | request-response | in-file: `_full_drain_tick`'s cache-write kwargs (`eval_drain.py:1115-1121`) | exact |
| `app/services/eval_apply.py` (modified) | service | CRUD | in-file rename of `_write_oracle_counts`; `_fetch_dedup_evals` one-line `.where` | in-place |
| `scripts/backfill_flaws.py` (modified) | operator script | batch | in-file `run_backfill` + `scripts/resweep_holed_games.py` `--db` shape | role-match |
| `tests/scripts/test_opening_cache_repair.py` (new) | test | — | `tests/scripts/test_gen_red_herring_pool.py` | exact |
| `tests/test_eval_worker_endpoints.py` (extended) | test | — | its own `_atomic_request` / `_insert_opening_cache` helpers (RESEARCH §Test Infrastructure) | exact |
| `tests/services/test_full_eval_drain.py` (extended) | test | — | its own 6 `OPENING_CACHE_BACKFILL_SQL` gate sites | exact |
| `.claude/skills/db-report/SKILL.md` (modified) | skill doc | — | its own `### Check A` / `### Check B` blocks | exact |
| `reports/opening-cache-repair/….md` (new output) | report artifact | file-I/O | `scripts/benchmark_lane.py::write_record_report` | exact |

## Pattern Assignments

---

### `scripts/opening_cache_repair.py` (operator script, batch + engine transform)

**Primary analog:** `scripts/gen_red_herring_pool.py` — the only script doing both DB and
engine work that is unit-tested without Stockfish.
**Secondary analog:** `scripts/benchmark_lane.py` — the only in-repo argparse-subcommand
script, and the report writer.

**Module docstring / `--db` header convention** (`scripts/resweep_holed_games.py:20-27`):

```python
"""...
The --db target is REQUIRED so this never silently runs against the wrong database.
dev=localhost:5432, benchmark=localhost:5433, prod=localhost:15432 (via bin/prod_db_tunnel.sh).

Usage:
    uv run python scripts/resweep_holed_games.py --db prod --dry-run   # count only
"""
```

**Path bootstrap + import block** (`scripts/resweep_holed_games.py:29-46`) — required
because a bare script must configure the SQLAlchemy mapper registry itself:

```python
import argparse
import asyncio
import sys
from pathlib import Path

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import db_url_for_target  # noqa: E402

# Import every ORM model so the SQLAlchemy registry fully configures. ...
import app.models.oauth_account  # noqa: E402, F401
import app.models.user  # noqa: E402, F401
```

**Subcommand wiring** — one `_add_<cmd>_subparser` per stage
(`scripts/benchmark_lane.py:802-826`, `925-938`):

```python
def _add_select_subparser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    select_parser = subparsers.add_parser(
        "select",
        help="Materialize benchmark_selection for one TC tranche.",
    )
    select_parser.add_argument(
        "--db",
        choices=["dev", "test", "prod", "benchmark"],
        default="benchmark",
        help="DB target (default: benchmark).",
    )
```

**Deviation to apply:** make `--db` **required with no default**, matching
`scripts/gen_red_herring_pool.py:254-259` (the rule; `benchmark_lane`'s default is the
exception):

```python
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target: dev (localhost:5432), benchmark (localhost:5433), prod (via SSH tunnel).",
    )
```

**Command dispatch + Sentry init** (`scripts/benchmark_lane.py`, tail):

```python
async def main() -> None:
    args = parse_args()
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    if args.command == "select":
        await _run_select(args)
    ...
    else:  # pragma: no cover — unreachable while argparse enforces a known command set
        raise ValueError(f"Unknown command: {args.command!r}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Stage-runner signature: injectable `session_maker` AND `EnginePool`** — copy this exactly;
it is what makes the tests Stockfish-free (`scripts/gen_red_herring_pool.py:791-831`):

```python
async def run_generation(
    *,
    db: str,
    n_positions: int,
    phase: PhaseName | None,
    dry_run: bool,
    reset: bool = False,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    pool: EnginePool | None = None,
) -> None:
    """...
    Args:
        session_maker: Injectable session factory for testing. When None, a
            real engine is created from db_url_for_target(db).
        pool: Injectable EnginePool for testing. When None, a real pool of
            HERRING_GENERATOR_WORKERS is started and stopped by this function.
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    if session_maker is None:
        url = db_url_for_target(db)
        engine = create_async_engine(url, pool_pre_ping=True)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

    owns_pool = pool is None
    if pool is None:
        pool = EnginePool(HERRING_GENERATOR_WORKERS)
        await pool.start()
    try:
        ...
    finally:
        if owns_pool:
            await pool.stop()
```

**Named-constant block** (`scripts/gen_red_herring_pool.py:192-240`) — the shape for
`MAX_CARRIERS_PER_HASH`, batch sizes, worker count. Every constant carries a comment stating
its basis; batch/commit constants are named, e.g.
`HERRING_COMMIT_EVERY: int = 50`, `HERRING_SCAN_PAGE_SIZE: int = 500`,
`HERRING_GENERATOR_WORKERS: int = 1`. Keyset-scan sentinels are also constants
(`_KEYSET_MAX_GAME_ID: int = (1 << 31) - 1  # INTEGER max`) — reuse that idea for the
`last_game_id_walked` cursor.

**Cooperative SIGTERM** — `scripts/import_stress_monitor.py:385-395` (the only precedent
outside the worker supervisor); excerpt already quoted in RESEARCH.md §Pattern 5. Copy
verbatim into the stage loop, checking `stop_requested` between commits.

**Engine gather with no session open** — `app/services/eval_drain.py:988-1006` (RESEARCH
§Pitfall 8). Load boards in a session → close → `asyncio.gather` engine calls → open the
write session.

**Report writer** — `scripts/benchmark_lane.py:696-798` + `:100-101`:

```python
# D-16: `record` mirrors the db-report/tactic-tagger-report timestamped-markdown
# convention -- reports/{topic}/{topic}-YYYY-MM-DD.md.
RECORD_REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "benchmark-lane"

async def write_record_report(db_url: str, tranche: TcTranche, now: datetime) -> Path:
    """... Takes ``now`` as a parameter (never calls datetime.now() internally)
    so a test can pin the filename. ..."""
    ...
    RECORD_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = now.strftime("%Y-%m-%d")
    report_path = RECORD_REPORTS_DIR / f"benchmark-lane-{tranche}-{date_str}.md"
    lines = [
        "| Metric | Value |",
        "|---|---|",
        f"| `game_flaws` rows | {game_flaws_rows:,} |",
        "",
        "## Provenance",
        ...
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
```

Copy: the `reports/{topic}/{topic}-YYYY-MM-DD.md` path, the injected `now`, the
`list[str]` + `"\n".join(...)` build, the closing `## Provenance` prose section. Target dir:
`reports/opening-cache-repair/`. Reports are committed (RESEARCH §Pitfall 10) — user **ids**
only, no PII.

---

### `alembic/versions/<new>_phase_220_opening_cache_audit.py` (migration, DDL)

**Analog:** `alembic/versions/20260727_214735_03df30e3c008_phase_192_herring_pool_and_drill_solve_link.py`
(down_revision must be the current head `e55d2651a373`).

**Header shape** (lines 1-18):

```python
"""phase 192 herring pool and drill solve link

Revision ID: 03df30e3c008
Revises: ed0735f3d998
Create Date: 2026-07-27 21:47:35.817268+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '03df30e3c008'
down_revision: Union[str, Sequence[str], None] = 'ed0735f3d998'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**`create_table` with CHECKs, composite FK, named constraints** (lines 24-43):

```python
    op.create_table('herring_pool',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('ply', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("mover_color IN ('white', 'black')", name='ck_herring_pool_mover_color'),
    sa.ForeignKeyConstraint(['game_id', 'user_id'], ['games.id', 'games.user_id'], name='herring_pool_game_user_fkey', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'game_id', 'ply', name='uq_herring_pool_source')
    )
    op.create_index('ix_herring_pool_recency', 'herring_pool', ['source_played_at', 'id'], unique=False)
```

`downgrade()` mirrors in reverse order (drop_index → drop_table). File naming:
`YYYYMMDD_HHMMSS_<rev12>_<snake_slug>.py`.

---

### `alembic/versions/<new>_phase_220_cache_provenance.py` (migration, DDL + backfill, Release 2)

**Analog:** `alembic/versions/20260815_084711_0ac0176294fd_phase_210_games_initial_fen.py`.

**Rich why-docstring + backfill SQL as a module constant so a test can execute the exact
statement** (lines 1-25, 60-80):

```python
"""phase 210 games initial fen
...
The backfill lives here rather than in a script (D-04): ... Alembic runs automatically on
backend container startup (`deploy/entrypoint.sh`), so there is no manual production step
and no window in which the column exists but is empty. ~176 affected rows in production.
...
`tests/test_normalization.py::test_migration_sql_matches_extract_initial_fen`
pins the two against each other on shared fixtures (D-06).
"""

# The backfill's extraction expression, exported so the D-06 agreement test can
# execute the exact SQL this migration ran rather than a paraphrase of it.
BACKFILL_SQL = f"""
    UPDATE games
    SET initial_fen = ...
"""


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable add — metadata-only in PostgreSQL, so no rewrite of a large table.
    op.add_column("games", sa.Column("initial_fen", sa.Text(), nullable=True))
    op.execute(sa.text(BACKFILL_SQL))
```

**Deviations this phase must make** (RESEARCH §Schema & Migrations):
- add all seven CACHEFIX-08 columns in **one** `op.execute("ALTER TABLE … ADD COLUMN …, ADD COLUMN …")`
  (each `op.add_column` is its own ACCESS EXCLUSIVE lock);
- the status-derived marking `UPDATE` over ~2.5M rows must be **batched** or moved to a
  `mark-confirmed` subcommand — there is **no batched-migration precedent in this repo**, so
  whichever is chosen is new code and needs its own justification comment.

---

### `app/models/opening_cache_audit.py` + siblings (model, CRUD)

**Analog A (constraint-heavy table):** `app/models/herring_pool.py:77-152`

```python
class HerringPool(Base):
    """One globally-shared, position-scoped red-herring candidate (POOL-03 amended)."""

    __tablename__ = "herring_pool"
    __table_args__ = (
        ForeignKeyConstraint(
            ["game_id", "user_id"],
            ["games.id", "games.user_id"],
            ondelete="SET NULL",
            name="herring_pool_game_user_fkey",
        ),
        UniqueConstraint("user_id", "game_id", "ply", name="uq_herring_pool_source"),
        CheckConstraint("phase IN (0, 1, 2)", name="ck_herring_pool_phase"),
        Index("ix_herring_pool_recency", "source_played_at", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

Use this for `status TEXT` + `CheckConstraint("status IN (...)")` on
`opening_cache_audit`, `(game_id, ply)` PK on `opening_cache_repair_rows`, and the
`ForeignKeyConstraint(..., ondelete=...)` on the repair-games table.

**Analog B (hash-keyed, deliberately FK-free):** `app/models/opening_position_eval.py:26-56` —
copy its per-column comment discipline and its "no FK, no cascade, no invalidation logic"
rationale for `source_game_id BIGINT NULL` (D-13):

```python
class OpeningPositionEval(Base):
    """Denormalized dedup cache of game_positions opening-region our-engine evals."""

    __tablename__ = "opening_position_eval"

    # Zobrist hash of the complete board position — explicit BIGINT for 64-bit values,
    # matching game_positions.full_hash (D-123.1-01).
    full_hash: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    eval_cp: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```

**Docstring pattern to imitate:** `herring_pool.py`'s "Assumption Delta" paragraph — this is
where the CLAUDE.md deviation must be recorded (`status` stays `TEXT`+CHECK on a 2.57M-row
table despite the cardinality rule; RESEARCH §Project Constraints) and where the
"post-hardening re-audit mode is NOT built" note goes (CONTEXT D-01).

**Also update `app/models/opening_position_eval.py`'s docstring:** its "Immutable" claim
(lines 1, 8-11) becomes false under CACHEFIX-08.

**Registration (two places, or autogenerate emits `drop_table`):**

`alembic/env.py:12-29`:
```python
from app.models.herring_pool import HerringPool  # noqa: F401
from app.models.push_subscription import PushSubscription  # noqa: F401
```

`app/models/__init__.py` — add the import **and** the `__all__` entry:
```python
from app.models.opening_position_eval import OpeningPositionEval

__all__ = [
    ...
    "OpeningPositionEval",
]
```

---

### `app/routers/eval_remote.py` (router, request-response) — CACHEFIX-12

**Analog:** the tick's own call site, `app/services/eval_drain.py:1115-1121`:

```python
            update_opening_cache=True,
            upsert_opening_cache_fn=_upsert_opening_cache,
            engine_targets_for_cache=engine_targets,
```

and the semantics of `engine_targets` (`app/services/eval_drain.py:990-994`) — "targets the
engine actually evaluated, dedup hits excluded". The submit path must reproduce that
semantic, snapshotting worker plies **before** `_merge_dedup_pv_into_engine_map` at
`eval_remote.py:1302` (RESEARCH §Pitfall 2 has the exact diff). Trusted-operator gating
(`require_operator_token`, `eval_remote.py:173`) is untouched.

---

### `scripts/backfill_flaws.py` (operator script, batch) — `--from-repair-table`

**Analog for the CLI surface:** its own existing argparse block
(`scripts/backfill_flaws.py:72-105`, `BACKFILL_GAMES_PER_BATCH = 100` at :62) and
`resweep_holed_games.py`'s required `--db`.

**Anti-pattern — do NOT reuse this file's own write path** (`scripts/backfill_flaws.py:~231-245`):

```python
                    # Delete-then-insert = idempotent recompute (threshold-change safe).
                    await delete_flaws_for_game(session, game_id=game_id_val, user_id=game_user_id)
                    rows = [ flaw_record_to_row(...) for flaw in flaw_list ]
                    await bulk_insert_game_flaws(session, rows)
```

It destroys `allowed_pv_lines` / `missed_pv_lines` and all 8 tactic-tag columns. The
rederive path must go through `_classify_and_fill_oracle` under the advisory lock — skeleton
in RESEARCH.md §Code Examples.

---

### `tests/scripts/test_opening_cache_repair.py` (test)

**Analog:** `tests/scripts/test_gen_red_herring_pool.py` (the only script test that stubs the
engine).

**Header + coverage-map docstring** (lines 1-37) — copy the "one bullet per test naming the
decision it pins" style:

```python
"""Tests for scripts/gen_red_herring_pool.py (Phase 192, Plan 03).

These are selection/persistence-logic tests — the engine is always stubbed
(a `_FakePool` recording every board it was asked to evaluate) ... so
every test is deterministic regardless of ambient game_positions data left
behind by other test files sharing the same isolated per-worker test
database.

Coverage:
- test_generator_rejects_fewer_than_five_legal_moves : D-18's legal-move-count
  reject runs BEFORE any engine call.
...
"""
```

**Imports + module handle + fake pool** (lines 39-56, 84-90):

```python
from __future__ import annotations

import chess
import chess.engine
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import scripts.gen_red_herring_pool as gen_module
from scripts.gen_red_herring_pool import run_generation

pytestmark = pytest.mark.asyncio


class _FakePool:
    """Stub EnginePool. Returns a scripted ladder keyed by board FEN and
    records every board it was asked to evaluate (fen strings)."""
```

The fake pool for this phase needs `evaluate(board)` (depth-15 screen) and
`evaluate_nodes_with_pv(board)` (1M-node confirm), injected via `pool=`. The
CancelledError-on-Nth-call resume test (RESEARCH §Testing SIGTERM design 1) hangs off the
same fake.

Also copy: per-test cleanup of every non-guest `Game` insert
(`tests/test_eval_worker_endpoints.py:5464-5466` shape, memory
`project_eval_lottery_test_isolation`).

---

### `.claude/skills/db-report/SKILL.md` §3 (skill doc) — CACHEFIX-09

**Analog:** the existing `### Check A` block, `.claude/skills/db-report/SKILL.md:193-292`.
Copy all seven structural parts in order:

1. intro bullet (line 196-198 shape):
```markdown
- **Check A — Flaw counts: `games` oracle columns vs `game_flaws`.** Are the per-color ... consistent with the derived `game_flaws` table?
```
2. `### Check A — <name>`
3. `#### Background (read before interpreting results)` with a
   `> **History note (do not re-derive this the hard way):** …` blockquote where relevant
4. `### Query N — <name>` with a ```sql fence (mark the lichess cross-check **heavy**, "run
   it last, alongside Query 11")
5. `#### Check X output format`
6. verdict line (line 290):
```markdown
Verdict line (Check A): **PASS** if `flaws_but_all_counts_null = 0` on every platform and aggregate totals agree within ~1%; **INVESTIGATE** otherwise.
```
7. reference blockquote (line 292):
```markdown
> Reference (prod snapshot 2026-07-31), all platforms, `flaws_but_all_counts_null = 0` everywhere:
```

Also change §3's intro line 195 "Run both unless the user asks for one." → "Run all four…".

---

## Shared Patterns

### Sentry in scripts
**Source:** `scripts/gen_red_herring_pool.py:818-819`, `scripts/backfill_flaws.py:130-131`, `:~203-215`
**Apply to:** `scripts/opening_cache_repair.py`, `scripts/backfill_flaws.py`
```python
if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
...
sentry_sdk.set_context("<name>", {"game_id": ..., "user_id": ...})
sentry_sdk.capture_exception(exc)
continue
```
Never embed variables in the message string. For D-12 use the fixed-message +
`set_tag("source", "opening-cache")` shape from `app/services/eval_drain.py:1021-1029`.

### `--db` target resolution
**Source:** `app/core/config.py:222` (`db_url_for_target`), used at
`scripts/resweep_holed_games.py:55`
**Apply to:** every new script entry point
```python
engine = create_async_engine(db_url_for_target(db), pool_pre_ping=True)
session_maker = async_sessionmaker(engine, expire_on_commit=False)
try:
    print(f"Target: {engine.url.host}:{engine.url.port}/{engine.url.database} ({db})")
    ...
finally:
    await engine.dispose()
```
Never `os.environ[...]`; never bind to the app's module-global `async_session_maker` (it
points at dev locally, so `--db prod` would silently hit dev — the comment at
`resweep_holed_games.py:50-53` records exactly that trap).

### asyncpg-safe casts in `text()` writes
**Source:** `app/services/eval_apply.py:517-527`, rule stated at `app/services/eval_drain.py:464-465`
**Apply to:** the propagate `UPDATE`, every batched audit-row write
```python
f"(CAST(:ply_{i} AS smallint), CAST(:ecp_{i} AS smallint), CAST(:emt_{i} AS smallint))"
```
`CAST(x AS t)`, never `x::t` — required for `IS NOT DISTINCT FROM :old_mate` with a NULL bind
(RESEARCH §Pitfall 1).

### Per-game advisory lock
**Source:** `app/services/eval_apply.py:2876-2881`, key at `:121-148`
**Apply to:** rederive's per-game transaction (first statement) and the blob-submit write
session (D-04 choice: advisory lock **+ in-lock re-read** of surviving flaw plies)
```python
await session.execute(
    sa.text("SELECT pg_advisory_xact_lock(:lock_key)"),
    {"lock_key": _game_write_lock_key(game_id)},
)
```
Lock-test technique: `tests/services/test_eval_apply.py:1113-1190`.

### Named constants with a stated basis
**Source:** `scripts/gen_red_herring_pool.py:192-240`
**Apply to:** `MAX_CARRIERS_PER_HASH = 3`, `OPENING_CACHE_AGREE_MAX_SCORE_DELTA`, batch sizes
(500/commit per the ROADMAP cross-cutting constraint), keyset sentinels. Every constant gets a
comment naming the decision or measurement it came from — `OPENING_CACHE_AGREE_MAX_SCORE_DELTA`
must cite the calibration date and measured `confirm_floor` (D-11).

### Timestamped markdown report
**Source:** `scripts/benchmark_lane.py:100-101`, `:696-798`
**Apply to:** the `report` and `legacy-sample` subcommands.
`reports/{topic}/{topic}-YYYY-MM-DD.md`, `now` injected as a parameter, `mkdir(parents=True,
exist_ok=True)`, `"\n".join(lines)` + `write_text(..., encoding="utf-8")`, returns `Path`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| the batched status-derived `UPDATE` inside the Release-2 migration | migration | batch | **No batched-migration precedent exists in this repo** (RESEARCH: grep for `LIMIT`/loop in `alembic/versions/` found none). Either write it new with a justification comment, or move it to a `mark-confirmed` subcommand of `opening_cache_repair.py` (which then follows the script batch/commit pattern above). Planner must pick and record. |

Partial-analog note: the real-SIGTERM subprocess resume test has no in-repo precedent either
(`grep SIGTERM tests/` → only unrelated hits). RESEARCH prescribes in-process
`CancelledError` injection for CI (patterned on the `_FakePool` above) and the literal
SIGTERM as a documented dev-smoke operator step, not a pytest test.

## Metadata

**Analog search scope:** `scripts/`, `app/models/`, `app/services/`, `app/routers/`,
`alembic/versions/`, `tests/scripts/`, `tests/`, `.claude/skills/db-report/`, `reports/`
**Files read this pass:** 12 (plus RESEARCH.md's already-extracted service/router excerpts)
**Tracked-source verification:** `git ls-files` on all 11 named analog paths, 2026-09-09
**Pattern extraction date:** 2026-09-09
