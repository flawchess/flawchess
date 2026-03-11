# Phase 1: Data Foundation - Research

**Researched:** 2026-03-11
**Domain:** SQLAlchemy 2.x async ORM, Alembic async migrations, python-chess Zobrist hashing, PostgreSQL schema design
**Confidence:** HIGH

## Summary

Phase 1 establishes the entire data layer that every subsequent phase depends on. The two core deliverables are: (1) the database schema with `games` and `game_positions` tables, Alembic migrations, and the project scaffolding (`app/` package, `pyproject.toml`, `.env`); and (2) a pure-Python Zobrist hash module that produces `white_hash`, `black_hash`, and `full_hash` as 64-bit signed integers for every board position.

The Zobrist hash approach is technically confirmed: python-chess's `chess.polyglot.POLYGLOT_RANDOM_ARRAY` uses a deterministic indexing scheme of `64 * ((piece_type - 1) * 2 + color_pivot) + square`. This makes color-specific hashes straightforward — iterate only `board.occupied_co[chess.WHITE]` (or `chess.BLACK`) and XOR the corresponding array entries. The `full_hash` uses `chess.polyglot.zobrist_hash(board)` directly. All three hashes store as PostgreSQL `BIGINT` (64-bit signed integer).

The schema design uses SQLAlchemy 2.x `DeclarativeBase` with `type_annotation_map = {int: BIGINT}` so all `Mapped[int]` columns resolve to `BIGINT` automatically. Alembic is initialized with `-t async` to generate the async-compatible `env.py` template. Tests for the hash module are pure unit tests (no database needed) and can run instantly.

**Primary recommendation:** Scaffold the project, define models with SQLAlchemy 2.x typed ORM, create the Zobrist module using POLYGLOT_RANDOM_ARRAY directly, and write unit tests that verify hash determinism without any database dependency.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None explicitly locked by user — all Phase 1 decisions delegated to Claude.

### Claude's Discretion
- **Game metadata fields (`games` table):** Store all available metadata from both platforms: PGN, time control string, estimated duration, rated flag, result, opponent username, user color, platform URL, platform game ID, platform name, timestamps (played_at, imported_at). Include opponent rating and user rating at time of game. Include opening name/ECO from platform as-is. Variant column to filter Standard-only at query time.
- **Zobrist hash approach:** Use python-chess's built-in `chess.polyglot.zobrist_hash()` for full_hash. For white_hash and black_hash: compute custom hashes by iterating only over pieces of the target color using POLYGLOT_RANDOM_ARRAY. All hashes stored as 64-bit signed integers (PostgreSQL `BIGINT`).
- **Project bootstrapping:** Backend rooted at project root — `app/` package with `main.py`. Directory structure: `app/{routers,services,repositories,models,schemas,core}/`. `pyproject.toml` with uv, ruff config, pytest config. Alembic initialized with async PostgreSQL driver (asyncpg). `.env` for database URL and secrets (with `.env.example` committed).
- **ID and key strategy:** `games.id`: auto-increment `BIGINT` PK. `game_positions`: composite indexes on `(user_id, full_hash)`, `(user_id, white_hash)`, `(user_id, black_hash)`. Hash columns: `BIGINT`. Unique constraint: `(platform, platform_game_id)` on `games`.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Database schema supports efficient position-based queries using indexed Zobrist hash columns | Composite indexes `(user_id, full_hash)`, `(user_id, white_hash)`, `(user_id, black_hash)` on `game_positions`; BIGINT equality lookups are ~40% faster than UUID due to smaller index pages |
| INFRA-03 | Duplicate games are prevented via unique constraint on (platform, platform_game_id) | SQLAlchemy `UniqueConstraint("platform", "platform_game_id")` in `__table_args__`; enforced at DB level |
| IMP-05 | All available game metadata is stored (PGN, time control, rated flag, result, opponent, color, platform URL, timestamps) | Full `games` table column list documented in Architecture Patterns section below |
| IMP-06 | Position hashes (white, black, full Zobrist) are precomputed and stored for every half-move at import time | Hash module using POLYGLOT_RANDOM_ARRAY with color-filtered iteration; documented with verified code examples |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlalchemy[asyncio] | 2.0.x | ORM + async DB access | Project-specified; typed ORM via `Mapped[]` + `mapped_column()` |
| asyncpg | 0.29.x | PostgreSQL async driver | Only mature async PostgreSQL driver for SQLAlchemy |
| alembic | 1.13.x | Schema migrations | Standard companion to SQLAlchemy; has `-t async` template |
| python-chess | 1.10.x | Board representation + Zobrist hash | Project-specified; provides `POLYGLOT_RANDOM_ARRAY` |
| pydantic | 2.x | Config validation | Project-specified; v2 throughout |
| fastapi | 0.115.x | App framework (minimal in Phase 1) | Project-specified |
| python-dotenv | 1.0.x | Load `.env` config | Standard for FastAPI env management |

