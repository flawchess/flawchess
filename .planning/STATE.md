---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Opening Explorer & UI Restructuring
status: executing
last_updated: "2026-03-17T00:00:00.000Z"
last_activity: 2026-03-17 — Completed 14-02-PLAN.md (OpeningsPage tabbed hub)
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 8
  completed_plans: 8
  percent: 88
---

# Project State: Chessalytics

## Current Phase
Phase: 14 of 14 (UI Restructuring)
Plan: 2 of 2 complete
Status: Phase 14 complete — ready for Phase 15 (Consolidation)
Last activity: 2026-03-17 — Completed 14-02-PLAN.md (OpeningsPage tabbed hub with 3 URL-based sub-tabs)

Progress: [█████████░] 88%

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
| 15 | Consolidation | Planned | ? |

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

### Pending Todos
- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions for querying pieces on specific squares
- **Display opening name from lichess chess-openings database** (ui) — Show ECO code + opening name on interactive board via prefix-match
- **GamesTab pagination offset**: offset is in OpeningsPage state and resets to 0 on tab switch — decided in 14-02 execution
- **Track user account creation and last login timestamps** (auth) — Add created_at and last_login columns to users table

### Roadmap Evolution
- Phase 15 added: Consolidation - remove unnecessary code, rename endpoints/modules, update CLAUDE.md and README.md

### Blockers/Concerns
None.

---
Last activity: 2026-03-17 — Completed 14-02-PLAN.md (OpeningsPage tabbed hub with 3 URL-based sub-tabs, shared sidebar, auto-fetch on all tabs)
