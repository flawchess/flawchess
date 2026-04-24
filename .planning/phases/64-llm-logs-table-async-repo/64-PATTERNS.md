# Phase 64: `llm_logs` Table & Async Repo — Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 9 (7 new + 2 modified)
**Analogs found:** 7 / 9 (two files have no in-repo analog — flagged for Wave 0 scaffolding)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/models/llm_log.py` | model | ORM / DDL | `app/models/game_position.py` (`__table_args__` + composite `Index(...)`) + `app/models/position_bookmark.py` (FK + `server_default=func.now()`) | hybrid (no single 1:1 match — JSONB has no precedent) |
| `app/schemas/llm_log.py` | schema | request-response / validation | `app/schemas/position_bookmarks.py` (`Literal` aliases + Pydantic v2 `BaseModel`) | exact (same shape: module-level `Literal`, `BaseModel` DTO) |
| `app/repositories/llm_log_repository.py` | repository | CRUD / own-session write | **Deviation pair**: `app/services/import_service.py::cleanup_orphaned_jobs` (OWN-SESSION pattern — lines 64–74) + `app/repositories/import_job_repository.py` (module-level async fn template — but takes caller `session`) | role-match with deliberate D-02 deviation |
| `alembic/versions/<ts>_<hash>_create_llm_logs.py` | migration | DDL | `alembic/versions/20260313_095730_00e469a985ef_add_bookmarks_table.py` (create_table + indexes) + `alembic/versions/20260311_133123_dcef507678d8_initial_schema.py` (inline `sa.ForeignKeyConstraint(...ondelete="CASCADE")` in create_table — lines 49–58) | role-match, but Phase 64 hand-edits for JSONB + DESC |
| `alembic/env.py` (modify) | config | side-effect imports | current file lines 10–17 (`noqa: F401` model imports) | exact (append one line) |
| `pyproject.toml` (modify) | config | dependency | lines 6–19 (existing `dependencies = [...]`) | exact |
| `tests/test_llm_log_repository.py` | test | integration / CRUD | `tests/test_bookmark_repository.py` (pytest-asyncio + `db_session` + `ensure_test_user`) | exact |
| `tests/test_llm_log_cascade.py` | test | integration / FK cascade | **NO ANALOG** — no existing test exercises `ON DELETE CASCADE` on user deletion | flag for Wave 0 (RESEARCH.md §Example 3 is the only reference) |
| `tests/test_llm_logs_migration.py` | test | integration / DDL inspection | **NO ANALOG** — no existing alembic smoke test (grep confirmed: only `conftest.py` calls `alembic_command.upgrade`) | flag for Wave 0 (RESEARCH.md §Example 4 is the only reference) |

**Layout note (per RESEARCH.md Assumption A7):** Tests go at the flat `tests/` root, NOT `tests/repositories/` / `tests/models/` / `tests/alembic/`. Matches existing convention; CONTEXT.md D-09's nested proposal is overridden.

---

## Pattern Assignments

### `app/models/llm_log.py` (model, ORM + DDL)

**Analogs (hybrid — no single file matches all three aspects):**
- `app/models/base.py` — `Base` import + `type_annotation_map` auto-conversion of `datetime.datetime → DateTime(timezone=True)`
- `app/models/position_bookmark.py` — FK `ondelete="CASCADE"` + `server_default=func.now()` for `created_at`
- `app/models/game_position.py` — `__table_args__` with multiple `Index(...)` entries, including `postgresql_where` / `postgresql_include` kwargs
- **NO ANALOG** for `postgresql.dialects.postgresql.JSONB` — first JSONB usage in the codebase (reference SQLAlchemy docs directly)

**`Base` inheritance + imports pattern** (`app/models/base.py` lines 1–11):
```python
import datetime

from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    type_annotation_map = {
        datetime.datetime: DateTime(timezone=True),
    }
