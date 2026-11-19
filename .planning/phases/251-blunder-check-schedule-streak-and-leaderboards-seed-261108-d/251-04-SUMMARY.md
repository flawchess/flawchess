---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 04
subsystem: api
tags: [train, settings, blunder-check, streak, fastapi, sqlalchemy]

requires:
  - phase: 251-01
    provides: train_settings blunder-check columns, dated blunder-check sessions, complete_session -> bool
  - phase: 251-12
    provides: apply_day_completion (idempotent via streak_credited_on), day_is_complete both-modes rule
  - phase: 251-03
    provides: level_fallback_elo and puzzle_cooled_pairs inputs for composition
provides:
  - "PUT /train/settings edits both session sizes (puzzles 0..50, blunder check 0..30) and the stored level at any time"
  - "train_settings_service.apply_settings_update: settle, upsert, BC resize, puzzles-off close, day completion"
  - "resize_open_session / append_windows / compose_windows(start_position=): the D-06 resize of an open blunder-check session"
  - "Puzzles at size 0: compose writes nothing, waiting count 0, open session expired"
affects: [251-06, 251-09, 251-13]

plan_head_before: 065a86e7de82bb38e9dcfa9ff6f8acb5a0ca7c54
plan_head_after: db423fcff91d5a90e472d269f1a274e064a837ad

actuals:
  tokens: 21000
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Optional PUT fields keep the stored value (None = keep) as the documented exception to the full-replace body"
    - "Settings service orchestrates sequential awaits and ends with the idempotent apply_day_completion for today"
    - "Notice clearing is a SQL CASE in the UPSERT's SET clause, evaluated against the pre-update row"

key-files:
  created:
    - app/services/train_settings_service.py
    - tests/routers/test_train_settings_two_modes.py
    - tests/services/test_train_settings_service.py
  modified:
    - app/schemas/train.py
    - app/routers/train.py
    - app/repositories/train_repository.py
    - app/repositories/blunder_check_repository.py
    - app/services/blunder_check_selection.py
    - app/services/blunder_check_service.py
    - tests/routers/test_train.py

key-decisions:
  - "Both-zero is refused twice: a schema validator for an explicit 0/0 body, and a service check on the RESOLVED pair (a body that omits the blunder-check key resolves against the stored size)"
  - "The launch notice is cleared by a SQL CASE on the stored size inside the same UPSERT, not a Python compare, so it cannot race a concurrent write"
  - "resize_open_session takes a now_utc argument (not in the plan signature) because the 'completed' branch must stamp completed_at via complete_session"
  - "Today for the day credit is resolved with the NEW timezone; a changed timezone therefore credits the day the user now lives in"
  - "Puzzles switched off only expires the open session when the size actually changed to 0; resize and puzzles-off are both skipped when the size is unchanged"

patterns-established:
  - "_compose_for_user: one helper gives a fresh session and an extension the same fallback level and cooldown"

requirements-completed: []

coverage:
  - id: D1
    description: "PUT /train/settings round-trips blunder_check_per_session and blunder_check_level, refuses both-off with 422, accepts old PWA bodies, clears the notice on an amount change"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_settings_two_modes.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Setting blunder check to 0 after puzzles are done ticks the streak exactly once (tracer, over HTTP)"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_settings_two_modes.py#test_settings_bc_off_after_puzzles_done_ticks_streak"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every D-06 resize branch: expire at 0, complete at or below done, shorten, extend, completed never reopens, extension never re-serves a shown blunder"
    verification:
      - kind: integration
        ref: "tests/services/test_train_settings_service.py -k resize (7 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Puzzles at 0: compose writes and discards nothing, waiting count 0, open session expired with solves kept, blunder check alone completes the day"
    verification:
      - kind: integration
        ref: "tests/services/test_train_settings_service.py -k puzzles_off (4 tests)"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-11-18
status: complete
---

# Phase 251 Plan 04: Editable session sizes with D-06 resize Summary

**PUT /train/settings now edits both session sizes (puzzles 0..50, blunder check 0..30) at any time: an open blunder-check session is expired, completed, shortened or extended to match, puzzles can be switched off, and a change that completes today credits the streak exactly once.**

