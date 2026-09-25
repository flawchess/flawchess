---
quick_id: 260925-ine
plan: 01
subsystem: auth, eval-pipeline
tags: [fastapi-users, pwdlib, sqlalchemy, postgresql, sentry, integrity-error]

# Dependency graph
requires: []
provides:
  - "UserManager.authenticate override (app/users.py) — empty-hash (Google-only/guest) accounts return 400 LOGIN_BAD_CREDENTIALS on password login instead of 500 UnknownHashError"
  - "eval_apply.commit_unless_game_deleted — shared helper mapping a mid-write game deletion to None instead of an unhandled FK IntegrityError"
  - "Router (_apply_atomic_submit) and both drain write paths (_full_drain_tick, _tier4b_minimal_drain_tick via _write_tier4b_best_moves) wired through the shared helper"
affects: [eval-pipeline, auth, sentry-noise]

# Actuals (#2632)
actuals:
  tokens: 11600
  tasks: 2
  commits: 2
plan_head_before: 190b59f25ce6c1c1cc9b16f9de6c4ac54feca2e6

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "commit_unless_game_deleted(write_session, game_id, write) — non-locking existence pre-check + narrow SQLSTATE-23503 in-transaction FK-violation catch, used as the standard pattern for any future eval write session that can race a game delete"

key-files:
  created: []
  modified:
    - app/users.py
    - app/services/eval_apply.py
    - app/routers/eval_remote.py
    - app/services/eval_drain.py
    - tests/test_auth.py
    - tests/services/test_eval_apply.py
    - tests/services/test_full_eval_drain.py
    - tests/test_eval_worker_endpoints.py
    - CHANGELOG.md

key-decisions:
  - "UserManager.authenticate mirrors upstream fastapi-users structure exactly (get_by_email -> UserNotExists dummy-hash branch -> empty-hash dummy-hash branch -> super().authenticate()) so real verification and the hash-upgrade write stay owned by fastapi-users; only the empty-hash short-circuit is new."
  - "No row lock (SELECT ... FOR KEY SHARE) on the games row in commit_unless_game_deleted — rejected because delete_all_games_for_user deletes game_positions before games (children-then-parent), so a games row lock would deadlock against that delete, and it would also jump ahead of apply_full_eval's advisory lock, which must stay the first lock taken on every path (260825-v8g invariant). Used a non-locking pre-check + narrow post-rollback re-check instead."
  - "_tier4b_minimal_drain_tick's write body was extracted into a module-level _write_tier4b_best_moves so it could run through commit_unless_game_deleted, which needs a zero-argument callable."

requirements-completed: [FLAWCHESS-BQ, FLAWCHESS-2A, FLAWCHESS-A0]

coverage:
  - id: D1
    description: "Password login against a Google-only or guest account (hashed_password=\"\") returns 400 LOGIN_BAD_CREDENTIALS instead of 500 UnknownHashError; a normal login and a wrong-password login are unaffected."
    requirement: "FLAWCHESS-BQ"
    verification:
      - kind: unit
        ref: "tests/test_auth.py::TestLogin::test_login_empty_hash_account_returns_400[False] / [True]"
        status: pass
      - kind: unit
        ref: "tests/test_auth.py::TestLogin::test_login_returns_access_token, test_login_wrong_password_returns_400"
        status: pass
    human_judgment: false
  - id: D2
    description: "The same fix also closes FLAWCHESS-2A (frontend Sentry-captured non-400 login failures) since the 500 that triggered that capture no longer occurs."
    requirement: "FLAWCHESS-2A"
    verification:
      - kind: unit
        ref: "tests/test_auth.py::TestLogin::test_login_empty_hash_account_returns_400"
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /api/eval/remote/atomic-submit for a game deleted mid-submit returns 404 'Game not found' and writes nothing (no game_best_moves, no game_flaws, no IntegrityError)."
    requirement: "FLAWCHESS-A0"
    verification:
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_game_deleted_mid_submit_returns_404"
        status: pass
    human_judgment: false
  - id: D4
    description: "The drain lane's full path (_full_drain_tick) and tier-4b minimal path (_tier4b_minimal_drain_tick) both return False instead of raising into run_full_eval_drain's Sentry catch-all when the claimed game is deleted mid-write."
    requirement: "FLAWCHESS-A0"
    verification:
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestMarkerWrite::test_full_drain_tick_game_deleted_mid_write_returns_false"
        status: pass
      - kind: unit
        ref: "tests/services/test_full_eval_drain.py::TestBestMoveBackfill::test_full_drain_tick_tier4b_game_deleted_mid_write_returns_false"
        status: pass
    human_judgment: false
  - id: D5
    description: "commit_unless_game_deleted's contract: pre-check short-circuit, in-transaction race handling, and narrow-catch (unrelated IntegrityError still propagates)."
    verification:
      - kind: unit
        ref: "tests/services/test_eval_apply.py::TestCommitUnlessGameDeleted (3 tests)"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-09-25
