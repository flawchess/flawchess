---
phase: 41-code-quality-dead-code
plan: 03
subsystem: ui
tags: [knip, dead-code, typescript, react, frontend, shadcn]

# Dependency graph
requires:
  - phase: 41-code-quality-dead-code
    plan: 01
    provides: Knip installed and configured for frontend dead export detection
provides:
  - Knip reports zero dead exports on the frontend codebase
  - 7 dead files deleted (Dashboard.tsx, ImportModal.tsx, ImportProgress.tsx, GameTable.tsx, WDLBar.tsx, table.tsx, tooltip.tsx)
  - Dead hooks and type exports removed
  - Knip.json tuned with ignoreDependencies and ignoreBinaries for false positives
  - Missing direct deps @dnd-kit/core and @dnd-kit/utilities added to package.json
affects: [41-04, ci]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dead exports removed from shadcn/ui components: only export what is actually imported"
    - "CSS-imported packages added to ignoreDependencies in knip.json"
    - "Unlisted transitive deps added as explicit dependencies in package.json"

key-files:
  created: []
  modified:
    - frontend/knip.json
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/hooks/useAnalysis.ts
    - frontend/src/hooks/useUserProfile.ts
    - frontend/src/types/api.ts
    - frontend/src/components/ui/alert.tsx
    - frontend/src/components/ui/badge.tsx
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/tabs.tsx

key-decisions:
  - "Delete entire unused files rather than leaving dead code — Dashboard.tsx, ImportModal.tsx, ImportProgress.tsx, GameTable.tsx, WDLBar.tsx, table.tsx, tooltip.tsx all removed"
  - "ignoreDependencies in knip.json for CSS-imported packages (tw-animate-css, tailwindcss-safe-area, shadcn, clsx, tailwind-merge, tailwindcss) — knip doesn't scan CSS imports"
  - "Add @dnd-kit/core and @dnd-kit/utilities as explicit deps — they were unlisted transitive deps being imported directly"
  - "Remove entry point src/main.tsx from knip.json — it's auto-detected, having it explicit generates configuration hint"

patterns-established:
  - "Knip: CSS-imported packages go to ignoreDependencies, not to be flagged as unused"
  - "Knip: CLI scripts used in package.json scripts go to ignoreBinaries"

requirements-completed: [QUAL-03]

# Metrics
duration: 30min
completed: 2026-04-02
---

# Phase 41 Plan 03: Frontend Dead Code Removal Summary

**Knip reports zero dead exports after deleting 7 unused files (including Dashboard.tsx and all its dependencies) and removing unused shadcn/ui re-exports from 8 UI component files**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-02T19:46:00Z
- **Completed:** 2026-04-02T20:16:18Z
- **Tasks:** 1
- **Files modified:** 16

## Accomplishments

- Deleted 7 completely unused files: `Dashboard.tsx` (superseded by dedicated pages), `ImportModal.tsx`, `ImportProgress.tsx`, `GameTable.tsx`, `WDLBar.tsx` (all only referenced in dead Dashboard), plus `table.tsx` and `tooltip.tsx` (shadcn/ui components never imported)
- Removed dead hooks `useAnalysis`, `useGamesQuery` (only used in deleted Dashboard), and `useUpdateUserProfile` (unused anywhere)
- Removed unused exported types: `NextMovesRequest`, `AnalysisRequest`, `ApiMatchSide` (internal only), `BoardArrow` (internal only), `ChessGameState` (internal only)
- Pruned unused shadcn/ui re-exports from 8 UI component files (alertVariants, buttonVariants, badgeVariants, CardFooter, CardAction, ChartTooltipContent, ChartStyle, DrawerPortal/Overlay/Trigger/Footer/Description, DialogClose/Overlay/Portal/Trigger, SelectGroup/Label/ScrollButtons/Separator, tabsListVariants, Toggle)
- Tuned `knip.json` with `ignoreDependencies` for CSS-only packages and `ignoreBinaries` for cloudflared script
- Added `@dnd-kit/core` and `@dnd-kit/utilities` as explicit package.json dependencies (were unlisted transitive deps being directly imported)
- Removed `@fontsource-variable/geist` from package.json (font never imported anywhere in CSS or TS)

## Task Commits

1. **Task 1: Run Knip, review report, and remove confirmed dead exports** - `459fd74` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `frontend/knip.json` - Added ignoreDependencies for CSS-imported packages and ignoreBinaries for cloudflared; removed redundant src/main.tsx entry
- `frontend/package.json` - Added @dnd-kit/core + @dnd-kit/utilities, removed @fontsource-variable/geist
- `frontend/package-lock.json` - Updated after package.json changes
- `frontend/src/pages/Dashboard.tsx` - DELETED (superseded by dedicated Import/Openings/Endgames/GlobalStats pages)
- `frontend/src/components/import/ImportModal.tsx` - DELETED (moved to Import page)
- `frontend/src/components/import/ImportProgress.tsx` - DELETED (moved to Import page)
- `frontend/src/components/results/GameTable.tsx` - DELETED (unused)
- `frontend/src/components/results/WDLBar.tsx` - DELETED (unused)
- `frontend/src/components/ui/table.tsx` - DELETED (shadcn UI component never imported)
- `frontend/src/components/ui/tooltip.tsx` - DELETED (shadcn UI component never imported)
- `frontend/src/hooks/useAnalysis.ts` - Removed dead useAnalysis and useGamesQuery hooks
- `frontend/src/hooks/useUserProfile.ts` - Removed unused useUpdateUserProfile hook
- `frontend/src/types/api.ts` - Removed unused NextMovesRequest interface and AnalysisRequest interface
- `frontend/src/components/ui/alert.tsx` - Removed alertVariants from export
- `frontend/src/components/ui/badge.tsx` - Removed badgeVariants from export
- `frontend/src/components/ui/button.tsx` - Removed buttonVariants from export
- `frontend/src/components/ui/tabs.tsx` - Removed tabsListVariants from export

## Decisions Made

- Deleted entire unused files rather than leaving dead code behind
- CSS-imported packages (tw-animate-css, tailwindcss-safe-area, shadcn, clsx, tailwind-merge, tailwindcss) added to `ignoreDependencies` in knip.json because knip doesn't scan `.css` files for imports
- Added `@dnd-kit/core` and `@dnd-kit/utilities` as explicit direct dependencies — they were being imported directly in source files but only listed as transitive deps of `@dnd-kit/sortable`
- Removed `src/main.tsx` from knip.json `entry` list — it is auto-detected by knip's Vite plugin, having it explicit produces a configuration hint

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- TypeScript `noUnusedLocals` flag caused build failures when functions were removed from exports but their bodies and imports remained — required full function deletion, not just export removal. The project's ESLint/linter also auto-removed functions and cleaned up imports during the build process, which simplified some of the cleanup.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Knip baseline is now clean (zero dead exports) — CI gate will catch any future regressions
- Plan 04 (TypeScript strictness improvements) can proceed
- Any new component that exports unused symbols will be caught by CI knip step

## Self-Check: PASSED

- FOUND: `frontend/knip.json` — updated with ignoreDependencies and ignoreBinaries
- FOUND: `frontend/package.json` — @dnd-kit/core, @dnd-kit/utilities added; @fontsource-variable/geist removed
- FOUND: commit 459fd74 (feat(41-03): remove dead frontend exports, files, and dependencies)
- VERIFIED: knip exits 0 after changes
- VERIFIED: npm run build passes
- VERIFIED: npm test passes (31 tests)

---
*Phase: 41-code-quality-dead-code*
*Completed: 2026-04-02*
