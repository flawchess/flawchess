---
quick_id: 260619-dvf
slug: phase-126-uat-tactic-tag-colors-eval-cha
date: 2026-06-19
status: complete
---

# Summary: Phase 126 UAT — tactic tag colors + ordering

Four UAT fixes for the Phase 126 tactic-motif feature.

## What changed

1. **Flaw families → neutral grey** (`frontend/src/lib/theme.ts`)
   All six `FAM_*` (+`_BG`) constants now point at a shared `FAM_NEUTRAL`
   (= `EVAL_CHART_AREA_WHITE_AHEAD`, `oklch(0.78 0 0)`) / `FAM_NEUTRAL_BG`
   (`oklch(0.78 0 0 / 0.15)`). Constant names kept. Only the new `TAC_*` tactic
   families retain hue. Per user decision the grey applies everywhere `FAM_*` is
   consumed: chips, Tags/eval tooltips, the you-vs-opponent Flaw Comparison grid,
   and the Flaws filter panel.

2. **Eval chart tooltip** (`EvalChart.tsx`)
   New `betaEnabled?: boolean` prop. When on and the active marker has a
   `tactic_motif`, the tooltip lists it FIRST (above the flaw tags), styled like
   the other tag rows (family icon + label). Wired from both EvalChart call sites
   in `LibraryGameCard.tsx` via `userProfile?.beta_enabled`.

3. **Games card** (`LibraryGameCard.tsx`)
   Tactic-motif chip row now renders BEFORE the flaw-tag chip row.

4. **Tags tooltip** (`TagChip.tsx` `TagLegend`)
   New optional `tacticMotifs?: string[]` prop; tactic rows render FIRST (family
   icon + `TACTIC_MOTIF_DEFINITIONS`), then flaw-tag rows. Wired from
   `LibraryGameCard.tsx` (`tacticMotifs`) and `FlawCard.tsx`
   (`[flaw.tactic_motif]` when beta + present). Tactic display is beta-gated by
   the callers.

## Verification

- `npx tsc -b` — clean
- `npm run lint` — clean
- `npm run knip` — clean
- `npm test -- --run` — 985 passed (86 files)

## Notes / heads-up

- The grey now also flattens family color-coding in the **Flaw Comparison grid**
  and **Flaws filter panel** (user-confirmed "everywhere"). If that reads as too
  monochrome in those two surfaces, revert just those consumers to keep hue there
  while leaving the chip/tooltip surfaces grey.
- `TagLegend` only mounts when a card has ≥1 flaw tag (existing condition), so a
  tactic motif with no accompanying flaw tag won't appear in the legend; the
  tactic chip itself still shows. Left as-is (out of scope; matches current mount).
