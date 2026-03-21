# FlawChess

A chess analysis platform. Import games from chess.com and lichess, then analyze win/draw/loss rates by board position using Zobrist hashes — solving inconsistent opening categorization on existing platforms.

## Prerequisites

- Python 3.13+
- Docker (for PostgreSQL)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Getting Started

```bash
# Start the dev database (PostgreSQL 18 in Docker)
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the dev server
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Development

### Running Tests

```bash
uv run pytest                              # Run all tests
uv run pytest tests/test_foo.py            # Run a specific test file
uv run pytest tests/test_foo.py::test_bar  # Run a single test
uv run pytest -x                           # Stop on first failure
```

### Linting and Formatting

```bash
uv run ruff check .    # Lint
uv run ruff format .   # Format
```

### Database Migrations

```bash
uv run alembic upgrade head                            # Apply all migrations
uv run alembic revision --autogenerate -m "description"  # Create a new migration
```

## Docker Compose

```bash
cp .env.example .env  # Fill in values
docker compose up -d --build
```

Runs three services: PostgreSQL 16, FastAPI backend (with auto-migration), and Caddy reverse proxy with automatic HTTPS. See `deploy/cloud-init.yml` for a production server setup example.

## Architecture

### Zobrist Hash Position Matching

The core idea: positions are matched via precomputed 64-bit Zobrist hashes rather than FEN string comparison. Three hashes are computed at import time for every half-move:

- **white_hash** — white pieces only (enables "my pieces only" queries)
- **black_hash** — black pieces only
- **full_hash** — complete board position

All hashes are stored in the `game_positions` table, turning position queries into fast indexed integer lookups.

### Project Structure

```
app/
  routers/        # HTTP layer — no business logic
  services/       # Business logic (import, analysis)
  repositories/   # Database access (no raw SQL in services)
  models/         # SQLAlchemy models
  schemas/        # Pydantic schemas
  core/           # Config, database, shared utilities
alembic/          # Database migrations
tests/            # Test suite
```

## License

MIT
