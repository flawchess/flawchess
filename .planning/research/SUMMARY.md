# Research Summary: Chessalytics

## Recommended Stack

- **Backend:** FastAPI 0.115.x with Uvicorn 0.30.x, Python 3.12, uv for package management
- **Frontend:** React 18.x + TypeScript + Vite 5.x; react-chessboard 4.x for the interactive board; chess.js 1.x for client-side move logic; TanStack Query 5.x for server state; Tailwind CSS 3.x
- **Database:** SQLite for local dev, PostgreSQL 16.x for production; SQLAlchemy 2.x (async engine) + Alembic for migrations
- **Key libraries:**
  - `python-chess 1.10.x` — PGN parsing, board state, FEN extraction, Zobrist hashing via `chess.polyglot`
  - `httpx 0.27.x` (AsyncClient) — all outbound API calls; never use `requests` or `berserk`
  - `asyncpg 0.29.x` / `aiosqlite 0.20.x` — async DB drivers
  - `pydantic 2.7.x` + `pydantic-settings` — request/response validation and config

---

## Core Architecture Decision

### Position Matching Strategy: Zobrist Hashes

Every position in every game is precomputed at import time and stored as three 64-bit integer hashes in a `game_positions` table:

- `full_hash` — standard Zobrist hash of both sides (`chess.polyglot.zobrist_hash(board)`)
- `white_hash` — Zobrist hash of white pieces only (black pieces removed from a board copy before hashing)
- `black_hash` — Zobrist hash of black pieces only (white pieces removed before hashing)

These are indexed integer columns. Position queries are equality lookups on indexed integers — no string comparison, no table scans, no FEN `LIKE` patterns.

The two matching modes map directly to query variants:
- **Any-order match:** `WHERE white_hash = :target AND user_id = :uid` (no ply constraint)
- **Strict move-order match:** same query plus `AND ply = :target_ply` — extremely selective

### White-only / Black-only Filtering at the DB Level

Because `white_hash` and `black_hash` are stored independently, side filtering is simply a matter of which column is queried:

| User filter | Query predicate |
|---|---|
| My white pieces only | `white_hash = :target_white_hash` |
| My black pieces only | `black_hash = :target_black_hash` |
| Both sides exact | `full_hash = :target_full_hash` |

This is the key architectural enabler: the "own pieces only" feature is a free consequence of storing hashes per side, not a separate algorithm.

The `game_positions` table also carries a denormalized `user_id` column (duplicated from `games`) so the primary query `WHERE user_id = ? AND white_hash = ?` hits a compound index without a join to filter by user.

---

## Table Stakes Features

- Import games from chess.com and lichess by username (no auth required for public games)
- Incremental re-sync: fetch only games since the last stored timestamp per user+platform
- Store full PGN and metadata (time control, rated flag, result, opponent, color played, platform URL)
- Precompute and store position hashes for every half-move at import time
- Interactive chess board for position input (playing moves to define a target position)
- Win/draw/loss rate display for all matching games
- Matching games list: opponent name, result, date, time control, link to source platform
- Filter by color (white / black / both), time control (bullet / blitz / rapid / classical), rated vs casual, and recency
- User accounts with data isolation (each user sees only their own games)
- Import progress feedback; clear error states for invalid usernames or API failures

---

## Key Differentiators

- **Position-based grouping, not opening names.** Lichess and chess.com group by ECO code or opening name. Chessalytics groups by actual board state — the same piece placement reached via different move orders or misnamed by the platform is counted together.
- **Own-pieces-only filtering.** No existing consumer tool lets a player define a position using only their own pieces and ignore what the opponent played. This is the stated core value of the product.
- **Personal game database.** Lichess Explorer queries global databases; chess.com Insights gives aggregate stats but not position-level queries. Chessalytics is the only tool answering "what is MY personal win rate from this exact pawn structure?"
- **Transparent, composable filters.** All filter dimensions are exposed simultaneously; users see how each filter affects the result count.

---

## Critical Pitfalls to Avoid

Ranked by severity (highest first):

1. **Schema mistakes in the positions table.** Not storing `user_id` on `game_positions` forces a join on every query; storing hashes as strings instead of 64-bit integers kills index performance; omitting the hash columns entirely makes the core feature impossible without a full rewrite. This is the highest-leverage architectural decision — get it right before storing any data.

2. **Synchronous import blocking the event loop.** An active player may have 50,000+ games. A synchronous import in a FastAPI request handler will time out and freeze the server. Make import async from day one using FastAPI `BackgroundTasks` (acceptable for v1) or a task queue. The import endpoint returns a job ID immediately; the client polls for status.

