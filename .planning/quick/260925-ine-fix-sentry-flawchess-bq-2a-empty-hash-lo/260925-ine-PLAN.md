---
quick_id: 260925-ine
slug: fix-sentry-flawchess-bq-2a-empty-hash-login-and-a0-deleted-game-submit
date: 2026-09-25
phase: quick-260925-ine
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: true
requirements: [FLAWCHESS-BQ, FLAWCHESS-2A, FLAWCHESS-A0]
files_modified:
  - app/users.py
  - tests/test_auth.py
  - CHANGELOG.md
  - app/services/eval_apply.py
  - app/routers/eval_remote.py
  - app/services/eval_drain.py
  - tests/services/test_eval_apply.py
  - tests/services/test_full_eval_drain.py
  - tests/test_eval_worker_endpoints.py

estimate:
  tokens: 90000
  raw_tokens: 90000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "POST /api/auth/jwt/login with any password against an account whose hashed_password is empty (Google-only or guest) returns 400 with detail LOGIN_BAD_CREDENTIALS, never a 500 / UnknownHashError."
    - "A normal password account still logs in (200 + bearer token) and a wrong password still returns 400."
    - "POST /api/eval/remote/atomic-submit for a game deleted after the read phase returns 404 'Game not found' (the worker's existing transient/discard code), writes no game_best_moves / game_flaws rows, and raises no IntegrityError."
    - "A foreign-key violation raised inside the eval write session is mapped to 'game deleted' ONLY when its SQLSTATE is 23503 AND a post-rollback re-check finds the games row gone; any other IntegrityError still propagates."
    - "The drain lane (_full_drain_tick full path and its tier-4b minimal path) returns False instead of raising when the claimed game is deleted before or during its write session."
  artifacts:
    - app/users.py
    - app/services/eval_apply.py
    - app/routers/eval_remote.py
    - app/services/eval_drain.py
    - tests/test_auth.py
    - tests/services/test_eval_apply.py
    - tests/services/test_full_eval_drain.py
    - tests/test_eval_worker_endpoints.py
  key_links:
    - "fastapi_users router login -> UserManager.authenticate (override in app/users.py) -> returns None -> router raises 400 LOGIN_BAD_CREDENTIALS; the override must run BEFORE password_helper.verify_and_update ever sees an empty hash."
    - "_apply_atomic_submit / _full_drain_tick / _tier4b_minimal_drain_tick write sessions -> eval_apply.commit_unless_game_deleted -> apply_full_eval (or the tier-4b upsert) + commit; a None return must map to 404 (router) or return False (drain)."
    - "remote worker (scripts/remote_eval_worker.py _TRANSIENT_HTTP_STATUSES includes 404) -> the 404 is ridden out silently and the next cycle leases a different game, so the deleted game is dropped, not retried."
---

<objective>
Fix two production Sentry bugs, one task and one commit per bug.

1. FLAWCHESS-BQ / FLAWCHESS-2A: a password login against an account with `hashed_password = ""` (Google-only accounts and guests, see app/services/guest_service.py lines 41 and 173) 500s because pwdlib's `verify_and_update` raises `UnknownHashError` on an empty hash and fastapi-users' `BaseUserManager.authenticate` (.venv/lib/python3.14/site-packages/fastapi_users/manager.py lines 636-665) calls it unguarded. The frontend LoginForm also Sentry-captures every non-400 login failure, which is likely the second issue ID.
2. FLAWCHESS-A0: `/api/eval/remote/atomic-submit` 500s with `ForeignKeyViolation` on `game_best_moves_game_id_fkey` when the leased game is deleted between the read phase and the write session commit. The drain lane funnels through the same `apply_full_eval` (and its tier-4b branch writes `game_best_moves` directly), so it hits the same race and currently Sentry-captures it in `run_full_eval_drain`'s catch-all.

Purpose: stop two recurring 500s / Sentry issues with no behavior change for the happy paths.
Output: a `UserManager.authenticate` override, a shared `commit_unless_game_deleted` helper wired into all three eval write sessions, regression tests, one CHANGELOG bullet.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@.planning/STATE.md
@app/users.py
@app/services/guest_service.py

Key facts gathered during planning (do not re-derive):

