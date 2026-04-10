# Phase 49: Openings Desktop Sidebar - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current always-visible desktop sidebar (board + filters/bookmarks tabs in a fixed left column) with a collapsible left-edge sidebar containing only Filters and Bookmarks panels. The board, board controls, move list, and opening name move to the main content area. This preserves horizontal space on smaller desktop screens while keeping filter/bookmark access one click away.

Scope: Desktop layout only (md: breakpoint and above). Mobile layout is unchanged (Phase 50).

</domain>

<decisions>
## Implementation Decisions

### Desktop Layout Restructuring
- **D-01:** The current 2-column desktop layout (`[350px sidebar] | [1fr tabs]`) is replaced. The board and its associated controls (board controls, opening name, move list) move from the sidebar into the main content area.
- **D-02:** A collapsed sidebar strip lives on the left edge of the Openings page, showing filter and bookmark icons. This strip is always visible on desktop.
- **D-03:** Clicking a filter or bookmark icon in the collapsed strip opens the respective panel directly — no intermediate state.

### Sidebar Panel Behavior
- **D-04:** Only one panel (Filters or Bookmarks) is visible at a time. Clicking the other icon switches panels without requiring a double-click (close then open).
- **D-05:** Filter changes apply live while the sidebar panel is open — no deferred apply button on desktop. This matches the current desktop behavior where filters update immediately.

### Overlay vs Push
- **D-06:** On smaller desktop screens (where a 3-column push layout would cause overflow), the open sidebar overlays the chessboard rather than pushing it.
- **D-07:** On larger desktop screens where space permits, the sidebar pushes the board content right without overflow.

### Claude's Discretion
- Collapsed strip width, icon sizing, and tooltip labels
- Animation style for sidebar open/close (slide vs instant)
- Exact breakpoint for overlay vs push transition
- Whether clicking outside the open panel closes it
- How to reorganize the main content area (board + tabs layout)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — DESK-01 through DESK-05 requirement definitions for this phase

### Roadmap
- `.planning/ROADMAP.md` — Phase 49 success criteria (5 criteria) and phase details

### Existing Code
- `frontend/src/pages/Openings.tsx` — Main page component with current desktop 2-column layout (line 903), sidebar variable (line 427), mobile drawers (line 1062+)
- `frontend/src/components/filters/FilterPanel.tsx` — Reusable filter panel component with FilterState interface
- `frontend/src/components/position-bookmarks/PositionBookmarkList.tsx` — Bookmark list component
- `frontend/src/hooks/useFilterStore.ts` — Shared filter state management

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **FilterPanel** (`frontend/src/components/filters/FilterPanel.tsx`): Self-contained filter component with `FilterState` interface and `onChange` callback. Already used in both desktop sidebar tabs and mobile drawers.
- **PositionBookmarkList** (`frontend/src/components/position-bookmarks/PositionBookmarkList.tsx`): Bookmark list with drag-reorder, chart-enable toggles. Used in desktop sidebar and mobile drawer.
- **Drawer component** (`@/components/ui/drawer`): Currently used for mobile filter/bookmark sidebars. Could inform the desktop sliding panel pattern.
- **Tabs component** (`@/components/ui/tabs`): Used for current desktop sidebar filter/bookmark tabs and Moves/Games/Stats tabs.
- **Lucide icons**: `SlidersHorizontal` (filters) and `BookMarked` (bookmarks) already imported in Openings.tsx.

### Established Patterns
- **Desktop/mobile split**: Desktop layout uses `hidden md:grid` (line 903), mobile uses `md:hidden` (line 935). Phase 49 only modifies the desktop branch.
- **Filter state**: Shared via `useFilterStore` hook, debounced with `useDebounce(filters, 300)`. Live updates already work on desktop.
- **Sidebar tab state**: `sidebarTab` state variable (line 95) already tracks which panel is active (filters vs bookmarks). This can be extended to track open/closed state.
- **Mobile deferred apply**: Mobile drawers use `localFilters` state and apply on close. Desktop applies immediately. This distinction must be preserved.

### Integration Points
- **Openings.tsx desktop layout** (line 903): The `hidden md:grid md:grid-cols-[350px_1fr]` div is the primary change target. The sidebar variable (line 427) needs to be decomposed — board/controls/move-list extracted to main content, filter/bookmark tabs moved to the new collapsible sidebar.
- **Played as + Piece filter**: Currently rendered in both the desktop sidebar tabs (line 518) and mobile drawer (line 1075). The desktop copy moves into the new sidebar panel.
- **Board collapse state**: `boardCollapsed` state (line 108) is mobile-only. Desktop board should always be visible.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for collapsible sidebar implementation. The key constraint is matching the existing visual style (charcoal containers, brand colors, glass overlays from `frontend/src/lib/theme.ts`).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 49-openings-desktop-sidebar*
*Context gathered: 2026-04-09*
