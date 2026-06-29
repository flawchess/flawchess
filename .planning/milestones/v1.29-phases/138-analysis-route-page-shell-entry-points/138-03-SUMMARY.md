---
phase: 138-analysis-route-page-shell-entry-points
plan: "03"
subsystem: frontend
tags: [openings, analysis, routing, entry-point, tdd]
status: complete

dependency_graph:
  requires: []
  provides:
    - "buildAnalysisUrl(fen) pure encoder in frontend/src/lib/analysisUrl.ts"
    - "Analyze position button on Openings desktop board surface"
    - "Analyze position button on Openings mobile board surface"
  affects:
    - "frontend/src/pages/Openings.tsx"

tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN for pure utility extraction (mirrors openingsBoardLayout.ts pattern)"
    - "encodeURIComponent for FEN URL encoding (spaces → %20, slashes → %2F)"
    - "useCallback dependency on chess.position for navigate handler"

key_files:
  created:
    - frontend/src/lib/analysisUrl.ts
    - frontend/src/lib/analysisUrl.test.ts
  modified:
    - frontend/src/pages/Openings.tsx

decisions:
  - "Button placed in Openings.tsx not ExplorerTab.tsx — ExplorerTab is a pure presentational child with no navigate/chess in scope"
  - "Explorer-tab-only guard: activeTab === 'explorer' wraps both desktop and mobile buttons"
  - "Mobile button keeps visible label (not icon-only) as screen width is sufficient for the full-width board column"

metrics:
  duration: "3min"
  completed: "2026-06-26"
  tasks_completed: 2
  files_changed: 3
---

# Phase 138 Plan 03: Openings Analyze Entry Summary

**One-liner:** ROUTE-02 opening-position entry — buildAnalysisUrl pure encoder + "Analyze position" button on both Openings Explorer board surfaces.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing test for buildAnalysisUrl | 81e9f5de | frontend/src/lib/analysisUrl.test.ts |
| 1 (GREEN) | Implement buildAnalysisUrl encoder | 3ae8fffe | frontend/src/lib/analysisUrl.ts |
| 2 | Add Analyze position button to both board surfaces | 43a790e2 | frontend/src/pages/Openings.tsx |

## Deviations from Plan

None — plan executed exactly as written.

## Key Implementation Details

`buildAnalysisUrl` is a one-purpose pure function that applies `encodeURIComponent` to the FEN and returns `/analysis?fen=<encoded>`. Named constants `ANALYSIS_PATH` and `FEN_PARAM` avoid magic literals. The unit test locks the encoding: `%20` for spaces, `%2F` for slashes, and round-trip equality with `encodeURIComponent(fen)`.

In `Openings.tsx`, the `handleAnalyzePosition` callback calls `navigate(buildAnalysisUrl(chess.position))` with `[navigate, chess.position]` in deps. Both desktop (testid `btn-analyze-position`) and mobile (testid `btn-analyze-position-mobile`) board surfaces use `variant="brand-outline"`, the `Microscope` lucide icon, and "Analyze position" as the visible label. Both buttons are conditional on `activeTab === 'explorer'` (the only position-bearing tab surface for ROUTE-02).

## Verification Results

- `npm test -- --run src/lib/analysisUrl.test.ts src/pages/__tests__/Openings.statsBoard.test.tsx`: 20/20 tests pass
- `npx tsc -b`: clean (zero errors)
- `npm run lint`: 3 warnings in coverage/ files (pre-existing, unrelated to this plan)
- `npm run knip`: one unresolved import `../Analysis` in `Analysis.test.tsx` (expected — Plan 02 creates `Analysis.tsx`; full-suite green verified at post-wave merge gate)

## Known Stubs

None — all wiring is live (navigate, chess.position, buildAnalysisUrl).

## Threat Flags

None — no new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- [x] `frontend/src/lib/analysisUrl.ts` exists and exports `buildAnalysisUrl`
- [x] `frontend/src/lib/analysisUrl.test.ts` exists with 4 passing tests
- [x] `frontend/src/pages/Openings.tsx` has both `btn-analyze-position` and `btn-analyze-position-mobile`
- [x] Commits 81e9f5de, 3ae8fffe, 43a790e2 exist in git log
