---
phase: quick-261010-e5l
plan: 01
subsystem: frontend/train
tags: [train, reveal, stockfish, arrows]
status: complete
commits: 2
plan_head_before: 85e6c140d1fd246ac1ad8f86b8a009449cb31dd0
plan_head_after: 0cd92a603ff027b57570a351eb02379d3f698db8
key-files:
  modified:
    - frontend/src/lib/trainArrows.ts
    - frontend/src/lib/theme.ts
    - frontend/src/hooks/useTrainRevealTree.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/lib/__tests__/trainArrows.test.ts
    - frontend/src/hooks/__tests__/useTrainRevealTree.test.ts
    - CHANGELOG.md
actuals:
  tasks: 2
  commits: 2
---

# Quick 261010-e5l: Train reveal live engine good-move alternatives

At a soft puzzle's root the Train reveal board now draws up to 3 alternatives in total: the server-certified green one first, then the reveal engine's own good lines (pvLines[1..], filtered through `classifyLiveSeverity` on mover-POV expected scores, depth >= 10 on both the top and the candidate line) as faint `STOCKFISH_SECONDARY_LINE` arrows with no badge and no "Also fine" entry.

## Commits

- `3ce3514be` feat: builder, chip-focus extension, theme constant, root MultiPV floor, screen wiring, re-expressed VETFINE-03 e2e test
- `0cd92a603` test: unit matrix (builder, chip focus, `trainRootMultiPvFloor`, reveal-tree root width) + CHANGELOG bullet

## What changed

- `trainArrows.ts`: `TRAIN_SOFT_TOTAL_ALT_MOVE_ARROWS` (3), `TRAIN_LIVE_ALT_MIN_DEPTH` (10), `TRAIN_LIVE_ALT_ROOT_MULTIPV` (4), `trainRootMultiPvFloor`, `TrainLiveAlternativeContext`, `buildTrainLiveAlternativeArrows`; `buildChipFocusOverlay` takes an optional `liveArrows` parameter (live arrows first, dim level `TRAIN_FOCUS_LIVE_ALT_DIM_OPACITY`, lit when sharing the focused chip's squares).
- `theme.ts`: `TRAIN_FOCUS_LIVE_ALT_DIM_OPACITY = 0.4`.
- `useTrainRevealTree.ts`: `rootMinMultiPv` option, applied only while `currentNodeId === null`; engine comment rewritten.
- `TrainSolveScreen.tsx`: `revealPuzzleType`, `rootMinMultiPv: trainRootMultiPvFloor(...)`, `liveAlternatives` input to `resolveRevealBoardOverlay`.
- VETFINE-03 (pre-211 cache shape) test re-expressed: zero green arrows and no "Also fine", but three live translucent arrows (`d2d4,g1f3,c2c4,e2e4`) with live-dim / lit opacities. No other existing test needed an expectation update.

## Deviations from Plan

### Orchestrator override

**Task 2 skipped entirely** (owner-side scope decision): `useStockfishEngine.ts` and its tests are untouched; it is shared with the Analysis board and the coincident fen + multiPv double start is harmless (same FEN, same width, stale bestmove discarded). Consequences:
- Plan must-have truth 6 ("a fen change and a multiPv change in the same render start exactly one search") is dropped. A settled root<->line step still starts two `go`s and a `stop` for one position (the finding documented in the plan context).
- The `useTrainRevealTree` engine comment does not carry the extra sentence about `useStockfishEngine` folding the width change into the FEN-driven search (that sentence belonged to Task 2).
- Plan threat T-261010e5l-03 mitigation text ("Task 2 removes the redundant go/stop/go") no longer applies; the extra search on root<->line steps is accepted.
- The `searchedFenRef` key link and artifact in the plan frontmatter are not delivered.

No auto-fix deviations (Rules 1-3).

## Verification

- Mutation check: removing the `classifyLiveSeverity` check in `buildTrainLiveAlternativeArrows` made 2 tests fail (inaccuracy/mistake/blunder exclusion, mover-POV black case); restored, all green.
- Frontend gate (from `frontend/`): `npm run lint` clean, `npm run build` clean, `npm test -- --run` 5479 passed, `npm run knip` clean (one pre-existing configuration hint about `.css` in knip.json, not a finding).

## Known Stubs

None.

## Threat Flags

None. Live arrows are built only from `revealTree.pvLines` in the root branch, which exists only after the verdict.

## Self-Check: PASSED

Commits 3ce3514be and 0cd92a603 are on `main`; all modified files exist.