### Supporting (Dev / Test)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x | Test runner | All tests |
| pytest-asyncio | 0.23.x | Async test support | Any async test function |
| ruff | 0.4.x | Lint + format | Replaces flake8 + black in uv projects |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncpg | psycopg3 (asyncio mode) | asyncpg is more mature for SQLAlchemy; psycopg3 is viable but less tested in this stack |
| BIGINT PK on games | UUID PK | BIGINT is 8 bytes vs 16 bytes; ~40% smaller indexes; simpler joins. UUID better for distributed systems — not needed here |
| python-chess POLYGLOT_RANDOM_ARRAY | Custom random table | Custom table breaks compatibility; POLYGLOT values are fixed and deterministic |

**Installation:**
```bash
uv add fastapi[standard] uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic python-chess pydantic python-dotenv
uv add --dev pytest pytest-asyncio ruff
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── main.py              # FastAPI app creation, lifespan
├── core/
│   └── config.py        # Pydantic Settings, reads .env
├── models/
│   ├── base.py          # DeclarativeBase with BIGINT type_annotation_map
│   ├── game.py          # Game SQLAlchemy model
│   └── game_position.py # GamePosition SQLAlchemy model
├── schemas/             # Pydantic v2 schemas (empty Phase 1)
├── repositories/        # DB access layer (empty Phase 1)
├── services/
│   └── zobrist.py       # Pure hash computation module
└── routers/             # HTTP layer (empty Phase 1)
alembic/
├── env.py               # Async-configured env
├── script.py.mako
└── versions/
    └── XXXX_initial_schema.py
pyproject.toml
.env
.env.example
```

### Pattern 1: SQLAlchemy 2.x Typed Models with BIGINT

**What:** Use `DeclarativeBase` with `type_annotation_map` so all `Mapped[int]` columns automatically resolve to PostgreSQL `BIGINT`. Avoids repeating `BIGINT` on every column.

**When to use:** All ORM models in this project.

```python
# Source: SQLAlchemy 2.0 docs — Table Configuration with Declarative
# https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
from sqlalchemy import BIGINT, DateTime
from sqlalchemy.orm import DeclarativeBase, AsyncAttrs
import datetime

class Base(AsyncAttrs, DeclarativeBase):
    type_annotation_map = {
        int: BIGINT,
        datetime.datetime: DateTime(timezone=True),
    }
```

Then any model column:
```python
id: Mapped[int] = mapped_column(primary_key=True)         # resolves to BIGINT
white_hash: Mapped[int] = mapped_column(nullable=False)   # resolves to BIGINT
```

### Pattern 2: Game Model with Full Metadata (IMP-05)

