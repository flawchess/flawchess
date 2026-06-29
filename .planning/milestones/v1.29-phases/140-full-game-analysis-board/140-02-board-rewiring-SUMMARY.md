---
phase: 140-full-game-analysis-board
plan: 02
subsystem: ui
tags: [react, typescript, chess, analysis-board, variation-tree, eval-chart, game-mode]

# Dependency graph
requires:
  - 140-01 (pvLine + insertPvLine/clearPvLine/isOnPvLine, TAC_MISSED_BORDER, EvalChart sliderTestId/sliderDisabled)
provides:
  - VariationTree two-level PV nesting (variation-pv-section, variation-subpv-section)
  - VariationTree inline flaw chips (flaw-inline-tag-missed/allowed-{nodeId}) with loading spinner + error state
  - VariationTree blunder/mistake severity markers (BlunderIcon, MistakeIcon); inaccuracy = no marker (D-03)
  - Analysis.tsx game mode: isGameMode fetch + board seeding + EvalChart below board + contextual overlay
  - Analysis.tsx BoardControls relocated to right column below VariationTree
  - Unified TacticModeOverlay resolver for URL-tactic and contextual-chip paths
affects:
  - 140-03-entry-points (VariationTree game-mode props ready; Analysis.tsx game mode live)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Two-effect board seeding (loadMainLine effect + separate initialPly navigation effect via mainLine.length watch)
    - Seeding guard refs (hasLoadedMainLine, hasNavigatedToInitialPly) prevent re-running after first game load
    - Chip toggle handler (clearPvLine on same chip; clearPvLine + setActivePvFlaw on new chip)
    - insertPvLine effect keyed on contextualTacticData + activePvFlaw ply/orientation (mainLine omitted from deps)
    - flawMarkerByNodeId useMemo keyed by gameData (not gameData?.flaw_markers) to avoid ESLint preserve-manual-memoization error
    - Dual useTacticLines hook calls at top level (L-3: both unconditional, gated by enabled flag)
    - Unified overlay resolver: isTacticMode has priority; contextual overlay shown only in game mode

key-files:
  modified:
    - frontend/src/components/analysis/VariationTree.tsx (two-level nesting, chips, markers, new props)
    - frontend/src/components/analysis/__tests__/VariationTree.test.tsx (8 new Phase 140 test cases)
    - frontend/src/pages/Analysis.tsx (game mode rewiring, layout relocation)
    - frontend/src/pages/__tests__/Analysis.test.tsx (useLibraryGame mock added)

key-decisions:
  - "activePvNodeId is keyed by mainLine[activePvFlaw.ply] (the node AFTER the flaw move) to match chip render position in VariationTree"
  - "forkNodeId for insertPvLine is mainLine[activePvFlaw.ply - 1] (position BEFORE flaw move, where PV branches)"
  - "EvalChart receives gameData dep (not gameData?.flaw_markers) in flawMarkerByNodeId useMemo to satisfy react-hooks/preserve-manual-memoization"
  - "handleReset game mode: clearPvLine + setActivePvFlaw(null) + goToNode(mainLine[initialPly]) (not goToRoot which only works for tactic seed)"
  - "BoardControls relocated to right column below VariationTree matching chess.com layout pattern"

# Metrics
duration: 45min
completed: 2026-06-27
status: complete
---

# Phase 140 Plan 02: Board Rewiring Summary

**VariationTree extended with two-level PV nesting, inline missed/allowed flaw chip pills, and blunder/mistake severity markers; Analysis.tsx rewired for game mode with game-by-id fetch, board seeding, EvalChart below board, contextual TacticModeOverlay, and BoardControls relocated to right column**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-06-27T11:03:56Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

### Task 1: VariationTree Two-Level Nesting + Inline Chips + Markers

- Extended `VariationTreeProps` with 6 new optional props (backward-compatible): `pvLine`, `flawMarkerByNodeId`, `onPvChipClick`, `activePvNodeId`, `pvFetchPending`, `pvFetchError`
- Exported `FlawMarkerEntry` interface with `missedMotif`, `allowedMotif`, `severity`, `ply` fields
- `buildVariationChain` returns `level: 0 | 1 | 2` and `subChain: NodeId[]` — level 2 detected when walk from `currentNodeId` crosses a pvLine node before reaching mainLine
- `DesktopTree`: `variation-pv-section` (ml-8, border-l-2) for level-1; nested `variation-subpv-section` for level-2
- `renderFlawChip`: missed/allowed pills with TAC theme colors, ACTIVE_FILTER_RING_CLASS ring on active chip, spinner when `isActive && pvFetchPending`, sibling error span on `pvFetchError`
- BlunderIcon/MistakeIcon rendered for non-tactic blunder/mistake severity (D-02); inaccuracy renders no marker (D-03, D-04)
- MobileTree: double-paren `((...))`  for level-2, blunder/mistake markers on mobile rows, no inline chips
- 8 new tests covering: level-1 pv-section, level-2 subpv-section, missed/allowed chip render, chip click callback, active chip aria-label, error state, blunder SVG presence, inaccuracy empty SVG

### Task 2: Analysis.tsx Game Mode Rewiring

