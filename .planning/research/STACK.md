# Stack Research: Chessalytics

## Backend

### Framework: FastAPI 0.115.x

Already decided per PROJECT.md constraints. FastAPI is the right call:

- **Async-native**: Game imports from chess.com and lichess are I/O-bound. `async def` endpoints with `httpx` let you fetch multiple pages of games concurrently without blocking.
- **Automatic OpenAPI docs**: Useful while building — the `/docs` UI lets you test import and query endpoints without a frontend.
- **Pydantic-first**: Request/response validation is built in. Position filter payloads (FEN strings, color selection, time control filters) are self-documenting.
- **Version 0.115.x**: The current stable release as of mid-2025. Requires Pydantic v2. Do not use 0.100.x or older — they used Pydantic v1 and have a different dependency model.

### ASGI Server: Uvicorn 0.30.x

- The standard production-grade ASGI server for FastAPI.
- Use `uvicorn[standard]` to pull in `uvloop` (faster event loop on Linux/macOS) and `websockets`.
- Run with `--workers 1` in development; use `gunicorn -k uvicorn.workers.UvicornWorker` for multi-process production deployments.

### Data Validation: Pydantic v2.7.x

- FastAPI 0.115.x requires Pydantic v2. Do not pin to v1.
- Pydantic v2 is a full rewrite in Rust — validation is ~5–50x faster than v1. At thousands of games per user, position-matching involves many FEN comparisons; fast validation matters.
- Use `model_config = ConfigDict(from_attributes=True)` for ORM mode (replaces `orm_mode = True` from v1).

### HTTP Client: HTTPX 0.27.x

- The async-native HTTP client for Python. Use `httpx.AsyncClient` for all chess.com and lichess API calls.
- Drop-in replacement for `requests` with full async support. Do NOT use `requests` — it blocks the event loop.
- Supports connection pooling, timeouts, and retries. Configure a shared `AsyncClient` instance at app startup (lifespan context) and reuse it across requests rather than creating a new client per call.

### Package Management: uv (latest)

- Already decided per PROJECT.md. Use `uv` for all dependency management and virtual environment creation.
- `uv add <package>` writes to `pyproject.toml` and updates `uv.lock`. Commit `uv.lock` to the repo for reproducible installs.
- Use `uv run` for running scripts and `uv sync` for installing from lockfile.

---
 
## Frontend

### Recommendation: React 19.x with Vite 5.x

React is the right choice here over simpler alternatives (plain HTML/JS, Vue, Svelte) for one key reason: the best interactive chess board library in the JavaScript ecosystem — **Chessground** and its React wrappers — is built with React in mind, and the broader chess UI ecosystem (react-chessboard, etc.) is React-first.

- **Vite 5.x**: The standard modern bundler/dev server. Fast hot module reload, simple config, excellent TypeScript support. Do not use Create React App — it is unmaintained.
- **TypeScript**: Use TypeScript from the start. FEN strings, board positions, and filter state have enough structure that type safety pays off immediately.
- **No framework router needed for v1**: This is a single-page application with simple navigation (import page, analysis page). React Router 6.x is fine if needed, but a flat component tree may suffice initially.

### Chess Board Library: react-chessboard 4.x

- **react-chessboard** (by Clyde Lovell, maintained on npm) is the leading React chess board component as of 2025.
- Supports drag-and-drop piece movement, custom positions via FEN, orientation (white/black), and custom square highlighting.
- Pair it with **chess.js 1.x** on the frontend to maintain board state and validate moves as the user builds a position.
- `react-chessboard` renders the visual board; `chess.js` manages the legal move logic and FEN generation client-side.

**Alternative considered — Chessground**: Lichess's own board library. More powerful and lower-level, but designed for use with Svelte/vanilla JS. The React integration is unofficial and requires more wiring. Not recommended unless react-chessboard proves limiting.

**What NOT to use**: `chessboardjs` (jQuery-based, legacy), `chess-board` (outdated npm package). Both are unmaintained.

### State Management

- **React Query (TanStack Query) 5.x**: For server state — fetching games, submitting analysis queries, polling sync status. Handles loading/error states, caching, and background refetch out of the box. Do not reach for Redux for this use case.
- **React built-in state (`useState`, `useReducer`)**: For the interactive board position state (current FEN, selected filters).

### Styling: Tailwind CSS 3.x

- Utility-first, pairs well with component-based React. No context switching between CSS files.
- Alternative: plain CSS modules if Tailwind feels heavy for the scope. Either works; Tailwind is faster to iterate with.

---

## Database

### Recommendation: PostgreSQL 16.x (primary), SQLite for local dev

