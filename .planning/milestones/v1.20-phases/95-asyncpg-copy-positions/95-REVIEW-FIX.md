---
phase: 95-asyncpg-copy-positions
fixed_at: 2026-05-27T20:00:00Z
review_path: .planning/phases/95-asyncpg-copy-positions/95-REVIEW.md
iteration: 2
findings_in_scope: 12
fixed: 12
skipped: 0
status: all_fixed
---

# Phase 95: Code Review Fix Report

**Fixed at:** 2026-05-27T20:00:00Z
**Source review:** `.planning/phases/95-asyncpg-copy-positions/95-REVIEW.md`
**Iteration:** 2

**Summary:**
- Findings in scope: 12 (5 Warnings + 7 Info)
- Fixed: 12
- Skipped: 0

Iteration 1 fixed the 5 Warnings (WR-01..WR-05). Iteration 2 extended scope to `all`
and addressed the 7 Info findings (IN-01..IN-07).

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

### IN-01: `chunk_size = 1700` is a magic number with a multi-line rationale

**Files modified:** `app/repositories/game_repository.py`, `tests/test_game_repository_bulk_insert_positions.py`
**Commit:** `e8f1e61e`
**Applied fix:** Promoted the local `chunk_size = 1700` inside `bulk_insert_positions` to a module-level constant `_POSITION_CHUNK_SIZE: int = 1700` with a brief rationale comment. Updated the chunking docstring to reference the new constant name. In the test file, replaced the duplicated `_CHUNK_SIZE = 1700` literal with a direct import of `_POSITION_CHUNK_SIZE` from `app.repositories.game_repository`, then used it in the chunking-boundary test (`n_rows = _POSITION_CHUNK_SIZE + 1`). The chunk-boundary test now tracks tuning changes automatically.

### IN-02: `_POSITION_COPY_COLUMNS` referenced with `# noqa: SLF001` in tests

**Files modified:** `app/repositories/game_repository.py`, `tests/test_game_repository_bulk_insert_positions.py`
**Commit:** `f57d4768`
**Applied fix:** Renamed `_POSITION_COPY_COLUMNS` → `POSITION_COPY_COLUMNS` (dropped the leading underscore — the constant is a CI-enforced public contract, not a private implementation detail) at every reference site (definition, both internal usages in `bulk_insert_positions`, and both test references). Removed the two `# noqa: SLF001` suppressions in the test file along with the corresponding docstring/assert message references to the old name. Did NOT touch references in `95-01-PLAN.md` / `95-01-SUMMARY.md` — those are historical planning artifacts that describe the originally-implemented name and should remain as historical context.

### IN-03: `assert raw_conn is not None` runs in production with assertions disabled under `python -O`

**Files modified:** `app/repositories/game_repository.py`
**Commit:** `24f95546` (plus formatter follow-up `22fab4c3`)
**Applied fix:** Replaced `assert raw_conn is not None, "..."` with an explicit `if raw_conn is None: raise RuntimeError("asyncpg driver_connection is None — SQLAlchemy adapter changed")`. The new guard survives `python -O` / `PYTHONOPTIMIZE=1` (which strips asserts) and gives a specific, debuggable error if SQLAlchemy's asyncpg adapter ever changes the contract. Added an inline comment explaining why an explicit check is preferred over assert for type narrowing. Ruff format collapsed the multi-line raise into a single line in a follow-up `style(95)` commit.

### IN-04: Sampler keyword-only param `output_tag` has no default and follows params that do

**Files modified:** `scripts/stress_test_dual_platform_import.py`
**Commit:** `074efca5`
**Applied fix:** Moved `output_tag: str` (required, no default) to immediately after `lichess_username: str` in `run_stress_test`'s keyword-only block, in front of the kw-only args that have defaults (`sample_interval_s`, `db_container_name`, `output_dir`). The call site in `main()` already uses keyword arguments throughout, so the reorder is API-compatible for all current callers.

### IN-05: `PG_DBNAME` constant disagrees with the original plan (cosmetic)

**Files modified:** `scripts/stress_test_dual_platform_import.py`
**Commit:** `26c04eab`
**Applied fix:** Added a two-line comment above `PG_DBNAME: str = "flawchess"` explaining that the dev DB name comes from `app.core.config.settings.DATABASE_URL` and that the plan (95-02-PLAN.md line 107) said `flawchess_dev` as a plan-side typo. A future maintainer cross-referencing the plan against the code will see the discrepancy is intentional.

### IN-06: `_sample_pg_activity` opens a new connection per sample tick

**Files modified:** `scripts/stress_test_dual_platform_import.py`
**Commit:** `e3981f3a`
**Applied fix:** Hoisted the pg connection out of `_sample_pg_activity` and into the outer `_sample_metrics` context via `async with metric_engine.connect() as pg_conn:`, wrapping the existing `with (...docker_fh, ...pg_fh):` block. Changed `_sample_pg_activity`'s signature from `engine: object` to `conn: object` (typed as `AsyncConnection` at runtime via `isinstance` narrowing) and dropped the `async with engine.connect()` block inside the helper. The connection is now reused across every sample tick, eliminating the per-tick TCP handshake + auth round-trip and avoiding the +1 connection churn in `pg_stat_activity`.

### IN-07: `_sample_pg_activity` row count includes the sampler's own backend

**Files modified:** `scripts/stress_test_dual_platform_import.py`
**Commit:** `92905db5`
**Applied fix:** Appended `AND pid != pg_backend_pid()` to the `WHERE` clause in `_sample_pg_activity`'s SQL so the sampler's own backend is excluded from the row count. `peak_connection_count` now reflects only import-driven connections; the pre-copy vs post-copy comparison in the verdict report is no longer offset by +1 from observability noise. Added a one-line comment referencing IN-07 above the new WHERE term.

---

_Fixed: 2026-05-27T20:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
