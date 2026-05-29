---
phase: quick-260529-cum
plan: "01"
subsystem: percentile-compute / canonical_slice_sql
tags: [perf, sql, game-positions, recent-capped, percentile]
dependency_graph:
  requires: []
  provides: [optimized-per-TC-percentile-CTEs]
  affects: [app/services/canonical_slice_sql.py, tests/scripts/fixtures/global_percentile_cdf/]
tech_stack:
  added: []
  patterns: [game_id-membership-filter via IN subquery, JOIN scoping pattern]
key_files:
  created: []
  modified:
    - app/services/canonical_slice_sql.py
    - tests/scripts/fixtures/global_percentile_cdf/*.sql (20 of 32 files)
    - CHANGELOG.md
decisions:
  - Use IN (SELECT id FROM recent_capped) for endgame_game_ids CTEs rather than JOIN to keep the filter predicate in the WHERE clause (matches _score_gap_bucket_tc proof pattern's JOIN only on the FROM clause, not in a subquery)
  - Scope _endgame_entry_clocks_cte via JOIN rather than IN subquery for consistency with the existing per_user_cte_score_gap_bucket_tc spans pattern
metrics:
  duration: ~20 min
  completed: "2026-05-29T07:24:22Z"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 22
---

# Phase quick-260529-cum Plan 01: Scope game_positions Aggregation to recent_capped Summary

Scoped five per-TC percentile CTE builders' `game_positions` scans to the selected user's `recent_capped` game set, eliminating a full-table scan on every import and eval-drain hot-path call.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Scope three game_positions aggregations to recent_capped | 8d175a14 | app/services/canonical_slice_sql.py |
| 2 | Regenerate SQL fixtures and confirm only expected cells drifted | e6183801 | tests/scripts/fixtures/global_percentile_cdf/ (20 files) |
| 3 | CHANGELOG entry + full pre-PR checklist gate | a94a5b61 | CHANGELOG.md |

## What Was Done

Three edits to `app/services/canonical_slice_sql.py`:

1. `_endgame_entry_clocks_cte()`: Changed `FROM game_positions gp` to `FROM game_positions gp JOIN recent_capped rc ON rc.id = gp.game_id`. Fixes all three time-pressure per-TC builders (`per_user_cte_time_pressure_score_gap`, `per_user_cte_clock_gap`, `per_user_cte_net_flag_rate`) since they all call this helper.

2. `per_user_cte_score_gap_tc` `endgame_game_ids` CTE: Added `AND game_id IN (SELECT id FROM recent_capped)` predicate.

3. `per_user_cte_achievable_tc` `endgame_game_ids` CTE: Applied the identical `AND game_id IN (SELECT id FROM recent_capped)` predicate. The `entry_rows` CTE inherits scoping automatically via its JOIN on `endgame_game_ids`.

Each edit site carries an inline result-equivalence comment explaining that only `recent_capped` games survive downstream joins, and that `HAVING count(*) >= 6` is unaffected by game_id membership filtering.

`per_user_cte_score_gap_bucket_tc` was left unchanged (already has `JOIN recent_capped rc ON rc.id = gp.game_id` in its `spans` CTE). The non-`_tc` builders `per_user_cte_score_gap` and `per_user_cte_achievable` were also left unchanged per scope.

## Fixture Drift Confirmation

20 of 32 fixtures changed (exactly the expected set):
- `score_gap__{bullet,blitz,rapid,classical}.sql`
- `achievable_score_gap__{bullet,blitz,rapid,classical}.sql`
- `time_pressure_score_gap__{bullet,blitz,rapid,classical}.sql`
- `clock_gap__{bullet,blitz,rapid,classical}.sql`
- `net_flag_rate__{bullet,blitz,rapid,classical}.sql`

The `score_gap_conv__*`, `score_gap_parity__*`, `score_gap_recovery__*` fixtures are byte-identical (untouched builder).

## Pre-PR Checklist Results

- ruff format: 187 files unchanged
- ruff check: all checks passed
- ty check: all checks passed (zero errors)
- pytest targeted suite (3 files, 459 tests): all passed
- pytest full suite (excluding pre-existing environmental failure): 2206 passed, 16 skipped

Note: `tests/scripts/test_backfill_user_percentiles.py::test_backfill_target_prod_refuses_when_tunnel_down` was failing with `DID NOT RAISE <class 'SystemExit'>` because the prod DB SSH tunnel was active on port 15432 during this session. This test is unrelated to the edited files and fails whenever the prod tunnel is open. It is a pre-existing environmental condition.

## Deviations from Plan

None. Plan executed exactly as written.

## Self-Check: PASSED

- `app/services/canonical_slice_sql.py` exists and contains `JOIN recent_capped rc ON rc.id = gp.game_id` at line 609 (new) plus lines 498 and 1025 (pre-existing)
- `AND game_id IN (SELECT id FROM recent_capped)` appears at lines 874 and 937
- 20 fixture files changed, 12 bucket fixtures unchanged
- Commits 8d175a14, e6183801, a94a5b61 present in git log
- `per_user_cte_score_gap_bucket_tc` and non-`_tc` builders untouched
