---
title: Openings subnav layout refactor — match Endgames pattern
date: 2026-04-27
context: Pre-discuss-phase design notes for Phase 71.1 (UI layout refactor)
related_phases: [71.1]
related_files:
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/components/layout/SidebarLayout.tsx
---

# Openings subnav layout refactor — design decisions

Captured during `/gsd-explore` on 2026-04-27. Feeds the eventual `/gsd-discuss-phase`
for Phase 71.1 so we don't relitigate the desktop/mobile split.

## Goal

Bring Openings layout in line with the Endgames pattern now that Phase 71 has
introduced the 4th subtab (Insights). Current Openings layout has the subnav
sitting only above the right column; with 4 tabs that's cramped, and mobile
still uses the legacy chevron-fold sticky board.

## Final spec

### Desktop (`lg` breakpoint, 1024px+)

- Subnav moves to **span full width of (board column + main content)**, placed
  above both. Matches how Endgames sits the subnav at the top of the right side
  of `SidebarLayout`.
- **Left sidebar strip + slide-out panel stays unchanged.** Filter and bookmark
  icons stay in the 48px strip, color toggle stays below. Slide-out panel still
  triggered from the strip.
- Right-of-board settings column unchanged (visible Moves + Games subtabs only;
  hidden on Stats + Insights).
- Board column persists on **all 4 subtabs** on desktop — no full-width
  collapse like Endgames.

### Mobile (< 1024px)

- Sticky subnav at top, full width: 4 subtabs + filter button on the right.
  Filter drawer trigger moves from the current control-row icon to this button.
- Chevron fold + grid-rows collapse animation **removed entirely**.
- Board, board controls (now full-width across the chessboard), moves field —
  all **non-sticky**, scroll with the page on Moves + Games.
- Right-of-board settings column hosts bookmarks, color toggle, info popover —
  visible Moves + Games only.
- On Stats + Insights subtabs: board + controls + moves field hidden entirely.
  Only sticky subnav + tab content shown (matches Endgames mobile shape).

## Rejected options + why

| Option | Why rejected |
|--------|--------------|
| Hide board on desktop Stats + Insights too (full Endgames mirror) | Bigger refactor; user wants board persistent on desktop. |
| Move filter button into desktop subnav too | Left sidebar strip stays as-is on desktop; filter button only moves to subnav on mobile. Asymmetry mirrors Endgames (which has both patterns at different breakpoints). |
| Drop bookmarks drawer trigger entirely on mobile | Loses feature parity. Bookmarks button moves into right-of-board settings column instead. |
| Keep board sticky on mobile | Initially considered, then rejected: sticky board reserves ~half the viewport on Moves + Games. User confirmed non-sticky is cleaner; subtab switches reset scroll-to-top so insights → moves deep-links land with board visible by default. |
| Add as v1.14 seed | Coupling to Phase 71 (4th subtab landing) is tight. Without this refactor, v1.13 ships with a visibly worse Openings page than Endgames. Inserting as Phase 71.1 ahead of Phase 72 also avoids double-touching the same UI surface in Phase 72. |

## Known tradeoffs accepted

- Non-sticky board on mobile means users scroll past the board to reach move
  list / tab content. Acceptable: subtab switching resets scroll, and
  insights → moves deep-links land with board at top.
- Removing chevron fold means the only way to see less board on mobile is to
  switch subtabs. If this feels cramped in practice, "tap board to collapse"
  is a cheap retrofit later — not blocking.

## Implementation hints (not binding)

- Subnav component is currently inside Openings.tsx main-content region; needs
  to lift to a wrapper that spans the right side of `SidebarLayout` (sideContent
  + main).
- Mobile sticky container in Openings.tsx has the chevron + grid-rows trick;
  delete it wholesale, replace with a sticky subnav header + normal scroll flow
  for board + content.
- `data-testid` additions: `subnav-filter-button` (mobile), updated `nav-*`
  testids per CLAUDE.md frontend rules.
- Knip will flag dead exports from chevron/fold logic — clean these up.
- Verify Phase 72 inline-bullet work still composes cleanly on top of the new
  layout before that phase starts.
