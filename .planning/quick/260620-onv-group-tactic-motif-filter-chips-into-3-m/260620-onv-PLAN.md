---
quick_id: 260620-onv
title: Group tactic-motif filter chips into 3 mechanism sections
status: ready
date: 2026-06-20
---

# Quick Task 260620-onv: Group tactic-motif filter chips into 3 mechanism sections

Converged in `/gsd-explore`. Frontend-only. Reorganize the flat "Tactic Type"
filter chips in the Tags filter panel into three mechanism-based groups, each with
its own scoped legend icon. Chips become kebab-case.

## Decisions (locked)

- **Groups + chip order:**
  - **Piece Attacks:** `fork, pin, skewer, x-ray, hanging-piece, trapped-piece`
  - **Discoveries & Checks:** `discovered-attack, discovered-check, double-check`
  - **Checkmate:** `mate-patterns`
- Drop the master "Tactic Type" label; the three group labels stand alone.
- Chip text = kebab-case (`hanging-piece`, not "Hanging piece"). Group titles = Title Case with `&`.
- Keep `x-ray` and `trapped-piece` visible even though the tagger suppresses them today.
- Each group label gets its own brown `TagLegend variant="icon"` scoped to that group's motifs (3 legends, not 1 over all 10). No new glyphs — reuse the Tags icon.
- No per-chip icons (chips stay text-only).
- "Discoveries & Checks" order deliberately reverses the old detector/UI order (discovered-attack → discovered-check → double-check, general→specific). Display order does NOT follow dispatch priority.

## Tasks

### Task 1 — meta source of truth (`frontend/src/lib/tacticComparisonMeta.ts`)
- Add `group: TacticGroupKey` and `chipLabel: string` to `TacticFamilyDef`.
- Add `TacticGroupKey` type + ordered `TACTIC_GROUPS` array (`{ key, label }`).
- Reorder `TACTIC_COMPARISON_FAMILIES` into grouped/chip order; annotate each with `group` + kebab `chipLabel`. (Grid looks up by `.find(family===)` and renders in server order — reorder is safe.)
- **verify:** grid still resolves every family by key; `mate.chipLabel === 'mate-patterns'`.
- **done:** types compile; both consumers (grid + filter) import cleanly.

### Task 2 — filter render (`frontend/src/components/filters/FlawFilterControl.tsx`)
- Replace the single flat `.map` over `TACTIC_COMPARISON_FAMILIES` (+ the master "Tactic Type" label and its single `ALL_TACTIC_MOTIFS` legend) with a loop over `TACTIC_GROUPS`: per group → Title-Case label + group-scoped `TagLegend` (motifs = that group's families' motifs) + the group's chips (kebab `chipLabel`).
- Remove the now-unused `ALL_TACTIC_MOTIFS` const.
- Keep per-chip `data-testid="filter-flaw-tactic-${family}"` unchanged; add `data-testid="filter-flaw-tactic-group-${key}"` on each group header.
- text-sm floor; no `text-xs`.
- **verify:** `FlawFilterControl` has no mobile/desktop duplicate of this block (single component); search confirms.
- **done:** `npm run build` (tsc), `npm run lint`, `npm test -- --run`, `npm run knip` all green.

## Must-haves
- 3 group headers render with scoped legends; 10 chips total in the specified order.
- Chips read kebab-case; group titles read Title Case.
- No master "Tactic Type" label.
- Existing per-chip testids intact; new group-header testids added.
- Comparison grid unaffected.