## Performance

- **Duration:** about 70 min
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Commits:** 5 (measured from `plan_head_before`)
- **Files:** 10 (3 created, 7 modified); no migration, no STATE/ROADMAP writes

## Accomplishments

- **Schema (D-05, D-07):** `TrainSettingsUpdate.puzzles_per_session` is `ge=0, le=PUZZLES_PER_SESSION_MAX`; `blunder_check_per_session` (0..30) and `blunder_check_level` are optional (None keeps the stored value, documented as the exception to the full-replace rule); a model validator rejects an explicit 0/0 body with 422. `TrainSettingsResponse` carries both new fields.
- **Repository `upsert_settings`:** new kw-only parameters default to None (keep), so the ~30 pre-existing direct callers stay valid unchanged. The written blunder-check size and level now land (251-12 note a) and the same UPSERT clears `blunder_check_notice_from` through a SQL `CASE` when the size differs (D-21).
- **`train_settings_service.apply_settings_update`:** resolve optional fields against the stored row, raise `TrainSettingsInvalidError` for a resolved 0/0 (router maps it to 422, not sent to Sentry), upsert, resize the open blunder-check session when its size changed, expire the open puzzle session when puzzles went to 0, then `apply_day_completion` for today (idempotent through `streak_credited_on`).
- **D-06 resize:** `resize_open_session` locks the caller's open unexpired session (`FOR UPDATE`, user scoped) and returns a `ResizeOutcome` literal: n = 0 expires it and deletes never-started windows; 0 < n <= ended deletes never-started windows, sets `window_count` to the rows left and completes it; ended < n < window_count deletes windows at position >= n; n > window_count answers `needs_extension`. `blunder_check_service.resize_for_settings` composes `n - window_count` windows with `compose_windows(start_position=window_count)` (same fallback level and cooldown as a fresh session via the shared `_compose_for_user`) and `append_windows` inserts them. A shown window is never deleted and no outcome or points are ever written to an existing window.
- **Puzzles off:** `compose_and_materialize_session` returns the empty session before any read or write at size 0, `get_waiting_puzzle_count` returns 0, `expire_open_session` flips the open puzzle session to `expired` (solves and points stay).

## Task Commits

1. **Task 1 (tracer): settings PUT edits both sizes, credits the completed day** - `6abc306b7` (feat)
2. **Task 2 RED** - `6b715ecb4` (test); **GREEN** - `f54cb5caf` (feat)
3. **Task 3 RED** - `345017a90` (test); **GREEN** - `db423fcff` (feat)

## TDD notes

- **Task 2 RED** (`6b715ecb4`): 6 of 7 target tests failed on the planned assertions (`'open' == 'expired'`, `'open' == 'completed'` twice, `window_count 6 == 4`, `positions [0..5] == [0..8]`, `extension composed nothing`). `test_resize_after_completion_applies_next_session` passed immediately: it is a regression guard (a completed session is never reopened), not a new behaviour. Semantic assessment: every failing test executed and failed on the missing behaviour, not on a collection or fixture fault. `gsd_run check tdd-red-evidence` not run (pytest format unsupported, plan is `type: execute`).
- **Task 3 RED** (`345017a90`): 3 of 4 target tests failed on the planned assertions (`[] == [(1, 'open')]`: the untouched open session was discarded; `4 == 0` waiting count from a touched open session; `'open' == 'expired'`). `test_puzzles_off_bc_done_ticks` passed immediately (puzzle size 0 already satisfies the both-modes rule from 251-12), a regression guard. The first draft of the waiting-count test passed by coincidence because `min(count, 0)` already yields 0, so it was strengthened with a touched open session, which fails without the guard.
- No REFACTOR commits. Task 1 is a tracer (not TDD); its tests were written alongside the code.

## Deviations from Plan

**1. [Rule 3 - Blocking] `resize_open_session` takes `now_utc`**
- **Issue:** The planned signature `(session, *, user_id, today, new_size)` cannot stamp `completed_at` in the "completed" branch, because `complete_session` needs the instant.
- **Fix:** added kw-only `now_utc`. Commit `f54cb5caf`.