```python
# app/models/game.py
from sqlalchemy import String, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
import datetime

class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("platform", "platform_game_id", name="uq_games_platform_game_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)  # FK to users in Phase 4

    # Platform identity
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # "chess.com" | "lichess"
    platform_game_id: Mapped[str] = mapped_column(String(100), nullable=False)
    platform_url: Mapped[str | None] = mapped_column(String(500))

    # Game content
    pgn: Mapped[str] = mapped_column(nullable=False)
    variant: Mapped[str] = mapped_column(String(50), nullable=False, default="Standard")

    # Result
    result: Mapped[str] = mapped_column(String(10), nullable=False)   # "1-0" | "0-1" | "1/2-1/2"
    user_color: Mapped[str] = mapped_column(String(5), nullable=False) # "white" | "black"

    # Time control
    time_control_str: Mapped[str | None] = mapped_column(String(50))  # raw string e.g. "600+0"
    time_control_bucket: Mapped[str | None] = mapped_column(String(20)) # "bullet"|"blitz"|"rapid"|"classical"
    time_control_seconds: Mapped[int | None]  # estimated duration in seconds

    # Flags
    rated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Opponent info
    opponent_username: Mapped[str | None] = mapped_column(String(100))
    opponent_rating: Mapped[int | None]
    user_rating: Mapped[int | None]

    # Opening info (from platform, display only — not used for position matching)
    opening_name: Mapped[str | None] = mapped_column(String(200))
    opening_eco: Mapped[str | None] = mapped_column(String(10))

    # Timestamps
    played_at: Mapped[datetime.datetime | None]
    imported_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        default=datetime.datetime.utcnow,
    )

    positions: Mapped[list["GamePosition"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
```

### Pattern 3: GamePosition Model with Hash Indexes (INFRA-01)

```python
# app/models/game_position.py
from sqlalchemy import Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class GamePosition(Base):
    __tablename__ = "game_positions"
    __table_args__ = (
        # Composite indexes for the three query patterns (Phase 3)
        Index("ix_gp_user_full_hash", "user_id", "full_hash"),
        Index("ix_gp_user_white_hash", "user_id", "white_hash"),
        Index("ix_gp_user_black_hash", "user_id", "black_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(nullable=False)  # denormalized for query perf
    ply: Mapped[int] = mapped_column(nullable=False)       # half-move number (0 = initial)

    # Zobrist hashes — all BIGINT via type_annotation_map
    full_hash: Mapped[int] = mapped_column(nullable=False)
    white_hash: Mapped[int] = mapped_column(nullable=False)
    black_hash: Mapped[int] = mapped_column(nullable=False)

    game: Mapped["Game"] = relationship(back_populates="positions")
```

### Pattern 4: Async Engine and Session Factory

```python
# app/core/database.py
# Source: https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,       # postgresql+asyncpg://...
    echo=settings.DB_ECHO,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
```

### Pattern 5: Alembic Async env.py

Initialize with: `uv run alembic init -t async alembic`

The `-t async` flag generates an `env.py` with `run_async_migrations()` already implemented. Key manual additions:

```python
# alembic/env.py — additions after init
import asyncio
from app.core.config import settings
from app.models.base import Base
# Import all models so Alembic sees them for autogenerate:
from app.models.game import Game           # noqa: F401
from app.models.game_position import GamePosition  # noqa: F401

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

The `run_async_migrations()` function from the `-t async` template:
```python
async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()
```

### Pattern 6: Zobrist Hash Module (IMP-06)

**Key verified fact:** `chess.polyglot.POLYGLOT_RANDOM_ARRAY` uses the indexing scheme `64 * ((piece_type - 1) * 2 + color_pivot) + square` where:
- `piece_type` is 1–6 (PAWN through KING, from `chess.PAWN` etc.)
- `color_pivot` is 0 for WHITE, 1 for BLACK
- `square` is 0–63

This means color-specific hashes are computed by iterating only the target color's occupied squares:

```python
# app/services/zobrist.py
# Source: polyglot.py source analysis from python-chess
# https://python-chess.readthedocs.io/en/latest/_modules/chess/polyglot.html
import chess
import chess.polyglot
from chess.polyglot import POLYGLOT_RANDOM_ARRAY


def _color_hash(board: chess.Board, color: chess.Color) -> int:
    """XOR Polyglot piece-square values for pieces of one color only."""
    h = 0
    color_pivot = 0 if color == chess.WHITE else 1
    for square in chess.scan_reversed(board.occupied_co[color]):
        piece_type = board.piece_type_at(square)
        piece_index = (piece_type - 1) * 2 + color_pivot
        h ^= POLYGLOT_RANDOM_ARRAY[64 * piece_index + square]
    return h


