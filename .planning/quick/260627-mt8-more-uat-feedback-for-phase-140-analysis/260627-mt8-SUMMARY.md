---
quick_id: 260627-mt8
title: Phase 140 analysis-board UAT polish round 3
status: complete
date: 2026-06-27
---

# Quick Task 260627-mt8 — Summary

Phase 140 `/analysis` game-mode UAT polish, round 3. Seven frontend tweaks, all
green through `tsc -b` + ESLint + Vitest (1203 tests) + knip.

## What changed

1. **Engine info line** — new always-visible header above the engine PV lines:
   `<engine toggle> SF 18, Depth <d>` (`data-testid="analysis-engine-info"`). The
   Cpu toggle (moved off the board control bar) enables/disables the engine; depth
   reads from the live engine and only renders while the engine is on and searching.
   `SF 18` matches the bundled `stockfish-18-lite-single` WASM.

2. **Eval badges + single-line PV rows** (`EngineLines.tsx`) — each PV line is now
   one row: a filled eval badge then the move chips. Best line = blue
   (`BEST_MOVE_ARROW`), second = grey (`ARROW_NEUTRAL`), matching the board arrows.
   The old two-row score-header layout and the `d{depth}` badge are gone; the
   `depth` prop was removed from `EngineLines`.

3. **Relocated/removed controls** — engine on/off toggle dropped from `BoardControls`
   (now in the info line); depth badge removed from the best line (now in the info line).

4. **Fixed-height loading container** — the engine-lines region sits in a
   `min-h-[60px]` container and the "Analyzing…" indicator lost its spinner for a
   fixed-height placeholder, so the panel no longer jumps loading → analyzing → 2 lines.

5. **Move-list sizing + bottom alignment** — right column narrowed to `lg:w-[360px]`,
   the row set to `lg:items-stretch`, and `VariationTree` made `flex-1` fill-and-scroll,
   so `BoardControls`'s bottom vertically aligns with the eval-chart slider's bottom.

6. **Eval-chart sync on navigation** — new `syncPly` prop on `EvalChart` parks the
   slider at a parent-driven ply without surfacing the tooltip or stealing focus
   (unlike `commandedPly`, which would break keyboard board navigation). Analysis
   drives it from the board's current main-line ply.

7. **Sideline → fork point** — `syncPly` resolves to the nearest main-line ancestor
   when off the main line, so clicking a sideline move parks the eval chart at the
   position the sideline branches from.

## Files

- `frontend/src/components/analysis/EngineLines.tsx`
- `frontend/src/pages/Analysis.tsx`
- `frontend/src/components/library/EvalChart.tsx`
- `frontend/src/components/analysis/VariationTree.tsx`
- `frontend/src/components/analysis/__tests__/EngineLines.test.tsx`

## Verification

- `npx tsc -b` — clean
- `npm run lint` — 0 errors (3 warnings are in generated `coverage/`, unrelated)
- `npm test -- --run` — 103 files, 1203 tests passing
- `npm run knip` — clean

**HUMAN-UAT:** items 1–7 are visual/interactive. Loop-sync (item 6/7) is loop-safe by
construction (on the main line `syncPly == current ply` → idempotent re-navigation; on a
sideline the disabled slider just parks at the fork). The exact pixel alignment of item 5
and the badge look (item 2/3) want a visual confirmation on a real game in the browser.
No automated coverage was added for the layout/alignment changes.