**2. [Rule 2 - Test determinism] Extension tests seed foreign supply and force the sample to 100%**
- **Issue:** `draw_slot_plan` draws about half the slots as foreign; with own games only, an extension composed a random 0 to 3 windows and `test_resize_extend_composes_more` failed 5 of 6 runs.
- **Fix:** the service test module seeds another user's games and monkeypatches `FOREIGN_SAMPLE_PERCENT` to 100 (the same device the 251-03 tests use). Seven consecutive runs of the resize tests passed afterwards. Commit `f54cb5caf`.

**3. [Rule 3 - Structure] `insert_session` row building factored into `_window_row`**
- Shared by the insert and `append_windows`, avoiding a second copy of the 17-column mapping. Behaviour unchanged. Commit `f54cb5caf`.

**Total deviations:** 3 (1 signature addition, 1 test determinism, 1 small extraction). **Impact:** none on scope.

## Assumptions and behaviour notes for later plans

- **A4 honoured:** blunder check set to 0 marks the open session `expired`, so raising it again the same day composes a fresh session (the shown windows of the expired session stay in the served set).
- **251-12 note (b) reconciled:** `compose_or_resume` still returns None at size 0, but the settings PUT now expires any open blunder-check session at size 0, so a leftover open session cannot exist after the switch through the normal path.
- **Started-but-unended window in the "n <= ended" case** stays stored with no outcome, so it is excluded from the boards (Plan A, as decided in the plan context).
- **Known limitation (extension and "one window per game"):** `compose_windows` derives its used-game set from the windows it composes itself, so an extension may place a second, non-overlapping window on a game that already hosts an earlier window of the same session. Serve-once (D-01) holds because the blunder-ply and judged-range checks read every window of the user. Closing this would mean threading the session's game ids into the composer; not done (outside the plan's scope).
- **Thin supply:** an extension may compose fewer windows than asked (the same thin-supply behaviour 251-03 measured); `append_windows` then sets `window_count` to the rows actually held, so the header stays consistent.
- **Pre-existing exact-dict settings tests** in `tests/routers/test_train.py` got the two new keys (`blunder_check_per_session: 6`, `blunder_check_level: None`); nothing else changed there.

## Issues Encountered

None blocking. Full backend suite `uv run pytest -n auto`: 7079 passed, 19 skipped. `ruff format --check`, `ruff check`, `ty check app/ tests/ scripts/` and `check_function_size.py app/ --fail-over-depth 4` are clean. Focused suites run: `tests/repositories/test_train_repository.py`, `tests/routers/test_train.py`, `tests/routers/test_train_two_mode_streak.py`, the two new test files, plus the blunder-check session/repository/selection/drill suites (all pass). The frontend was not touched.

## Known Stubs

None.

## Threat Flags

None. No new endpoint. T-251-12 (bounds, Literal level, both-off validator, service-level resolved check) and T-251-13 (`apply_day_completion` idempotent per day, completed sessions never reopen; tested by repeated identical PUTs) are mitigated and tested. T-251-14: extension is capped by the 30 bound on the PUT and one open session per user. T-251-15: `resize_open_session` and `append_windows` scope every statement by the auth-derived `user_id` and never take a client session id.

## Self-Check: PASSED

- Created files exist: `app/services/train_settings_service.py`, `tests/routers/test_train_settings_two_modes.py`, `tests/services/test_train_settings_service.py`, this SUMMARY.
- Commits `6abc306b7`, `6b715ecb4`, `f54cb5caf`, `345017a90`, `db423fcff` are ancestors of HEAD.
- Acceptance greps: one `async def apply_settings_update`, router delegates to it, one `async def resize_open_session`, `start_position` x4 in the selection module, one `async def expire_open_session`; no `.values(outcome=` / new `points_scored=` write in the resize functions; 7 tests selected by `-k resize`, 4 by `-k puzzles_off`, 7 `test_settings_*` tests in the router file.

---
*Phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d*
*Completed: 2026-11-18*
