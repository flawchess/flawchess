---
quick_id: 260625-grv
status: complete
date: 2026-06-25
---

# Summary — 260625-grv

Three mobile UAT tweaks for the Phase 135 Tactic Line Explorer. Done inline (small,
mechanical frontend work). No backend changes.

## What changed

1. **Right-side drawer + close button** (`TacticLineExplorer.tsx`)
   - Mobile drawer now opens from the right (`direction="right"`), matching the filter
     panel drawers: `!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[95vh]`.
   - Added a top-right close (X) button — ghost icon `Button` inside `DrawerClose`,
     wrapped in a `Tooltip`, `aria-label="Close tactic explorer"`,
     `data-testid="tactic-explorer-close"`.

2. **Smaller board, move list beside it** (`TacticLineExplorer.tsx`)
   - New `MOBILE_BOARD_COLUMN_WIDTH = '58%'` constant.
   - Mobile layout changed from stacked (board above ladder) to a two-column row:
     board + controls in the 58% column, SAN ladder in the flex-1 column to its right
     (`min-w-0`, `max-h-[70vh]` scroll). The header row (motif chips + eval badge) stays
     full-width above the row.

3. **Truncated badges** (`TacticMotifChip.tsx`)
   - New `MAX_PREFIXED_LABEL_CHARS = 16`. The orientation-prefixed visible label is
     truncated to 15 chars + `…` when longer, e.g. `"allowed: hanging-piece"` →
     `"allowed: hangin…"`. Full label kept in `aria-label` and a native `title` tooltip.
   - Applies to every prefixed (`{orientation}: {motif}`) badge form (explorer switch +
     Flaws-tab cards). The `hidePrefix` grouped chips (Games tab) are unaffected.

## Verification

- `npm run lint` — clean (only pre-existing warnings under `coverage/`).
- `npx tsc -b` — passes.
- Component tests: `TacticMotifChip`, `TacticLineExplorer`, `FlawCard` — 78 passed.

## Notes

- The 16-char cap lives in the chip component, so it applies wherever the
  `{orientation}: {motif}` badge form renders (not just the explorer). This is the
  natural reading of the cap and keeps the cards tidy; full text remains available via
  tooltip/aria. Flag if explorer-only scoping is preferred.
- No browser UAT performed (needs a logged-in account with tagged tactic data); the
  user re-verifies mobile manually.
