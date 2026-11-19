---
phase: quick-261119-x7t
plan: 01
subsystem: blunder-check
tags: [blunder-check, resume, answer-ceiling, ready-gate, race-safety]
requires: []
provides:
  - "start_window settles a stale open prompt as a timeout and reopens on a mid-sequence Ready gate"
  - "WindowStartResponse.outcome for ended-window payloads"
  - "is_past_ceiling, the single home of the answer-ceiling comparison"
affects:
  - app/services/blunder_check_service.py
  - frontend/src/lib/blunderCheckDrill.ts
tech-stack:
  added: []
  patterns:
    - "gate = started window with no open prompt row (no flag or column)"
    - "start/begin/answer serialize on the window row lock (for_update=True)"
key-files:
  created: []
  modified:
    - app/services/blunder_check_grading.py
    - app/services/blunder_check_service.py
    - app/repositories/blunder_check_repository.py
    - app/schemas/blunder_check.py
    - app/routers/blunder_check.py
    - tests/routers/test_blunder_check_drill.py
    - tests/services/test_blunder_check_grading.py
    - CHANGELOG.md
    - frontend/src/types/blunderCheck.ts
    - frontend/src/lib/blunderCheckDrill.ts
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx
    - frontend/src/lib/__tests__/blunderCheckDrill.test.ts
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx
decisions:
  - "Gate before move N is a started window with no outcome and no open prompt row; move N = last answered move_index + 1"
  - "Server-settled rows store answer TIMEOUT, client_elapsed_ms NULL, server_elapsed_ms the real elapsed time"
  - "Ended resume reuses WindowStartResponse with a new outcome field; the better-move resume now reports outcome caught"
  - "begin_window never settles; start_window is the only resume path"
status: complete
completed: 2026-11-20
commits: 3
plan_head_before: 7de2b5dd6138e2eb1cc09dcf51a2ceb40782014b
plan_head_after: 48316651d58bab1886df293d48d11e8f5c6d89f6
actuals:
  tokens: 14000
  tasks: 3
  commits: 3
---

# Phase quick-261119-x7t Plan 01: Blunder check, settle a stale open prompt on resume Summary

A resume that finds an open blunder-check prompt more than 17 s past its `prompted_at` now grades it as a timeout (normal rules, NULL client time) and reopens the sequence on a Ready gate before the next move, instead of returning a dead 0 ms clock that the client auto-submitted.

## What changed

**Server (commit 6fcee6901)**
- `is_past_ceiling` in the grading module; `effective_answer` uses it, so the stale check and the answer ceiling cannot drift.
- `_grade_row` (the single `grade_answer` call, shared by `answer_prompt` and the settle), `_settle_stale_prompt` (carries the bug-fix comment citing 261119-x7t), `_next_move_index`, `_ended_window_start` (generalized from `_resume_better_move`), `_resume_after_settle`.
- `_window_start` builds the gate at any move index (no open row), takes `window_points` explicitly; the old "rows but none open raises window_ended" branch is gone (that state is now the mid-sequence gate; `_next_move_index` keeps the defensive check).
- `start_window` and `begin_window` load the window with `for_update=True`. `begin_window` inserts the NEXT move's prompt (never move 1 after a settle) and never settles.
- `WindowStart.outcome` / `WindowStartResponse.outcome` (new required field); the better-move resume reports `caught`. `claim_answer` accepts `client_elapsed_ms=None`. No migration.

**Client (commit 18bfaf6bf)**
- `betterMoveResumed` generalized to `endedWindowResumed`; a non-null `outcome` without a better-move task goes `solution_loading` then `solution`.
- `windowFromServer` shows lead-in + answered moves + replies on a mid-sequence gate; a fresh gate still shows nothing. `ReadyGateBubble` takes the gate's board FEN (prop renamed `startFen` to `fen`), so the turn sentence reads "It's your turn." mid-sequence.

**Tests and changelog (commit 48316651d)**
- Boundary, post-Ready reload, herring last move, session moving on, concurrent double resume, resume vs late answer, better-move `caught` outcome, no key-material leak; `is_past_ceiling` unit test; CHANGELOG `[Unreleased]` / `### Fixed` bullet.

## Mutation checks (done for real)
- Settle disabled (`_settle_stale_prompt` returns None at the top): the 3 Task 1 tests failed (gate, Ready-with-full-clock, ending settle). Restored.
- `start_window` row lock turned off (`for_update=False`): `test_stale_concurrent_double_resume_settles_once` and `test_stale_resume_racing_a_late_answer_grades_the_prompt_once` failed in 3 of 3 runs. Restored (service file verified identical to the committed version).

## Verification (all run, all green)
- `uv run ruff format app/ tests/ scripts/`: unchanged. `uv run ruff check . --fix`: clean. `uv run ty check app/ tests/ scripts/`: clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Backend blunder-check suites (drill, solution, grading): 117 passed serial (105 baseline + 12 new). All blunder-check test files under tests/repositories, tests/routers, tests/services: 258 passed with `-n auto`. (`tests/scripts/test_blunder_check_*` sit in an addopts-ignored directory and were not run.)
- Frontend: `blunderCheckDrill.test.ts` + `BlunderCheckTab.test.tsx` 110 passed (102 baseline + 8 new); `npm run lint` clean; `npm run build` (tsc -b + vite) clean; `npm run knip` reports no issues (two pre-existing configuration hints only).
- No Alembic change (`git ls-files -m alembic` empty).
- The full pre-merge gate (full suite, analysis/ ty check, frontend full test run) was NOT run; it is the orchestrator's integration step.

## Deviations from Plan

None. The plan executed as written. Production code needed no change after Task 3's tests.

Note: the task 1 and task 3 mutation checks were stricter than required (extra lock mutation, see above).

## Known Stubs

None.

## Threat Flags

None. The new `outcome` field exposes no key material; `test_stale_bodies_leak_no_key_material` asserts exactly `_START_KEYS` and no `_FORBIDDEN_KEYS` on both the gate and ended bodies.

## Self-Check: PASSED

- Commits 6fcee6901, 18bfaf6bf, 48316651d exist on `main` (3 commits since 7de2b5dd6).
- All modified files listed in the plan exist and carry the described changes.
