---
phase: 108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr
plan: "02"
subsystem: backend
tags: [game_flaws, materialization, eval_drain, repository, bulk-insert, sentry, classification]
dependency_graph:
  requires:
    - phase: 108-01
      provides: "GameFlaw ORM model (app/models/game_flaw.py) with composite PK (user_id, game_id, ply)"
  provides:
    - "game_flaws_repository.py: bulk_insert_game_flaws, delete_flaws_for_game, flaw_record_to_row"
    - "_classify_and_insert_flaws hook in eval_drain.py — post-eval materialization path"
    - "Materialization round-trip test (test_flaws_materialization.py) — D-10 classify path invariant"
  affects:
    - "Plans 108-03..08 — downstream plans read game_flaws rows written by this hook"
    - "scripts/backfill_flaws.py (Plan 108-08) — reuses flaw_record_to_row"
    - "reclassify_positions.py — will reuse flaw_record_to_row when recomputing"
tech_stack:
  added: []
  patterns:
    - "flaw_record_to_row: single FlawRecord→game_flaws row mapping (D-10 one-classify-path)"
    - "bulk_insert_game_flaws: pg_insert ON CONFLICT DO NOTHING for idempotent import hook"
    - "delete_flaws_for_game: scoped to BOTH game_id AND user_id (T-108-05 mitigation)"
    - "_classify_and_insert_flaws: sequential per-game loop in write session, no asyncio.gather"
    - "Per-game try/except + Sentry capture + continue (T-108-04: one bad game doesn't abort batch)"
    - "GameNotAnalyzed detected via 'reason' in result dict check (TypedDict runtime pattern)"
key_files:
  created:
    - app/repositories/game_flaws_repository.py
    - tests/test_flaws_materialization.py
  modified:
    - app/services/eval_drain.py
key-decisions:
  - "isinstance(result, GameNotAnalyzed) fails at runtime (TypedDict is plain dict) — use 'reason' in result check instead, consistent with library_service.py"
  - "Hook placement: AFTER _apply_eval_results so eval_cp is available for classify_game_flaws; BEFORE _mark_evals_completed so flaw rows commit atomically with eval results"
  - "Game loop is sequential (no asyncio.gather) per CLAUDE.md hard rule — 10 games x ~5 rows = ~50 rows max, fast enough serial"
requirements-completed: [D-10, D-03]
duration: 8min
completed: "2026-06-06"
tasks_completed: 3
tasks_total: 3
files_created: 2
files_modified: 1
---

# Phase 108 Plan 02: game_flaws Repository, Import Hook, and Materialization Round-Trip Test Summary

**Bulk-insert repository + Sentry-guarded post-eval import hook materializing M+B flaws atomically with eval results, verified by a 24-test round-trip suite proving the D-10 one-classify-path invariant**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-06T15:22:59Z
- **Completed:** 2026-06-06T15:30:56Z
- **Tasks:** 3
- **Files modified/created:** 3

## Accomplishments

- Created `app/repositories/game_flaws_repository.py` with `flaw_record_to_row` (single FlawRecord→row mapping), `bulk_insert_game_flaws` (ON CONFLICT DO NOTHING, no-op on empty), and `delete_flaws_for_game` (scoped to both game_id and user_id)
- Added `_classify_and_insert_flaws` hook in `eval_drain.py` — called AFTER `_apply_eval_results` and BEFORE `_mark_evals_completed` in the same write session, sequential, Sentry-guarded per-game try/except
- Created `tests/test_flaws_materialization.py` with 24 tests verifying the D-10 invariant: materialized rows exactly match the M+B subset of `classify_game_flaws` output

## Task Commits

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | game_flaws repository — bulk insert, delete, FlawRecord→row mapping | 60c70cec | app/repositories/game_flaws_repository.py |
| 2 | Import-pipeline classify + insert hook in eval_drain.py | 0e9c1a18 | app/services/eval_drain.py |
| 3 | Materialization round-trip test (Wave 0 stub) | 7b48a6be | tests/test_flaws_materialization.py |

## Files Created/Modified

