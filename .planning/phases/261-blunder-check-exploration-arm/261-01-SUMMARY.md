---
phase: 261-blunder-check-exploration-arm
plan: 01
subsystem: blunder-check
tags: [postgres, alembic, sqlalchemy, facepalm, selection, tdd]

requires:
  - phase: 259-facepalm-first-principles-refit
    provides: quiet_line_facts, loss_by_depth, gain_by_depth, the five stored score inputs, facepalm_expr
  - phase: 257-facepalm-rate-library-stats
    provides: facepalm_type_of (D-02 type rule)
provides:
  - serve-time record on blunder_check_windows (arm, P(arm), score snapshot, five inputs, type-line facts)
  - WindowArm, WindowSelectionRecord, NewWindow.selection, loader returning the five inputs
  - blunder_check_feedback module (type_line_facts at serve time, blunder_feedback at read time)
  - EXPLORATION_SHARE, arm_probability(), SlotPlan.arm, TYPE_LINE_MIN_SWING, HARD_TO_CATCH_SCORE_BELOW
affects: [261-03 exploration draw, 261-06 wire and solution feedback, calibration script]

actuals:
  tokens: 13000
  tasks: 3
  commits: 4
plan_head_before: b9ebe962a4065cb8b7151f20c60220ac91d553c8
plan_head_after: 2a01e03f9fcff03a0090e2fa1d3f6ecae5545e12

tech-stack:
  added: []
  patterns:
    - "serve-time snapshot of a query-time score on the window row, refit-proof"
    - "type-line facts stored raw (swing + mate flag), floor applied at read time"

key-files:
  created:
    - alembic/versions/20261130_120000_a7c3e5f9b261_phase_261_window_selection_snapshot.py
    - app/services/blunder_check_feedback.py
    - tests/services/test_blunder_check_feedback.py
    - tests/repositories/test_blunder_check_window_snapshot.py
  modified:
    - app/models/blunder_check.py
    - app/repositories/blunder_check_repository.py
    - app/services/blunder_check_rules.py
    - app/services/blunder_check_selection.py
    - tests/services/test_blunder_check_selection.py

key-decisions:
  - "Type-line storage is the raw swing plus a mate flag (not a frozen enum): the 2-point floor stays a read-time constant"
  - "arm_probability stores P(arm) among blunder slots (0.2 exploration, 0.8 main)"
  - "A blunder window whose flaw row lacks a score input is served without a record rather than failing session start"
  - "SlotPlan.arm defaults to main so every existing two-argument SlotPlan stays a main slot; plan 03 sets the arm"

patterns-established:
  - "Snapshot CHECKs are all-or-nothing per record and tie the herring case to a NULL arm"

requirements-completed: [SEED-261121-t50, D-04, D-06, D-08, D-09, D-12]

coverage:
  - id: D1
    description: "Composed blunder windows store arm, P(arm), the score and its five inputs; herring windows store none"
    requirement: "SEED-261121-t50"
    verification:
      - kind: integration
        ref: "tests/services/test_blunder_check_selection.py#test_blunder_window_records_the_main_arm_snapshot"
        status: pass
      - kind: integration
        ref: "tests/services/test_blunder_check_selection.py#test_herring_window_records_nothing"
        status: pass
    human_judgment: false
  - id: D2
    description: "Type-line facts follow the Phase 259 walk at the deepest settled odd depth on the facepalm-type side only; mate only when the stored line reaches it"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "tests/services/test_blunder_check_feedback.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "blunder_feedback applies the 2-point type-line floor and the 0.5 hard-to-catch cut at read time"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "tests/services/test_blunder_check_feedback.py#test_hard_to_catch_is_a_score_below_the_cut"
        status: pass
    human_judgment: false
  - id: D4
    description: "The migration adds only nullable columns and CHECKs, round-trips, and the CHECKs reject malformed records"
    verification:
      - kind: integration
        ref: "tests/repositories/test_blunder_check_window_snapshot.py"
        status: pass
      - kind: other
        ref: "uv run alembic downgrade -1 && uv run alembic upgrade head && uv run alembic check"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-11-22
status: complete
---

# Phase 261 Plan 01: Serve-time selection record Summary

