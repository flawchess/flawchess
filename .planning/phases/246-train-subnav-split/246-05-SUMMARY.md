---
phase: 246-train-subnav-split
plan: 05
subsystem: ui
tags: [react, react-router, tanstack-query, radix-toggle-group, vitest]
status: complete

requires:
  - phase: 246-train-subnav-split
    provides: "246-01 GET /train/archive wire shape; 246-02 URL-routed Train layout and latch; 246-04 TrainPuzzleCard; 246-08 Train layout with medal host"
provides:
  - "Archive as the third URL-routed Train tab (/train/archive = Mastered, /train/archive/parked = Parked)"
  - "trainApi.getArchive and TrainArchiveResponse"
  - "useTrainArchive(list, page) with ARCHIVE_PAGE_SIZE and a list-scoped placeholderData rule"
  - "buildArchivePath, parseArchivePage, ARCHIVE_PAGE_MAX in lib/trainRoute.ts"
  - "TrainArchiveTab: toggle with counts and explainers, grid, URL-held pagination, empty/loading/error states"
affects: [246-03, 246-06, 246-07]

actuals:
  tokens: 11400
  tasks: 2
  commits: 2
plan_head_before: fcfb5988c2a6e079d107bb14a0e01c92fadb8592
plan_head_after: 27240feb6258c9857cbf65175b803557eab3f651

tech-stack:
  added: []
  patterns:
    - "placeholderData as a function keyed on the query's list, so paging holds the old cards and a list switch shows the skeleton"
    - "Popover as a SIBLING of a ToggleGroupItem (inside the item its click would switch the list)"

key-files:
  created:
    - frontend/src/hooks/useTrainArchive.ts
    - frontend/src/components/train/TrainArchiveTab.tsx
    - frontend/src/components/train/__tests__/TrainArchiveTab.test.tsx
  modified:
    - frontend/src/types/train.ts
    - frontend/src/api/client.ts
    - frontend/src/lib/trainRoute.ts
    - frontend/src/lib/__tests__/trainRoute.test.ts
    - frontend/src/components/train/TrainSubnav.tsx
    - frontend/src/pages/Train.tsx
    - frontend/src/pages/__tests__/Train.subnav.test.tsx

key-decisions:
  - "Mastered is the default list and lives at /train/archive; Parked at /train/archive/parked"
  - "The over-range effect only replaces when the last page is below the requested page, so a stale response can never loop"
  - "The toggle stays visible in the loading, error and empty states so the other list is always one tap away"

requirements-completed: [D-01, D-04, D-05, D-06, D-09, D-15, D-16]

duration: 35min
completed: 2026-11-06
---

# Phase 246 Plan 05: Archive tab Summary

**Mastered / Parked toggle over a paginated two-column grid of puzzle cards, with list and page in the URL, deep-linkable with no session and no Worker.**

## Accomplishments

- `/train/archive` and `/train/archive/parked` parse to `{ tab: 'archive', list }`; `/train/archive/mastered` and other unknown paths redirect to `/train`. `TrainSubnav` gains the `Archive` trigger (`tab-train-archive`).
- `useTrainArchive` calls `GET /train/archive` with `limit=20` and `offset=(page-1)*20`, `refetchOnMount: 'always'`, and a `placeholderData` function that keeps the previous data only when the previous query was for the same list.
- `TrainArchiveTab`: toggle with `Mastered 12` / `Parked 3` counts from `useTrainProgress` (no number while progress is pending or failed), the two explainer popovers beside the items, `Pagination` when the list exceeds 20, `?page=` pushed on a page click (page 1 carries no param), over-range pages replaced to the last page without a history entry, a four-card skeleton at `h-56`, `LoadError` on failure, and a per-list empty state with a `Go to Today` link (no import button for any account).
- Archive panel in `Train.tsx` is a plain `mt-4` div with no `max-w-*`; the wrapper keeps the shared `max-w-7xl` class.
- `parseArchivePage` returns 1 for null, non-digits, `0`, `-3`, `1.5`, and caps at `ARCHIVE_PAGE_MAX = 1_000_000`, keeping the offset inside the backend's `2^31 - 1` bound.

## Task Commits

1. Task 1 (tracer): `f8f67117c` Archive tab opens by URL with a card grid and no session
2. Task 2 (tdd): `27240feb6` toggle with counts and explainers, URL-held pages, empty states

Task 2's tests were written first and run RED (16 failures in `TrainArchiveTab.test.tsx`) before the implementation. The tracer feedback gate (Task 1 verify: tests, lint, build) passed before expanding.

## Mutation checks (each reverted before commit)

| Mutation | Failing test |
|----------|--------------|
| Hook `placeholderData` replaced with `keepPreviousData` | `TrainArchiveTab.test.tsx` > placeholder data across navigation > "a list switch with the new request pending shows the skeleton, not the other list cards" (only failure; the page-change test still passes) |
| Over-range `setSearchParams(..., { replace: true })` made a push | `TrainArchiveTab.test.tsx` > pagination > "an over-range page replaces the URL with the last page, adding no history entry" (only failure) |

Both restorations confirmed: `useTrainArchive.ts` shows no diff against the commit, and `replace: true` is back in `TrainArchiveTab.tsx`.

## Verification

- `npm run lint`, `npm run build`: clean. `npm test -- --run`: 351 files, 5935 tests pass. `npm run knip`: clean (two pre-existing configuration hints only).
- Page-level (`Train.subnav.test.tsx`): the deep link asserts `getArchive` called with `{ list: 'mastered', limit: 20, offset: 0 }`, 0 session POSTs, 0 Workers, Analyze href `/analysis?game_id=100&ply=19`; the geometry test covers `train-page` on all three tabs and no `max-w-` on the Archive panel; `train-tabs` stays while `getArchive` rejects; Archive to Today to Start to `navigate(-1)` leaves `chessboard` absent with compose at 1; a remount at `/train/archive/parked?page=2` repeats `list=parked, offset=20` with compose at 0.
- Not done here, per the plan: real-browser checks for tab geometry, the grid and Back live in plan 246-06.

## Deviations from Plan

None - plan executed as written. Notes:

- The Analyze testid is `btn-train-puzzle-analyze` (from plan 246-04), used in the page test instead of a per-card id.
- `IntersectionObserver` is stubbed in the page test's `beforeEach` rather than at module level, because the file's `afterEach` calls `vi.unstubAllGlobals()` and would drop a module-level stub.
- The per-plan commit ledger was written with a plain shell redirect to the worktree git dir; `commits: 2` is measured from it.

## Known Stubs

None.

## Draft copy for owner review

The Parked empty state ("Nothing parked" / "Puzzles you keep missing get set aside here so they stop resurfacing.") is DRAFT per the plan's design notes; a comment at the `EMPTY_COPY` constant says so.

## Threat Flags

None. `page` and the list path are the only user-controlled inputs: `parseArchivePage` falls back to 1 and caps the value (T-246-15), the list is matched against exact path strings, and over-range replaces to the last page.

## Self-Check: PASSED

- FOUND: frontend/src/components/train/TrainArchiveTab.tsx, frontend/src/hooks/useTrainArchive.ts, frontend/src/components/train/__tests__/TrainArchiveTab.test.tsx
- FOUND commits: f8f67117c, 27240feb6
