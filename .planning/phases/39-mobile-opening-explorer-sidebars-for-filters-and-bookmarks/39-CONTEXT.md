# Phase 39: Mobile Opening Explorer sidebars for filters and bookmarks - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the mobile collapsible sections (More Filters + Position Bookmarks) on the Opening Explorer with two slide-in sidebars triggered from buttons below the sticky chessboard action bar. Mobile-only changes — desktop layout stays as-is. Includes compacting the board action buttons and implementing deferred filter application on sidebar close.

</domain>

<decisions>
## Implementation Decisions

### Board Action Bar Compacting
- **D-01:** Reduce all mobile board action buttons from `h-11 w-11` to smaller size (e.g. `h-9 w-9` or `h-8 w-8`) to free vertical space for sidebar trigger buttons
- **D-02:** Sidebar trigger buttons (filter + bookmark) are placed **below and outside** the BoardControls component, not inside it
- **D-03:** Sidebar trigger buttons are visually distinct from the board navigation buttons — no divider line needed, their visual style alone distinguishes them

### Sidebar Component
- **D-04:** Use the existing Vaul-based Drawer component with `direction="right"` for both sidebars
- **D-05:** Both sidebars slide in from the right side. Only one sidebar can be open at a time
- **D-06:** Sidebars use DrawerHeader + DrawerTitle ("Filters" or "Position Bookmarks") and are full-width overlays with unconstrained vertical scroll

### Sidebar Trigger & Layout
- **D-07:** Remove the existing mobile collapsible sections (More Filters collapsible and Position Bookmarks collapsible) entirely — replaced by sidebars
- **D-08:** The quick filters (Played as, Piece filter) that were previously always visible below the board also move into the filter sidebar
- **D-09:** Trigger buttons show a highlighted/active state (e.g. brand-brown background or filled icon) when their sidebar is open

### Filter Deferred Apply
- **D-10:** Mobile filter sidebar uses deferred apply: clone current filters to local state on open, user toggles affect local state only, commit to real filters on sidebar close (any close method: overlay tap, X button, swipe)
- **D-11:** Desktop sidebar filters keep immediate apply behavior (unchanged) — this phase is mobile-only
- **D-12:** No explicit "Apply" button in the sidebar — closing the sidebar is the apply action

### Bookmark Sidebar Behavior
- **D-13:** When a bookmark is loaded from the sidebar, the sidebar closes and the position is applied to the board
- **D-14:** All existing bookmark functionality (save, suggest, drag reorder, chart toggle, label edit, delete) remains available inside the sidebar

### Claude's Discretion
- Exact reduced button size for board action buttons (h-9 vs h-8)
- Icon choices for filter and bookmark trigger buttons
- Exact highlight style for active trigger buttons
- Whether to add swipe-to-dismiss gesture on the Drawer (Vaul supports this natively)
- Transition duration and easing for sidebar open/close

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### UI Components
- `frontend/src/components/ui/drawer.tsx` — Vaul-based Drawer component with directional support, overlay, and animations
- `frontend/src/components/board/BoardControls.tsx` — Vertical board action button bar (Reset, Back, Forward, Flip + optional infoSlot)
- `frontend/src/components/filters/FilterPanel.tsx` — Filter panel with Recency, Time controls, Platforms, Rated, Opponent filters

### Page Layout
- `frontend/src/pages/Openings.tsx` lines 785-981 — Mobile layout: sticky board container, quick filters, More Filters collapsible, Position Bookmarks collapsible
- `frontend/src/pages/Openings.tsx` lines 260-263 — Current immediate filter apply via `handleFiltersChange`

### Bookmark Components
- `frontend/src/components/position-bookmarks/PositionBookmarkList.tsx` — Drag-and-drop bookmark list
- `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` — Bookmark card with mini board, chart toggle, load/delete

### Theme
- `frontend/src/lib/theme.ts` — Brand colors and button classes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Drawer component** (`components/ui/drawer.tsx`): Vaul-based, supports `direction` prop for left/right/top/bottom, has DrawerOverlay with backdrop-blur, DrawerHeader/Title/Description/Close. Currently used for mobile nav "More" menu as bottom drawer.
- **FilterPanel** (`components/filters/FilterPanel.tsx`): Renders all filter types with `show(field)` conditional. Can be reused directly inside the filter sidebar.
- **PositionBookmarkList/Card**: Complete bookmark UI with drag-and-drop, chart toggle, label editing. Can be placed inside bookmark sidebar as-is.
- **BoardControls**: Accepts `vertical` prop and optional `infoSlot`. Trigger buttons should be rendered separately below this component.

### Established Patterns
- Mobile-first responsive design with `md:hidden` / `md:grid` breakpoints
- Radix UI primitives (Collapsible, Dialog, ToggleGroup) throughout
- Filter state managed via `useState` + `useDebounce(filters, 300)` for API calls
- Charcoal texture background class for container sections

### Integration Points
- Openings.tsx mobile section (lines 785-981): Replace collapsibles with Drawer triggers
- `handleFiltersChange` callback: Mobile sidebar needs to defer calling this until close
- Bookmark load handler: Needs to close sidebar before/after applying position
- BoardControls: Button size reduction is a prop/class change, no structural change needed

</code_context>

<specifics>
## Specific Ideas

- Sidebar trigger buttons should be visually distinct from board nav buttons on their own merit (different style), not via a divider line
- Both sidebars slide from right — consistent with trigger button placement on right side of board
- Filter sidebar title: "Filters" / Bookmark sidebar title: "Position Bookmarks"
- All filters (Played as, Piece filter, and all More Filters content) consolidate into the single filter sidebar — no separate quick filters visible on mobile anymore

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 39-mobile-opening-explorer-sidebars-for-filters-and-bookmarks*
*Context gathered: 2026-03-30*
