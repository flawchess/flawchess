---
quick_id: 260627-l2z
title: "Phase 140 UAT polish round 2 — remove tactic mode, clear stale arrows, PV-line overlay/coloring, flip for black"
status: complete
date: 2026-06-27
---

# Quick Task 260627-l2z — Summary

Five UAT items on the `/analysis` full-game board (game mode = `?game_id=X&ply=Y`).
Built on Quick 260627-jqk (`useGameOverlay`, precomputed blue arrow + eval bar).

## What changed

1. **Removed tactic mode (item 1).** The legacy `?game_id=X&flaw_ply=Y` entry is gone.
   It was reachable only by hand-typed URL / tests (no production link generated it).
   Deleted `components/analysis/TacticModeOverlay.tsx` and
   `pages/__tests__/Analysis.tactic.test.tsx`; relocated the still-needed `buildPvArrow`
   into new `lib/tacticArrows.ts`. `Analysis.tsx` lost ~150 lines of `isTacticMode`
   branching (re-seed effect, per-position flip, depth/payoff derivations,
   `tacticNodeColors`, root/PV arrow branch, the `<TacticModeOverlay>` side panel,
   `?orientation=`/`flaw_ply` parsing, `plyShift`). Game mode and the move-list
   tactic-chip → PV-sideline graft are unchanged.

2. **Stale arrows clear immediately on position change (item 2).** `useStockfishEngine`
   now resets `pvLines`/`evalCp`/`evalMate`/`depth` the moment the analyzed `fen` changes
   (in the debounce effect), so the prior ply's grey/blue arrows never linger. On the game
   main line the precomputed blue best-move arrow + precomputed eval still render
   immediately (via `useGameOverlay`); the live engine's grey 2nd-best reappears when the
   new search reports.

3. **Tactic overlay works on PV-sideline moves (item 3).** New `pvSidelineArrows` in
   `Analysis.tsx`: while navigating a clicked tactic PV sideline (or sitting on its fork),
   the board shows the depth-countdown overlay arrow on the next stored PV move via the
   relocated `buildPvArrow`, mirroring the old tactic-mode overlay. Depth/orientation come
   from `contextualTacticData` + `activePvFlaw.orientation`; the live engine still adds the
   grey 2nd-best. Previously the board went bare on sideline nodes.

4. **Depth-0 resolving sideline move is colored (item 4).** New `sidelineNodeColors` map
   colors the PV node at `missed_tactic_ply_index`/`allowed_tactic_ply_index` blue
   (`TAC_MISSED`, missed) or red (`TAC_ALLOWED`, allowed) in the variation tree, replacing
   the old `isTacticMode`-gated `tacticNodeColors`.

5. **Board + eval chart open from the player's perspective (item 5).** Game mode now
   initializes `boardFlipped` from `gameData.user_color === 'black'` once on load (a
   `hasAutoFlipped` ref lets manual flips win afterward), and passes
   `flipped={user_color === 'black'}` to `<EvalChart>`. Free play (`?fen=`) stays
   white-default.

## Files

- `frontend/src/lib/tacticArrows.ts` (new) — relocated `buildPvArrow`.
- `frontend/src/components/analysis/TacticModeOverlay.tsx` (deleted).
- `frontend/src/pages/__tests__/Analysis.tactic.test.tsx` (deleted).
- `frontend/src/pages/Analysis.tsx` — tactic-mode removal + items 3/4/5.
- `frontend/src/hooks/useStockfishEngine.ts` — clear PV/eval on fen change (item 2).

## Verification

- `npx tsc -b` clean; `npm run lint` clean (only pre-existing `coverage/` warnings);
  `npm run knip` clean; `npm test -- --run` → 1202/1202 pass (was 1206; the 4 deleted
  `Analysis.tactic.test.tsx` cases account for the drop).
- **Not exercised in a real browser (HUMAN-UAT).** Recommended visual checks on an
  analyzed game: (a) no orphaned arrow when scrubbing positions; (b) precomputed blue
  arrow + eval appear instantly, grey 2nd-best follows; (c) clicking a tactic chip and
  walking the sideline shows the depth-countdown overlay arrow; (d) the resolving move is
  red/blue in the move list; (e) a game you played as Black opens flipped.

## Notes

- Item 3's overlay styling mirrors the deleted tactic-mode `buildPvArrow` (depth-countdown
  arrow on the next stored move) — visual confirmation recommended.
- The Phase 139 `## [Unreleased]` CHANGELOG bullet still describes Explore opening "in
  tactic mode"; that wording is now stale (both are unreleased). No changelog edit was made
  here (consistent with the prior phase-140 quick `jqk`); reconcile the Unreleased section
  at milestone close.
