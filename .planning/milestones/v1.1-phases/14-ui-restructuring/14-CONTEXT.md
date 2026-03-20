# Phase 14: UI Restructuring - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

The Openings page becomes a tabbed hub with three sub-tabs (Move Explorer, Games, Statistics) sharing a unified filter sidebar and board state. Import moves to its own dedicated page. Navigation updates to: Import | Openings | Rating | Global Stats. The Dashboard page is removed entirely.

</domain>

<decisions>
## Implementation Decisions

### Openings page sidebar
- Board, played-as toggle, piece filter, and bookmark button are always visible — NOT inside a collapsible. Remove the "Position filter" collapsible wrapper, show content directly.
- Position bookmarks section stays as a collapsible
- More filters section stays as a collapsible
- Unified filter state: merge Dashboard's `FilterState` and Openings' `StatsFilters` into one shared state lifted to OpeningsPage parent

### Sub-tab structure
- Three sub-tabs: Move Explorer, Games, Statistics
- Tab bar positioned at the top of the right column (content area)
- URL-based routing: `/openings/explorer`, `/openings/games`, `/openings/statistics`
- `/openings` defaults to `/openings/explorer`
- Tabs are bookmarkable and work with browser back/forward

### Auto-fetch behavior
- ALL sub-tabs auto-fetch when position or filters change — no Filter/Analyze button anywhere
- Move Explorer: auto-fetches next moves on position/filter change (existing behavior)
- Games: auto-fetches game list on position/filter change (replaces manual Filter button)
- Statistics: auto-fetches bookmark time series on bookmark/filter change (replaces Analyze button)
- Remove the Filter button and Analyze button entirely

### Games tab
- Shows all games by default when no position filter is active (no positionFilterActive gating)
- W/D/L bar appears above game cards (same as current Dashboard behavior)
- Pagination resets to page 1 on tab switch (offset not preserved across tabs)
- GameCardList with existing game cards, pagination, matched count

### Statistics tab
- WDL bar chart and Win Rate Over Time chart (current Openings page content)
- Auto-fetches when bookmarks or filters change
- No separate Analyze button

### Import page
- Dedicated page at `/import` replacing the import modal
- Same controls as ImportModal but laid out as a full page (expanded, not in a dialog)
- Username management, platform select, import trigger — all inline
- Delete All Games button moves here (from Dashboard header)
- Import progress shown inline on the page (not just toasts)
- Toast notification fires globally when import completes and user is on another page
- Cache invalidation on import complete: `['games']`, `['gameCount']`, `['userProfile']`

### Navigation
- Nav order: Import | Openings | Rating | Global Stats
- Routes: `/import`, `/openings/*`, `/rating`, `/global-stats`
- `/` redirects to `/openings`
- DashboardPage.tsx deleted entirely (no redirect component)
- All existing routes resolve correctly with no broken links

### Claude's Discretion
- Exact tab component implementation (shadcn Tabs, custom, or react-router-based)
- Debounce strategy for auto-fetch on rapid filter/position changes
- Mobile responsive layout for the tabbed Openings page
- Import page layout details (spacing, grouping of controls)
- Loading/skeleton states for each sub-tab during auto-fetch
- How to handle the transition from ImportModal to ImportPage (component refactoring approach)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — UIRS-01 (Openings sub-tabs), UIRS-02 (filter persistence), UIRS-03 (Import page), UIRS-04 (nav update)

### Current implementation to restructure
- `frontend/src/pages/Dashboard.tsx` — Main page being decomposed; contains board, filters, MoveExplorer, games, import modal, delete games
- `frontend/src/pages/Openings.tsx` — Current Statistics page; becomes the Statistics sub-tab content
- `frontend/src/App.tsx` — Router and NavHeader; needs route/nav updates

### Components to relocate/reuse
- `frontend/src/components/import/ImportModal.tsx` — Import controls to extract into ImportPage
- `frontend/src/components/import/ImportProgress.tsx` — Progress tracking; inline on Import page + global toast
- `frontend/src/components/move-explorer/MoveExplorer.tsx` — Self-contained, receives props; slots into Move Explorer sub-tab
- `frontend/src/components/filters/FilterPanel.tsx` — Shared filter component for sidebar
- `frontend/src/components/results/WDLBar.tsx` — Used in Games sub-tab
- `frontend/src/components/results/GameCardList.tsx` — Used in Games sub-tab
- `frontend/src/components/charts/WDLBarChart.tsx` — Used in Statistics sub-tab
- `frontend/src/components/charts/WinRateChart.tsx` — Used in Statistics sub-tab

### Board and hooks
- `frontend/src/components/board/ChessBoard.tsx` — Board component with arrows
- `frontend/src/hooks/useChessGame.ts` — Board state, shared across all sub-tabs
- `frontend/src/hooks/useNextMoves.ts` — Move Explorer data hook
- `frontend/src/hooks/useAnalysis.ts` — Games/analysis data hook
- `frontend/src/hooks/usePositionBookmarks.ts` — Bookmarks + time series hooks

### Prior phase context
- `.planning/phases/13-frontend-move-explorer-component/13-CONTEXT.md` — MoveExplorer designed for portability, full_hash only, auto-fetch behavior

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MoveExplorer` component: fully self-contained, receives `moves`, `isLoading`, `isError`, `position`, `onMoveClick`, `onMoveHover` as props — direct slot into Move Explorer tab
- `FilterPanel` component: already a standalone filter form, used in Dashboard sidebar
- `ImportModal` component: contains all import UI logic — needs extraction from Dialog wrapper into page layout
- `ImportProgress` component: polling-based progress tracking — needs adaptation for inline display
- `WDLBar`, `GameCardList`, `WDLBarChart`, `WinRateChart`: all reusable as-is in their respective sub-tabs
- `ChessBoard`, `MoveList`, `BoardControls`, `PositionBookmarkList`: sidebar components, reusable as-is

### Established Patterns
- TanStack Query for all server state (useQuery for reads, useMutation for writes)
- Filter state as React useState in parent, passed down as props
- `data-testid` on all interactive elements (CLAUDE.md requirement)
- shadcn/ui components (Button, ToggleGroup, Collapsible, Select, Dialog, etc.)
- Board arrows computed via useMemo from nextMoves data in parent

### Integration Points
- Dashboard.tsx (~650 lines) is the decomposition source — its logic splits into OpeningsPage (sidebar + sub-tabs), ImportPage, and shared hooks
- Two separate filter type systems exist: Dashboard's `FilterState` and Openings' `StatsFilters` — must be unified
- `useChessGame` hook provides board state shared by sidebar and all sub-tabs
- `boardArrows` useMemo computation stays in OpeningsPage parent (needs nextMoves data + chess position)
- Global import progress toasts need to work from any page (lift ImportProgress to App level or use global state)

</code_context>

<specifics>
## Specific Ideas

- Import progress should be inline on the Import page (not just toasts) for a more spacious, full-page experience
- Toast notification fires globally when import completes and user is on another page — user knows without checking
- Delete All Games lives on the Import page (data management grouped together)
- The current `positionFilterActive` gating concept goes away for Games tab — always show games

</specifics>

<deferred>
## Deferred Ideas

- GamesTab pagination offset survival across tab switches — decided to reset to page 1 (simpler)
- MEXP-08: Move sorting options (by win rate, alphabetical) — future requirement
- MEXP-09: Show resulting position FEN/thumbnail on move hover — future requirement
- Phase 15: Consolidation — code cleanup, endpoint renaming, CLAUDE.md/README updates

</deferred>

---

*Phase: 14-ui-restructuring*
*Context gathered: 2026-03-16*
