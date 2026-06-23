---
quick_id: 260620-sep
title: Declutter tactic motif chips on Library Games tab game card
date: 2026-06-20
status: complete
commit: ef0dc775
---

# Quick Task 260620-sep — Summary

## What changed

Compressed the Games-tab game card's tactic motif chips so beginner games with many
distinct motifs no longer pile up a wall of prefixed chips. Decision came from a
`/gsd-explore` session: keep the aggregate per-game tactic view (recurring motifs +
filter affordance matter) but make it compact.

**`TacticMotifChip.tsx`** — two new optional, backward-compatible props:
- `hidePrefix` — drops the visible `allowed:`/`missed:` prefix (aria-label + testid still
  encode orientation for accessibility + browser automation).
- `count` — renders a count-first occurrence count when `> 1`, matching `TagChip` and the
  severity badges.
- FlawCard passes neither → its chips are unchanged (keep prefix, no count).

**`TacticMotifGroup.tsx`** (new) — one orientation group: a muted `text-sm` leading label
(`Allowed`/`Missed`), the chips (rendered `hidePrefix` + `count`), and a `+N more` /
`Show less` toggle that caps visible chips at `TACTIC_CHIP_CAP_PER_GROUP = 4`. Owns the
`expanded` state and an optional `trailing` slot for the shared TagLegend.

**`LibraryGameCard.tsx`** — the flat tactic row is replaced by a `flex flex-col` of one
`TacticMotifGroup` per present orientation (allowed first, then missed), still gated on
`beta_enabled && tacticMotifs.length > 0`. Per-chip counts derive from the existing
`motifPlies` map; the single TagLegend icon rides on the last present group. New
`TACTIC_ORIENTATIONS` / `TACTIC_ORIENTATION_LABELS` constants.

## Preserved (verified)
- Beta gating, active-filter ring, click-to-cycle-ply + hover highlight, TagLegend popover,
  allowed-before-missed ordering, FlawCard appearance. Chip testids still encode orientation
  (`chip-tactic-{orientation}-{motif}-{gameId}`), so existing Games-card tests pass unchanged.

## Verification
- `npx tsc -b` → 0 errors.
- `npm run lint` (eslint) → clean.
- `npm run knip` → clean (new component imported; no dead exports).
- `npm test -- --run` → 90 files, 1072 tests passed.
- Manual visual check (busy beginner game, beta user) left to the user — the change is
  visual and the exact game is in the Phase 130 screenshots.

## Scoped out (intentionally not captured)
- "Show Flaws" deep-link button (Games card → Flaws tab filtered to that game). It needs a
  new `game_id` filter built end-to-end (backend router/service/repository + frontend
  API/hook/store/URL + cross-tab handoff) — a full-stack feature, not quick-task sized. Per
  the user's explicit instruction, no seed was created.

## Follow-up — desktop card layout (2026-06-20)

After the grouping landed, the chips still looked messy because on desktop (`lg+`) the
card was a 3-column grid and all chips were crammed into a ~1/3-width column. Fixed the
layout (Option A, chosen via AskUserQuestion):

- The tablet/desktop body is now a flex column. **Row 1**: board+info, a widened eval
  chart (`flex-[2]`), and the severity badges **stacked vertically** on the right.
  **Row 2**: a full-width tactic + flaw chip block, so chips get the whole card width.
- `severityBadges` + `chipsBlock` extracted as shared pieces — the mobile flaw block and
  the desktop layout compose the same elements (same testids/handlers; only one body
  visible at a time). Mobile/tablet stacking otherwise unchanged.
- Both desktop severity + chip wrappers keep the `flaw-controls` testid so the
  outside-pointer highlight guard still fires.
- Tactic group cap raised **4 → 6** now that width is no longer the constraint.

Gate GREEN again: tsc -b 0, eslint + knip clean, 1072 frontend tests pass.

## Follow-up 2 — Allowed/Missed/Context columns (2026-06-20)

The full-width single stack still looked sparse/unbalanced on games with few tags. Chip
block is now a responsive grid of **three equal-width labeled columns — Allowed | Missed
| Context** — 1/3 each on `md+`, stacking vertically below `md`. Stable lanes fix the
"weird with few tags" look: empty tactic columns hold their lane with a muted "—".

- New lightweight `ChipColumn` (small uppercase section label + flex-wrap chip row).
  Deliberately **not** a shadcn `Card` — its border/shadow/padding would clutter the
  dense card; a CSS grid + light labels is the right primitive (there's no dedicated
  shadcn component for labeled inline groups).
- `TacticMotifGroup` now renders through `ChipColumn` (label on top) and no longer
  self-hides when empty (so the grid keeps 3 stable lanes).
- Order kept Allowed | Missed | Context for app consistency (allowed-before-missed).
- Beta gating unchanged; tactic legend rides the last non-empty tactic column; non-beta /
  no-tactic games fall back to the single full-width flaw-chip row.

Gate GREEN: tsc -b 0, eslint + knip clean, 1072 frontend tests pass.

## Commits
- `ef0dc775` — feat(library): group Games-card tactic chips by orientation with counts + cap
- `9e882271` — refactor(library): full-width chip row + severity beside chart on Games card
- `39f47a0b` — refactor(library): lay out Games-card chips as Allowed/Missed/Context columns
- `66ee0c3b` — fix(library): align Games-card top row to the chip column grid

## Follow-up 3 — gridline alignment (2026-06-20)

The chart's left edge sat just before the MISSED column because board+info was `flex-1`
(under 1/3 once the stacked severity column ate into the row). Row 1 now uses the **same
`md+` 3-column grid** as the chip block: board+info = col 1 (aligns with ALLOWED),
chart+severity = col-span-2 (chart left edge lands on the MISSED boundary). Chip-grid
column gap matched to the row-1 gap (12px) so gridlines coincide. Chose alignment over
card borders (lighter; fixes the root cause). Gate GREEN: tsc 0, eslint + knip, 1072 tests.
