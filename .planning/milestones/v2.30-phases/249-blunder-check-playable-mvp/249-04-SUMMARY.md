---
phase: 249-blunder-check-playable-mvp
plan: 04
subsystem: blunder-check
tags: [blunder-check, grading, timer, fastapi, drill, beta-gate]
status: complete

requires:
  - phase: 249-02
    provides: tables, beta router, insert_session, repository read paths
  - phase: 249-03
    provides: composed windows with key_uci / move_ucis snapshot, compose_windows
provides:
  - app/services/blunder_check_grading.py (grade_answer state machine, timer ceiling, window move helpers, better-move graded set)
  - start_window / answer_prompt / finish_session in app/services/blunder_check_service.py
  - POST /api/blunder-check/sessions/{id}/windows/{position}/start, .../answers, /sessions/{id}/finish
  - wire schemas for prompts, answers, better-move task and the session result
affects: [249-05, 249-06, 249-07, phase-251]

tech-stack:
  added: []
  patterns:
    - "One API call per answer (D-16): the next arrow and the reply exist only in the response to the previous grade"
    - "Pre-inserted answer row + claiming UPDATE ... WHERE answered_at IS NULL, plus a row-locked window (SELECT ... FOR UPDATE) so concurrent answers serialize"
    - "Router _guarded() wrapper: commit, 404/409 mapping, Sentry capture only for unexpected exceptions"
    - "Tests build deterministic sessions with insert_session + NewWindow from seeded games and drive time through app.dependency_overrides[dev_now_utc]"

key-files:
  created:
    - app/services/blunder_check_grading.py
    - tests/services/test_blunder_check_grading.py
    - tests/routers/test_blunder_check_drill.py
  modified:
    - app/services/blunder_check_service.py
    - app/repositories/blunder_check_repository.py
    - app/routers/blunder_check.py
    - app/schemas/blunder_check.py

key-decisions:
  - "The window row is locked FOR UPDATE on the answer path; the claiming UPDATE is the second line of defence. Without both a concurrent double submit awarded twice (mutation-checked)"
  - "The stored `answer` column holds the SUBMITTED kind, `result` holds the graded verdict; a late 'blunder' is stored as answer=blunder, result=timeout_blunder"
  - "The opponent reply is returned when the window continues or clears, and withheld after caught/missed/false_alarm (the solution endpoint of plan 05 reveals it)"
  - "A restart of a started window re-derives the open prompt from answer rows and keeps the original prompted_at; timer_remaining_ms never includes the animation allowance (D-18)"
  - "finish_session treats an unknown/foreign session as 404 via an empty user-scoped window list (every session has >= 1 window)"

patterns-established:
  - "Wire literals (AnswerKindWire, AnswerResultWire, OutcomeName) are mirrored once in the grading module with enum maps in both directions"

requirements-completed: [D-10, D-12, D-13, D-14, D-16, D-17, D-18]

actuals:
  tokens: 36000
  tasks: 3
  commits: 4
plan_head_before: 97872ff98c86029e70428e7a3a439513b0caac95
plan_head_after: a6adc06a27ab78db5067d4e2c9a5fc63f3735089
---

# Phase 249 Plan 04: Server-graded blunder-check drill Summary

A beta user can start a window, answer each prompt "safe", "blunder" or "timeout", and have the server grade it against the secret key (points, forfeits, timeouts, the better-move task on a caught blunder), then finish the session with points, points possible and Score %.

## Tasks

