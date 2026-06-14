---
phase: 120-headless-remote-trusted-operator-eval-worker-seed-048
plan: "02"
subsystem: api
tags: [fastapi, remote-eval, operator-auth, eval-drain, seed-044, seed-045, integration-tests]

requires:
  - phase: 120
    plan: "01"
    provides: Settings.EVAL_OPERATOR_TOKEN + Settings.EXPECTED_SF_VERSION + eval_remote schemas

provides:
  - POST /api/eval/remote/lease (claim tier-3 game → ply+FEN positions)
  - POST /api/eval/remote/submit (apply worker evals via SEED-044 write path)
  - require_operator_token FastAPI dependency (hmac.compare_digest, fail-closed)
  - tests/test_eval_worker_endpoints.py (10 integration tests)

affects:
  - app/main.py (eval_remote_router registered under /api)
  - 120-03 (CLI worker calls these two endpoints)

tech-stack:
  added: []
  patterns:
    - "Operator-token auth: optional Header dep, fail-closed on empty config (403), wrong token (401); hmac.compare_digest for constant-time compare"
    - "Session discipline: two short read sessions (claim + load), then ONE late write session encompassing all UPDATEs + commit (mirrors _full_drain_tick)"
    - "SEED-044 storage convention owned server-side: worker submits position-keyed evals; _apply_full_eval_results applies the +1 post-move shift"
    - "SEED-045 decision tree in submit: Path A (no holes → stamp), B (holes + under cap → retry), C (cap reached → stamp + Sentry warning)"

key-files:
  created:
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py
  modified:
    - app/main.py

key-decisions:
  - "require_operator_token uses optional Header parameter (str|None default=None) to avoid FastAPI 422 on missing header; unconfigured server always returns 403 regardless of header presence"
  - "response_model=None on lease endpoint (returns Response|LeaseResponse union — FastAPI cannot serialize Response in a response_model)"
  - "_build_lease_positions and _apply_submit extracted as private module-level helpers to keep endpoint functions under nesting depth 3 / 50 LOC"
  - "dedup_map is empty {} in submit — no cross-user dedup for remote submissions; worker already evaluated all positions (D-2)"

metrics:
  duration: ~35 min
  completed: "2026-06-14"
  tasks: 2
  files_modified: 3
---

# Phase 120 Plan 02: Eval Remote Router (Lease + Submit Endpoints) Summary

**POST /api/eval/remote/lease and POST /api/eval/remote/submit wired via thin FastAPI router reusing the existing SEED-044 eval_drain write path; operator-token auth gate (hmac.compare_digest, fail-closed); SEED-045 bounded-retry stamping; 10 integration tests covering auth, version gate, server-side shift, completion stamp, and idempotency.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-06-14T18:00:00Z
- **Completed:** 2026-06-14T18:13:53Z
- **Tasks:** 2
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- Created `app/routers/eval_remote.py` with:
  - `require_operator_token` dependency: `hmac.compare_digest` constant-time, fail-closed on unconfigured server (T-120-01)
  - `lease_eval_game` (POST `/lease`): calls `_claim_tier3_derived` directly (bypasses `EVAL_AUTO_DRAIN_ENABLED` gate), defers lichess games (204), builds `(ply, FEN, is_terminal)` lease response with terminal donor included
  - `submit_eval` (POST `/submit`): D-5 SF-version gate first, then reads phase + writes phase pattern, calls `_apply_full_eval_results` (server-side SEED-044 shift), `_classify_and_fill_oracle`, SEED-045 decision tree (paths A/B/C), `_signal_flaw_completion` after commit
- Registered `eval_remote_router` in `app/main.py` under `/api` prefix
- Created `tests/test_eval_worker_endpoints.py` with 10 integration tests (all green)
- Full test suite: 2628 passed, 10 skipped

## Task Commits

1. **Task 1: eval_remote router + main.py registration** - `4a4da8be` (feat)
2. **Task 2: integration tests + auth fix** - `0d7ae01b` (test)

## Files Created/Modified

