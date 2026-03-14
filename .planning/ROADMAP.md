# Roadmap: Chessalytics

## Overview
- Total phases: 9
- Total requirements: 21 (v1) + 7 provisional (Phase 5) + 5 provisional (Phase 6) + 6 provisional (Phase 7) + 5 provisional (Phase 8) + 5 provisional (Phase 9)
- Granularity: Coarse

---

## Phase 1: Data Foundation

**Goal:** Establish the database schema and position-hashing module that every subsequent phase depends on — getting this wrong would require rewriting the data layer.

**Requirements:**
- INFRA-01: Database schema supports efficient position-based queries using indexed Zobrist hash columns
- INFRA-03: Duplicate games are prevented via unique constraint on (platform, platform_game_id)
- IMP-05: All available game metadata is stored (PGN, time control, rated flag, result, opponent, color, platform URL, timestamps)
- IMP-06: Position hashes (white, black, full Zobrist) are precomputed and stored for every half-move at import time

**Plans:** 2/2 plans complete

Plans:
- [ ] 01-01-PLAN.md — Project scaffold, SQLAlchemy models, and Alembic migration
- [ ] 01-02-PLAN.md — Zobrist hash computation module (TDD)

**Success Criteria:**
1. A developer can run migrations and observe `games`, `game_positions`, and related tables with the correct columns and indexes in the DB.
2. Given a PGN string, the position hash module returns three integer hashes per half-move, and unit tests confirm identical board states produce identical hashes.
3. Inserting the same game twice leaves exactly one row (duplicate constraint enforced at the DB level).

**Dependencies:** None

---

## Phase 2: Import Pipeline

**Goal:** Let a user fetch their full game history from chess.com and lichess in the background, with incremental re-sync and visible progress.

**Requirements:**
- IMP-01: User can import games from chess.com by entering their username
- IMP-02: User can import games from lichess by entering their username
- IMP-03: User can re-sync to fetch only new games since last import (incremental)
- IMP-04: User sees import progress and status while games are being fetched
- INFRA-02: Game import runs as a background task (does not block the API server)

**Plans:** 4/4 plans complete

Plans:
- [x] 02-01-PLAN.md — ImportJob model, schemas, normalization utilities, and game repository
- [x] 02-02-PLAN.md — chess.com and lichess API clients
- [ ] 02-03-PLAN.md — Import service orchestrator and API router

**Success Criteria:**
1. A user submits a chess.com or lichess username and immediately receives a job ID; the import runs in the background and completes without blocking other requests.
2. Polling the import status endpoint shows live progress (games fetched so far) and a terminal state (completed or failed with an error message).
3. Running re-sync after new games have been played fetches only the new games; total game count increases by the exact number of new games, with no duplicates.
4. Submitting an invalid username returns a clear error message without crashing the import pipeline.

**Dependencies:** Phase 1

---

## Phase 3: Analysis API

**Goal:** Define and implement the full backend analysis contract so that any client (including the not-yet-built frontend) can query win/draw/loss rates and matching game lists by position, side, and filters.

**Requirements:**
- ANL-02: User can filter position matches by white pieces only, black pieces only, or both sides
- ANL-03: User sees win/draw/loss counts and percentages for all matching games
- FLT-01: User can filter analysis results by time control (bullet, blitz, rapid, classical)
- FLT-02: User can filter analysis results by rated vs casual games
- FLT-03: User can filter analysis results by game recency (week, month, 3 months, 6 months, 1 year, all time)
- FLT-04: User can filter analysis results by color played (white or black)
- RES-01: User sees a list of matching games showing opponent name, result, date, and time control
- RES-02: Each matching game has a clickable link to the game on chess.com or lichess
- RES-03: User always sees the total games denominator ("X of Y games matched")

**Plans:** 2/2 plans complete

Plans:
- [ ] 03-01-PLAN.md — Schemas, repository, service, and router for analysis endpoint
- [ ] 03-02-PLAN.md — Repository and service test suite

**Success Criteria:**
1. Posting a target position hash to the analysis endpoint with `match_side=white` returns only games where the user's white pieces matched, with correct W/D/L counts.
2. Applying time control, rated, recency, and color filters in combination changes the match count predictably — verifiable against the raw game records in the DB.
3. Every result record includes opponent name, result, date, time control, and a working external URL to the game.
4. The response always includes both the match count and the total eligible game count, even when zero games match.