- `isGameMode = gameId != null && initialPly != null && !isTacticMode` (mutually exclusive with URL-tactic per L-2)
- `useLibraryGame(isGameMode ? gameId : null)` — unconditional top-level call, enabled only in game mode
- Dual `useTacticLines` calls: existing tactic path (`isTacticMode` flag) + contextual path (`activePvFlaw != null && isGameMode`)
- Two-effect board seeding: Effect 1 calls `loadMainLine(gameData.moves, STARTING_FEN)` once (guarded via `hasLoadedMainLine` ref); Effect 2 navigates to `initialPly` after `mainLine.length` changes (guarded via `hasNavigatedToInitialPly` ref)
- `flawMarkerByNodeId` Map built from `gameData.flaw_markers` keyed by `mainLine[fm.ply]` with noUncheckedIndexedAccess guards (T-140-02b)
- `handlePvChipClick`: toggles off same chip (clearPvLine + setActivePvFlaw(null)) or sets new chip + navigates to fork node
- `insertPvLine` effect: grafts PV sideline at `mainLine[activePvFlaw.ply - 1]` when contextual data arrives
- EvalChart rendered below board+EvalBar in left column (game mode only, guarded by all non-null props)
- `sliderDisabled = !isOnMainLineForSlider` — slider parks with tooltip when on pvLine or sub-fork (D-05)
- BoardControls relocated from left column to bottom of right column below VariationTree (UI-SPEC Layout Contract)
- Unified TacticModeOverlay resolver: URL-tactic has priority; contextual overlay activates in game mode when `activePvFlaw != null && contextualTacticData != null`
- `handleReset` game mode branch: `clearPvLine() + setActivePvFlaw(null) + goToNode(mainLine[initialPly ?? 0])`
- Error state: `isGameMode && gameError` shows "Failed to load game. Something went wrong. Please try again in a moment." (CLAUDE.md isError rule)
- Analysis.test.tsx mock updated to include `useLibraryGame` and full `useTacticLines` return shape

## Task Commits

1. **Task 1: VariationTree two-level nesting + inline flaw chips + blunder/mistake markers** - `34b66278` (feat)
2. **Task 2: Analysis.tsx game mode rewiring** - `9900c183` (feat)

## Files Modified

- `frontend/src/components/analysis/VariationTree.tsx` — two-level nesting, inline chips, severity markers, new props
- `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` — 8 new Phase 140 test cases
- `frontend/src/pages/Analysis.tsx` — game mode fetch + seeding + layout relocation + contextual overlay
- `frontend/src/pages/__tests__/Analysis.test.tsx` — `useLibraryGame` mock added

## Decisions Made

- `activePvNodeId` is `mainLine[activePvFlaw.ply]` (node AFTER flaw move) — this is where the chip renders in VariationTree, not the fork position
- `forkNodeId` for `insertPvLine` is `mainLine[activePvFlaw.ply - 1]` (position BEFORE flaw move, where the PV branches from)
- `flawMarkerByNodeId` useMemo uses `gameData` (not `gameData?.flaw_markers`) in deps to satisfy `react-hooks/preserve-manual-memoization`
- `onOrientationChange` is a no-op for the contextual TacticModeOverlay (orientation fixed by chip click; switching requires a new chip click)
- `mainLine` is intentionally omitted from the `insertPvLine` effect's dep array (stable after game load; including it causes spurious re-runs during user variation navigation)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ESLint `react-hooks/preserve-manual-memoization` error on `flawMarkerByNodeId` useMemo**
- **Found during:** Task 2 (first lint run)
- **Issue:** `}, [isGameMode, gameData?.flaw_markers, mainLine])` — ESLint requires the root object (`gameData`) in deps, not the optional-chain property path
- **Fix:** Changed dep from `gameData?.flaw_markers` to `gameData`
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Verification:** `npm run lint` — 0 errors (3 pre-existing coverage warnings)

**2. [Rule 3 - Blocking] Analysis.test.tsx missing `useLibraryGame` in mock**
- **Found during:** Task 2 (full test suite run)
- **Issue:** `vi.mock('@/hooks/useLibrary', ...)` only exported `useTacticLines`; adding `useLibraryGame` import to Analysis.tsx caused test failure with "No useLibraryGame export is defined on the mock"
- **Fix:** Added `useLibraryGame: () => ({ data: undefined, isError: false })` and updated `useTacticLines` mock to return full shape `{ data: undefined, isFetching: false, isError: false }`
- **Files modified:** `frontend/src/pages/__tests__/Analysis.test.tsx`
- **Verification:** `npm test -- --run` — 103 files, 1210 tests all pass

## Known Stubs

None — game mode is fully wired. `useLibraryGame` fetches real game data; `useTacticLines` fetches real contextual PV; `flawMarkerByNodeId` reads live `gameData.flaw_markers`.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes. `useLibraryGame` calls an existing authenticated endpoint. URL param parsing (`?ply=`) uses NaN-guard (T-140-02a). All `mainLine[i]` accesses use noUncheckedIndexedAccess guards (T-140-02b).

## Self-Check: PASSED

- [x] `frontend/src/components/analysis/VariationTree.tsx` exports `FlawMarkerEntry` and renders `variation-pv-section`
- [x] `frontend/src/pages/Analysis.tsx` contains `isGameMode` and `useLibraryGame`
- [x] Commits exist: 34b66278, 9900c183
- [x] `npx tsc -b` — zero errors
- [x] `npm run lint` — 0 errors (3 pre-existing coverage warnings)
- [x] `npm test -- --run` — 103 files, 1210 tests all pass