1. **Task 1 (tracer)**, commit `d84693741`: grading module, repository drill queries, `start_window` / `answer_prompt`, the start and answers routes, schemas, and a tracer test that starts a window and catches a position-1 blunder (+3, `better_move` with the pre-blunder FEN and the window key). Verified end to end before expansion.
2. **Task 2 (TDD)**, RED `4bb18929f`, GREEN `b38409d46`: 29 pure grading tests and 18 router tests (all six results, forfeits, timeout paths, false alarm leaves no blunder-ply row and the composer can pick it again, ceiling vs reload timing, payload key sets and recursive forbidden-key scan, double submit sequential and concurrent, prompt/window order, IDOR, request bounds). RED failed only on the window-order test (the one behavior Task 1 did not implement); GREEN added `earlier_windows_ended` and the `previous_window_open` guard.
3. **Task 3**, commit `a6adc06a2`: `windows_for_session`, `complete_session`, `finish_session`, the finish route and tests (4 of 10 points = 40 %, the unreached blunder's 3 + 2 counted as possible; `windows_open` 409; idempotent re-finish; IDOR 404; GET open is null afterwards and a new POST composes a fresh session).

## Verification

- `uv run pytest` on grading, drill router, sessions router, repository and selection suites: 87 passed.
- `ruff format` / `ruff check .` / `ty check app/ tests/ scripts/` clean; `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Mutation checks (each reverted afterwards, diff confirmed clean): removing both the window row lock and the claiming `answered_at IS NULL` guard fails the concurrent double-submit test; disabling the ceiling in `effective_answer` fails the unit and router ceiling tests; replacing the frozen points-possible sum with points scored fails the finish test (a first, weaker mutation did not fail and was replaced).

## Deviations from Plan

### Auto-fixed / judgement calls

**1. [Rule 2 - Correctness] Row lock on the answer path**
- **Issue:** the plan's claiming UPDATE alone leaves the forfeit computation reading `window.points_scored` before the claim; a concurrent same-prompt submit could compute from a stale read.
- **Fix:** `get_window_for_user(..., for_update=True)` on the answer route serializes concurrent answers; the loser then sees the advanced prompt and gets 409 `stale_prompt`.
- **Files:** app/repositories/blunder_check_repository.py, app/services/blunder_check_service.py

**2. [Scope note] `earlier_windows_ended` was withheld from the tracer commit on purpose**
- It is Task 2's behavior; keeping it out of Task 1 let the RED test fail for a real reason. Net result matches the plan.

**3. Additive repository nothing else:** `windows_for_session` doubles as the existence check for `finish_session` (no separate session getter was added).

The unit-test RED run was green for the grading table (the module already existed from Task 1); the only RED failure was the order guard. Recorded here rather than hidden.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-249-10 (payload secrecy: exact key sets, recursive forbidden-key scan, reply only after its answer), T-249-11 (claim guard + row lock, concurrent test), T-249-12 (ceiling from server `prompted_at`, restart keeps the stamp), T-249-13 (every lookup joins the caller's user_id, second beta user gets 404), T-249-14 (`stale_prompt`, `previous_window_open`) are mitigated and tested.

## Hand-off notes for plan 05

- Wire contract is in `app/schemas/blunder_check.py`; plan 06 mirrors it in TypeScript. Conflict `detail` strings: `window_ended`, `previous_window_open`, `session_closed`, `not_started`, `stale_prompt`, `windows_open`.
- A caught window ends with `outcome = CAUGHT`, `better_move_*` columns still NULL, `points_scored` including the +3. The better-move endpoint must not require an open window; use `get_window_for_user` and check `outcome == CAUGHT` and `better_move_at IS NULL`.
- `better_move_graded_moves` (grading module) is the single derivation for the task and should be reused when plan 05 resolves the played move.
- The service never returns the reply after a caught/missed/false-alarm answer; the solution endpoint should reveal it from the window snapshot (`move_ucis` holds the reply when the game continued).
- Test helpers: `_setup`, `_Spec`, `_Clock` in `tests/routers/test_blunder_check_drill.py` build deterministic sessions from seeded games; reusable by copying or promoting to `tests/blunder_check_seed.py`.

## Self-Check: PASSED

- Files exist: grading module, both test files, service/repository/router/schema edits.
- Commits `d84693741`, `4bb18929f`, `b38409d46`, `a6adc06a2` are ancestors of HEAD.