status: complete
---

# Quick Task 260925-ine: Fix Sentry FLAWCHESS-BQ/2A (empty-hash login 500) and FLAWCHESS-A0 (deleted-game eval FK 500) Summary

**Two independent production Sentry fixes: password login against a Google-only/guest account (empty `hashed_password`) now returns 400 bad-credentials instead of a pwdlib `UnknownHashError` 500, and the eval write pipeline (atomic-submit router + both drain lanes) now discards a game deleted mid-write as a 404/no-op instead of raising an unhandled `ForeignKeyViolation` into Sentry.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-25T13:47:48+02:00
- **Tasks:** 2/2 completed
- **Files modified:** 9 (8 code/test files + CHANGELOG.md)

## Accomplishments

- `UserManager.authenticate` (app/users.py) short-circuits on the same credential-state predicate `on_after_forgot_password` already uses (`not user.hashed_password`), returning the identical 400 `LOGIN_BAD_CREDENTIALS` a wrong password gets — never revealing which accounts are Google-only or guest.
- New shared `eval_apply.commit_unless_game_deleted` helper: a non-locking existence pre-check plus a narrow SQLSTATE-23503 (foreign_key_violation) in-transaction catch, wired into all three eval write sessions that can race a game delete (`_apply_atomic_submit`, `_full_drain_tick`, `_tier4b_minimal_drain_tick`).
- Six new regression tests, each proven to fail against the unfixed code (RED) before the fix was applied, then re-verified GREEN after restoring the fix (see "RED evidence" below).

## Task Commits

Each task was committed atomically:

1. **Task 1: Empty-hash accounts get 400 bad credentials on password login (FLAWCHESS-BQ, FLAWCHESS-2A)** - `6c0eed5e3` (fix)
2. **Task 2: Deleted-game race in eval write sessions maps to 404 / tick no-op instead of an FK 500 (FLAWCHESS-A0)** - `051956944` (fix)

**Plan metadata:** committed separately by the orchestrator (this SUMMARY, STATE.md, ROADMAP.md are not committed by the executor per plan instructions).

## Files Created/Modified

- `app/users.py` - `UserManager.authenticate` override guarding empty-hash accounts before pwdlib ever sees the hash
- `tests/test_auth.py` - parametrized regression test (`is_guest` False/True) + `_create_empty_hash_user` helper
- `CHANGELOG.md` - one `### Fixed` bullet under `## [Unreleased]` for FLAWCHESS-BQ
- `app/services/eval_apply.py` - `_PG_FOREIGN_KEY_VIOLATION_SQLSTATE` constant, `_game_row_exists`, `commit_unless_game_deleted` (new shared helper, `TypeVar`/`Awaitable` added to imports)
- `app/routers/eval_remote.py` - `_apply_atomic_submit`'s write session routed through `commit_unless_game_deleted`; `None` outcome -> `logger.info` + 404 "Game not found"; docstring updated
- `app/services/eval_drain.py` - `_full_drain_tick`'s write session and a new `_write_tier4b_best_moves` (extracted from `_tier4b_minimal_drain_tick`'s write body) both routed through `commit_unless_game_deleted`; `None` outcome -> `logger.info` + `return False`
- `tests/services/test_eval_apply.py` - `TestCommitUnlessGameDeleted` (3 tests: pre-check, in-transaction race, narrow-catch re-raise)
- `tests/services/test_full_eval_drain.py` - `test_full_drain_tick_game_deleted_mid_write_returns_false` (full path), `test_full_drain_tick_tier4b_game_deleted_mid_write_returns_false` (tier-4b path, wraps the REAL builder)
- `tests/test_eval_worker_endpoints.py` - `test_atomic_submit_game_deleted_mid_submit_returns_404`

## Decisions Made

