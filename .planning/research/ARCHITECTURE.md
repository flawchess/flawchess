# Architecture Research: Chessalytics

## System Components

### Backend API (FastAPI)
Handles all server-side logic. Responsibilities:
- User authentication and session management
- Game import orchestration (chess.com and lichess APIs)
- Position query processing
- Returning win/draw/loss statistics and matching game records

### Frontend (TBD: React or HTMX+Alpine)
- Interactive chessboard for position entry (e.g., chessboard.js or react-chessboard)
- Filter controls: side to match, move-order mode, time control, rated/casual, date range
- Results display: aggregate W/D/L rates plus individual game list with opponent names and external links

### Database
Stores users, games, and the position index. The position index is the critical component — everything else is standard CRUD. SQLite works at development scale and for single-server deployments; PostgreSQL is the right choice for multi-user production because of concurrent writes and better indexing options.

### Game Import Pipeline
An async background pipeline that runs on demand (triggered by the user requesting a sync):
1. Fetch game list from chess.com / lichess API for the user's username
2. Diff against already-stored games to find new ones
3. Parse each game's PGN to extract moves and metadata
4. Walk every position in the game, compute its position key, and write to the position index
5. Commit game record and all positions atomically

### Component Boundaries

```
User browser
    └─► Frontend (React / HTMX)
            ├─► GET /api/games/import          → triggers background sync
            ├─► GET /api/analysis?fen=...      → returns W/D/L stats + game list
            └─► GET /api/games/:id             → single game metadata + external link

FastAPI backend
    ├── routers/          HTTP layer only — no business logic
    ├── services/         Business logic (import, analysis)
    ├── repositories/     DB access (no SQL in services)
    └── background_tasks/ Import pipeline workers

Database (SQLite / PostgreSQL)
    ├── users
    ├── games
    ├── game_positions   (the position index — high write volume during import)
    └── sync_state       (tracks last sync per user/platform)
```

---

## Data Model

### Core Tables

**users**
```sql
id          INTEGER PRIMARY KEY
username    TEXT NOT NULL UNIQUE
created_at  TIMESTAMP
```

**games**
```sql
id              INTEGER PRIMARY KEY
user_id         INTEGER REFERENCES users(id)
platform        TEXT      -- 'chess_com' | 'lichess'
platform_id     TEXT      -- platform's own game ID (for dedup and external links)
pgn             TEXT      -- full PGN, stored for re-parsing without re-fetching
played_at       TIMESTAMP
time_control    TEXT      -- 'bullet' | 'blitz' | 'rapid' | 'classical'
rated           BOOLEAN
user_color      TEXT      -- 'white' | 'black'
opponent_name   TEXT
result          TEXT      -- 'win' | 'draw' | 'loss' (from user's perspective)
opening_eco     TEXT      -- from platform metadata, stored but not relied upon
```

**game_positions** (the hot table)
```sql
id              INTEGER PRIMARY KEY
game_id         INTEGER REFERENCES games(id)
ply             INTEGER   -- half-move number (0 = starting position, 1 = after White's first move)
white_hash      INTEGER   -- 64-bit hash of white piece placement only
black_hash      INTEGER   -- 64-bit hash of black piece placement only
full_hash       INTEGER   -- 64-bit hash of both sides (complete position)
-- Indexes: (white_hash), (black_hash), (full_hash), (game_id, ply)
```

### Position Representation

**FEN (Forsyth-Edwards Notation)** is the human-readable format but is a poor database key because string comparison is slow, it encodes side-to-move and castling rights (irrelevant for this use case), and it is large.

**The right storage key is a Zobrist hash** — a 64-bit integer computed by XOR-ing random bitstrings for each (square, piece-type, color) combination present on the board. python-chess computes this via `board.zobrist_hash()` (using the `chess.polyglot` module). For this application, the standard Zobrist hash is extended: two separate hashes are computed — one for white pieces only and one for black pieces only — enabling independent side filtering.

**Bitboards** are the internal engine representation (a 64-bit integer per piece type per color, one bit per square). python-chess uses bitboards internally; the application does not need to store them — only the derived hashes.

### Position Hash Computation Strategy

