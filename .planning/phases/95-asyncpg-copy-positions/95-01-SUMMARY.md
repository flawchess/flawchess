---
phase: 95-asyncpg-copy-positions
plan: "01"
subsystem: backend/repositories
tags:
  - asyncpg
  - bulk-insert
  - copy-protocol
  - import-pipeline
  - memory-optimization
dependency_graph:
  requires: []
  provides:
    - bulk_insert_positions now uses asyncpg binary COPY protocol
    - _POSITION_COPY_COLUMNS module-level constant for column coverage CI enforcement
  affects:
    - app/services/import_service.py (caller unchanged)
    - tests/test_reclassify.py (still passes — no caller change needed)
    - tests/test_import_service.py (still passes — mocks unchanged)
tech_stack:
  added: []
  patterns:
    - asyncpg Connection.copy_records_to_table for bulk position writes
    - SQLAlchemy async session.connection().get_raw_connection() for raw driver access
key_files:
  created:
    - tests/test_game_repository_bulk_insert_positions.py
  modified:
    - app/repositories/game_repository.py
decisions:
  - "D-1: Acquire asyncpg Connection via (await (await session.connection()).get_raw_connection()).driver_connection — stays in session transaction"
  - "D-2: Explicit _POSITION_COPY_COLUMNS tuple (not runtime introspection) — enforced by CI test"
  - "D-3: dict.get(col) for each column — missing optional keys become None"
  - "D-5: Empty position_rows short-circuits before connection acquisition"
  - "get_raw_connection() requires await in SQLAlchemy 2.x asyncpg adapter (deviation from context skeleton which showed single-await chain)"
metrics:
  duration_minutes: 25
  completed_date: "2026-05-27"
  tasks_completed: 3
  files_modified: 2
---

# Phase 95 Plan 01: asyncpg COPY for bulk_insert_positions — Summary

Switch `bulk_insert_positions` from `insert(GamePosition).values(chunk)` to asyncpg's binary `Connection.copy_records_to_table`, with six integration tests proving column coverage, round-trip fidelity, NULL handling, empty-batch no-op, rollback atomicity, and chunking correctness.

## What Was Built

### app/repositories/game_repository.py

`bulk_insert_positions` body replaced with asyncpg COPY path:

1. Module-level `_POSITION_COPY_COLUMNS: tuple[str, ...] = (...)` with 19 entries matching all non-id columns of `GamePosition`. The test enforces set-equality against `GamePosition.__table__.columns` so any future column drift becomes a CI failure rather than silent data corruption.

2. `if not position_rows: return` short-circuits before any DB connection is acquired (test 4 asserts `session.connection` is not called on empty input).

3. Connection acquisition: `sa_conn = await session.connection(); raw_wrapper = await sa_conn.get_raw_connection(); raw_conn = raw_wrapper.driver_connection`. Both `session.connection()` and `get_raw_connection()` are async in SQLAlchemy 2.x with the asyncpg adapter — the context skeleton in `95-CONTEXT.md` showed a single-await chain that would have produced an `AttributeError`.

4. Chunk loop unchanged at 1700 rows. Inside: `records = [tuple(row.get(col) for col in _POSITION_COPY_COLUMNS) for row in chunk]` then `await raw_conn.copy_records_to_table("game_positions", records=records, columns=_POSITION_COPY_COLUMNS)`.

5. Trailing `await session.flush()` retained for session-state consistency.

6. Unused `insert` import removed (only `pg_insert` from `sqlalchemy.dialects.postgresql` is now needed for `bulk_insert_games`).

### tests/test_game_repository_bulk_insert_positions.py

Six async integration tests against the test Postgres DB (`flawchess_test`) via the `db_session` fixture (which auto-rolls-back each test):

