---
quick_id: 260628-ojq
title: "Phase 140 UAT: tactic-colored arrows on flaw/game cards and analysis board sideline"
status: complete
date: 2026-06-28
commit: 71aa4df6
---

# Quick Task 260628-ojq — Summary

## What changed

Recolored tactic-related board arrows and sideline moves so a move that belongs to a
missed or allowed tactic is drawn in that tactic's color (allowed → teal `TAC_ALLOWED`,
missed → magenta `TAC_MISSED`), matching the tactic chips.

### FlawCard (`frontend/src/components/library/FlawCard.tsx`)
- Played-move (flaw) arrow: teal when the move allowed a tactic, else severity color.
- Best-move arrow: magenta when a tactic was missed, else blue.
- Both gated on the same `tacticOrientation` + motif condition that controls whether the
  matching tactic chip renders, so the arrow color and chip can never disagree.

### LibraryGameCard (`frontend/src/components/results/LibraryGameCard.tsx`)
- The following-best arrow (the opponent's refuting response while scrubbing a flaw ply)
  turns teal when that flaw allowed a tactic (`tacticDepthByPly.get(activePly)?.allowed`);
  otherwise stays the neutral best-continuation blue.
- Missed tactics were already drawn via the violet should-have-played arrow — unchanged,
  per the UAT note.

### Analysis board sideline (`frontend/src/pages/Analysis.tsx`, `frontend/src/lib/tacticArrows.ts`)
- `sidelineNodeColors`: now colors every PV-sideline move from the fork up to and including
  the depth-0 resolving move in the orientation color (previously only the resolving move).
- `buildPvArrow`: the countdown arrows up to depth 0 are painted in the orientation color
  (teal/magenta) instead of `BEST_MOVE_ARROW` blue; past the punchline they keep the lighter
  neutral `PAYOFF_MOVE_ARROW` color. The allowed flaw lead-in arrow was already teal.
  `BEST_MOVE_ARROW` import dropped (no longer used in this module).

## Verification
- `npx tsc -b` — clean
- `npm run lint` — clean (3 pre-existing warnings in `coverage/`, unrelated)
- `npm run knip` — clean
- `npm test -- --run` — 1214 tests pass (103 files)

## Follow-up: orientation colors swapped (same task)
Per UAT follow-up the two orientation hues were swapped in `theme.ts` (constant names
unchanged, so every chip/arrow/badge/tooltip propagates automatically):
- **missed** → teal (`oklch(0.70 0.15 200)`), formerly the allowed color.
- **allowed** → crimson (`oklch(0.60 0.22 10)`). A vivid pink-red in the warm "this hurt you"
  family, set apart from the blunder's orange-red (hue 25) by being more saturated (chroma
  0.22 vs 0.19), a touch lighter, and hue-shifted toward magenta. Interim tries — a lighter
  wine red, a cool purple/violet, then a dark burgundy — were dropped (wine/burgundy too close
  to or muddier than the blunder, purple too detached from any "bad" cue).
- `TAC_*_LABEL`, `_BG`, `_BORDER` variants updated to match. Color-name comments across
  `useGameOverlay.ts`, `LibraryGameCard.tsx`, `Analysis.tsx`, `tacticArrows.ts`, `FlawCard.tsx`
  updated (violet/magenta → teal, teal → wine red) so they no longer lie.

## Notes / decisions
- No new color constants introduced; only the hue/lightness values behind `TAC_MISSED`
  and `TAC_ALLOWED` changed.
- FlawCard gates the recolor on motif+orientation (motif is directly available); the game
  card gates on the allowed depth badge, matching its existing violet should-have arrow,
  which also gates on the depth badge. Each card is internally consistent.