```python
import chess
import chess.polyglot

def compute_position_hashes(board: chess.Board):
    """
    Compute three 64-bit hashes:
    - full_hash:  both sides, standard Zobrist (built into python-chess)
    - white_hash: white pieces only, ignoring black pieces
    - black_hash: black pieces only, ignoring white pieces
    """
    # Full hash — python-chess provides this directly
    full_hash = chess.polyglot.zobrist_hash(board)

    # Side-isolated hashes: clone board, remove one side's pieces, hash
    white_only = board.copy()
    for sq in chess.SQUARES:
        piece = white_only.piece_at(sq)
        if piece and piece.color == chess.BLACK:
            white_only.remove_piece_at(sq)
    white_hash = chess.polyglot.zobrist_hash(white_only)

    black_only = board.copy()
    for sq in chess.SQUARES:
        piece = black_only.piece_at(sq)
        if piece and piece.color == chess.WHITE:
            black_only.remove_piece_at(sq)
    black_hash = chess.polyglot.zobrist_hash(black_only)

    return white_hash, black_hash, full_hash
```

This approach is fast (< 1 ms per position), produces deterministic keys, and enables independent side-filtering at query time with simple integer equality comparisons — which database indexes handle extremely efficiently.

### Indexing Strategy

The three hash columns on `game_positions` are the critical indexes:

```sql
CREATE INDEX idx_gp_white_hash ON game_positions(white_hash);
CREATE INDEX idx_gp_black_hash ON game_positions(black_hash);
CREATE INDEX idx_gp_full_hash  ON game_positions(full_hash);
```

A typical analysis query becomes:
```sql
-- "Show me all my games where my white pieces matched this position"
SELECT g.id, g.result, g.opponent_name, g.platform, g.platform_id, g.played_at, gp.ply
FROM game_positions gp
JOIN games g ON g.id = gp.game_id
WHERE gp.white_hash = :white_hash
  AND g.user_id = :user_id
  AND g.time_control IN ('blitz', 'rapid')   -- optional filter
  AND g.played_at >= :since                   -- optional filter
```

At thousands of games with ~40 positions each (~100k rows per user), this query resolves in milliseconds via the hash index.

---

## Position Matching Algorithms

### The Two Dimensions of Matching

Chessalytics has two orthogonal matching modes:

1. **Which side to match**: white pieces only, black pieces only, or both sides
2. **Move-order sensitivity**: strict (must reach position via exact move sequence) vs. any-order (position reached by any move sequence)

These combine into four query variants.

### Side Filtering

Because the white and black hashes are stored independently, side filtering is trivially a matter of which hash column is queried:

| User wants | Query column |
|---|---|
| White pieces only | `white_hash = :target_white_hash` |
| Black pieces only | `black_hash = :target_black_hash` |
| Both sides exact  | `full_hash = :target_full_hash` |

The "white pieces only" case is the primary use case from the project requirements: "I always play 1.e4 e5 2.Nf3 — show me all my games where my white pieces were in that configuration, regardless of what Black played."

This means white_hash matches but black_hash may differ — which is precisely why storing the hashes separately is essential.

### Move-Order-Aware Matching (Strict)

In strict mode, the user specifies a sequence of moves (e.g., 1.e4 e5 2.Nf3), and we only want games that reached the target position via exactly that move sequence.

**Implementation:** Walk the game's move list in order. At each ply, compare the position's hash against the target hash for the appropriate ply depth. If any ply diverges, stop — the game does not match.

```python
def game_matches_strict(game_pgn: str, target_moves: list[str], match_side: str) -> bool:
    board = chess.Board()
    target_board = chess.Board()

    for target_move_san in target_moves:
        target_board.push_san(target_move_san)
    target_hash = side_hash(target_board, match_side)
    target_ply = len(target_moves)

    game = chess.pgn.read_game(io.StringIO(game_pgn))
    board = game.board()
    for i, move in enumerate(game.mainline_moves()):
        board.push(move)
        if i + 1 == target_ply:
            return side_hash(board, match_side) == target_hash
    return False
```

**Database optimization for strict mode:** Store the ply number in `game_positions`. A strict query adds `AND gp.ply = :target_ply` to the hash lookup, drastically reducing the result set before any Python-side validation.

```sql
SELECT g.id, g.result ...
FROM game_positions gp
JOIN games g ON g.id = gp.game_id
WHERE gp.white_hash = :white_hash
  AND gp.ply = :target_ply      -- strict mode: only at the right move depth
  AND g.user_id = :user_id
```

