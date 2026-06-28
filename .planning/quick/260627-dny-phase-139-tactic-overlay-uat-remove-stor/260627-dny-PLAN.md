---
quick_id: 260627-dny
title: Phase 139 tactic overlay UAT — arrows, eval bar perspective/position, controls eval, remove badge
status: planned
---

# Quick Task 260627-dny

UAT feedback for phase 139 tactic-mode overlay (`/analysis` page). Five changes, all
frontend, across `Analysis.tsx`, `EvalBar.tsx`, `TacticModeOverlay.tsx`.

## Changes

1. **Remove the Stored-PV / Engine arrow-source toggle.** Engine stays always-on. On the
   stored PV line, the blue (best-move) arrow uses the precomputed stored PV move; the grey
   second-best arrow comes from the live engine (`pvLines[1]`). Off-line behavior unchanged
   (blue = engine best, grey = engine second-best). Drop `arrowSource` state, its reset
   effects, `showArrowSourceToggle`, and the toggle UI in TacticModeOverlay.

2. **Eval bar follows board perspective.** Add a `flipped` prop to `EvalBar`. When the board
   is flipped to Black's perspective, the bottom of the bar is Black; in White's perspective
   the bottom is White. Mate label end + text color flip accordingly.

3. **Eval bar on the right, a bit wider.** Reorder the flex-row in `Analysis.tsx` so the bar
   renders after the board (right side). Widen default `w-4` → `w-5`; update the board-column
   fixed width comment/value (504 → 508).

4. **Live eval number in board controls.** Show the live white-POV engine eval (cp/mate) next
   to the engine toggle button in the `infoSlot`, reusing `formatFlawEvalPart`.

5. **Remove the stored-PV eval badge** (`tactic-eval`) from `TacticModeOverlay`, plus its now
   unused eval computation and imports (`Cpu`, `formatFlawEvalPart`, `mateAtPly`, `cn`).

## Verify

- `npm run lint`, `npm test -- --run`, `npx tsc -b` all clean.
- No remaining references to `arrowSource` / `tactic-arrow-source-*` / `tactic-eval`.
