---
phase: 234-milestone-feedback-ask
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, jsonb, postgres, state-machine]

requires:
  - phase: 233
    provides: Alembic head a7c3e9d41f02 (drill_solves telemetry)
provides:
  - users.prompt_state JSONB NOT NULL DEFAULT '{}' and feedback.source TEXT NOT NULL DEFAULT 'floating_button' with ck_feedback_source
  - FeedbackAskState / FeedbackAskView / FeedbackAskActionRequest schemas and FEEDBACK_ASK_* constants
  - feedback_ask_repository (active-day count, get_state, apply_view/apply_snooze/apply_done as single guarded UPDATE ... RETURNING)
  - feedback_ask_service (pure resolve_feedback_ask, profile snapshot, action routing)
  - GET and PUT /api/users/me/profile both return active_days and feedback_ask via one shared builder
  - POST /api/users/me/feedback-ask (view | snooze | done)
affects: [234-02, 234-03, 234-04, frontend profile type, feedback source attribution]

actuals:
  tokens: 16900
  tasks: 2
  commits: 3

plan_head_before: e7a9d965a8fd0d443ed97ebe70ae6844fdb5e129
plan_head_after: 65e49a4d9d9764f4dea8d6ae0fd2dba754253b99

tech-stack:
  added: []
  patterns:
    - "Guarded single-statement UPDATE ... RETURNING on a JSONB key, CAST-typed binds, validated on write by a Pydantic extra=forbid model"
    - "One profile builder shared by GET and PUT so the frontend cache write from PUT can never drop a field"

key-files:
  created:
    - alembic/versions/20261005_140000_f4b9d2c7e815_users_prompt_state_feedback_source.py
    - app/schemas/feedback_ask.py
    - app/repositories/feedback_ask_repository.py
    - app/services/feedback_ask_service.py
    - tests/test_feedback_ask.py
    - tests/repositories/test_feedback_ask_repository.py
    - tests/services/test_feedback_ask_service.py
  modified:
    - app/models/user.py
    - app/models/feedback.py
    - app/models/user_activity.py
    - app/schemas/users.py
    - app/repositories/feedback_repository.py
    - app/routers/users.py

key-decisions:
  - "active_days = count(user_activity rows dated strictly before today) + 1, so a middleware row for today never counts twice and the first fetch of the 5th day already shows the ask"
  - "feedback_ask exposes only {active}; round lives only in the stored state (D-02)"
  - "Corrupt stored state fails closed (ask inactive) after a Sentry capture; a ValidationError on a RETURNING value rolls the request back"
  - "PUT /me/profile now takes the impersonation dependency so GET and PUT stay identical"

patterns-established:
  - "Ask transitions mirror resolve_feedback_ask in SQL WHERE guards, sharing named constants as bound params"

requirements-completed: [FBASK-01, FBASK-02, FBASK-03, FBASK-04]

coverage:
  - id: D1
    description: "Migration adds users.prompt_state (NOT NULL, '{}') and feedback.source (default floating_button, ck_feedback_source); applies and downgrades cleanly"
    requirement: FBASK-01
    verification:
      - kind: integration
        ref: "tests/test_feedback_ask.py#test_feedback_ask_new_user_prompt_state_is_empty_object"
        status: pass
      - kind: other
        ref: "uv run alembic downgrade -1 && uv run alembic upgrade head (MIGRATION-ROUNDTRIP-OK)"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET and PUT profile return active_days and feedback_ask with identical values"
    requirement: FBASK-02
    verification:
      - kind: integration
        ref: "tests/test_feedback_ask.py#test_feedback_ask_get_and_put_profile_agree"
        status: pass
    human_judgment: false
  - id: D3
    description: "Server-decided eligibility: non-guest, >= 5 today-inclusive active days, no feedback from any source"
    requirement: FBASK-03
    verification:
      - kind: unit
        ref: "tests/services/test_feedback_ask_service.py#test_resolve_feedback_ask"
        status: pass
      - kind: integration
        ref: "tests/test_feedback_ask.py#test_feedback_ask_today_row_counts_once"
        status: pass
    human_judgment: false
  - id: D4
    description: "View/snooze/done lifecycle with daily view dedupe, 3rd-view auto-snooze with same-day grace, round 2 after +10 active days, exhaustion, atomic concurrency, guest/impersonation no-write"
    requirement: FBASK-04
    verification:
      - kind: integration
        ref: "tests/repositories/test_feedback_ask_repository.py and tests/test_feedback_ask.py (51 tests)"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-06
status: complete
---

# Phase 234 Plan 01: Milestone Feedback Ask backend Summary

**Server-side milestone feedback ask: `users.prompt_state` JSONB with three atomic guarded UPDATEs (view/snooze/done), pure server-decided eligibility, `active_days` + `feedback_ask` on both profile routes, and `POST /api/users/me/feedback-ask`.**

## Performance

- **Duration:** about 45 min
- **Completed:** 2026-10-06
- **Tasks:** 2 (tracer + TDD task)
- **Files:** 7 created, 6 modified

