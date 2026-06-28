---
phase: 140-full-game-analysis-board
plan: 01
subsystem: ui
tags: [react, typescript, chess, analysis-board, theme, hooks]

# Dependency graph
requires: []
provides:
  - TAC_MISSED_BORDER constant in theme.ts (oklch(0.70 0.15 258 / 0.30))
  - buildGameAnalysisUrl(gameId, ply) URL builder in analysisUrl.ts
  - EvalChart sliderTestId + sliderDisabled optional props (backward-compatible)
  - useAnalysisBoard pvLine state + insertPvLine/clearPvLine/isOnPvLine methods
affects:
  - 140-02-board-rewiring (imports insertPvLine, clearPvLine, isOnPvLine, pvLine)
  - 140-03-entry-points (imports buildGameAnalysisUrl for unified Analyze button)
  - VariationTree.tsx (imports TAC_MISSED_BORDER for inline chip border)
  - Analysis.tsx (calls insertPvLine, clearPvLine, reads pvLine; passes sliderTestId/sliderDisabled to EvalChart)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Single-setState batch PV insert (avoids stale stateRef in loop)
    - Traverse prev.nodes before deletion in clearPvLine (avoid dangling lookups)
    - Optional prop with backward-compatible default (sliderTestId, sliderDisabled)

key-files:
  created:
    - frontend/src/lib/analysisUrl.ts (buildGameAnalysisUrl added)
  modified:
    - frontend/src/lib/theme.ts (TAC_MISSED_BORDER constant)
    - frontend/src/lib/analysisUrl.test.ts (buildGameAnalysisUrl tests)
    - frontend/src/components/library/EvalChart.tsx (sliderTestId + sliderDisabled props)
    - frontend/src/hooks/useAnalysisBoard.ts (pvLine state + PV-nesting methods)
    - frontend/src/hooks/__tests__/useAnalysisBoard.test.ts (3 invariant tests)

key-decisions:
  - "insertPvLine implemented as single setState call (not makeMove loop) to avoid stale stateRef"
  - "clearPvLine traverses prev.nodes before deleting pvLine ids to recover mainLine ancestor"
  - "sliderDisabled uses class string template (not cn()) to stay backward-compatible"

patterns-established:
  - "PV insert pattern: single setState updater, graft onto Map copy, chain from forkNodeId"
  - "pvLine recovery pattern: walk parentId through pre-deletion prev.nodes to find mainLine ancestor"

requirements-completed: [SC-2, SC-3, SC-4, D-4]

# Metrics
duration: 30min
completed: 2026-06-27
status: complete
---

# Phase 140 Plan 01: Foundation Primitives Summary

**Four additive primitives: TAC_MISSED_BORDER theme constant, buildGameAnalysisUrl URL builder (unit-tested), EvalChart sliderTestId/sliderDisabled props, and useAnalysisBoard two-level PV nesting API (insertPvLine/clearPvLine/isOnPvLine) with invariant tests**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-06-27T10:36:00Z
- **Completed:** 2026-06-27T10:41:31Z
- **Tasks:** 3 (Task 3 TDD: RED + GREEN)
- **Files modified:** 6

## Accomplishments

- `TAC_MISSED_BORDER` exported from theme.ts with value `'oklch(0.70 0.15 258 / 0.30)'` — symmetric with `TAC_ALLOWED_BORDER`, used by VariationTree inline chip border (140-02)
- `buildGameAnalysisUrl(gameId, ply)` added to analysisUrl.ts with unit tests asserting exact format `/analysis?game_id={id}&ply={ply}` — no encoding needed for numeric params
- EvalChart accepts `sliderTestId?: string` and `sliderDisabled?: boolean`; existing LibraryGameCard callers pass neither and see zero behavior or testid change
- `insertPvLine`/`clearPvLine`/`isOnPvLine` + `pvLine: NodeId[]` on useAnalysisBoard, with 3 invariant tests covering the chain-back, node-removal, and level-2-fork behaviors

## Task Commits

1. **Task 1: TAC_MISSED_BORDER + buildGameAnalysisUrl** - `397f4cb2` (feat)
2. **Task 3 RED: failing PV-nesting tests** - `61ab7921` (test)
3. **Task 2: EvalChart sliderTestId + sliderDisabled** - `681fc106` (feat)
4. **Task 3 GREEN: pvLine + insertPvLine/clearPvLine/isOnPvLine** - `05d0fe07` (feat)

## Files Created/Modified