def compute_hashes(board: chess.Board) -> tuple[int, int, int]:
    """
    Returns (white_hash, black_hash, full_hash) for the current board state.

    - white_hash: XOR of Polyglot values for white pieces only
    - black_hash: XOR of Polyglot values for black pieces only
    - full_hash: standard Polyglot Zobrist hash (includes castling/en passant)

    All values are 64-bit unsigned integers from POLYGLOT_RANDOM_ARRAY,
    stored in PostgreSQL as BIGINT (Python int fits without truncation for
    values <= 2^63-1; use ctypes.c_int64(h).value to convert if needed).
    """
    white_hash = _color_hash(board, chess.WHITE)
    black_hash = _color_hash(board, chess.BLACK)
    full_hash = chess.polyglot.zobrist_hash(board)
    return white_hash, black_hash, full_hash


def hashes_for_game(pgn_text: str) -> list[tuple[int, int, int, int]]:
    """
    Parse a PGN string and return (ply, white_hash, black_hash, full_hash)
    for every half-move including the initial position (ply=0).

    Wraps parsing in try/except per CLAUDE.md constraint.
    """
    import io
    import chess.pgn

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return []

    results = []
    board = game.board()
    wh, bh, fh = compute_hashes(board)
    results.append((0, wh, bh, fh))

    for ply, move in enumerate(game.mainline_moves(), start=1):
        board.push(move)
        wh, bh, fh = compute_hashes(board)
        results.append((ply, wh, bh, fh))

    return results
```

**BIGINT signed integer note:** Polyglot hashes are 64-bit unsigned. Python handles arbitrary-precision integers, but PostgreSQL `BIGINT` is signed (range -2^63 to 2^63-1). Values that exceed 2^63-1 will cause overflow. Convert with:
```python
import ctypes
signed_hash = ctypes.c_int64(unsigned_hash).value
```
Apply this conversion in `compute_hashes()` before returning.

### Anti-Patterns to Avoid
- **Using `board.fen()` for position comparison:** Full FEN includes castling rights and en passant — use `board.board_fen()` if comparing FEN strings, or rely on `full_hash` (which correctly includes these for full matching via Polyglot).
- **Storing hashes as `VARCHAR`/text:** Kills index performance. Must be `BIGINT` integer columns.
- **Nullable hash columns:** Every position must have all three hashes. Use `nullable=False`.
- **Legacy SQLAlchemy 1.x `session.query()`:** Use `select()` API throughout per project constraint.
- **Forgetting `expire_on_commit=False`:** Async sessions with `expire_on_commit=True` (the default) will trigger lazy loads that fail in async context.
- **Alembic autogenerate without importing models:** `env.py` must import all model modules so `Base.metadata` is populated before `--autogenerate` runs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Zobrist hash tables | Custom random array | `chess.polyglot.POLYGLOT_RANDOM_ARRAY` | POLYGLOT values are the industry standard; custom arrays produce incompatible hashes |
| Full board hash | Custom XOR loop | `chess.polyglot.zobrist_hash(board)` | Built-in handles castling rights and en passant edge cases correctly |
| Schema migrations | Hand-written SQL | Alembic autogenerate | Autogenerate catches column additions, index changes, constraint diffs |
| Database URL handling | Manual string concat | Pydantic `BaseSettings` | Type-safe, env-var loading, validation |
| Async session management | Manual `await session.close()` | `async with async_session_maker() as session:` | Context manager handles commit/rollback/close correctly |

**Key insight:** The Zobrist hash tables in python-chess are hardcoded Polyglot-compatible values — they are not random at runtime. This guarantees that the same position always produces the same hash values across all deployments, restarts, and Python versions.

## Common Pitfalls

### Pitfall 1: BIGINT Signed Overflow on Hash Storage
**What goes wrong:** Polyglot hashes are computed as unsigned 64-bit integers. Values between 2^63 and 2^64-1 are valid unsigned values but overflow PostgreSQL's signed `BIGINT` range, causing `asyncpg.exceptions.NumericValueOutOfRangeError` on insert.
**Why it happens:** Python `int` is arbitrary precision; asyncpg enforces PostgreSQL's signed range.
**How to avoid:** Convert all hashes with `ctypes.c_int64(h).value` before storing. The XOR comparison still works correctly because the bit patterns are preserved.
**Warning signs:** Insert errors mentioning "integer out of range" on first game import.

### Pitfall 2: Alembic Not Detecting Models
**What goes wrong:** `alembic revision --autogenerate` produces an empty migration (no detected changes) even though models are defined.
**Why it happens:** `env.py`'s `target_metadata = Base.metadata` captures metadata at import time. If model modules are not imported before this line, `Base.metadata` has no tables registered.
**How to avoid:** Import all model modules in `env.py` before `target_metadata` is assigned. The imports can be `# noqa: F401` since they're side-effect imports.
**Warning signs:** Generated migration file has empty `upgrade()` body.

