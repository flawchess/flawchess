---
phase: quick
plan: 260319-oig
subsystem: auth, frontend, backend
tags: [auth, user-isolation, import-page, profile]
dependency_graph:
  requires: []
  provides: [user-isolation-fix, import-page-user-info]
  affects: [frontend/src/hooks/useAuth.ts, app/routers/users.py, app/schemas/users.py, app/repositories/game_repository.py, frontend/src/types/users.ts, frontend/src/pages/Import.tsx]
tech_stack:
  added: []
  patterns: [cache-after-token-swap, profile-endpoint-with-aggregates]
key_files:
  modified:
    - frontend/src/hooks/useAuth.ts
    - app/schemas/users.py
    - app/routers/users.py
    - app/repositories/game_repository.py
    - frontend/src/types/users.ts
    - frontend/src/pages/Import.tsx
decisions:
  - "queryClient.clear() after localStorage.setItem: ensures refetches triggered by the clear use the new token already in localStorage, preventing stale cross-user data in cache"
  - "Per-platform counts via count_games_by_platform repository function: groups by Game.platform returning a dict, router reads 'chess.com' and 'lichess' keys with .get() defaulting to 0"
metrics:
  duration: ~10 minutes
  completed: 2026-03-19
  tasks_completed: 2
  files_modified: 6
---

# Quick Task 260319-oig: Fix User Isolation Bug and Show User Email/Game Counts

**One-liner:** Moved `queryClient.clear()` after token storage to prevent stale cross-user cache reads, and added email + per-platform game counts to the profile endpoint and import page.

## Tasks Completed

### Task 1: Fix user isolation — move queryClient.clear() after token swap

**File:** `frontend/src/hooks/useAuth.ts`

The bug: `queryClient.clear()` was called at the top of `login()` before the POST request and before the new token was stored. Any active query observers that immediately refetched after the cache clear would use the OLD token still in localStorage, caching User A's data under User B's session.

Fix applied to both `login()` and `loginWithToken()`:
- Removed `queryClient.clear()` from before the API call
- Added `queryClient.clear()` AFTER `localStorage.setItem('auth_token', ...)` and BEFORE `setToken(...)`
- Added inline comments explaining the ordering requirement

`logout()` was already correct (clear before token removal is appropriate there).

### Task 2: Add email and per-platform game counts to profile endpoint and import page

**Backend:**
- `app/repositories/game_repository.py`: Added `count_games_by_platform(session, user_id)` — queries `Game` table grouped by `platform`, returns `dict[str, int]`
- `app/schemas/users.py`: Added `email: str`, `chess_com_game_count: int`, `lichess_game_count: int` to `UserProfileResponse`
- `app/routers/users.py`: Both `get_profile` and `update_profile` now import `game_repository`, call `count_games_by_platform`, and populate the new response fields from `user.email` and `counts.get(..., 0)`

**Frontend:**
- `frontend/src/types/users.ts`: Added `email: string`, `chess_com_game_count: number`, `lichess_game_count: number` to `UserProfile` interface
- `frontend/src/pages/Import.tsx`:
  - Added `"Logged in as {profile.email}"` paragraph below the `<h1>` heading with `data-testid="import-user-email"`
  - Each platform label row wrapped in a flex div showing the label + game count in muted text
  - chess.com count: `data-testid="import-game-count-chess-com"`
  - lichess count: `data-testid="import-game-count-lichess"`
  - Both counts only render when `profile` is loaded (guarded by `{profile && ...}`)

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `uv run python -c "from app.schemas.users import UserProfileResponse; print(list(UserProfileResponse.model_fields.keys()))"` — outputs all 7 fields including `email`, `chess_com_game_count`, `lichess_game_count`
- `cd frontend && npx tsc --noEmit` — zero errors after both tasks

## Self-Check

Key files:
- [x] `frontend/src/hooks/useAuth.ts` — modified
- [x] `app/repositories/game_repository.py` — modified (count_games_by_platform added)
- [x] `app/schemas/users.py` — modified (email, chess_com_game_count, lichess_game_count added)
- [x] `app/routers/users.py` — modified (both endpoints updated)
- [x] `frontend/src/types/users.ts` — modified (3 fields added)
- [x] `frontend/src/pages/Import.tsx` — modified (email + game counts displayed)

## Self-Check: PASSED
