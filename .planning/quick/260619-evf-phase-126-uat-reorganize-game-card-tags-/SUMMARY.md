---
quick_id: 260619-evf
title: Phase 126 UAT — reorganize game card tags into severity/tactics/other lines with brown tag-icon legends
status: complete
date: 2026-06-19
---

# Summary

Reorganized the tag block on the Library **game card** (`LibraryGameCard`) into three
labeled lines and replaced the single combined "Tags + info-icon" legend with two
inline brown Tag-icon legends, each scoped to its own line.

## Final layout (analyzed flaw block, both mobile + desktop bodies)

1. **Severity tags** — `SeverityBadge × 3` row (unchanged).
2. **Tactic tags** (beta-gated) — `TacticMotifChip`s, then a brown `Tag`-icon popover
   explaining **only the tactic tags** on this line.
3. **Other tag families** — `TagChip` flaw chips, then a brown `Tag`-icon popover
   explaining **only those flaw tags**.

The old `<span>Tags</span> + HelpCircle` legend was removed from the game card.

## Changes

- `frontend/src/components/ui/info-popover.tsx` — added optional `icon?: LucideIcon`
  prop (default `HelpCircle`) so the trigger glyph can be a brown `Tag` icon. Trigger
  already renders brown (`text-brand-brown-light/70 hover:text-brand-brown`).
- `frontend/src/components/library/TagChip.tsx` — `TagLegend` gains `variant`
  (`'label' | 'icon'`, default `'label'`) and a `testId` override. The `'icon'`
  variant renders a label-less brown `Tag`-icon popover; `'label'` is unchanged so
  `FlawCard` keeps its existing "Tags" legend.
- `frontend/src/components/results/LibraryGameCard.tsx` — split into the 3-line layout;
  one `TagLegend variant="icon"` per chip line (`tag-legend-tactic-*` /
  `tag-legend-*`), each fed only its line's tags/motifs.

## Out of scope

- `FlawCard.tsx` (single-flaw card, Flaws subtab) keeps its inline `label="Tags"`
  legend — the 3-line split only applies to the multi-flaw game card.

## Follow-up (same task, second commit)

- `FlawCard.tsx` (Flaws subtab single-flaw card) — restructured the tags row to a
  single inline wrapping row in the order **severity → tactic chip → other flaw
  chips → brown Tags-icon legend**. The legend (icon variant) explains every tag
  listed except severity; the old inline `label="Tags"` legend was removed.
- Icon swap: the legend trigger now uses lucide `Tags` (plural) instead of `Tag`,
  applied in `TagChip.tsx`'s icon variant so **both** the game card and flaw card
  pick it up.

## Verification

- `npx tsc -b` clean (shared prop-type change), `npm run lint` clean,
  `npm run knip` clean, `vitest run` → 985 passed (both commits).
- Frontend-only. On `gsd/phase-126-comparison-stats-frontend`; not pushed.
- HUMAN-UAT: confirm legend popovers open and list the correct subset on a beta
  account, no "Tags" text remains on either card, and the trigger shows the plural
  `Tags` glyph.
