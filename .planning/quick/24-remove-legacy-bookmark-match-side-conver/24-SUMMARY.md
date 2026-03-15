---
phase: quick-24
plan: 01
subsystem: frontend
tags: [cleanup, types, dead-code]
dependency_graph:
  requires: []
  provides: [clean-match-side-types]
  affects: [frontend/src/types/api.ts, frontend/src/types/position_bookmarks.ts, frontend/src/pages/Dashboard.tsx, frontend/src/pages/Openings.tsx]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - frontend/src/types/api.ts
    - frontend/src/types/position_bookmarks.ts
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/pages/Openings.tsx
decisions:
  - "MatchSide import removed from Openings.tsx — it was only used for the now-removed 'as MatchSide' cast alongside legacyToMatchSide"
metrics:
  duration: 2min
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_modified: 4
---

# Phase quick-24 Plan 01: Remove Legacy Bookmark Match Side Conversion Summary

**One-liner:** Removed legacyToMatchSide dead code and narrowed PositionBookmarkResponse.match_side to MatchSide type since no legacy white/black/full values exist in the DB.

## Objective

Remove the `legacyToMatchSide` function and all its usages. Bookmark `match_side` values are already in `mine/opponent/both` format — no legacy conversion needed. Clean up `PositionBookmarkResponse.match_side` type to remove legacy union members.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove legacyToMatchSide and clean up types | 415546c | api.ts, position_bookmarks.ts |
| 2 | Remove legacyToMatchSide usages from pages | 41b1cd7 | Dashboard.tsx, Openings.tsx |

## Decisions Made

- **MatchSide import removed from Openings.tsx** — the import was only used for the `as MatchSide` type cast paired with `legacyToMatchSide`. After removing the function call, `b.match_side` is already typed as `MatchSide` by the narrowed `PositionBookmarkResponse`, so no cast or import needed.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `grep -r "legacyToMatchSide" frontend/src/` returns no results
- `npm run build` in frontend/ succeeds (built in 3.25s)
- `grep -r "resolveMatchSide" frontend/src/` still shows usages in Dashboard.tsx and Openings.tsx

## Self-Check: PASSED

- [x] 415546c commit exists
- [x] 41b1cd7 commit exists
- [x] frontend/src/types/api.ts modified (legacyToMatchSide removed)
- [x] frontend/src/types/position_bookmarks.ts modified (match_side narrowed to MatchSide)
- [x] frontend/src/pages/Dashboard.tsx modified (direct bkm.match_side usage)
- [x] frontend/src/pages/Openings.tsx modified (simplified resolveMatchSide calls)
