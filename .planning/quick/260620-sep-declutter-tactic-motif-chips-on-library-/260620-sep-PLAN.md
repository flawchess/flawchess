---
quick_id: 260620-sep
title: Declutter tactic motif chips on Library Games tab game card
date: 2026-06-20
status: planned
---

# Quick Task 260620-sep: Declutter tactic motif chips (Games tab card)

## Problem

The Games-tab game card (`LibraryGameCard.tsx`) renders all tactic motif chips in a
single flattened flex-wrap row, each chip carrying a redundant `allowed:` / `missed:`
prefix. Beginner games with many distinct motifs accumulate a wall of chips
(see Phase 130 screenshots). The Flaws tab avoids this (one card per flaw).

Decision (from `/gsd-explore`, 2026-06-20): keep the aggregate per-game tactic view but
compress it. Group chips by orientation (Allowed / Missed), drop the per-chip prefix,
add per-motif occurrence counts (count-first, matching `TagChip`/severity badges), and
cap each group with a `+N more` expander. The "Show Flaws" deep-link button discussed
was scoped OUT (full-stack feature, not quick-task sized) and explicitly NOT captured.

## Scope (frontend only, no backend / no data-shape change)

### Task 1 — `TacticMotifChip.tsx`: support grouped display + count
- Add optional `count?: number` prop. Render count-first (before the icon/label) only
  when `count > 1`, mirroring `TagChip` (`{count != null && count > 1 && <span className="font-bold">{count}</span>}`) and the severity badges.
- Add optional `hidePrefix?: boolean` prop. When true, `visibleLabel` is just the motif
  label (no `allowed:`/`missed:` prefix). **aria-label and testid keep orientation
  unchanged** (accessibility + browser automation must still distinguish orientation).
- Backward compatible: FlawCard (passes neither prop) is unaffected — keeps its prefixed
  label and no count.

### Task 2 — new `TacticMotifGroup.tsx`: one orientation group with cap/expander
- New component under `frontend/src/components/library/`.
- Props: `orientation: 'allowed' | 'missed'`, `label: string`, `gameId: number`,
  `motifs: { motif: string; count: number }[]`, `onChipHover: (motif, active) => void`,
  `onChipActivate: (motif) => void`, `trailing?: React.ReactNode`.
- Renders a `flex flex-wrap items-center gap-1.5` row: a muted `text-sm` leading label
  (`Allowed` / `Missed`), then up to `TACTIC_CHIP_CAP_PER_GROUP` chips (the cap is a named
  constant, default 4), a `+N more` / `Show less` toggle button when over cap, and the
  optional `trailing` slot (used for the shared TagLegend on the last group).
- Local `expanded` state. Chips render with `hidePrefix` + their `count`, passing
  `orientation` through so the active-filter ring + testids still work.
- data-testids: `tactic-group-{orientation}-{gameId}`, `btn-tactic-more-{orientation}-{gameId}`.

### Task 3 — `LibraryGameCard.tsx`: render two groups instead of the flat row
- Replace the single tactic flex-wrap row (lines ~678–700) with a `flex flex-col gap-1.5`
  container that renders a `TacticMotifGroup` for each present orientation (allowed first,
  then missed), gated unchanged on `userProfile?.beta_enabled && tacticMotifs.length > 0`.
- Per-chip count comes from the existing `motifPlies` map:
  `motifPlies.get(motifPliesKey(orientation, motif))?.length ?? 0`.
- `onChipHover` / `onChipActivate` close over the group orientation to build the existing
  `{ kind: 'motif', motif, orientation }` highlight/activate payloads (no behavior change).
- The single TagLegend icon is passed as `trailing` to the LAST present group (so it stays
  on a chip row, not orphaned). `tacticMotifLabels` unchanged.

## Preserve (must not regress)
- Beta gating (`userProfile?.beta_enabled`).
- Active-filter ring highlight on chips (`useFlawFilterStore` in `TacticMotifChip`).
- Click-to-cycle-ply + hover-to-highlight eval-chart behavior.
- TagLegend icon popover explaining the tactic tags.
- Allowed-before-missed ordering.
- FlawCard tactic chips unchanged.

## Verification
- `npx tsc -b` (type-check — esbuild/lint do NOT catch type errors; mandatory per project rule).
- `npm run lint`, `npm test -- --run`.
- Manual reasoning: a busy beginner game now shows `Allowed: <chips> +N more` /
  `Missed: <chips> +N more`, each chip `count`-prefixed when repeated, no per-chip prefix.

## must_haves
- truths: tactic chips grouped into Allowed/Missed; prefix dropped from visible label;
  per-motif counts shown count-first when >1; each group capped with +N more expander.
- artifacts: `TacticMotifGroup.tsx` (new); edited `TacticMotifChip.tsx`, `LibraryGameCard.tsx`.
- key_links: filter ring, cycle/hover, TagLegend, beta gate, FlawCard all preserved.