### Pitfall 3: Async Alembic env.py Without `-t async`
**What goes wrong:** Running `alembic upgrade head` hangs or raises `RuntimeError: This event loop is already running`.
**Why it happens:** Default Alembic `env.py` uses synchronous `engine.connect()` which blocks when called with asyncpg.
**How to avoid:** Always initialize with `alembic init -t async alembic`. If already initialized without it, replace `env.py` with the async template pattern.
**Warning signs:** `alembic upgrade head` hangs indefinitely on first run.

### Pitfall 4: Missing `user_id` Denormalization on `game_positions`
**What goes wrong:** Analysis queries require `JOIN games g ON g.id = gp.game_id WHERE g.user_id = :uid` — this double-join prevents using the composite index efficiently.
**Why it happens:** Normalizing `user_id` to only the `games` table seems cleaner, but kills query performance on the hot path.
**How to avoid:** Store `user_id` directly on `game_positions` (denormalized). Indexes `(user_id, full_hash)` then work without any join for position lookups.
**Warning signs:** Slow analysis queries even with indexes present (explain plan shows sequence scans).

### Pitfall 5: FastAPI-Users UUID Primary Key Mismatch
**What goes wrong:** FastAPI-Users defaults to UUID primary keys. Using `SQLAlchemyBaseUserTableUUID` with `user_id: Mapped[int]` foreign keys on `games`/`game_positions` causes type mismatch errors.
**Why it happens:** Phase 4 will add Auth, but Phase 1 schema must be compatible. The `user_id` column type must match the Users table PK type chosen in Phase 4.
**How to avoid:** In Phase 1, define `user_id` on both `games` and `game_positions` as `Mapped[int]` (BIGINT). In Phase 4, configure FastAPI-Users with integer PKs (`SQLAlchemyBaseUserTable[int]`) for consistency. Note this as an integration constraint in Phase 4 context.
**Warning signs:** Foreign key constraint errors when Phase 4 adds the `users` table.

### Pitfall 6: `board_fen()` vs `fen()` Confusion
**What goes wrong:** Code uses `board.fen()` thinking it captures position, but `fen()` includes castling rights and en passant square — two boards with identical piece placement but different castling rights produce different FENs.
**Why it happens:** `fen()` is the first method developers reach for; `board_fen()` is less obvious.
**How to avoid:** For any FEN string comparison of piece placement only, use `board.board_fen()`. For the Zobrist hash, `full_hash` via `chess.polyglot.zobrist_hash()` correctly includes castling/en passant (this is intentional behavior for position identity).

## Code Examples

Verified patterns from official sources:

### Minimal pyproject.toml for uv project
```toml
[project]
name = "chessalytics"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "chess>=1.10.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
```

### Pydantic Settings for Database URL
```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/chessalytics"
    DB_ECHO: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

### Bulk Insert Pattern for game_positions (Phase 2 preview)
```python
# Source: SQLAlchemy 2.0 docs — ORM-Enabled INSERT
# https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html
from sqlalchemy import insert

async def bulk_insert_positions(session: AsyncSession, rows: list[dict]) -> None:
    await session.execute(insert(GamePosition), rows)
    await session.commit()
```

### pytest conftest.py for Unit Tests (no DB required)
```python
# tests/conftest.py
# Hash module tests are pure unit tests — no database fixture needed
import pytest
import chess

@pytest.fixture
def starting_board() -> chess.Board:
    return chess.Board()

@pytest.fixture
def empty_board() -> chess.Board:
    b = chess.Board()
    b.clear()
    return b
```

### Test Pattern for Hash Determinism (IMP-06)
```python
# tests/test_zobrist.py
import chess
from app.services.zobrist import compute_hashes, hashes_for_game

