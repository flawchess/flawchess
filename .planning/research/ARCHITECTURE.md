# Architecture Research

**Domain:** Per-position metadata and endgame analytics for an existing chess analytics platform
**Researched:** 2026-03-23
**Confidence:** HIGH — based on direct codebase inspection of all affected modules

---

## Current Architecture (as-built)

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Frontend (React 19 + TS)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ OpeningsPage│  │ GlobalStats  │  │ [NEW] EndgamesPage       │ │
│  │  /openings  │  │  /stats      │  │  /endgames               │ │
│  └──────┬──────┘  └──────┬───────┘  └────────────┬─────────────┘ │
│         │                │                        │               │
│  TanStack Query hooks -- useAnalysis, useEndgames (new)           │
│  api/client.ts + types/api.ts + types/endgames.ts (new)           │
└─────────────────────────┬────────────────────────┴───────────────┘
                          │ HTTP (JSON + JWT Bearer)
┌─────────────────────────▼────────────────────────────────────────┐
│                  FastAPI Routers (HTTP layer only)                 │
│  routers/analysis.py   routers/stats.py  routers/endgames.py(new)│
└─────────────────────────┬────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────┐
│                    Services (business logic)                       │
│  analysis_service.py   stats_service.py  endgames_service.py(new)│
│                   import_service.py (MODIFIED)                    │
│                   position_classifier.py (NEW)                    │
└────────────┬────────────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────────┐
│                   Repositories (DB access)                      │
│  analysis_repository.py  stats_repository.py                   │
│  game_repository.py (MODIFIED -- new position_rows columns)    │
│  endgames_repository.py (NEW)                                  │
└────────────┬───────────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────────┐
│               PostgreSQL 18 (asyncpg via SQLAlchemy 2.x)        │
│  games          game_positions (MODIFIED -- new columns)        │
│  users          import_jobs                                     │
│  [optional: game_engine_analysis NEW table]                     │
└────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Changes

### Decision: Extend `game_positions` vs. New Table

**Recommendation: Add new columns directly to `game_positions`.**

Rationale:
- All new data (game_phase, material_signature, endgame_class) is computed once per position at import time and never changes. It is not a separate concern — it is part of the position descriptor.
- A JOIN from a separate table on every endgame query would be expensive: `game_positions` is already the largest table (avg 80 rows per game). A separate `position_metadata` table would double the join cost for all endgame queries.
- `ALTER TABLE ADD COLUMN DEFAULT NULL` is a metadata-only operation in PostgreSQL 11+ and does not rewrite rows. Adding 4-5 nullable columns to an existing large table is instantaneous.
- The new columns are nullable, so backfill can proceed independently of new imports; both old and new rows are in the same table.

**Reject: Separate `position_metadata` table.** Only warranted if metadata had a different write pattern (e.g., updated post-import). Here it is computed once and never updated.

### New Columns on `game_positions`

```sql
-- Phase: 'opening' | 'middlegame' | 'endgame'
game_phase        VARCHAR(12)   NULL

-- Canonical material string sorted by piece type, e.g. 'KQRBNPkqrbnp' or 'KRPkr'
-- Uppercase = white pieces, lowercase = black. NULL until backfilled.
material_signature VARCHAR(32)  NULL

-- Signed centipawn material imbalance from user's perspective:
-- positive = user is up material, negative = down
-- NULL until backfilled. Based on standard piece values (Q=9,R=5,B=3,N=3,P=1).
material_imbalance SMALLINT     NULL

-- Endgame classification; NULL when game_phase != 'endgame'
-- Examples: 'rook', 'queen', 'minor_piece', 'pawn', 'queen_vs_rook', etc.
endgame_class     VARCHAR(30)   NULL
```

**Note on `material_signature` design:** Store as a compact canonical string (sorted piece characters), not a hash. Strings like `'KRPkr'` are human-readable, debuggable, and support LIKE/substring queries if needed later. Length 32 covers all practical positions (max ~16 pieces). Index only when needed for endgame queries (see Index section below).

