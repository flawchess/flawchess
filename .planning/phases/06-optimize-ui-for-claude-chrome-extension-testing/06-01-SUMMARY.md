---
phase: 06-optimize-ui-for-claude-chrome-extension-testing
plan: 01
subsystem: ui
tags: [react, typescript, testing, accessibility, data-testid, aria, semantic-html]

# Dependency graph
requires: []
provides:
  - data-testid on every interactive element across all non-board frontend components
  - Semantic <nav> wrapper for main navigation
  - BookmarkCard label converted from <span onClick> to semantic <button>
  - aria-label and aria-pressed on icon-only and toggle buttons
affects: [06-02, browser-automation, chrome-extension-testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "data-testid naming: kebab-case, component-prefixed ({component}-{element}-{qualifier})"
    - "nav-{page} for nav links, btn-{action} for buttons, filter-{name} for filter controls"
    - "board-btn-{action} for board controls, move-{ply} for move list, bookmark-{element}-{id} for dynamic bookmark elements"

key-files:
  created: []
  modified:
    - frontend/src/App.tsx
    - frontend/src/pages/Auth.tsx
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/pages/Bookmarks.tsx
    - frontend/src/pages/Stats.tsx
    - frontend/src/components/auth/LoginForm.tsx
    - frontend/src/components/auth/RegisterForm.tsx
    - frontend/src/components/import/ImportModal.tsx
    - frontend/src/components/import/ImportProgress.tsx
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/components/board/BoardControls.tsx
    - frontend/src/components/board/MoveList.tsx
    - frontend/src/components/bookmarks/BookmarkCard.tsx
    - frontend/src/components/results/GameTable.tsx

key-decisions:
  - "data-testid on Link element (not Button asChild wrapper) so it renders on the <a> tag in the DOM"
  - "BookmarkCard label converted from <span onClick> to <button> for semantics and accessibility"
  - "Pre-existing lint errors in ui/ components (react-refresh/only-export-components) are out of scope — confirmed pre-existing before this plan"

patterns-established:
  - "data-testid convention: nav-{label}, btn-{action}, filter-{name}, board-btn-{action}, move-{ply}, bookmark-{element}-{id}"
  - "All icon-only buttons keep existing aria-label; toggle buttons get aria-pressed for screen readers"

requirements-completed: [TEST-01, TEST-02, TEST-03]

# Metrics
duration: 7min
completed: 2026-03-13
---

# Phase 06 Plan 01: Accessibility and Test Selectors Summary

**data-testid, ARIA attributes, and semantic HTML added to all non-board frontend components, enabling stable browser automation targeting via the Claude Chrome extension**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-13T11:46:31Z
- **Completed:** 2026-03-13T11:53:44Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Added data-testid to every interactive element across auth, nav, dashboard, bookmarks, stats, import, filters, board controls, move list, bookmark cards, and game table
- Wrapped nav links in semantic `<nav aria-label="Main navigation">` element
- Converted BookmarkCard label from `<span onClick>` to `<button>` with aria-label and correct styling
- Added aria-label + aria-pressed to all time control and platform filter toggle buttons

## Task Commits

Each task was committed atomically:

1. **Task 1: Auth, nav, import, and page containers** - `a7161ab` (feat)
2. **Task 2: Filters, board controls, move list, bookmarks, game table** - `973679f` (feat)

## Files Created/Modified
- `frontend/src/App.tsx` - Semantic `<nav>`, data-testid on nav links and logout button
- `frontend/src/pages/Auth.tsx` - data-testid on auth-page, auth tabs
- `frontend/src/pages/Dashboard.tsx` - data-testid on dashboard-page, action buttons, bookmark dialog
- `frontend/src/pages/Bookmarks.tsx` - data-testid on bookmarks-page
- `frontend/src/pages/Stats.tsx` - data-testid on stats-page and analyze button
- `frontend/src/components/auth/LoginForm.tsx` - data-testid on email, password, submit, Google button
- `frontend/src/components/auth/RegisterForm.tsx` - data-testid on email, password, submit, Google button
- `frontend/src/components/import/ImportModal.tsx` - data-testid on modal, platform toggles, username input, cancel/submit
- `frontend/src/components/import/ImportProgress.tsx` - data-testid on progress container
- `frontend/src/components/filters/FilterPanel.tsx` - data-testid on all toggle groups and items, time/platform buttons with aria, more-filters trigger, recency select
- `frontend/src/components/board/BoardControls.tsx` - data-testid on all four control buttons
- `frontend/src/components/board/MoveList.tsx` - data-testid (move-{ply}) and aria-label on each move button
- `frontend/src/components/bookmarks/BookmarkCard.tsx` - Semantic label button, data-testid on card/label/input/load/delete
- `frontend/src/components/results/GameTable.tsx` - data-testid on table container and pagination prev/next

## Decisions Made
- `data-testid` placed on the `<Link>` element (not the `<Button asChild>` wrapper) so it ends up on the rendered `<a>` tag — Button with asChild merges props into the child element
- Pre-existing lint errors in `ui/` shadcn components (`react-refresh/only-export-components`) are out of scope and confirmed to pre-exist this plan

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `npm run lint` reported 5 pre-existing errors in shadcn ui components (badge, button, tabs, toggle) and FilterPanel's `DEFAULT_FILTERS` export — all confirmed pre-existing via `git stash` verification. Build passes cleanly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All non-board interactive elements now have stable data-testid selectors
- Plan 06-02 (ChessBoard click-to-move + board data-testid) is the remaining phase task
- Claude Chrome extension can now reliably target auth forms, nav, import flow, filters, bookmarks, and pagination

---
*Phase: 06-optimize-ui-for-claude-chrome-extension-testing*
*Completed: 2026-03-13*
