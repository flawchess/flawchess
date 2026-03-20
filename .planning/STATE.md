---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Opening Explorer & UI Restructuring
status: executing
last_updated: "2026-03-19T18:54:35Z"
last_activity: "2026-03-19 — Completed quick task 260319-rj3: Persist import job status across login"
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 14
  completed_plans: 14
  percent: 100
---

# Project State: Chessalytics

## Current Phase
Phase: 16 of 16 (Improve game cards UI — icons, layout, hover minimap)
Plan: 3 of 3 complete
Status: Complete
Last activity: 2026-03-18 — Completed 16-03: result_fen Alembic migration gap closure (GCUI-01 fully satisfied)

Progress: [██████████] 100%

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-16)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.1 — Opening Explorer & UI Restructuring

## Phase Progress
| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 11 | Schema and Import Pipeline | Complete (1/1 plan complete) | 1 |
| 12 | Backend Next-Moves Endpoint | Complete (2/2 plans complete) | 2 |
| 13 | Frontend Move Explorer Component | Complete (2/2 plans complete) | 2 |
| 14 | UI Restructuring | Complete (2/2 plans complete) | 2 |
| 15 | Enhanced game import data | Complete (3/3 plans complete) | 3 |
| 16 | Improve game cards UI — icons, layout, hover minimap | Complete (3/3 plans complete) | 3 |

## Key Context
- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- DB wipe accepted for v1.1 — no backfill migration needed for move_san

## Accumulated Context

