---
quick_id: 260619-evf
title: Phase 126 UAT — reorganize game card tags into severity/tactics/other lines with brown tag-icon legends
status: in-progress
date: 2026-06-19
---

# Phase 126 UAT — game card tag reorganization

## Goal

Reorganize the tag block in the **Library game card** (`LibraryGameCard.tsx`, the
"games and flaws" card on the Games subtab) into three clearly separated lines, each
with its own explanation popover, and drop the now-redundant `"Tags" + info icon`
label row.

## Target layout (analyzed flaw block)

1. **Line 1 — severity tags** (unchanged): the `SeverityBadge × 3` row.
2. **Line 2 — tactic tags** (beta-gated): the floating `TacticMotifChip`s, followed
   by a brown `Tag`-icon popover that explains **only the tactic tags** on this line.
3. **Line 3 — other tag families**: the `TagChip` flaw chips, followed by a brown
   `Tag`-icon popover that explains **only those flaw tags**.
4. **Remove** the old combined `<span>Tags</span> + HelpCircle` legend.

## Changes

### 1. `frontend/src/components/ui/info-popover.tsx`
- Add optional `icon?: LucideIcon` prop (default `HelpCircle`) so the trigger glyph
  can be swapped. The trigger already renders brown (`text-brand-brown-light/70
  hover:text-brand-brown`), which satisfies the "brown tag icon" requirement.

### 2. `frontend/src/components/library/TagChip.tsx` (`TagLegend`)
- Add a `variant?: 'label' | 'icon'` prop (default `'label'`) and an optional
  `testId` override so two legends can coexist on one card.
- `variant='icon'`: render just the `InfoPopover` with `icon={Tag}` and no visible
  "Tags" label (the brown tag icon IS the affordance).
- `variant='label'`: unchanged (FlawCard keeps its current legend).

### 3. `frontend/src/components/results/LibraryGameCard.tsx`
- Tactic line: append `<TagLegend variant="icon" tags={[]} tacticMotifs={tacticMotifs} ... />`.
- Flaw-tag line: replace the existing `<TagLegend ... label="Tags" />` with
  `<TagLegend variant="icon" tags={game.chips} tacticMotifs={[]} ... />`.
- Give the two legends distinct testids (`tag-legend-tactic-*` / `tag-legend-*`).

## Out of scope
- `FlawCard.tsx` (single-flaw card on the Flaws subtab) keeps its inline `label="Tags"`
  legend — the 3-line split only applies to the multi-flaw game card.

## Verification
- `npm run lint`, `npm test -- --run`, `npx tsc -b` (shared-type / prop changes).
- Visual: both popovers open and list the correct subset; no "Tags" text remains on
  the game card; mobile + desktop bodies both updated (shared `flawContent`).
