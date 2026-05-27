---
phase: 95-asyncpg-copy-positions
created: 2026-05-27T00:00:00Z
reviewed: 2026-05-27T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - app/repositories/game_repository.py
  - tests/test_game_repository_bulk_insert_positions.py
  - scripts/stress_test_dual_platform_import.py
findings:
  critical: 0
  warning: 5
  info: 7
  total: 12
status: issues_found
---

# Phase 95: Code Review Report

**Reviewed:** 2026-05-27
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

The asyncpg COPY conversion in `bulk_insert_positions` is correctly implemented: the column tuple matches the model, the connection acquisition chain enrolls the COPY in the active SQLAlchemy transaction (validated by a rollback-atomicity test), and NULL handling via `dict.get(col)` is sound. `bulk_insert_games` is byte-identical to its pre-phase form.

No Critical issues found. Five Warnings, mostly in the stress driver (`scripts/stress_test_dual_platform_import.py`): the metric sampler runs `docker stats` twice per sampling tick (doubling the per-sample subprocess cost), several dead parameters get plumbed through helpers, broad `except Exception` blocks silently swallow sampler errors without any logging, and the rollback-atomicity test leaks a committed test user across the session-scoped engine. The stress driver is a one-off measurement tool, so the bar is "produces correct numbers without hanging" rather than production-grade, but the dead parameters and silent error swallowing make debugging harder if something goes wrong mid-run.

## Warnings

### WR-01: Docker stats subprocess invoked twice per sample tick

**File:** `scripts/stress_test_dual_platform_import.py:189-202`
**Issue:** `_sample_metrics` calls `_sample_docker(...)` (which spawns `docker stats --no-stream`) and then immediately calls `_get_docker_mem_bytes(...)` (which spawns `docker stats --no-stream` again) just to capture the peak. Each `docker stats --no-stream` invocation takes roughly 1-2 seconds, so every 5-second sample window now spends 2-4 s waiting on Docker — half of every sampling tick. The peak memory captured by the second invocation can disagree with the value written to the CSV by the first invocation (the two reads are seconds apart under live memory pressure), so the CSV trace and the `peak_mem_usage_bytes` field in the summary JSON are *not* sourced from the same observation. This complicates report interpretation: the table value and the per-row trace can legitimately diverge by hundreds of MB during an OOM spike.
**Fix:** Have `_sample_docker` return the parsed `mem_bytes` and use that single value both for the CSV write and the peak tracker. Remove `_get_docker_mem_bytes` entirely (or keep it as a thin helper that `_sample_docker` calls internally).
```python
# scripts/stress_test_dual_platform_import.py — sketch
async def _sample_docker(...) -> int:
    # ... existing parse logic ...
    writer.writerow({...})
    return mem_bytes  # return the observation

# in _sample_metrics:
mem_bytes = await _sample_docker(ts=ts, db_container=db_container, writer=docker_writer)
if mem_bytes > peak_mem_bytes:
    peak_mem_bytes = mem_bytes
# delete the second `await _get_docker_mem_bytes(...)` call
```

### WR-02: Dead parameters threaded through sampler helpers

**File:** `scripts/stress_test_dual_platform_import.py:251-291` and `294-330`
**Issue:** `_sample_docker(...)` accepts `fh` and `peak_mem_bytes` parameters that are never read inside the function body. `_sample_pg_activity(...)` accepts an `fh` parameter that is never read. The `peak_mem_bytes` arg is particularly misleading because it suggests the helper *updates* the peak — but the helper only writes a row; the actual peak update happens in the caller via the redundant `_get_docker_mem_bytes` call (WR-01). A future reader will spend time tracing why the peak tracker doesn't appear to be mutated through the helper signature it pretends to use.
**Fix:** Remove the unused parameters. The `fh.flush()` calls already happen in `_sample_metrics` after both helpers return, so the file handles do not need to be passed in. Drop `peak_mem_bytes` from `_sample_docker`'s signature in tandem with WR-01.

### WR-03: Bare `except Exception` in sampler helpers swallows all errors with no logging