### Engine Analysis Data

**Recommendation: New separate table `game_engine_analysis`.**

Unlike position metadata (per-ply, computed from board state), engine analysis is per-game, externally sourced, and only available for a subset of games. Putting it in `games` would add many nullable columns that are always NULL for non-analyzed games. A separate table avoids that column pollution and matches the natural 0..1 relationship.

```sql
CREATE TABLE game_engine_analysis (
    id              BIGINT PRIMARY KEY,
    game_id         BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    user_id         BIGINT NOT NULL,          -- denormalized for query perf
    source          VARCHAR(20) NOT NULL,     -- 'chess.com' | 'lichess'
    white_accuracy  FLOAT NULL,               -- overall accuracy % (0-100)
    black_accuracy  FLOAT NULL,
    user_accuracy   FLOAT NULL,               -- derived: white or black accuracy per user_color
    -- Future: per-move eval array could be stored as JSONB if needed
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(game_id)
);
CREATE INDEX ix_gea_user_id ON game_engine_analysis (user_id);
```

**API availability reality:**
- **chess.com**: `accuracies.white` and `accuracies.black` (float) are returned in the game JSON only when previously computed. No per-move eval in the public API.
- **lichess**: `accuracy` and `acpl` (average centipawn loss) are available per-player in the JSON export when `accuracy=true` parameter is used AND the game has been analyzed. Bulk exports (`/api/games/user`) do NOT include analysis data -- only individual game exports do.

**Consequence for import design:** Engine analysis data must be fetched as a separate optional pass, not inline with the main import. Do not attempt to fetch per-game analysis during the main import loop -- the extra per-game HTTP calls would multiply import time by 10-100x and risk rate bans. Treat as a separate "enrich analyzed games" job, or skip entirely for v1.5 and implement as a follow-on feature.

---

## Backfill Strategy

### The Problem

All existing `game_positions` rows have NULL for the new columns. Users may have thousands of games imported. The production server has 3.7 GB RAM and was OOM-killed on large batch inserts.

### Recommendation: Alembic Migration + Background Task Backfill

**Step 1: Alembic migration** -- Add the nullable columns. This is instant (PostgreSQL metadata-only operation). No data is touched. Deploy runs this automatically.

**Step 2: Background backfill task** -- A new `backfill_service.py` runs position classification for all existing games. Works from the stored PGN in `games` -- no re-download needed.

```
Backfill approach:
1. SELECT g.id, g.pgn FROM games g
   JOIN game_positions gp ON gp.game_id = g.id
   WHERE gp.game_phase IS NULL
   GROUP BY g.id
   LIMIT 100  -- process 100 games per batch
2. For each game: re-parse PGN, classify each position, batch UPDATE game_positions
3. Commit, sleep briefly (asyncio.sleep(0) to yield), repeat
4. Partial index on game_positions WHERE game_phase IS NULL
   allows efficient "find unbackfilled games" scans
```

**Key constraints:**
- Never rewrite position rows from scratch -- UPDATE only the new columns to preserve existing hashes.
- Process in game-level batches (100 games = ~8,000 position rows per UPDATE batch). This stays well under OOM limits.
- The backfill runs as a low-priority asyncio task with `asyncio.sleep(0)` yields between batches so it does not block the API.
- Partial index `CREATE INDEX CONCURRENTLY ix_gp_game_phase_null ON game_positions (game_id) WHERE game_phase IS NULL` lets the backfill query find unprocessed rows efficiently. Drop it after backfill completes.
- Do NOT re-download games from chess.com/lichess. PGN is stored in `games.pgn` -- compute everything from that.

**Alternative rejected: Full reimport (wipe + re-import all games).** Rejected because: users lose their import history, import takes hours for large libraries, and the server RAM constraint makes large batch imports risky. The backfill approach is safe and incremental.

---

## New Component: `position_classifier.py`

This is the core new service module. It computes game_phase, material_signature, material_imbalance, and endgame_class from a `chess.Board` object.

### Design