**Use PostgreSQL in production.** Here is why:

The core query for Chessalytics is: "find all games where position P appears at move N, filtering by color, time control, date range." This is a substring/pattern match across potentially millions of move records. PostgreSQL's indexing capabilities, full-text search extensions, and `jsonb` type make this tractable. SQLite cannot use multiple concurrent write connections (problematic for multi-user sync) and lacks the indexing power needed at scale.

**Use SQLite for local development** to avoid requiring a Postgres install. SQLAlchemy's abstraction layer makes this practical — same ORM code, different connection string.

### Schema Considerations for Position Matching

The critical insight is how positions are stored and queried. There are two approaches:

**Option A — Store PGN move text, parse at query time**: Simple to store, very slow to query. Do not use this for the position-matching feature.

**Option B — Pre-compute and store FEN strings per move (recommended)**:

- For each game, walk through all moves with python-chess and store the FEN for each half-move (ply) in a `game_positions` table.
- Index on a **normalized FEN** column. A full FEN encodes whose turn it is, castling rights, and en passant — which you do not want for position matching (you want "does this piece placement appear, regardless of whose turn"). Strip the FEN to just the piece placement portion (the first field, before the first space) for matching.
- For "my pieces only" filtering: also store a **masked FEN** variant — e.g., white-pieces-only FEN — by replacing black piece characters with empty squares. This allows the filter-by-color feature without scanning all positions at query time.

**Recommended tables (high-level)**:

```
users               (id, username, created_at)
user_sources        (id, user_id, platform [chesscom|lichess], platform_username, last_synced_at)
games               (id, user_source_id, platform_game_id, pgn, time_control, rated, played_at, result, color_played, opponent_username, game_url)
game_positions      (id, game_id, ply_number, fen_full, fen_pieces_only, fen_white_pieces, fen_black_pieces)
```

Index `game_positions(user_source_id, fen_pieces_only)` — but since `user_source_id` is on `games`, this will need a join. Consider a denormalized `user_id` on `game_positions` for query performance.

PostgreSQL `GIN` or `HASH` indexes on the FEN columns work well since FEN matching is always equality (not range), not LIKE.

### ORM: SQLAlchemy 2.x with Alembic 1.13.x

