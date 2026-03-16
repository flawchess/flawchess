# Architecture Research

**Domain:** Chess analysis platform — move explorer and UI restructuring (v1.1)
**Researched:** 2026-03-16
**Confidence:** HIGH (based on direct codebase analysis of v1.0 implementation)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React 19)                          │
├──────────────────┬───────────────────────────────┬──────────────────┤
│  /import (NEW)   │  /openings (RESTRUCTURED)      │  / (Dashboard)   │
│  ImportPage      │  OpeningsPage                  │  DashboardPage   │
│  (full page)     │  ├─ Board + shared filters      │  (unchanged      │
│                  │  ├─ MoveExplorerTab (NEW)        │   except import  │
│                  │  ├─ GamesTab (extracted)         │   button links   │
│                  │  └─ StatisticsTab (existing)     │   to /import)    │
├──────────────────┴───────────────────────────────┴──────────────────┤
│               TanStack Query (cache / server state)                  │
│  useAnalysis  useNextMoves(NEW)  useImport  usePositionBookmarks     │
├─────────────────────────────────────────────────────────────────────┤
│                   API Client (axios / apiClient)                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP/JSON
┌────────────────────────────▼────────────────────────────────────────┐
│                        BACKEND (FastAPI)                             │
├─────────────────────────────────────────────────────────────────────┤
│  routers/analysis.py                                                 │
│    POST /analysis/positions       (existing)                         │
│    POST /analysis/time-series     (existing)                         │
│    POST /analysis/next-moves      (NEW)                              │
│    GET  /games/count              (existing)                         │
├─────────────────────────────────────────────────────────────────────┤
│  services/analysis_service.py                                        │
│    analyze()           get_time_series()    get_next_moves() (NEW)   │
│                                                                      │
│  services/import_service.py                                          │
│    _flush_batch()      MODIFY to populate move_san                   │
├─────────────────────────────────────────────────────────────────────┤
│  repositories/analysis_repository.py                                 │
│    query_all_results()  query_matching_games()  query_time_series()  │
│    query_next_moves()   (NEW)                                        │
├─────────────────────────────────────────────────────────────────────┤
│  models/game_position.py                                             │
│    ADD  move_san: Mapped[str | None]                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                         PostgreSQL                                   │
│                                                                      │
│  game_positions                                                      │
│    id, game_id, user_id, ply                                         │
│    full_hash, white_hash, black_hash                                 │
│    move_san  VARCHAR(10)   ← ADD (NULL at ply 0)                     │
│                                                                      │
│  Existing indexes:                                                   │
│    ix_gp_user_full_hash   (user_id, full_hash)                       │
│    ix_gp_user_white_hash  (user_id, white_hash)                      │
│    ix_gp_user_black_hash  (user_id, black_hash)                      │
│                                                                      │
│  New index:                                                          │
│    ix_gp_user_full_hash_move_san  (user_id, full_hash, move_san)     │
│    (covering index — eliminates heap fetch for next-moves GROUP BY)  │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `game_positions` table | Position fingerprints per half-move | ADD `move_san` column + covering index |
| `hashes_for_game()` in `zobrist.py` | Compute hashes for every ply | MODIFY to also return SAN per ply |
| `import_service._flush_batch()` | Build position rows for bulk insert | MODIFY to populate `move_san` |
| `analysis_repository` | DB queries for position lookups | ADD `query_next_moves()` |
| `analysis_service` | Orchestrate queries, compute WDL | ADD `get_next_moves()` |
| `analysis` router | HTTP surface for analysis | ADD `POST /analysis/next-moves` |
| `OpeningsPage` | Openings analysis tab | RESTRUCTURE with board + sub-tabs |
| `DashboardPage` | Position filter + game list | REMOVE import modal, link to `/import` |
| `ImportPage` (new) | Dedicated import / sync page | NEW |
| `MoveExplorerTab` (new) | Next-move table with W/D/L | NEW |
| `GamesTab` (new) | Game list extracted from Dashboard | NEW |
| `StatisticsTab` (new) | Charts extracted from current Openings | NEW |
| `useNextMoves` (new) | TanStack Query wrapper | NEW |

