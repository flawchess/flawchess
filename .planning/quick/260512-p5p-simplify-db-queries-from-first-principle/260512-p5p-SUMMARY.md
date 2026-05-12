---
phase: 260512-p5p
plan: 01
subsystem: repositories
tags: [refactor, sql, stats, openings, planner-stability]
requires: []
provides:
  - "Single query_resulting_position_wdl for resulting-position WDL (transposition_counts/wdl helpers removed)"
  - "Flat single-SELECT query_position_wdl_batch (no dedup subquery)"
  - "REVERTED: CTE-free query_opening_phase_entry_metrics_batch — see Task 3 below"
affects:
  - app/repositories/openings_repository.py
  - app/repositories/stats_repository.py
  - app/services/openings_service.py
  - tests/repositories/test_opening_insights_repository.py
  - tests/test_openings_repository.py
  - tests/test_stats_repository_phase_entry.py
key-files-created: []
key-files-modified:
  - app/repositories/openings_repository.py
  - app/repositories/stats_repository.py
  - app/services/openings_service.py
  - tests/repositories/test_opening_insights_repository.py
  - tests/test_openings_repository.py
  - tests/test_stats_repository_phase_entry.py
decisions:
  - "Behavior-preserving structural refactor only; no schema/API surface changes."
  - "Derive trans_counts inline from wins+draws+losses to eliminate the extra DB round trip in get_next_moves."
  - "Mirror PR #90 (commit 3fe670fe) shape: COUNT(DISTINCT game_id) FILTER (...) at aggregate level beats wrapping a DISTINCT dedup subquery."
  - "REVERSED: dropping the CTE in query_opening_phase_entry_metrics_batch (Task 3) measured 18-45% slower on prod across all user sizes. The dedup_subq is referenced twice, so a plain subquery is emitted as two independent inline derived tables that PG does not CSE — doubling the heavy DISTINCT-ON. CTE auto-materialization (PG 12+) is exactly what's wanted here."
metrics:
  duration: ~20m
  completed: 2026-05-12
---

# Quick 260512-p5p: Simplify Overcomplicated DB Queries Summary

Three behavior-preserving SQL simplifications landed as three atomic refactor commits, mirroring the planner-stability precedent set by PR #90 (`refactor(openings): simplify opening insights query to flat aggregation`, commit 3fe670fe).

## Task 1 - Consolidate transposition WDL queries

**Commit:** `77dfdb86 refactor(openings): consolidate transposition WDL queries into single function`

- Deleted `query_transposition_counts` and `query_transposition_wdl` from `app/repositories/openings_repository.py`. The surviving `query_resulting_position_wdl` has identical SQL shape and one extra column (`last_played_at`).
- Updated `get_next_moves` in `app/services/openings_service.py` to issue a single resulting-position WDL round trip. `trans_counts` is derived inline as `{h: w + d + lo for h, (w, d, lo, _last) in pos_wdl.items()}` since every game has exactly one result.
- Per-move loop unpacking changed from `w, d, lo = pos` to `w, d, lo, _last = pos`. The 4th tuple element (last_played_at) is not consumed at the move level; Move Explorer surfaces last-played at the position level.
- Docstring of `get_next_moves` updated to reflect the now-single round trip.

**Surface area removed:** two repository functions, ~130 lines of duplicated SQL, one DB round trip per move-explorer request.

## Task 2 - Flatten query_position_wdl_batch

**Commit:** `830ec0b2 refactor(stats): flatten query_position_wdl_batch to single-SELECT aggregation`