- `frontend/src/lib/theme.ts` — added `TAC_MISSED_BORDER = 'oklch(0.70 0.15 258 / 0.30)'` after `TAC_MISSED_BG`
- `frontend/src/lib/analysisUrl.ts` — added `GAME_ID_PARAM`, `PLY_PARAM`, `buildGameAnalysisUrl`
- `frontend/src/lib/analysisUrl.test.ts` — added 2 tests for `buildGameAnalysisUrl`
- `frontend/src/components/library/EvalChart.tsx` — added `sliderTestId`/`sliderDisabled` props and wired to slider input
- `frontend/src/hooks/useAnalysisBoard.ts` — added `pvLine` to state + return, `insertPvLine`, `clearPvLine`, `isOnPvLine`
- `frontend/src/hooks/__tests__/useAnalysisBoard.test.ts` — added 3 invariant tests (behaviors 5, 6, 7)

## Decisions Made

- `insertPvLine` uses a single `setState` call (not a `makeMove` loop): `stateRef.current` only syncs after render, so sequential calls would graft all PV nodes onto the same stale parent (L-1/L-7 from RESEARCH.md).
- `clearPvLine` traverses `prev.nodes` (before deletion) to walk up parentId and find the mainLine ancestor. Using the new map after deletion would cause dangling lookups since pvLine nodes are removed.
- `sliderDisabled` wiring uses template literal string concat rather than `cn()` to keep the change minimal and avoid importing `cn` into EvalChart.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed illegal test PV SAN `Bc5` with `Bc4`**
- **Found during:** Task 3 GREEN (first run)
- **Issue:** The test used `['Nf6', 'Bc5']` as the PV from the post-Nf3 position; after `Nf6` (black) it is white's turn, and `Bc5` is not a legal bishop move from f1.
- **Fix:** Changed the second PV SAN to `'Bc4'` (f1→c4, legal diagonal from f1).
- **Files modified:** `frontend/src/hooks/__tests__/useAnalysisBoard.test.ts`
- **Verification:** `npm test -- --run useAnalysisBoard` green (10/10)
- **Committed in:** `05d0fe07` (Task 3 GREEN commit)

**2. [Rule 1 - Bug] Fixed clearPvLine walking deleted nodes map**
- **Found during:** Task 3 GREEN (first run — test 6 failed with `currentNodeId` null)
- **Issue:** `clearPvLine` built `newNodes` (with pvLine ids deleted) first, then tried to traverse `newNodes.get(recoveredId)` to walk up to mainLine. Since pvLine ids were already gone, the walk returned null immediately.
- **Fix:** Reordered to compute `recoveredId` by walking `prev.nodes` (intact, before deletion), then delete from `newNodes`.
- **Files modified:** `frontend/src/hooks/useAnalysisBoard.ts`
- **Verification:** `npm test -- --run useAnalysisBoard` green (10/10)
- **Committed in:** `05d0fe07` (Task 3 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs caught on first GREEN run)
**Impact on plan:** Both fixes essential for correct behavior. No scope creep.

## Issues Encountered

None beyond the two bugs above, both caught by the TDD invariant tests and fixed before commit.

## Known Stubs

None — all primitives are fully implemented with no placeholder data.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. No new threat surface beyond the plan's threat model (T-140-01a guarded: `insertPvLine` returns `prev` unchanged on missing `forkNodeId`; replay loop breaks on null `chess.move`).

## Self-Check

- [x] `frontend/src/lib/theme.ts` contains `TAC_MISSED_BORDER`
- [x] `frontend/src/lib/analysisUrl.ts` exports `buildGameAnalysisUrl`
- [x] `frontend/src/components/library/EvalChart.tsx` contains `sliderDisabled`
- [x] `frontend/src/hooks/useAnalysisBoard.ts` contains `insertPvLine`
- [x] Commits exist: 397f4cb2, 681fc106, 61ab7921, 05d0fe07
- [x] `npm test -- --run` 103 files, 1201 tests green
- [x] `npx tsc -b` zero errors
- [x] `npm run lint` zero errors (3 pre-existing coverage-dir warnings)

## Self-Check: PASSED

## Next Phase Readiness

All four primitives required by 140-02 (board rewiring) are landed and unit-tested:
- `TAC_MISSED_BORDER` ready for VariationTree inline chip border
- `insertPvLine`/`clearPvLine`/`isOnPvLine` ready for Analysis.tsx PV expand/collapse
- `buildGameAnalysisUrl` ready for 140-03 entry-point buttons

No blockers for 140-02.

---
*Phase: 140-full-game-analysis-board*
*Completed: 2026-06-27*