## Recommended Project Structure

### Backend additions

```
app/
├── models/
│   └── game_position.py        # ADD move_san: Mapped[str | None]
├── services/
│   ├── zobrist.py              # MODIFY hashes_for_game() → 5-tuples
│   ├── import_service.py       # MODIFY _flush_batch() — unpack move_san
│   └── analysis_service.py     # ADD get_next_moves()
├── repositories/
│   └── analysis_repository.py  # ADD query_next_moves()
├── routers/
│   └── analysis.py             # ADD POST /analysis/next-moves
└── schemas/
    └── analysis.py             # ADD NextMovesRequest, NextMoveRecord, NextMovesResponse
```

### Frontend additions

```
frontend/src/
├── pages/
│   ├── Openings.tsx            # RESTRUCTURE with Tabs + sub-tab routing
│   └── Import.tsx              # NEW — full page for import/sync
├── components/
│   └── openings/
│       ├── MoveExplorerTab.tsx  # NEW — next-move table with W/D/L per move
│       ├── GamesTab.tsx         # NEW — game list (logic from Dashboard)
│       └── StatisticsTab.tsx    # NEW — charts from current OpeningsPage
├── hooks/
│   └── useNextMoves.ts          # NEW — TanStack Query for /analysis/next-moves
└── types/
    └── api.ts                   # ADD NextMovesRequest, NextMoveRecord, NextMovesResponse
```

## Architectural Patterns

### Pattern 1: move_san stored at the origin position ply

**What:** The `move_san` column on a `game_positions` row holds the SAN of the move played FROM that position (ply N → ply N+1). The initial position (ply 0) has `move_san = NULL` — no move was played to reach the starting position.

**Why this is correct for move explorer:** The query is "what moves were played FROM position X?" That means: `WHERE full_hash = hash(X) AND move_san IS NOT NULL GROUP BY move_san`. Each matching row's `move_san` is exactly the move played from position X. If move_san were stored on the destination row, you would need to know destination hashes in advance — a circular dependency.

**Trade-offs:** move_san is derivable from PGN + ply at any time, so this is storage redundancy (~4-6 bytes per row). At 200k position rows per user, overhead is negligible. Eliminates costly PGN re-parsing at query time.

**Example:**
```
ply=0  full_hash=<start>   move_san=NULL     (initial position; no move yet)
ply=1  full_hash=<after e4> move_san="e5"    (White played e4 to reach this pos)
ply=2  full_hash=<after e5> move_san="Nf3"   (Black played e5 to reach this pos)
```

When querying moves FROM the starting position: `WHERE full_hash = <start> → move_san = "e4"` (from the ply=0 row... wait — ply=0 has `move_san=NULL`). Correction: the ply=0 row has `move_san=NULL`. The ply=1 row's `full_hash` is hash(after e4). The move "e4" was played at ply=0 so `move_san="e4"` belongs on the ply=0 row. Clarification:

```
ply=0  full_hash=<start>     move_san="e4"   (the move played FROM the start position)
ply=1  full_hash=<after e4>  move_san="e5"   (the move played FROM after-e4 position)
ply=2  full_hash=<after e5>  move_san="Nf3"
...
ply=N  full_hash=<last pos>  move_san=NULL   (final position; no move played from it)
```

So move_san is NULL on the LAST position in a game (the game-ending position), not on ply 0.

**Implementation in `hashes_for_game()`:**
```python
# ply 0 — initial position; capture the move that will be played from it
board = game.board()
moves = list(game.mainline_moves())

for ply, move in enumerate(moves):
    move_san = board.san(move)      # SAN before push — while move is legal on this board
    wh, bh, fh = compute_hashes(board)
    results.append((ply, wh, bh, fh, move_san))  # ply=0 gets move_san of first move
    board.push(move)

# Final position (no move played from it)
wh, bh, fh = compute_hashes(board)
results.append((len(moves), wh, bh, fh, None))
```

