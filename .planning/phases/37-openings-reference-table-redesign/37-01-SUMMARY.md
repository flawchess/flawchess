---
phase: 37-openings-reference-table-redesign
plan: 01
subsystem: database
tags: [postgresql, sqlalchemy, alembic, python-chess, seed-script]

# Dependency graph
requires:
  - phase: 27-import-wiring-backfill
    provides: scripts/__init__.py making scripts/ a Python package
provides:
  - openings SQLAlchemy model (app/models/opening.py)
  - Alembic migration creating openings table and openings_dedup view
  - Idempotent seed script populating 3641 rows from app/data/openings.tsv
  - Test suite validating seed data and dedup view
affects:
  - 37-02 (WDL aggregation queries will JOIN against openings_dedup)
  - 37-03 (frontend openings table will fetch data via the new openings reference)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Idempotent seed via INSERT ... ON CONFLICT ON CONSTRAINT ... DO NOTHING"
    - "openings_dedup view uses DISTINCT ON (eco, name) ORDER BY eco, name, id for stable dedup"
    - "board.board_fen() (not board.fen()) for piece-placement-only FEN per project convention"
    - "asyncio.run() in sync pytest fixture to seed test DB after alembic upgrade head"

key-files:
  created:
    - app/models/opening.py
    - alembic/versions/20260328_194057_1b941ecba0a6_create_openings_table.py
    - scripts/seed_openings.py
    - tests/test_seed_openings.py
  modified:
    - alembic/env.py

key-decisions:
  - "openings_dedup view uses DISTINCT ON (eco, name) ORDER BY eco, name, id — stable deterministic dedup picking lowest id per pair"
  - "Seed fixture uses asyncio.run() in sync session-scoped pytest fixture to avoid event loop conflicts with pytest-asyncio"
  - "REAL/Float(precision=24) autogenerate noise excluded from migration — semantically equivalent in PostgreSQL, pre-existing issue out of scope"

patterns-established:
  - "Seed scripts: asyncio.run() entry point, INSERT ON CONFLICT DO NOTHING, TSV via csv.DictReader"
  - "Test seeding: session-scoped sync fixture depends on test_engine, calls asyncio.run(seed_fn()) after migrations"

requirements-completed: [ORT-01, ORT-02]

# Metrics
duration: 4min
completed: 2026-03-28
---

# Phase 37 Plan 01: Openings Reference Table Summary

**PostgreSQL openings table with 3641 rows seeded from TSV, openings_dedup view with 3301 unique (eco, name) pairs, idempotent seed script using python-chess for FEN/ply computation**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-28T19:40:39Z
- **Completed:** 2026-03-28T19:43:46Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created Opening SQLAlchemy model with SmallInteger ply_count, UniqueConstraint on (eco, name, pgn), and index on (eco, name)
- Created Alembic migration applying openings table + openings_dedup view (DISTINCT ON eco, name) in a single transaction
- Created idempotent seed script using python-chess board.board_fen() for FEN computation; seeded 3641 rows with 0 errors
- All 9 tests pass: 4 unit tests for pgn_to_fen_and_ply, 5 integration tests for table/view correctness

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Opening model, migration with dedup view, and seed script** - `dbfe475` (feat)
2. **Task 2: Write tests for seed script and dedup view** - `cd849a0` (test)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `app/models/opening.py` - Opening SQLAlchemy model (eco, name, pgn, ply_count, fen)
- `alembic/versions/20260328_194057_1b941ecba0a6_create_openings_table.py` - Migration: openings table + openings_dedup view
- `scripts/seed_openings.py` - Idempotent seed script reading app/data/openings.tsv
- `tests/test_seed_openings.py` - Test suite for seed script and dedup view
- `alembic/env.py` - Added Opening import for autogenerate support

## Decisions Made

- openings_dedup view uses `DISTINCT ON (eco, name) ORDER BY eco, name, id` for stable deterministic dedup (lowest id per eco+name pair)
- Test seeding uses `asyncio.run()` in a sync session-scoped pytest fixture (depends on `test_engine`) to avoid event loop conflicts with pytest-asyncio
- Excluded REAL/Float(precision=24) autogenerate noise from migration — semantically equivalent in PostgreSQL, pre-existing issue out of scope

## Deviations from Plan

**1. [Rule 1 - Bug] Fixed asyncio.get_event_loop() in test fixture**
- **Found during:** Task 2 (test execution)
- **Issue:** `asyncio.get_event_loop().run_until_complete()` raises RuntimeError in pytest-asyncio session-scoped sync fixture — no current event loop in thread
- **Fix:** Replaced with `asyncio.run(seed_openings())` which creates its own event loop
- **Files modified:** tests/test_seed_openings.py
- **Verification:** All 9 tests pass
- **Committed in:** cd849a0 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary fix for test infrastructure. No scope creep.

## Issues Encountered

- Alembic autogenerate included pre-existing REAL/Float(precision=24) alter_column noise for game_positions.clock_seconds and games.white_accuracy/black_accuracy — these are semantically equivalent in PostgreSQL and were excluded from the migration per project convention (seen in previous phases).

## Known Stubs

None — all data is real (seeded from openings.tsv with computed FEN/ply values).

## User Setup Required

None - no external service configuration required. The seed script must be run against production when deploying this migration: `uv run python -m scripts.seed_openings`

## Next Phase Readiness

- openings table (3641 rows) and openings_dedup view (3301 rows) ready for Plan 02 WDL aggregation queries
- Opening model importable from app.models.opening for JOIN queries
- Seed script is idempotent; safe to re-run after production deployment

---
*Phase: 37-openings-reference-table-redesign*
*Completed: 2026-03-28*
