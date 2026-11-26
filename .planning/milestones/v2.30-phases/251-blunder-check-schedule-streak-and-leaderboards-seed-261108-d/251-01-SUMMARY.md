---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 01
subsystem: database
tags: [postgres, alembic, fastapi, train, blunder-check, sqlalchemy]

requires:
  - phase: 249-blunder-check
    provides: blunder_check_sessions / windows tables and the compose_or_resume flow
provides:
  - "Alembic revision ccc5e4f91f6d: all non-leaderboard schema of phase 251"
  - "Phase 251 Train constants and BlunderCheckLevel in train_scheduler"
  - "Blunder-check sessions dated with the user's local day that expire, resume or show as done within their window"
  - "complete_session returning bool, get_open_session read path, seed_completed_blunder_check_session helper"
affects: [251-02, 251-03, 251-04, 251-12]

plan_head_before: c56374ff6c287b027ed1a3f0013e4925a0351abc
plan_head_after: 8316dba0d0995aba422577e025fee15a7c9c93a7

actuals:
  tokens: 15000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Blunder-check sessions reuse the drill_sessions window model: session_date/expires_on, expire_stale_sessions, completed_session_in_window"
    - "Timezone backfills join pg_timezone_names so an unknown stored zone falls back to UTC instead of aborting"

key-files:
  created:
    - alembic/versions/20261118_202527_ccc5e4f91f6d_phase_251_two_mode_train.py
    - tests/repositories/test_blunder_check_session_day.py
  modified:
    - app/models/train_settings.py
    - app/models/blunder_check.py
    - app/services/train_scheduler.py
    - app/repositories/blunder_check_repository.py
    - app/services/blunder_check_service.py
    - app/routers/blunder_check.py
    - tests/blunder_check_seed.py
    - tests/routers/test_blunder_check_sessions.py
    - tests/routers/test_blunder_check_drill.py
    - tests/routers/test_blunder_check_solution.py
    - tests/repositories/test_blunder_check_repository.py
    - tests/services/test_blunder_check_selection.py

key-decisions:
  - "Expired blunder-check sessions delete only never-started windows (A9); shown windows stay so a shown blunder is never served again (D-01)"
  - "A finished session inside its window is returned by Start instead of composing a new one (completed_session_in_window)"
  - "get_open_session uses the read-only get_settings with DEFAULT_TIMEZONE fallback so GET /open never writes"
  - "complete_session uses UPDATE ... RETURNING id to report whether it moved the row"

patterns-established:
  - "Read path ignores an expired open row without writing; the compose path owns expiry"

requirements-completed: []

coverage:
  - id: D1
    description: "Migration ccc5e4f91f6d applies, downgrades and round-trips; alembic check is clean"
    verification:
      - kind: other
        ref: "uv run alembic upgrade head && uv run alembic check; downgrade -1 then upgrade head"
        status: pass
    human_judgment: false
  - id: D2
    description: "A blunder-check session started over HTTP carries the user's local day and window"
    verification:
      - kind: integration
        ref: "tests/routers/test_blunder_check_sessions.py#test_start_session_dated_local_today"
        status: pass
    human_judgment: false
  - id: D3
    description: "Expired sessions delete only never-started windows; stale session expired on next Start"
    verification:
      - kind: unit
        ref: "tests/repositories/test_blunder_check_session_day.py#test_bc_expire_deletes_only_unstarted_windows"
        status: pass
      - kind: integration
        ref: "tests/routers/test_blunder_check_sessions.py#test_start_after_window_expires_old_session_and_composes_new"
        status: pass
    human_judgment: false
  - id: D4
    description: "Start on a done day returns the finished session; next session day composes a new one"
    verification:
      - kind: integration
        ref: "tests/routers/test_blunder_check_drill.py#test_finish_then_start_returns_done_session_until_next_day"
        status: pass
    human_judgment: false
  - id: D5
    description: "complete_session true once, get_session_date user-scoped, open read ignores expired"
    verification:
      - kind: unit
        ref: "tests/repositories/test_blunder_check_session_day.py"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-18
status: complete
---

# Phase 251 Plan 01: Two-mode Train schema and dated blunder-check sessions Summary

**One Alembic revision carries every non-leaderboard schema change of phase 251, and blunder-check sessions now have a local session day that expires like a puzzle session's, keeping shown windows and showing a finished session until the next day.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Commits:** 4 (measured from `plan_head_before`)
- **Files:** 14 (2 created, 12 modified)

## Accomplishments