**Dependencies:** Phase 1, Phase 2

---

## Phase 4: Frontend and Auth

**Goal:** Deliver a complete, multi-user web application where each user can log in, import their games, specify a position on an interactive board, apply filters, and read their personal win rates.

**Requirements:**
- ANL-01: User can specify a target position by playing moves on an interactive chess board
- AUTH-01: User can create an account and log in
- AUTH-02: Each user's games and analyses are isolated (row-level data scoping)

**Plans:** 3/3 plans complete

Plans:
- [x] 04-01-PLAN.md — Backend auth: User model, FastAPI-Users, auth routes, CORS, replace user_id=1, tests
- [x] 04-02-PLAN.md — Frontend scaffold: Vite + React + shadcn/ui, auth pages, Zobrist JS port
- [ ] 04-03-PLAN.md — Dashboard UI: chess board, filters, W/D/L results, import modal

**Success Criteria:**
1. A new user can register, log in, enter a chess.com or lichess username, and see their import progress — all from the browser with no manual API calls.
2. A user can play moves on the interactive board, select a side filter, and submit the position; the page displays W/D/L percentages and a scrollable list of matching games with external links.
3. Two different users' game data and analysis results are fully isolated — user A cannot see or query user B's games.
4. All filter controls (time control, rated, recency, color) are visible simultaneously and update results without a page reload.

**Dependencies:** Phase 1, Phase 2, Phase 3

---

## Requirement Coverage

All 21 v1 requirements are mapped:
- Phase 1: 4 requirements (INFRA-01, INFRA-03, IMP-05, IMP-06)
- Phase 2: 5 requirements (IMP-01, IMP-02, IMP-03, IMP-04, INFRA-02)
- Phase 3: 9 requirements (ANL-02, ANL-03, FLT-01, FLT-02, FLT-03, FLT-04, RES-01, RES-02, RES-03)
- Phase 4: 3 requirements (ANL-01, AUTH-01, AUTH-02)
- Phase 5: 7 provisional requirements (BKM-01 through BKM-07)
- Phase 6: 5 provisional requirements (TEST-01 through TEST-05)
- Phase 7: 6 provisional requirements (STATS-01 through STATS-06)
- Phase 8: 5 provisional requirements (REWORK-01 through REWORK-05)
- Phase 9: 5 provisional requirements (GAMES-01 through GAMES-05)

---

## Phase 5: Position Bookmarks and W/D/L Comparison Charts

**Goal:** Let users save chess positions as bookmarks (with move history and filter settings), view them on a dedicated /bookmarks page with live W/D/L bars per bookmark and a win-rate-over-time line chart, and load bookmarks back into the board editor for editing.

**Requirements:**
- BKM-01: User can create, read, update, and delete position bookmarks stored in the backend
- BKM-02: User can reorder bookmarks by drag-and-drop; order persists across sessions
- BKM-03: /bookmarks page shows a monthly win-rate line chart with one line per bookmark
- BKM-04: Months with 0 games for a bookmark show as gaps in the chart line (not 0%)
- BKM-05: Each user's bookmarks are isolated (user A cannot see user B's bookmarks)
- BKM-06: [Load] on a bookmark navigates to / with the board pre-populated from the bookmark
- BKM-07: Bookmark labels are editable inline on the /bookmarks page

**Depends on:** Phase 4
**Plans:** 4/5 plans executed

Plans:
- [ ] 05-01-PLAN.md — Backend bookmark model, migration, schemas, repository, and CRUD router
- [ ] 05-02-PLAN.md — Backend time-series endpoint (POST /analysis/time-series)
- [ ] 05-03-PLAN.md — Frontend TS types, API client, useBookmarks hooks, useChessGame.loadMoves, Dashboard bookmark button
- [ ] 05-04-PLAN.md — Frontend /bookmarks routing, nav tabs, BookmarksPage, sortable BookmarkList, BookmarkRow
- [ ] 05-05-PLAN.md — WinRateChart (Recharts) and real WDL bar stats wired into BookmarksPage