- `app/routers/eval_remote.py` — New file: lease + submit endpoints, require_operator_token dep, _build_lease_positions and _apply_submit private helpers (375 lines)
- `tests/test_eval_worker_endpoints.py` — New file: 10 integration tests for auth, version gate, server-side shift, completion stamp, idempotency (593 lines)
- `app/main.py` — Added `eval_remote_router` import + `app.include_router(eval_remote_router, prefix="/api")`

## Decisions Made

- `require_operator_token` uses `Annotated[str | None, Header(alias="X-Operator-Token")] = None` to avoid FastAPI 422 on missing header. Unconfigured server always returns 403; configured server with missing or wrong token returns 401.
- `lease_eval_game` uses `response_model=None` to allow returning `Response | LeaseResponse` — FastAPI cannot derive a response schema from a union containing `starlette.responses.Response`.
- Private helpers `_build_lease_positions` and `_apply_submit` keep both endpoint bodies under nesting depth 3 and ~30 logic LOC each (CLAUDE.md coding guidelines).
- `dedup_map = {}` in submit: no cross-user dedup for remote submissions; worker evaluated all positions already; `_apply_full_eval_results` applies the +1 shift server-side (D-2).
- Test monkeypatching: `_claim_tier3_derived` patched in `app.routers.eval_remote` namespace per test to control which game is leased; `async_session_maker` patched in same namespace to route DB writes to the test DB.

## Deviations from Plan

**1. [Rule 1 - Bug] require_operator_token must accept optional header**
- **Found during:** Task 2 first test run (`test_lease_requires_operator_token` got 422 instead of 403)
- **Issue:** FastAPI validates required `str` Header before the dependency body runs. A missing `X-Operator-Token` header returns 422 (validation error) rather than allowing the dependency to return 403 for unconfigured server.
- **Fix:** Changed parameter to `str | None` with `= None` default. Added explicit `if x_operator_token is None` check after the `not configured` gate so behavior is: unconfigured server → 403 (regardless of header), configured server + missing/wrong header → 401.
- **Files modified:** `app/routers/eval_remote.py`
- **Commit:** `0d7ae01b` (included in Task 2 commit)

## Issues Encountered

- FastAPI 422 on missing `str` Header — fixed inline (deviation above).
- Test seeding bug: list comprehension used `{"ply": 0, "full_hash": 1000 + i, ...}` (all ply=0) instead of `{"ply": ply, ...}` — caught immediately by UniqueViolationError on game_positions PK; fixed in same edit pass before commit.

## User Setup Required

None — no new packages, no external services, no environment variable changes required for development. Production requires `EVAL_OPERATOR_TOKEN` and optionally `EXPECTED_SF_VERSION` in `.env` (added in Plan 120-01).

## Next Phase Readiness

- 120-03 (CLI worker) can call `POST /api/eval/remote/lease` and `POST /api/eval/remote/submit` via `httpx.AsyncClient` with `X-Operator-Token` header.
- No blockers.

## Known Stubs

None — both endpoints are fully wired to the existing eval_drain write path.

## Threat Flags

No new threat surfaces beyond what was documented in the plan's threat model (T-120-01 through T-120-SC). All mitigations from the threat register are implemented:
- T-120-01: `hmac.compare_digest` + fail-closed (403 when unconfigured)
- T-120-02: D-5 SF-version gate in submit (422 on mismatch)
- T-120-03: Server-side SEED-044 shift via `_apply_full_eval_results`; ply-keyed writes only land on server-derived targets; ON CONFLICT DO NOTHING for flaws (idempotent)

## Self-Check: PASSED

- FOUND: app/routers/eval_remote.py
- FOUND: tests/test_eval_worker_endpoints.py
- FOUND: commit 4a4da8be (Task 1)
- FOUND: commit 0d7ae01b (Task 2)
- FOUND: /api/eval/remote/lease registered on app
- FOUND: /api/eval/remote/submit registered on app
- 10/10 integration tests green
- 2628/2628 full suite tests green