```
**Implication for `llm_log.py`:** Declare `created_at: Mapped[datetime.datetime]` with no explicit `DateTime(timezone=True)` — the base's `type_annotation_map` handles it. Only add `server_default=func.now()`.

**FK + CASCADE + `server_default` pattern** (`app/models/position_bookmark.py` lines 10–28):
```python
class PositionBookmark(Base):
    __tablename__ = "position_bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    ...
    is_flipped: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
```
**Copy exactly** for `user_id` FK (note: Phase 64 OVERRIDES `index=True` — the five indexes are declared in `__table_args__`, not inline), `cache_hit` (`default=False, server_default="false"`), and `created_at`.

**CRITICAL type deviation:** `PositionBookmark.user_id` uses bare `Mapped[int]` which SQLAlchemy defaults to `Integer` — correct for `users.id`. Phase 64 must explicitly pass `Integer` as the first arg: `mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)` because `users.id` is 4-byte `Integer` (RESEARCH.md Pitfall 1). The log's OWN `id` stays `BigInteger` per D-05.

**`__table_args__` with multiple `Index(...)` pattern** (`app/models/game_position.py` lines 10–35):
```python
class GamePosition(Base):
    __tablename__ = "game_positions"
    __table_args__ = (
        # Composite indexes for the three query patterns (Phase 3)
        Index("ix_gp_user_full_hash", "user_id", "full_hash"),
        Index("ix_gp_user_white_hash", "user_id", "white_hash"),
        Index("ix_gp_user_black_hash", "user_id", "black_hash"),
        # Covering index for Phase 12 next-moves aggregation queries
        Index("ix_gp_user_full_hash_move_san", "user_id", "full_hash", "move_san"),
        # Partial index for endgame queries — only indexes rows where endgame_class IS NOT NULL
        Index(
            "ix_gp_user_endgame_class",
            "user_id",
            "endgame_class",
            postgresql_where=text("endgame_class IS NOT NULL"),
        ),
        ...
    )
