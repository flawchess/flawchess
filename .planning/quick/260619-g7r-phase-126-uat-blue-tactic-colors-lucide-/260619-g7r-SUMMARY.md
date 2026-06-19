---
quick_id: 260619-g7r
title: "Phase 126 UAT: blue tactic colors, lucide-move-up icon, tactic tooltip explanations"
status: complete
date: 2026-06-19
---

# Quick Task 260619-g7r — Summary

Phase 126 UAT, three frontend-only tweaks to the tactic-motif feature.

## Changes

1. **All tactic motif colors are now blue.** `frontend/src/lib/theme.ts`: introduced
   `TAC_BLUE` / `TAC_BLUE_BG` (the indigo `oklch(0.68 0.16 240)` previously used only
   for pin/skewer) and pointed all six `TAC_*` family color constants (and `_BG`
   variants) at them. Mirrors the existing `FAM_NEUTRAL` grey-collapse pattern; the
   per-family constant names are preserved so every `TAC_*` consumer (tactic chips,
   Tactic Motifs comparison grid icons, Flaws filter panel) renders the single blue.

2. **Pin/skewer icon → `MoveUp`.** `frontend/src/lib/tacticComparisonMeta.ts`: swapped
   the `pin_skewer` family icon from `Minus` to `lucide-react`'s `MoveUp` (import
   updated, `Minus` dropped).

3. **Tactic comparison tooltip now explains the tactic.** Added a `definition` field
   to `TacticFamilyDef` and wrote one-line explanations for all six families in
   `TACTIC_COMPARISON_FAMILIES`. `TacticBulletPopover` (in
   `frontend/src/components/library/TacticComparisonGrid.tsx`) first paragraph now
   renders the family-colored icon + bold label + definition, matching the flaw-tag
   tooltip format (`FlawBulletPopover`). The prior "tactic flaws allowed per game"
   label line was replaced; the you/opponent rates, sign-convention, and confidence
   paragraphs are unchanged.

## Verification

- `tsc -b` clean, `eslint` clean, `knip` clean.
- `vitest` library + lib suites: 334 passed (incl. TacticComparisonGrid 29, TacticMotifChip).
- No test assertions referenced the old first-paragraph text or per-family hues.

Frontend-only. On branch `gsd/phase-126-comparison-stats-frontend`; not pushed.