3. **FEN gotchas in position matching.** Full FEN encodes castling rights and en passant, which means visually identical positions can have different FEN strings. Always use piece-placement-only for matching. The Zobrist approach sidesteps this naturally since hashes are computed from the board object, not the FEN string.

4. **PGN parsing failures crashing the batch.** Chess.com returns multi-game PGN blobs; malformed PGNs, null moves, Chess960 games, and non-UTF-8 player names will crash naive parsers. Wrap every per-game parse in try/except, log failures with context, and continue. Filter variant games out before parsing.

5. **Chess.com rate limiting with no backoff.** The chess.com API returns 429s aggressively. Fetch monthly archives sequentially with 100–300ms delays; cache raw JSON before parsing; set a descriptive `User-Agent` header.

6. **Re-sync creating duplicate game records.** Without a unique constraint on `(platform, platform_game_id)` in the games table, re-sync will duplicate games and corrupt win rate statistics. This constraint must be in the initial schema with `INSERT ... ON CONFLICT DO NOTHING` semantics.

7. **UX confusion between match modes.** Users will not understand "strict move order" vs "any position." Avoid jargon; use plain language ("I played these moves in this exact order" vs "I reached this exact position"). Make the distinction prominent, not buried. Default to any-order matching.

---

## Suggested Build Order

### Phase 1 — Data Foundation
- Database schema with all tables and indexes (including denormalized `user_id` on `game_positions`, `platform_game_id` unique constraint, integer hash columns)
- Position hash module: `compute_position_hashes(board)` returning `(white_hash, black_hash, full_hash)` — pure Python, fully unit-tested before any other work
- PGN parser + position indexer: takes a PGN string, yields game metadata + list of position records; handles multi-game strings, variant filtering, per-game error isolation
- chess.com API client: monthly archive fetch, rate-limit backoff, raw JSON caching
- lichess API client: NDJSON streaming, millisecond timestamps, `since` parameter for incremental sync

### Phase 2 — Import Pipeline
- Import service: orchestrates dedup, parsing, and batch DB writes as a background task
- Sync state tracking: last-synced marker per user+platform
- Import progress endpoint: allows UI to poll job status
- Data normalization layer: maps both platforms' time control formats, result strings, and metadata to the unified internal schema

### Phase 3 — Analysis Engine
- Analysis query builder: selects the right hash column and ply filter based on `match_side` and `move_order` parameters
- Analysis API endpoint (`POST /api/v1/analysis`): stable contract defined before frontend work begins; returns `total_games`, match counts, and per-game results with `platform_url` and `matched_at_ply`; internal hashes never exposed

### Phase 4 — Frontend
- Interactive chessboard component (react-chessboard + chess.js): exports both FEN and move sequence on submit
- Filter controls and results display (W/D/L counts, matching games table with external links)
- Empty state handling: always show denominator ("0 of 847 blitz games matched"), suggest filter relaxation when result is zero

### Phase 5 — Auth and Multi-User
- User accounts and session management (FastAPI-Users or simple JWT)
- Row-level data isolation (all queries scoped to `user_id`)

---

## Open Questions

- **Auth approach:** FastAPI-Users vs. a minimal custom JWT implementation. FastAPI-Users adds a dependency but provides email verification, password reset, and OAuth out of the box. Decision needed before Phase 5 but can be deferred until the single-user flow is validated.
- **Background task queue for v1:** FastAPI `BackgroundTasks` has no persistence across restarts and no retry. For a single-server v1 this is acceptable, but if the server restarts mid-import the job is silently lost. Decide whether to accept this or add Redis + a lightweight queue (arq, rq) before launch.
- **"Strict move order" semantics:** Does "strict" mean the full game move sequence matches the prefix, or only the user's moves (ignoring opponent moves) match? These produce different results for transpositions. The definition must be locked before the search algorithm is implemented.
- **Castling rights and en passant in match results:** The Zobrist hash ignores these (consistent with the current design), which means two visually identical positions with different castling rights will match. This is probably the desired behavior, but it should be documented and confirmed.
- **SQLite ceiling:** SQLite handles the use case well up to ~50k games per user. Above that, Postgres is needed. The current plan (SQLite local, Postgres production) is correct, but the switchover threshold and migration path should be defined before any users with very large game counts are onboarded.
- **lichess OAuth token:** Without a token, lichess limits public endpoints to ~15–20 req/min, which makes large initial imports slow. Prompting users for an optional personal access token during onboarding would significantly improve the import experience but adds an onboarding step.

---

*Synthesized: 2026-03-11. Source documents: PROJECT.md, STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md*
