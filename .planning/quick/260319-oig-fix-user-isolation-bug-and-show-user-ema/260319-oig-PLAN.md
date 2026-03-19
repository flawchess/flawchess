---
phase: quick
plan: 260319-oig
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/hooks/useAuth.ts
  - app/routers/users.py
  - app/schemas/users.py
  - app/repositories/game_repository.py
  - frontend/src/types/users.ts
  - frontend/src/hooks/useUserProfile.ts
  - frontend/src/pages/Import.tsx
autonomous: true
requirements: []

must_haves:
  truths:
    - "After user B logs in (replacing user A), all displayed data belongs to user B"
    - "Import page shows the current user's email address"
    - "Import page shows per-platform game counts (chess.com: N games, lichess: M games)"
  artifacts:
    - path: "frontend/src/hooks/useAuth.ts"
      provides: "Cache cleared AFTER token swap, not before"
    - path: "app/schemas/users.py"
      provides: "UserProfileResponse with email and per-platform game counts"
    - path: "frontend/src/pages/Import.tsx"
      provides: "Email and game count display on import page"
  key_links:
    - from: "frontend/src/hooks/useAuth.ts"
      to: "queryClient.clear()"
      via: "Called after localStorage token is set"
      pattern: "setItem.*clear"
    - from: "frontend/src/pages/Import.tsx"
      to: "/users/me/profile"
      via: "useUserProfile hook"
      pattern: "profile.*email|profile.*game_count"
---

<objective>
Fix user isolation bug where switching users shows stale data, and enhance the import page to show the current user's email and per-platform game counts.

Purpose: Prevent cross-user data leakage and give users visibility into their import state.
Output: Fixed auth cache clearing + enhanced import page with user info.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@frontend/src/hooks/useAuth.ts
@frontend/src/pages/Import.tsx
@frontend/src/hooks/useUserProfile.ts
@frontend/src/types/users.ts
@app/routers/users.py
@app/schemas/users.py
@app/repositories/game_repository.py
@app/repositories/user_repository.py
@app/models/user.py
@app/models/game.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix user isolation — move queryClient.clear() after token swap</name>
  <files>frontend/src/hooks/useAuth.ts</files>
  <action>
    The bug: in `login()`, `queryClient.clear()` is called BEFORE the login POST and token storage. Active query observers may immediately refetch after the clear, but the OLD token is still in localStorage (request interceptor reads from localStorage). These refetches return User A's data and cache it under User B's session.

    Fix `login()`:
    1. Remove `queryClient.clear()` from the top of the function (line 34)
    2. Add `queryClient.clear()` AFTER `localStorage.setItem('auth_token', access_token)` and BEFORE `setToken(access_token)` — this ensures the cache is wiped when the new token is already in place, so any refetches use the new token.

    The corrected login flow:
    ```
    const { access_token } = response.data;
    localStorage.setItem('auth_token', access_token);
    queryClient.clear();
    setToken(access_token);
    ```

    `loginWithToken` has the same issue — fix it the same way:
    ```
    localStorage.setItem('auth_token', externalToken);
    queryClient.clear();
    setToken(externalToken);
    ```

    `logout` is fine — clearing before removing the token is correct (we want to prevent any fetches with the old token).

    `register` calls `login` internally, so it inherits the fix.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit</automated>
  </verify>
  <done>queryClient.clear() executes after the new token is stored in localStorage in both login() and loginWithToken(), preventing stale-user data from being cached.</done>
</task>

<task type="auto">
  <name>Task 2: Add email and per-platform game counts to profile endpoint and import page</name>
  <files>
    app/schemas/users.py
    app/routers/users.py
    app/repositories/game_repository.py
    frontend/src/types/users.ts
    frontend/src/pages/Import.tsx
  </files>
  <action>
    **Backend — add per-platform game counts to profile:**

    1. In `app/repositories/game_repository.py`, add a new function:
       ```python
       async def count_games_by_platform(session: AsyncSession, user_id: int) -> dict[str, int]:
           """Return game counts grouped by platform for the given user."""
           result = await session.execute(
               select(Game.platform, func.count()).select_from(Game)
               .where(Game.user_id == user_id)
               .group_by(Game.platform)
           )
           return {row[0]: row[1] for row in result.all()}
       ```

    2. In `app/schemas/users.py`, add fields to `UserProfileResponse`:
       ```python
       email: str
       chess_com_game_count: int
       lichess_game_count: int
       ```

    3. In `app/routers/users.py`, update `get_profile` to:
       - Import `game_repository`
       - Call `game_repository.count_games_by_platform(session, user.id)` to get per-platform counts
       - Read email from `user.email` (available on the User model from FastAPI-Users)
       - Pass `email=user.email`, `chess_com_game_count=counts.get("chess.com", 0)`, `lichess_game_count=counts.get("lichess", 0)` to the response

    4. Also update `update_profile` response to include the same new fields (email from refreshed user, counts from game_repository).

    **Frontend — display on import page:**

    5. In `frontend/src/types/users.ts`, add to `UserProfile`:
       ```typescript
       email: string;
       chess_com_game_count: number;
       lichess_game_count: number;
       ```

    6. In `frontend/src/pages/Import.tsx`, below the `<h1>Import Games</h1>` heading and before the platform rows, add a small info section showing:
       - User email in muted text: `Logged in as {profile.email}`
       - This should display when `profile` is loaded (inside the `!profileLoading` branch)

    7. In each platform row, after the Label, show the game count in muted text. For chess.com: `{profile.chess_com_game_count} games`. For lichess: `{profile.lichess_game_count} games`. Use `text-xs text-muted-foreground` styling. Only show when profile is loaded.

    Add `data-testid` attributes per project rules:
    - `data-testid="import-user-email"` on the email text
    - `data-testid="import-game-count-chess-com"` on chess.com count
    - `data-testid="import-game-count-lichess"` on lichess count
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run python -c "from app.schemas.users import UserProfileResponse; print(UserProfileResponse.model_fields.keys())" && cd frontend && npx tsc --noEmit</automated>
  </verify>
  <done>Profile endpoint returns email + per-platform game counts. Import page displays user email and game counts next to each platform's sync row.</done>
</task>

</tasks>

<verification>
1. TypeScript compiles without errors
2. Backend schema includes email, chess_com_game_count, lichess_game_count
3. Manual test: log in as user A, import games, log out, log in as user B — user B should NOT see user A's data
4. Import page shows email and per-platform game counts
</verification>

<success_criteria>
- User isolation: switching users clears all cached data AFTER new token is stored
- Import page shows logged-in user's email
- Import page shows chess.com and lichess game counts per platform
- All data-testid attributes present on new elements
</success_criteria>

<output>
After completion, create `.planning/quick/260319-oig-fix-user-isolation-bug-and-show-user-ema/260319-oig-SUMMARY.md`
</output>