```python
# services/position_classifier.py

from dataclasses import dataclass
import chess

PIECE_VALUES = {
    chess.QUEEN: 9,
    chess.ROOK: 5,
    chess.BISHOP: 3,
    chess.KNIGHT: 3,
    chess.PAWN: 1,
    chess.KING: 0,
}

@dataclass
class PositionMetadata:
    game_phase: str            # 'opening' | 'middlegame' | 'endgame'
    material_signature: str    # e.g. 'KQRBBNPPPkqrbbnnppp'
    material_imbalance: int    # centipawn material delta from user perspective
    endgame_class: str | None  # None unless game_phase == 'endgame'
```

**Game phase algorithm (material-based):**

python-chess provides `board.pieces(piece_type, color)` which returns a SquareSet. Material count is a loop over piece types. A practical threshold based on non-pawn, non-king material:

```
endgame threshold:  total non-pawn pieces (both sides, excluding kings) <= 6
opening heuristic:  ply < OPENING_PLY_THRESHOLD (e.g., 20) AND non-pawn material above endgame threshold
middlegame:         everything in between
```

The exact thresholds are a tunable constant in `position_classifier.py`, not magic numbers scattered through the code.

**Material signature encoding:**

Canonical string: uppercase = white pieces, lowercase = black, sorted by piece type (K first, then Q, R, B, N, P). Example: `KQRBNPPkqrbnpp`. This is compact, human-readable, and directly queryable with equality.

**Endgame classification:**

Classify by dominant piece types once `game_phase == 'endgame'`:
- Both queens present: `'queen'`
- No queens, rooks present: `'rook'` (or `'rook_minor'` if minor pieces also present)
- No queens, no rooks, bishops only: `'bishop'`
- No queens, no rooks, knights only: `'knight'`
- No queens, no rooks, mixed minor: `'minor_piece'`
- Pawns only (K+P vs K+P or K vs K+P): `'pawn'`
- Queen vs Rook: `'queen_vs_rook'`

---

## Import Pipeline Modifications

### Where Classification Plugs In

The classification step fits cleanly into the existing `hashes_for_game` function in `zobrist.py`. The board is already constructed at each ply for Zobrist hash computation. Classification calls `classify_position(board, user_color)` at the same loop iteration -- zero extra PGN parses.

**Current `hashes_for_game` output tuple:**
```
(ply, white_hash, black_hash, full_hash, move_san, clock_seconds)
```

**Extended tuple (v1.5):**
```
(ply, white_hash, black_hash, full_hash, move_san, clock_seconds,
 game_phase, material_signature, material_imbalance, endgame_class)
```

The `position_rows` dict in `_flush_batch` gains the four new fields. The `bulk_insert_positions` in `game_repository.py` automatically includes them since it does a bulk INSERT of the dict.

**Impact on batch size:** The `bulk_insert_positions` chunk_size calculation `32767 / 8 = 4095` must be updated to `32767 / 12 = 2730` (or 2700 for safety) when the column count increases from 8 to 12.

---

## New Feature: Endgames Tab

### Backend

**New files:**
- `app/routers/endgames.py` -- HTTP layer, auth, request parsing
- `app/services/endgames_service.py` -- business logic (W/D/L aggregation, phase stats)
- `app/repositories/endgames_repository.py` -- SQL queries against game_positions + games
- `app/schemas/endgames.py` -- Pydantic request/response models

**Primary API endpoint:**

```
POST /endgames/stats
Body: EndgamesRequest (filters: time_control, platform, rated, color, recency,
                        endgame_class, material_signature)
Response: EndgamesStatsResponse
```

The endgames repository core query:
```sql
SELECT
    gp.endgame_class,
    g.result,
    g.user_color,
    COUNT(DISTINCT g.id)
FROM game_positions gp
JOIN games g ON g.id = gp.game_id
WHERE gp.user_id = :user_id
  AND gp.game_phase = 'endgame'
  AND gp.endgame_class IS NOT NULL
  -- optional: AND gp.endgame_class = :endgame_class
  -- + standard game filters (time_control, color, recency, etc.)
GROUP BY gp.endgame_class, g.result, g.user_color
```

