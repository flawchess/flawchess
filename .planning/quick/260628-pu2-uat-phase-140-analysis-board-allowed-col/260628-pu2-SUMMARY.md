---
quick_id: 260628-pu2
slug: uat-phase-140-analysis-board-allowed-col
status: complete
date: 2026-06-28
commit: 582df240
---

# Summary — Quick Task 260628-pu2

Phase 140 full-game analysis board UAT. Three interrelated arrow/depth-overlay fixes,
done inline (well-scoped frontend, no executor subagent).

## Changes

- **`frontend/src/hooks/useGameOverlay.ts`** — Following-best arrow on a flaw position is
  now `TAC_ALLOWED` (crimson) when the flaw allowed a tactic (`depths.allowed != null`),
  else `BEST_MOVE_ARROW`. Mirrors `LibraryGameCard.boardArrows`. Added `TAC_ALLOWED` import.
- **`frontend/src/pages/Analysis.tsx`** — New module helper `forkPlyForOrientation(flawPly,
  orientation)`: missed → `flawPly-1` (decision board), allowed → `flawPly` (flaw position).
  Applied to the insertPvLine effect (+ `allowed_moves.slice(1)` to drop the prepended flaw
  move), `pvSidelineArrows` fork lookup, and `handlePvChipClick` navigation. Sideline-color
  `resolveIdx` shifted -1 for allowed (lead-in dropped). `pvSidelineArrows` now uses
  `isPayoff = stepIntoPv >= rootDisplayDepth` so display-depth 0 is the neutral payoff arrow;
  removed the `isFlawLeadIn` computation.
- **`frontend/src/lib/tacticArrows.ts`** — `buildPvArrow` lost its dead `isFlawLeadIn`
  parameter and branch (no allowed line has a lead-in move now).
- **`frontend/src/hooks/__tests__/useGameOverlay.test.ts`** — Updated the allowed-flaw test
  to assert the crimson following-best arrow (no blue, no teal).

## Result

- `npx tsc -b` clean · `npm run lint` clean (pre-existing `coverage/` warnings only) ·
  `npm test -- --run` 1214 passed · `npm run knip` clean.
- Depth counter now runs ...2, 1 (punchline) then payoff for BOTH orientations; allowed
  is no longer one level low.

## Round 2 (commit 1baecc57)

UAT follow-up: the allowed-tactic **depth number was on the wrong square** — the played
flaw move's target square — instead of the opponent's best-response target. It also
appeared **twice** when the allowed line was opened (played-move glyph + sideline countdown
arrow). Fix: moved the allowed depth label off the played-move square marker and onto the
crimson following-best arrow (its target square is the opponent's response), in both
`useGameOverlay.ts` (analysis board) and `LibraryGameCard.tsx` (game card miniboard). The
square marker keeps only its severity glyph. Re-verified: tsc / lint / 1214 tests / knip.

## Follow-up (HUMAN-UAT)

Visual confirmation on a real game with allowed + missed tactics: arrow colors, the
countdown ending at 1 on the punchline, the allowed line opening at the flaw position, and
the depth number sitting on the opponent's response square (once, not twice).