**Success Criteria:**
1. User can click "★ Bookmark" on the Analysis page to save the current position; it appears immediately on /bookmarks.
2. The /bookmarks page shows each bookmark with a W/D/L bar and the user can drag to reorder, edit labels inline, load positions back to the board, and delete bookmarks.
3. A multi-line Recharts chart below the list shows monthly win rate per bookmark; months with no games show as gaps (not 0%).
4. All bookmark data is user-scoped — no cross-user data leakage.

---

## Phase 6: Optimize UI for Claude Chrome Extension Testing

**Goal:** Audit the frontend and optimize the DOM for AI browser automation via the Claude Chrome extension — add data-testid attributes, semantic HTML, ARIA labels, and click-to-move on the chess board so every interactive element is reliably targetable by automated agents.

**Requirements:**
- TEST-01: All interactive elements use semantic HTML (button, a, nav) rather than generic div/span with onClick
- TEST-02: All clickable elements, inputs, and major layout containers have descriptive data-testid attributes
- TEST-03: All icon-only buttons and dynamic states have accurate aria-labels and ARIA roles
- TEST-04: Chess board moves are playable by clicking source and target squares (not just drag-and-drop)
- TEST-05: CLAUDE.md contains Browser Automation Rules mandating data-testid, semantic HTML, and ARIA for all future frontend code

**Depends on:** Phase 5
**Plans:** 2/2 plans complete

Plans:
- [ ] 06-01-PLAN.md — Semantic HTML fixes + data-testid + ARIA labels across all components
- [ ] 06-02-PLAN.md — Click-to-move on chess board + CLAUDE.md Browser Automation Rules

**Success Criteria:**
1. Every interactive element in the frontend has a data-testid attribute following the kebab-case naming convention.
2. The Claude Chrome extension can target any button, link, input, or toggle via data-testid selectors.
3. The chess board supports both drag-and-drop and click-to-move (two-click pattern).
4. CLAUDE.md permanently mandates automation-friendly patterns for all future frontend development.

---

## Phase 7: Add More Game Statistics and Charts

**Goal:** Extend the application with three statistics pages (Openings, Rating, Global Stats) providing rating-over-time charts per platform/time-control, WDL breakdowns by time control and color, and restructured 5-item navigation -- all using existing game data with no schema migration.

**Requirements:**
- STATS-01: Navigation restructured from 3 to 5 items (Analysis, Bookmarks, Openings, Rating, Global Stats)
- STATS-02: Openings page replaces Stats with identical content (bookmark WDL bars, win rate chart, all filters)
- STATS-03: Rating page shows per-platform rating-over-time line charts with togglable time control lines and recency filter
- STATS-04: Global Stats page shows WDL breakdown by time control and by color with recency filter
- STATS-05: Backend GET endpoints for rating history and global stats with recency filter and auth
- STATS-06: ECO extraction test coverage confirms chess.com variation URLs handled correctly

**Depends on:** Phase 6
**Plans:** 3/3 plans complete

Plans:
- [ ] 07-01-PLAN.md — Backend stats schemas, repository, service, router, and tests
- [ ] 07-02-PLAN.md — Frontend navigation restructuring and Openings page rename
- [ ] 07-03-PLAN.md — Rating page and Global Stats page with charts, hooks, and API wiring

**Success Criteria:**
1. Navigation shows 5 items; Openings page has all existing Stats functionality; /stats redirects to /openings.
2. Rating page shows two separate Recharts LineCharts (chess.com and lichess) with per-time-control lines togglable via legend click, filtered by recency.
3. Global Stats page shows WDL stacked bars by time control (4 categories) and by color (2 categories), filtered by recency.
4. Backend GET /stats/rating-history and GET /stats/global return correct data with auth and recency filter support.
5. ECO extraction handles chess.com variation URLs gracefully with test coverage.

---

## Phase 8: Rework Games and Bookmark tabs: position filter section, position bookmarks section, rename bookmarks to position_bookmarks

**Goal:** Restructure the Games (Dashboard) page left column into three collapsible sections (Position filter, Position bookmarks, More filters), merge bookmark content from the Bookmarks tab into the Games page, remove the Bookmarks navigation tab, and rename bookmarks to position_bookmarks across the entire stack (DB, backend, frontend, API paths).

