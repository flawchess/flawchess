---
quick_id: 260627-dny
title: Phase 139 tactic overlay UAT — arrows, eval bar perspective/position, controls eval, remove badge
status: complete
commit: 46067dff
---

# Quick Task 260627-dny — Summary

Phase 139 tactic-mode overlay (`/analysis`) UAT feedback. Five frontend changes,
all shipped in one commit (`46067dff`).

## What changed

1. **Removed the Stored-PV / Engine arrow-source toggle** (`TacticModeOverlay`,
   `Analysis.tsx`). The engine is always on. On the stored PV line the blue
   best-move arrow uses the precomputed stored-PV move (`best_move_uci` at ply 0,
   the played move at ply 1+); off-line it uses the live engine best move. The grey
   second-best arrow always comes from the live engine (`pvLines[1]`), deduped
   against the blue arrow. Dropped `arrowSource` state, its reset effects,
   `showArrowSourceToggle`, and the `onArrowSourceChange` plumbing. `handleReset` /
   `canReset` simplified accordingly.

2. **EvalBar follows board perspective** (`EvalBar.tsx`). New optional `flipped`
   prop. White's view (default) puts White at the bottom; flipped to Black's view
   puts Black at the bottom. Fills anchor to the correct end and the mate label
   end + text color flip with them. `Analysis.tsx` passes `flipped={boardFlipped}`.

3. **Eval bar moved to the right of the board and widened** — flex-row reordered;
   default width `w-4` → `w-5`; board-column fixed width `504px` → `508px`.

4. **Live eval number in the board controls** — the live white-POV engine eval
   (`formatFlawEvalPart(engine.evalCp, engine.evalMate)`) renders next to the
   engine toggle button in the `infoSlot` (`data-testid="analysis-live-eval"`),
   hidden while the engine is off or has no score yet.

5. **Removed the stored-PV eval badge** (`tactic-eval`) from `TacticModeOverlay`,
   along with its now-dead eval computation and the `Cpu` / `formatFlawEvalPart` /
   `mateAtPly` / `cn` imports.

## Verification

- `npm run build` (tsc + vite) — pass
- `npm run lint` — 0 errors (3 pre-existing `coverage/` warnings, unrelated)
- `npm run knip` — clean
- `npm test -- --run` — 103 files, 1197 tests pass (includes updated
  `EvalBar.test.tsx` perspective coverage and the `Analysis.tactic.test.tsx`
  Phase 135 regression gate)

## Notes

- The EvalBar perspective test was updated to the new semantics (White at bottom
  in White's view) and a flipped-view case added; the old white-on-top assertion
  contradicted the requested behavior.
- Visual layout changes (bar position, live eval number) are not pixel-asserted by
  tests — a quick manual UAT pass on a real tactic position is recommended.
