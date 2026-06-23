---
quick_id: 260619-dvf
slug: phase-126-uat-tactic-tag-colors-eval-cha
date: 2026-06-19
status: in-progress
---

# Quick Task: Phase 126 UAT — tactic tag colors + ordering

Four UAT fixes for the Phase 126 tactic-motif feature.

## Decisions

- **Gray scope (user-confirmed):** set ALL six `FAM_*` flaw-family color
  constants to the neutral light grey used for the white-ahead eval area
  (`EVAL_CHART_AREA_WHITE_AHEAD = oklch(0.78 0 0)`). This also affects the
  you-vs-opponent Flaw Comparison grid and the Flaws filter panel (accepted).
  Constant *names* are kept; only values change. Tactic `TAC_*` constants are
  left untouched so only tactic families carry hue.
- Tactic display in tooltips/legend is **beta-gated** to match the rest of the
  feature (chips are already beta-gated).

## Tasks

1. **theme.ts** — set `FAM_TEMPO/OPPORTUNITY/IMPACT/SEVERITY/PHASE/COMBO` (+ `_BG`)
   to the neutral grey (solid `EVAL_CHART_AREA_WHITE_AHEAD`, bg `oklch(0.78 0 0 / 0.15)`).

2. **EvalChart.tsx** — add `betaEnabled?: boolean` prop; render the active
   marker's `tactic_motif` (if present) as a tooltip row, listed FIRST (above the
   flaw-tag list), styled like the other tag rows (family icon + label). Gated on
   `betaEnabled`. Wire `betaEnabled` from both call sites in LibraryGameCard.

3. **LibraryGameCard.tsx** — render the tactic-motif chip row BEFORE the flaw-tag
   chip row (tactic first). Pass `betaEnabled` + `tacticMotifs` down.

4. **TagChip.tsx (TagLegend)** — add optional `tacticMotifs?: string[]` prop;
   render tactic rows FIRST (family icon + `TACTIC_MOTIF_DEFINITIONS`), then the
   flaw-tag rows. Wire from LibraryGameCard (`tacticMotifs`) and FlawCard
   (`[flaw.tactic_motif]` when beta + present).

## Verification

- `npm run lint`, `npm test -- --run`, `npx tsc -b` (shared-type/prop changes), `npm run knip`.
