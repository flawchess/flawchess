---
phase: quick-260616-jq1
plan: "01"
type: execute
subsystem: eval_drain
tags: [performance, n-plus-one, batch-write, sentry, flawchess-6b]
dependency_graph:
  requires: []
  provides: [batched-eval-write, batched-pv-write]
  affects: [app/services/eval_drain.py, tests/services/test_full_eval_drain.py]
tech_stack:
  added: []
  patterns: [UPDATE ... FROM (VALUES ...) batched write, CAST() for asyncpg named-param compatibility]
key_files:
  created: []
  modified:
    - app/services/eval_drain.py
    - tests/services/test_full_eval_drain.py
decisions:
  - "Used CAST(:param AS type) instead of ::type cast syntax — asyncpg rewrites named params to $N positional before server parses, making ::$1 a syntax error"
  - "Split write rows into two groups (bm_only_rows and eval_rows) rather than a single catch-all group — cleaner model matching the existing branching logic"
  - "eval_rows includes best_move as nullable in the same VALUES tuple — overwriting NULL with NULL is safe since both come from the same target pass"
  - "Batched PV UPDATE wrapped in try/except at batch level (not per-row) — the realistic failure mode (DB connection error) would have invalidated the whole session anyway; the pre-filter removes the only realistic per-row failure (None skips)"
  - "Used f-strings for static SQL structure only; all values are bound params via named :param_N placeholders — no user input interpolated"
metrics:
  duration: "~25 minutes"
  completed: "2026-06-16"
  tasks_completed: 3
  files_changed: 2
---

# Phase quick-260616-jq1 Plan 01: Batch Eval Write N+1 Fix Summary

Batched the two per-row `UPDATE game_positions` loops in the SEED-044 hot eval write path, eliminating the N+1 pattern Sentry flagged as FLAWCHESS-6B.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Batch main eval write in `_apply_full_eval_results` | 2ac78457 | app/services/eval_drain.py |
| 2 | Batch flaw-PV write in `_classify_and_fill_oracle` (Fixes FLAWCHESS-6B) | 22190da0 | app/services/eval_drain.py |
| 3 | Add multi-flaw batched-write regression test + touched-area gate | a2b0b1f7 | tests/services/test_full_eval_drain.py |

## What Was Built

**Task 1:** Replaced the `for target in targets:` write loop in `_apply_full_eval_results` with two new module-level helper functions:

- `_batch_update_best_move_rows(session, game_id, bm_rows)` — emits one `UPDATE game_positions SET best_move = v.best_move FROM (VALUES ...) AS v(ply, best_move)` for lichess-eval plies (best_move-only) and engine hole-rows that still have a best_move.
- `_batch_update_eval_rows(session, game_id, eval_rows)` — emits one `UPDATE game_positions SET eval_cp = v.eval_cp, eval_mate = v.eval_mate, best_move = v.best_move FROM (VALUES ...) AS v(...)` for engine plies with a resolved eval.

The per-target pass still accumulates `failed_ply_count` and classifies rows into the two groups (pure Python, no DB I/O), then calls both helpers at the end.

**Task 2:** Replaced the `for flaw in flaw_list:` PV-write loop in `_classify_and_fill_oracle` with a pre-filter + single batched UPDATE pattern. Pass 1 collects surviving `(pv_ply, pv_string)` pairs (skipping None entries). If non-empty, emits one `UPDATE game_positions SET pv = v.pv FROM (VALUES ...) AS v(ply, pv)`. The batch-level try/except preserves the fault-tolerance intent: a failure is Sentry-captured (game_id in `set_context`, not message string) without aborting flaw rows or oracle counts already committed above.

**Task 3:** Added `TestBatchedWriteRegression.test_two_flaw_pvs_written_at_correct_plies` which exercises the multi-row VALUES clause with a two-blunder game (white at ply 2, black at ply 3), asserting pv at both N+1 plies (3 and 4) and NULL elsewhere, plus eval_cp correctness at the blunder plies.

## Key Technical Decision: asyncpg CAST() vs ::

asyncpg's named-parameter rewrite converts `:param` to `$N` positional params before the PostgreSQL server parses the SQL. This means `::$1` would be a syntax error at the server. Used `CAST(:param_N AS type)` throughout — functionally identical to `::type` but compatible with asyncpg's rewrite order.

## Correctness Preserved

All existing correctness invariants are maintained:

- `failed_ply_count` computed in the same per-target pass, unchanged logic (ends_game exemption, NULL-hole counting, is_lichess_eval_game branching)
- lichess %evals never overwritten (is_lichess_eval_game gate unchanged)
- best_move written independently of eval (SEED-044 independence preserved)
- Empty row groups emit no UPDATE (guarded in each helper)
- Terminal targets skipped (same `if target.is_terminal: continue` guard)
- PV fault-tolerance: pre-filter removes None entries; batch try/except captures failures without aborting oracle counts

## Verification

- `grep` confirms no `await session.execute(update(...))` inside a `for target in targets:` or `for flaw in flaw_list:` loop in the write functions
- `grep -nE "f['\"].*UPDATE|f['\"].*VALUES"` shows only static structural f-strings, never user-data interpolation — all values are bound params
- `grep -n "asyncio.gather" app/services/eval_drain.py` shows only the pre-existing engine fan-out outside any session scope
- 47 tests pass: `test_full_eval_drain.py` (34, including new regression) + `test_eval_drain.py` (13)
- `ruff format --check`, `ruff check`, `ty check` all clean

## Deviations from Plan

**[Rule 1 - Bug] asyncpg named-param / cast syntax incompatibility**

- **Found during:** Task 1 first test run
- **Issue:** The plan's suggested `::smallint` / `::varchar` cast syntax adjacent to named parameters fails with asyncpg because it rewrites `:param` to `$N` before server parsing, making `::$1` a PostgreSQL syntax error.
- **Fix:** Used `CAST(:param AS type)` throughout all three batched UPDATEs. Functionally identical result; documented in each helper's docstring.
- **Files modified:** app/services/eval_drain.py
- **Commit:** 2ac78457 (fix applied before first task commit)

## Known Stubs

None.

## Threat Flags

None — this change only modifies the DB write path for internal background workers, adds no new endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- app/services/eval_drain.py: modified (confirmed via git log)
- tests/services/test_full_eval_drain.py: modified (confirmed via git log)
- Commits 2ac78457, 22190da0, a2b0b1f7: all present in git log
- 47 tests pass, all format/lint/type gates clean
