# Phase 13: Frontend Move Explorer Component - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can see and navigate next moves for any position, click a move row to advance the board, and the explorer refreshes automatically with the new position's continuations. Built as a standalone component on the Dashboard (right column, above game list) ready for Phase 14 to move into the first Openings sub-tab.

</domain>

<decisions>
## Implementation Decisions

### Explorer table layout
- Placement: right column of Dashboard, above W/D/L bar and game cards
- 3-column table: Move (SAN), Games (count), Results (mini stacked W/D/L bar)
- Rows ordered by game_count descending (most-played first)
- Mini stacked bar reuses existing WDL color scheme (green/gray/red), hover tooltip shows W/D/L percentages
- Always visible — shows next moves even from the starting position (no positionFilterActive gating for the explorer)
- Built as a self-contained component so Phase 14 can slot it into the first sub-tab with minimal rewiring

### Board integration & navigation
- Clicking a move row plays the move on the board via `useChessGame.makeMove`, extending the move history
- Back/Forward navigation works normally — user can navigate back and see previous explorer state
- Auto-fetch: explorer refreshes automatically on position change (move played, bookmark loaded, navigation) AND on filter changes — no Filter button click needed
- W/D/L bar and game list still require the Filter button (heavier query)
- Explorer uses `full_hash` only (ignoring piece filter / match_side), consistent with Phase 12 backend decision
- Explorer respects all other active filters (time control, platform, rated, opponent, recency)

### Arrow overlays on board
- Blue arrows with opacity proportional to move frequency
- Show arrows for ALL moves in the explorer (no cap)
- Minimum 15% opacity so even rare moves remain visible
- Most-played move gets full opacity, proportional scaling down from there
- Uses react-chessboard's native `arrows` option

### Transposition indicators
- Small icon (⇄) appears after the Games count number when `transposition_count > game_count`
- Hover tooltip shows: "Position reached in X total games (Y via other move orders)"
- `transposition_count` comes from backend; frontend derives "via other move orders" as `transposition_count - game_count`

### Claude's Discretion
- Exact component file structure and naming
- Loading/skeleton state design while explorer fetches
- Empty state message when no moves available for current position
- Debounce strategy for auto-fetch on rapid filter changes
- Exact opacity scaling formula for arrows
- Mobile responsive layout adjustments for the explorer table

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend API contract
- `app/schemas/analysis.py` — `NextMovesRequest`, `NextMoveEntry`, `NextMovesResponse`, `WDLStats` schemas
- `app/routers/analysis.py` — `POST /analysis/next-moves` endpoint registration

### Frontend components to extend/reuse
- `frontend/src/components/board/ChessBoard.tsx` — Board component, needs `arrows` prop support
- `frontend/src/components/results/WDLBar.tsx` — WDL color constants and stacked bar pattern to reuse for mini bars
- `frontend/src/hooks/useChessGame.ts` — Board state management, `makeMove`, `goToMove`, `replayTo`, `hashes`
- `frontend/src/pages/Dashboard.tsx` — Integration point for explorer in right column
- `frontend/src/types/api.ts` — TypeScript type mirrors, needs `NextMoveEntry`/`NextMovesResponse` types

### Filter system
- `frontend/src/components/filters/FilterPanel.tsx` — Filter state shape and controls
- `frontend/src/hooks/useAnalysis.ts` — Existing analysis mutation pattern (reference for new useNextMoves hook)

### Requirements
- `.planning/REQUIREMENTS.md` — MEXP-06 (explorer table), MEXP-07 (click-to-navigate), MEXP-11 (transposition icon), MEXP-12 (board arrows)

### Prior phase context
- `.planning/phases/12-backend-next-moves-endpoint/12-CONTEXT.md` — Backend decisions: full_hash only, response contract, transposition handling, sort_by support

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `WDLBar` component: WDL color constants (`oklch(0.55 0.18 145)` green, `oklch(0.65 0.01 260)` gray, `oklch(0.55 0.2 25)` red) and stacked bar pattern — reuse for mini inline bars
- `useChessGame` hook: complete board state management with `makeMove`, `goToMove`, `goBack`, `goForward`, `hashes` (includes `fullHash`)
- `ChessBoard` component: uses react-chessboard with `squareStyles` — needs `arrows` option added
- `hashToString` utility: converts BigInt hash to string for API calls
- `apiClient`: axios instance with auth interceptors

### Established Patterns
- TanStack Query for server state (`useQuery` for reads, `useMutation` for writes)
- Filter state as React `useState` in parent, passed down as props
- `data-testid` on all interactive elements (kebab-case, component-prefixed)
- shadcn/ui components (Button, ToggleGroup, Collapsible, etc.)

### Integration Points
- Dashboard right column: explorer component inserted above the existing `positionFilterActive` conditional block
- `useChessGame.hashes.fullHash` provides the hash for next-moves API calls
- Filter state from Dashboard's `filters` useState drives explorer's filter params
- New `useNextMoves` hook (TanStack Query `useQuery`) auto-fetches on hash/filter changes

</code_context>

<specifics>
## Specific Ideas

- Inspired by openingtree.com and lichess explorer — frequency-first move ordering is the standard
- Explorer should feel instant — auto-fetch on every position/filter change, no manual trigger
- The component is designed for Phase 14 portability: self-contained, receives board state and filters as props

</specifics>

<deferred>
## Deferred Ideas

- MEXP-08: Move sorting options (by win rate, alphabetical) — future requirement, not Phase 13 scope
- MEXP-09: Show resulting position FEN/thumbnail on move hover — future requirement (result_fen is already in the API response)
- Sub-tab structure (Move Explorer / Games / Statistics) — Phase 14 UI Restructuring

</deferred>

---

*Phase: 13-frontend-move-explorer-component*
*Context gathered: 2026-03-16*
