# Phase 8: Rework Games and Bookmark Tabs - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the Games (Dashboard) page left column into three collapsible sections (Position filter, Position bookmarks, More filters), merge bookmark content from the Bookmarks tab into the Games page, remove the Bookmarks navigation tab, and rename `bookmarks` → `position_bookmarks` across the entire stack (DB, backend, frontend, API paths).

</domain>

<decisions>
## Implementation Decisions

### Left column layout — three collapsible sections
- **Position filter** (open by default): Contains chessboard, opening name display, move list, board controls (back/forward/reset/flip), Played as / Match side toggle groups, and "Bookmark this position" button
- **Position bookmarks** (collapsed by default): Contains the BookmarkList with drag-and-drop reordering. Bookmark cards show only: drag handle, editable label, Load button, Delete button. No WDL bars, no WDL charts, no WinRateChart
- **More filters** (collapsed by default): Time control, Platform, Rated, Opponent, Recency — unchanged from current implementation
- **Filter + Import buttons**: Always visible below all three collapsible sections (not inside any collapsible)
- All three collapsibles are siblings at the same nesting level — no nested collapsibles

### Bookmarks tab removal
- Remove the `/bookmarks` route and `BookmarksPage` component
- Remove "Bookmarks" from the `NAV_ITEMS` array (5 tabs → 4 tabs: Games, Openings, Rating, Global Stats)
- All bookmark functionality now lives inside the "Position bookmarks" collapsible section on the Games page

### WDL removal from bookmarks
- Remove WDL bars from individual bookmark cards
- Remove WinRateChart (time-series line chart) entirely — it was on the old Bookmarks/Openings page
- No stats displayed on bookmark cards at all — they are lightweight position references

### Bookmark button
- Moved from the action buttons row into the "Position filter" collapsible section
- Renamed from "Bookmark" to "Bookmark this position"
- Still opens the existing label dialog before saving

### Rename scope: bookmarks → position_bookmarks
- **DB table**: `bookmarks` → `position_bookmarks` (Alembic migration with `op.rename_table`)
- **Backend model**: `Bookmark` → `PositionBookmark`, `__tablename__ = "position_bookmarks"`
- **Backend files**: `bookmark_repository.py` → `position_bookmark_repository.py`, `bookmarks.py` (schemas) → `position_bookmarks.py`, `bookmarks.py` (router) → `position_bookmarks.py`
- **Backend schemas**: `BookmarkCreate` → `PositionBookmarkCreate`, `BookmarkUpdate` → `PositionBookmarkUpdate`, `BookmarkResponse` → `PositionBookmarkResponse`, etc.
- **API endpoint paths**: `/bookmarks` → `/position-bookmarks` (hyphenated in URL)
- **Frontend types**: `bookmarks.ts` → `position_bookmarks.ts`, `BookmarkResponse` → `PositionBookmarkResponse`
- **Frontend hooks**: `useBookmarks.ts` → `usePositionBookmarks.ts`, hook names updated accordingly
- **Frontend components**: `components/bookmarks/` → `components/position-bookmarks/`, component names prefixed with `PositionBookmark`
- **API client paths**: all `/bookmarks` calls updated to `/position-bookmarks`

### Claude's Discretion
- Exact styling of collapsible section headers (chevron icons, font size, spacing)
- How to handle the "Load" bookmark action now that bookmarks are on the same page as the board (no navigation needed — can just replay moves in-place)
- Empty state text for the Position bookmarks section when no bookmarks exist
- Whether the Openings page needs updates after WinRateChart removal (it may share the chart)

</decisions>

<specifics>
## Specific Ideas

- The three collapsible sections should use the same visual pattern — consistent header style with expand/collapse chevron
- The "Bookmark this position" button should be visually distinct within the Position filter section (not confused with board controls)
- BookmarkCard simplification: drag handle (☰), editable label, [Load] [✕] — that's it

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Collapsible` / `CollapsibleTrigger` / `CollapsibleContent` (shadcn/ui): Already used in FilterPanel for "More filters" — reuse for all three sections
- `BookmarkList` + `BookmarkCard` (`components/bookmarks/`): Existing drag-and-drop with @dnd-kit — move into Position bookmarks section, strip WDL
- `useBookmarks` / `useCreateBookmark` / `useReorderBookmarks` hooks: All bookmark CRUD hooks exist — rename and reuse
- `FilterPanel` component: Currently renders "More filters" collapsible — extract as standalone collapsible or restructure

### Established Patterns
- Collapsible sections use `Button variant="ghost"` as trigger with ChevronUp/ChevronDown icons
- TanStack Query for all server state (bookmarks, analysis)
- shadcn/ui dark theme (Nova/Radix) — all new UI must match
- Backend: routers/services/repositories layering

### Integration Points
- `Dashboard.tsx`: Major restructuring — left column becomes three collapsible sections + always-visible buttons
- `App.tsx`: Remove `/bookmarks` route, remove "Bookmarks" from NAV_ITEMS
- `FilterPanel.tsx`: "More filters" becomes its own top-level collapsible (currently embedded in FilterPanel)
- `app/main.py`: Update router include for renamed position_bookmarks router
- `app/routers/analysis.py`: References bookmark schemas for time-series — update imports
- Alembic: New migration to rename the `bookmarks` table

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-rework-games-and-bookmark-tabs-position-filter-section-position-bookmarks-section-rename-bookmarks-to-position-bookmarks*
*Context gathered: 2026-03-14*