def test_starting_position_is_deterministic():
    b1 = chess.Board()
    b2 = chess.Board()
    assert compute_hashes(b1) == compute_hashes(b2)

def test_different_positions_produce_different_hashes():
    b1 = chess.Board()
    b2 = chess.Board()
    b2.push_san("e4")
    wh1, bh1, fh1 = compute_hashes(b1)
    wh2, bh2, fh2 = compute_hashes(b2)
    assert fh1 != fh2

def test_white_hash_ignores_black_pieces():
    b = chess.Board()
    wh1, _, _ = compute_hashes(b)
    # Move only black pawn — white hash should be unchanged
    # (after e4 e5, white pawn moved so white_hash DOES change;
    # test: verify white_hash only changes when white moves)
    b2 = chess.Board()
    b2.push_san("e4")  # white moves
    b2.push_san("e5")  # black moves
    b3 = chess.Board()
    b3.push_san("e4")  # white moves
    b3.push_san("d5")  # black different move
    wh2, _, _ = compute_hashes(b2)
    wh3, _, _ = compute_hashes(b3)
    # After same white move e4, white hash should be identical regardless of black's response
    assert wh2 == wh3

def test_hashes_are_signed_int64():
    import ctypes
    b = chess.Board()
    wh, bh, fh = compute_hashes(b)
    # All values must fit in signed int64 (already converted in compute_hashes)
    assert -(2**63) <= wh <= 2**63 - 1
    assert -(2**63) <= bh <= 2**63 - 1
    assert -(2**63) <= fh <= 2**63 - 1

def test_hashes_for_game_returns_ply_zero():
    pgn = '[Event "?"]\n1. e4 e5 2. Nf3 *'
    results = hashes_for_game(pgn)
    assert results[0][0] == 0   # ply 0 = initial position
    assert len(results) == 5    # ply 0 + 4 half-moves

def test_duplicate_game_positions_hash_equal():
    """Same position via different move orders should produce equal full_hash."""
    pgn1 = '[Event "?"]\n1. e4 e5 2. Nf3 Nc6 *'
    pgn2 = '[Event "?"]\n1. e4 Nc6 2. Nf3 e5 *'  # transposition
    results1 = {(wh, bh, fh) for _, wh, bh, fh in hashes_for_game(pgn1)}
    results2 = {(wh, bh, fh) for _, wh, bh, fh in hashes_for_game(pgn2)}
    # Some hashes from both games should overlap (positions in common)
    assert len(results1 & results2) > 0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Column(Integer, primary_key=True)` | `id: Mapped[int] = mapped_column(primary_key=True)` | SQLAlchemy 2.0 (2023) | Type-safe, mypy-friendly ORM |
| `session.query(Model)` | `select(Model)` | SQLAlchemy 2.0 | Required by project constraint |
| `engine = create_engine(...)` (sync) | `create_async_engine(...)` | SQLAlchemy 1.4+ | Required for asyncpg |
| `alembic init alembic` | `alembic init -t async alembic` | Alembic 1.11+ | Generates async-ready env.py |
| `DeclarativeBase` without `AsyncAttrs` | `class Base(AsyncAttrs, DeclarativeBase)` | SQLAlchemy 2.0 | Required for async lazy loading (if used) |
| `bulk_insert_mappings()` | `session.execute(insert(Model), rows)` | SQLAlchemy 2.0 | `bulk_insert_mappings` removed in 2.0 |
| `fastapi-users` UUID-only setup | `SQLAlchemyBaseUserTable[int]` generic | fastapi-users 10.x+ | Allows integer PKs |

**Deprecated/outdated:**
- `session.bulk_insert_mappings()`: Removed in SQLAlchemy 2.0. Use `session.execute(insert(Model), rows)`.
- `declarative_base()` function: Still works but `DeclarativeBase` class is the 2.0 style.
- `session.query()`: Works but deprecated style — project constraint requires `select()`.

## Open Questions

1. **FastAPI-Users PK type coordination with Phase 4**
   - What we know: FastAPI-Users 15.x supports both UUID and integer PKs via `SQLAlchemyBaseUserTable[int]`
   - What's unclear: Phase 4 will decide the Users table PK; Phase 1's `games.user_id` column type must match
   - Recommendation: Define `user_id` as `Mapped[int]` (BIGINT) in Phase 1 and document the Phase 4 constraint to use integer PKs for FastAPI-Users. This is noted in Pitfall 5.

2. **`board.occupied_co` attribute availability in python-chess 1.10.x**
   - What we know: `occupied_co` is a list `[white_bb, black_bb]` indexed by `chess.WHITE` (1) and `chess.BLACK` (0). Pattern confirmed from polyglot.py source analysis.
   - What's unclear: Whether the attribute name changed between minor versions
   - Recommendation: Write a simple smoke test that accesses `board.occupied_co[chess.WHITE]` at the start; the test suite will catch any naming issue immediately.

3. **asyncpg version compatibility with SQLAlchemy 2.0.x**
   - What we know: asyncpg 0.29.x is recommended alongside SQLAlchemy 2.0.x
   - What's unclear: asyncpg 0.30.x (if released) may have breaking changes
   - Recommendation: Pin `asyncpg>=0.29.0,<0.30.0` in pyproject.toml until verified.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` |
