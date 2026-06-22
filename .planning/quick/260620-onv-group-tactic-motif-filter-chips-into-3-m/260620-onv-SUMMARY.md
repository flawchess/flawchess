---
quick_id: 260620-onv
title: Group tactic-motif filter chips into 3 mechanism sections
status: complete
date: 2026-06-20
---

# Quick Task 260620-onv — Summary

Grouped the flat "Tactic Type" filter chips in the Tags filter panel into three
mechanism-based sections, each with its own scoped legend icon, and switched chip
text to kebab-case. Frontend-only; ran inline (phase branch ahead of main →
worktree isolation fail-closes, per documented recovery).

## What changed

- **`frontend/src/lib/tacticComparisonMeta.ts`**
  - Added `TacticGroupKey` type + ordered `TACTIC_GROUPS` array (`Piece Attacks`,
    `Discoveries & Checks`, `Checkmate`).
  - Added `group` and kebab `chipLabel` to `TacticFamilyDef`.
  - Reordered `TACTIC_COMPARISON_FAMILIES` into grouped/chip order
    (fork, pin, skewer, x_ray, hanging, trapped_piece | discovered_attack,
    discovered_check, double_check | mate) and annotated each entry.
- **`frontend/src/components/filters/FlawFilterControl.tsx`**
  - Replaced the single flat `.map` + master "Tactic Type" label + single
    all-motifs legend with a loop over `TACTIC_GROUPS`: per group → Title-Case
    label + group-scoped `TagLegend` + kebab chips.
  - Removed the now-unused `ALL_TACTIC_MOTIFS` const.
  - Kept per-chip `data-testid="filter-flaw-tactic-${family}"` unchanged; added
    `filter-flaw-tactic-group-${key}` (header), `-legend`, and `-chips` testids.
- **`frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx`**
  - Updated the removed-container assertion to the new group testid; added
    group-header presence + kebab-case chip-text assertions.

## Verification

- `npx tsc -b` — 0 errors
- `npm run lint` — clean
- `npm run knip` — clean
- `npm test -- --run` — 88 files / 1058 tests pass

## Notes

- `x-ray` and `trapped-piece` remain visible though the tagger suppresses them
  today (intentional — they graduate later).
- Comparison grid unaffected: it resolves families by `.find(f => f.family ===)`
  and renders in server order, so the array reorder is invisible to it.
- Display order deliberately does NOT follow detector dispatch priority;
  Discoveries order is general→specific (discovered-attack → discovered-check →
  double-check), reversing the old order.