- No row lock in `commit_unless_game_deleted`: a `SELECT ... FOR KEY SHARE` on `games` was considered and rejected — `delete_all_games_for_user` deletes `game_positions` before `games` (children-then-parent), so holding a `games` row lock while the deleter holds child-row locks is a deadlock cycle, and it would also insert a lock acquisition ahead of `apply_full_eval`'s `pg_advisory_xact_lock`, which must stay the FIRST lock taken (260825-v8g invariant). Used a non-locking existence pre-check plus a narrow post-rollback re-check instead — pre-check alone cannot close the race (the delete can land in the window between pre-check and commit), so the catch is required, not optional.
- `_tier4b_minimal_drain_tick`'s write-session body (UPSERT + conditional stamp) was extracted to a module-level `_write_tier4b_best_moves(write_session, game_id, best_move_rows, maia_available) -> int` purely so it could be passed as a zero-argument callable to `commit_unless_game_deleted`. It returns `len(best_move_rows)`, never `None`, by construction.
- `UserManager.authenticate` runs one extra dummy `password_helper.hash()` call for the empty-hash branch (timing parity with upstream's missing-user branch) and then falls through to `super().authenticate()` for every other case, rather than reimplementing verify_and_update locally — keeps the hash-upgrade write and all future upstream authenticate changes automatically inherited.

## Deviations from Plan

None — plan executed exactly as written. Both tasks matched their `<action>` specs; no Rule 1-4 auto-fixes were needed beyond what the plan itself specified (the plan's own design already accounted for the empty-hash timing-parity and narrow-FK-catch correctness requirements).

## RED Evidence (mutation-proof, per project convention)

All six new tests were proven to fail against the unfixed code by temporarily `git stash`-ing the three production file changes (`app/services/eval_apply.py`, `app/routers/eval_remote.py`, `app/services/eval_drain.py`) after writing all tests, running the full test set, then restoring the stash:

| Test | Failure mode against unfixed code |
|------|-----------------------------------|
| `tests/test_auth.py::TestLogin::test_login_empty_hash_account_returns_400` | `pwdlib.exceptions.UnknownHashError` raised through the ASGI transport (500) |
| `tests/services/test_eval_apply.py::TestCommitUnlessGameDeleted` (all 3) | Module import error — `ImportError: cannot import name 'commit_unless_game_deleted'` (collection failure) |
| `tests/test_eval_worker_endpoints.py::test_atomic_submit_game_deleted_mid_submit_returns_404` | `sqlalchemy.exc.IntegrityError` / `asyncpg.exceptions.ForeignKeyViolationError: ... game_best_moves_game_id_fkey ... Key (game_id)=(1) is not present in table "games"` — the exact prod error |
| `tests/services/test_full_eval_drain.py::test_full_drain_tick_game_deleted_mid_write_returns_false` | Same `ForeignKeyViolationError` on `game_best_moves_game_id_fkey`, raised from `apply_full_eval` -> `_upsert_best_move_rows` |
| `tests/services/test_full_eval_drain.py::test_full_drain_tick_tier4b_game_deleted_mid_write_returns_false` | Same `ForeignKeyViolationError` on `game_best_moves_game_id_fkey`, raised from `_tier4b_minimal_drain_tick` -> `_upsert_best_move_rows` |

After restoring the fix, all six tests pass and the full three-module suite (207 tests) is green.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

N/A - quick task, no follow-on phase. Both Sentry issues (FLAWCHESS-BQ/2A, FLAWCHESS-A0) are closed by these commits; no further action needed beyond normal deploy.

## Self-Check: PASSED

- All 9 modified files confirmed present on disk (`app/users.py`, `app/services/eval_apply.py`, `app/routers/eval_remote.py`, `app/services/eval_drain.py`, `tests/test_auth.py`, `tests/services/test_eval_apply.py`, `tests/services/test_full_eval_drain.py`, `tests/test_eval_worker_endpoints.py`, `CHANGELOG.md`).
- Both commit hashes confirmed in `git log --oneline --all`: `6c0eed5e3` (Task 1), `051956944` (Task 2).
- Full verification command from the plan (`pytest -n auto -x -q` on the three eval test modules + `tests/test_auth.py`/`tests/test_password_reset.py`, `ruff check`, `ruff format --check`, `ty check`, `check_function_size`, FLAWCHESS-A0 grep, commit-message grep) re-ran green after restoring the fix.
