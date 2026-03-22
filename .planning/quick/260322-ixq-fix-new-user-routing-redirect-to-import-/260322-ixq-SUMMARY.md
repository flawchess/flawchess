---
type: quick
task_id: 260322-ixq
date: 2026-03-22
duration_minutes: 5
tags: [routing, ux, onboarding]
key_files:
  modified:
    - frontend/src/pages/Home.tsx
decisions:
  - Always call useUserProfile unconditionally (React hook rules) and skip redirect logic when unauthenticated
  - Show Loader2 spinner while profile loads to prevent wrong-page flash on first visit
---

# Quick Task 260322-ixq: Fix New User Routing — Redirect to /import Summary

Redirect authenticated users with 0 imported games to `/import` for onboarding instead of the empty `/openings` page.

## What Was Done

**Task 1: Add game-count-aware redirect to HomePage** — commit `ceaf8bf`

- Added `useUserProfile` import and `Loader2` icon to `Home.tsx`
- `HomePage` now calls `useUserProfile()` unconditionally (React hook rules require this) but only uses the result when a token is present
- While the profile is loading, renders a centered spinner to prevent flashing the wrong redirect
- After load: if `chess_com_game_count + lichess_game_count === 0` → redirect to `/import`; otherwise → redirect to `/openings` (previous behavior)
- Unauthenticated users continue to see `HomePageContent` landing page unchanged

## Behavior Summary

| User state | Result |
|---|---|
| Unauthenticated | Landing page |
| Authenticated, 0 games | Redirect to `/import` |
| Authenticated, any games | Redirect to `/openings` |
| Authenticated, profile loading | Centered spinner (brief) |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `frontend/src/pages/Home.tsx` — modified and verified
- Commit `ceaf8bf` — exists
- TypeScript: no errors (`npx tsc --noEmit` clean)
