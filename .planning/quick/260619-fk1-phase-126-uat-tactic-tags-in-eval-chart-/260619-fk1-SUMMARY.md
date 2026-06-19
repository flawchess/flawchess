---
quick_id: 260619-fk1
title: "Phase 126 UAT — tactic tags in eval-chart tooltip + hover/click parity"
status: complete
created: 2026-06-19
completed: 2026-06-19
---

# Quick Task 260619-fk1 — Summary

Addressed four Phase 126 UAT items on the Library Games card so tactic-motif chips
behave exactly like the flaw-tag chips / severity badges.

## What changed

1. **Tactic motif now shows in the eval-chart tooltip.** The tooltip already
   rendered the motif gated on `betaEnabled`, but the **desktop** `EvalChart` call
   site in `LibraryGameCard` never passed the prop (only the mobile one did), so it
   was silently off on desktop. Added
   `betaEnabled={userProfile?.beta_enabled ?? false}` to the desktop call site.
2. **Removed the per-chip definition popover** from `TacticMotifChip`. Definitions
   are surfaced once via the shared `TagLegend` below the chip row (same as the
   flaw-tag chips, which already render with `definition={false}`). Dropped the
   Radix popover, its open/close timers, and the now-unused `useIsMobile` helper.
3. **Hover-highlight parity.** `TacticMotifChip` gained an optional `onHover` prop;
   the card wires it to `setHighlightYieldingFocus({ kind: 'motif', motif })`, so
   hovering a tactic chip emphasizes matching eval-chart markers and dims the rest.
4. **Click-to-cycle parity.** `TacticMotifChip` gained an optional `onActivate`
   prop; the card wires it to `handleActivate({ kind: 'motif', motif })`. Extended
   the existing `FlawRef` union with a `{ kind: 'motif'; motif: string }` variant
   and added a `motifPlies` map (mirroring `tagPlies`) so the same cycle/highlight
   machinery resolves a motif's flaw plies.

On FlawCard (no callbacks) the chip is now a plain decorative span, matching the
sibling `TagChip`s there.

## Files

- `frontend/src/components/library/TacticMotifChip.tsx` — drop popover; add
  `onHover`/`onActivate`; interactive-only-with-callbacks (mirrors `TagChip`).
- `frontend/src/components/results/LibraryGameCard.tsx` — `FlawRef` motif variant,
  `sameFlawRef`, `motifPlies`, `highlightedPlies`/`pliesForRef` motif handling,
  chip wiring, desktop `betaEnabled` fix.
- `frontend/src/components/library/__tests__/TacticMotifChip.test.tsx` — dropped
  popover assertions; added decorative-default + interactive (hover/click/keyboard)
  coverage.

## Gate

`npx tsc -b` ✓ · `npm run lint` ✓ · `npm test -- --run` ✓ (86 files, 987 tests) ·
`npm run knip` ✓