### Pattern 2: Composite covering index for next-move aggregation

**What:** The existing `ix_gp_user_full_hash` index (on `user_id, full_hash`) already covers the WHERE clause for next-moves queries. Adding `move_san` as a third column creates a covering index that eliminates heap lookups for the GROUP BY.

**Recommended index:**
```python
# In game_position.py __table_args__:
Index("ix_gp_user_full_hash_move_san", "user_id", "full_hash", "move_san"),
```

This is the only new index needed. The same index serves: `WHERE user_id = :uid AND full_hash = :h AND move_san IS NOT NULL GROUP BY move_san`.

The same white_hash / black_hash patterns are covered by existing indexes — no additional indexes needed for white/black match_side filtering in next-moves.

**No standalone index on `move_san`** — it is never queried in isolation.

### Pattern 3: next-moves query — GROUP BY in repository, WDL in service

**What:** Single aggregating SQL query in the repository. Service computes loss count and percentages. This mirrors the existing `query_all_results` → `analyze()` separation.

**SQLAlchemy query structure:**
```python
async def query_next_moves(
    session: AsyncSession,
    user_id: int,
    hash_column: Any,
    target_hash: int,
    # ... same filter params as _build_base_query
) -> list[tuple]:
    """Return (move_san, game_count, wins, draws) per move from target position."""
    wins_expr = func.sum(
        case(
            (and_(Game.result == "1-0", Game.user_color == "white"), 1),
            (and_(Game.result == "0-1", Game.user_color == "black"), 1),
            else_=0,
        )
    ).label("wins")
    draws_expr = func.sum(
        case((Game.result == "1/2-1/2", 1), else_=0)
    ).label("draws")

    stmt = (
        select(
            GamePosition.move_san,
            func.count(Game.id.distinct()).label("game_count"),
            wins_expr,
            draws_expr,
        )
        .join(Game, Game.id == GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            hash_column == target_hash,
            GamePosition.move_san.isnot(None),
        )
        .group_by(GamePosition.move_san)
        .order_by(func.count(Game.id.distinct()).desc())
    )
    # ... apply same optional filters (time_control, platform, rated, etc.)
    rows = await session.execute(stmt)
    return list(rows.all())
```

**DISTINCT on game_id** (`func.count(Game.id.distinct())`) is required. A transposition can cause the same position to appear at multiple plies in the same game, which would double-count that game without DISTINCT.

### Pattern 4: Sub-tabs with shared filter state in OpeningsPage

**What:** `OpeningsPage` owns both the chess board state (position, move history) and the filter state. These are passed as props to three sub-tabs. The `Tabs` component from `@/components/ui/tabs` is already installed and used throughout the project.

**Tab values:** `"explorer"`, `"games"`, `"statistics"`

**Query gating:** Each sub-tab enables its query only when it is the active tab. This prevents three simultaneous requests on page load.

```tsx
// MoveExplorerTab receives: { position_hash, match_side, filters }
// GamesTab receives: { position_hash, match_side, filters }
// StatisticsTab receives: { filters } (bookmarks-based, no board position needed)
```

**Filter state ownership:** `OpeningsPage` holds a single `filters` state object (same shape as `FilterState` from `FilterPanel`). The existing `FilterPanel` component is reused as a shared sidebar. Filters are NOT duplicated into each sub-tab — they flow down as read-only props.

### Pattern 5: ImportPage as a lifted ImportModal

**What:** The `ImportModal` component contains all the import logic (first-time view, sync view, edit mode, add-platform flow). For the dedicated `ImportPage`, this content is rendered as a full page rather than inside a `Dialog` wrapper.

**Implementation approach:** Either:
1. Extract `ImportModal`'s body into a separate `ImportForm` component used by both modal and page.
2. Or simply render the existing `ImportModal` content directly in `ImportPage` without the `Dialog` wrapper.

Option 2 is simpler — lift the inner `<form>` and sync view JSX into a standalone page component. The `ImportModal` can be removed entirely or kept temporarily while `DashboardPage` still references it (remove as part of the UI restructuring).