**Requirements:**
- REWORK-01: Rename bookmarks to position_bookmarks across DB table, backend models/schemas/routers, frontend types/hooks/components, and API paths
- REWORK-02: Dashboard left column restructured into three collapsible sections (Position filter open, Position bookmarks collapsed, More filters collapsed) with always-visible Filter + Import buttons
- REWORK-03: Remove dedicated Bookmarks page and navigation tab (5 tabs to 4 tabs: Games, Openings, Rating, Global Stats)
- REWORK-04: Remove WDL bars and WinRateChart from bookmark cards; relocate chart components to components/charts/
- REWORK-05: Move "Bookmark this position" button into the Position filter collapsible section

**Depends on:** Phase 7
**Plans:** 3/3 plans complete

Plans:
- [ ] 08-01-PLAN.md — Backend rename: Alembic migration, model/repo/schemas/router rename to position_bookmarks, test updates
- [ ] 08-02-PLAN.md — Frontend rename: types/hooks/API client/components rename to position-bookmarks, chart relocation, card simplification
- [ ] 08-03-PLAN.md — Dashboard UI restructure: three collapsible sections, in-place bookmark Load, Bookmarks page removal, nav update

**Success Criteria:**
1. Database table is `position_bookmarks` with all CRUD endpoints at `/position-bookmarks` paths; all tests pass.
2. Dashboard left column has three collapsible sections: Position filter (open by default), Position bookmarks (collapsed), More filters (collapsed); Filter and Import buttons always visible below.
3. Loading a bookmark replays moves in-place on the board without page navigation.
4. Navigation shows 4 tabs (Games, Openings, Rating, Global Stats); /bookmarks redirects to /.
5. Openings page WinRateChart and WDLBarChart render correctly from their new location in components/charts/.

---

## Phase 9: Rework the games list with game cards, username import, and improved pagination

**Goal:** Transform the games list from a plain HTML table to rich full-width game cards showing more metadata per game, move chess platform usernames from localStorage to backend user profile storage with a streamlined import modal, and replace naive pagination with truncated page numbers and a smaller page size.

**Requirements:**
- GAMES-01: Games displayed as full-width cards with colored left border accent (green=win, gray=draw, red=loss) showing result, opponent, ratings, opening, color, time control, date, moves, and platform link
- GAMES-02: Game model has move_count column; existing games backfilled from PGN; new games populated at import time
- GAMES-03: Platform usernames stored on backend User model; auto-saved on import; import modal shows sync view for returning users and input view for first-time users
- GAMES-04: GameRecord API response expanded with user_rating, opponent_rating, opening_name, opening_eco, user_color, move_count
- GAMES-05: Pagination uses truncated page numbers with ellipsis, page size 20, page change scrolls to top

**Depends on:** Phase 8
**Plans:** 5/5 plans complete

Plans:
- [ ] 09-01-PLAN.md — Backend model expansion, migration, schema enrichment, profile endpoint, import username auto-save
- [ ] 09-02-PLAN.md — Frontend game cards with colored left border and truncated pagination
- [ ] 09-03-PLAN.md — Import modal redesign with backend-stored usernames and two-mode UI
- [ ] 09-04-PLAN.md — Gap closure: both-player columns, optional target_hash, dev auth bypass
- [ ] 09-05-PLAN.md — Gap closure: GameCard redesign with both players, default games list on dashboard

**Success Criteria:**
1. Games page shows rich cards with colored left border accent instead of table rows; each card shows result, opponent, ratings, opening, color indicator, TC, date, moves, and platform link.
2. move_count column exists on Game model; existing games backfilled; new imports populate move_count.
3. Platform usernames stored in User model; auto-saved after import; localStorage username storage removed.
4. Import modal shows sync view with per-platform Sync buttons for returning users; input view for first-time users.
5. Pagination shows truncated page numbers with ellipsis; page size is 20; page change scrolls to top.

---
*Created: 2026-03-11*
*Phase 5 added: 2026-03-13*
*Phase 6 planned: 2026-03-13*
*Phase 7 planned: 2026-03-14*
*Phase 8 planned: 2026-03-14*
*Phase 9 planned: 2026-03-14*