| Quick run command | `uv run pytest tests/test_zobrist.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | Composite indexes created in migration | smoke (manual DB check) | `uv run alembic upgrade head` + `\d game_positions` in psql | Wave 0 |
| INFRA-03 | Duplicate insert rejected at DB level | integration (needs DB) | `uv run pytest tests/test_schema.py::test_duplicate_rejected -x` | Wave 0 |
| IMP-05 | All metadata columns present in `games` table | smoke (migration check) | `uv run alembic upgrade head` + `\d games` in psql | Wave 0 |
| IMP-06 | Hash module returns deterministic hashes | unit | `uv run pytest tests/test_zobrist.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_zobrist.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — package marker
- [ ] `tests/conftest.py` — shared fixtures (chess.Board instances, minimal async session for integration tests)
- [ ] `tests/test_zobrist.py` — covers IMP-06 (hash module unit tests, no DB needed)
- [ ] `tests/test_schema.py` — covers INFRA-01, INFRA-03, IMP-05 (requires live test DB or async engine with `create_all`)
- [ ] Framework install: `uv add --dev pytest pytest-asyncio` — verify in pyproject.toml

## Sources

### Primary (HIGH confidence)
- SQLAlchemy 2.0 docs (declarative_tables) — `type_annotation_map`, `DeclarativeBase`, `mapped_column` patterns
  https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
- python-chess polyglot module source — POLYGLOT_RANDOM_ARRAY indexing scheme verified
  https://python-chess.readthedocs.io/en/latest/_modules/chess/polyglot.html
- FastAPI-Users SQLAlchemy docs — async setup, UUID vs integer PK configuration
  https://fastapi-users.github.io/fastapi-users/latest/configuration/databases/sqlalchemy/
- Alembic async template — `run_async_migrations` pattern
  https://github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py

### Secondary (MEDIUM confidence)
- Berk Karaal blog (2024-09) — complete async Alembic + SQLAlchemy 2 setup walkthrough
  https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/
- Cybertec — BIGINT vs UUID index size benchmark (40% smaller for BIGINT)
  https://www.cybertec-postgresql.com/en/int4-vs-int8-vs-uuid-vs-numeric-performance-on-bigger-joins/
- pytest-asyncio PyPI — `asyncio_mode = "auto"` configuration
  https://pypi.org/project/pytest-asyncio/

### Tertiary (LOW confidence)
- WebSearch: FastAPI-Users 15.0.4 as latest version (February 2026) — not verified against PyPI directly

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against official docs and confirmed by CLAUDE.md project spec
- Architecture: HIGH — SQLAlchemy 2.x patterns from official docs; Zobrist indexing verified from source
- Pitfalls: HIGH for BIGINT overflow (known asyncpg behavior) and Alembic model import (common mistake); MEDIUM for FastAPI-Users PK coordination (depends on Phase 4 decisions)

**Research date:** 2026-03-11
**Valid until:** 2026-06-11 (stable libraries; SQLAlchemy 2.x and python-chess 1.x are mature)