This is extremely selective: a specific white_hash at a specific ply will typically match very few rows.

### Move-Order-Agnostic Matching (Any-Order)

In any-order mode, the user specifies a target board state and wants to find all games where that configuration appeared at any point — regardless of move order.

**Database query:** Drop the `ply` constraint entirely. The hash index lookup returns all games where the target position appeared at any move.

```sql
SELECT DISTINCT g.id, g.result ...
FROM game_positions gp
JOIN games g ON g.id = gp.game_id
WHERE gp.white_hash = :white_hash
  AND g.user_id = :user_id
```

The `DISTINCT` is needed because the same position could appear multiple times in a game (e.g., repetition). The first matching ply per game is the one to display.

### Partial Position Matching (Subset Matching)

The requirements specify matching by one side's pieces only. This is not "partial" in the sense of caring about a subset of squares — it is "partial" in the sense of ignoring one color. The hash-based approach handles this cleanly because the hash for white pieces is independent of black piece placement.

If a future requirement arises for true subset matching (e.g., "find games where my knight was on f3 and my bishop was on c4, regardless of other pieces"), that requires a different approach:

- **Column-per-piece-type**: Store the square occupancy for each piece type as a bitmask integer. Query with bitwise AND: `white_knights & :mask = :mask`.
- **PostgreSQL arrays or JSONB**: Store piece placements as queryable structured data.
- **Dedicated search index** (e.g., a trigram or inverted index over piece-square strings).

For v1, the full-side hash approach covers all stated requirements without this complexity.

### Hash Collision Risk

A 64-bit Zobrist hash has a collision probability of ~1/2^64 per pair of positions — negligible for thousands of games. False positive matches would show up as games that don't visually match the query position; these are rare enough to ignore for v1.

---

## Data Flow

### Game Import Pipeline

```
User triggers sync
    │
    ▼
ImportService.sync(user_id, platform, username)
    │
    ├─► Fetch game list from chess.com API
    │       GET https://api.chess.com/pub/player/{username}/games/{year}/{month}
    │       Returns JSON array of games with PGN included
    │
    ├─► Fetch game list from lichess API
    │       GET https://lichess.org/api/games/user/{username}
    │       Accept: application/x-ndjson  (streaming newline-delimited JSON)
    │
    ├─► Dedup: filter out platform_ids already in DB
    │
    └─► For each new game (run as async tasks):
            │
            ├─► Parse PGN with python-chess
            │       chess.pgn.read_game(io.StringIO(pgn))
            │
            ├─► Extract metadata
            │       time_control, rated, opponent name, result, played_at, opening ECO
            │
            ├─► Walk all positions
            │       board = game.board()
            │       for ply, move in enumerate(game.mainline_moves()):
            │           board.push(move)
            │           white_h, black_h, full_h = compute_position_hashes(board)
            │           stage position record: (game_id, ply+1, white_h, black_h, full_h)
            │
            └─► Write to DB atomically
                    INSERT INTO games ...
                    INSERT INTO game_positions (batch) ...
```

**chess.com API note:** The monthly endpoint returns complete PGNs, so one call per month per user covers everything. Pagination is by month; the sync state table records the last synced month.

**lichess API note:** The NDJSON streaming endpoint is more efficient — it can filter by `since` timestamp and returns games as a stream, avoiding large JSON payloads. The `moves=true&clocks=false&evals=false` query parameters trim the response.

**Throughput estimate:** A game with 40 moves generates 40 position records. A user with 5,000 games generates 200,000 position rows. With batch inserts, this processes in seconds.

### Analysis Query Flow

