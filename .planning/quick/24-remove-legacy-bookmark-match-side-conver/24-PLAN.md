---
phase: quick-24
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/types/api.ts
  - frontend/src/types/position_bookmarks.ts
  - frontend/src/pages/Dashboard.tsx
  - frontend/src/pages/Openings.tsx
autonomous: true
requirements: [QUICK-24]

must_haves:
  truths:
    - "legacyToMatchSide function no longer exists in the codebase"
    - "All bookmark match_side values are used directly as MatchSide type without legacy conversion"
    - "resolveMatchSide still works correctly (it is NOT legacy — it converts mine/opponent/both to white/black/full for the API)"
    - "Frontend builds without errors"
  artifacts:
    - path: "frontend/src/types/api.ts"
      provides: "MatchSide types and resolveMatchSide (no legacyToMatchSide)"
      exports: ["resolveMatchSide"]
    - path: "frontend/src/types/position_bookmarks.ts"
      provides: "PositionBookmarkResponse with clean match_side type"
  key_links:
    - from: "frontend/src/pages/Dashboard.tsx"
      to: "frontend/src/types/api.ts"
      via: "import resolveMatchSide (no legacyToMatchSide import)"
      pattern: "resolveMatchSide"
    - from: "frontend/src/pages/Openings.tsx"
      to: "frontend/src/types/api.ts"
      via: "import resolveMatchSide (no legacyToMatchSide import)"
      pattern: "resolveMatchSide"
---

<objective>
Remove the `legacyToMatchSide` function and all its usages. Since there are no legacy bookmarks in the DB, bookmark `match_side` values are already in `mine/opponent/both` format. Also clean up the `PositionBookmarkResponse.match_side` type to remove legacy union members (`white | black | full`).

Note: `resolveMatchSide` is NOT legacy — it converts the frontend's `mine/opponent/both` to the API's `white/black/full` and must be kept.

Purpose: Remove dead code that handled backward-compatible bookmark values that no longer exist.
Output: Cleaner type definitions and simplified bookmark loading code.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/types/api.ts
@frontend/src/types/position_bookmarks.ts
@frontend/src/pages/Dashboard.tsx
@frontend/src/pages/Openings.tsx
@frontend/src/hooks/useChessGame.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove legacyToMatchSide and clean up types</name>
  <files>frontend/src/types/api.ts, frontend/src/types/position_bookmarks.ts</files>
  <action>
    1. In `frontend/src/types/api.ts`: Delete the `legacyToMatchSide` function (lines 40-47) and its JSDoc comment (line 40). Keep `resolveMatchSide` unchanged.

    2. In `frontend/src/types/position_bookmarks.ts`: Change the `match_side` field in `PositionBookmarkResponse` (line 8) from:
       `match_side: 'mine' | 'opponent' | 'both' | 'white' | 'black' | 'full';`
       to:
       `match_side: MatchSide;`
       Add the import: `import type { MatchSide } from './api';`
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>legacyToMatchSide function deleted, PositionBookmarkResponse.match_side uses MatchSide type only</done>
</task>

<task type="auto">
  <name>Task 2: Remove legacyToMatchSide usages from pages</name>
  <files>frontend/src/pages/Dashboard.tsx, frontend/src/pages/Openings.tsx</files>
  <action>
    1. In `frontend/src/pages/Dashboard.tsx`:
       - Remove `legacyToMatchSide` from the import on line 37 (keep `resolveMatchSide`).
       - Line 193: Change `legacyToMatchSide(bkm.match_side)` to just `bkm.match_side` since it is already a MatchSide value. The full line becomes:
         `setFilters(prev => ({ ...prev, color: bkm.color ?? 'white', matchSide: bkm.match_side }));`

    2. In `frontend/src/pages/Openings.tsx`:
       - Remove `legacyToMatchSide` from the import on line 18 (keep `resolveMatchSide`).
       - Lines 97-100 and 119-122: Replace `legacyToMatchSide(b.match_side) as MatchSide` with just `b.match_side`. The match_side is already MatchSide type. The resolveMatchSide calls become:
         `match_side: resolveMatchSide(b.match_side, (b.color ?? 'white') as Color),`
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>No imports or calls to legacyToMatchSide remain anywhere in the codebase. Frontend builds successfully.</done>
</task>

</tasks>

<verification>
- `grep -r "legacyToMatchSide" frontend/src/` returns no results
- `npm run build` in frontend/ succeeds
- `grep -r "resolveMatchSide" frontend/src/` still shows usages (this function is kept)
</verification>

<success_criteria>
- legacyToMatchSide function and all references completely removed
- PositionBookmarkResponse.match_side type narrowed to MatchSide only
- resolveMatchSide preserved and working
- Frontend compiles and builds without errors
</success_criteria>

<output>
After completion, create `.planning/quick/24-remove-legacy-bookmark-match-side-conver/24-SUMMARY.md`
</output>
