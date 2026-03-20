---
phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
plan: 03
subsystem: ui
tags: [react, tanstack-query, import, user-profile, localStorage]

# Dependency graph
requires:
  - phase: 09-01
    provides: GET /users/me/profile and PUT /users/me/profile backend endpoints with auto-save on import

provides:
  - useUserProfile query hook (5min stale time) and useUpdateUserProfile mutation hook
  - Redesigned ImportModal with sync view (returning user) and input view (first-time/edit)
  - localStorage username storage completely removed
  - Profile prefetched on Dashboard load; invalidated on import completion

affects:
  - Dashboard page (profile prefetch added)
  - ImportModal (full rewrite)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Derived state pattern for syncing external data to form fields (avoids react-hooks/set-state-in-effect)"
    - "Profile prefetch in parent component (Dashboard) so modal opens without loading flash"

key-files:
  created:
    - frontend/src/types/users.ts
    - frontend/src/hooks/useUserProfile.ts
  modified:
    - frontend/src/components/import/ImportModal.tsx
    - frontend/src/pages/Dashboard.tsx

key-decisions:
  - "Derived state pattern for profile sync and modal-close reset: uses prevProfile/prevOpen state compared during render to avoid react-hooks/set-state-in-effect lint violation"
  - "useUpdateUserProfile sets query data directly on success (not invalidate) for instant UI update"
  - "ImportModal two-mode: sync view (per-platform Sync buttons) and input view (both username fields simultaneously)"

patterns-established:
  - "Derived state pattern for modal reset: track prevOpen in state, compare during render, call setState inline — React-recommended pattern avoiding useEffect for state sync"

requirements-completed: [GAMES-03]

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 09 Plan 03: Import Modal Redesign Summary

**Two-mode ImportModal with backend-stored usernames replacing localStorage: sync view for returning users (per-platform Sync buttons) and input view for first-time users, powered by useUserProfile TanStack Query hook**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-14T15:49:57Z
- **Completed:** 2026-03-14T15:52:57Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created UserProfile type and useUserProfile/useUpdateUserProfile hooks with proper TanStack Query integration
- Rewrote ImportModal with sync view (stored usernames + per-platform Sync buttons) and input view (two username fields simultaneously)
- Removed all localStorage references from import-related code (getStoredUsername, setStoredUsername, last_sync)
- Added profile prefetch in DashboardPage and profile cache invalidation after import completes

## Task Commits

Each task was committed atomically:

1. **Task 1: Create UserProfile type and useUserProfile hook** - `327192f` (feat)
2. **Task 2: Redesign ImportModal with two-mode UI and remove localStorage** - `362c388` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/src/types/users.ts` - UserProfile interface { chess_com_username, lichess_username }
- `frontend/src/hooks/useUserProfile.ts` - useUserProfile query hook (5min stale, GET /users/me/profile) and useUpdateUserProfile mutation
- `frontend/src/components/import/ImportModal.tsx` - Full rewrite: two-mode UI with sync/input views, localStorage removed, all data-testid attributes
- `frontend/src/pages/Dashboard.tsx` - Added useUserProfile() prefetch call and queryClient.invalidateQueries(['userProfile']) on job done

## Decisions Made
- **Derived state pattern for profile sync and modal-close reset**: Profile data synced to input fields via `prevProfile` state compared during render (not useEffect) to avoid `react-hooks/set-state-in-effect` lint violation — same pattern as STATE.md "State-during-render reset for selectedSquare"
- **useUpdateUserProfile sets query data directly**: On mutation success, query data is set directly (not invalidated) for instant UI update without round trip
- **Both username fields shown simultaneously in input view**: No platform toggle needed — cleaner UX for importing from both platforms in one step

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced useEffect setState with derived state pattern to fix lint errors**
- **Found during:** Task 2 (ImportModal rewrite)
- **Issue:** Initial implementation used `useEffect(() => { setState(...) }, [dep])` which triggers `react-hooks/set-state-in-effect` ESLint error — prevents `npm run lint` from passing
- **Fix:** Replaced both useEffect calls with derived state pattern: track `prevProfile` and `prevOpen` in state, compare during render, call setState inline
- **Files modified:** frontend/src/components/import/ImportModal.tsx
- **Verification:** `npm run lint` passes for ImportModal (6 remaining errors are pre-existing in unrelated files)
- **Committed in:** 362c388 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — lint violation)
**Impact on plan:** Required fix for clean lint. Same derived state pattern already established in project (STATE.md key decision). No scope creep.

## Issues Encountered
- Pre-existing lint errors in FilterPanel.tsx, GameCardList.tsx, and shadcn/ui components (badge, button, tabs, toggle) — `react-refresh/only-export-components`. These are out of scope and deferred per deviation rules.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Import modal redesign complete; plan 09-03 done
- Phase 09 all 3 plans complete
- Backend profile endpoint (09-01) and modal UI (09-03) are wired end-to-end

---
*Phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination*
*Completed: 2026-03-14*
