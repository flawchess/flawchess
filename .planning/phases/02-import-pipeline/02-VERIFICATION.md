---
phase: 02-import-pipeline
verified: 2026-03-11T15:00:00Z
status: passed
score: 18/18 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 15/15
  note: "Previous verification predated Plan 04 gap-closure commits (e87b739, 2d41b17). This verification covers all four plans including the UAT-identified chess.com error-handling gap."
  gaps_closed:
    - "Any non-200 archives response (410, 403, 500) raises a descriptive ValueError before .json() is called"
    - "Any non-200 individual archive response skips that archive gracefully rather than crashing the pipeline"
    - "Invalid/email-format chess.com usernames produce a failed job with readable error, not a background crash"
  gaps_remaining: []
  regressions: []
---

# Phase 2: Import Pipeline Verification Report

**Phase Goal:** Build async import pipeline for chess.com and lichess — background jobs fetch games, compute Zobrist hashes, bulk insert to PostgreSQL with incremental sync and duplicate prevention.
**Verified:** 2026-03-11T15:00:00Z
**Status:** PASSED
**Re-verification:** Yes — supersedes previous VERIFICATION.md which predated Plan 04 (gap-closure commits `2d41b17`, `e87b739`, `f7f3bde`).

---

## Goal Achievement

All must-haves are drawn from the four PLAN frontmatter `must_haves` blocks. Plans 01-03 contribute 15 truths; Plan 04 (gap-closure) contributes 3 additional truths.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ImportJob model exists with all fields needed for job tracking and incremental sync | VERIFIED | `app/models/import_job.py` — 11 fields present including `last_synced_at`, `completed_at`, `error_message` |
| 2 | Time control bucketing correctly classifies bullet/blitz/rapid/classical including increment | VERIFIED | `app/services/normalization.py` — `parse_time_control()` with `estimated = base + increment * 40`; 49 passing tests |
| 3 | chess.com and lichess game dicts normalize to a common dict format for Game model insertion | VERIFIED | `normalize_chesscom_game` and `normalize_lichess_game` both return full dicts matching all Game columns |
| 4 | Bulk game insert uses ON CONFLICT DO NOTHING and only returns IDs of newly inserted games | VERIFIED | `game_repository.py:27-31` — `pg_insert(Game).on_conflict_do_nothing(constraint="uq_games_platform_game_id").returning(Game.id)` |
| 5 | GamePosition rows are only created for newly inserted games (not duplicates) | VERIFIED | `_flush_batch` in `import_service.py` calls `bulk_insert_positions` only with IDs returned by `bulk_insert_games` |
| 6 | chess.com client fetches game archives sequentially with rate-limit delays and User-Agent header | VERIFIED | `chesscom_client.py:92` — `asyncio.sleep(0.15)`; `_HEADERS = {"User-Agent": USER_AGENT}` sent on every request |
| 7 | chess.com client supports incremental sync by filtering archive months before a given timestamp | VERIFIED | `_archive_before_timestamp()` helper at line 22; conditional skip at lines 86-89 |
| 8 | lichess client streams NDJSON line-by-line without buffering the full response | VERIFIED | `lichess_client.py:57-63` — `client.stream()` context manager + `async for line in response.aiter_lines()` |
| 9 | lichess client supports incremental sync via the since parameter (milliseconds) | VERIFIED | `params["since"] = str(since_ms)` at line 52; 9 passing tests confirm behavior |
| 10 | Both clients yield normalized game dicts ready for bulk insertion | VERIFIED | Both call `normalize_*_game()` before yielding; imports wired at module level |
| 11 | Invalid usernames raise ValueError with a clear message | VERIFIED | `chesscom_client.py:75` raises `ValueError(f"chess.com user '{username}' not found")` on 404; `lichess_client.py:61` raises similarly |
| 12 | POST /imports returns immediately with a job_id (does not block) | VERIFIED | `asyncio.create_task(import_service.run_import(job_id))` fires background task; returns `ImportStartedResponse` immediately |
| 13 | GET /imports/{job_id} returns current progress including games_fetched count | VERIFIED | Router returns `ImportStatusResponse` with `games_fetched`, `games_imported`, `status` from in-memory or DB |
| 14 | Re-sync detects last_synced_at and passes since parameter to platform client | VERIFIED | `_make_game_iterator()` reads `previous_job.last_synced_at` and passes as `since_timestamp`/`since_ms` |
| 15 | Zobrist hashes are computed and stored for each newly imported game | VERIFIED | `_flush_batch()` calls `hashes_for_game(pgn)` for every new game ID then inserts position rows |
| 16 | Any non-200 archives response (410, 403, 500) raises a descriptive ValueError before .json() is called | VERIFIED | `chesscom_client.py:76-80` — `if archives_resp.status_code != 200: raise ValueError(f"chess.com request failed (status {archives_resp.status_code}) for user '{username}'")`  |
| 17 | Any non-200 individual archive response skips that archive gracefully rather than crashing the pipeline | VERIFIED | `chesscom_client.py:102-103` — `if resp.status_code != 200: continue` after 429 retry logic, before `.json()` |
| 18 | Invalid/email-format chess.com usernames produce a failed job with readable error, not a background crash | VERIFIED | ValueError from truth 16 is caught by `run_import`'s top-level `except Exception as exc` handler, setting `job.status = FAILED` and `job.error = str(exc)` |