**File:** `scripts/stress_test_dual_platform_import.py:247-248`, `290-291`, `328-329`
**Issue:** `_get_docker_mem_bytes`, `_sample_docker`, and `_sample_pg_activity` each wrap their full body in `try/except Exception: pass` (or `return 0`). If the `docker` binary is missing, the container name is wrong, asyncpg disconnects mid-run, or the pg query times out, the sampler silently keeps writing empty CSVs — the user only finds out at the end when the summary JSON shows `peak_mem_usage_bytes: 0` with no explanation. CLAUDE.md is explicit that scripts (not services) need not call `sentry_sdk.capture_exception`, but they still need *some* operator-visible signal. Right now there is no `print`, no `logging`, and the script doesn't even keep a counter of how many sample ticks failed.
**Fix:** Add a one-line `print(f"[sampler] {kind} sample failed: {exc!r}", file=sys.stderr)` inside each except, and consider tracking a `sample_failures` counter in the summary JSON so a run that produced suspect data is flagged in the verdict report. Bonus: distinguish `FileNotFoundError` (missing `docker` binary, fatal) from transient errors (worth retrying) by re-raising the former.

### WR-04: Rollback-atomicity test leaks committed user across the session-scoped engine

**File:** `tests/test_game_repository_bulk_insert_positions.py:199-256`
**Issue:** `test_bulk_insert_positions_rollback_atomicity` opens its own `async_sessionmaker(test_engine, ...)` to bypass the `db_session` rollback wrapper (correct, per D-7), and explicitly commits the test user via `await setup_session.commit()` before the inner rollback experiment. Because `test_engine` is **session-scoped** (see `tests/conftest.py:78`), this committed user (id=2003) persists for the rest of the pytest session. A future test that picks the same id, or any test that does a `SELECT COUNT(*) FROM users`, will see this leak. The `_truncate_all_tables` step in `conftest.py:101` only runs **once** at the start of the session, before any test executes — it does not run between tests.
The test as written passes today by luck (no other test happens to use id=2003 or assert on a clean users table), but the leak is real. The same risk applies to id=2001/2002/2004 from the other tests, except those use the rollback-wrapped `db_session` so they auto-clean.
**Fix:** Either (a) wrap the user creation in a `try/finally` that explicitly `DELETE FROM users WHERE id = 2003` in a fresh session at test teardown, or (b) use a random user_id per run (e.g. derived from `uuid.uuid4().int % 2**31`) so id collisions become statistically impossible, or (c) add a `@pytest.fixture(autouse=True)` to this test file that cleans up the test users on teardown. Option (a) is the cleanest.

### WR-05: Test file docstring claims "live dev Postgres", but tests run against `flawchess_test`

**File:** `tests/test_game_repository_bulk_insert_positions.py:1-6`
**Issue:** The module docstring says "Uses the live test Postgres DB via the db_session fixture (no DB mocks)" — but earlier in the same docstring the wording is "live test Postgres DB". The phase summary's text says "6 integration tests against dev Postgres" (95-01-SUMMARY.md). The actual fixture (`tests/conftest.py:78-108`) creates an engine bound to `settings.TEST_DATABASE_URL` (`flawchess_test`), not the dev DB. The confusion matters because a developer reading the failing test output may try to debug against the dev DB schema and miss that schema drift could exist between the two databases (alembic_version aside, both are migrated by `alembic upgrade head` against the same migrations, so they should match — but the assertion is implicit, not enforced).
**Fix:** Update the docstring to "Uses the test Postgres DB (`flawchess_test`) via the `db_session` fixture, which auto-rolls-back each test." Fix the same phrasing in `95-01-SUMMARY.md` if accuracy matters there.

## Info

### IN-01: `chunk_size = 1700` is a magic number with a multi-line rationale

**File:** `app/repositories/game_repository.py:223`
**Issue:** The constant is defined as a local variable inside `bulk_insert_positions` with the rationale captured only in the function-level docstring. The number is also referenced by tests as `_CHUNK_SIZE = 1700` (a separate copy in `tests/test_game_repository_bulk_insert_positions.py:24`). If a future tuning change updates one but not the other, the chunking-boundary test silently stops exercising the boundary.
**Fix:** Promote `chunk_size` to a module-level constant `_POSITION_CHUNK_SIZE: int = 1700` and import it from the test file. This is a small lift and removes the duplication.

### IN-02: `_POSITION_COPY_COLUMNS` referenced with `# noqa: SLF001` in tests

