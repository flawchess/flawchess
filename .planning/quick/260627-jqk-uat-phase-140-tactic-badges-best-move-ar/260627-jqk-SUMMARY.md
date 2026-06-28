---
quick_id: 260627-jqk
title: "UAT phase 140 — analysis board: tactic tags, best-move arrows, eval bar, sideline PV, board overlay"
status: complete
date: 2026-06-27
---

# Quick Task 260627-jqk — Summary

Five UAT items on the `/analysis` full-game mode (`?game_id=&ply=`). Tactic mode
(`?flaw_ply=`) and plain mode are unchanged.

## What changed

1. **Removed the tactic-badge block above the engine lines (item 1).** In game mode
   `TacticModeOverlay` (the motif-chip header) is no longer rendered; the overlay is
   tactic-mode-only now. The tactic info lives in the move-list chips and the board
   depth overlay instead.

2. **Move-list tactic tags now show motif name + depth (item 2).** `renderFlawChip`
   renders e.g. `checkmate 4`, `hanging-piece 2` (mate-family collapses to
   `checkmate`) via `tacticMotifLabel` + `tacticDepthBadge`, replacing the literal
   `Missed`/`Allowed`. `FlawMarkerEntry` gained `missedDepth`/`allowedDepth`, populated
   from `FlawMarker.*_tactic_depth` in `Analysis.tsx`.

3. **Clicking a tactic chip now shows the PV as a sideline (item 3).** Root cause:
   `insertPvLine` parks `currentNodeId` at the fork node (on the main line) and
   `buildVariationChain` returns an empty chain there, so the grafted PV never
   rendered. New `resolvePvDisplayChain` renders the full `pvLine` whenever it exists
   and the user hasn't forked off it — applied in both DesktopTree and MobileTree.

4. **Precomputed best move drives the blue arrow + eval bar; engine only supplies the
   grey 2nd line (item 4).** New `hooks/useGameOverlay.ts` mirrors the LibraryGameCard
   miniboard: on the main line it builds a blue best-move arrow from
   `eval_series[ply].best_move` (shown immediately) and drives the eval bar from the
   precomputed eval (synthetic depth so mate renders); the live engine contributes only
   the grey `pvLines[1]` arrow. Off the main line (sideline/fork) the live engine
   drives both blue (`pvLines[0]`) and grey.

5. **Board tactic overlay shows without a loaded PV (item 5).** The same hook adds a
   severity-colored flaw arrow on the played move with the allowed-tactic depth label,
   keyed per ply from the flaw markers — visible while navigating/scrubbing the main
   line, no PV load required (the miniboard behavior).

## Files

- `frontend/src/hooks/useGameOverlay.ts` (new) — precomputed arrows + eval-bar inputs.
- `frontend/src/pages/Analysis.tsx` — wire the hook, merge game-mode arrows, eval bar
  from the hook, drop the game-mode overlay, populate chip depths.
- `frontend/src/components/analysis/VariationTree.tsx` — motif+depth chips, full-pvLine
  sideline rendering.
- `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` — updated chip
  assertions + fixture depth fields.

## Verification

- `npx tsc -b` clean; `npm run lint` clean (only pre-existing `coverage/` warnings);
  `npm run knip` clean; `npm test -- --run` → 1206/1206 pass.
- Not manually exercised in the browser (HUMAN-UAT): visual confirmation of the blue
  arrow timing, grey 2nd-best appearance, eval-bar tracking, and sideline display is
  recommended on a real analyzed game.