**Score:** 18/18 truths verified

---

## Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `app/models/import_job.py` | ImportJob SQLAlchemy model | VERIFIED | `class ImportJob(Base)` with all 11 required fields |
| `app/schemas/imports.py` | Pydantic import schemas | VERIFIED | `ImportRequest`, `ImportStartedResponse`, `ImportStatusResponse` |
| `app/services/normalization.py` | Platform-agnostic normalization utilities | VERIFIED | `parse_time_control`, `normalize_chesscom_game`, `normalize_lichess_game` all present |
| `app/repositories/game_repository.py` | Bulk insert with ON CONFLICT DO NOTHING | VERIFIED | `bulk_insert_games` + `bulk_insert_positions` |
| `app/repositories/import_job_repository.py` | CRUD for import_jobs table | VERIFIED | `create_import_job`, `update_import_job`, `get_import_job`, `get_latest_for_user_platform` |
| `app/services/chesscom_client.py` | Hardened async generator for chess.com games | VERIFIED | `fetch_chesscom_games` + `_archive_before_timestamp` + status-code guards before every `.json()` call |
| `app/services/lichess_client.py` | Async generator yielding normalized lichess games | VERIFIED | `fetch_lichess_games` with NDJSON streaming |
| `app/services/import_service.py` | Import orchestrator with in-memory job registry | VERIFIED | `create_job`, `get_job`, `find_active_job`, `run_import`, `_flush_batch`, `_make_game_iterator` |
| `app/routers/imports.py` | POST /imports and GET /imports/{job_id} endpoints | VERIFIED | `router` with both endpoints; `asyncio.create_task` wired |
| `app/main.py` | FastAPI app with imports router registered | VERIFIED | `app.include_router(imports.router)` at line 7 |
| `alembic/versions/9e234104d7f2_...py` | Migration for import_jobs table | VERIFIED | Alembic at head (`9e234104d7f2`); confirmed via `uv run alembic current` |
| `tests/test_normalization.py` | 49 normalization tests | VERIFIED | All pass |
| `tests/test_game_repository.py` | Repository tests against real PostgreSQL | VERIFIED | All pass with transaction rollback |
| `tests/test_chesscom_client.py` | 17 chess.com client tests (5 added in Plan 04) | VERIFIED | 17/17 pass including 410/403/500 regression tests |
| `tests/test_lichess_client.py` | lichess client unit tests | VERIFIED | All pass |
| `tests/test_import_service.py` | Import service unit tests | VERIFIED | All pass |
| `tests/test_imports_router.py` | Import router integration tests | VERIFIED | All pass |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/repositories/game_repository.py` | `app/models/game.py` | `pg_insert(Game).on_conflict_do_nothing().returning(Game.id)` | WIRED | Lines 27-31 |
| `app/services/chesscom_client.py` | `app/services/normalization.py` | `normalize_chesscom_game()` called on each raw game dict | WIRED | Import at line 14; called at line 107 |
| `app/services/lichess_client.py` | `app/services/normalization.py` | `normalize_lichess_game()` called on each raw NDJSON line | WIRED | Import at line 12; called at line 73 |
| `app/services/import_service.py` | `app/services/chesscom_client.py` | `fetch_chesscom_games()` called when platform is chess.com | WIRED | `chesscom_client.fetch_chesscom_games(...)` at line 215 |
| `app/services/import_service.py` | `app/services/lichess_client.py` | `fetch_lichess_games()` called when platform is lichess | WIRED | `lichess_client.fetch_lichess_games(...)` at line 232 |
| `app/services/import_service.py` | `app/services/zobrist.py` | `hashes_for_game(pgn)` called for each newly inserted game | WIRED | Import at line 23; called at line 299 |
| `app/services/import_service.py` | `app/repositories/game_repository.py` | `bulk_insert_games` + `bulk_insert_positions` for batch persistence | WIRED | Both called in `_flush_batch()` at lines 260, 317 |
| `app/routers/imports.py` | `app/services/import_service.py` | `create_job` + `asyncio.create_task(run_import)` in POST handler | WIRED | `asyncio.create_task(import_service.run_import(job_id))` at line 48 |
| `app/services/chesscom_client.py` | `archives_resp.status_code` | Non-200 guard before `.json()` on archives endpoint | WIRED | Lines 74-80: 404 check then `!= 200` check before `archives_resp.json()` |
| `app/services/chesscom_client.py` | `resp.status_code` | Non-200 guard before `.json()` on per-archive fetch | WIRED | Lines 102-103: `if resp.status_code != 200: continue` before `resp.json()` |

---

## Requirements Coverage

Phase 2 claims: IMP-01, IMP-02, IMP-03, IMP-04, INFRA-02 (across Plans 01-04).

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| IMP-01 | 02-02, 02-03, 02-04 | User can import games from chess.com | SATISFIED | `fetch_chesscom_games` + POST /imports wired; Plan 04 error hardening closes UAT gap for non-200 responses |
| IMP-02 | 02-02, 02-03 | User can import games from lichess | SATISFIED | `fetch_lichess_games` + POST /imports wired |
| IMP-03 | 02-01, 02-03 | User can re-sync to fetch only new games since last import | SATISFIED | `last_synced_at` stored on completion; `get_latest_for_user_platform` feeds since parameter to both clients |
| IMP-04 | 02-03 | User sees import progress and status while games are being fetched | SATISFIED | GET /imports/{job_id} returns live `games_fetched`, `games_imported`, `status` |
| INFRA-02 | 02-01, 02-03 | Game import runs as a background task (does not block API) | SATISFIED | `asyncio.create_task(import_service.run_import(job_id))` fires background task; POST returns immediately |

**Orphaned requirements check:** REQUIREMENTS.md maps IMP-01, IMP-02, IMP-03, IMP-04, INFRA-02 to Phase 2. All five are claimed across the four plans. No orphaned requirements.

Note: IMP-05 (all game metadata stored) and IMP-06 (Zobrist hashes precomputed) are mapped to Phase 1 in REQUIREMENTS.md and are not Phase 2 requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/routers/imports.py` | 32, 35 | `TODO(phase-4): Replace hardcoded user_id=1 with FastAPI-Users` | Info | Intentional deferral documented in plan and summary. Not a gap. |
| `app/models/game.py` | 56 | Pre-existing ruff F821 forward reference | Info | Pre-existing from Phase 1; `# type: ignore[name-defined]` suppresses at runtime. Out of Phase 2 scope. |
| `app/models/game_position.py` | 28 | Pre-existing ruff F821 forward reference | Info | Pre-existing from Phase 1; `# type: ignore[name-defined]` suppresses at runtime. Out of Phase 2 scope. |

