# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Chessalytics — a multi-user chess analysis platform. Users import games from chess.com/lichess and analyze win/draw/loss rates by board position using Zobrist hashes, solving inconsistent opening categorization on existing platforms.

## Tech Stack

- **Backend**: FastAPI 0.115.x, Python 3.12, uv, Uvicorn
- **Frontend**: React 18 + TypeScript + Vite 5, react-chessboard 4.x, chess.js, TanStack Query, Tailwind CSS
- **Database**: PostgreSQL (asyncpg). No SQLite.
- **ORM**: SQLAlchemy 2.x async (`select()` API, not legacy 1.x) + Alembic + asyncpg
- **Auth**: FastAPI-Users
- **HTTP client**: httpx async only — never use `requests` or `berserk`
- **Chess logic**: python-chess 1.10.x
- **Validation**: Pydantic v2 throughout

## Commands

```bash
# Backend
uv sync                          # Install dependencies from lockfile
uv run uvicorn app.main:app --reload  # Run dev server
uv run pytest                    # Run all tests
uv run pytest tests/test_foo.py::test_bar  # Run single test
uv run pytest -x               # Stop on first failure
uv run ruff check .             # Lint
uv run ruff format .            # Format
uv run alembic upgrade head     # Run migrations
uv run alembic revision --autogenerate -m "description"  # Create migration

# Frontend
npm install                     # Install dependencies
npm run dev                     # Dev server
npm run build                   # Production build
npm run lint                    # Lint
```

## Architecture

### Core Concept: Zobrist Hash Position Matching

The central architectural decision. Positions are matched via precomputed 64-bit integer Zobrist hashes, not FEN string comparison:
- `white_hash` — hash of white pieces only (enables "my pieces only" queries)
- `black_hash` — hash of black pieces only
- `full_hash` — hash of complete position

All three are computed at import time for every half-move and stored in `game_positions`. Position queries become indexed integer equality lookups.

### Backend Layout

```
routers/          # HTTP layer only — no business logic
services/         # Business logic (import, analysis)
repositories/     # DB access (no SQL in services)
```

### Key Tables

- `games` — game metadata, PGN, result, time control, platform info
- `game_positions` — the hot table: `(game_id, ply, white_hash, black_hash, full_hash, user_id)`. `user_id` is denormalized for query performance.
- Unique constraint on `(platform, platform_game_id)` prevents duplicates

### Import Pipeline

Background async tasks (not blocking the API). chess.com fetches monthly archives sequentially with rate-limit delays. lichess streams NDJSON line-by-line. Both normalize to a unified schema before storage.

### Analysis Query Pattern

```sql
SELECT g.* FROM game_positions gp
JOIN games g ON g.id = gp.game_id
WHERE gp.white_hash = :hash AND g.user_id = :uid
  AND g.time_control IN (...) -- optional filters
```

## Critical Constraints

- Always use `httpx.AsyncClient` for external HTTP calls — `requests` blocks the event loop
- lichess `since`/`until` parameters use millisecond timestamps, not seconds
- Only import `Standard` variant games — filter out Chess960, crazyhouse, etc.
- Time control bucketing: <=180s = bullet, <=600s = blitz, <=1800s = rapid, else classical (based on estimated game duration)
- PGN parsing: wrap per-game in try/except, handle `UnicodeDecodeError`, loop `read_game()` until `None` for multi-game strings
- Use `board.board_fen()` (piece placement only) not `board.fen()` (includes castling/en passant) when comparing positions
- chess.com requires `User-Agent` header; fetch archives sequentially with 100-300ms delays
- API responses never expose internal hashes — return FEN for display
