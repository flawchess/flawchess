---
phase: 95-asyncpg-copy-positions
fixed_at: 2026-05-27T18:45:00Z
review_path: .planning/phases/95-asyncpg-copy-positions/95-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 7
status: all_fixed
---

# Phase 95: Code Review Fix Report

**Fixed at:** 2026-05-27T18:45:00Z
**Source review:** `.planning/phases/95-asyncpg-copy-positions/95-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (Warnings WR-01 through WR-05)
- Fixed: 5
- Skipped: 7 (all out-of-scope Info findings)

## Fixed Issues

### WR-01: Docker stats subprocess invoked twice per sample tick

**Files modified:** `scripts/stress_test_dual_platform_import.py`
**Commit:** `787c1d0c`
**Applied fix:** `_sample_docker` now returns the parsed `mem_bytes` so the CSV write and the peak tracker share a single docker stats observation. Removed the redundant `_get_docker_mem_bytes` helper entirely (its functionality is subsumed by `_sample_docker`'s new return value). This halves per-sample subprocess cost (one `docker stats --no-stream` per tick instead of two) and eliminates the per-sample CSV/peak divergence under live memory pressure.

### WR-02: Dead parameters threaded through sampler helpers

**Files modified:** `scripts/stress_test_dual_platform_import.py`
**Commit:** `787c1d0c` (combined with WR-01)
**Applied fix:** Removed unused `fh` and `peak_mem_bytes` parameters from `_sample_docker` and unused `fh` from `_sample_pg_activity`. The `peak_mem_bytes` removal happened naturally as part of the WR-01 fix (the helper now returns the value instead of pretending to update it). Committed together with WR-01 because both fixes touch the same function signatures and the changes are inseparable.

### WR-03: Bare `except Exception` swallows all errors with no logging

**Files modified:** `scripts/stress_test_dual_platform_import.py`
**Commit:** `b7cdd1c7`
**Applied fix:** Added `print(f"[sampler] {kind} sample failed: {exc!r}", file=sys.stderr)` inside the `except Exception` blocks of both `_sample_docker` and `_sample_pg_activity`. Also added a dedicated `except FileNotFoundError: raise` branch in `_sample_docker` so a missing `docker` binary aborts the run immediately rather than silently producing 0-byte traces. The `_get_docker_mem_bytes` helper that the reviewer also flagged was removed by WR-01, so its `except` no longer exists. Did not add a `sample_failures` counter to the summary JSON (reviewer flagged that as a bonus suggestion, not required) — the stderr logging satisfies the "some operator-visible signal" requirement.

### WR-04: Rollback-atomicity test leaks committed user across the session-scoped engine

**Files modified:** `tests/test_game_repository_bulk_insert_positions.py`
**Commit:** `8a4f0a54` (plus formatter follow-up `ec631ec5`)
**Applied fix:** Chose reviewer's recommended option (a): wrapped the test body in `try/finally` and added a cleanup block that opens a fresh `session_maker()`, executes `DELETE FROM users WHERE id = :uid` for `user_id=2003`, and commits. The cleanup runs regardless of test outcome. Added an explanatory comment referencing WR-04. A follow-up `style(95)` commit picked up a ruff format unwrap of a multi-line assert (pure formatter output, no behavior change).

### WR-05: Test file docstring claims "live dev Postgres" but tests run against `flawchess_test`

**Files modified:** `tests/test_game_repository_bulk_insert_positions.py`, `.planning/phases/95-asyncpg-copy-positions/95-01-SUMMARY.md`
**Commit:** `50842cc7`
**Applied fix:** Updated the module docstring to "Uses the test Postgres DB (`flawchess_test`) via the `db_session` fixture, which auto-rolls-back each test (no DB mocks)." Also updated the matching phrasing in `95-01-SUMMARY.md` line 67 from "live dev Postgres" to "test Postgres DB (`flawchess_test`) via the `db_session` fixture (which auto-rolls-back each test)" — the reviewer flagged the SUMMARY phrasing explicitly as well.

## Skipped Issues

### IN-01: `chunk_size = 1700` is a magic number with a multi-line rationale

**File:** `app/repositories/game_repository.py:223`
**Reason:** out of scope (info)
**Original issue:** The constant is duplicated across `game_repository.py` (local `chunk_size = 1700`) and `tests/test_game_repository_bulk_insert_positions.py` (`_CHUNK_SIZE = 1700`). Should be promoted to a module-level `_POSITION_CHUNK_SIZE` and imported from the test.

### IN-02: `_POSITION_COPY_COLUMNS` referenced with `# noqa: SLF001` in tests

**File:** `tests/test_game_repository_bulk_insert_positions.py:102, 136`
**Reason:** out of scope (info)
**Original issue:** Test imports a single-underscore-prefixed name and silences `SLF001` twice. Should rename to public `POSITION_COPY_COLUMNS` since it is a CI contract.

### IN-03: `assert raw_conn is not None` runs in production with assertions disabled under `python -O`

**File:** `app/repositories/game_repository.py:221`
**Reason:** out of scope (info)
**Original issue:** Type-narrowing `assert` is stripped under `python -O`; should be replaced with `if raw_conn is None: raise RuntimeError(...)`. Project doesn't currently use `-O`, so this is informational.

### IN-04: Sampler keyword-only param `output_tag` has no default and follows params that do

**File:** `scripts/stress_test_dual_platform_import.py:338-347`
**Reason:** out of scope (info)
**Original issue:** Required kw-only `output_tag` is positioned after kw-only args that have defaults; convention is required-first within a kw-only block.

### IN-05: `PG_DBNAME` constant disagrees with the original plan (cosmetic)

**File:** `scripts/stress_test_dual_platform_import.py:57`
**Reason:** out of scope (info)
**Original issue:** Plan said `flawchess_dev` (typo); code correctly uses `flawchess`. Reviewer suggested adding a one-line comment explaining the discrepancy.

### IN-06: `_sample_pg_activity` opens a new connection per sample tick

**File:** `scripts/stress_test_dual_platform_import.py:314`
**Reason:** out of scope (info)
**Original issue:** Each sample tick opens/closes a pooled connection. Should hold one connection open for the lifetime of the sampler. Pure efficiency improvement, not a correctness issue.

### IN-07: `_sample_pg_activity` row count includes the sampler's own backend

**File:** `scripts/stress_test_dual_platform_import.py:301-330`
**Reason:** out of scope (info)
**Original issue:** `peak_connection_count` is inflated by +1 from the sampler's own pg_stat_activity row. Pre/post comparison still valid (both include the +1). Pure observability noise.

---

_Fixed: 2026-05-27T18:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