No blockers. No stubs. The `user_id=1` placeholder is intentional and documented for Phase 4.

---

## Test Results

```
132 passed in 0.54s
```

Breakdown by file:
- `tests/test_normalization.py` — 49 passed
- `tests/test_game_repository.py` — 13 passed (real PostgreSQL with transaction rollback)
- `tests/test_chesscom_client.py` — 17 passed (8 original + 4 helper tests + 5 Plan 04 regression tests)
- `tests/test_lichess_client.py` — 9 passed
- `tests/test_imports_router.py` — 10 passed
- `tests/test_import_service.py` — 18 passed
- `tests/test_zobrist.py` — 16 passed (Phase 1, no regressions)

---

## Commit Verification

All phase 2 commits verified in git history:

| Hash | Message |
|------|---------|
| `c38e9d8` | test(02-01): add failing tests for normalization utilities |
| `3e956bd` | feat(02-01): ImportJob model, schemas, normalization utilities, and migration |
| `c718f56` | test(02-01): add failing tests for game and import job repositories |
| `70dff45` | feat(02-01): game repository, import job repository, and db_session test fixture |
| `6fd7d3e` | fix(02-01): remove unused imports from test files |
| `501477a` | test(02-02): add failing tests for chess.com API client |
| `f5c54ec` | feat(02-02): implement chess.com API client |
| `95384dd` | test(02-02): add failing tests for lichess API client |
| `4ff2d59` | feat(02-02): implement lichess API client |
| `0e68bd5` | feat(02-03): import service with job registry and background orchestrator |
| `471afaf` | feat(02-03): import router endpoints and FastAPI wiring |
| `2d41b17` | test(02-04): add failing regression tests for non-200 archives and archive-fetch responses |
| `e87b739` | feat(02-04): harden chesscom_client status-code checks before .json() calls |

