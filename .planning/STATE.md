---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_plan: 09-03 complete
status: completed
stopped_at: "Completed quick-13: Fix dev bypass non-deterministic user query"
last_updated: "2026-03-14T20:01:59.938Z"
last_activity: "2026-03-14 - Completed 09-02: GameCard and GameCardList components with truncated pagination, PAGE_SIZE=20"
progress:
  total_phases: 9
  completed_phases: 8
  total_plans: 32
  completed_plans: 31
---

# Project State: Chessalytics

## Current Phase
Phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
Status: Complete — 3/3 plans done
Current Plan: 09-03 complete
Stopped At: Completed quick-13: Fix dev bypass non-deterministic user query

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-11)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Phase 5 - Position Bookmarks and W/D/L Comparison Charts

## Phase Progress
| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Data Foundation | Complete | 2/2 |
| 2 | Import Pipeline | Complete | 4/4 |
| 3 | Analysis API | Complete | 2/2 |
| 4 | Frontend and Auth | Complete | 3/3 |
| 5 | Position Bookmarks and W/D/L Charts | Complete | 5/5 |
| 6 | Optimize UI for Claude Chrome Extension Testing | Complete | 2/2 |
| 7 | More game statistics and charts | Complete | 3/3 |
| 8 | Rework Games and Bookmark tabs | Complete | 3/3 |
| 9 | Rework games list with game cards and improved pagination | In Progress | 4/5 |

## Key Context
- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import

## Accumulated Context

### Roadmap Evolution
- Phase 5 added: Position bookmarks and W/D/L comparison charts
- Phase 6 added: Optimize UI for Claude Chrome Extension Testing
- Phase 7 added: Add more game statistics and charts by replicating the most popular analyses from chess.com and lichess insights
- Phase 8 added: Rework Games and Bookmark tabs: position filter section, position bookmarks section, rename bookmarks to position_bookmarks
- Phase 9 added: Rework the games list with game cards, username import, and improved pagination

