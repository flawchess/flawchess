---
phase: 112-flaws-subtab-card-rework
plan: "02"
subsystem: library/flaws
tags: [endpoint, security, tdd, idor]
dependency_graph:
  requires:
    - "FlawListItem with eval_cp/eval_mate before/after + white/black rating (112-01)"
    - "_build_card builder + three batch repo functions (112-01)"
  provides:
    - "GET /api/library/games/{game_id} returning GameFlawCard"
    - "library_service.get_library_game(session, user_id, game_id) -> GameFlawCard | None"
    - "IDOR guard: None for cross-user or missing game (T-112-01)"
  affects:
    - "app/services/library_service.py"
    - "app/routers/library.py"
    - "tests/services/test_library_service.py"
    - "tests/test_library_router.py"
tech_stack:
  added: []
  patterns:
    - "Service returns None for IDOR/missing; router maps None to HTTP 404"
    - "TDD RED/GREEN flow: service tests, then router tests"
    - "Sequential awaits on single AsyncSession (no asyncio.gather)"
key_files:
  created: []
  modified:
    - app/services/library_service.py
    - app/routers/library.py
    - tests/services/test_library_service.py
    - tests/test_library_router.py
decisions:
  - "404 (not 403) returned for cross-user access to avoid confirming id existence (T-112-01)"
  - "IDOR guard lives at the service layer; router is thin (None -> 404 only)"
  - "Route uses relative path /games/{game_id} — no /library prefix in decorator (CLAUDE.md convention)"
metrics:
  duration: "~40 minutes"
  completed: "2026-06-09"
  tasks_completed: 2
  files_changed: 4
---

# Phase 112 Plan 02: Single-game endpoint Summary

Added `GET /api/library/games/{game_id}` returning one `GameFlawCard` for the authenticated user's own game, with a strict IDOR guard: returns 404 (not 403) for games the user does not own or that do not exist. Backs the Wave 3 "View game" modal (SC-7).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED (service) | Add failing tests for get_library_game | e56d3501 | tests/services/test_library_service.py |
| GREEN (service) | Implement get_library_game service function | a5895780 | app/services/library_service.py, tests/services/test_library_service.py |
| RED (router) | Add failing tests for GET /library/games/{game_id} | fe32a241 | tests/test_library_router.py |
| GREEN (router) | Add GET /library/games/{game_id} route + ruff reformat | fd60b51f | app/routers/library.py, + 3 others (ruff) |

## Key Changes

### Service function (app/services/library_service.py)
- Added `get_library_game(session, user_id, game_id) -> GameFlawCard | None`
- IDOR guard: `session.get(Game, game_id)` then `game.user_id != user_id` → return `None`
- Same three sequential batch queries as `get_library_games`: `fetch_page_analyzed_set`, `fetch_page_game_flaws`, `fetch_page_eval_positions`
- Calls `_build_card(game, flaw_rows, is_analyzed, positions)` — no inline card construction
- No `asyncio.gather` (CLAUDE.md §"Never use asyncio.gather on the same AsyncSession")
- Docstring notes IDOR guard and no-gather constraint

### Router endpoint (app/routers/library.py)
- Added `@router.get("/games/{game_id}", response_model=GameFlawCard)` (relative path, no `/library` prefix in decorator)
- Returns 200 + `GameFlawCard` for authenticated owner
- `HTTPException(status_code=404, detail="Game not found")` when service returns `None`
- `game_id` typed `int` → FastAPI rejects non-integer with 422 (T-112-05)
- `GameFlawCard` added to the `app.schemas.library` import block

### Tests
- Service level (3 cases in `TestGetLibraryGame`):
  - `test_own_game_returns_card`: analyzed game (9/10 positions with eval_cp) returns `GameFlawCard`
  - `test_cross_user_returns_none`: cross-user access returns `None` (IDOR guard at service level)
  - `test_missing_game_returns_none`: non-existent game_id returns `None`
- Router level (3 cases in `TestLibraryGameById`):
  - `test_library_game_by_id_own_game_200`: 200 + valid card for authenticated owner
  - `test_library_game_by_id_cross_user_404`: 404 with "Game not found" for cross-user access
  - `test_library_game_by_id_missing_404`: 404 for non-existent game_id
- `game_by_id_test_state` fixture seeds two committed users with analyzed positions and flaws

## TDD Gate Compliance

- RED commit (service): `e56d3501` — `test(112-02): add failing tests for get_library_game (RED)`
- GREEN commit (service): `a5895780` — `feat(112-02): implement get_library_game service function (GREEN)`
- RED commit (router): `fe32a241` — `test(112-02): add failing tests for GET /library/games/{game_id} (RED)`
- GREEN commit (router): `fd60b51f` — `feat(112-02): add GET /library/games/{game_id} route + ruff reformat (GREEN)`

## Deviations from Plan

None. Plan executed exactly as written.

## Known Stubs

None. The endpoint returns live data from `_build_card` using the same three batch queries as `get_library_games`.

## Threat Flags

No new threat surfaces introduced. The endpoint is covered by the plan's threat register:

| Threat ID | Mitigation |
|-----------|------------|
| T-112-01 | IDOR guard: `game.user_id != user_id` → None → 404. Cross-user 404 tested at service and router level. |
| T-112-04 | GameFlawCard schema never exposes `*_hash` columns (existing Phase 109 design). |
| T-112-05 | `game_id: int` path param — FastAPI rejects non-integer with 422. |

## Self-Check: PASSED

- [x] `app/services/library_service.py` contains `get_library_game`
- [x] `app/routers/library.py` contains `/games/{game_id}` route
- [x] `grep -n "/library/games" app/routers/library.py` returns nothing (prefix convention respected)
- [x] Commits `e56d3501`, `a5895780`, `fe32a241`, `fd60b51f` present in git log
- [x] 2469 backend tests pass, ty clean, ruff clean