---

## Human Verification Required

### 1. End-to-End Import with Real chess.com Account

**Test:** Run the dev server and POST `/imports` with a real chess.com username. Poll GET `/imports/{job_id}` every second.
**Expected:** `games_fetched` increments in real time; status transitions `pending -> in_progress -> completed`; games and positions appear in the database.
**Why human:** Requires a real chess.com account, live HTTP calls, and real PostgreSQL write-through — not covered by unit tests with mocked HTTP.

### 2. End-to-End Import with Real lichess Account

**Test:** Run the dev server and POST `/imports` with a real lichess username. Verify NDJSON streaming behaves correctly over a large game history.
**Expected:** All games stream without buffering issues; no memory spike; job completes successfully.
**Why human:** Requires a real lichess account and live streaming behavior that cannot be validated with unit test mocks.

### 3. Incremental Re-sync Correctness

**Test:** Run a full import, wait for new games, then POST `/imports` again for the same user. Verify `games_imported` count equals only the number of new games.
**Expected:** Only new games added; total DB count increases by exactly the new game count; no duplicates.
**Why human:** Requires actual new games played between two import runs on a real account.

### 4. Email-Format Username Produces Failed Job (UAT Gap Regression Confirmation)

**Test:** POST `/imports` with `{"platform": "chess.com", "username": "user@example.com"}`. Poll GET `/imports/{job_id}`.
**Expected:** Job transitions to `status: "failed"` with a readable error message containing the 410 status code — not a background crash with JSONDecodeError.
**Why human:** UAT originally identified this gap. Automated regression tests cover 410 behavior with mocks; a live confirmation against the real chess.com API validates the full end-to-end fix.

---

## Summary

Phase 2 goal fully achieved across all four plans. All 18 observable truths verified against the actual codebase. The previous VERIFICATION.md captured the state before Plan 04 executed — this re-verification incorporates the gap-closure work.

The full import pipeline is operational:

1. POST /imports fires `asyncio.create_task` and returns a `job_id` immediately.
2. The background task fetches games from the appropriate platform client, batches in groups of 50, bulk inserts with ON CONFLICT DO NOTHING, computes Zobrist hashes for new games only, inserts position rows, and updates the DB record.
3. GET /imports/{job_id} returns live in-memory progress or historical DB state.
4. Incremental sync reads `last_synced_at` from the previous completed job and passes it to both platform clients.
5. Duplicate import prevention via `find_active_job` returns the existing active job.
6. Failed imports capture the error message and always reach a terminal state.
7. chess.com client guards every `.json()` call with a status-code check — 410/403/500 on archives raises `ValueError` cleanly; per-archive non-200 skips that month without aborting the full import (UAT gap closed by Plan 04).

Four human-verification items are noted — three for end-to-end platform testing, one for live regression confirmation of the UAT gap fix.

---

_Verified: 2026-03-11T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