**DashboardPage change:** The import button (`btn-import`) changes from `onClick={() => setImportOpen(true)}` to a React Router `<Link to="/import">`. Remove `ImportModal` and `ImportProgress` from `DashboardPage` — these move to `ImportPage`.

## Data Flow

### Next-Moves Request Flow

```
User navigates board to position X in MoveExplorerTab
    ↓
MoveExplorerTab calls useNextMoves({ hash, match_side, ...filters })
    ↓
TanStack Query (enabled when tab is active):
    POST /analysis/next-moves
    { full_hash, match_side, time_control, platform, rated, opponent_type, recency, color }
    ↓
analysis router → analysis_service.get_next_moves()
    ↓
analysis_repository.query_next_moves()
    SELECT move_san, COUNT(DISTINCT g.id) AS game_count, SUM(wins), SUM(draws)
    FROM game_positions gp JOIN games g ON g.id = gp.game_id
    WHERE gp.user_id = :uid AND gp.full_hash = :hash AND gp.move_san IS NOT NULL
    GROUP BY move_san ORDER BY game_count DESC
    ↓
Service: loss = game_count - wins - draws; compute percentages
    ↓
NextMovesResponse: [{ move_san, game_count, wins, draws, losses, win_pct, ... }]
    ↓
MoveExplorerTab renders table: Move | Games | W% | D% | L%
Click on a row → board advances that move → new hash → new next-moves fetch
```

### Import Pipeline Change (move_san population)

```
_flush_batch() calls hashes_for_game(pgn)
    ↓
hashes_for_game() returns 5-tuples: (ply, wh, bh, fh, move_san)
    ↓
position_rows dicts include "move_san" key
    ↓
game_repository.bulk_insert_positions() writes move_san to DB
    (no change to bulk_insert_positions beyond the extra column in dicts)
```

### UI Routing Change

```
Current:
  /             DashboardPage  (board + game list + import modal)
  /openings     OpeningsPage   (bookmarks + WDL charts + win-rate chart)

After v1.1:
  /             DashboardPage  (board + game list; import button links to /import)
  /openings     OpeningsPage   (board + shared filters + sub-tabs)
                   sub-tab: explorer  → MoveExplorerTab
                   sub-tab: games     → GamesTab
                   sub-tab: statistics → StatisticsTab
  /import       ImportPage     (full-page import/sync UI)
```

### Filter and Board State in Restructured OpeningsPage

```
OpeningsPage
  │  owns: filters state, chess board state (position, move history)
  │
  ├─► ChessBoard + MoveList + BoardControls  (interactive board — same as Dashboard)
  │
  ├─► FilterPanel  (existing component, receives filters + onChange)
  │
  └─► <Tabs>
        ├─► MoveExplorerTab (props: hash, match_side, filters)
        │     useNextMoves({ hash, match_side, ...filters }, enabled: activeTab==='explorer')
        │
        ├─► GamesTab (props: hash, match_side, filters)
        │     useAnalysis() mutation (same as Dashboard's handleAnalyze)
        │
        └─► StatisticsTab (props: filters)
              useTimeSeries() (same as current OpeningsPage)
```

## New vs. Modified: Explicit Accounting

### New

| Item | Type | Location |
|------|------|----------|
| `move_san` column | DB column | `game_positions` table |
| `ix_gp_user_full_hash_move_san` | DB index | `game_positions` |
| `query_next_moves()` | Repository function | `analysis_repository.py` |
| `get_next_moves()` | Service function | `analysis_service.py` |
| `NextMovesRequest`, `NextMoveRecord`, `NextMovesResponse` | Pydantic schemas | `schemas/analysis.py` |
| `POST /analysis/next-moves` | API endpoint | `analysis` router |
| `useNextMoves` | React hook | `hooks/useNextMoves.ts` |
| `MoveExplorerTab` | React component | `components/openings/MoveExplorerTab.tsx` |
| `GamesTab` | React component | `components/openings/GamesTab.tsx` |
| `StatisticsTab` | React component | `components/openings/StatisticsTab.tsx` |
| `ImportPage` | React page | `pages/Import.tsx` |
| `/import` route + nav item | Router + nav | `App.tsx` |

