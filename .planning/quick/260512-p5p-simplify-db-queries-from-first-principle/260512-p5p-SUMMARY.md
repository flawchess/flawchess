---
phase: 260512-p5p
plan: 01
subsystem: repositories
tags: [refactor, sql, stats, openings, planner-stability]
requires: []
provides:
  - "Single query_resulting_position_wdl for resulting-position WDL (transposition_counts/wdl helpers removed)"
  - "Flat single-SELECT query_position_wdl_batch (no dedup subquery)"
  - "CTE-free query_opening_phase_entry_metrics_batch (plain subquery dedup)"
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
  - "Use .subquery() over .cte() so the PG 18 planner can inline freely (CTEs are optimization fences when inlining is inhibited by predicates)."
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

## Task 3 - Drop CTE from query_opening_phase_entry_metrics_batch

**Commit:** `1c51e188 refactor(stats): drop CTE from query_opening_phase_entry_metrics_batch`

- Single structural change: `dedup_select.cte("dedup")` → `dedup_select.subquery("dedup")`. The `.c` interface is identical so the downstream `phase_entry_subq` and `agg_select` references work unchanged.
- The six aggregates, sign convention (`case((Game.user_color == "white", 1), else_=-1) * eval_cp`), four eval-state predicates (`has_continuous_in_domain_eval`, `has_mate`, `has_null_eval`, `has_outlier_eval`), and `EVAL_OUTLIER_TRIM_CP = 2000` constant are preserved verbatim.
- Docstring updated to remove the obsolete "materialized as a CTE" rationale.

**Why this matters:** PG 18 inlines CTEs only when referenced once AND side-effect-free AND not marked MATERIALIZED, and even then inlining can be inhibited by complex predicates. A plain subquery has no such restrictions, giving the planner maximum flexibility (same lesson as PR #90).

## Guardrail Tests Added

Two new structural-shape guardrails compile a representative statement and assert the absence of pathological structures. Both follow PR #90's precedent (`test_query_compiles_to_flat_aggregation`):

1. **`test_query_position_wdl_batch_compiles_flat`** (in `tests/repositories/test_opening_insights_repository.py`) — asserts no `WITH `, no `SELECT DISTINCT`, no `FROM (SELECT` in the compiled SQL.
2. **`test_query_phase_entry_metrics_compiles_without_cte`** (same file) — asserts no `WITH ` in the compiled SQL.

The partition-invariant test `test_partition_invariant_phase_entry_total` was augmented to cover two distinct hashes with mixed bucket distributions (5 rows in hash A, 3 rows in hash B), with per-bucket counts hand-computed so a partition bug surfaces as a specific failed assertion rather than only as a sum mismatch.

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
- [x] `grep -n "\.cte(" app/repositories/stats_repository.py` returns no matches.
- [x] `grep -rn "query_transposition_counts\|query_transposition_wdl" app/ tests/` returns only comment/docstring/test-name occurrences, no symbol references.
- [ ] **Post-deploy:** Tunnel into prod with `bin/prod_db_tunnel.sh` and `EXPLAIN ANALYZE query_opening_phase_entry_metrics_batch` for user 84 on a representative hash batch; confirm the plan stays in the same zone as `query_opening_transitions` after PR #90. (Higher-risk task — CTE removal could surprise the planner on heavy users; PR #90 demonstrated the inverse case where dropping the CTE *improved* plan stability, but verifying on production data closes the loop.)

## Self-Check: PASSED

- File `app/repositories/openings_repository.py` exists, transposition helpers removed.
- File `app/repositories/stats_repository.py` exists, no `.cte(` in `query_opening_phase_entry_metrics_batch`.
- File `app/services/openings_service.py` exists, single resulting-position WDL call in `get_next_moves`.
- Commit `77dfdb86` exists on `worktree-agent-a3917997428703476`.
- Commit `830ec0b2` exists on `worktree-agent-a3917997428703476`.
- Commit `1c51e188` exists on `worktree-agent-a3917997428703476`.
