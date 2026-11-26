---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 08
subsystem: backend-repositories
tags: [facepalm-score, blunder-check, drill, query-time-expression, test-seeding]
requires:
  - phase: 254-02
    provides: "facepalm_expr(lam) and tests/facepalm_seed.py (facepalm_fact_columns, SEED_FACEPALM_MARGIN)"
  - phase: 254-15
    provides: "FACEPALM_DRILL_LAMBDA and the lam-aware score twins"
  - phase: 254-06
    provides: "R1 live on prod, facts copied and parity checked"
provides:
  - "Drill own-game and foreign-game EXISTS probes and load_blunder_flaws on facepalm_expr(FACEPALM_DRILL_LAMBDA)"
  - "SeedBlunder.facepalm_target seeding facts instead of a stored score"
affects: [254-18, 254-09, 254-10]
tech-stack:
  added: []
  patterns:
    - "One bound query-time expression selected as facepalm_score and used in the WHERE (same object)"
    - "Drill tests seed facts via facepalm_fact_columns with band-edge margins, never the exact cut"
key-files:
  created: []
  modified:
    - app/repositories/blunder_check_repository.py
    - tests/blunder_check_seed.py
    - tests/repositories/test_blunder_check_repository.py
    - tests/services/test_blunder_check_selection.py
key-decisions:
  - "The flaw_owner_id pin on the own-game probe and correlate_except are kept untouched (T-254-24); only the stored-column comparison was replaced"
  - "The loader labels the expression facepalm_score in the same column position, so BlunderFlawRow(*row[1:]) and BlunderFlawRow's shape are unchanged"
  - "Non-qualifying drill fixtures moved from FACEPALM_SCORE_MIN - 0.2 to FACEPALM_SCORE_MIN - SEED_FACEPALM_MARGIN so the tests sit at the band edge on both sides"
requirements-completed: [D-01, D-03, D-12]
coverage:
  - id: D1
    description: "Own-game pick qualifies a blunder through facepalm_expr(FACEPALM_DRILL_LAMBDA): at MIN + margin picked, at MIN - margin and unscored not"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py#test_own_pick_uses_drill_expression"
        status: pass
    human_judgment: false
  - id: D2
    description: "Foreign pick uses the expression with the same split and returns game ids only (no owner data)"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py#test_foreign_pick_uses_drill_expression"
        status: pass
    human_judgment: false
  - id: D3
    description: "Loader score equals facepalm_expr(FACEPALM_DRILL_LAMBDA) of the row and the seeded target, shape unchanged"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py#test_load_blunder_flaws_returns_expression_score"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py#test_facepalm_loader_and_judge_keep_only_qualifying"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every drill suite and the full backend suite pass on the new readers"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "uv run pytest -n auto -q (6566 passed, 19 skipped)"
        status: pass
    human_judgment: false
duration: 30 min
completed: 2026-11-15
status: complete
plan_head_before: 26a1bbee61de16765d5469aa59d9dfcf403654f3
plan_head_after: 2134db0c5946dca9fa61fdffad4bf6a7e77b3ea4
commits: 2
actuals:
  tokens: 4500
  tasks: 2
  commits: 2
---

# Phase 254 Plan 08: Drill selection on the facepalm expression Summary

**The blunder-check drill now picks (own and foreign games) and loads qualifying blunders through `facepalm_expr(FACEPALM_DRILL_LAMBDA) >= FACEPALM_SCORE_MIN` instead of the stored score column, with drill tests seeding facts.**

## Performance

- **Duration:** about 30 min (estimate; start time not captured), dominated by a 15 min full suite run
- **Completed:** 2026-11-15
- **Tasks:** 2 (a tracer and an auto task)
- **Files modified:** 4

## Accomplishments

- `_unserved_qualifying_blunder_exists` compares `facepalm_expr(FACEPALM_DRILL_LAMBDA)` to `FACEPALM_SCORE_MIN` in both the own-game and the foreign-game EXISTS; the `flaw_owner_id` pin, its docstring and `correlate_except` are unchanged.
- `load_blunder_flaws` binds the expression once, selects it `.label("facepalm_score")` in the same column position and filters on the same object, so `BlunderFlawRow` and its unpacking are unchanged. NULL (unscored rows, opponent rows without facts) drops out by SQL semantics.
- `SeedBlunder.facepalm_score` became `facepalm_target`; the seed inserts `facepalm_fact_columns(target, lam=FACEPALM_DRILL_LAMBDA)`. Every drill test that seeded a stored score now seeds facts.
- New tests: `test_own_pick_uses_drill_expression`, `test_foreign_pick_uses_drill_expression` (also asserts only `int` game ids come back), `test_load_blunder_flaws_returns_expression_score`.

## Task Commits

1. **Task 1 (tracer): drill selection on the expression with facts-seeded blunders** - `6114f91bc` (feat)
2. **Task 2: remaining drill tests on facts** - `2134db0c5` (test)

Tracer gate: the tracer `<verify>` is automated-only, so it was re-run end to end (20 passed in the repository file) before the expansion task.

## Files Created/Modified

- `app/repositories/blunder_check_repository.py` - both EXISTS probes and the loader on `facepalm_expr(FACEPALM_DRILL_LAMBDA)`, docstrings updated
- `tests/blunder_check_seed.py` - `facepalm_target`, facts seeding
- `tests/repositories/test_blunder_check_repository.py` - call sites on facts, band-edge margins, three new tests
- `tests/services/test_blunder_check_selection.py` - the facepalm gate test on facts; `LOW_SCORE_GAP` removed in favour of `SEED_FACEPALM_MARGIN`

## Decisions Made

See key-decisions. The router and candidates drill tests needed no change: they use `SeedBlunder` defaults or `BlunderFlawRow`/`_Flaw` values, as the plan expected. All 155 tests across the six drill suites passed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Prod EXPLAIN of the own-pick EXISTS (T-254-24) is plan 10's job and needs prod access, not done here.
- No dev database state was changed; Alembic head stays `a7d2c9e1b254`.

## Known Stubs

None.

## Threat Flags

None. T-254-24 mitigated (the `flaw_owner_id` pin is still in the own-game probe, 5 references remain); T-254-42 mitigated (the foreign pick still returns game ids only, asserted by `test_foreign_pick_uses_drill_expression`; the expression adds no selected column to the EXISTS probe).

## Next Phase Readiness

The drill is on the expression. Plan 18 (library readers) and plan 09 (operator scripts) follow on the same branch. Shipping needs plan 10's prod EXPLAIN of the own-pick probe.

## Self-Check: PASSED

Commits `6114f91bc` and `2134db0c5` are on HEAD. Verified: acceptance greps (`facepalm_expr(FACEPALM_DRILL_LAMBDA)` present, `flaw_owner_id` present, `GameFlaw.facepalm_score` count 0 in the repository, `SeedBlunder(...facepalm_score=` count 0 in tests), six drill suites 155 passed, `uv run ty check app/ tests/ scripts/` clean, `ruff check` clean, `check_function_size.py app/ --fail-over-depth 4` clean, full `uv run pytest -n auto -q` 6566 passed / 19 skipped.