- Migration `ccc5e4f91f6d` (down_revision `d1a7b3c5e261`): `train_settings` gains `blunder_check_per_session` (server default 6), `blunder_check_level`, `blunder_check_notice_from` (stamped for non-guest rows), `blunder_check_streak_from` (local launch day) and `streak_credited_on` (backfilled from `streak_settled_through`); `ck_train_settings_puzzles` widened to 0..50, plus `ck_train_settings_blunder_check`, `ck_train_settings_some_mode_on`, `ck_train_settings_blunder_check_level`. `blunder_check_sessions` gains NOT NULL `session_date`/`expires_on` (backfilled in the user's zone), an 'expired' status and `ix_blunder_check_sessions_user_date`; `ix_blunder_check_windows_ended_at` is the partial index for plan 02. Data-aware downgrade verified.
- Phase constants and `BlunderCheckLevel` in `train_scheduler.py` (`DEFAULT_BLUNDER_CHECK_PER_SESSION`, `BLUNDER_CHECK_PER_SESSION_MAX`, `PUZZLES_PER_SESSION_MAX`, `CROSS_MODE_COOLDOWN_DAYS`, `BLUNDER_CHECK_NOTICE_DAYS`, `BLUNDER_CHECK_LEVELS`), mirrored in both models with CHECK bounds from the constants.
- `compose_or_resume` resolves the user's settings, dates the session with `local_today` and `session_window`, expires stale sessions, resumes the open one, returns a finished in-window session, else composes. `get_open_session` is the read-only GET /open path.
- Repository: `expire_stale_sessions`, `completed_session_in_window`, `get_session_date`, `open_session_progress(today=...)`, `insert_session(session_date=, expires_on=)`, `complete_session -> bool`.
- Test seed helper `seed_completed_blunder_check_session` for plans 02, 04 and 12.

## TDD (Task 2)

- **RED** (`63867bc14`): six repository behaviour tests plus the seed helper. Run result: 5 failed, 1 passed. The failures were the planned behaviours: `AttributeError` for the missing `expire_stale_sessions` / `completed_session_in_window` / `get_session_date`, `TypeError` for `open_session_progress(today=...)`, and `complete_session` returning `None` instead of `True`. `test_bc_session_dated_local_today` passed because Task 1 already wrote the dated insert. The `gsd_run check tdd-red-evidence` classifier was not run: it does not support pytest report formats, and the plan is `type: execute`, not `type: tdd`. Semantic assessment: every failing target test executed and failed on the planned missing behaviour, not on a collection, import or fixture fault.
- **GREEN** (`3e9a5e8b1`): repository functions, service and router wiring; the drill test was rewritten to `test_finish_then_start_returns_done_session_until_next_day`. All blunder-check suites pass.
- **Follow-up** (`8316dba0d`): `test_start_after_window_expires_old_session_and_composes_new` pins the compose-time expiry end to end. Proven by mutation: replacing the `expire_stale_sessions` call in `compose_or_resume` with `pass` fails that test.
- No REFACTOR commit.

## Task Commits

1. **Task 1 (tracer): schema and dated start** - `9611db864` (feat)
2. **Task 2 RED** - `63867bc14` (test)
3. **Task 2 GREEN** - `3e9a5e8b1` (feat)
4. **Task 2 follow-up test** - `8316dba0d` (test)

## Deviations from Plan

### Auto-fixed / additions

**1. [Rule 2 - Missing critical test] Compose-time expiry had no end-to-end test**
- **Found during:** Task 2 verification (mutation check)
- **Issue:** The repository tests cover `expire_stale_sessions` directly, but nothing failed if `compose_or_resume` stopped calling it.
- **Fix:** Added `test_start_after_window_expires_old_session_and_composes_new` in `tests/routers/test_blunder_check_sessions.py`.
- **Commit:** `8316dba0d`

**Total deviations:** 1 (a test-only addition). **Impact:** none on scope.

## Issues Encountered

None. Full backend suite (`uv run pytest -n auto`: 6994 passed, 19 skipped), `alembic check`, `ty check app/ tests/ scripts/`, `ruff format --check`, `ruff check` and `check_function_size.py app/ --fail-over-depth 4` are all clean.

Note for the orchestrator: `uv run alembic upgrade head` was run against the shared dev DB, so it is now at `ccc5e4f91f6d`. Other worktrees on older code will still run (their test DBs clone from a template that refreshes on head change).

## Known Stubs

None.

## Threat Flags

None. No new endpoint or trust boundary: GET /blunder-check/sessions/open gained a `now_utc` dependency only. Every new repository lookup (`get_session_date`, `completed_session_in_window`, `expire_stale_sessions`) is scoped by the auth-derived user id (T-251-02, covered by `test_bc_get_session_date_scoped_to_user`).

## Next Phase Readiness

Plan 12 can read `blunder_check_streak_from`, `streak_credited_on`, `complete_session -> bool`, `get_session_date`, `completed_session_in_window` and `seed_completed_blunder_check_session`. Compose still uses the fixed `BLUNDER_CHECK_SESSION_WINDOWS`; plan 12 switches it to the per-user size.

## Self-Check: PASSED

- Created files exist: migration, `tests/repositories/test_blunder_check_session_day.py`, this SUMMARY.
- Commits `9611db864`, `63867bc14`, `3e9a5e8b1`, `8316dba0d` are ancestors of HEAD.
- `alembic heads` prints one head (`ccc5e4f91f6d`); all plan acceptance greps pass.