- **SQLAlchemy 2.x**: The standard Python ORM. Version 2.0+ has a fully async-capable engine (`create_async_engine`) that works with FastAPI's async model. Use the 2.x-style `select()` API, not the legacy 1.x query API.
- **Alembic 1.13.x**: Migration tool for SQLAlchemy schemas. Essential once the schema evolves past initial setup. Initialize with `alembic init` and configure to use the same `DATABASE_URL` as the app.
- **aiosqlite 0.20.x**: Async SQLite driver for local development (used by SQLAlchemy's async engine).
- **asyncpg 0.29.x**: Async PostgreSQL driver for production. Fastest available Postgres driver for Python. Connection string: `postgresql+asyncpg://...`.

---

## Chess Libraries

### Core: python-chess 1.10.x

The de facto standard for chess logic in Python. No serious alternative exists for this use case.

- **PGN parsing**: `chess.pgn.read_game(io.StringIO(pgn_text))` returns a `Game` object. Walk the mainline with `game.mainline_moves()` to iterate moves.
- **FEN generation**: After each move, call `board.fen()` to get the full FEN, or `board.board_fen()` for just the piece placement portion (the part you want for position matching).
- **Position comparison**: Use `board.board_fen()` for your normalized comparison key. For "my pieces only" matching, manipulate the piece map: `board.piece_map()` returns `{square: Piece}` — filter by color and reconstruct a masked board.
- **Move validation**: `board.is_legal(move)` — useful for validating user-submitted positions on the backend if needed.
- **No alternatives worth considering**: `pychess` is less maintained and has fewer users. `stockfish` Python bindings are for engine analysis, not position handling. python-chess is the right and only choice.

### FEN Manipulation Utilities

python-chess handles all needed FEN work:

- `chess.Board(fen)` — parse a FEN into a board object
- `board.board_fen()` — extract piece placement only (no turn, castling, en passant)
- `board.piece_map()` — get `{square_int: chess.Piece}` for custom masked FEN generation
- `chess.square_name(sq)` — convert square int to algebraic notation

For "white pieces only" masked FEN: iterate `board.piece_map()`, keep only pieces where `piece.color == chess.WHITE`, place them on a fresh empty board, call `board_fen()`.

---

## API Integration

### chess.com API

- **Base URL**: `https://api.chess.com/pub/`
- **No authentication required** for public data. The API is open for reading public player data.
- **Rate limiting**: chess.com enforces rate limits but does not publish exact numbers. Use exponential backoff on 429 responses. In practice, fetching game archives requires two steps:
  1. `GET /pub/player/{username}/games/archives` — returns a list of monthly archive URLs.
  2. `GET /pub/player/{username}/games/{YYYY}/{MM}` — returns all games for that month as PGN text plus metadata (JSON with a `games` array, each having `pgn`, `time_class`, `rated`, `white`, `black`, `url`, `end_time`).
- **Library**: No official Python SDK. Use `httpx.AsyncClient` directly. The API is simple enough that a thin wrapper function is all that is needed.
- **Key fields**: `time_class` (bullet/blitz/rapid/classical), `rated` (bool), `white.result`/`black.result` (win/lose/draw/etc.), `url` (link back to game), `end_time` (Unix timestamp).

### lichess API

- **Base URL**: `https://lichess.org/api/`
- **No authentication required** for public game exports. OAuth is only needed for private data or write operations.
- **Rate limiting**: lichess publishes limits. Unauthenticated: 15 requests/minute for most endpoints. Game export streams are generous but respect the `Accept: application/x-ndjson` header for streaming.
- **Game export endpoint**: `GET /api/games/user/{username}` — streams games as NDJSON (newline-delimited JSON) or PGN. Parameters:
  - `max` — maximum number of games
  - `since`/`until` — Unix timestamps in milliseconds for date filtering
  - `perfType` — filter by time control (bullet, blitz, rapid, classical)
  - `rated` — true/false
  - `pgnInJson=true` — include PGN inside the JSON object
  - `moves=true` — include move list
- **Streaming**: Use `httpx.AsyncClient` with `stream=True` and process NDJSON line by line. Do not buffer the entire response — for users with many games this will be large.
- **Library**: `berserk` is a Python client for the lichess API (version 0.13.x as of 2025). It wraps the NDJSON streaming correctly. However, it uses synchronous `requests` internally — for a FastAPI async app, using `httpx` directly is cleaner than running `berserk` in a thread pool. Use `httpx` directly.

---

## Key Dependencies

### Full Dependency List

**Backend (`pyproject.toml`)**:

```toml
[project]
requires-python = ">=3.12"

dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",   # Settings management via .env
    "sqlalchemy>=2.0.30",
    "alembic>=1.13.0",
    "asyncpg>=0.29.0",             # Postgres async driver
    "aiosqlite>=0.20.0",           # SQLite async driver (local dev)
    "httpx>=0.27.0",
    "python-chess>=1.10.0",
]

[dependency-groups]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",               # Also used as test client for FastAPI
    "ruff>=0.4.0",                 # Linter + formatter
]
```

**Frontend (`package.json`)**:

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-chessboard": "^4.6.0",
    "chess.js": "^1.0.0",
    "@tanstack/react-query": "^5.40.0"
  },
  "devDependencies": {
    "vite": "^5.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0"
  }
}
```

### Python Version

Use Python **3.12**. It is the current stable release, has performance improvements over 3.11, and is supported by all listed libraries. Do not use 3.13 yet — asyncpg and some other packages may have lagging support.

### What NOT to Use and Why

| Package | Reason to Avoid |
|---|---|
| `requests` | Synchronous — blocks FastAPI's event loop during API calls. Use `httpx` instead. |
| `berserk` | Lichess client that wraps `requests` synchronously. Too much friction to use in async context. Call lichess NDJSON endpoints directly with `httpx`. |
| `Flask` / `Django` | Not async-native; Flask requires `gevent`/`eventlet` hacks for concurrency; Django is too heavy. FastAPI is already decided. |
| `tortoise-orm` | Async ORM alternative to SQLAlchemy. Smaller ecosystem, fewer migrations tools, less documentation. SQLAlchemy 2.x async is the better choice. |
| `databases` (encode) | Thin async query layer that predates SQLAlchemy 2.x async. Now redundant. |
| `SQLAlchemy 1.x` | Legacy query API, no native async support. Always use 2.x. |
| `Pydantic v1` | FastAPI 0.115.x requires v2. v1 is EOL. |
| `Create React App` | Unmaintained since 2023. Use Vite. |
| `chessboardjs` | jQuery-dependent, no longer maintained, no React support. |
| `Redux` / `Zustand` | Overkill for this app's state needs. React Query handles server state; local state is simple enough for `useState`. |
| PostgreSQL `LIKE '%fen%'` queries | Full-table scans. Always store the FEN piece-placement string as a discrete indexed column and query with equality (`=`), not pattern matching. |

---

*Research completed: 2026-03-11. Versions based on ecosystem state as of mid-2025 training data; verify against PyPI and npm before pinning in production.*