### Key Decisions
- **DB wipe for v1.1**: No migration needed — reimport after schema change (settled in PROJECT.md)
- **move_san ply semantics**: move_san on ply N = move played FROM position at ply N (leading to ply N+1); final position row has NULL; ply-0 has first move SAN (not NULL) — confirmed in 11-01 execution
- **DISTINCT + GROUP BY for next-moves**: use COUNT(DISTINCT g.id) not COUNT(*) — transpositions cause same position at multiple plies in one game; mirrors existing _build_base_query discipline
- **query_next_moves self-join pattern**: gp1/gp2 aliased GamePosition self-join on (game_id, ply+1) gets both move_san and result_hash in single aggregation round-trip
- **_apply_game_filters helper**: shared filter application across query_next_moves and query_transposition_counts — prevents filter drift between endpoint consistency
- **Filter state lifted to OpeningsPage**: all shared filter state must live in OpeningsPage parent — not inside sub-tab components — to survive tab switches without reset
- **positionFilterActive gating**: Move Explorer should only activate when at least 1 move played or bookmark loaded (avoids overwhelming starting-position list)
- **Import page cache invalidation**: handleJobDone callbacks must invalidate ['games'], ['gameCount'], ['userProfile'] on the new ImportPage — same as current Dashboard modal
- **result_fen via PGN replay**: _fetch_result_fens pushes N moves in mainline and calls board.board_fen() — computed at query time, not stored; uses DISTINCT ON batch + PGN batch to avoid N+1
- **position_stats uses full_hash**: next-moves endpoint always uses GamePosition.full_hash for position_stats (no match_side concept in this endpoint)
- **BoardArrow type defined locally in ChessBoard.tsx**: react-chessboard v5 Arrow import path is fragile; local interface is simpler and sufficient
- **clearArrowsOnPositionChange: false is CRITICAL**: without it react-chessboard clears arrows on every position prop change, causing them to vanish after every move
- **useNextMoves has no enabled gate**: explorer is always visible per design; positionFilterActive gate handled at parent component level in Plan 02
- **MoveExplorer receives props not hook**: hook called in Dashboard parent so boardArrows can be computed from same data in single useMemo
- **TypeScript filter narrowing**: `.filter((a): a is NonNullable<typeof a> => a !== null)` required — `.filter(Boolean)` does not narrow union types in strict mode
- **ImportProgress at App level**: rendered outside Routes in AppRoutes fragment so job toasts fire from any page
- **isActive() nav helper**: uses startsWith('/openings') for prefix matching /openings/* wildcard route in NavHeader
- **usePositionAnalysisQuery uses useQuery**: not useMutation — Plan 02 can auto-fetch on position/filter change without manual trigger
- **OpeningsPage tabbed hub**: all shared state (chess, filters, boardFlipped, bookmarks, gamesOffset) in parent component — never inside TabsContent children — for tab-switch persistence (UIRS-02)
- **No positionFilterActive gate on Games tab**: usePositionAnalysisQuery always auto-fetches from initial position — cleaner UX than Dashboard's manual Filter button flow
- **Tab JSX content as variables**: moveExplorerContent/gamesContent/statisticsContent defined before return and reused in both desktop and mobile Tabs instances
- **selectedPlatforms state is null (all) or Platform[] array**: single-element array maps to platform query param in hooks; clicking only active platform resets to null (show all) — settled in 15-01
- **Rating page merged into Global Stats**: /rating redirects to /global-stats; nav reduced to 3 items (Import, Openings, Global Stats) — settled in 15-01
- **RatingChart monthly categorical axis**: uses YYYY-MM string keys (not timestamps) with formatMonth tickFormatter — matches WinRateChart approach, removes adaptive computeXTicks complexity — settled in 15-02
- **Openings Statistics chart headings**: text-lg font-medium mb-3 wrapping divs with h2 titles match GlobalStatsCharts pattern — settled in 15-02
- **180s time control is blitz**: strict `< 180` for bullet boundary so 3+0 (180s) is blitz; matches chess.com/lichess conventions — settled in 15-01 (EIGD-03)
- **clock_seconds as Float nullable**: stored on game_positions for future use; None when PGN lacks %clk or for final position row — settled in 15-01 (EIGD-01)
- **Termination from loser's result (chess.com)**: termination_raw = loser's result string; for draws both sides have same string — settled in 15-01 (EIGD-02)
- **username-scoped sync boundary**: get_latest_for_user_platform filters by username so second-username imports start full fetch — settled in 15-01 (EIGD-04)
- **Google SSO last_login via direct sa_update in google_callback**: on_after_login is not called for OAuth flow in FastAPI-Users — fix must be in the callback handler — settled in 15-02 (EIGD-06)
- **queryClient.clear() before localStorage.removeItem on logout**: clears all TanStack Query cache before auth state removal to prevent data leakage to next user on same browser — settled in 15-02 (EIGD-05)
- **_normalize_tc_str helper**: drops +0 suffix for zero-increment time controls — both chess.com (raw API string) and lichess (constructed f"{initial}+{increment}") call this helper for consistent storage — settled in 15-03 (EIGD-07)
- **QueryClient extracted to lib/queryClient.ts**: required because api/client.ts is a plain module (not React component) so useQueryClient hook is unavailable; shared singleton allows 401 interceptor and login() to call queryClient.clear() — settled in 15-03 (EIGD-05)
- **result_fen stored at import time via hashes_for_game()**: board.board_fen() captured after final push in PGN replay loop, returned as 2nd element of (hash_tuples, result_fen) tuple; stored in games table alongside move_count — settled in 16-01 (GCUI-01)
- **Single TooltipProvider in GameCardList**: wraps all game cards to avoid 50x context overhead; TooltipContent uses hidden sm:block for desktop-only hover — settled in 16-02 (GCUI-03)
- **Mobile game card expand via isExpanded/onToggle**: expandedGameId state in GameCardList; only one card expanded at a time; reset on page change — settled in 16-02 (GCUI-04)
- **GameCard null-safe metadata**: time_control_bucket, played_at, move_count, termination each have guard clauses; null fields omitted entirely (no dash placeholders) — settled in 16-02 (GCUI-05)
- **result_fen migration gap closure**: migration file was generated during 16-01 execution but left untracked in git; 16-03 committed it and fixed test call sites for get_latest_for_user_platform missing username arg — settled in 16-03 (GCUI-01)

### Pending Todos
- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions for querying pieces on specific squares
- **Display opening name from lichess chess-openings database** (ui) — Show ECO code + opening name on interactive board via prefix-match
- **GamesTab pagination offset**: offset is in OpeningsPage state and resets to 0 on tab switch — decided in 14-02 execution

### Roadmap Evolution
- Phase 15 added: Consolidation - remove unnecessary code, rename endpoints/modules, update CLAUDE.md and README.md
- Phase 15 replaced: removed "Chart Consolidation and Polish" (completed), renumbered Phase 16 "Enhanced game import data" to Phase 15
- Phase 16 added: Improve game cards UI — icons, layout, hover minimap

### Blockers/Concerns
None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260317-ppo | Fix piece filter interaction with games and moves tables | 2026-03-17 | aa21696 | [260317-ppo-fix-piece-filter-interaction-with-games-](./quick/260317-ppo-fix-piece-filter-interaction-with-games-/) |
| 260317-qe1 | Move Suggest bookmarks below list, full-width buttons, right-align Piece filter | 2026-03-17 | 23e1a6c | [260317-qe1-move-suggest-bookmarks-below-list-full-w](./quick/260317-qe1-move-suggest-bookmarks-below-list-full-w/) |
| 260317-qjf | Match Suggest bookmarks button size, add color circles to bookmark cards | 2026-03-17 | 22609e8 | [260317-qjf-match-suggest-bookmarks-button-size-add-](./quick/260317-qjf-match-suggest-bookmarks-button-size-add-/) |
| 260317-qsf | Fix bookmark delete not updating UI until page refresh | 2026-03-17 | 9ce0453 | [260317-qsf-fix-bookmark-delete-not-updating-ui-unti](./quick/260317-qsf-fix-bookmark-delete-not-updating-ui-unti/) |
| 260317-qyx | Style action buttons with dark blue, move into collapsible, add dividers | 2026-03-17 | 13b127b | [260317-qyx-style-action-buttons-with-distinct-color](./quick/260317-qyx-style-action-buttons-with-distinct-color/) |
| 260317-rac | Relabel Bookmark to Save and add hover darkening | 2026-03-17 | 49c6bbd | [260317-rac-relabel-bookmark-to-save-add-hover-darke](./quick/260317-rac-relabel-bookmark-to-save-add-hover-darke/) |
| 260318-pp5 | Add hover info icon to Piece filter, remove tab-based filter disabling | 2026-03-18 | 679a315 | [260318-pp5-add-hover-info-icon-to-piece-filter-with](./quick/260318-pp5-add-hover-info-icon-to-piece-filter-with/) |
| 260318-pz3 | Show played-as color circle in Results by Opening bar chart labels | 2026-03-18 | 05dee09 | [260318-pz3-show-played-as-color-circle-in-results-b](./quick/260318-pz3-show-played-as-color-circle-in-results-b/) |
| 260318-qtt | Store created_at and last_login timestamps on user accounts | 2026-03-18 | 60a88cc | [260318-qtt-store-the-date-time-when-a-user-account-](./quick/260318-qtt-store-the-date-time-when-a-user-account-/) |
| 260318-vux | Darken WDL chart win/loss colors to match board arrow tone | 2026-03-18 | 30833d9 | [260318-vux-darken-wdl-chart-red-green-colors-to-mat](./quick/260318-vux-darken-wdl-chart-red-green-colors-to-mat/) |
| 260318-w15 | Fix Google SSO requiring double-click to sign in | 2026-03-18 | f277957 | [260318-w15-fix-google-sso-requiring-double-click-to](./quick/260318-w15-fix-google-sso-requiring-double-click-to/) |
| 260319-owl | Darken WDL draw color to match win/loss brightness | 2026-03-19 | pending | [260319-owl-make-draw-color-darker-grey-in-wdl-so-it](./quick/260319-owl-make-draw-color-darker-grey-in-wdl-so-it/) |
| 260319-p80 | Color-code move arrows by win rate using oklch gradient | 2026-03-19 | efb2764 | [260319-p80-color-code-move-arrows-by-win-rate-using](./quick/260319-p80-color-code-move-arrows-by-win-rate-using/) |
| 260319-rj3 | Persist import job status across login | 2026-03-19 | 9824bf6 | [260319-rj3-persist-import-job-status-across-login-a](./quick/260319-rj3-persist-import-job-status-across-login-a/) |
| 260319-t3x | Add tooltip info hover icons for move arrows and position bookmarks | 2026-03-19 | 5eb3c22 | [260319-t3x-add-tooltip-info-hover-icons-to-explain-](./quick/260319-t3x-add-tooltip-info-hover-icons-to-explain-/) |
| 260320-cit | Adaptive granularity in RatingChart (daily/weekly/monthly) | 2026-03-20 | 5c7fa4a | [260320-cit-use-daily-datapoints-in-global-stats-rat](./quick/260320-cit-use-daily-datapoints-in-global-stats-rat/) |
| 260320-d5b | Smarter win rate over time chart with rolling windows | 2026-03-20 | 79ce0e8 | [260320-d5b-smarter-win-rate-over-time-chart-with-ro](./quick/260320-d5b-smarter-win-rate-over-time-chart-with-ro/) |
| 260320-eeo | Move arrow explanation from Move tooltip to chessboard info icon | 2026-03-20 | 6ae1562 | [260320-eeo-remove-arrow-explanation-from-move-toolt](./quick/260320-eeo-remove-arrow-explanation-from-move-toolt/) |
| 260320-epc | Add thin outlines to the move arrows | 2026-03-20 | 55a23a1 | [260320-epc-add-thin-outlines-to-the-move-arrows](./quick/260320-epc-add-thin-outlines-to-the-move-arrows/) |

---
Last activity: 2026-03-20 - Completed quick task 260320-epc: Add thin outlines to the move arrows