### Modified

| Item | Change | Location |
|------|--------|----------|
| `hashes_for_game()` | Returns 5-tuples with `move_san` | `services/zobrist.py` |
| `import_service._flush_batch()` | Unpacks 5-tuples, adds `move_san` to position row dicts | `services/import_service.py` |
| `GamePosition` model | ADD `move_san: Mapped[str \| None]` | `models/game_position.py` |
| `OpeningsPage` | Restructure: add board, shared filters, Tabs container | `pages/Openings.tsx` |
| `App.tsx` | Add `/import` route and nav item | `App.tsx` |
| `DashboardPage` | Import button links to `/import`; remove ImportModal + ImportProgress | `pages/Dashboard.tsx` |

### Unchanged / Reused As-Is

| Item | Why unchanged |
|------|---------------|
| `_build_base_query()` | `query_next_moves()` mirrors its filter parameter pattern |
| Existing hash indexes | `ix_gp_user_full_hash` covers the WHERE for next-moves |
| `analysis_service.analyze()` | GamesTab reuses this endpoint unchanged |
| `useAnalysis` / `useGamesQuery` hooks | Reused by GamesTab as-is |
| `FilterPanel` component | Reused as shared filter sidebar in OpeningsPage |
| `ChessBoard`, `MoveList`, `BoardControls` | Reused in OpeningsPage (same as Dashboard) |

## Build Order (Dependency-Aware)

```
Step 1 — DB schema + import pipeline (blocks everything)
  1a. Add move_san to GamePosition model + covering index
  1b. Modify hashes_for_game() to return 5-tuples with move_san
  1c. Modify _flush_batch() to unpack 5-tuples and include move_san in position rows
  1d. DB wipe + fresh import to validate move_san populates correctly

Step 2 — Backend endpoint (blocks frontend next-moves)
  2a. Add Pydantic schemas: NextMovesRequest, NextMoveRecord, NextMovesResponse
  2b. Add query_next_moves() to analysis_repository.py
  2c. Add get_next_moves() to analysis_service.py
  2d. Add POST /analysis/next-moves to analysis router
  2e. Write test for query_next_moves() and get_next_moves()

Step 3 — Frontend: move explorer (depends on Step 2)
  3a. Add NextMovesRequest/Response types to types/api.ts
  3b. Add useNextMoves hook
  3c. Build MoveExplorerTab component

Step 4 — Frontend: UI restructuring (independent of Steps 2-3, can parallel)
  4a. Create ImportPage (lift ImportModal content into full page)
  4b. Add /import route to App.tsx, add Import to nav
  4c. Update DashboardPage: change import button to link, remove ImportModal
  4d. Create GamesTab (extract game list + analysis from Dashboard logic)
  4e. Create StatisticsTab (extract charts from current OpeningsPage)
  4f. Restructure OpeningsPage: add board state, shared FilterPanel, Tabs
  4g. Wire all three sub-tabs into OpeningsPage

Step 5 — Integration
  5a. Connect MoveExplorerTab into OpeningsPage (merge Steps 3 + 4)
  5b. End-to-end test: play moves → explorer shows next moves with WDL
```

## Anti-Patterns

### Anti-Pattern 1: Querying move_san without DISTINCT on game_id

**What people do:** `COUNT(*)` instead of `COUNT(DISTINCT g.id)` in the next-moves GROUP BY.

**Why it's wrong:** Transpositions cause the same position hash to appear at multiple plies in one game. Without DISTINCT, a single game contributes multiple rows and inflates counts. The existing `_build_base_query` already uses `.distinct(Game.id)` for this exact reason. The next-moves query must apply the same discipline.

**Do this instead:** `COUNT(DISTINCT g.id)` in the aggregation. Or use a subquery to deduplicate by game_id before grouping — but the DISTINCT aggregate is simpler and performs well.