- fastapi-users `authenticate` (manager.py 636-665): `try: user = await self.get_by_email(credentials.username) / except exceptions.UserNotExists: self.password_helper.hash(credentials.password); return None`, then `verified, updated_password_hash = self.password_helper.verify_and_update(credentials.password, user.hashed_password)`, then optional `self.user_db.update(user, {"hashed_password": ...})`. The login router maps a None return to 400 `LOGIN_BAD_CREDENTIALS`. The frontend (frontend/src/components/auth/LoginForm.tsx ~line 47) shows "Invalid email or password." for 400/401 and Sentry-captures anything else.
- `UserManager.on_after_forgot_password` in app/users.py already gates on `if not user.hashed_password` (credential state, not account type). Reuse exactly that predicate.
- tests/test_password_reset.py `_create_direct_user` (lines ~79-116) builds a user row with `hashed_password=""` via `app.core.database.async_session_maker`. tests/test_auth.py `TestLogin` already has `test_login_returns_access_token` (normal login) and `test_login_wrong_password_returns_400`.
- app/routers/eval_remote.py `_apply_atomic_submit` (starts ~line 1200): read phase already raises `HTTPException(404, "Game not found")` when the game is missing (line ~1262). The write session is at ~lines 1435-1484: `async with async_session_maker() as write_session:` -> `failed_ply_count, stamp_complete, flaws_written = await apply_full_eval(write_session, ...)` -> `await write_session.commit()`. Between the read phase and the write session run the CPU-heavy steps (`_derive_atomic_sentinel_lines`, `_build_best_move_candidates` at ~line 1401), which is the widest deletion window. `functools` is already imported there.
- scripts/remote_eval_worker.py: `_TRANSIENT_HTTP_STATUSES = frozenset({401, 404, 409, 425, 429})` (line 93); `_handle_atomic_response` calls `submit_resp.raise_for_status()` and `_is_expected_transient` rides a 404 out silently, then the next cycle leases a new game. So 404 is already the correct "discard" contract. No worker change.
- app/services/eval_apply.py `apply_full_eval` (~line 2789) returns `tuple[int, bool, int]`, takes `pg_advisory_xact_lock(_game_write_lock_key(game_id))` as its FIRST statement (260825-v8g invariant: the advisory lock must stay the first lock acquisition), then UPDATEs game_positions, classifies, and upserts best-move rows via `_upsert_best_move_rows` (~line 2455) with no try/except (WR-01 fail-closed). eval_apply has no module logger.
- app/repositories/game_repository.py `delete_all_games_for_user` (line 308) deletes `game_positions` FIRST and `games` SECOND (children then parent). This is why a `SELECT ... FOR KEY SHARE` on the games row is NOT used here: our write session would hold the parent-row lock and then wait on child rows the deleter already holds while the deleter waits on our parent lock, which is a deadlock cycle that PostgreSQL resolves by aborting one side (possibly the user's delete). It would also break the advisory-lock-first invariant. The same bulk delete also explains the likely prod sequence: our game_positions UPDATE blocks behind the deleter, the deleter commits, our UPDATEs hit 0 rows, and the next FK-checked insert (game_best_moves) fails. So an in-transaction FK catch is required, not optional; a pre-check alone cannot close it.
- SQLAlchemy's asyncpg dialect exposes the Postgres SQLSTATE on the translated error: `getattr(exc.orig, "sqlstate", None)`; foreign-key violation is `"23503"`.
- app/services/eval_drain.py: `_full_drain_tick` (line ~1290) already returns False when the game is deleted between claim and load (line ~1347, "Game deleted between claim and load — nothing to do."). Its write session is at ~lines 1510-1552 (`apply_full_eval(...)` then `await write_session.commit()`). `_tier4b_minimal_drain_tick` write session is at ~lines 1281-1285 (`_upsert_best_move_rows` + optional `_mark_best_moves_completed` + commit), and it writes `game_best_moves` directly, the exact FLAWCHESS-A0 constraint. `run_full_eval_drain` Sentry-captures any exception from a tick.
- `_build_best_move_candidates` returns [] when the game is already gone at its `_fetch_rating_metadata` read, so a test that wants to reproduce the real FK violation must delete the game AFTER the builder produced rows (wrap the real builder, or return a hand-built row). GameBestMove row keys: game_id, ply, maia_prob (NOT NULL), best_cp, best_mate, second_cp, second_mate.
- Test harnesses: tests/test_eval_worker_endpoints.py `TestAtomicSubmitEndpoint` (line 2907; see `test_atomic_submit_gates_tactic_tag_and_stamps_both_markers` for the setup with `_SIX_PLY_PGN_142`, `_BLUNDER_SUBMIT_EVALS_142`, `_patch_router_session`, `_make_client`, `_ATOMIC_SUBMIT_URL`, `_delete_games`, `_count_game_best_moves`). tests/services/test_full_eval_drain.py `_patch_drain_for_tick_tests` (~line 760), `TestMarkerWrite.test_marker_set_after_drain` (~line 825), and `test_full_drain_tick_tier4b_minimal_path` (~line 2556, produces exactly one game_best_moves row at ply 6). tests/services/test_eval_apply.py has `ea_session_maker` / `ea_user` fixtures and a local `_insert_game` helper.
- Project memory: eval lottery tests are GLOBAL+random, so every non-guest Game a test inserts needs finally-cleanup (idempotent `_delete_games` in `finally`, even when the test body deletes the game itself). Do not disturb the post-move shift or the 4-way diff/upsert inside apply_full_eval.
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Empty-hash accounts get 400 bad credentials on password login (FLAWCHESS-BQ, FLAWCHESS-2A)</name>
  <files>app/users.py, tests/test_auth.py, CHANGELOG.md</files>
  <behavior>
    - Test A (new, parametrized over is_guest False/True): a user row created directly with hashed_password="" (mirror tests/test_password_reset.py `_create_direct_user`, unique uuid email) -> POST /api/auth/jwt/login with username=email and any non-empty password returns 400 and response JSON detail == "LOGIN_BAD_CREDENTIALS".
    - Existing TestLogin tests keep passing: a registered user logs in with 200 + access_token, a wrong password returns 400.
  </behavior>
  <action>
    Tracer for the login path (HTTP login route -> UserManager -> pwdlib). The two bugs in this plan are independent, so this task is a standalone vertical slice with its own end-to-end verify.

    RED: add the parametrized regression test to `TestLogin` in tests/test_auth.py (a small module-level helper that inserts the empty-hash user through `app.core.database.async_session_maker`, same field set as `_create_direct_user` in tests/test_password_reset.py, with `is_guest` taken from the parameter). Run it against the unfixed code and confirm it fails (the ASGI transport re-raises pwdlib `UnknownHashError`). Users are not games, so no finally-cleanup is required (test_auth.py's documented convention is unique emails, no rollback).

    GREEN: in app/users.py, add an `authenticate(self, credentials: OAuth2PasswordRequestForm) -> User | None` override on `UserManager` (import `OAuth2PasswordRequestForm` from `fastapi.security` and `exceptions` from `fastapi_users`). Mirror the upstream structure: look the user up with `self.get_by_email(credentials.username)`; on `exceptions.UserNotExists` run `self.password_helper.hash(credentials.password)` and return None (exactly as upstream). If the user exists but `not user.hashed_password` (the same credential-state predicate `on_after_forgot_password` uses; do not check is_guest or oauth accounts), run the same dummy `self.password_helper.hash(credentials.password)` for timing parity with the missing-user branch and return None. Otherwise `return await super().authenticate(credentials)`, so verify_and_update and the hash-upgrade write stay owned by fastapi-users (this costs one extra indexed email lookup per real login, which is negligible and keeps upstream behavior inherited). No Sentry capture: this is an expected bad-credentials outcome. Add a comment at the fix site naming FLAWCHESS-BQ / FLAWCHESS-2A and explaining what broke: Google-only and guest accounts store an empty hash, pwdlib cannot identify an empty hash and raises UnknownHashError, fastapi-users' authenticate does not catch it, so a password login against such an account returned 500 instead of bad credentials. Keep the response identical to a wrong password (same 400 detail) so the endpoint does not reveal which accounts are Google-only.

    CHANGELOG.md: append one bullet under `### Fixed` inside `## [Unreleased]` (the heading already exists above `## [v2.19]`), plain user-facing wording with sparse em-dashes, e.g. that signing in with an email and password on an account created through Google now shows the usual "Invalid email or password" message instead of failing with a server error (FLAWCHESS-BQ).

    Commit (one commit for this task): subject `fix(quick-260925-ine): treat empty-hash accounts as bad credentials on password login`; body must contain the lines `Fixes FLAWCHESS-BQ` and `Fixes FLAWCHESS-2A`, then the attribution trailer lines from the session's system reminder.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/test_auth.py tests/test_password_reset.py -x -q && uv run ruff check app/users.py tests/test_auth.py && uv run ruff format --check app/users.py tests/test_auth.py && uv run ty check app/users.py tests/test_auth.py && MSG="$(git log -1 --format=%B)" && printf '%s\n' "$MSG" | grep -q '^Fixes FLAWCHESS-BQ$' && printf '%s\n' "$MSG" | grep -q '^Fixes FLAWCHESS-2A$'</automated>
  </verify>
  <done>New parametrized test fails before the override and passes after; all of tests/test_auth.py and tests/test_password_reset.py pass; ruff and ty are clean on touched files; the commit body carries both `Fixes FLAWCHESS-BQ` and `Fixes FLAWCHESS-2A` (each line matched by its own grep -q); CHANGELOG has the Fixed bullet.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Deleted-game race in eval write sessions maps to 404 / tick no-op instead of an FK 500 (FLAWCHESS-A0)</name>
  <files>app/services/eval_apply.py, app/routers/eval_remote.py, app/services/eval_drain.py, tests/services/test_eval_apply.py, tests/services/test_full_eval_drain.py, tests/test_eval_worker_endpoints.py</files>
  <behavior>
    - Helper, pre-check: game deleted before the call -> `commit_unless_game_deleted` returns None and the write callable is never awaited (use an AsyncMock and assert not awaited).
    - Helper, in-transaction race: game exists at the pre-check; the write callable deletes the game from a SEPARATE `ea_session_maker()` session and commits, then inserts a GameBestMove row for that game_id in the passed write session -> helper returns None, raises nothing, and zero game_best_moves rows exist for the game afterwards.
    - Helper, narrowness: game exists and stays; the write callable inserts a GameBestMove row for a game_id that does not exist (the seeded id plus a large offset) -> `sqlalchemy.exc.IntegrityError` propagates out of the helper, and the seeded game still exists.
    - Router: in `TestAtomicSubmitEndpoint`, seed the same game as `test_atomic_submit_gates_tactic_tag_and_stamps_both_markers` (`_SIX_PLY_PGN_142`, six positions, `_BLUNDER_SUBMIT_EVALS_142` payload, `_patch_router_session`), and monkeypatch `eval_remote_module._build_best_move_candidates` with an async fake that deletes the game via `_delete_games(eval_worker_session_maker, [game_id])` and returns one hand-built row for (game_id, ply 2) with the full GameBestMove key set. POST /atomic-submit -> 404 with detail "Game not found", the games row is gone, `_count_game_best_moves(...) == 0`, zero game_flaws rows. Reverting the fix must reproduce the prod IntegrityError on game_best_moves_game_id_fkey (the ASGI transport raises it into the test).
    - Drain full path: mirror `test_marker_set_after_drain` (same `_patch_drain_for_tick_tests`, engine mock and positions) and monkeypatch `drain_module._build_best_move_candidates` with a fake that deletes the game and returns one hand-built row for (game_id, ply 0) -> `await drain_module._full_drain_tick()` returns False, raises nothing, zero game_best_moves rows.
    - Drain tier-4b path: mirror `test_full_drain_tick_tier4b_minimal_path`, but wrap the REAL `drain_module._build_best_move_candidates`: await the real builder (one row at ply 6 while the game still exists), then delete the game, then return the rows -> `_full_drain_tick()` returns False, raises nothing, zero game_best_moves rows. Without the fix this raises the exact FLAWCHESS-A0 FK violation.
    - Every test that inserts a game keeps an idempotent `_delete_games` call in `finally`.
  </behavior>
  <action>
    RED: write all six tests listed in behavior first and run them against the unfixed code. The helper tests fail on import (helper absent), the router test and tier-4b test fail with IntegrityError, and the drain full-path test fails with IntegrityError or `processed is True`. Record which failure each shows in the SUMMARY (mutation-proof per project memory).

    GREEN, shared helper in app/services/eval_apply.py (per the orchestrator's preference order: a row lock was considered and rejected, see the context bullet on `delete_all_games_for_user` children-first ordering and the advisory-lock-first invariant; use a non-locking existence pre-check plus a narrow FK-violation catch instead):
    - Add a named constant `_PG_FOREIGN_KEY_VIOLATION_SQLSTATE = "23503"`, a private `_game_row_exists(session, game_id) -> bool` (plain `select(Game.id).where(Game.id == game_id)`, `scalar_one_or_none() is not None`, no FOR UPDATE / FOR KEY SHARE), and a public generic `commit_unless_game_deleted(write_session, game_id, write) -> T | None` where `write: Callable[[], Awaitable[T]]` (module-level `TypeVar`, matching app/services/train_pool.py's style; add `Awaitable` to the collections.abc import and `TypeVar` to the typing import). Behavior: if the pre-check finds no row, return None without calling `write`. Otherwise `result = await write()` then `await write_session.commit()` inside a `try`; on `sqlalchemy.exc.IntegrityError as exc`, `await write_session.rollback()`, and return None only when `getattr(exc.orig, "sqlstate", None) == _PG_FOREIGN_KEY_VIOLATION_SQLSTATE` AND a fresh `_game_row_exists` re-check (same session, new transaction after the rollback) returns False; in every other case re-raise. Return `result` on success. Docstring states that `write` must never return None (None is the "game deleted" signal). Put the full FLAWCHESS-A0 explanation in the docstring: what broke (a game deleted by the user, typically via `delete_all_games_for_user` or account deletion, between the eval read phase and the write commit made the next FK-checked insert, `game_best_moves_game_id_fkey`, fail and the atomic-submit request 500'd), why no row lock (deadlock cycle against the children-first bulk delete, and apply_full_eval's advisory lock must stay the first acquisition), and why the catch is narrow (only SQLSTATE 23503 with the game confirmed gone, so a genuine integrity bug still surfaces). Callers own logging; the helper does not log and never Sentry-captures.

    GREEN, router (app/routers/eval_remote.py `_apply_atomic_submit`): import `commit_unless_game_deleted` in the existing `from app.services.eval_apply import (...)` block. Inside the existing `async with async_session_maker() as write_session:` replace the direct `apply_full_eval(...)` call plus `await write_session.commit()` with `outcome = await commit_unless_game_deleted(write_session, game_id, lambda: apply_full_eval(write_session, ...))`, keeping every existing keyword argument and its surrounding comments verbatim (if ty rejects the lambda's inferred type, use a small local `async def` returning `tuple[int, bool, int]` instead). After the `async with` block, when `outcome is None`: `logger.info` a constant-format message with `game_id` and `worker_id` as %-args (e.g. "atomic-submit: game deleted before write, discarding (game_id=%s worker_id=%s)"), then raise `HTTPException(status_code=404, detail="Game not found")`, matching the read-phase 404 response that the worker already treats as transient and drops. Do not Sentry-capture. Then unpack `failed_ply_count, stamp_complete, flaws_written = outcome` and leave `_signal_flaw_completion` and the response unchanged. Add a short comment at this call site naming FLAWCHESS-A0 and pointing to the helper docstring. Extend the "Expected status codes" 404 line in `atomic_submit_eval`'s docstring to mention a game deleted mid-submit. This adds only a handful of lines to `_apply_atomic_submit`; do not move anything else.

    GREEN, drain lane (app/services/eval_drain.py): import `commit_unless_game_deleted` from eval_apply alongside `apply_full_eval`.
    - `_full_drain_tick`: wrap the existing write the same way (`lambda: apply_full_eval(write_session, ...)` with all kwargs verbatim), and when the result is None, `logger.info` a constant-format message with game_id and `return False`, mirroring the existing "Game deleted between claim and load" early return.
    - `_tier4b_minimal_drain_tick`: extract the write-session body into a small module-level `_write_tier4b_best_moves(write_session, game_id, best_move_rows, maia_available) -> int` that runs `_upsert_best_move_rows` and the conditional `_mark_best_moves_completed` and returns `len(best_move_rows)` (non-None by construction), call it through `commit_unless_game_deleted` inside the existing `async with`, and on None `logger.info` and `return False`.
    - Both sites get a one-line FLAWCHESS-A0 comment. No Sentry capture on these branches.

    Size rules: nesting depth stays at or under 4 and logic LOC well under 200 in every touched function; the helper is where the new branching lives.

    Commit (one commit for this task): subject `fix(quick-260925-ine): drop eval writes for games deleted mid-submit instead of a FK 500`; body must contain the line `Fixes FLAWCHESS-A0`, a sentence that the drain lane (full and tier-4b paths) is covered by the same helper, then the attribution trailer lines from the session's system reminder.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest -n auto -x -q tests/services/test_eval_apply.py tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py && uv run ruff check app/services/eval_apply.py app/routers/eval_remote.py app/services/eval_drain.py tests/services/test_eval_apply.py tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py && uv run ruff format --check app/services/eval_apply.py app/routers/eval_remote.py app/services/eval_drain.py tests/services/test_eval_apply.py tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py && uv run ty check app/services/eval_apply.py app/routers/eval_remote.py app/services/eval_drain.py tests/services/test_eval_apply.py tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py && uv run python scripts/check_function_size.py app/services/eval_apply.py app/routers/eval_remote.py app/services/eval_drain.py --fail-over-depth 4 --fail-over-loc 200 && test -z "$(grep -L FLAWCHESS-A0 app/services/eval_apply.py app/routers/eval_remote.py app/services/eval_drain.py)" && MSG="$(git log -1 --format=%B)" && printf '%s\n' "$MSG" | grep -q '^Fixes FLAWCHESS-A0$'</automated>
  </verify>
  <done>All six new tests failed before the fix (failure mode recorded in the SUMMARY) and pass after; the three eval test modules pass in full; ruff, format check, ty and check_function_size are clean on touched files; each of the three app files mentions FLAWCHESS-A0 at least once; the commit body carries `Fixes FLAWCHESS-A0`.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| anonymous client -> POST /api/auth/jwt/login | untrusted email + password; response and timing must not reveal account type |
| remote eval worker -> POST /api/eval/remote/atomic-submit | operator-token authenticated, but payload and timing are worker-controlled |
| concurrent user delete -> eval write session | a user-initiated games/account delete races the eval writer on the same game rows |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-ine-01 | Information disclosure | UserManager.authenticate override | medium | mitigate | Empty-hash accounts return the identical 400 LOGIN_BAD_CREDENTIALS as a wrong password, and run a dummy password_helper.hash for timing parity with upstream's missing-user branch, so the endpoint does not reveal which emails are Google-only or guest accounts. |
| T-ine-02 | Spoofing | UserManager.authenticate override | high | mitigate | The empty-hash branch only ever returns None (never a user); real verification stays in super().authenticate, so no path authenticates without a verified hash. Regression test asserts 400 for an empty-hash account. |
| T-ine-03 | Tampering | commit_unless_game_deleted IntegrityError catch | medium | mitigate | Catch is limited to SQLSTATE 23503 AND a post-rollback re-check that the games row is gone; any other integrity error re-raises (narrowness test), so genuine data-integrity bugs still reach Sentry. |
| T-ine-04 | Denial of service | eval write session vs bulk games delete | medium | mitigate | No new row lock is taken (the rejected FOR KEY SHARE would form a deadlock cycle with delete_all_games_for_user's children-first deletes and could abort the user's delete); the advisory lock stays the first acquisition. |
| T-ine-05 | Repudiation | discarded submits | low | accept | A discarded submit is logged at INFO only (prod keeps WARNING+ in docker logs), and its heartbeat counters are rolled back. Acceptable: the game no longer exists and there is nothing to attribute. |
</threat_model>

<verification>
- `uv run pytest tests/test_auth.py tests/test_password_reset.py -x -q` green.
- `uv run pytest -n auto -x -q tests/services/test_eval_apply.py tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py` green.
- ruff check, ruff format --check and ty clean on every touched file; check_function_size clean on the three eval app files.
- Two commits on the current branch: Task 1's body has `Fixes FLAWCHESS-BQ` and `Fixes FLAWCHESS-2A`, Task 2's body has `Fixes FLAWCHESS-A0`.
- Full pre-merge gate is NOT required here (quick task on main, relevant tests only per the request).
</verification>

<success_criteria>
- Password login against an empty-hash account returns 400 bad credentials (no 500, no UnknownHashError, no frontend Sentry capture).
- atomic-submit for a game deleted mid-submit returns 404 and writes nothing; the drain lane's full and tier-4b paths return False instead of raising into the Sentry catch-all.
- Each new regression test demonstrably failed before its fix.
</success_criteria>

<output>
Create `.planning/quick/260925-ine-fix-sentry-flawchess-bq-2a-empty-hash-lo/260925-ine-SUMMARY.md` when done
</output>
