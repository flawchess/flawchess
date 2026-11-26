---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 06
subsystem: api
tags: [train, progress, blunder-check, reminder, fastapi, sqlalchemy]

requires:
  - phase: 251-12
    provides: day_complete_on / both-modes day rule
  - phase: 251-04
    provides: blunder_check_per_session / blunder_check_level settings, notice cleared on size change
  - phase: 251-01
    provides: dated blunder-check sessions, blunder_check_repository open/completed lookups
provides:
  - "GET /train/progress per-mode read model: modes.puzzles, modes.blunder_check, day_complete, pending_count, blunder_check_notice"
  - "POST /train/blunder-check-notice/dismiss (204, idempotent, caller-scoped)"
  - "Reminder job skips only when every required mode is done (day_complete_on)"
affects: [251-07, 251-08, 251-09, 251-10, 251-11, 251-13]

plan_head_before: 773f99d985d863aa05d987d9c2346feccd5574b4
plan_head_after: 81fe94d290d7bac20c48c7b3c2343badb0c01aa5

actuals:
  tokens: 15400
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "One read helper per mode so get_progress stays shallow (nesting-depth gate clean)"
    - "Launch notice derived on read from the stamp, the 14-day window and a completed_at >= stamp EXISTS; no write on completion"

key-files:
  created:
    - tests/repositories/test_train_progress_modes.py
    - tests/routers/test_train_progress_modes.py
  modified:
    - app/schemas/train.py
    - app/routers/train.py
    - app/repositories/train_repository.py
    - app/repositories/train_reminder_repository.py
    - app/services/train_reminder_service.py
    - tests/routers/test_train.py
    - tests/services/test_train_reminder_service.py

key-decisions:
  - "Puzzles state precedence: off (size 0), done (completed in window), in_progress (open unexpired session with >=1 solve), else pending; remaining stays waiting_count and pending stays badge-gated, so badge_visible / waiting_count keep their meaning"
  - "Blunder check: a completed in-window session wins over an open one; size 0 wins over everything (a leftover open session at size 0 is off, contributes 0)"
  - "has_completed_session_on removed (its only caller was the reminder service) together with TestHasCompletedSessionOn"
  - "Repository dataclasses (ModeProgress, BlunderCheckModeProgress, ModesProgress) are mapped to the wire models in the router via dataclasses.asdict"

patterns-established:
  - "Per-mode progress helpers: _puzzles_mode_progress, _blunder_check_session_state, _blunder_check_mode_progress, _launch_notice_visible"

requirements-completed: []

