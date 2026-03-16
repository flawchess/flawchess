# Roadmap: Chessalytics

## Milestones

- ✅ **v1.0 Initial Platform** - Phases 1-10 (shipped 2026-03-15)
- 🚧 **v1.1 Opening Explorer & UI Restructuring** - Phases 11-14 (in progress)

## Phases

<details>
<summary>✅ v1.0 Initial Platform (Phases 1-10) - SHIPPED 2026-03-15</summary>

### Phase 1: Data Foundation
**Goal**: Establish the database schema and position-hashing module that every subsequent phase depends on.
**Plans**: 2/2 complete

Plans:
- [x] 01-01: Project scaffold, SQLAlchemy models, and Alembic migration
- [x] 01-02: Zobrist hash computation module (TDD)

### Phase 2: Import Pipeline
**Goal**: Let a user fetch their full game history from chess.com and lichess in the background, with incremental re-sync and visible progress.
**Plans**: 4/4 complete

Plans:
- [x] 02-01: ImportJob model, schemas, normalization utilities, and game repository
- [x] 02-02: chess.com and lichess API clients
- [x] 02-03: Import service orchestrator and API router
- [x] 02-04: Gap closure

### Phase 3: Analysis API
**Goal**: Define and implement the full backend analysis contract so any client can query win/draw/loss rates and matching game lists by position, side, and filters.
**Plans**: 2/2 complete

Plans:
- [x] 03-01: Schemas, repository, service, and router for analysis endpoint
- [x] 03-02: Repository and service test suite

### Phase 4: Frontend and Auth
**Goal**: Deliver a complete multi-user web application where each user can log in, import games, specify a position, apply filters, and read personal win rates.
**Plans**: 3/3 complete

Plans:
- [x] 04-01: Backend auth: User model, FastAPI-Users, auth routes
- [x] 04-02: Frontend scaffold: Vite + React + shadcn/ui, auth pages, Zobrist JS port
- [x] 04-03: Dashboard UI: chess board, filters, W/D/L results, import modal

### Phase 5: Position Bookmarks and W/D/L Comparison Charts
**Goal**: Let users save chess positions as bookmarks with live W/D/L bars and a win-rate-over-time line chart.
**Plans**: 5/5 complete

Plans:
- [x] 05-01: Backend bookmark model, migration, schemas, repository, CRUD router
- [x] 05-02: Backend time-series endpoint
- [x] 05-03: Frontend TS types, API client, useBookmarks hooks
- [x] 05-04: Frontend /bookmarks routing, BookmarksPage, sortable BookmarkList
- [x] 05-05: WinRateChart and real WDL bar stats

### Phase 6: Browser Automation Optimization
**Goal**: Audit the frontend and optimize the DOM for AI browser automation.
**Plans**: 2/2 complete

Plans:
- [x] 06-01: Semantic HTML fixes + data-testid + ARIA labels across all components
- [x] 06-02: Click-to-move on chess board + CLAUDE.md Browser Automation Rules

### Phase 7: Game Statistics and Charts
**Goal**: Extend the application with Openings, Rating, and Global Stats pages.
**Plans**: 3/3 complete

Plans:
- [x] 07-01: Backend stats schemas, repository, service, router, and tests
- [x] 07-02: Frontend navigation restructuring and Openings page rename
- [x] 07-03: Rating page and Global Stats page with charts

### Phase 8: Games and Bookmark Tab Rework
**Goal**: Restructure Dashboard left column into three collapsible sections, merge bookmark content, rename to position_bookmarks.
**Plans**: 3/3 complete

Plans:
- [x] 08-01: Backend rename to position_bookmarks
- [x] 08-02: Frontend rename and chart relocation
- [x] 08-03: Dashboard UI restructure: three collapsible sections, nav update

### Phase 9: Game Cards, Username Import, and Pagination
**Goal**: Transform the games list to rich game cards, move usernames to backend, improve pagination.
**Plans**: 8/8 complete

Plans:
- [x] 09-01: Backend model expansion, migration, schema enrichment, profile endpoint
- [x] 09-02: Frontend game cards with colored left border and truncated pagination
- [x] 09-03: Import modal redesign with backend-stored usernames
- [x] 09-04 through 09-08: Gap closure plans

### Phase 10: Auto-Generate Position Bookmarks
**Goal**: Let users auto-generate position bookmarks from their most-played opening positions.
**Plans**: 4/4 complete

Plans:
- [x] 10-01: Backend suggestion endpoint + match_side update endpoint
- [x] 10-02: Frontend suggestions modal with mini boards and bulk save
- [x] 10-03: Bookmark card enhancements: mini board thumbnails and inline piece filter
- [x] 10-04: Gap closure: fix suggestion dedup, match_side heuristic, sort_order

</details>

---

### v1.1 Opening Explorer & UI Restructuring (In Progress)

**Milestone Goal:** Add an interactive move explorer showing next moves with W/D/L stats per position, and restructure the UI with a dedicated Import page and merged Openings tab with sub-tabs.

## Phase Details

### Phase 11: Schema and Import Pipeline
**Goal**: game_positions carries move_san so every position knows the move played from it, unblocking all downstream explorer work.
**Depends on**: Phase 10
**Requirements**: MEXP-01, MEXP-02, MEXP-03
**Success Criteria** (what must be TRUE):
  1. game_positions table has a nullable move_san column; NULL appears on ply-0 rows and the final position row; all other rows have a valid SAN string.
  2. The covering index (user_id, full_hash, move_san) exists in the database and is used by EXPLAIN ANALYZE on a representative aggregation query.
  3. After a full re-import, every game_positions row for a completed game has move_san populated; re-importing the same games produces identical move_san values with no duplicates.