- `/home/aimfeld/Projects/Python/flawchess/app/repositories/game_flaws_repository.py` — `flaw_record_to_row` (encoding maps _SEVERITY_INT/_TEMPO_INT/_PHASE_INT, phase guard, ValueError on inaccuracy), `bulk_insert_game_flaws` (pg_insert ON CONFLICT DO NOTHING, early return on empty), `delete_flaws_for_game` (scoped to game_id AND user_id)
- `/home/aimfeld/Projects/Python/flawchess/app/services/eval_drain.py` — Added imports, `_classify_and_insert_flaws` helper, and call site between `_apply_eval_results` and `_mark_evals_completed`
- `/home/aimfeld/Projects/Python/flawchess/tests/test_flaws_materialization.py` — 24 tests: `TestFlawRecordToRow` (unit), `TestBulkInsertGameFlaws` (DB), `TestMaterializationRoundTrip` (integration)

## Decisions Made

- `isinstance(result, GameNotAnalyzed)` raises `TypeError` at runtime because TypedDict is a plain dict. Used `"reason" in result` check (the runtime discriminant) and `isinstance(result, dict)` where ty narrowing was needed — consistent with the established `library_service.py` pattern.
- Hook insertion point: AFTER `_apply_eval_results` ensures `eval_cp` is committed and available to `classify_game_flaws` before classification (Pitfall 2 from RESEARCH). BEFORE `_mark_evals_completed` ensures flaw rows commit atomically with eval results in one transaction.
- GameNotAnalyzed discrimination in `_classify_and_insert_flaws` uses `"reason" in result` (dict key check) not `isinstance(result, GameNotAnalyzed)`, matching the runtime TypedDict semantics.

## Deviations from Plan

**1. [Rule 1 - Bug] isinstance(GameNotAnalyzed) replaced with "reason" in result check**

- **Found during:** Task 2 (`_classify_and_insert_flaws` implementation)
- **Issue:** `isinstance(result, GameNotAnalyzed)` is flagged as a `TypeError` by `ty` because `TypedDict` cannot be used as the second argument to `isinstance` — TypedDicts are plain dicts at runtime.
- **Fix:** Changed to `"reason" in result` dict key check (the established discriminant pattern from `library_service.py`); type narrowing in tests uses `isinstance(result, dict)`.
- **Files modified:** `app/services/eval_drain.py`, `tests/test_flaws_materialization.py`
- **Verification:** `uv run ty check app/ tests/` exits 0; all tests pass.
- **Committed in:** 0e9c1a18 (Task 2), 7b48a6be (Task 3)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in TypedDict isinstance check)
**Impact on plan:** Necessary for correct runtime behavior and ty compliance. No scope creep.

## Issues Encountered

None beyond the TypedDict isinstance deviation documented above.

## Known Stubs

None — all three outputs are fully functional: the repository provides production-ready insert/delete/mapping, the hook runs in the live import pipeline, and the test suite verifies the D-10 invariant against real DB rows.

## Threat Flags

No new network endpoints or auth paths introduced. The T-108-03, T-108-04, T-108-05 mitigations from the plan's threat model are fully implemented:
- T-108-03: Hook only processes game_ids from the authenticated eval-drain batch; rows stamped with `game.user_id`.
- T-108-04: Per-game try/except + Sentry capture + continue — one bad classify cannot abort the batch.
- T-108-05: `flaw_record_to_row` derives user_id from `game.user_id`; positions loaded scoped to `game.user_id` in `_classify_and_insert_flaws`.

## Next Phase Readiness

- `game_flaws_repository.py` is ready for Plans 108-03..08 (library service migration, backfill script, frontend)
- `flaw_record_to_row` is the single FlawRecord→row mapping for all write paths (D-10 invariant)
- Import hook materializes M+B flaws for all new analyzed games going forward
- The test suite (28 tests total with Plan 01's model tests) provides a green baseline for downstream plans

## Verification

```
uv run pytest tests/test_flaws_materialization.py tests/test_game_flaws_model.py -x  → 28 passed
uv run ty check app/ tests/                                                           → All checks passed!
```

## Self-Check: PASSED