coverage:
  - id: D1
    description: "GET /train/progress returns per-mode state, the D-13 pending sum and day_complete"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_progress_modes.py -k pending_count (5 tests)"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_progress_returns_200_with_every_field"
        status: pass
    human_judgment: false
  - id: D2
    description: "Puzzles/blunder-check row states, first_session_done, needs_level, day_complete over the repository"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_progress_modes.py (6 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Launch notice window, derived hide after a completed session, dismissal (204, idempotent, caller-scoped), hide after a size change, NULL for new users and guests"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_progress_modes.py -k notice (4 tests)"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_progress_modes.py#test_notice_visible_window"
        status: pass
    human_judgment: false
  - id: D4
    description: "Reminder nudges while a required mode is pending, stays quiet once the day is complete or blunder check is off"
    verification:
      - kind: integration
        ref: "tests/services/test_train_reminder_service.py::TestAlreadyTrained (4 tests)"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-11-18
status: complete
---

# Phase 251 Plan 06: Per-mode progress read model Summary

**GET /train/progress now carries a server-computed `modes` object (puzzles and blunder check state, remaining, pending, first-session flag, points today, level need), the D-13 summed `pending_count`, `day_complete` and the D-21 launch notice with a dismiss endpoint, and the reminder job only stays quiet once every required mode is done.**

## Performance

- **Duration:** about 40 min
- **Completed:** 2026-11-18T21:57Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files:** 9 (2 created, 7 modified)
- **Commits:** 5 measured from `plan_head_before`

## Accomplishments

- `app/schemas/train.py`: `TrainModeState`, `TrainModeProgress`, `TrainBlunderCheckModeProgress`, `TrainModesProgress`, and the four new `TrainProgressResponse` fields. Every pre-existing field and meaning is unchanged for installed clients.
- `app/repositories/train_repository.py`: frozen dataclasses `ModeProgress`, `BlunderCheckModeProgress`, `ModesProgress`, the extended `ProgressSnapshot`, and per-mode helpers composed by `get_progress` (sequential awaits, no `asyncio.gather`). `dismiss_blunder_check_notice` clears the caller's stamp.
- `app/routers/train.py`: maps the snapshot onto the response and adds `POST /train/blunder-check-notice/dismiss` (204, `current_active_user`, Sentry capture with `set_context` on unexpected errors).
- Reminder: `_process_candidate` calls `train_repository.day_complete_on` after the committed settlement and before the claim; `has_completed_session_on` and its tests are removed (no other caller).

## Task Commits

1. **Task 1 (tracer): per-mode state and summed pending count** - `ad71a5b65` (feat)
2. **Task 2 RED** - `b9b6a11f7` (test); **GREEN** - `7edc56490` (feat)
3. **Task 3 RED** - `a6dddd635` (test); **GREEN** - `81fe94d29` (feat)

## TDD notes

- **Task 2 RED**: 8 target tests failed on the planned assertions against Task 1's deliberate placeholders (`'pending' == 'in_progress'`, `0 == 7` points, `first_session_done False is True`, `needs_level False is True`, notice `False is True`). No collection or fixture faults. `test_day_complete_flag` and `test_notice_never_for_new_user_or_guest` passed immediately (the former because Task 1 already computed `day_complete`; the latter because the placeholder was False); they are regression guards. `gsd_run check tdd-red-evidence` was not run (pytest report format unsupported; plan is `type: execute`).
- **Task 3 RED**: `test_reminder_sent_when_puzzles_done_bc_pending` failed (`Expected mock to have been awaited once. Awaited 0 times`) and the repointed `TestFailureIsolation` test failed (`sent == 2` instead of 1, the patched call was not yet reached). The day-complete and bc-off cases passed before GREEN because the old puzzle-only check also suppressed them; they guard the new rule.
- No REFACTOR commit.

## Pre-existing tests changed

- `tests/routers/test_train.py`: the two progress key-set assertions gain the four new keys; `test_progress_returns_200_with_all_eleven_fields` renamed `..._with_every_field`. No other assertion touched.
- `tests/services/test_train_reminder_service.py`: seeders take kw-only `blunder_check_per_session` (omitted from the insert when not given, so the server default 6 applies); the already-trained completed-session test passes 0; `TestFailureIsolation` patches `train_repository.day_complete_on`; `TestHasCompletedSessionOn` deleted with the removed function.

## Deviations from Plan

None - plan executed exactly as written. (Placeholders in Task 1 for `first_session_done`, `points_today`, `has_rated_games`, `needs_level`, the notice and the puzzles `in_progress` refinement were the plan's own Task 1 / Task 2 split; all are filled in Task 2 and none remain.)

## Issues Encountered

None. Full backend suite `uv run pytest -n auto -x`: 7094 passed, 19 skipped. `ruff format`, `ruff check .`, `ty check app/ tests/ scripts/` and `check_function_size.py app/ --fail-over-depth 4` are clean. Frontend not touched.

## Behaviour notes for later plans (frontend consumers)

- `modes.puzzles.pending` equals `waiting_count` only when `badge_visible`; `modes.blunder_check.pending` is the session's remaining count when today is scheduled or an unexpired session is open, else 0. `pending_count` is their sum.
- A completed in-window blunder-check session wins over an open one; `blunder_check_per_session == 0` yields `state "off"` even with a leftover open session.
- `needs_level` is computed even at blunder-check size 0 (harmless: the client hides the whole row when off).
- `blunder_check_notice` is derived, so the dismissal and the size-change null are the only writes; a blunder-check session completed after the stamp hides it without any write.
- `day_complete` uses `session_date == today` (plan 12), while the per-mode `done` state uses "completed session still in its window"; the two can differ on an unscheduled day with a multi-day window, by design (the row state shows the recap, the day rule credits the streak).

## Known Stubs

None.

## Threat Flags

None. T-251-18: dismiss writes only the caller's own row (test `test_notice_dismiss_is_scoped_to_caller`). T-251-19: the response carries only the caller's own counts and flags. T-251-20: day-complete check sits after the committed settlement and before the claim; claim guard unchanged.

## Self-Check: PASSED

- Created files exist: both new test files and this SUMMARY.
- Commits `ad71a5b65`, `b9b6a11f7`, `7edc56490`, `a6dddd635`, `81fe94d29` are ancestors of HEAD.
- Acceptance greps: one `class TrainModesProgress`; `blunder-check-notice/dismiss` route under the `/train` prefix with a relative decorator path; one `async def dismiss_blunder_check_notice` in `train_repository.py`; one `day_complete_on` in `train_reminder_service.py`; `tests/repositories/test_train_progress_modes.py` collects 6 tests; depth gate OK.

---
*Phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d*
*Completed: 2026-11-18*
