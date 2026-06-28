---
quick_id: 260627-w8k
slug: phase-140-uat-round-6-miniboard-border-h
date: 2026-06-27
status: complete
---

# Summary: Phase 140 analysis-board UAT round 6

Five frontend UAT tweaks for the full-game analysis board. All five verified live in
the browser (Claude-in-Chrome) on `/analysis?game_id=687478&ply=56`. Full frontend
gate green: `tsc -b` clean, eslint 0 errors (3 pre-existing warnings in generated
`coverage/`), 1205 vitest tests pass.

## What changed

1. **Miniboard hover tooltip** (`32fbec93`) — the engine-line hover miniboard had a
   dark padding frame (the shared tooltip's `px-3 py-1.5 bg-foreground`) and square
   corners poking out of the `rounded-md`. Added an optional `contentClassName` to the
   `Tooltip` (merged last so tailwind-merge wins) and passed `p-0 overflow-hidden` from
   `EngineLines`, so the board fills the box with clipped rounded corners and no frame.
   The played PV move now gets a green overlay (`lastMove` + `MOVE_HIGHLIGHT_GOOD`).

2. **Eval-chart slider ↔ board-controls alignment** (`a51fd685`) — the 4th attempt,
   root-caused in the browser. The `lg:items-stretch` row stretched the *shorter* board
   column to match the right column, whose `max-h-[455px] mb-[25px]` move list inflated
   the row to 677px and left 42px dead space under the slider (49px misalignment). Fix:
   the move-list scroller is now `absolute inset-0` inside a `relative` flex parent, so
   it can't inflate the row's intrinsic height — the board column drives the height and
   the controls bottom-align with the slider. **Measured: controls bottom 742→700 = eval
   slider container bottom, diff 0, no magic numbers.** Prior `max-h`/`mb` tweaks could
   never fix it because they don't stop the list from inflating the row.
   - **Follow-up** (`fix` commit): the user still saw a residual gap. Re-measured at
     multiple window sizes: at `lg` both columns equalise at the eval-chart container
     bottom, but the slider `<input>` was `inline-block`, leaving ~7px of descender
     space below it inside the container — so the bottom-aligned controls hung 7px below
     the slider's actual bottom. Made the input `block`: container bottom == slider
     bottom == controls bottom (browser-verified delta 0).

3. **Move-list badges on a new line** (`a51fd685`) — tactic pill chips now render on
   their own line below the SAN move (the `??`/`?` severity glyph stays inline as
   standard chess annotation); rows top-align so the move number lines up with the SAN.

4. **Live free-move classification** (`755ece45`, `e116912c`) — user chose to classify
   *any* played move via the live engine. New `lib/liveFlaw.ts` (engine cp/mate → mover
   expected score via the Lichess sigmoid, mate→±1000cp; drop tiers 0.05/0.10/0.15) and
   `useLiveMoveFlaw.ts`. `Analysis.tsx` caches each position's completed engine eval
   (state-backed, FIFO-capped) and, for any node off the precomputed line (incl.
   free-play), grades the move (parent-eval vs child-eval) into a blunder/mistake/
   inaccuracy glyph + colored square overlay; the precomputed overlay still wins on the
   main line. Generated `flawThresholds.ts` extended (via the generator) so the tiers
   stay a single source of truth with the backend. **Verified live: Nc7-e8 → `?!`
   inaccuracy + yellow overlay on both squares.**

5. **Missed tactics one ply earlier** (`a51fd685`, `cfaa7856`, `e116912c`) — the missed
   tactic belongs to the *decision* position (`ply-1`), where the blue best-move arrow
   already points to the missed move. The arrow now carries the missed depth label on
   the analysis board (`useGameOverlay`) and minimap (`LibraryGameCard`); the eval-chart
   tooltip sources its missed line from `ply+1`; and the move-list missed chip renders on
   the decision node (`mainLine[ply-1]`). The allowed tactic + severity glyph stay on the
   flaw move. **Verified: the blue "checkmate 3" chip moved from Qb3 (move 29) to the
   Nc7 decision node (move 28); the red "hanging-piece" allowed chip stayed put.**

## Verification
- Browser: item 2 geometry (controls bottom == slider container bottom = 700, diff 0);
  item 1 tooltip (rounded, no frame, green overlay); item 3 badge wrap; item 4 live
  classification (`?!` on a free move); item 5 missed-chip shift in the move list.
- `cd frontend && npx tsc -b` clean; `npm run lint` 0 errors; `npm test -- --run` 1205 pass.
- `uv run python scripts/gen_flaw_thresholds_ts.py --check` (no drift); ruff clean.

## Notes
- No backend changes. Live classification depends on the live engine, so the glyph
  appears with engine lag and can differ slightly from the game's stored classification
  (caveat accepted by the user when choosing "live-classify any move").
