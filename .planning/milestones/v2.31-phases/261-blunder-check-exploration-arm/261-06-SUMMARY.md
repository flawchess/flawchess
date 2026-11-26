---
phase: 261-blunder-check-exploration-arm
plan: 06
subsystem: blunder-check
tags: [solution, feedback, wire, exploration, snapshot]

requires:
  - phase: 261-blunder-check-exploration-arm
    provides: blunder_feedback / BlunderFeedbackData, the window snapshot columns (plan 01); the exploration arm (plan 03); the frontend feedback type (plan 04)
provides:
  - BlunderSolution.feedback on the wire (BlunderFeedback, BlunderTypeLineWire), built from the window's serve-time snapshot
  - end-to-end HTTP proof of an exploration window (compose, start, answer, solution), counts-as-normal and no pre-answer leak
affects: [261-07 release and prod check]

actuals:
  tokens: 11000
  tasks: 2
  commits: 2
plan_head_before: da91fc27c181ffbc724b76753e9db1fdac3bf5d3
plan_head_after: bbe69598562ba7f0f1cb6c138727a0db63f9c715

tech-stack:
  added: []
  patterns:
    - "solution feedback reads the window snapshot only, never game_flaws"

key-files:
  created:
    - tests/routers/test_blunder_check_exploration.py
  modified:
    - app/schemas/blunder_check.py
    - app/services/blunder_check_service.py
    - app/routers/blunder_check.py
    - tests/routers/test_blunder_check_solution.py

key-decisions:
  - "feedback is the last field of BlunderSolution and is null (not absent) for windows without a snapshot, matching the frontend type field for field"
  - "FalseAlarmSolution and HerringSolution are untouched, so D-05 holds structurally"

requirements-completed: [SEED-261121-t50, D-04, D-05, D-06]

status: complete
completed: 2026-11-22
---

# Phase 261 Plan 06: Solution feedback on the wire Summary

**A caught or missed blunder window's solution now carries `feedback {score, type_line, hard_to_catch}` from its serve-time snapshot (null for pre-phase windows, absent from false alarms and herrings), and an exploration window is proven end to end over HTTP including points, the weekly aggregate and the absence of any arm or score before the answer.**

## Accomplishments

- Schema: `BlunderTypeLineWire`, `BlunderFeedback`, `BlunderSolution.feedback: BlunderFeedback | None` as the last field. The shape matches `frontend/src/types/blunderCheck.ts` field for field.
- Service: `BlunderSolutionData.feedback`, set in `_blunder_solution` by `blunder_feedback(...)` over the window's `facepalm_score / facepalm_loss / facepalm_missed / type_swing / type_mate`. The live `game_flaws` row is never read, so the value survives a game delete and a score refit.
- Router: `_feedback_schema()` and `feedback=_feedback_schema(data.feedback)` in `_blunder_solution_schema`.
- Tracer tests (`tests/routers/test_blunder_check_exploration.py`): with the slot draw forced to an own exploration plan, a below-cut (0.3) blunder is served, missed over HTTP, and its solution shows `score` about 0.3, `hard_to_catch` true, `type_line` null (the seed stores no engine line); the window row has `selection_arm = EXPLORATION`. A caught exploration window awards `BLUNDER_POINTS`, and `fetch_week_bc_aggregates` for the clock's week counts the user's points equal to the window's `points_scored`. A deep key scan of the POST /sessions, start and answer bodies finds none of `arm, selection_arm, arm_probability, facepalm_score, feedback, type_line, hard_to_catch`.
- Contract tests (`tests/routers/test_blunder_check_solution.py`): `_BLUNDER_KEYS` gains `feedback`; legacy window gives `feedback: null`; caught and missed both return the snapshot feedback (0.95, allowed_material, not hard to catch); mate plus hard to catch (0.42, missed_mate); a low-score false alarm keeps exactly `_FALSE_ALARM_KEYS` (D-05); feedback is unchanged after the game is deleted while `game_id` becomes null.

## Task Commits

1. Task 1 (tracer): `c326f67f0` feat, schema, service, router, the three end-to-end tests, `_BLUNDER_KEYS` gains "feedback" (done here so the existing exact key-set test stayed green at this commit)
2. Task 2: `bbe695985` test, five solution contract tests

Mutation check: replacing `type_mate=window.type_mate` with `False` in the service made `test_solution_feedback_mate_and_hard_to_catch` fail; restored.

## Deviations from Plan

None - plan executed exactly as written. Notes: the one-line `_BLUNDER_KEYS` edit planned for Task 2 landed in the Task 1 commit to avoid a red commit. The new exploration module defines its own `clock` fixture (importing the drill module's fixture trips ruff F811, the same reason the solution module redefines it).

## Known Stubs

None.

## Threat Flags

None. `FalseAlarmSolution` is unchanged (T-261-15), solution reads stay scoped by `get_window_for_user` (T-261-16), and start, answer and session payloads were not touched and are deep-scanned (T-261-17).

## Verification

- `uv run pytest tests/routers/test_blunder_check_exploration.py`: 3 passed
- `uv run pytest tests/routers/test_blunder_check_solution.py`: 38 passed
- `uv run pytest -n auto tests/routers/ -k "blunder_check or train"`: 292 passed
- `uv run ruff format --check`, `ruff check .`, `uv run ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean

## Self-Check: PASSED

- `tests/routers/test_blunder_check_exploration.py` exists; commits `c326f67f0` and `bbe695985` are ancestors of HEAD.