```
User specifies position on interactive board
    │
    ▼
Frontend sends query
    POST /api/analysis
    {
        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "match_side": "white",          // "white" | "black" | "both"
        "move_order": "any",            // "strict" | "any"
        "move_sequence": ["e4"],        // only for "strict" mode
        "filters": {
            "time_controls": ["blitz", "rapid"],
            "rated_only": true,
            "since_days": 365
        }
    }
    │
    ▼
AnalysisService
    │
    ├─► Parse FEN with python-chess → compute query hashes
    │
    ├─► Build SQL query based on match_side and move_order
    │
    ├─► Execute query → list of (game_id, ply, result)
    │
    ├─► Aggregate: count wins/draws/losses
    │
    └─► Return response:
            {
                "total": 47,
                "wins": 28, "draws": 5, "losses": 14,
                "win_rate": 0.596,
                "games": [
                    {
                        "id": 123,
                        "platform": "lichess",
                        "platform_id": "aBcDeFgH",
                        "external_url": "https://lichess.org/aBcDeFgH",
                        "opponent": "DragonSlayer99",
                        "result": "win",
                        "played_at": "2025-11-03",
                        "matched_at_ply": 2
                    }, ...
                ]
            }
```

**FEN input vs. move sequence:** The frontend interactive board can export both a FEN (for any-order mode) and the move sequence used to reach it (for strict mode). For strict mode, the move sequence is the authoritative input — the FEN is derived from it but the ply number and move list determine the query.

---

## Suggested Build Order

The dependencies flow from data inward to query outward. Nothing in the query layer can be validated until the data layer produces real records.

### Phase 1: Data Foundation
1. **Database schema** — Define all tables and indexes. Migrate with Alembic. Get this right early; schema changes later are expensive.
2. **Position hash module** — Pure Python, no DB dependency. Test exhaustively: verify white_hash and black_hash are independent, verify hash stability across python-chess versions, add collision sanity checks.
3. **PGN parser + position indexer** — Takes a PGN string, produces game metadata and a list of position records. Pure logic, easily unit-tested without a DB.

### Phase 2: Import Pipeline
4. **chess.com API client** — Fetch games by username/month, handle rate limits and 404s for unknown users.
5. **lichess API client** — NDJSON streaming, `since` parameter for incremental sync.
6. **Import service** — Orchestrates dedup, parsing, and DB writes. Background task in FastAPI.
7. **Sync state tracking** — Record last-synced timestamp per user/platform so re-sync only fetches new games.

### Phase 3: Analysis Engine
8. **Analysis query builder** — Takes parsed query parameters, selects the right hash column and ply filter, returns game IDs and results.
9. **Analysis API endpoint** — Thin HTTP layer around the analysis service.

### Phase 4: Frontend
10. **Interactive chessboard** — Position entry is the core UX. Use `react-chessboard` (React) or `chessboard.js` (vanilla). Must export both FEN and move sequence.
11. **Filter controls and results display** — Relatively straightforward once the board works.

### Phase 5: Auth and Multi-User
12. **User auth** — FastAPI-Users or a simple JWT approach. Can be bolted on after single-user flow is validated.

### Key Dependency: Validate the hash strategy first

Before writing any API client code, write a test that:
1. Creates a known position in python-chess
2. Computes white_hash and black_hash
3. Creates a second board with the same white pieces but different black pieces
4. Asserts that white_hash matches but full_hash differs

This test is the proof-of-concept for the entire data model. If it passes, the architecture is sound. Do this before importing a single real game.

---

## Design Decisions and Tradeoffs

### SQLite vs PostgreSQL
- SQLite is fine for development and single-user deployments. The position index at 200k rows per user is well within SQLite's sweet spot.
- PostgreSQL becomes necessary for multi-user concurrent writes and for `BIGINT` index performance at scale (1M+ rows). Given the multi-user requirement in the project, plan for PostgreSQL in production even if SQLite is used for local dev.
- Use SQLAlchemy ORM with Alembic migrations so the DB backend is swappable.

### Storing full PGN vs. derived data only
- Store the raw PGN. It is small (a 40-move game is ~2 KB) and preserves optionality: re-parse with different logic later without re-fetching from the API.
- The position index can be rebuilt from stored PGNs if the schema changes.

### Hash-per-position vs. game-level move array
- Alternative: store each game as a JSON array of FEN strings and use JSON operators in PostgreSQL to query. This is simpler to write but slower to query — JSON path operators don't benefit from conventional B-tree indexes.
- The hash-per-row approach with indexed integers is faster at query time and scales better.

### Precomputing vs. on-demand position extraction
- Precompute and store all position hashes at import time. This shifts cost to import (acceptable — runs in background) and makes queries fast (critical — user is waiting).
- On-demand parsing (walk PGN at query time) is too slow for thousands of games.
