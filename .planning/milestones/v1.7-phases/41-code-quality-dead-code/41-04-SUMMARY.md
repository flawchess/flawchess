---
phase: 41-code-quality-dead-code
plan: 04
subsystem: frontend
tags: [typescript, type-safety, noUncheckedIndexedAccess, tsconfig, components, hooks, lib]

# Dependency graph
requires: [41-01]
provides:
  - TypeScript config with noUncheckedIndexedAccess enabled
  - All array/Record index accesses safely narrowed across 14 files
  - Zero TypeScript build errors with strict index access checking
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "noUncheckedIndexedAccess: non-null assertion ! for loop-bounded index access"
    - "noUncheckedIndexedAccess: flatMap pattern to narrow Record key access after filter"
    - "noUncheckedIndexedAccess: explicit variable type annotation over STEP_CANDIDATES[0] init"
    - "noUncheckedIndexedAccess: ?? fallback for Object.keys Record access"

key-files:
  modified:
    - frontend/tsconfig.app.json
    - frontend/src/lib/zobrist.ts
    - frontend/src/lib/openings.ts
    - frontend/src/lib/utils.ts
    - frontend/src/hooks/useChessGame.ts
    - frontend/src/hooks/useStats.ts
    - frontend/src/pages/Openings.tsx
    - frontend/src/components/board/ChessBoard.tsx
    - frontend/src/components/board/MoveList.tsx
    - frontend/src/components/charts/EndgameConvRecovChart.tsx
    - frontend/src/components/charts/EndgameGauge.tsx
    - frontend/src/components/charts/EndgameTimelineChart.tsx
    - frontend/src/components/position-bookmarks/SuggestionsModal.tsx
    - frontend/src/components/results/GameCard.tsx
    - frontend/src/components/stats/RatingChart.tsx
    - frontend/src/components/ui/card.tsx
    - frontend/src/components/ui/chart.tsx
    - frontend/src/components/ui/dialog.tsx
    - frontend/src/components/ui/drawer.tsx
    - frontend/src/components/ui/select.tsx
    - frontend/src/components/ui/toggle.tsx
    - frontend/src/types/api.ts

key-decisions:
  - "flatMap over filter+map for Record access narrowing in Openings.tsx — TypeScript cannot narrow computed property access through separate filter/map chain"
  - "Non-null assertion ! preferred over as T cast — narrower and more explicit about safety invariant"
  - "Remove unused local functions after Plan 03 removed their exports — prevents noUnusedLocals TS6133 errors"

requirements-completed: [QUAL-03]

# Metrics
duration: 22min
completed: 2026-04-02
---

# Phase 41 Plan 04: noUncheckedIndexedAccess Type Safety Summary

**noUncheckedIndexedAccess enabled in tsconfig.app.json, all 56 resulting type errors fixed across 14 files using safe narrowing patterns with zero @ts-ignore**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-04-02T19:53:00Z
- **Completed:** 2026-04-02T20:15:15Z
- **Tasks:** 2
- **Files modified:** 22

## Accomplishments

- Added `"noUncheckedIndexedAccess": true` to `frontend/tsconfig.app.json`
- Fixed 56 TypeScript errors across 14 source files using four safe access patterns:
  - **Pattern A (!):** Non-null assertion for loop-bounded or invariant-guaranteed access
  - **Pattern B (?? fallback):** Nullish coalescing for Record key access with fallback
  - **Pattern C (flatMap):** Combined filter+map to narrow Record key access in Openings.tsx
  - **Pattern D (local var):** Explicit variable type annotation instead of array index initialization
- Zero `// @ts-ignore` used anywhere
- `npm run build` and `npm test` (31 tests) pass cleanly after changes

## Task Commits

1. **Task 1: Enable flag and fix lib/hooks errors** — `fba1ba5`
   - tsconfig.app.json: noUncheckedIndexedAccess: true
   - zobrist.ts: 11 non-null assertions on POLYGLOT_RANDOM_ARRAY and square character access
   - openings.ts: explicit parts[] indexing + loop index assertion
   - utils.ts: non-null assertions on dates[0]! and dates[length-1]!
   - useChessGame.ts: history[i]! in replay loop
   - useStats.ts: platforms[0]! after length === 1 check

