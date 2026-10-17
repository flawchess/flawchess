---
phase: 241-codebase-cleanup
plan: 53
subsystem: services-eval-engine
tags: [naming, refactor, rename]
requires: [241-02, 241-03, 241-09, 241-11, 241-13]
provides:
  - FLAW_BLOB_AND_TACTIC_COLUMNS
  - _book_ply_count
  - refresh_game_flaw_counts_and_accuracy
  - mover_color_col (best_move_tier_sql / _es_sql parameter)
affects: [app/repositories/game_flaws_repository.py, app/services/eval_apply.py, app/services/accuracy_acpl.py, app/services/best_move_candidates.py]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-53.tsv
    - .planning/phases/241-codebase-cleanup/allow/241-53.tsv
  modified:
    - app/repositories/game_flaws_repository.py
    - app/services/eval_apply.py
    - app/services/accuracy_acpl.py
    - app/services/best_move_candidates.py
key-decisions:
  - "ruff format's magic trailing comma after the FLAW_BLOB rename is allowed via allow/241-53.tsv (the only non-rename token change)"
requirements-completed: [D-06, D-07, D-10, D-17]
status: complete
commits: 4
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: 5655f496fc72dc802d1d258bd2f40e815aad5b70
actuals:
  tokens: 4000
  tasks: 2
  commits: 4
completed: 2026-10-16
---

# Phase 241 Plan 53: Eval-engine renames Summary

Four INVENTORY section 5 renames in the eval engine, each its own `refactor(naming)` commit, with no behavior change.

## Renames

| old | new | commit | files |
|-----|-----|--------|-------|
| `FLAW_BLOB_COLUMNS` | `FLAW_BLOB_AND_TACTIC_COLUMNS` | a9aacff05 | game_flaws_repository.py, eval_apply.py |
| `_out_of_book_ply_count` | `_book_ply_count` | 77429433e | eval_apply.py |
| `refresh_game_oracle_counts` | `refresh_game_flaw_counts_and_accuracy` | b7a491751 | eval_apply.py, accuracy_acpl.py |
| `user_color_col` | `mover_color_col` (best_move_candidates only) | 5655f496f | best_move_candidates.py |

rename-maps/241-53.tsv holds the four rows.

## Notes

- Tuple string values (DB column names) unchanged. `ruff format` split the lengthened definition line and added a magic trailing comma; this is the only non-rename token change and is covered by an allow row in allow/241-53.tsv.
- `_book_ply_count`'s docstring said "out-of-book test"; reworded to "count the in-book plies" to match the new name. The `oracle_counts_written` local variable and `test_oracle_counts_*` test name were left alone (not in the plan's four identifiers).
- `refresh_game_oracle_counts` had no caller in scripts/ or tests (re-grepped); only eval_apply.py and the accuracy_acpl.py docstring.
- `user_color_col` use counts outside best_move_candidates.py before and after: train_pool.py 3, query_utils.py 8, library_repository.py 5 (identical). Callers of `best_move_tier_sql` pass the color positionally, so no caller changed.

## Verification

- `uv run ty check app/ tests/ scripts/`: pass (baseline also clean).
- Targeted tests: test_eval_apply, test_full_eval_drain, test_flaw_upsert_equivalence (107 passed); test_eval_apply, test_accuracy_acpl, test_best_move_candidates, test_backfill_accuracy_acpl (94 passed). One transient xdist DB-clone collision error occurred once while other worktrees ran in parallel; the identical re-run passed.
- `cleanup.py absent` (4 rows, 0 hits), `cleanup.py diff --plan 241-53` (exit 0), `source_scan_tests.sh --py` (5 passed).

## Deviations from Plan

**1. [Rule 3 - Blocking] ruff format trailing comma** found during Task 1: formatter-required reflow of the renamed tuple definition added a `,` token that `diff` reported as residue. Fix: allow row in allow/241-53.tsv (new file, same pattern as the plan's isort precedent). Commit a9aacff05.

Total deviations: 1 auto-fixed (blocking). Impact: none on behavior.

## Self-Check: PASSED

All four commits present in `git log`; rename-maps/241-53.tsv and allow/241-53.tsv exist.
