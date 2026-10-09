---
phase: quick-261009-por
plan: 01
subsystem: frontend/train
tags: [train, reveal, engine-arrows, stockfish]
status: complete
requirements: [QUICK-261009-por]
key-files:
  modified:
    - frontend/src/lib/trainArrows.ts
    - frontend/src/lib/__tests__/trainArrows.test.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/hooks/useTrainRevealTree.ts
    - frontend/src/hooks/__tests__/useTrainRevealTree.test.ts
    - CHANGELOG.md
decisions:
  - "Depth gate TRAIN_STEP_LIVE_ARROW_MIN_DEPTH = 12, checked per PvLine"
  - "Puzzle position uses the same MultiPV width as known lines and sidelines (no third special case)"
  - "End of line (null next move): deep live moves still draw as secondaries, no primary"
actuals:
  tasks: 2
  commits: 2
plan_head_before: b19a96710f25f8a1dce6eda9845f659c645d42aa
plan_head_after: 9284b51053ffca87df046c158ce41a2e3041e50f
---

# Phase quick-261009-por Plan 01: Live engine arrows on known lines Summary

On a stepped known-line position the board keeps the solid blue line pointer (painted last) and adds the reveal engine's other top moves as translucent secondary arrows, gated on per-line depth >= 12 and deduped by from-to squares; the reveal engine now searches at max(Stockfish lines, Stockfish arrows) on every node.

## Tasks

1. **Tracer** (c23c5c5c9): `buildTrainStepOverlayArrows` + `TRAIN_STEP_LIVE_ARROW_MIN_DEPTH` in `trainArrows.ts`; `resolveRevealBoardOverlay` step branch fed `revealTree.pvLines` and `sfArrows`; 11-case unit matrix; end-to-end component test (FakeWorker gained an optional depth parameter defaulting to 10, so all existing stepped-position tests are the below-gate check and pass unchanged).
2. **Expansion** (9284b5105): removed `TRAIN_REVEAL_ONLINE_MULTIPV`, `multiPv: Math.max(sfLines, sfArrows)` unconditionally; hook test rewritten (default 2 at root and on known line, arrows 3 gives 3); CHANGELOG bullet.

## Verification

- Full frontend suite: 5459 tests passed.
- `npm run lint`, `npm run build` (tsc -b), `npm run knip`: all clean (knip exit 0).

## Deviations from Plan

None - plan executed as written.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