Note: `COUNT(DISTINCT g.id)` prevents transposition double-counting (same pattern as existing analysis queries -- a game entering a rook endgame contributes ~50 position rows all with `endgame_class='rook'`).

**Conversion/recovery stats query:**

```sql
SELECT
    gp.game_phase,
    SIGN(gp.material_imbalance) AS material_side,
    g.result,
    g.user_color,
    COUNT(DISTINCT g.id)
FROM game_positions gp
JOIN games g ON g.id = gp.game_id
WHERE gp.user_id = :user_id
  AND gp.material_imbalance != 0
  -- + standard filters
GROUP BY gp.game_phase, material_side, g.result, g.user_color
```

### Frontend

**New files:**
- `src/pages/Endgames.tsx` -- page wrapper, filter state
- `src/components/endgames/EndgamesStats.tsx` -- main stats display
- `src/components/endgames/EndgameTypeFilter.tsx` -- filter for rook/queen/minor/pawn endgames
- `src/components/endgames/MaterialPhaseStat.tsx` -- conversion/recovery breakdown
- `src/hooks/useEndgames.ts` -- TanStack Query hook
- `src/types/endgames.ts` -- TypeScript mirrors of Pydantic schemas

**Integration with existing FilterPanel:** The existing `FilterPanel` handles time_control, platform, rated, color, recency. `EndgamesPage` reuses `FilterPanel` for those standard filters and adds `EndgameTypeFilter` for endgame class selection.

**Navigation:** Add `/endgames` route in `App.tsx` and add nav item to the bottom bar and "More" drawer on mobile, following the existing mobile nav pattern.

---

## Index Design for Material-Based Queries

### New Indexes Required

**1. Composite partial index for endgame queries (most important):**
```sql
CREATE INDEX ix_gp_user_endgame_class
ON game_positions (user_id, endgame_class)
WHERE endgame_class IS NOT NULL;
```
Partial index excludes the majority of rows (opening/middlegame positions). After backfill, roughly 20-30% of positions will have a non-NULL endgame_class.

**2. Index for game phase queries:**
```sql
CREATE INDEX ix_gp_user_game_phase
ON game_positions (user_id, game_phase)
WHERE game_phase IS NOT NULL;
```
Needed for phase-breakdown stats (conversion/recovery by phase).

**3. Temporary backfill index (drop after backfill completes):**
```sql
CREATE INDEX CONCURRENTLY ix_gp_game_phase_null
ON game_positions (game_id)
WHERE game_phase IS NULL;
```

**Indexes NOT needed yet:**
- `material_signature` alone: high cardinality, no confirmed query pattern requiring it as a leading column. Add `(user_id, material_signature)` only when a filter-by-material-configuration feature is added.
- `material_imbalance` alone: queries use `SIGN(material_imbalance)` grouping, not equality lookup. The phase index covers the scan.

### Existing Index Compatibility

The new columns do NOT change any existing query patterns. All existing indexes (`ix_gp_user_full_hash`, `ix_gp_user_white_hash`, `ix_gp_user_black_hash`, `ix_gp_user_full_hash_move_san`) are unaffected.

---

## Data Flow Diagrams

### Modified Import Pipeline

```
Platform API (chess.com / lichess)
    |
    v (normalized game dict)
import_service._flush_batch()
    |
    v
game_repository.bulk_insert_games()      --> games table
    |
    v (new game IDs + PGNs)
hashes_for_game(pgn)                     <-- zobrist.py (MODIFIED)
  + classify_position(board, user_color) <-- position_classifier.py (NEW)
    |
    v (ply, hashes, move_san, clock, game_phase, material_sig, imbalance, endgame_class)
game_repository.bulk_insert_positions()  --> game_positions (new columns populated)
```

### Endgames Tab Request Flow