### Anti-Pattern 2: Putting move_san on the destination position row

**What people do:** Attach move_san to the position row for the position REACHED by the move (ply N+1) instead of the position FROM which the move was played (ply N).

**Why it's wrong:** The move explorer query asks "what moves are available FROM position X?" This requires `WHERE full_hash = hash(X)` and reading `move_san` on those rows. If move_san were on destination rows, you would need to know destination hashes — which is the answer you are trying to find.

**Do this instead:** Store move_san on the row for the position FROM which the move was played. The final game position (no move played from it) has `move_san = NULL`.

### Anti-Pattern 3: Each sub-tab fires queries independently on mount

**What people do:** All three sub-tabs use `enabled: true` in their query hooks, triggering three DB queries simultaneously on page load.

**Why it's wrong:** Wasted DB hits, degraded load time, and potentially inconsistent intermediate states as tabs render with stale data.

**Do this instead:** Gate each query with `enabled: activeTab === 'explorer'` (or `'games'`, `'statistics'`). TanStack Query caches results — switching back to a previously active tab with unchanged filters is instant (no re-fetch unless `staleTime` has passed).

### Anti-Pattern 4: Duplicating filter state into sub-tabs

**What people do:** Each sub-tab manages its own copy of filter controls (time control, platform, rated, etc.).

**Why it's wrong:** Three sources of truth for the same filter state. Filter changes in one tab don't reflect in others. The existing Openings page already has inline filter widgets — multiplying them by 3 is confusing.

**Do this instead:** Filter state lives in `OpeningsPage`. The existing `FilterPanel` component is rendered once as a shared sidebar and passes state down via props. Sub-tabs receive `filters` as a read-only prop.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| chess.com API | `chesscom_client.py` — unchanged | move_san comes from PGN parsing, not the API |
| lichess API | `lichess_client.py` — unchanged | Same — PGN already fetched and stored |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `hashes_for_game()` → `_flush_batch()` | Return type extends from 4-tuple to 5-tuple | Single call site — update together |
| `analysis_repository` → `analysis_service` | New `query_next_moves()` mirrors `query_all_results()` pattern | Reuse `HASH_COLUMN_MAP` and filter helpers |
| `OpeningsPage` → sub-tabs | Props: `{ filters, position_hash, match_side }` | Sub-tabs are presentational; query logic lives in hooks |
| `ImportPage` / `DashboardPage` → import flow | `ImportPage` owns the import UI; Dashboard links to it | `ImportProgress` component may stay in Dashboard or move to a layout-level component |

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-10k games/user | Indexed GROUP BY is sub-10ms; no adjustments needed |
| 10k-100k games/user | Covering index `(user_id, full_hash, move_san)` eliminates heap fetches |
| 100k+ games/user | Consider materialised view for move aggregates if GROUP BY latency becomes noticeable (not expected for this user base) |

### Scaling Priorities

1. **First bottleneck:** next-moves GROUP BY on large `game_positions` tables — mitigated by the covering index added in this milestone.
2. **Second bottleneck:** GamesTab pagination in Openings reuses the existing optimised `query_matching_games()` path — no additional work needed.

## Sources

- Direct analysis of `app/models/game_position.py` — existing schema
- Direct analysis of `app/repositories/analysis_repository.py` — existing query patterns (DISTINCT, filter helpers, HASH_COLUMN_MAP)
- Direct analysis of `app/services/zobrist.py` — `hashes_for_game()` current return type
- Direct analysis of `app/services/import_service.py` — `_flush_batch()` position row construction
- Direct analysis of `frontend/src/pages/Openings.tsx` — existing filter state and chart components
- Direct analysis of `frontend/src/pages/Dashboard.tsx` — ImportModal usage, board state, game list
- Direct analysis of `frontend/src/App.tsx` — existing routes and nav items
- `.planning/PROJECT.md` — v1.1 scope and settled decisions (DB wipe confirmed)

---
*Architecture research for: Chessalytics v1.1 — Move Explorer + UI Restructuring*
*Researched: 2026-03-16*
