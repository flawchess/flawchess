# Phase 5: Position Bookmarks and W/D/L Comparison Charts - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a bookmark system that lets users save chess positions (with move history and filter settings), then view a dedicated /bookmarks page showing W/D/L horizontal bars per bookmark and a win rate over time line chart. Users can reorder bookmarks by drag-and-drop, edit labels, load bookmarks back into the board editor, and save updates.

</domain>

<decisions>
## Implementation Decisions

### Navigation and routing
- New `/bookmarks` route — separate page, not tabs or a panel on the existing dashboard
- Header gets two nav tabs: **Analysis** (existing /) and **Bookmarks** (/bookmarks)
- Existing dashboard layout unchanged

### Adding bookmarks
- **Bookmark button** (`★ Bookmark`) sits next to the Analyze button in the left column of the Analysis page
- Clicking it saves the current position (moves + filters + hash + FEN + opening label if known)
- Works independently of whether analysis has been run

### Loading a bookmark to edit
- On the /bookmarks page, each bookmark has a **[Load]** button
- Clicking navigates to `/` with the board pre-populated from the bookmark (moves replayed, filters restored, bookmark ID tracked for overwrite)
- After editing, user clicks **Save** (overwrite in place — not save-as-new)

### /bookmarks page layout (desktop)
- Full-width stacked layout: bookmark list on top, win rate line chart below
- Each bookmark row: drag handle (☰), label (editable), [Load] [✕] actions, WDL bar underneath
- [+ Add bookmark] button below the list (alternative to adding from dashboard)
- Mobile: same vertical stack, drag-and-drop supported

### Bookmark storage
- **Backend database** (new `bookmarks` table in PostgreSQL)
- Persists across devices and browser clears
- Stored fields per bookmark: `moves` (SAN array), `color` (played-as filter), `match_side`, `label`, `target_hash` (BIGINT Zobrist), `fen` (position FEN for potential thumbnail use), `sort_order` (integer for drag reorder)
- No cap on number of bookmarks per user

### Bookmark editing rules
- Saving an edited bookmark **overwrites in place** — original is replaced
- Label is editable inline on the /bookmarks page (no separate edit modal needed)

### WDL bars on bookmarks page
- **Reuse existing `WDLBar` component** — same look as analysis results, rendered under each bookmark row
- Stats fetched from backend when /bookmarks page loads

### Chart library
- **Recharts** — React-native, TypeScript-friendly, fits shadcn/ui ecosystem
- shadcn/ui provides Recharts chart wrappers (consistent styling)

### Win rate over time line chart
- **One line per bookmark** showing monthly win rate
- Win rate = wins / (wins + draws + losses) per month
- **Monthly buckets** — each data point is one calendar month
- **Skip months with 0 games** — gap in the line (no interpolation)
- **All-time by default** — full historical range shown
- Data fetched from new backend endpoint: `GET /analysis/time-series` (accepts bookmark params)

### Claude's Discretion
- Exact drag-and-drop library (react-beautiful-dnd or @dnd-kit — pick what fits React 19 best)
- Inline label editing UX (click to edit, blur to save, or pencil icon)
- Loading skeleton / empty state design for bookmarks page
- Color coding of lines in the win rate chart per bookmark (use distinct hues)
- Whether the [+ Add bookmark] on the /bookmarks page opens a modal or navigates to / with a special "add bookmark" mode

</decisions>

<specifics>
## Specific Ideas

- The bookmark button on the dashboard was described as `[Analyze]  [Bookmark ★]` — same row, secondary action
- The /bookmarks page mockup: each bookmark row has `☰ Label  [Edit][✕] [Load]` with the WDL bar underneath
- Time series endpoint should return data usable directly by Recharts: `[{ month: "2025-01", win_rate: 0.45, game_count: 12 }, ...]`
- FEN stored per bookmark to enable future position thumbnail display without replaying moves

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `WDLBar` (`src/components/results/WDLBar.tsx`): Existing horizontal stacked W/D/L bar — reuse directly per bookmark row
- `useChessGame` hook: Manages move history + position; needs a `loadMoves(sans: string[])` method to restore a bookmark
- `FilterState` / `DEFAULT_FILTERS` (`FilterPanel.tsx`): Bookmark stores the `color` and `matchSide` subset of this; load restores those two fields
- `shadcn/ui` components available: card, button, input, dialog, tabs, badge — all usable for bookmark UI
- React Router already configured in `App.tsx` — just add a `/bookmarks` Route

### Established Patterns
- TanStack Query for server state (bookmarks list, WDL stats, time series data)
- shadcn/ui dark theme — all new UI must match existing Nova/Radix dark palette
- Backend: routers/services/repositories layering — new bookmarks feature follows same pattern
- SQLAlchemy 2.x async + Alembic for new `bookmarks` table migration

### Integration Points
- `App.tsx`: Add `/bookmarks` route (protected) and nav tabs in header
- `Dashboard.tsx`: Add Bookmark button alongside Analyze button; pass current `chess` state + filters to bookmark handler
- New `BookmarksPage` component mirrors `DashboardPage` structure
- New API endpoints needed: CRUD for bookmarks + time-series query
- `useChessGame` hook may need `loadMoves(sans)` method if not already present

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-position-bookmarks-and-w-d-l-comparison-charts*
*Context gathered: 2026-03-13*