```
User selects filters on /endgames
    |
    v
useEndgames() TanStack Query hook
    |
    v  POST /endgames/stats
EndgamesRouter.post_stats()
    |
    v
endgames_service.get_endgame_stats()
    |
    v
endgames_repository.query_endgame_wdl_by_class()
    |  (SQL: game_positions JOIN games, COUNT(DISTINCT game_id) GROUP BY endgame_class)
    ^
EndgamesStatsResponse --> EndgamesPage --> EndgamesStats component
```

### Backfill Pipeline

```
startup / admin trigger
    |
    v
backfill_service.run_backfill()  [asyncio.create_task, low priority]
    |
    v
SELECT g.id, g.pgn FROM games JOIN game_positions WHERE game_phase IS NULL
    (uses partial index ix_gp_game_phase_null)
    |
    v (batch of 100 games)
hashes_for_game(pgn)
  + classify_position(board)    <-- same function as import pipeline
    |
    v
UPDATE game_positions SET game_phase=..., material_signature=..., ...
WHERE game_id = :game_id
    |
    v (asyncio.sleep(0) yield, repeat until complete)
```

---

## Build Order (Phase Dependencies)

Hard sequential dependency chain:

```
1. position_classifier.py (new service, no deps)
        |
        v
2. Alembic migration: ADD COLUMN to game_positions (instantaneous, nullable)
        |
        v
3. zobrist.py + import_service.py modifications
   (wire classifier into hashes_for_game / _flush_batch)
        |
        v
4. backfill_service.py (reads PGN from games, updates game_positions)
        |
        v
5. New indexes (ix_gp_user_endgame_class, ix_gp_user_game_phase)
        |
        v
6. endgames_repository.py + endgames_service.py + schemas/endgames.py
        |
        v
7. routers/endgames.py (register in main.py)
        |
        v
8. Frontend: types/endgames.ts + hooks/useEndgames.ts
        |
        v
9. Frontend: EndgamesPage + components
        |
        v
10. Navigation: add /endgames route + nav items
```

Engine analysis (`game_engine_analysis` table) is independent and can be deferred or run in parallel with steps 6-10.

---

## Modified vs. New Components Summary

### Modified (existing files changed)

| File | Change |
|------|--------|
| `app/services/zobrist.py` | `hashes_for_game` returns 4 additional fields per ply |
| `app/services/import_service.py` | `_flush_batch` populates new position columns; pass `user_color` to classifier |
| `app/repositories/game_repository.py` | Update chunk_size: 8 cols -> 12 cols (32767/12=2730); new fields in position_rows |
| `app/models/game_position.py` | Add 4 new `Mapped` columns |
| `frontend/src/App.tsx` | Add `/endgames` route |
| `frontend/src/components/layout/` | Add Endgames nav item to bottom bar and More drawer |

### New (new files created)

| File | Purpose |
|------|---------|
| `app/services/position_classifier.py` | Game phase + material classification logic |
| `app/services/backfill_service.py` | Background backfill of existing positions |
| `app/repositories/endgames_repository.py` | SQL for endgame W/D/L aggregation |
| `app/services/endgames_service.py` | Endgame business logic |
| `app/routers/endgames.py` | HTTP endpoints for endgame tab |
| `app/schemas/endgames.py` | Pydantic request/response models |
| `frontend/src/pages/Endgames.tsx` | Endgames page |
| `frontend/src/components/endgames/` | Endgame-specific UI components |
| `frontend/src/hooks/useEndgames.ts` | TanStack Query hook |
| `frontend/src/types/endgames.ts` | TypeScript type mirrors |
| `alembic/versions/*_add_position_metadata_columns.py` | Alembic migration: 4 new columns |
| `alembic/versions/*_add_game_engine_analysis_table.py` | Optional: engine analysis table |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Re-downloading Games for Backfill

**What it looks like:** Triggering a new import job to populate the new columns.
**Why it's wrong:** Forces users to wait hours for a re-import, risks rate-limit bans, wastes API quota. PGN is already in `games.pgn`.
**Do this instead:** Backfill by reading `games.pgn` directly from the DB. All classification is pure computation.