**File:** `tests/test_game_repository_bulk_insert_positions.py:102, 136`
**Issue:** The test imports a single-underscore-prefixed name (`_POSITION_COPY_COLUMNS`) and silences `SLF001` (private member access) twice. The leading underscore signals "module-private", but the test's whole purpose is to assert a CI contract on this constant — so either it's a public CI artifact (drop the underscore) or it's private (then expose a public helper like `get_position_copy_columns()` for the test to call). Either pattern is cleaner than `# noqa: SLF001` repeated at every access site.
**Fix:** Rename to `POSITION_COPY_COLUMNS` (public) — this signals "this is the contract enforced by CI" and removes the `noqa` clutter. Existing callers in this file are the only consumers.

### IN-03: `assert raw_conn is not None` runs in production with assertions disabled under `python -O`

**File:** `app/repositories/game_repository.py:221`
**Issue:** The `assert` is added (per the summary) to satisfy `ty` type narrowing on a `Connection | None` slot. Under `python -O` or `PYTHONOPTIMIZE=1`, asserts are stripped — the code would silently call `.copy_records_to_table` on `None` and raise `AttributeError: 'NoneType' object has no attribute 'copy_records_to_table'` at runtime. The current project doesn't use `-O` (verified via the docker entrypoint and CLAUDE.md commands), so this is informational rather than a bug — but the pattern of "assert for type narrowing" is fragile.
**Fix:** Replace with an explicit check that always runs:
```python
if raw_conn is None:
    raise RuntimeError("asyncpg driver_connection is None — SQLAlchemy adapter changed")
```
This survives `-O` and gives a more specific runtime error if the dialect ever changes (which the comment already anticipates).

### IN-04: Sampler keyword-only param `output_tag` has no default and follows params that do

**File:** `scripts/stress_test_dual_platform_import.py:338-347`
**Issue:** `run_stress_test(*, user_id, chesscom_username, lichess_username, sample_interval_s=5.0, db_container_name="...", output_dir=Path(...), output_tag)` has `output_tag` (no default) **after** several keyword-only args that *do* have defaults. This is legal Python (all are keyword-only after `*`), but the ordering misleads readers: by convention, required-without-default args come first within a keyword-only block. A reader scanning the signature could miss that `output_tag` is required.
**Fix:** Move `output_tag` to immediately after the other required args (`user_id`, `chesscom_username`, `lichess_username`).

### IN-05: `PG_DBNAME` constant disagrees with the original plan (cosmetic)

**File:** `scripts/stress_test_dual_platform_import.py:57`
**Issue:** The plan (`95-02-PLAN.md` line 107) specified `WHERE datname='flawchess_dev'`, but the actual dev database name is `flawchess` (verified via `app/core/config.py:DATABASE_URL`). The author correctly identified and fixed this — but there's no comment explaining the discrepancy. A future maintainer reading 95-02-PLAN.md against the code will wonder if the value is a typo or intentional.
**Fix:** Add a one-line comment: `# Dev DB name is "flawchess" per app.core.config.settings.DATABASE_URL; the plan said "flawchess_dev" which was a plan-side typo.`

### IN-06: `_sample_pg_activity` opens a new connection per sample tick

**File:** `scripts/stress_test_dual_platform_import.py:314`
**Issue:** Each sample tick calls `async with engine.connect() as conn:` — opens and closes a connection from the pool every 5 seconds. With `pool_size=1, max_overflow=0` (line 171), this is one of two pooled connections cycling; each cycle does a TCP handshake and authentication round-trip. Not a correctness issue (the result row counts will be the same), but each sampler tick now counts the sampler's own connection in `pg_stat_activity`, slightly inflating `peak_connection_count`. Hold the connection open for the lifetime of the sampler instead.
**Fix:** Open one connection in the outer `with` block in `_sample_metrics` and pass it to `_sample_pg_activity`, mirroring how `docker_writer` is opened once and reused.

### IN-07: Out-of-scope: `_sample_pg_activity` row count includes the sampler's own backend

**File:** `scripts/stress_test_dual_platform_import.py:301-330`
**Issue:** `peak_connection_count` will be at least 1 even with no imports running (the sampler's own SELECT shows up in `pg_stat_activity`). The pre-copy vs post-copy comparison is still valid (both runs include the +1), but the absolute number reported in the verdict report should be documented as "includes sampler backend." Pure observability noise — not a correctness issue.
**Fix:** Either filter out the sampler's PID via `AND pid != pg_backend_pid()` in the WHERE clause, or document the +1 offset in the report's Methodology section.

---

_Reviewed: 2026-05-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
