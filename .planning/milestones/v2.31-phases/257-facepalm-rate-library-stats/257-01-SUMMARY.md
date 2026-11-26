---
phase: 257-facepalm-rate-library-stats
plan: 01
subsystem: api
tags: [facepalm, sqlalchemy, pydantic, react, library-flaws]
status: complete

requires:
  - phase: 256-facepalm-refit-material-aggregated-over-depths
    provides: material_loss / material_missed and the shipped FACEPALM_MODEL the type rule reads
provides:
  - facepalm type twin (facepalm_type / facepalm_type_sql / facepalm_type_expr) on the model's loss and missed inputs
  - FACEPALM_STATS_MIN = 0.7, the library stats cut
  - FlawListItem.facepalm_type on GET /api/library/flaws (backend schema and TS mirror)
  - Flaws-card Facepalm chip tinted by type (teal missed win, crimson allowed loss)
  - typed facepalm seeds (facepalm_fact_columns(facepalm_type=...)) for later reader tests
affects: [257-02, 257-03, 257-04, 257-05]

actuals:
  tokens: 13400
  tasks: 2
  commits: 3
plan_head_before: cfc2337f1c7f4bde0ff323005713c6897430c50e
plan_head_after: 942f034724a63db824e0670d7750d3e979395a52
commits: 3

tech-stack:
  added: []
  patterns:
    - "Type twin pair on the score's own loss/missed inputs, lambda-free and coefficient-free, parity pinned by string equality"
    - "Reader nulls the SQL type with the score (type is NULL only for an unknown loss, score also for missing probabilities)"

key-files:
  created: []
  modified:
    - app/services/facepalm_score.py
    - app/services/blunder_check_rules.py
    - app/repositories/library_repository.py
    - app/schemas/library.py
    - frontend/src/types/library.ts
    - frontend/src/lib/facepalm.ts
    - frontend/src/components/library/FacepalmChip.tsx
    - frontend/src/components/library/FlawCard.tsx
    - tests/facepalm_seed.py
    - tests/services/test_facepalm_score.py
    - tests/services/test_facepalm_seed.py
    - tests/test_library_repository.py
    - tests/repositories/test_library_repository.py
    - tests/test_library_router.py
    - frontend/src/components/library/__tests__/FlawCard.test.tsx

key-decisions:
  - "D-02 type rule lives next to the score twin: allowed_loss when loss > 0 and loss >= missed, else missed_win, NULL only for an unknown loss"
  - "facepalm_type_sql retypes its CASE with type_coerce(..., String()) so ty accepts ColumnElement[str]"
  - "query_flaws nulls the type whenever facepalm_score is None (244 of 11,020 dev rows have a type but no score)"
  - "FACEPALM_STATS_MIN (0.7) is its own constant, pinned to the High preset bound 70 / 100.0"
  - "Missed-win chip border is the full teal, allowed-loss border the lower-alpha crimson (TacticMotifChip convention)"

patterns-established:
  - "Typed seed helper: facepalm_fact_columns(target, lam=..., facepalm_type=...) checks the Python type twin before returning"

requirements-completed: [D-01, D-02, D-07, D-08, D-09]

duration: 20 min
completed: 2026-11-20
---

# Phase 257 Plan 01: Facepalm type tracer and stats cut Summary

**Every scored blunder now has a facepalm type (missed win / allowed loss) computed in SQL from the model's own loss and missed inputs, returned by GET /api/library/flaws and shown as a teal or crimson tint on the Flaws-card chip; the 0.7 stats cut and typed test seeds are in place for plans 02 to 05.**

## Performance

- **Duration:** about 20 min
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files modified:** 15 (no new files)
- **Commits:** 3 (feat tracer, RED test, GREEN feat)

## Accomplishments

- D-02 type twin in `app/services/facepalm_score.py`: `FacepalmType`, `FACEPALM_TYPES`, `facepalm_type_of`, `facepalm_type` (Python), `facepalm_type_sql`, `facepalm_type_expr` (SQL), `facepalm_type_from_sql`; the GameFlaw column map is now one private helper shared by `facepalm_expr` and `facepalm_type_expr`.
- `query_flaws` adds `facepalm_type_expr().label("facepalm_type")` to the paged statement only; `_build_flaw_item` nulls the type with the score. `FlawListItem.facepalm_type` and the TS `FacepalmType` / `FlawListItem.facepalm_type` mirror it.
- `FACEPALM_TYPE_STYLE` in `frontend/src/lib/facepalm.ts`; `FacepalmChip` takes a required `type`; `FlawCard` renders the chip only when score and type are both non-null (D-09). Chip text unchanged (D-07).
- `FACEPALM_STATS_MIN = 0.7` in `app/services/blunder_check_rules.py`, test-pinned to `70 / _FACEPALM_PCT_SCALE` and different from `FACEPALM_SCORE_MIN`.
- Typed seeds: `facepalm_fact_columns(..., facepalm_type="missed_win" | "allowed_loss")` with `SEED_BEST_PROBS`, checked against the Python twin.
- Tests: SQL vs Python type parity over the depth-3 grid x every shape model, the aggregate-input grid, extreme rows, tie and no-material edge rows, and stored game_flaws facts; coefficient-invariance; router end-to-end; vitest tint assertions.