### Anti-Pattern 2: Fetching Engine Analysis Inline with Import

**What it looks like:** Adding an extra HTTP call per game inside `_flush_batch` to fetch accuracy scores.
**Why it's wrong:** Multiplies import time by 10-100x. chess.com only returns accuracy for analyzed games anyway. Lichess bulk export omits analysis data entirely -- only individual game export (`accuracy=true`) includes it.
**Do this instead:** Implement engine analysis as a separate background enrichment task, or defer to a future milestone.

### Anti-Pattern 3: Counting Position Rows Instead of Distinct Games

**What it looks like:** `COUNT(*) FROM game_positions WHERE game_phase='endgame' GROUP BY endgame_class`.
**Why it's wrong:** A game that transitions to a rook endgame at ply 30 has ~50 rows all with `endgame_class='rook'`. Counting rows inflates stats by 50x.
**Do this instead:** Always `COUNT(DISTINCT game_id)`. One W/D/L outcome per unique game_id per endgame_class.

### Anti-Pattern 4: Serving Endgame Stats Before Backfill Completes

**What it looks like:** Showing endgame stats immediately after deployment while backfill is running.
**Why it's wrong:** Returns silently incomplete results -- lower game counts than actual for users whose games haven't been backfilled yet.
**Do this instead:** Track backfill completion per-user (flag in `users` table or count comparison). Show a progress indicator or "analyzing your games..." state during backfill.

### Anti-Pattern 5: Broad Index on `material_signature`

**What it looks like:** `CREATE INDEX ON game_positions (user_id, material_signature)` at the start.
**Why it's wrong:** `material_signature` has very high cardinality. An index on it uses significant space and slows INSERT/UPDATE during backfill and ongoing imports.
**Do this instead:** Only add a `material_signature` index when a specific filter-by-material-config query is confirmed. Start with the `endgame_class` partial index which covers the primary access pattern.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (small user base) | Backfill runs as inline asyncio task at startup; acceptable |
| ~100 users, ~50k games each | Backfill should be per-user, throttled, with asyncio.sleep yields between batches |
| ~1k+ users | Backfill moves to a dedicated background worker process separate from the API; current asyncio approach blocks event loop under heavy concurrent load |

**First bottleneck:** Endgame aggregation queries join `game_positions` (large) to `games`. With the partial index on `(user_id, endgame_class)`, performance should be acceptable for libraries up to ~100k games. Verify with `EXPLAIN ANALYZE` for any user with large imports before deploying.

---

## Sources

- Direct codebase inspection: `app/models/game_position.py`, `app/models/game.py`, `app/services/import_service.py`, `app/services/zobrist.py`, `app/repositories/analysis_repository.py`, `app/repositories/game_repository.py`, `frontend/src/types/api.ts`, `frontend/src/pages/Openings.tsx`
- [postgresql.org: Modifying Tables (ALTER TABLE ADD COLUMN performance)](https://www.postgresql.org/docs/current/ddl-alter.html) -- ADD COLUMN DEFAULT NULL is metadata-only in PG 11+
- [postgresql.org: Partial Indexes](https://www.postgresql.org/docs/current/indexes-partial.html)
- [python-chess Core docs](https://python-chess.readthedocs.io/en/latest/core.html) -- `board.pieces()`, `board.piece_map()` for material counting
- [chess.com Published-Data API](https://gist.github.com/andreij/0e3309200c0a6bb26308817a168203f3) -- `accuracies.white/black` optional field; no per-move eval
- [lichess forum: accuracy in API](https://lichess.org/forum/lichess-feedback/trying-to-find-accuracy-from-the-api) -- accuracy only in individual game export, not bulk export
- [Chessprogramming wiki: Game Phases](https://www.chessprogramming.org/Game_Phases) -- material-threshold phase detection standard

---
*Architecture research for: FlawChess v1.5 -- per-position metadata and endgame analytics*
*Researched: 2026-03-23*
