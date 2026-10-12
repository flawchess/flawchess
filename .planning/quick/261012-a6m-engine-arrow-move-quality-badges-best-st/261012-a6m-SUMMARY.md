---
phase: quick-261012-a6m
plan: 01
subsystem: frontend-engine-arrows
tags: [stockfish, arrows, move-quality-badges, analysis, train]
requires: []
provides:
  - lib/engineArrowGrades (gradeEngineLines, secondaryArrowAlpha, badge builders, mergeEngineBadges)
affects:
  - Analysis board Stockfish arrows and square markers
  - Train step-preview and free-play boards
tech-stack:
  added: []
  patterns: [single grade pass feeds arrow alpha and badge opacity, collision authority via mergeEngineBadges]
key-files:
  created:
    - frontend/src/lib/engineArrowGrades.ts
    - frontend/src/lib/__tests__/engineArrowGrades.test.ts
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/hooks/analysis/useAnalysisBoardArrows.ts
    - frontend/src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts
    - frontend/src/lib/trainArrows.ts
    - frontend/src/lib/__tests__/trainArrows.test.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx
    - CHANGELOG.md
decisions:
  - "STOCKFISH_SECONDARY_ALPHA_MAX 0.6 / MIN 0.25 in theme.ts (owner-UAT tunable)"
  - "ENGINE_ARROW_GRADE_MIN_DEPTH = 10 is its own constant (avoids import cycle with trainArrows)"
  - "BLUNDER_DROP imported from @/generated/flawThresholds (same constant classifyLiveSeverity uses)"
metrics:
  completed: 2026-10-12
  duration: ~25 min
status: complete
commits: 3
plan_head_before: 0a9185d84ad04ed70d075388f9fc153b599baef6
plan_head_after: ed23039f9655b89437022aeb8e7d9ee98455b866
actuals:
  tokens: 16000
  tasks: 3
  commits: 3
---

# Quick 261012-a6m: Engine arrow move-quality badges Summary

Stockfish arrows on the Analysis board and the Train step/free-play boards now carry a best-move star (top line, opaque) or a good/inaccuracy/mistake/blunder badge (other lines), graded against the top line through the existing expected-score pipeline, with arrow alpha and badge opacity both derived from the same expected-score drop.

## What was built

- `frontend/src/lib/engineArrowGrades.ts`: pure module. `gradeEngineLines(lines, fen)` does ONE grade pass per position (side-to-move POV, depth gate 10, null for shallow/unscored lines). `secondaryArrowAlpha` maps drop 0..BLUNDER_DROP linearly to MAX..MIN. `stockfishSecondaryArrowColor`, `engineBadgeMarker`, `buildRankedEngineBadges`, `mergeEngineBadges` (existing marker wins, then higher rank; returns the same array identity when nothing is added).
- `theme.ts`: `STOCKFISH_ARROW_RGB`, `STOCKFISH_SECONDARY_ALPHA_MAX` (0.6), `STOCKFISH_SECONDARY_ALPHA_MIN` (0.25); comment on `STOCKFISH_SECONDARY_LINE` rewritten as the pre-gate fallback.
- `useAnalysisBoardArrows`: one `stockfishGrades` memo feeds the Stockfish arrow colors and the badges; old marker memo renamed `baseSquareMarkers` (also what `lastMoveTierColor` reads); new `boardSquareMarkers` merges engine badges only while the engine arrows are visibly drawn (engine on, no hover overlay, no PV-sideline overlay). FlawChess arrows untouched.
- `trainArrows`: `buildTrainFreePlayOverlay` and `buildTrainStepOverlay` return `{ arrows, badges }` from one grade pass. Step preview pointer gets an opaque star only when it is the live top move, an opaque graded badge when it matches a lower live line, none otherwise. One `drawnLiveRanks` predicate shared by arrow and badge loops.
- `TrainSolveScreen`: off-root branch extracted to `resolveOffRootOverlay`; merges engine badges under the chip/tree markers. Reveal-root overlay unchanged.

## Deviations from Plan

None to the design. Test expectation changes (legitimate consequences of D-04/D-08):
- `TrainSolveScreen.test.tsx`: two sideline tests now expect 2 markers (the played-move badge plus the opaque best star on the engine/preview top move) instead of 1.
- `Analysis.test.tsx` "SF arrows 2": translucent arrow now selected by `stockfishSecondaryArrowColor` at ALPHA_MIN, plus an assertion that a `<g opacity=ALPHA_MIN>` marker group renders.
- A malformed top-line first move still grades the remaining ranks (the top line is scored); test written to match.

Note: with the Stockfish arrows setting at 0 on a Train step board, the solid preview pointer still gets its star when it matches a live line (the badge follows the pointer, which always draws).

## Verification

From `frontend/`: `npm run lint` clean, `npm run build` clean, `npm test -- --run` 322 files / 5427 tests pass, `npm run knip` exit 0 (two pre-existing config hints). `npm run lint:cognitive`: no new function over 15 (remaining reports are pre-existing: TrainSolveScreen component line 611, useAnalysisGemMarkers, uciParser).

## Commits

- c3e457f50 feat: grade Stockfish arrows and badge them on the Analysis board
- e805415e8 feat: graded arrows and quality badges on Train step and free-play boards
- ed23039f9 test: page-level graded arrow and badge opacity, changelog entry

## Known Stubs

None.

## Self-Check: PASSED
