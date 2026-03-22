---
type: quick
autonomous: true
files_modified:
  - frontend/src/pages/Home.tsx
---

<objective>
Fix new user routing so authenticated users with 0 games are redirected to /import instead of /openings.

Purpose: New users who just registered see an empty openings page with no guidance. They should land on the import page to get started.
Output: Updated HomePage redirect logic in Home.tsx
</objective>

<context>
@frontend/src/pages/Home.tsx
@frontend/src/hooks/useUserProfile.ts
@frontend/src/types/users.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add game-count-aware redirect to HomePage</name>
  <files>frontend/src/pages/Home.tsx</files>
  <action>
Replace the `HomePage` export component (lines 267-271) with game-count-aware routing:

1. Import `useUserProfile` from `@/hooks/useUserProfile`
2. In `HomePage`, after the existing `useAuth()` call, conditionally call `useUserProfile()` only when authenticated
3. Redirect logic for authenticated users:
   - While profile is loading (`isLoading` is true): render a minimal centered spinner or empty fragment to avoid flash (use the same Loader2 spinner pattern used elsewhere in the app, or a simple `null` return if brief enough)
   - If profile loaded and `chess_com_game_count + lichess_game_count === 0`: redirect to `/import`
   - Otherwise: redirect to `/openings` (existing behavior)
4. Unauthenticated users continue to see `HomePageContent` (no change)

Important: The `useUserProfile` query has `staleTime: 300_000` so for returning users this will be near-instant from cache. The loading state only matters on first visit or after cache expiry.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>
- Authenticated user with 0 games on both platforms is redirected to /import
- Authenticated user with any games is redirected to /openings
- Unauthenticated user sees the landing page
- No TypeScript errors
  </done>
</task>

</tasks>

<verification>
1. TypeScript compiles without errors
2. Manual: Log in as new user with 0 games -> lands on /import
3. Manual: Log in as user with games -> lands on /openings
4. Manual: Visit / unauthenticated -> see landing page
</verification>

<success_criteria>
New users are guided to import page; existing users go to openings as before.
</success_criteria>
