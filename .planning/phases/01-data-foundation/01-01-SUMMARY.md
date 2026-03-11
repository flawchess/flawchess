---
phase: 01-data-foundation
plan: "01"
subsystem: database
tags: [postgresql, sqlalchemy, alembic, asyncpg, pydantic-settings, fastapi, python-chess]

# Dependency graph
requires: []
provides:
  - PostgreSQL schema with games and game_positions tables
  - SQLAlchemy 2.x async ORM models (Game, GamePosition)
  - Alembic async migration (initial schema)
  - FastAPI project skeleton with async engine and session factory
  - Pydantic v2 Settings loading DATABASE_URL from .env
affects: [02-import-pipeline, 03-analysis-api, 04-frontend-and-auth]

# Tech tracking
tech-stack:
  added:
    - fastapi[standard] 0.135.x
    - uvicorn[standard]
    - sqlalchemy[asyncio] 2.0.x
    - asyncpg 0.31.x
    - alembic 1.18.x
    - chess (python-chess) 1.11.x
    - pydantic 2.x
    - pydantic-settings 2.x
    - python-dotenv 1.x
    - pytest 9.x + pytest-asyncio
    - ruff
  patterns:
    - SQLAlchemy 2.x DeclarativeBase with type_annotation_map (all Mapped[int] -> BIGINT)
    - AsyncAttrs mixin on Base for async lazy loading compatibility
    - async_session_maker with expire_on_commit=False
    - Alembic initialized with -t async template
    - Pydantic v2 SettingsConfigDict(env_file=".env") (not legacy class Config)
    - server_default=func.now() for import timestamps (not Python-evaluated default)

key-files:
  created:
    - pyproject.toml
    - app/core/config.py
    - app/core/database.py
    - app/models/base.py
    - app/models/game.py
    - app/models/game_position.py
    - app/models/__init__.py
    - app/main.py
    - alembic.ini
    - alembic/env.py
    - alembic/versions/dcef507678d8_initial_schema.py
  modified: []

key-decisions:
  - "AsyncAttrs must be imported from sqlalchemy.ext.asyncio (not sqlalchemy.orm) in SQLAlchemy 2.0.x"
  - "user_id denormalized onto game_positions to enable single-table composite index lookups without joins"
  - "All hash columns BIGINT not nullable — every position must have all three hashes"
  - "UniqueConstraint on (platform, platform_game_id) enforced at database level"
  - "PostgreSQL started via brew install postgresql@17 and initialized locally for development"

patterns-established:
  - "Pattern 1: Base class always AsyncAttrs + DeclarativeBase with BIGINT type_annotation_map"
  - "Pattern 2: Alembic env.py imports all model modules before target_metadata assignment"
  - "Pattern 3: Settings use SettingsConfigDict(env_file='.env') Pydantic v2 style"
  - "Pattern 4: All session factories use expire_on_commit=False for async safety"

requirements-completed: [INFRA-01, INFRA-03, IMP-05]

# Metrics
duration: 5min
completed: 2026-03-11
---

# Phase 1 Plan 01: Scaffold Backend and Database Schema Summary

**FastAPI project skeleton with SQLAlchemy 2.x async models, BIGINT Zobrist hash columns, composite position indexes, and Alembic async migration applied to PostgreSQL**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-11T13:27:29Z
- **Completed:** 2026-03-11T13:31:58Z
- **Tasks:** 2
- **Files modified:** 18

## Accomplishments

- Scaffolded complete FastAPI project with uv, pyproject.toml, and all runtime/dev dependencies
- Defined SQLAlchemy 2.x async ORM models for `games` (26 columns, UniqueConstraint) and `game_positions` (7 columns, 3 composite hash indexes)
- Generated and applied Alembic async migration creating the full database schema in PostgreSQL
- All BIGINT columns, composite indexes (ix_gp_user_full_hash, ix_gp_user_white_hash, ix_gp_user_black_hash) and uq_games_platform_game_id confirmed via psql

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold project and define SQLAlchemy models** - `fbf3bd2` (feat)
2. **Task 2: Initialize Alembic and generate initial migration** - `4bebe9b` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `pyproject.toml` - Project dependencies and pytest/ruff config
- `.python-version` - Pin Python 3.13
- `.env.example` - Template env file for DATABASE_URL and DB_ECHO
- `app/__init__.py` - Package marker
- `app/main.py` - FastAPI app with /health endpoint
- `app/core/config.py` - Pydantic v2 Settings with DATABASE_URL
- `app/core/database.py` - Async engine, async_session_maker, get_async_session
- `app/models/base.py` - DeclarativeBase with AsyncAttrs and BIGINT type_annotation_map
- `app/models/game.py` - Game model with all metadata columns and UniqueConstraint
- `app/models/game_position.py` - GamePosition model with Zobrist hash columns and composite indexes
- `app/models/__init__.py` - Imports Game and GamePosition
- `app/routers/__init__.py` - Empty package marker
- `app/services/__init__.py` - Empty package marker
- `app/repositories/__init__.py` - Empty package marker
- `app/schemas/__init__.py` - Empty package marker
- `alembic.ini` - Alembic config with empty sqlalchemy.url (overridden in env.py)
- `alembic/env.py` - Async env.py with model imports and settings
- `alembic/versions/dcef507678d8_initial_schema.py` - Initial migration

## Decisions Made

- Used `AsyncAttrs` from `sqlalchemy.ext.asyncio` (not `sqlalchemy.orm`) — this is the correct location in SQLAlchemy 2.0.48
- Used `server_default=func.now()` for `imported_at` per plan instruction, not `default=datetime.utcnow` which would evaluate at class definition time
- Local PostgreSQL server installed via `brew install postgresql@17` and started as service; database created with `createdb chessalytics`
- .env uses `postgresql+asyncpg://ws80@localhost:5432/chessalytics` (no password for local trust auth)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed AsyncAttrs import path**
- **Found during:** Task 1 verification (import check)
- **Issue:** `from sqlalchemy.orm import AsyncAttrs` raised ImportError — `AsyncAttrs` is in `sqlalchemy.ext.asyncio`, not `sqlalchemy.orm`, in SQLAlchemy 2.0.48
- **Fix:** Changed import to `from sqlalchemy.ext.asyncio import AsyncAttrs`
- **Files modified:** `app/models/base.py`
- **Verification:** `uv run python -c "from app.models.game import Game; ..."` succeeds
- **Committed in:** fbf3bd2 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — wrong import path)
**Impact on plan:** Required for all models to be importable. One-line fix, no scope change.

## Issues Encountered

- PostgreSQL server not installed (only libpq client tools present). Installed `postgresql@17` via brew, started service, created database before generating migration. Plan noted this might be needed.

## User Setup Required

None beyond ensuring PostgreSQL is running locally. The .env file (gitignored) is pre-configured for the local dev database `ws80@localhost:5432/chessalytics`.

## Next Phase Readiness

- Database schema fully defined and applied — Phase 2 (Import Pipeline) can build on top of the `games` and `game_positions` tables
- Async session factory ready for use in repositories
- Models importable and verified — no circular import issues
- Alembic configured and working — future schema changes use `alembic revision --autogenerate`

## Self-Check: PASSED

- app/models/game.py: FOUND
- app/models/game_position.py: FOUND
- app/models/base.py: FOUND
- app/core/database.py: FOUND
- app/core/config.py: FOUND
- alembic/env.py: FOUND
- alembic/versions/dcef507678d8_initial_schema.py: FOUND
- Commit fbf3bd2: FOUND
- Commit 4bebe9b: FOUND

---
*Phase: 01-data-foundation*
*Completed: 2026-03-11*