### Key Decisions
- **FastAPI dependency_overrides for test auth bypass**: Use `dependency_overrides[_dev_bypass_user] = _jwt_current_active_user` in session-scoped autouse fixture — intercepts at resolution time regardless of how routers imported the callable; avoids patching module-level attributes directly
- **ENVIRONMENT setting dev bypass**: `ENVIRONMENT=development` in .env swaps `current_active_user` to `_dev_bypass_user` at import time — returns first active user without JWT; all routers get the bypass automatically since they import from `app.users`
- **Optional target_hash in analysis**: `target_hash=None` skips the `game_positions` join entirely and queries `games` table directly with `Game.user_id` filter — enables a default "all games" list without position filter
- **Backfill migration partial data**: `white_username` is NULL for existing games where user played white (own per-game username was never stored); correctly backfilled where known from `opponent_username`
- **Derived state pattern for ImportModal reset**: track prevProfile/prevOpen in state, compare during render, call setState inline — avoids react-hooks/set-state-in-effect lint violation (same pattern as selectedSquare)
- **result.unique().scalar_one() for User queries**: User model has joined eager load on oauth_accounts — must call .unique() before scalar extraction or SQLAlchemy raises InvalidRequestError
- **update_profile non-None only**: PUT /users/me/profile only applies fields with non-None values so partial updates don't clear existing usernames
- **Import auto-save best-effort**: platform username saved after final import commit in separate try/except + commit so username save failure doesn't roll back the import
- **AsyncAttrs import path**: Use `from sqlalchemy.ext.asyncio import AsyncAttrs` (not `sqlalchemy.orm`) in SQLAlchemy 2.0.x
- **user_id denormalized on game_positions**: Required for composite index lookups without joins on the analysis hot path
- **BIGINT type_annotation_map**: `Base` class maps `int -> BIGINT` so all `Mapped[int]` columns auto-resolve to BIGINT
- **server_default=func.now()**: Used for `imported_at` (not Python-evaluated `datetime.utcnow`)
- **Local PostgreSQL**: postgresql@17 installed via brew, database `chessalytics` created for development
- **Zobrist color_pivot**: 0 for WHITE, 1 for BLACK — matches polyglot standard (white = even indices per piece type, black = odd)
- **hashes_for_game empty list**: Returns [] for PGN with no mainline moves (garbage input); ply 0 only included when at least one move exists
- **Zobrist ply 0**: hashes_for_game includes ply 0 (initial position) before any move is played
- **bulk_insert_positions no RETURNING**: positions only inserted for new games returned by bulk_insert_games; no conflict handling needed
- **db_session fixture**: AsyncSession bound to connection-level transaction rolled back per-test for real-DB isolation without cleanup code
- **Time control bucketing**: estimated duration = base + increment*40; thresholds <=180 bullet, <=600 blitz, <=1800 rapid, else classical
- **chess.com incremental sync boundary**: archive skipped when archive_end (first day of next month) <= since_timestamp; current month always included
- **chess.com 429 backoff**: single 60s sleep + one retry (not exponential) for simplicity
- **lichess perfType filter**: ultraBullet,bullet,blitz,rapid,classical sent on every request; correspondence and unlimited excluded
- **lichess moves=false**: PGN available via pgnInJson=true so moves array field excluded from response
- **In-memory job registry + DB fallback**: Live job state in _jobs dict (zero-latency reads); DB queried only for historical/restarted jobs
- **PGN lookup via SELECT after bulk_insert**: Correctness over index-alignment — SELECT (id, pgn) for new game IDs handles ON CONFLICT gaps correctly
- **chess.com non-200 archives raises ValueError**: Any non-200/non-404 archives response raises ValueError with status code before .json() is called — consistent with job error contract
- **chess.com per-archive non-200 uses continue**: Partial archive failure uses continue not raise — one bad month should not abort the whole user import
- **Analysis DISTINCT by Game.id**: _build_base_query uses .distinct(Game.id) so a position appearing at multiple plies counts the game only once in W/D/L stats
- **Analysis two-query pattern**: query_all_results fetches lightweight (result, user_color) tuples for stats; query_matching_games fetches full Game objects for display — keeps stats accurate for total > limit
- **DISTINCT ON ORDER BY constraint**: PostgreSQL requires DISTINCT ON column to be first in ORDER BY — paginated analysis query uses order_by(Game.id, Game.played_at.desc())
- **select_entity list unpacking**: _build_base_query normalizes select_entity to list and unpacks via *entities — supports both single ORM entity and multi-column selects in query_all_results
- **FastAPI-Users IntegerIDMixin on UserManager**: IntegerIDMixin goes on UserManager class, not on the User model itself
- **asyncio_default_test_loop_scope=session**: App-level engine pool binds to first event loop; session scope prevents cross-test asyncpg RuntimeError
- **Auth test unique emails**: Users table persists across runs; tests use uuid4 email suffixes for idempotency
- **user_id before create_task**: Depends(current_active_user) only valid in request scope — extract user.id before asyncio.create_task
- **Vite proxy for API routing**: Frontend uses relative URLs (/auth, /analysis, /imports) forwarded to localhost:8000 via Vite server.proxy — no hardcoded backend URL
- **BigInt + string transport for Zobrist**: Hashes computed as BigInt throughout JS (avoids IEEE-754 precision loss), converted to decimal string for JSON; backend coerce_target_hash validator converts str->int
- **Zobrist JS uses dual indexing**: whiteHash/blackHash use color-relative pivot (white=0, black=1 matching _color_hash); fullHash uses ZobristHasher pivot (white=1, black=0) plus castling/EP/turn
- **Turn hash XOR on white to move**: chess.polyglot.zobrist_hash XORs index 780 when WHITE is to move — JS port matches this (not black)
- **shadcn/ui Nova preset, dark-only**: <html class="dark"> in index.html, Nova/Radix theme locked for frontend
- **react-chessboard v5 options API**: v5 changed from flat props to a single `options` object prop — `<Chessboard options={{ position, boardStyle, onPieceDrop }} />`
- **useChessGame replay approach**: goToMove replays from new Chess() rather than undoing — chess.js has no undo API; replay guarantees correctness
- **PieceDropHandlerArgs.targetSquare is string | null**: null when piece dropped off board — guard required before calling makeMove
- **Google OAuth SPA flow**: /callback redirects to FRONTEND_URL/auth/callback#token=JWT so SPA can read token from URL fragment without it appearing in server logs
- **ImportJobStatus mismatch**: backend uses 'completed'/'failed', not 'done'/'error' — was root cause of spinner never stopping + errors never showing
- **GET /games/count**: lightweight endpoint for dashboard empty-state CTA — avoids special-casing analysis endpoint with null hash
- **react-chessboard squareStyles**: prop name for per-square CSS overrides is `squareStyles` (not `customSquareStyles`)
- **Bookmark user_id no FK constraint**: bookmarks table omits FK on user_id — users table is in a different migration, avoids FK ordering issues
- **Bookmark moves as JSON Text**: moves column stores JSON-encoded list[str] in Text column; BookmarkResponse uses model_validator to deserialize
- **PUT /bookmarks/reorder before /bookmarks/{id}**: FastAPI route ordering — "reorder" must be defined before /{id} to prevent it being parsed as integer
- **BookmarkResponse model_validator deserializes moves**: mode="before" validator converts ORM string to list[str] before field validation
- **get_async_session auto-commit**: Session dependency commits after yield — repositories use flush() for within-request visibility, commit happens automatically at request end
- **date_trunc UTC normalization**: Use `func.timezone("UTC", timestamptz_col)` before `func.date_trunc` — PostgreSQL session timezone (Europe/Zurich) causes month drift without explicit UTC conversion
- **query_time_series raw tuples**: Returns (month_dt, result, user_color) tuples; service aggregates W/D/L per month key — gap months (no games) are absent from results, not zero-filled
- **ProtectedLayout + Outlet**: NavHeader rendered once in ProtectedLayout above Outlet; replaces per-page ProtectedRoute wrapper; auth guard is in ProtectedLayout
- **isDirtyRef for bookmark blur cancel**: ref (not state) tracks whether blur should skip save; set true on Escape key or action button mousedown
- **BookmarkRow WDL stats optional**: rendered only when stats prop provided; plan 05-05 wires actual POST /analysis/time-series data
- **data-testid on Link not Button asChild**: Button with asChild merges props into child — put data-testid on the `<Link>` so it renders on the `<a>` tag in the DOM
- **BookmarkCard label as button**: Converted from `<span onClick>` to `<button>` for semantic HTML and accessibility compliance
- **State-during-render reset for selectedSquare**: avoids react-hooks/set-state-in-effect and react-hooks/refs lint violations; uses prevPosition state compared during render — React-recommended derived state pattern
- **Browser Automation Rules in CLAUDE.md**: permanent mandatory rules for all future frontend code — data-testid on every interactive element, semantic HTML, ARIA labels, chess board must have data-testid="chessboard" and id="chessboard"
- **data-testid hyphen normalization for multi-word nav labels**: label.toLowerCase().replace(/\s+/g, '-') so "Global Stats" -> nav-global-stats (not "nav-global stats" with a space)
- **Stats.tsx kept as dead code**: not deleted after Openings.tsx rename — will be removed in cleanup at end of phase 7
- **RatingChart data model**: flat array of {date, [tc]: rating} rows (one per game) — each row has only one TC key, Recharts handles gaps between TC lines naturally
- **WDLCategoryChart as local component**: unexported component inside GlobalStatsCharts.tsx — avoids react-refresh/only-export-components lint violation while keeping chart logic co-located
- **op.rename_table + ALTER INDEX RENAME for bookmarks->position_bookmarks**: preserves existing data for zero-data-loss rename in Alembic migration
- **PositionBookmarkRepository = sys.modules[__name__] alias**: satisfies import contract while keeping module-level function pattern in position_bookmark_repository
- **PositionBookmarkCard uses onLoad(bookmark) callback instead of navigate()**: consumer decides navigation behavior — decouples card from routing
- **WinRateChart and WDLBarChart relocated to components/charts/**: shared chart components now live in neutral folder, use PositionBookmarkResponse type
- **position-bookmarks query key replaces bookmarks in TanStack Query cache**: all hooks use ['position-bookmarks'] query key for cache invalidation
- **Dashboard three-section collapsible layout**: Position filter (open by default), Position bookmarks (collapsed), More filters (collapsed) — Played as and Match side toggles moved from FilterPanel into Position filter section
- **handleLoadBookmark pattern**: chess.loadMoves(bkm.moves), setBoardFlipped(bkm.is_flipped), setFilters to bkm.color + bkm.match_side — consumer decides navigation behavior
- **Vite proxy /bookmarks -> /position-bookmarks**: proxy entry must match API route prefix; old /bookmarks entry caused black screen on load and 404s on bookmark save
- **getPaginationItems module-private**: not exported from GameCardList.tsx to satisfy react-refresh/only-export-components ESLint rule
- **GameCardList replaces GameTable**: drop-in replacement with matching props interface; PAGE_SIZE reduced from 50 to 20 games per page
- **GameCard left border accent**: border-l-4 with border-l-green-600/border-l-gray-500/border-l-red-600 for win/draw/loss — plain div not shadcn Card
- **positionFilterActive flag for Dashboard right-column**: false=auto-fetched default games list (useQuery), true=WDL+position-filtered view (useMutation result)
- **useGamesQuery vs useAnalysis split**: useGamesQuery uses useQuery for auto-fetch on mount; useAnalysis useMutation is for Filter button only; enabled=!positionFilterActive prevents redundant API calls when filter is active
- **Derived user_rating via CASE WHEN**: stats_repository uses CASE WHEN user_color='white' THEN white_rating ELSE black_rating END — no stored user_rating column needed
- **GameCard opponent bolding**: !isUserWhite for white span bold, isUserWhite for black span bold — the opponent (not the user) is always emphasized

### Performance Metrics
| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01 | 5min | 2 | 18 |
| 01 | 02 | 3min | 3 | 4 |
| 02 | 01 | 6min | 2 | 10 |
| 02 | 02 | 3min | 2 | 4 |
| 02 | 03 | 3min | 2 | 5 |
| 02 | 04 | 2min | 2 | 2 |
| 03 | 01 | 2min | 2 | 5 |
| 03 | 02 | 4min | 2 | 3 |
| 04 | 01 | 10min | 2 | 12 |
| 04 | 02 | 15min | 3 | 20 |
| 04 | 03 | 45min | 3 | 27 |
| 05 | 01 | 3min | 2 | 8 |
| 05 | 02 | 15min | 2 | 5 |
| 05 | 03 | 10min | 2 | 5 |
| 05 | 04 | 5min | 2 | 7 |
| 06 | 01 | 7min | 2 | 14 |
| 06 | 02 | 5min | 2 | 2 |
| Phase 07 P02 | 2min | 2 tasks | 4 files |
| Phase 07 P01 | 5min | 2 tasks | 8 files |
| Phase 07 P03 | 2min | 2 tasks | 7 files |
| Phase 08 P01 | 8min | 2 tasks | 9 files |
| Phase 08 P02 | 6min | 2 tasks | 12 files |
| Phase 08 P03 | 30min | 3 tasks | 7 files |
| Phase 08 P03 | 30min | 3 tasks | 7 files |
| Phase 09 P01 | 5min | 3 tasks | 12 files |
| Phase 09 P03 | 3min | 2 tasks | 4 files |
| Phase 09 P02 | 4min | 2 tasks | 4 files |
| Phase 09 P04 | 4min | 2 tasks | 8 files |
| Phase 09 P05 | 4min | 2 tasks | 4 files |
| Phase 09 P07 | 5min | 1 tasks | 1 files |
| Phase 09 P06 | 6min | 2 tasks | 12 files |
| Phase 09 P08 | 5min | 2 tasks | 2 files |

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | can the coordinate numbers and letters be displayed outside of the board? | 2026-03-12 | b40ad87 | [1-can-the-coordinate-numbers-and-letters-b](.planning/quick/1-can-the-coordinate-numbers-and-letters-b/) |
| 2 | add platform filter in more filters section | 2026-03-12 | b5266a9 | [2-add-platform-filter-in-more-filters-sect](.planning/quick/2-add-platform-filter-in-more-filters-sect/) |
| 3 | fix matched games count showing wrong total and board reset clears analysis | 2026-03-12 | d6fadbc | [3-fix-matched-games-count-showing-wrong-to](.planning/quick/3-fix-matched-games-count-showing-wrong-to/) |
| 4 | flag computer opponent games on import and parse chess.com opening names | 2026-03-12 | a2479c2 | [4-flag-computer-opponent-games-on-import-a](.planning/quick/4-flag-computer-opponent-games-on-import-a/) |
| 5 | add opponent filter (human/bot/both) to dashboard analysis | 2026-03-12 | 011e56a | [5-add-opponent-filter-human-bot-both-to-da](.planning/quick/5-add-opponent-filter-human-bot-both-to-da/) |
| 6 | fix bookmark save: BookmarkResponse int target_hash validation error + session commit | 2026-03-13 | 0e94bcf | [6-fix-bookmark-save-failed-to-save-bookmar](.planning/quick/6-fix-bookmark-save-failed-to-save-bookmar/) |
| 7 | Store board flip state in bookmarks | 2026-03-13 | c0a980e | [7-store-board-flip-state-in-bookmarks](.planning/quick/7-store-board-flip-state-in-bookmarks/) |
| 9 | Fix Global Stats 500 error (_aggregate_wdl KeyError) and RatingChart adaptive Y-axis | 2026-03-14 | befcb4c | [9-some-fixes-for-phase-7](.planning/quick/9-some-fixes-for-phase-7/) |
| 10 | Fix Y-axis ticks on chess.com RatingChart — uniform spacing via adaptive step selection | 2026-03-14 | d9eb0f0 | [10-fix-y-axis-ticks-on-chess-com-rating-cha](.planning/quick/10-fix-y-axis-ticks-on-chess-com-rating-cha/) |
| 11 | Toggle series on/off by clicking legend in all Recharts charts | 2026-03-14 | 4c398f0 | [11-toggle-series-on-off-by-clicking-legend-](.planning/quick/11-toggle-series-on-off-by-clicking-legend-/) |
| 12 | Fix opening ECO categorization via openings.tsv longest-prefix matching | 2026-03-14 | fceef4f | [12-fix-the-opening-eco-categorization-for-c](.planning/quick/12-fix-the-opening-eco-categorization-for-c/) |
| 13 | Critical bug: games, bookmarks, and usernames not displayed despite valid DB data | 2026-03-14 | 814b76d | [13-critical-bug-games-bookmarks-and-usernam](.planning/quick/13-critical-bug-games-bookmarks-and-usernam/) |

### Pending Todos
- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions for querying pieces on specific squares
- **Display opening name from lichess chess-openings database** (ui) — Show ECO code + opening name on interactive board via prefix-match; optional backend Zobrist lookup
- **Optimize for automated browser testing with Chrome Plugin** (testing) — Add data-testid attributes and stable selectors for browser automation UAT

---
Last activity: 2026-03-14 - Completed quick task 13: Fix dev bypass non-deterministic user query
