---
phase: 246-train-subnav-split
plan: 04
subsystem: ui
tags: [react, typescript, train, archive, lazyminiboard, vitest]
status: complete

requires:
  - phase: 246-train-subnav-split
    provides: "246-01 wire shape for GET /train/archive (mirrored field for field, no code dependency)"
provides:
  - "TrainPuzzleCard: spoiler-free archive card (pre-mistake board, no arrows, opponent, date, time control, status line, Analyze)"
  - "buildTrainPuzzleAnalysisUrl: shared ply-minus-one Analyze helper"
  - "ArchiveList and TrainArchiveItem frontend types"
affects: [246-05 archive tab grid]

actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: 0c84cf49c8fb0fd6cfa04cc7fdb30c6f3882fa43
plan_head_after: 17f858c85814e99e193badf8fd8a78e97e904846

tech-stack:
  added: []
  patterns:
    - "Single horizontal card tree at every width via useMiniBoardSize (no separate mobile/desktop trees)"

key-files:
  created:
    - frontend/src/components/train/TrainPuzzleCard.tsx
    - frontend/src/components/train/__tests__/TrainPuzzleCard.test.tsx
  modified:
    - frontend/src/types/train.ts
    - frontend/src/lib/analysisUrl.ts
    - frontend/src/lib/analysisUrl.test.ts
    - frontend/src/components/train/TrainSolveScreen.tsx

key-decisions:
  - "Analyze lands on ply - 1 via buildTrainPuzzleAnalysisUrl, shared by the card and the solve screen"
  - "Time-control bucket is capitalized in JS (literal 'Blitz 10' text) rather than a CSS capitalize class, so the text is directly assertable"
  - "TrainArchiveResponse deliberately not added here; it arrives with its consumer in 246-05 (knip)"

requirements-completed: [D-05, D-07, D-08]

duration: 20min
completed: 2026-11-06
---

# Phase 246 Plan 04: TrainPuzzleCard Summary

**Spoiler-free archive card on LazyMiniBoard with an Analyze link that opens the game on the puzzle's own position (ply - 1), shared with the solve screen.**

## Accomplishments

- `TrainPuzzleCard({ item, list })`: horizontal at every width, board left (200px desktop, 50% viewport below `sm`), details and Analyze right. The board receives the pre-mistake FEN, the arriving move as `lastMove`, and no `arrows` prop. A null FEN renders a muted board-sized slot (`train-puzzle-board-unavailable`) and Analyze still works.
- Details block: opponent and rating (`?` for a null name, no parentheses for a null rating), game date `MMM d, yyyy`, time control (`Blitz 10`), and a status line (`Mastered Oct 3, 2026`, `Parked Oct 3, 2026 · 4 misses`, `1 miss` singular, null date dropped).
- `buildTrainPuzzleAnalysisUrl(gameId, ply)` added to `analysisUrl.ts`; `TrainSolveScreen` now uses it instead of the inline expression. `buildGameAnalysisUrl` stays exported.
- No Retry button, no Retry testid, no played move, motif or severity anywhere on the card.

## Task Commits

1. Task 1 (tracer): `ef69653d2` types, helper, card shell with board and Analyze, tests
2. Task 2: `17f858c85` game details, status line, solve screen shares the helper, tests

## Verification

- `npm test` for `TrainPuzzleCard.test.tsx`, `analysisUrl.test.ts`, `TrainSolveScreen.test.tsx`: 240 passed (the existing solve-screen href tests pass unchanged).
- `npm run lint`, `npm run build`, `npm run knip`: clean (knip prints two pre-existing configuration hints only).
- Tracer feedback gate: Task 1's verify (tests, lint, build) re-run end to end before expanding, passed.

### Mutation checks (reverted before commit)

1. `buildTrainPuzzleAnalysisUrl` passing `ply` instead of `ply - 1`: 7 tests failed.
   - `analysisUrl.test.ts` > buildTrainPuzzleAnalysisUrl > lands on the puzzle position by passing ply - 1
   - `TrainPuzzleCard.test.tsx` > Analyze > links to the puzzle position with ply - 1
   - `TrainPuzzleCard.test.tsx` > board > renders the empty board slot ... keeps Analyze working
   - `TrainSolveScreen.test.tsx`: "the action bar appears under the board only once the verdict lands...", "renders the Analyze link when the source game is present", "the Analyze link href is unchanged on a sideline", "mobileBoardControls publishing > publishes for the whole reveal ... with Next and the Analyze URL"
2. Passing an `arrows` array to `LazyMiniBoard`: the no-arrows test failed on both the mastered and parked lists.

Both mutations were restored; the final diff contains neither.

## Deviations from Plan

None in behavior. Notes:

- Test files need `// @vitest-environment jsdom` and an explicit `afterEach(cleanup)` (globals are off), and the project has no jest-dom, so assertions use `getAttribute`, `toBeTruthy` and `toBeNull`.
- The per-plan commit ledger file `gsd-plan-head-before-246-04` was written by hand from the known spawn base `0c84cf49c`, since the worktree git dir could not be written via the Write tool. `commits: 2` was measured with `git rev-list --count` from that base.

## Known Stubs

None. The `list` prop and all card fields are wired to rendered output.

## Threat Flags

None. Usernames render as React text children only (T-246-14); the Analyze URL is built from numeric `game_id` and `ply` only (T-246-17); the card has no arrows and no SAN token (T-246-16, asserted by test).

## Self-Check: PASSED

- FOUND: frontend/src/components/train/TrainPuzzleCard.tsx
- FOUND: frontend/src/components/train/__tests__/TrainPuzzleCard.test.tsx
- FOUND commits: ef69653d2, 17f858c85
