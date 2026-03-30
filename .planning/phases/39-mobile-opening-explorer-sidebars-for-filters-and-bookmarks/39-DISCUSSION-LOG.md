# Phase 39: Mobile Opening Explorer sidebars for filters and bookmarks - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 39-mobile-opening-explorer-sidebars-for-filters-and-bookmarks
**Areas discussed:** Board action bar compacting, Sidebar component, Sidebar trigger & layout, Filter deferred apply

---

## Board Action Bar Compacting

| Option | Description | Selected |
|--------|-------------|----------|
| Smaller buttons | Reduce all action buttons from h-11 to h-9 or h-8. Simple, keeps all visible. Saves 75-150px total. | ✓ |
| Merge reset+info into one | Combine less-used buttons. Reduces count but adds UX complexity. | |
| Two-column grid | Arrange in 2-column grid. Cuts height in half but doubles width, shrinking board. | |

**User's choice:** Smaller buttons
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Separator line | Thin horizontal divider between sidebar triggers (top) and board nav buttons (bottom). | |
| Same style, no separator | All buttons identical, simple and uniform. | |
| Brand color accent | Sidebar triggers use subtle brand-brown tint or border. | |

**User's choice:** Other — "The sidebar buttons should be below and outside of the board nav buttons. They should be visually distinct and don't need a divider line"
**Notes:** Trigger buttons placed below BoardControls, not inside it. Visually distinct on their own.

---

## Sidebar Component

| Option | Description | Selected |
|--------|-------------|----------|
| Vaul Drawer | Reuse existing Drawer with direction='right'. Free animations, overlay, scroll locking, accessibility. | ✓ |
| Custom slide-in panel | Custom div with CSS transitions. More control but need to handle overlay, focus trap, scroll lock manually. | |
| Radix Dialog (sheet style) | Radix Dialog styled as full-width sheet. More control than Drawer but no swipe-to-dismiss. | |

**User's choice:** Vaul Drawer
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Both from right | Both sidebars slide from right. Consistent with trigger button placement. | ✓ |
| Filters left, bookmarks right | Each from opposite sides. Spatial distinction but inconsistent with trigger placement. | |

**User's choice:** Both from right
**Notes:** None

---

## Sidebar Trigger & Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Remove collapsibles | Replace collapsible sections entirely with sidebars. Quick filters also move into sidebar. | ✓ |
| Keep collapsibles too | Keep both access methods. More discovery but duplicated UI. | |
| Keep quick filters, remove rest | Keep Played as + Piece filter visible below board. Only More Filters and Bookmarks in sidebars. | |

**User's choice:** Remove collapsibles
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Highlighted when open | Trigger button gets brand-brown background or filled icon when sidebar is open. | ✓ |
| No active state | Button looks same open or closed. | |
| Badge/dot indicator | Small dot on filter button when non-default filters active. | |

**User's choice:** Highlighted when open
**Notes:** None

---

## Filter Deferred Apply

| Option | Description | Selected |
|--------|-------------|----------|
| Apply on close | Clone filters to local state on open, commit on close. No Apply button needed. | ✓ |
| Explicit Apply button | "Apply Filters" button at bottom. Closing without Apply discards changes. | |
| Apply on close + reset button | Apply on close plus a Reset button to clear filters to defaults. | |

**User's choice:** Apply on close
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Desktop stays immediate | Only mobile uses deferred apply. Desktop keeps current instant behavior. | ✓ |
| Both deferred | Change desktop to also defer apply. Consistent but changes existing UX. | |

**User's choice:** Desktop stays immediate
**Notes:** Phase is mobile-only per description.

---

## Claude's Discretion

- Exact reduced button size (h-9 vs h-8)
- Icon choices for filter and bookmark trigger buttons
- Exact highlight style for active trigger buttons
- Swipe-to-dismiss gesture support
- Transition duration and easing

## Deferred Ideas

None