## Task Commits

1. **Task 1 (tracer): type in SQL, API payload, tinted chip** - `79782d47f` (feat)
2. **Task 2 RED: failing tests for the stats cut, typed seeds, null-type reader rule** - `c61c7a62c` (test)
3. **Task 2 GREEN: stats cut constant and typed seeds** - `942f03472` (feat)

## TDD Gate Compliance

- RED: `test(257-01)` commit `c61c7a62c`. `gsd_run check tdd-red-evidence` returned `RED_EVIDENCE_OK` (reason `target_test_failed`, JUnit format) for target `tests/services/test_facepalm_seed.py::test_seeded_type_and_target[allowed_loss-0.8]`. It failed with `TypeError: facepalm_fact_columns() got an unexpected keyword argument 'facepalm_type'`. Semantic assessment: the target executed and failed because the planned typed-seed behavior did not exist. Also red in that run: `test_facepalm_stats_min_is_the_high_preset_cut` (constant missing, assertion on `None == 0.7`), the other two seed cases and both `TestQueryFlawsFacepalmType` tests (same TypeError on the new keyword).
- GREEN: `feat(257-01)` commit `942f03472`; all of those pass.
- The type-parity tests were already green at RED time: the type twin itself was delivered by the Task 1 tracer, so they pin existing behavior rather than drive it. Mutation check: changing the SQL tie rule `loss >= missed` to `loss > missed` fails 28 of the `-k type` tests; restored afterwards.
- No REFACTOR commit.

## Decisions Made

See `key-decisions` above. No decisions beyond the plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing `_build_flaw_item` test callers**
- **Found during:** Task 1 (ty check)
- **Issue:** the new required keyword `facepalm_type` broke two direct `_build_flaw_item(...)` calls in `tests/repositories/test_library_repository.py`.
- **Fix:** passed `facepalm_type=None` at both call sites (kept the parameter required so a future caller cannot forget it).
- **Files modified:** `tests/repositories/test_library_repository.py`
- **Commit:** `79782d47f`

**2. [Plan path note] Two files named test_library_repository.py**
- The plan's `tests/test_library_repository.py` (holds `_seed_game_flaw`, `query_flaws` tests) is the one extended in Task 2; `tests/repositories/test_library_repository.py` is a separate file that only needed the Rule 3 keyword fix above.

**Total deviations:** 1 auto-fixed (Rule 3), 1 path clarification. **Impact:** none on scope.

## Issues Encountered

- A first mutation-check command also contained a `git checkout -- <file>`; the permission classifier denied the whole command before anything ran, so no work was lost. The check was redone with a scratch-copy restore.

## Known Stubs

None.

## Threat Flags

None. The type column joins the existing `query_flaws` statement, which keeps `GameFlaw.user_id == user_id` and `player_only_gate`; no new endpoint, parameter or join (T-257-01). Parity tests cover T-257-02.

## Intermediate State (as planned)

Only the Flaws-card chip is tinted. The analysis move-list mini-chip and the eval-chart tooltip still use the neutral `FACEPALM_CHIP*` colours, and the popover does not name the type yet; plan 02 puts the type on `FlawMarker`, plan 03 tints those surfaces (D-10) and deletes the neutral constants.

## Verification Run

- `uv run pytest` on facepalm_score, facepalm_seed, both library repository files, library router, eval chart service: 447 passed.
- `uv run ty check app/ tests/ scripts/`, `uv run ruff check .`, `uv run ruff format --check`, `check_function_size.py --fail-over-depth 4`: clean.
- Frontend: `npm run lint`, `npm run build` (tsc), `npm run knip` clean; `npm test -- --run src/components/library` 284 passed. Vitest mutation check: swapping the missed-win colour fails the missed-win tint test.

## Self-Check: PASSED

- FOUND: app/services/facepalm_score.py, frontend/src/lib/facepalm.ts, tests/facepalm_seed.py (all modified files exist)
- FOUND commits: 79782d47f, c61c7a62c, 942f03472
- Acceptance greps: `def facepalm_type_sql` 1, `def facepalm_type_expr` 1, `facepalm_type_expr().label("facepalm_type")` 1, `^FACEPALM_STATS_MIN: float` 1, `class TestQueryFlawsFacepalmType` 1