| Test | What it asserts |
|------|-----------------|
| `test_bulk_insert_positions_column_coverage` | `_POSITION_COPY_COLUMNS` set-equals `GamePosition.__table__.columns` minus `id` |
| `test_bulk_insert_positions_round_trip` | 3 fully-populated rows round-trip byte-for-byte (REAL float tolerance for `clock_seconds`) |
| `test_bulk_insert_positions_null_optional_fields` | 2 required-only rows have all optional columns read back as `None` |
| `test_bulk_insert_positions_empty_batch_noop` | `session.connection` is not called when input is empty |
| `test_bulk_insert_positions_rollback_atomicity` | COPY enrolled in session transaction — rollback after duplicate-PK violation removes both games and positions |
| `test_bulk_insert_positions_chunking_across_chunk_size` | 1701 rows (chunk_size+1) all land in the table |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Double-await required for get_raw_connection()**

- **Found during:** Task 2 (GREEN phase), first test run
- **Issue:** The context skeleton in `95-CONTEXT.md` and the PLAN showed `(await session.connection()).get_raw_connection().driver_connection` — a single-await chain. In practice, `get_raw_connection()` is also an async method in SQLAlchemy 2.x's asyncpg adapter, so calling it without `await` returns a coroutine object, and `.driver_connection` on a coroutine raises `AttributeError: 'coroutine' object has no attribute 'driver_connection'`.
- **Fix:** Split into three lines: `sa_conn = await session.connection()`, `raw_wrapper = await sa_conn.get_raw_connection()`, `raw_conn = raw_wrapper.driver_connection`.
- **Files modified:** `app/repositories/game_repository.py`
- **Commit:** included in `feat(95-01)` commit (3f7500a1)

**2. [Rule 1 - Bug] Test helper used invalid gameresult enum value**

- **Found during:** Task 2, second test run
- **Issue:** `_make_game_row` used `result="*"` which is not in the Postgres `gameresult` enum (`"1-0"`, `"0-1"`, `"1/2-1/2"`). This caused `asyncpg.exceptions.InvalidTextRepresentationError` when calling `bulk_insert_games`.
- **Fix:** Changed to `result="1/2-1/2"`.
- **Files modified:** `tests/test_game_repository_bulk_insert_positions.py`
- **Commit:** included in `feat(95-01)` commit

**3. [Rule 1 - Bug] Signed int64 overflow in chunking test hash values**

- **Found during:** Task 2, third test run
- **Issue:** Hash values `ply | 0xFF00000000000000` exceed the signed int64 range (Python integers are arbitrary precision, but Postgres BIGINT is signed int64). asyncpg raised `OverflowError: value out of int64 range` when encoding the hash column.
- **Fix:** Changed to `0x7F00000000000000 | ply` (and similar 0x5A/0x3B prefixes for white/black hashes) which stay within signed int64 range.
- **Files modified:** `tests/test_game_repository_bulk_insert_positions.py`
- **Commit:** included in `feat(95-01)` commit

**4. [Rule 2 - Missing critical functionality] Type narrowing for driver_connection**

- **Found during:** Task 2 ty check
- **Issue:** `ty` flagged `raw_wrapper.driver_connection` as `Any | None`, which propagated to a `copy_records_to_table` call on a potentially-None value — an `unresolved-attribute` error.
- **Fix:** Added `assert raw_conn is not None, "asyncpg driver_connection must not be None"` after the assignment, which narrows the type and provides a clear runtime error if the dialect changes.
- **Files modified:** `app/repositories/game_repository.py`
- **Commit:** included in `feat(95-01)` commit

## Known Stubs

None.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes. This is an internal implementation swap on an existing write path.

## Self-Check: PASSED

- [x] `tests/test_game_repository_bulk_insert_positions.py` exists
- [x] `app/repositories/game_repository.py` contains `_POSITION_COPY_COLUMNS`
- [x] `grep -n "copy_records_to_table" app/repositories/game_repository.py` — 1 match
- [x] `grep -n "insert(GamePosition)" app/repositories/game_repository.py` — 0 matches
- [x] All 6 new tests pass
- [x] Full test suite: 2193 passed, 16 skipped, 3 warnings
- [x] `uv run ruff check app/ tests/` — clean
- [x] `uv run ruff format --check app/ tests/` — clean
- [x] `uv run ty check app/ tests/` — zero errors
- [x] Commits: cb403018 (RED tests), 3f7500a1 (GREEN implementation)
