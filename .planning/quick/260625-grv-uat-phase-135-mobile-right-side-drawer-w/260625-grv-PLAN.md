---
quick_id: 260625-grv
title: "UAT phase 135 mobile: right-side drawer + close X, smaller board, truncated badges"
status: complete
date: 2026-06-25
---

# Quick Task 260625-grv

Phase 135 (Tactic Line Explorer) mobile UAT polish. Three focused frontend tweaks,
no backend changes.

## Tasks

1. **Right-side drawer with close button** — change the mobile `TacticLineExplorer`
   drawer from `direction="bottom"` to `direction="right"` and add a top-right close
   (X) button, mirroring `MobileFilterDrawer` (full width on phones, 3/4 on small
   tablets, `!rounded-bl-xl`). `data-testid="tactic-explorer-close"`.

2. **Smaller board, move list beside it (mobile)** — replace the stacked mobile layout
   (board full-width above the ladder) with a two-column row: a `MOBILE_BOARD_COLUMN_WIDTH`
   (58%) column holding the board + controls, and the SAN ladder in the flex-1 column to
   its right, so the move list always fits beside the board.

3. **Truncate missed/allowed badges to 16 chars** — in `TacticMotifChip`, cap the
   orientation-prefixed visible label (`"{orientation}: {motif}"`) at
   `MAX_PREFIXED_LABEL_CHARS = 16` (15 chars + ellipsis), e.g.
   `"allowed: hanging-piece"` → `"allowed: hangin…"`. Full text preserved in `aria-label`
   and a native `title` tooltip.

## Files

- `frontend/src/components/library/TacticLineExplorer.tsx`
- `frontend/src/components/library/TacticMotifChip.tsx`
- `CHANGELOG.md` (amend the unreleased Phase 135 bullet: bottom → right-side drawer)

## Verify

- `npm run lint`, `npx tsc -b`, and the affected component tests all pass.