- Replaced the `SELECT DISTINCT (full_hash, game_id, ...) AS dedup` subquery + outer `COUNT()` wrapper with a flat `SELECT ... JOIN games ... GROUP BY full_hash` using `COUNT(DISTINCT game_id) FILTER (win_cond)` at aggregate level. Transposition dedup (same game's hash at multiple plies counted once) is now handled by the COUNT-DISTINCT directly.
- `total` is derived in Python as `wins + draws + losses` rather than executing a fourth `COUNT(DISTINCT)` aggregate; equivalent because every game has exactly one result.
- Filter parity preserved via `apply_game_filters` with identical kwargs; signature unchanged.

## Task 3 - Drop CTE from query_opening_phase_entry_metrics_batch — REVERTED

**Original commit:** `1c51e188 refactor(stats): drop CTE from query_opening_phase_entry_metrics_batch`
**Reverted in PR #93 after prod EXPLAIN ANALYZE.**

The original rationale (PG 18 CTEs as optimization fences) was wrong for this query. `dedup_subq` is referenced twice — once in `phase_entry_subq.WHERE game_id IN (...)` and once in `agg_select.select_from(...)`. SQLAlchemy emits each reference as an independent inline derived table, and Postgres does not CSE identical subquery bodies. The CTE form auto-materializes (PG 12+ behavior when CTE has >1 reference) and reuses the materialized tuples cheaply — exactly what the deleted comment said.

**Prod measurements** (25-hash batch, prod DB via `bin/prod_db_tunnel.sh`, median of 3 runs after warm-up):

| User | Games | CTE (old) | subquery (new) | Slowdown |
|---|---:|---:|---:|---:|
| 45 | 38,953 | 1298 ms | 1527 ms | +18% |
| 13 | 21,835 | 963 ms | 1166 ms | +21% |
| 84 | 718 | 43 ms | 51 ms | +17% |
| 33 | 445 | 32 ms | 39 ms | +22% |
| 43 | 229 | 28 ms | 41 ms | +45% |

EXPLAIN buffer counts confirm the cause: SUBQUERY scans `shared hit=590k` vs CTE `shared hit=294k` for user 45 — almost exactly 2× due to the doubled DISTINCT-ON evaluation. CTE wins across the entire user range and shows lower variance on light users (user 43: 27-30ms stable vs 30-57ms with subquery).

The deleted comment was load-bearing. Restored with a stronger warning citing these measurements and a `DO NOT replace with .subquery()` directive so the choice doesn't get re-questioned. PR #90's precedent (where dropping a dedup wrapper improved plans) does not generalize — that query referenced its dedup once; this one references twice.

## Guardrail Tests Added

Two new structural-shape guardrails compile a representative statement and assert the absence of pathological structures. Both follow PR #90's precedent (`test_query_compiles_to_flat_aggregation`):

1. **`test_query_position_wdl_batch_compiles_flat`** (in `tests/repositories/test_opening_insights_repository.py`) — asserts no `WITH `, no `SELECT DISTINCT`, no `FROM (SELECT` in the compiled SQL.
2. ~~`test_query_phase_entry_metrics_compiles_without_cte`~~ — removed when Task 3 was reverted; the query intentionally uses a CTE.

## Deviations from Plan

### Rule 3 fix - Stale tests in tests/test_openings_repository.py

**Found during:** Task 1
**Issue:** The plan listed only `tests/repositories/test_opening_insights_repository.py` as a verify target, but `tests/test_openings_repository.py` also imported `query_transposition_counts` and `query_transposition_wdl` (the `TestTranspositionCounts` and `TestQueryTranspositionWdl` classes). Deleting the functions broke these tests at import time, blocking the Task 1 verify suite.
**Fix:** Adapted both test classes to call the surviving `query_resulting_position_wdl` instead, swapping `result_hash_list=` for `hash_list=` and slicing the 4-tuple `[:3]` when comparing W/D/L. Coverage preserved — same convergence, single-order, filter-parity, empty-list, and unknown-hash cases.
**Files modified:** `tests/test_openings_repository.py`
**Commit:** rolled into `77dfdb86` (Task 1).

### Note - global ruff format already had drift

`uv run ruff format --check .` reports 96 unrelated files would be reformatted (pre-existing drift). Modified files in this refactor are all format-clean. Not in scope to fix the pre-existing drift; logged but not corrected here.

## Test Plan

- [x] `uv run ruff check .` clean.
- [x] `uv run ty check app/ tests/` zero errors.
- [x] Targeted suites pass after each task: 130 tests (Task 1), 152 tests (Task 2), 200 tests (Task 3).
- [x] Full suite green: 1388 passed, 6 skipped (pre-existing).
- [x] `grep -rn "query_transposition_counts\|query_transposition_wdl" app/ tests/` returns only comment/docstring/test-name occurrences, no symbol references.
- [x] **Prod EXPLAIN ANALYZE on 5 users (45, 13, 84, 33, 43)** — Task 3 measured slower across all sizes (+17% to +45%). Reverted.

## Self-Check: PASSED

- File `app/repositories/openings_repository.py` exists, transposition helpers removed.
- File `app/repositories/stats_repository.py` exists, `query_opening_phase_entry_metrics_batch` uses `.cte("dedup")` (restored after prod measurement, see Task 3).
- File `app/services/openings_service.py` exists, single resulting-position WDL call in `get_next_moves`.
- Commit `77dfdb86` exists on `worktree-agent-a3917997428703476`.
- Commit `830ec0b2` exists on `worktree-agent-a3917997428703476`.
- Commit `1c51e188` reverted in PR #93.