2. **Task 2: Fix component/page errors + cleanup** — `93f5602`
   - Openings.tsx: flatMap pattern replaces filter+map for wdlStatsMap Record access
   - ChessBoard.tsx: square[0]! and square[1]! (chess square strings are always 2 chars)
   - MoveList.tsx: moveHistory[i]! in pair-building loop
   - EndgameConvRecovChart.tsx: payload[0]! and optional chaining on chartConfig entries
   - EndgameGauge.tsx: zones[i]! and zones[0]! in getZoneColor and GaugeArcs
   - EndgameTimelineChart.tsx: ?? [] for Object.keys-based Record access
   - SuggestionsModal.tsx: toSave[i]! in save loop
   - GameCard.tsx: entries[0]! for IntersectionObserver callback
   - RatingChart.tsx: explicit let step: number = 10 initialization
   - ui/card.tsx, chart.tsx, dialog.tsx, drawer.tsx, select.tsx, toggle.tsx: removed unused
     local functions made dead by Plan 03's export removals (prevents TS6133 noUnusedLocals errors)
   - types/api.ts: removed unused local AnalysisRequest interface

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Unused local declarations in UI components after Plan 03 parallel execution**

- **Found during:** Task 2
- **Issue:** Plan 03 (running in parallel) removed export keywords from shadcn/ui component
  functions (CardAction, CardFooter, ChartTooltipContent, DialogTrigger, DialogClose,
  DrawerTrigger, DrawerFooter, DrawerDescription, SelectGroup, SelectLabel, SelectSeparator,
  Toggle). With noUncheckedIndexedAccess enabled and `noUnusedLocals: true`, these now-local
  functions triggered TS6133 errors. Additionally, types/api.ts AnalysisRequest interface was
  de-exported and became unused.
- **Fix:** Removed the unused function bodies and corresponding unused imports from 6 UI
  component files and removed the AnalysisRequest interface from api.ts
- **Files modified:** card.tsx, chart.tsx, dialog.tsx, drawer.tsx, select.tsx, toggle.tsx, api.ts
- **Commit:** 93f5602

## Files Created/Modified

### Primary Files (plan scope)

- `frontend/tsconfig.app.json` — Added noUncheckedIndexedAccess: true
- `frontend/src/lib/zobrist.ts` — 11 non-null assertions added
- `frontend/src/lib/openings.ts` — Safe array indexing
- `frontend/src/lib/utils.ts` — Non-null assertions after length check
- `frontend/src/hooks/useChessGame.ts` — Loop-bounded assertion
- `frontend/src/hooks/useStats.ts` — Length-checked assertion
- `frontend/src/pages/Openings.tsx` — flatMap narrowing pattern
- `frontend/src/components/board/ChessBoard.tsx` — Square char assertions
- `frontend/src/components/board/MoveList.tsx` — Loop assertion
- `frontend/src/components/charts/EndgameConvRecovChart.tsx` — payload and chartConfig narrowing
- `frontend/src/components/charts/EndgameGauge.tsx` — zones array assertions
- `frontend/src/components/charts/EndgameTimelineChart.tsx` — ?? [] fallback
- `frontend/src/components/position-bookmarks/SuggestionsModal.tsx` — Loop assertion
- `frontend/src/components/results/GameCard.tsx` — IntersectionObserver assertion
- `frontend/src/components/stats/RatingChart.tsx` — Explicit type annotation

### Secondary Files (deviation fixes)

- `frontend/src/components/ui/card.tsx` — Removed CardAction, CardFooter
- `frontend/src/components/ui/chart.tsx` — Removed ChartTooltipContent
- `frontend/src/components/ui/dialog.tsx` — Removed DialogTrigger, DialogClose
- `frontend/src/components/ui/drawer.tsx` — Removed DrawerTrigger, DrawerFooter, DrawerDescription
- `frontend/src/components/ui/select.tsx` — Removed SelectGroup, SelectLabel, SelectSeparator
- `frontend/src/components/ui/toggle.tsx` — Removed Toggle function + cleaned up imports
- `frontend/src/types/api.ts` — Removed AnalysisRequest interface

## Known Stubs

None — all data access patterns are properly narrowed.

## Self-Check: PASSED

- FOUND: frontend/tsconfig.app.json with noUncheckedIndexedAccess: true
- FOUND: commit fba1ba5 (feat(41-04): enable noUncheckedIndexedAccess and fix lib/hooks)
- FOUND: commit 93f5602 (feat(41-04): fix noUncheckedIndexedAccess errors in components)
- FOUND: 0 TypeScript errors from `npx tsc -p tsconfig.app.json --noEmit`
- FOUND: npm run build passes (exit 0)
- FOUND: npm test passes (31/31 tests)
- FOUND: no @ts-ignore in any modified file

---
*Phase: 41-code-quality-dead-code*
*Completed: 2026-04-02*