```
**Copy the shape** for Phase 64's 5 indexes. The `postgresql_where=` kwarg here is analogous to `postgresql_ops={"created_at": "DESC"}` in Phase 64 — both are Postgres-specific index kwargs that SQLAlchemy passes through to the DDL. Precedent exists in the codebase for trusting these kwargs.

**`__table_args__` simpler pattern with UniqueConstraint + Index** (`app/models/opening.py` lines 7–13):
```python
class Opening(Base):
    __tablename__ = "openings"
    __table_args__ = (
        UniqueConstraint("eco", "name", "pgn", name="uq_openings_eco_name_pgn"),
        Index("ix_openings_eco_name", "eco", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
```
**`BigInteger` hash column precedent** from same file lines 21–23:
```python
full_hash: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
white_hash: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
black_hash: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
```
Use `BigInteger` for `llm_logs.id` (D-05).

**JSONB — no in-codebase analog.** Reference directly (first JSONB usage):
```python
from sqlalchemy.dialects.postgresql import JSONB

filter_context: Mapped[dict] = mapped_column(JSONB, nullable=False)
flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```
Per RESEARCH.md Pattern 1 + Assumption A3 (asyncpg has native JSONB codec; roundtrip to Python `dict`/`list` is seamless).

**`users.id` type reference** (`app/models/user.py` lines 13–16):
```python
class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
```
Bare `Mapped[int]` → `Integer` (4-byte). The FK column in `llm_log.py` must use `Integer`, not `BigInteger`.

---

### `app/schemas/llm_log.py` (schema, request-response / validation)

**Analog:** `app/schemas/position_bookmarks.py`

**Module header + Literal alias pattern** (lines 1–11):
```python
"""Pydantic v2 schemas for position bookmark CRUD operations."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator

from app.models.position_bookmark import PositionBookmark

Color = Literal["white", "black"]
BookmarkMatchSide = Literal["mine", "opponent", "both", "full"]
```
**Copy for `llm_log.py`:**
```python
"""Pydantic v2 schemas for llm_logs writes.

LlmLogEndpoint is a single-member Literal in Phase 64 — extend it when new
LLM features ship. See Phase 64 CONTEXT.md D-04.
"""

from typing import Any, Literal

from pydantic import BaseModel

LlmLogEndpoint = Literal["insights.endgame"]
```

**`BaseModel` DTO pattern** (`app/schemas/position_bookmarks.py` lines 14–29):
```python
class PositionSuggestion(BaseModel):
    """A single position bookmark suggestion derived from most-played openings."""

    white_hash: str
    black_hash: str
    full_hash: str
    fen: str
    moves: list[str]
    color: Color
    game_count: int
    opening_name: str | None
    opening_eco: str | None
```
Note: no `ConfigDict`, no `field_validator` required for Phase 64's DTO — it's a write-side input record, not a response serializer. Stick to plain fields. See RESEARCH.md Pattern 3 for the full `LlmLogCreate` shape (already locked in CONTEXT.md §Specifics).

---

### `app/repositories/llm_log_repository.py` (repository, CRUD + own-session write)

**Deliberate D-02 deviation — show BOTH analogs so the planner sees the difference:**

#### Analog A (shape copy): `app/repositories/import_job_repository.py` — module-level async template, but **takes caller session**

Lines 1–42:
```python
"""Import job repository: CRUD for the import_jobs table."""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportJob


async def create_import_job(
    session: AsyncSession,
    job_id: str,
    user_id: int,
    platform: str,
    username: str,
) -> ImportJob:
    """Create a new ImportJob row with status='pending'.

    Args:
        session: AsyncSession to use.
        ...
    """
    job = ImportJob(
        id=job_id,
        user_id=user_id,
        ...
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return job
```
**What to copy:** module-docstring format, per-function Google-style docstrings (`Args:` / `Returns:`), module-level `async def`, `session.add(...)` + `await session.refresh(row)`.

**What to REJECT:** the `session: AsyncSession` parameter AND `session.flush()` (no commit). Phase 64's `create_llm_log` takes `data: LlmLogCreate` only AND must `await session.commit()` (RESEARCH.md Pitfall 4).

#### Analog B (semantic copy — own-session, own-commit): `app/services/import_service.py::cleanup_orphaned_jobs`

Lines 1–28 + 64–74:
```python
"""Import service: in-memory job registry and background import orchestrator."""

import asyncio
...

from app.core.database import async_session_maker
...


async def cleanup_orphaned_jobs() -> None:
    """Mark any DB jobs stuck in pending/in_progress as failed.

    Called at startup — no in-memory tasks survive a restart, so any
    non-terminal DB jobs are orphaned.
    """
    async with async_session_maker() as session:
        count = await import_job_repository.fail_orphaned_jobs(session)
        await session.commit()
        if count:
            logger.info("Marked %d orphaned import job(s) as failed", count)
```
**What to copy:** `from app.core.database import async_session_maker`, `async with async_session_maker() as session:`, and the explicit `await session.commit()` before the block exits. This is the entire D-02 skeleton.

**Read helper — takes caller session (matches Analog A):** `get_latest_log_by_hash` takes `session: AsyncSession` as first param. See `app/repositories/import_job_repository.py::get_latest_for_user_platform` lines 77–110 for the `select(...).where(...).order_by(...desc()).limit(1)` + `scalar_one_or_none()` shape to copy verbatim.

**`async_session_maker` reference** (`app/core/database.py` lines 1–15):
```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
```
**Key fact** (repeated in RESEARCH.md Pitfall 4): `expire_on_commit=False` means `await session.refresh(row)` after `await session.commit()` is safe and returns a live ORM object — `create_llm_log` can return the full `LlmLog` instance as D-02 / CONTEXT.md Discretion §"return full LlmLog" requires.

---

### `alembic/versions/<ts>_<hash>_create_llm_logs.py` (migration, DDL)

**Analog A (header + autogenerate skeleton):** `alembic/versions/20260414_184435_179cfbd472ef_add_base_time_seconds_and_increment_.py` lines 1–19:
```python
"""add base_time_seconds and increment_seconds to games

Revision ID: 179cfbd472ef
Revises: 78845c63e456
Create Date: 2026-04-14 18:44:35.344792+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "179cfbd472ef"
down_revision: Union[str, Sequence[str], None] = "78845c63e456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```
**Copy header format.** Phase 64's migration's `down_revision` will be `"179cfbd472ef"` (current head at research time — planner confirms with `uv run alembic current` right before running autogenerate in case another phase lands first).

**Analog B (create_table + index pattern):** `alembic/versions/20260313_095730_00e469a985ef_add_bookmarks_table.py` lines 21–46:
```python
def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('bookmarks',
    sa.Column('id', sa.BIGINT(), nullable=False),
    sa.Column('user_id', sa.BIGINT(), nullable=False),
    sa.Column('label', sa.String(length=200), nullable=False),
    sa.Column('target_hash', sa.BIGINT(), nullable=False),
    ...
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bookmarks_user_id'), 'bookmarks', ['user_id'], unique=False)
```

**Analog C (inline FK + CASCADE inside create_table):** `alembic/versions/20260311_133123_dcef507678d8_initial_schema.py` lines 49–63:
```python
op.create_table('game_positions',
sa.Column('id', sa.BIGINT(), nullable=False),
sa.Column('game_id', sa.BIGINT(), nullable=False),
sa.Column('user_id', sa.BIGINT(), nullable=False),
sa.Column('ply', sa.BIGINT(), nullable=False),
sa.Column('full_hash', sa.BIGINT(), nullable=False),
sa.Column('white_hash', sa.BIGINT(), nullable=False),
sa.Column('black_hash', sa.BIGINT(), nullable=False),
sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
sa.PrimaryKeyConstraint('id')
)
op.create_index(op.f('ix_game_positions_game_id'), 'game_positions', ['game_id'], unique=False)
op.create_index('ix_gp_user_black_hash', 'game_positions', ['user_id', 'black_hash'], unique=False)
op.create_index('ix_gp_user_full_hash', 'game_positions', ['user_id', 'full_hash'], unique=False)
op.create_index('ix_gp_user_white_hash', 'game_positions', ['user_id', 'white_hash'], unique=False)
```
**Copy for Phase 64:** inline `sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')` inside `op.create_table(...)`. Keep the ASC indexes as-is; add `postgresql_ops={"created_at": "DESC"}` kwarg to the three DESC composite indexes (RESEARCH.md Pattern 4 has the full template). Drop the `op.f(...)` wrapper for named indexes — not needed when the index name is fully explicit.

**Hand-edit differences versus autogenerate** (RESEARCH.md Pitfall 2):
1. JSONB: autogenerate emits `sa.JSON()` — change to `postgresql.JSONB()` (add `from sqlalchemy.dialects import postgresql`).
2. DESC: autogenerate drops `postgresql_ops={"created_at": "DESC"}` — re-add on the 3 composite indexes.
3. FK column type: confirm `sa.Integer()` (not `sa.BigInteger()`) for `user_id` to match `users.id`.

---

### `alembic/env.py` (config, side-effect imports)

**Analog:** current file lines 10–17 — this IS the registration point (RESEARCH.md finding #3).

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import settings
from app.models.base import Base
from app.models.position_bookmark import PositionBookmark  # noqa: F401
from app.models.game import Game  # noqa: F401
from app.models.game_position import GamePosition  # noqa: F401
from app.models.oauth_account import OAuthAccount  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.opening import Opening  # noqa: F401
```
**Add one line after the existing block:**
```python
from app.models.llm_log import LlmLog  # noqa: F401
```
Alphabetical order is not enforced in the existing list — append is fine. `app/models/__init__.py` (5 lines, currently re-exports `Game`, `GamePosition`, `ImportJob` only) is NOT where autogenerate looks. Updating `__init__.py` is cosmetic — skip it unless there's a reason to add `LlmLog` as a public re-export.

---

### `pyproject.toml` (config, dependency)

**Analog:** current file lines 6–19.

```toml
dependencies = [
    "fastapi[standard]>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "chess>=1.10.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.27.0",
    "fastapi-users[oauth,sqlalchemy]>=15.0.4",
    "httpx-oauth>=0.16.1",
    "sentry-sdk[fastapi]>=2.54.0",
]
```
**Add one line:**
```toml
"genai-prices>=0.0.56,<0.1.0",
```
Version cap per RESEARCH.md §Standard Stack (pre-1.0 library — likely to break minor). Prefer adding via `uv add 'genai-prices>=0.0.56,<0.1.0'` so `uv.lock` updates in the same commit.

---

### `tests/test_llm_log_repository.py` (test, integration)

**Analog:** `tests/test_bookmark_repository.py` lines 1–76 — exact shape match for async repo tests with `db_session` + `ensure_test_user`.

**Imports + module docstring pattern** (lines 1–38):
```python
"""Integration tests for position bookmark repository.

Coverage:
- TestCRUD: BKM-01 - create, list, update, delete position bookmarks
- TestReorder: BKM-02 - drag-reorder support with sort_order reassignment
- TestIsolation: BKM-05 - per-user isolation enforced at repository layer
...
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.position_bookmark_repository import (
    create_bookmark,
    ...
)
from app.schemas.position_bookmarks import (
    BookmarkMatchSide,
    Color,
    PositionBookmarkCreate,
    PositionBookmarkUpdate,
)
```

**Fixture pattern — ensure user FK target exists** (lines 67–76):
```python
# All user IDs used across bookmark tests
_TEST_USER_IDS = [1, 2, 3, 10, 20, 99, 500, 501, 502, 503, 504, 505, 600, 601, 700, 701, 710]


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure all test user IDs exist in the users table before each test."""
    from tests.conftest import ensure_test_user
    for uid in _TEST_USER_IDS:
        await ensure_test_user(db_session, uid)
```

**Caveat for Phase 64 (RESEARCH.md Pitfall 5):** `db_session` rolls back at end of test. `create_llm_log` opens its OWN session (D-02) which uses a DIFFERENT connection from the pool — its commit WILL persist outside the test's rollback scope. Options:
1. Build a bespoke `fresh_test_user` fixture that creates + commits a user via `async_session_maker()` and deletes (CASCADE) at teardown. RESEARCH.md §Pitfall 5 recommended pattern.
2. Use unique `user_id` per test (e.g. `uuid.uuid4().int % 1_000_000_000`) to avoid cross-test residue in the committed-rows table.

Recommend option 1 (see RESEARCH.md Pitfall 5 example). Place the fixture in `tests/conftest.py` so the cascade test can share it.

**`ensure_test_user` helper** (`tests/conftest.py` lines 155–165):
```python
async def ensure_test_user(session: AsyncSession, user_id: int) -> None:
    """Create a test user with the given ID if it doesn't already exist."""
    existing = (await session.execute(select(User).where(User.id == user_id))).unique()
    if existing.scalar_one_or_none() is None:
        session.add(
            User(id=user_id, email=f"test-{user_id}@example.com", hashed_password="fakehash")
        )
        await session.flush()
```
NOT directly usable for Phase 64 because it uses `db_session.flush()` (caller's transaction — rolls back). For the cascade test, a user that actually persists is needed. Use RESEARCH.md §Pitfall 5's `fresh_test_user` fixture with `session.commit()`.

**Test test_create_llm_log — concrete template:** see RESEARCH.md §Example 1.
**cost_unknown fallback tests:** see RESEARCH.md §Example 2.

---

### `tests/test_llm_log_cascade.py` (test, integration)

**NO IN-REPO ANALOG.** Grep for `cascade|ondelete` in `tests/` returned zero hits.

**Reference:** RESEARCH.md §Example 3 is the only template. Key shape:
```python
# Setup: create user + log via repo's own-session
session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
async with session_maker() as session:
    user = User(email="cascade@example.com", hashed_password="x")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    user_id = user.id

data = LlmLogCreate(user_id=user_id, ...)
row = await create_llm_log(data)
log_id = row.id

# Act: delete user
async with session_maker() as session:
    await session.execute(delete(User).where(User.id == user_id))
    await session.commit()

# Assert: log row is gone
async with session_maker() as session:
    result = await session.execute(select(LlmLog).where(LlmLog.id == log_id))
    assert result.scalar_one_or_none() is None
```

**Scaffolding note for the planner:** Flag in PLAN.md that this is a new test-infrastructure pattern. Document explicitly in the test's module docstring why it doesn't use the standard `db_session` fixture.

---

### `tests/test_llm_logs_migration.py` (test, integration)

**NO IN-REPO ANALOG.** Grep for `get_table_names|get_indexes|inspect` across `tests/` returned only `conftest.py` (which uses `alembic_command.upgrade`, not schema inspection).

**Reference:** RESEARCH.md §Example 4. Key shape:
```python
import pytest
from sqlalchemy import inspect


@pytest.mark.asyncio
async def test_llm_logs_table_exists_with_all_columns_and_indexes(test_engine):
    def _inspect(sync_conn):
        insp = inspect(sync_conn)
        assert "llm_logs" in insp.get_table_names()

        cols = {c["name"] for c in insp.get_columns("llm_logs")}
        expected = {"id", "user_id", "created_at", "endpoint", ...}
        assert expected <= cols, f"missing columns: {expected - cols}"

        indexes = {i["name"] for i in insp.get_indexes("llm_logs")}
        expected_ix = {"ix_llm_logs_created_at", ...}
        assert expected_ix <= indexes, f"missing indexes: {expected_ix - indexes}"

    async with test_engine.connect() as conn:
        await conn.run_sync(_inspect)
```

Uses existing `test_engine` fixture from `tests/conftest.py` lines 69–99 — that fixture already runs `alembic upgrade head` before the first test. So no migration rerun is needed in the smoke test; it inspects the schema produced by the session-scoped `test_engine`.

**DESC ordering is NOT observable via `inspect.get_indexes()`** — the public API only reports column names, not ASC/DESC. For true DESC verification, either (a) do a raw `pg_indexes.indexdef` query (`select indexdef from pg_indexes where indexname = 'ix_llm_logs_user_id_created_at'`) and regex for `DESC`, or (b) rely on manual `psql \d llm_logs` verification after migration. Planner decides — RESEARCH.md Validation Architecture table notes this gap.

---

## Shared Patterns

### Pattern S1: Module-level async repo functions, Google-style docstrings

**Source:** `app/repositories/import_job_repository.py` (entire file)

**Apply to:** `app/repositories/llm_log_repository.py`

Every repo function is `async def`, module-level (no class), with a docstring that has `Args:` / `Returns:` / optional `Raises:` sections. Module docstring is a one-liner: `"""X repository: Y for the Z table."""` — **Phase 64 extends this one-liner to 3–5 lines to call out the D-02 deviation** (per CONTEXT.md §Specifics last bullet).

### Pattern S2: `async_session_maker` own-scope + explicit `await session.commit()`

**Source:** `app/services/import_service.py::cleanup_orphaned_jobs` lines 64–74

**Apply to:** `app/repositories/llm_log_repository.py::create_llm_log`

```python
async with async_session_maker() as session:
    # ... add + flush/refresh ...
    await session.commit()
```
Do NOT copy `import_job_repository.create_import_job`'s `await session.flush()` (no commit — caller commits). Phase 64 commits.

### Pattern S3: CLAUDE.md compliance — `Literal` over bare `str`, explicit return types, no `# type: ignore`

**Source:** CLAUDE.md §Coding Guidelines + `app/schemas/position_bookmarks.py` lines 10–11

**Apply to:** all new `.py` files. `LlmLogEndpoint = Literal["insights.endgame"]`; every `async def` has an explicit `-> ReturnType`; use `# ty: ignore[<rule>]` only where SQLAlchemy forward refs force it (none expected in Phase 64).

### Pattern S4: No f-string interpolation of runtime vars into error messages

**Source:** CLAUDE.md §Error Handling & Sentry + CONTEXT.md D-08

**Apply to:** `app/repositories/llm_log_repository.py`

Only exception allowed per SC #4: the stable `"cost_unknown:<model>"` prefix. Treated as a composite enum-like marker, not a dynamic error string. No `raise RuntimeError(f"Failed for user {user_id}")` — let SQLAlchemy/asyncpg exceptions propagate verbatim; Phase 65's caller captures + sets Sentry context.

### Pattern S5: FK to `users.id` with `ondelete="CASCADE"` (mandatory per CLAUDE.md DB rules)

**Source:** `app/models/position_bookmark.py` line 14–16, `app/models/game_position.py` lines 41–43, migration lines 49–58 of `20260311_133123_dcef507678d8_initial_schema.py`.

**Apply to:** `app/models/llm_log.py` + migration.

```python
user_id: Mapped[int] = mapped_column(
    Integer,  # EXPLICIT — users.id is Integer not BigInteger
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
)
```

### Pattern S6: `server_default=func.now()` for created timestamps

**Source:** `app/models/position_bookmark.py` lines 25–28 + `app/models/user.py` lines 23–25 + `app/models/import_job.py` lines 24–27

**Apply to:** `app/models/llm_log.py` `created_at` column.

```python
created_at: Mapped[datetime.datetime] = mapped_column(
    nullable=False,
    server_default=func.now(),
)
```
The `type_annotation_map` in `Base` auto-converts to `DateTime(timezone=True)` — no explicit type arg needed.

### Pattern S7: Pydantic v2 `BaseModel` — no `ConfigDict` unless ORM-roundtrip required

**Source:** `app/schemas/position_bookmarks.py` lines 14–25 (no `ConfigDict` on PositionSuggestion, which is pure read-side)

**Apply to:** `app/schemas/llm_log.py::LlmLogCreate`. Input-only DTO, no serialization roundtrip, no need for `ConfigDict(from_attributes=True)`.

---

## No Analog Found

| File | Role | Data Flow | Reason | Mitigation |
|------|------|-----------|--------|------------|
| `tests/test_llm_log_cascade.py` | test | FK cascade | No existing test in `tests/` exercises `ON DELETE CASCADE` — all existing tests use the rolled-back `db_session` fixture which prevents commits | Use RESEARCH.md §Example 3 verbatim as the starting template. Add a `fresh_test_user` fixture to `tests/conftest.py` (new). |
| `tests/test_llm_logs_migration.py` | test | DDL inspection | No existing alembic/DDL smoke test exists; `conftest.py` runs `alembic upgrade head` but does not assert on the result | Use RESEARCH.md §Example 4 verbatim. Relies on the existing `test_engine` fixture which already runs migrations — no new fixture needed. |
| `app/models/llm_log.py` — JSONB columns | model | ORM | No prior JSONB usage in codebase (position_bookmarks uses Text-encoded JSON for `moves` — migration-era choice) | Reference `sqlalchemy.dialects.postgresql.JSONB` directly; asyncpg native codec handles roundtrip (RESEARCH.md Assumption A3). |

---

## Metadata

**Analog search scope:**
- `app/models/` (7 files)
- `app/repositories/` (surveyed — confirmed `import_job_repository.py` is closest analog)
- `app/schemas/` (11 files — `position_bookmarks.py` wins on Literal + BaseModel shape)
- `app/services/import_service.py` (own-session precedent confirmed at lines 64–74)
- `app/core/database.py` (full file, 21 lines)
- `alembic/env.py` (full file, 100 lines)
- `alembic/versions/*.py` (40 migrations — 4 read in detail: bookmarks create, import_jobs create, initial_schema, FK-constraints migration)
- `tests/` (41 test files globbed; cascade/DDL-inspection patterns confirmed absent via Grep)

**Files scanned in detail:** 16
**Pattern extraction date:** 2026-04-20
**Phase:** 64 — `llm_logs` Table & Async Repo