**Plans**: 1 plan

Plans:
- [ ] 11-01-PLAN.md -- Add move_san column, covering index, update zobrist and import pipeline

### Phase 12: Backend Next-Moves Endpoint
**Goal**: A single endpoint aggregates next moves for any position hash with correct W/D/L counts, respecting all existing filters and handling transpositions without double-counting.
**Depends on**: Phase 11
**Requirements**: MEXP-04, MEXP-05, MEXP-10
**Success Criteria** (what must be TRUE):
  1. POST /analysis/next-moves returns a list of next moves with move_san, game_count, wins, draws, losses, win_pct, draw_pct, loss_pct for any valid position hash.
  2. A position reachable by two different move orders in the same game is counted only once per move entry (transposition-safe).
  3. All existing filters (time control, rated/casual, recency, color, opponent type) reduce the move list correctly — verified by comparing filtered vs unfiltered game counts.
  4. Each move entry includes a transposition count (total games reaching the resulting position via any move order) alongside the direct game count.
**Plans**: 2 plans

Plans:
- [ ] 12-01-PLAN.md -- Schemas + repository aggregation queries with tests
- [ ] 12-02-PLAN.md -- Service orchestration, result_fen computation, router endpoint with tests

### Phase 13: Frontend Move Explorer Component
**Goal**: Users can see and navigate next moves for any position, click a move row to advance the board, and the explorer refreshes automatically with the new position's continuations.
**Depends on**: Phase 12
**Requirements**: MEXP-06, MEXP-07, MEXP-11, MEXP-12
**Success Criteria** (what must be TRUE):
  1. The Move Explorer tab shows a table with three columns (Move, Games, Results) where Results is a stacked W/D/L bar; rows are ordered by frequency.
  2. Clicking a move row advances the board to the resulting position and immediately refreshes the explorer table with that position's next moves.
  3. The explorer shows no results (empty state) when no position filter is active or no moves are available for the current position.
  4. A transposition warning icon with hover tooltip appears on move rows where the resulting position has been reached through other move orders.
  5. The chessboard displays transparent arrows for all next moves, with opacity proportional to move frequency (using react-chessboard's native `arrows` option).
**Plans**: 2 plans

Plans:
- [ ] 13-01-PLAN.md -- Types, useNextMoves hook, WDL color export, ChessBoard arrows prop, tooltip install
- [ ] 13-02-PLAN.md -- MoveExplorer component, Dashboard integration, board arrows, human verification

### Phase 14: UI Restructuring
**Goal**: The Openings page becomes a tabbed hub with shared filter state, and import lives on its own dedicated page — giving every feature a clear home with no state loss on tab switch.
**Depends on**: Phase 11, Phase 13
**Requirements**: UIRS-01, UIRS-02, UIRS-03, UIRS-04
**Success Criteria** (what must be TRUE):
  1. The Openings page has three sub-tabs (Move Explorer, Games, Statistics); switching between them preserves all filter selections and board position without any reset.
  2. The Import page at /import contains all import controls, username management, and sync functionality; the import modal no longer exists.
  3. Navigation shows exactly four items: Import, Openings, Rating, Global Stats; all existing routes resolve correctly with no broken links.
  4. After completing an import on the Import page, game counts and user profile data update automatically (TanStack Query cache invalidated correctly).
**Plans**: 3 plans

Plans:
- [ ] 14-01-PLAN.md -- Import page, App routing/nav update, useDebounce and usePositionAnalysisQuery hooks
- [ ] 14-02-PLAN.md -- OpeningsPage tabbed hub with sidebar and 3 sub-tabs (Move Explorer, Games, Statistics)
- [ ] 14-03-PLAN.md -- Human verification of all UIRS requirements

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 2/2 | Complete | 2026-03-11 |
| 2. Import Pipeline | v1.0 | 4/4 | Complete | 2026-03-12 |
| 3. Analysis API | v1.0 | 2/2 | Complete | 2026-03-12 |
| 4. Frontend and Auth | v1.0 | 3/3 | Complete | 2026-03-12 |
| 5. Position Bookmarks | v1.0 | 5/5 | Complete | 2026-03-13 |
| 6. Browser Automation Optimization | v1.0 | 2/2 | Complete | 2026-03-13 |
| 7. Game Statistics and Charts | v1.0 | 3/3 | Complete | 2026-03-14 |
| 8. Games and Bookmark Tab Rework | v1.0 | 3/3 | Complete | 2026-03-14 |
| 9. Game Cards, Username Import, Pagination | v1.0 | 8/8 | Complete | 2026-03-15 |
| 10. Auto-Generate Position Bookmarks | v1.0 | 4/4 | Complete | 2026-03-15 |
| 11. Schema and Import Pipeline | 1/1 | Complete    | 2026-03-16 | - |
| 12. Backend Next-Moves Endpoint | 2/2 | Complete    | 2026-03-16 | - |
| 13. Frontend Move Explorer Component | 2/2 | Complete    | 2026-03-16 | - |
| 14. UI Restructuring | 1/3 | In Progress|  | - |

### Phase 15: Consolidation - remove unnecessary code, rename endpoints/modules, update CLAUDE.md and README.md

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 14
**Plans:** 1/3 plans executed

Plans:
- [ ] TBD (run /gsd:plan-phase 15 to break down)

---
*Created: 2026-03-11*
*v1.0 phases 1-10 shipped: 2026-03-15*
*v1.1 phases 11-14 added: 2026-03-16*