## Accomplishments

- One migration (`f4b9d2c7e815`, down_revision `a7c3e9d41f02`) adds `users.prompt_state` and `feedback.source` + `ck_feedback_source`; applied to the dev DB, downgrade/upgrade round trip verified.
- Tracer: a 5-active-day user's profile reports `feedback_ask.active` true and one view POST lands `{"feedback_v1": {"round": 1, "views": 1, "last_view_date": ...}}` in Postgres end to end.
- Full lifecycle against real Postgres: once-per-UTC-day view dedupe, 3rd view auto-snoozes (`snoozed_by` views) while the ask keeps showing the rest of that day, snooze by click hides immediately (and upgrades a grace-day views-snooze to click), re-ask at `snoozed_at_days + 10`, nothing after round 2, done ends it forever.
- Every transition is one guarded `UPDATE ... RETURNING`; unrelated `prompt_state` keys survive; two concurrent same-day views leave `views == 1`.
- Guests and impersonation tokens get `active: false` and write nothing; unknown action or extra key returns 422; no token returns 401.
- GET and PUT profile share `_build_profile_response`.

## Task Commits

1. **Task 1 (tracer): migration, view path, profile fields, endpoint** - `06ab0d90e` (feat)
2. **Task 2 RED: failing tests for snooze, done, round 2, guards, concurrency** - `9adea6664` (test)
3. **Task 2 GREEN: snooze/done transitions and dispatch** - `65e49a4d9` (feat)

## TDD Gate Compliance

- RED (`9adea6664`): 12 tests failed. The HTTP snooze/done tests failed on the planned assertion (`{'active': True} != {'active': False}`, the Task 1 dispatch no-op); the repository snooze/done tests failed with `AttributeError` because `apply_snooze`/`apply_done` did not exist yet (a per-test failure, not a collection error). The pure truth-table and view-matrix tests passed already (their code shipped with the Task 1 tracer, as the plan prescribes), so those are characterization tests, proven instead by the mutation checks below.
- GREEN (`65e49a4d9`): all 51 tests pass.
- REFACTOR: none needed.

## Mutation Proofs (each reverted afterwards)

| # | Mutation | Result (red) |
|---|----------|--------------|
| a | VIEW WHERE once-per-day clause (`last_view_date <> today`) replaced by `TRUE` | `TestView::test_same_day_view_is_noop` and `test_feedback_ask_concurrent_same_day_views_count_once` FAILED |
| b | VIEW WHERE round cap (`round < max_rounds`) removed | `test_exhausted_round_two_is_never_viewed_again[click]` and `[views]` FAILED |
| c | Grace clause removed from `resolve_feedback_ask` | `test_resolve_feedback_ask[grace-day]` and `test_feedback_ask_three_view_days_auto_snooze_with_grace` FAILED |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `text` name shadowed in the Feedback model**
- **Found during:** Task 1
- **Issue:** `Feedback.text` (a column attribute) shadows `sqlalchemy.text` inside the class body, so `server_default=text(...)` for the new `source` column would have called the column object.
- **Fix:** import `text as sql_text` and use it for the server default, with a comment.
- **Files modified:** app/models/feedback.py
- **Commit:** `06ab0d90e`

**2. [Rule 3 - Blocking] ty needed an ignore for the FastAPI-Users email comparison**
- **Found during:** Task 2
- **Issue:** `User.email == email` is typed as plain `bool`; same known idiom as `tests/test_password_reset.py`.
- **Fix:** `# ty: ignore[invalid-argument-type]` with reason.
- **Files modified:** tests/test_feedback_ask.py
- **Commit:** `65e49a4d9`

**3. [Rule 3 - Blocking] Fresh worktree needed `uv sync --group maia-inference`**
- Phantom `unresolved-import` for onnxruntime in `scripts/maia_parity_spike.py` until the group was synced (known project note); environment only, no code change.

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking). **Impact:** none on scope.

## Verification

- `uv run alembic heads` shows `f4b9d2c7e815 (head)`; downgrade -1 then upgrade head OK.
- `uv run pytest tests/test_feedback_ask.py tests/repositories/test_feedback_ask_repository.py tests/services/test_feedback_ask_service.py tests/test_feedback_router.py tests/test_feedback_repository.py ...` green; full `uv run pytest -n auto -x`: 5248 passed, 19 skipped.
- `ruff format --check`, `ruff check .`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: all clean.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model (the new POST route is T-234-01..04, mitigated and tested).

## Issues Encountered

None.

## Next Phase Readiness

Plan 03 can add `FeedbackSource` to `POST /api/feedback` and write `feedback.source` (the column, default and CHECK exist; `create_feedback` is untouched). The frontend profile type needs `active_days: number` and `feedback_ask: { active: boolean }`.

## Self-Check: PASSED

- Files exist: migration, schemas/feedback_ask.py, repositories/feedback_ask_repository.py, services/feedback_ask_service.py, three test files (verified below).
- Commits `06ab0d90e`, `9adea6664`, `65e49a4d9` are ancestors of HEAD.