**Every composed blunder window now stores its arm, P(arm), a refit-proof snapshot of the facepalm score with its five inputs, and the deepest-settled type-line swing and mate flag, with eight CHECKs guarding the record and a pure read-time feedback decision (type line, hard to catch) for plan 06.**

## Performance

- **Duration:** about 40 min
- **Tasks:** 3 (tracer, TDD, constraint tests)
- **Files:** 4 created, 5 modified

## Accomplishments

- Migration `a7c3e5f9b261` adds ten nullable columns and eight validated CHECKs to `blunder_check_windows` (literal SQL, no native ENUM, no app imports). `alembic check` is clean and `downgrade -1` / `upgrade head` round-trips.
- `WindowArm` IntEnum, `WindowSelectionRecord` and `NewWindow.selection`; `load_blunder_flaws` now returns the five score inputs (`BlunderFlawRow` grew five fields, selected in the same positional order).
- `compose_windows` writes the record through `_selection_record` / `_type_line_facts_for` in `blunder_check_selection.py`; every window is main until plan 03 sets the arm on `_Filled`.
- `app/services/blunder_check_feedback.py`: `type_line_facts` (serve time, Phase 259 functions only) and `blunder_feedback` (read time). Mate beats material, a lone non-mating best move gives no missed swing (D-12), the type side is `facepalm_type_of(loss, missed)` and `window_case` is never read.
- Constants in `blunder_check_rules.py`: `EXPLORATION_SHARE = 0.2`, `arm_probability()`, `SlotArm`, `SlotPlan.arm` (default main), `TYPE_LINE_MIN_SWING = 2`, `HARD_TO_CATCH_SCORE_BELOW = 0.5`. `draw_slot_plan` is untouched (the coin flip is plan 03).

## Task Commits

1. Task 1 (tracer): `ccf4312df` feat, migration, model, repository, rules, feedback `type_line_facts`, selection wiring, two selection tests
2. Task 2 RED: `8cbd2a51c` test, 24 feedback tests (collection fails on the missing constants)
3. Task 2 GREEN: `ffbeb497a` feat, `blunder_feedback`, `TYPE_LINE_MIN_SWING`, `HARD_TO_CATCH_SCORE_BELOW`
4. Task 3: `2a01e03f9` test, valid round trip plus nine CHECK rejections

Mutation check on Task 2: flipping `<` to `<=` on the hard-to-catch cut and `>=` to `>` on the swing floor made three tests fail; restored.

## Decisions Made

See `key-decisions`. The two recorded planning assumptions (raw swing plus mate flag; P(arm) among blunder slots) were kept as planned.

## Deviations from Plan

None - plan executed exactly as written. One Task 3 addition inside scope: a ninth rejection case for `ck_blunder_check_windows_type_swing` (the plan listed the other eight), so all eight CHECKs are proven.

Notes, not deviations: the nesting-depth gate stays at depth 4 (`check_function_size` reports no breaches); the test fixtures `OWNER_MISS_FIXTURES` games 817357 and 820181 give missed swings 3 and 5.

## Issues Encountered

None. `uv sync --locked --group maia-inference` avoided the three phantom ty errors.

## Known Stubs

None.

## Threat Flags

None. No wire field was added (T-261-01 holds: the record is internal, plan 06 exposes post-end feedback only and never the arm).

## Verification

- `uv run alembic upgrade head && uv run alembic check`: "No new upgrade operations detected."
- `uv run alembic current`: `a7c3e5f9b261 (head)`
- `uv run pytest -n auto` over the plan's regression set (selection, candidates, repository, rules, drill / solution / sessions routers, feedback, snapshot): 246 passed
- `uv run ty check app/ tests/ scripts/`, `ruff check`, `ruff format --check`, `check_function_size.py app/ --fail-over-depth 4`: clean

## Next Phase Readiness

Plan 03 sets `_Filled.arm` from the slot's arm and adds the no-cut draw; plan 06 reads `blunder_feedback(...)` from the window columns. Ready for both.

## Self-Check: PASSED

- Created files exist (migration, feedback module, both new test modules).
- Commits `ccf4312df`, `8cbd2a51c`, `ffbeb497a`, `2a01e03f9` are ancestors of HEAD.
