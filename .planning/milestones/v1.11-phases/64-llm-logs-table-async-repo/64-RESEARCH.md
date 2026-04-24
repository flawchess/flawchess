# Phase 64: `llm_logs` Table & Async Repo — Research

**Researched:** 2026-04-20
**Domain:** Backend DB layer (SQLAlchemy 2.x async model + Alembic migration + async write repo)
**Confidence:** HIGH

## Summary

Phase 64 ships a single new table (`llm_logs`), one SQLAlchemy 2.x ORM model, one Alembic
migration, and one async repository (`create_llm_log` + at least one read helper) that Phase 65
will call from inside the `POST /api/insights/endgame` endpoint. CONTEXT.md has locked almost
every implementation decision (D-01 through D-09) including the repo-opens-its-own-session
deviation (D-02). Research focus was on closing the three external unknowns the CONTEXT.md
explicitly delegated to Claude's Discretion:

1. **`genai-prices` error semantics** — Verified via upstream source: `calc_price` raises
   `LookupError` when the model cannot be matched. `[VERIFIED: data_snapshot.py Snapshot.calc]`
2. **Alembic autogenerate + DESC indexes** — Verified via upstream issue tracker: Alembic
   autogenerate does NOT reliably preserve DESC ordering on indexes (issues #1166, #1213, #1285).
   The three DESC indexes in D-07 must be hand-written in the migration; autogenerate output is
   starting scaffold only. `[VERIFIED: sqlalchemy/alembic issue tracker]`
3. **`app/models/__init__.py` registration is NOT how autogenerate discovers models** — Verified
   in codebase: `app/models/__init__.py` only exports 3 of 7 models; autogenerate sees models via
   `alembic/env.py`'s `noqa: F401` imports. The new `LlmLog` MUST be added to `env.py`; updating
   `__init__.py` is cosmetic. `[VERIFIED: app/models/__init__.py + alembic/env.py]`

A fourth unknown surfaced during codebase inspection: **`users.id` is `Integer` (4-byte), not
`BigInteger`.** CONTEXT.md D-06 wrote "BigInt FK → users.id" but the production column is
32-bit integer (verified via `psql \d users`). The FK column must be `Integer` to match, not
`BigInteger`. The log's own `id` can and should still be `BigInteger` per D-05.
`[VERIFIED: psql \d users on dev DB + app/models/user.py line 16]`

**Primary recommendation:** Run `uv run alembic revision --autogenerate -m "create llm_logs"`
to generate the migration skeleton, then hand-edit to (a) convert `Integer` default JSON cols
to `postgresql.JSONB`, (b) add `postgresql_ops={"created_at": "DESC"}` for the three
descending-order composite indexes, (c) verify FK is `sa.Integer` (not BigInteger) matching
`users.id`. Ship the repo as a module of three functions (`create_llm_log`, one
Phase-65-stub read helper, and nothing else) with a module docstring that calls out the
D-02 own-session deviation.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DDL (table + indexes) | Alembic migration | — | Standard ORM-backed migration pattern; `app/models/llm_log.py` is source of truth but `alembic/env.py` autogenerate-from-metadata is the delivery channel |
| Column types / constraints | ORM model | Alembic (echoed) | `app/models/llm_log.py` owns the Python-side types; the migration file mirrors them as raw `sa.*` calls |
| Input validation (LLM call sites) | Pydantic v2 schema | — | `app/schemas/llm_log.py` owns `LlmLogCreate`; repo accepts schema instance (D-01) |
| Cost computation | Repository | — | `create_llm_log` calls `genai-prices.calc_price` internally; callers never import `genai-prices` (D-03) |
| DB write (INSERT + commit) | Repository | — | Repo opens its own `async_session_maker()` scope (D-02) — diverges from co-transactional pattern |
| Cascade-on-user-delete | Postgres FK | — | `ON DELETE CASCADE` enforced by `ForeignKey(..., ondelete="CASCADE")` per CLAUDE.md DB rules |
| Sentry capture | Caller (Phase 65) | — | Repo re-raises on DB failure; `sentry_sdk.capture_exception` belongs at the router/service catch block (D-08) |

## Standard Stack

### Core (already in `pyproject.toml`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlalchemy[asyncio]` | ≥ 2.0.0 (installed 2.x async API) | ORM + AsyncSession | Project-wide choice per CLAUDE.md |
| `alembic` | ≥ 1.13.0 | Migrations | Integrated in CI (`deploy/entrypoint.sh`) |
| `asyncpg` | ≥ 0.29.0 | Postgres driver | Project-wide choice; JSONB returns `dict` natively |
| `pydantic` | ≥ 2.0.0 | `LlmLogCreate` schema | Pydantic v2 is the project default |

### New (to add in Phase 64)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `genai-prices` | 0.0.56 (latest, released 2026-03-20) | Compute `cost_usd` from `(model, input_tokens, output_tokens)` | SEED-003 §Observability calls out `genai-prices` explicitly; published by the pydantic org (same vendor as pydantic-ai); no realistic alternative |

`[VERIFIED: PyPI registry, 2026-04-20]` — `curl https://pypi.org/pypi/genai-prices/json` returned
version `0.0.56`, released `2026-03-20T20:33:02Z`, `requires_python: >=3.9`.

**Version pinning:** Pin as `genai-prices>=0.0.56,<0.1.0` — the library is pre-1.0 and likely
to introduce breaking API changes in minor releases. Revisit the cap when it hits 1.0.

**Installation:**
```bash
uv add genai-prices
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `genai-prices` | Hand-maintain a price table in `app/core/config.py` | Rejected. Forces ops to track per-model price changes across 4+ providers; SEED-003 explicitly names `genai-prices` as the source of truth |
| SQLAlchemy 2.x `Mapped[dict] = mapped_column(JSONB, ...)` | `Text` with app-side JSON encode/decode | Rejected. JSONB is queryable (`filter_context->>'recency'`) and the v1.0 `position_bookmarks.moves` workaround (Text-encoded JSON) was a migration-era choice, not the current pattern |
| Pydantic `LlmLogCreate` DTO (D-01) | 16-kwarg `create_llm_log(...)` signature | Rejected by D-01 — DTO is type-safe, trivially fixtureable, consistent with `app/schemas/` layer |

## Architecture Patterns

### System Architecture Diagram

```
Phase 65 caller (insights router/service)
        │
        │  constructs LlmLogCreate(...) with Usage fields already extracted
        │  from pydantic-ai Agent.run() result + request context
        ▼
app.repositories.llm_log_repository.create_llm_log(data: LlmLogCreate)
        │
        │ 1. Compute cost_usd:
        │      try:
        │          price = genai_prices.calc_price(
        │              Usage(input_tokens, output_tokens),
        │              model_ref=<model from data>,
        │          )
        │          cost_usd = Decimal(str(price.total_price))
        │      except LookupError:
        │          cost_usd = Decimal("0")
        │          data.error = ";".join(filter(None, [data.error, f"cost_unknown:{model}"]))
        │
        │ 2. Open own session scope (D-02):
        │      async with async_session_maker() as session:
        │          row = LlmLog(**data.model_dump(), cost_usd=cost_usd)
        │          session.add(row)
        │          await session.commit()
        │          await session.refresh(row)
        │          return row
        ▼
Postgres llm_logs table (17 columns + 5 indexes)
        │
        │ ON DELETE CASCADE via users.id FK
        ▼
GDPR deletion path: DELETE FROM users WHERE id=... → all llm_logs rows removed
```

### Recommended Project Structure

```
app/
├── models/
│   └── llm_log.py                    # ORM: class LlmLog(Base) — 17 columns, 5 indexes in __table_args__
├── schemas/
│   └── llm_log.py                    # LlmLogEndpoint Literal + LlmLogCreate DTO
├── repositories/
│   └── llm_log_repository.py         # create_llm_log + get_latest_log_by_hash (Phase 65 stub)
alembic/
├── env.py                            # ADD: from app.models.llm_log import LlmLog  # noqa: F401
└── versions/
    └── <timestamp>_<hash>_create_llm_logs.py   # autogenerate → hand-edit for JSONB + DESC indexes
tests/
├── repositories/
│   └── test_llm_log_repository.py    # insert round-trip + cost_unknown fallback
├── models/
│   └── test_llm_log_cascade.py       # user delete → log cascade
└── alembic/
    └── test_llm_logs_migration.py    # (optional) inspect table + indexes exist
```

Note: `tests/alembic/` and `tests/repositories/` and `tests/models/` subdirectories do not yet
exist. The convention in the repo today is flat (`tests/test_bookmark_repository.py` etc.), but
CONTEXT.md D-09 proposes the nested layout. Planner should decide: flat keeps consistency,
nested gives headroom for additional phase-64-style repos. **Recommend flat** (`tests/test_llm_log_repository.py`,
`tests/test_llm_log_cascade.py`, `tests/test_llm_logs_migration.py`) to match existing
convention. Zero reason to change layout mid-milestone.

### Pattern 1: SQLAlchemy 2.x model with JSONB + composite index + DESC

```python
# app/models/llm_log.py
import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class LlmLog(Base):
    """One row per LLM cache-miss call. Generic across future LLM features.

    See SEED-003 §"Log table schema" and Phase 64 CONTEXT.md for the locked
    column set and index plan. See Phase 64 D-02 for the repo-owned-session
    deviation from `import_job_repository`'s co-transactional pattern.
    """

    __tablename__ = "llm_logs"
    __table_args__ = (
        Index("ix_llm_logs_created_at", "created_at"),
        Index(
            "ix_llm_logs_user_id_created_at",
            "user_id",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index("ix_llm_logs_findings_hash", "findings_hash"),
        Index(
            "ix_llm_logs_endpoint_created_at",
            "endpoint",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index(
            "ix_llm_logs_model_created_at",
            "model",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # NOTE: users.id is Integer (not BigInteger) — FK type must match exactly.
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    endpoint: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    findings_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 hex = 64 chars
    filter_context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    cache_hit: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**When to use:** Exactly this pattern for Phase 64's `LlmLog` model.

**Sources:**
- [SQLAlchemy 2.0 declarative + `postgresql_ops`](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#operator-classes)
- [Alembic autogenerate caveats for Index ordering](https://github.com/sqlalchemy/alembic/issues/1166)
- Codebase: `app/models/position_bookmark.py` (FK + server_default pattern); `app/models/game_position.py` (composite Index + `__table_args__` pattern).

### Pattern 2: Repo with own-session scope (D-02 deviation)

```python
# app/repositories/llm_log_repository.py
"""LLM log repository: async write + minimal read for the llm_logs table.

UNLIKE other repositories in this package, `create_llm_log` opens its OWN async
session and commits independently so log rows survive caller rollbacks. This is
intentional: llm_logs captures LLM failures, and if the caller's request-scoped
session rolls back (HTTPException, validation error, pydantic-ai crash), the log
row must still persist. See Phase 64 CONTEXT.md D-02.

`create_llm_log` computes cost_usd internally via genai-prices.calc_price and
appends `cost_unknown:<model>` to the row's `error` on LookupError (see D-03).
"""
from decimal import Decimal

from genai_prices import Usage, calc_price
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.llm_log import LlmLog
from app.schemas.llm_log import LlmLogCreate

_COST_UNKNOWN_PREFIX = "cost_unknown:"  # keep LIKE-queryable


async def create_llm_log(data: LlmLogCreate) -> LlmLog:
    """Persist one llm_logs row. Computes cost_usd via genai-prices.

    On LookupError from genai-prices (unknown model), sets cost_usd=0 and
    appends `cost_unknown:<model>` to data.error. Never swallows DB errors.
    """
    cost_usd = _compute_cost(data.model, data.input_tokens, data.output_tokens)
    error = data.error
    if cost_usd is None:
        cost_marker = f"{_COST_UNKNOWN_PREFIX}{data.model}"
        error = f"{error}; {cost_marker}" if error else cost_marker
        cost_usd = Decimal("0")

    async with async_session_maker() as session:
        row = LlmLog(
            **data.model_dump(exclude={"error"}),
            error=error,
            cost_usd=cost_usd,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal | None:
    """Return cost in USD as Decimal, or None if genai-prices can't match the model."""
    try:
        price = calc_price(
            Usage(input_tokens=input_tokens, output_tokens=output_tokens),
            model_ref=model,
        )
    except LookupError:
        return None
    # genai-prices returns Decimal already; Decimal(str(...)) is defensive normalization.
    return Decimal(str(price.total_price))


async def get_latest_log_by_hash(
    session: AsyncSession,
    findings_hash: str,
    prompt_version: str,
    model: str,
) -> LlmLog | None:
    """Phase 65 cache-lookup stub. Returns most recent successful log for the key.

    UNLIKE create_llm_log, this read helper takes a caller-supplied session —
    Phase 65's cache-lookup path already has one, and reads don't have the
    durability-across-rollback motivation that writes do.
    """
    result = await session.execute(
        select(LlmLog)
        .where(
            LlmLog.findings_hash == findings_hash,
            LlmLog.prompt_version == prompt_version,
            LlmLog.model == model,
            LlmLog.response_json.is_not(None),
            LlmLog.error.is_(None),
        )
        .order_by(LlmLog.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
```

**Sources:**
- Codebase: `app/services/import_service.py` lines 64-74 (existing `async_session_maker()` own-scope pattern in `cleanup_orphaned_jobs`).
- Codebase: `app/repositories/import_job_repository.py` (module-level async function + docstring convention).
- [genai-prices Python README](https://github.com/pydantic/genai-prices/blob/main/packages/python/README.md) (`calc_price` signature).
- genai-prices source `data_snapshot.py::Snapshot.calc → find_provider_model` (raises `LookupError(f'Unable to find model with {model_ref=!r} in {provider.id}')`).

### Pattern 3: Pydantic v2 DTO with Literal endpoint

```python
# app/schemas/llm_log.py
"""Pydantic v2 schemas for llm_logs writes.

LlmLogEndpoint is a single-member Literal in Phase 64 — extend it when new
LLM features ship (Phase 65+ adds nothing; future milestones add more).

All fields come from the caller:
  - user_id, endpoint, prompt_version, findings_hash, filter_context, flags,
    system_prompt, user_prompt, cache_hit, error — request/context
  - model — the pydantic-ai model string (e.g. `anthropic:claude-haiku-4-5-20251001`)
  - response_json — parsed EndgameInsightsReport dict, or None on error
  - input_tokens, output_tokens — from pydantic-ai RunResult.usage()
  - latency_ms — wall-clock time caller measured around Agent.run()

Fields NOT on LlmLogCreate (repo computes):
  - id (DB auto)
  - created_at (DB default)
  - cost_usd (repo: genai-prices.calc_price)
"""
from typing import Any, Literal

from pydantic import BaseModel

LlmLogEndpoint = Literal["insights.endgame"]


class LlmLogCreate(BaseModel):
    user_id: int
    endpoint: LlmLogEndpoint
    model: str  # pydantic-ai provider:model format, e.g. "anthropic:claude-haiku-4-5-20251001"
    prompt_version: str
    findings_hash: str  # 64-char sha256 hex from insights_service.compute_findings (Phase 63)
    filter_context: dict[str, Any]
    flags: list[str]
    system_prompt: str
    user_prompt: str
    response_json: dict[str, Any] | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cache_hit: bool = False
    error: str | None = None
```

**Sources:**
- CLAUDE.md §Coding Guidelines — "`Literal` over bare str" rule.
- Codebase: `app/schemas/position_bookmarks.py` lines 10-11 (Literal aliases pattern).
- [pydantic-ai provider:model format](https://github.com/pydantic/pydantic-ai/blob/main/agent_docs/api-design.md).

### Pattern 4: Migration hand-edit over autogenerate

```python
# alembic/versions/<timestamp>_<hash>_create_llm_logs.py
"""create llm_logs

Revision ID: <hash>
Revises: 179cfbd472ef
Create Date: 2026-04-...
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "<hash>"
down_revision: Union[str, Sequence[str], None] = "179cfbd472ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("findings_hash", sa.String(64), nullable=False),
        sa.Column("filter_context", postgresql.JSONB(), nullable=False),
        sa.Column("flags", postgresql.JSONB(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("response_json", postgresql.JSONB(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "cache_hit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_llm_logs_created_at", "llm_logs", ["created_at"])
    op.create_index(
        "ix_llm_logs_user_id_created_at",
        "llm_logs",
        ["user_id", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index("ix_llm_logs_findings_hash", "llm_logs", ["findings_hash"])
    op.create_index(
        "ix_llm_logs_endpoint_created_at",
        "llm_logs",
        ["endpoint", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        "ix_llm_logs_model_created_at",
        "llm_logs",
        ["model", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    op.drop_index("ix_llm_logs_model_created_at", table_name="llm_logs")
    op.drop_index("ix_llm_logs_endpoint_created_at", table_name="llm_logs")
    op.drop_index("ix_llm_logs_findings_hash", table_name="llm_logs")
    op.drop_index("ix_llm_logs_user_id_created_at", table_name="llm_logs")
    op.drop_index("ix_llm_logs_created_at", table_name="llm_logs")
    op.drop_table("llm_logs")
```

**Why hand-edit matters:** Autogenerate is known-unreliable for (a) DESC ordering in composite
indexes, (b) JSONB (it would emit `sa.JSON` by default — portable but non-queryable in asyncpg),
(c) the exact `postgresql_ops={"created_at": "DESC"}` kwarg. Running autogenerate gives a 95%
skeleton; the planner should plan for a hand-edit pass that touches these three aspects
specifically. Verify by running the generated migration file against dev DB, then
`pg_dump --schema-only --table=llm_logs flawchess | grep -A1 CREATE INDEX` to confirm DESC
appears in the DDL.

**Sources:**
- [Alembic issue #1166 — column order in indexes](https://github.com/sqlalchemy/alembic/issues/1166)
- [Alembic issue #1213 — DESC not detected as diff](https://github.com/sqlalchemy/alembic/issues/1213)
- [Alembic issue #1285 — postgresql_ops DESC regenerated without change](https://github.com/sqlalchemy/alembic/issues/1285)
- Codebase: `alembic/versions/20260414_184435_179cfbd472ef_*.py` for the migration file header convention.

### Anti-Patterns to Avoid

- **Calling genai-prices from Phase 65**. D-03 pins cost logic inside the repo. Phase 65 never
  imports `genai_prices` — the planner should flag any Phase 65 import of the library as a
  contract violation.
- **Using `session: AsyncSession` as the first parameter of `create_llm_log`**. D-02 explicitly
  diverges. Anyone copying the `import_job_repository.py` signature literally will get this
  wrong. Code review for D-02 compliance is mandatory.
- **`sentry_sdk.capture_exception` inside the repo**. D-08 pins capture at the caller. Repo
  raises; caller catches + captures. Anyone adding `capture_exception` in `create_llm_log`
  before re-raising is duplicating what the caller already does and fragments the Sentry
  grouping.
- **Relying on `app/models/__init__.py` for autogenerate visibility.** Autogenerate sees models
  via `alembic/env.py`'s imports. Adding the new model to `__init__.py` is cosmetic and must
  NOT be relied upon for Alembic to find the table. The planner should include a dedicated
  "add import to env.py" step.
- **Interpolating `model` or `user_id` into error messages.** CLAUDE.md §Sentry rule. The
  `cost_unknown:<model>` marker is an *explicit exception* (SC #4) — it's a stable enum-like
  prefix suffixed with the user-facing model identifier; Sentry never sees this exception
  because the repo catches it. All other errors propagate as-is from asyncpg/SQLAlchemy without
  any f-string interpolation by repo code.
- **`Integer` for `user_id` FK when the CONTEXT.md mentions BigInt.** CONTEXT.md D-06 says
  "BigInt FK → users.id" but this is ambiguous at best — `users.id` is `Integer` in Postgres
  (verified via `\d users`). Use `Integer`. If the planner reads D-06 literally, Alembic will
  emit a type mismatch when the FK is created. **Flag this as a CONTEXT.md correction the
  planner should call out in PLAN.md.**

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Compute cost from `(model, input_tokens, output_tokens)` | In-repo price table or lookup dict | `genai_prices.calc_price(...)` | Per-model prices drift; upstream genai-prices tracks 100+ models across 4+ providers with historical pricing |
| Serialize `dict`/`list` → JSON → DB | Text column + `json.dumps/loads` | `postgresql.JSONB` | Queryable via operators, indexable, native asyncpg codec returns `dict`/`list` |
| Own-session management | Manual `engine.connect() + begin() + commit()` | `async with async_session_maker() as session` + `await session.commit()` | Matches existing `import_service.cleanup_orphaned_jobs` pattern, respects pool_pre_ping, connection_pool_size |
| SHA256 hashing of findings | Re-compute in the repo | (don't — repo receives `findings_hash` from Phase 63's `compute_findings`) | Phase 63 already owns the canonical hash recipe (FIND-05). Repo treats `findings_hash` as an opaque string |
| Schema for insights response (`response_json`) | Free-form dict validation | Store whatever Phase 65 dumps; Phase 65 validates via `pydantic_ai.Agent(result_type=EndgameInsightsReport)` before calling `create_llm_log` | The repo's job is to persist, not re-validate. JSONB is lenient. |

**Key insight:** Three of the four external behaviors (cost, cache key hashing, structured
output validation) are already owned by other libraries or phases. Phase 64's repo is a thin
wrapper: compute-cost-then-INSERT. If a plan task grows beyond ~80 LOC in the repo, it's doing
too much.

## Runtime State Inventory

> Phase 64 is a greenfield DB-layer addition, NOT a rename/refactor/migration. This section
> documents that no pre-existing runtime state references `llm_logs` (correctly — the table
> doesn't exist yet), and flags the one post-deploy consideration.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `llm_logs` doesn't exist yet; no prior table to migrate from | None |
| Live service config | None — no n8n/Datadog/etc. service references `llm_logs` | None |
| OS-registered state | None — no cron, systemd, or Task Scheduler entry references this table | None |
| Secrets/env vars | None added by Phase 64. Phase 65 introduces `PYDANTIC_AI_MODEL_INSIGHTS` + provider API keys, NOT this phase | None |
| Build artifacts | `uv.lock` will update when `genai-prices` is added. `.venv` will need `uv sync` after pulling the branch | Call `uv sync` noted in the plan as a setup step |

**Post-deploy note:** The `entrypoint.sh` already runs `alembic upgrade head` on container
startup. No manual migration step is needed on the Hetzner box after deploy. Rollback story:
`alembic downgrade -1` drops the table; no data loss risk because Phase 64 does not ship any
write path — the table is born empty.

## Common Pitfalls

### Pitfall 1: `users.id` is Integer, not BigInteger

**What goes wrong:** CONTEXT.md D-06 says "BigInt FK → users.id" but the Postgres `users.id`
column is 32-bit `integer`. Declaring the FK as `BigInteger` in the ORM will cause SQLAlchemy
to emit DDL that Postgres rejects (FK type mismatch), OR silently coerces — either way the
model doesn't match reality.
**Why it happens:** SEED-003's snippet uses `Mapped[int] = mapped_column(ForeignKey(...))`
without an explicit type and relies on SQLAlchemy's `int → Integer` default, which is correct.
CONTEXT.md D-06 then paraphrased as "BigInt FK" which is a misread of D-05 (log's own `id` is
BigInt) bleeding into D-06 (user FK).
**How to avoid:** Use explicit `Integer` for the `user_id` FK column. The log's OWN `id` stays
`BigInteger` per D-05.
**Warning signs:** `alembic upgrade head` emitting `ERROR: foreign key constraint
"llm_logs_user_id_fkey" cannot be implemented` / `DETAIL: Key columns "user_id" and "id" are
of incompatible types: bigint and integer.`

### Pitfall 2: Autogenerate silently drops DESC on indexes

**What goes wrong:** Running `uv run alembic revision --autogenerate -m "create llm_logs"`
produces a migration that creates the three composite indexes WITHOUT `postgresql_ops={...: "DESC"}`.
Postgres then stores them as ASC, and per-user-recency queries in Phase 65 miss the index.
**Why it happens:** Alembic issues #1166, #1213, and #1285 document this — DESC ordering is
not part of Alembic's index comparison semantics.
**How to avoid:** After autogenerate, open the generated migration, confirm that the
`postgresql_ops={"created_at": "DESC"}` kwarg appears on the three DESC indexes, and add it
if missing.
**Warning signs:** `pg_dump --schema-only --table=llm_logs` output lacks `DESC` in the
`CREATE INDEX` statements for the user/endpoint/model + created_at composites.

### Pitfall 3: Forgetting to register the model in `alembic/env.py`

**What goes wrong:** Autogenerate runs but produces an empty diff because `LlmLog` isn't
imported in `env.py`'s side-effect import list.
**Why it happens:** `app/models/__init__.py` is a thin re-export convenience used by *some*
app code; autogenerate sees models exclusively via `alembic/env.py`'s `# noqa: F401` imports.
New contributors assume `__init__.py` is the registration point — it's not.
**How to avoid:** Add `from app.models.llm_log import LlmLog  # noqa: F401` to `alembic/env.py`
(following the pattern of lines 12-17). Updating `app/models/__init__.py` is cosmetic and can
be deferred or skipped.
**Warning signs:** Autogenerate produces `# ### empty ###` or an unrelated diff; Phase 64's
migration file is surprisingly short.

### Pitfall 4: `expire_on_commit=False` is already the project default — but own-session still needs explicit commit

**What goes wrong:** Copying `import_job_repository.create_import_job` which does `session.flush()`
(no commit) and returns — assumes the caller's session will commit. Own-session repo (D-02)
must call `await session.commit()` explicitly inside its `async with` block.
**Why it happens:** The 35-line import_job_repository.create_import_job is the closest
reference; easy to copy-paste the `flush()` without noticing the semantic difference.
**How to avoid:** Inside `async with async_session_maker() as session:`, call `await session.commit()`
before the context manager exits. The project's `async_session_maker` uses
`expire_on_commit=False` (line 15 of `app/core/database.py`) so `session.refresh(row)` after
commit is safe.
**Warning signs:** Test-side insert appears to succeed in-process but `SELECT * FROM llm_logs`
in a separate psql session returns zero rows — the transaction rolled back on block exit
because no commit was issued.

### Pitfall 5: Tests that use `db_session` fixture cannot observe rows written by `create_llm_log`

**What goes wrong:** The `db_session` fixture (conftest.py lines 168-185) wraps each test in a
connection-level transaction that always rolls back. `create_llm_log` opens its OWN session via
`async_session_maker()`, which uses a DIFFERENT connection from the pool — so the log row
IS committed to the test DB, outside the test's transaction scope.
**Why it happens:** D-02's own-session design is deliberate, but test fixtures assume all
writes happen on the fixture's session.
**How to avoid:** Tests for `create_llm_log` must (a) use a separate session (same pool) to
read back the inserted row, AND (b) include explicit cleanup — either delete the row at the
end of the test, or rely on the session-start `TRUNCATE TABLE ... RESTART IDENTITY CASCADE`
in `conftest._truncate_all_tables` which runs once per session and fires at pytest setup. The
second option means row residue persists across tests within a single session — which is the
existing pattern for commits-outside-rollback (`cleanup_orphaned_jobs`, on_after_login).
**Warning signs:** Test asserts row exists → passes. Next test's `SELECT COUNT(*) FROM llm_logs`
returns 1 unexpectedly. Solution: each test creates its own unique `user_id`+`findings_hash`
pair, or deletes explicitly.

**Recommended test pattern:**
```python
@pytest_asyncio.fixture
async def fresh_test_user(test_engine):
    """Create + yield a user that tests mutate; cleanup deletes them cascading logs."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email=f"llm-log-test-{uuid.uuid4()}@example.com", hashed_password="x")
        session.add(user)
        await session.commit()
        await session.refresh(user)
    yield user
    async with session_maker() as session:
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()
```

## Code Examples

### Example 1: Insert round-trip (SC #2)

```python
# tests/test_llm_log_repository.py — happy path
import pytest
from app.repositories.llm_log_repository import create_llm_log
from app.schemas.llm_log import LlmLogCreate


@pytest.mark.asyncio
async def test_create_llm_log_inserts_and_returns_row(fresh_test_user):
    data = LlmLogCreate(
        user_id=fresh_test_user.id,
        endpoint="insights.endgame",
        model="anthropic:claude-haiku-4-5-20251001",
        prompt_version="endgame_v1",
        findings_hash="a" * 64,
        filter_context={"recency": "last_3mo"},
        flags=["baseline_lift_mutes_score_gap"],
        system_prompt="You are FlawChess's endgame analyst...",
        user_prompt="Filters: recency=last_3mo...",
        response_json={"overview": "...", "sections": []},
        input_tokens=1200,
        output_tokens=180,
        latency_ms=2345,
    )
    row = await create_llm_log(data)
    assert row.id is not None
    assert row.created_at is not None
    assert row.cost_usd > 0  # genai-prices knows this model
    assert row.error is None
```

### Example 2: `cost_unknown` fallback (SC #4)

```python
@pytest.mark.asyncio
async def test_unknown_model_records_cost_unknown_and_zero_cost(fresh_test_user):
    data = LlmLogCreate(
        user_id=fresh_test_user.id,
        endpoint="insights.endgame",
        model="fictional-vendor:fake-model-9000",  # not in genai-prices catalog
        prompt_version="endgame_v1",
        findings_hash="b" * 64,
        filter_context={},
        flags=[],
        system_prompt="x",
        user_prompt="y",
        response_json=None,
        input_tokens=100,
        output_tokens=50,
        latency_ms=500,
    )
    row = await create_llm_log(data)
    assert row.cost_usd == Decimal("0")
    assert row.error == "cost_unknown:fictional-vendor:fake-model-9000"


@pytest.mark.asyncio
async def test_unknown_model_appends_to_existing_error(fresh_test_user):
    data = LlmLogCreate(
        ...,  # same as above
        error="provider_rate_limit",
    )
    row = await create_llm_log(data)
    assert row.cost_usd == Decimal("0")
    assert row.error == "provider_rate_limit; cost_unknown:fictional-vendor:fake-model-9000"
```

### Example 3: Cascade on user delete (SC #3)

```python
# tests/test_llm_log_cascade.py
import pytest
from sqlalchemy import delete, select
from app.models.llm_log import LlmLog
from app.models.user import User


@pytest.mark.asyncio
async def test_deleting_user_cascades_llm_logs(test_engine):
    # Setup: create user + log via repo's own-session
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="cascade@example.com", hashed_password="x")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    data = LlmLogCreate(user_id=user_id, ...)  # minimal valid payload
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

### Example 4: Migration smoke test (SC #1)

```python
# tests/test_llm_logs_migration.py
import pytest
from sqlalchemy import inspect


@pytest.mark.asyncio
async def test_llm_logs_table_exists_with_all_columns_and_indexes(test_engine):
    def _inspect(sync_conn):
        insp = inspect(sync_conn)
        assert "llm_logs" in insp.get_table_names()

        cols = {c["name"] for c in insp.get_columns("llm_logs")}
        expected = {
            "id", "user_id", "created_at", "endpoint", "model", "prompt_version",
            "findings_hash", "filter_context", "flags", "system_prompt", "user_prompt",
            "response_json", "input_tokens", "output_tokens", "cost_usd", "latency_ms",
            "cache_hit", "error",
        }
        assert expected <= cols, f"missing columns: {expected - cols}"

        indexes = {i["name"] for i in insp.get_indexes("llm_logs")}
        expected_ix = {
            "ix_llm_logs_created_at",
            "ix_llm_logs_user_id_created_at",
            "ix_llm_logs_findings_hash",
            "ix_llm_logs_endpoint_created_at",
            "ix_llm_logs_model_created_at",
        }
        assert expected_ix <= indexes, f"missing indexes: {expected_ix - indexes}"

    async with test_engine.connect() as conn:
        await conn.run_sync(_inspect)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.x `Query` API | SQLAlchemy 2.x `select()` async | Project-wide 2024 | Repo uses `select(LlmLog).where(...)` — no legacy Query |
| Pydantic v1 `Config` | Pydantic v2 `ConfigDict` / field_validator | Project-wide | `LlmLogCreate` uses v2 style |
| Hand-rolled cost tables | genai-prices library | This phase | Pinned `>=0.0.56,<0.1.0`; revisit at 1.0 |
| `json.dumps` → Text column | `postgresql.JSONB` | This phase (first JSONB in codebase) | Queryable via operators; native dict roundtrip with asyncpg |

**Deprecated/outdated:**
- None specific to Phase 64. SEED-003's snippet (lines 120-150) uses `Mapped[dict]` without a
  type annotation for JSONB — slightly out-of-date versus the Phase 64 model's explicit
  `Mapped[dict] = mapped_column(JSONB, ...)` pattern. Treat SEED-003 as architectural sketch;
  this research doc is the implementation reference.

## Assumptions Log

> Claims tagged `[ASSUMED]` that the planner and/or `/gsd-discuss-phase` should confirm.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `users.id` is `Integer` (not BigInteger) → FK column must be `Integer` | Pitfall 1, Pattern 1 | **VERIFIED via psql `\d users`** — no risk, drop [ASSUMED] tag |
| A2 | `genai-prices.calc_price` accepts a single `model_ref` with or without `provider:` prefix and internally dispatches | Pattern 2 | Medium. The Python README examples always pass `provider_id=`. If the pydantic-ai `provider:model` format (e.g., `"anthropic:claude-haiku-4-5-20251001"`) doesn't match `genai-prices`'s expectations, every call would raise LookupError and every row would be `cost_unknown:*`. **Plan should include a Wave 0 smoke test:** run `calc_price(Usage(100, 100), model_ref="anthropic:claude-haiku-4-5-20251001")` in a one-liner to confirm a price comes back, BEFORE writing the repo. If it requires splitting the string into provider_id + model_ref, the repo's `_compute_cost` helper does that split |
| A3 | JSONB columns roundtrip cleanly through SQLAlchemy 2.x async + asyncpg as native `dict` / `list[str]` | Pattern 1 | Low. asyncpg has native JSONB codec (returns Python dict/list), SQLAlchemy's `postgresql.JSONB` type integrates cleanly. No other code in this repo uses JSONB yet, so the first test run is the confirmation |
| A4 | Alembic autogenerate on a migration that adds JSONB columns produces `postgresql.JSONB` (not generic `sa.JSON`) | Pattern 4 | Low. The type hint `Mapped[dict] = mapped_column(JSONB, ...)` is explicit; autogenerate reflects the declared type. Hand-edit pass catches if not |
| A5 | The Phase 65 cache-lookup query signature is `get_latest_log_by_hash(findings_hash, prompt_version, model) → LlmLog | None` | Pattern 2 | Low. CONTEXT.md lists this as Claude's Discretion; Phase 65 plan will confirm. If Phase 65 wants a different signature (e.g., include `endpoint`), the planner can adjust in Phase 64 or Phase 65 trivially since nothing outside Phase 64 currently calls this function |
| A6 | `error` column should be nullable `Text` (matches SEED-003 and CLAUDE.md convention for arbitrary-length failure messages) | Pattern 1 | Low. Locked by LOG-01 requirement. |
| A7 | `tests/` uses flat layout; don't create `tests/repositories/`, `tests/models/`, `tests/alembic/` subdirs despite CONTEXT.md D-09 nesting proposal | Project Structure | Low. CONTEXT.md D-09 is scope-anchor, not structure-locked. Matches existing codebase convention — `test_insights_service.py` lives at top-level `tests/`, not `tests/services/` (one exception exists but is the post-Phase-63 addition). **Planner should decide but flat is my recommendation** |

## Open Questions

1. **Does `genai-prices` accept `provider:model` format directly, or must the repo split it?**
   - What we know: Python README examples pass `model_ref='gpt-4o'` + `provider_id='openai'` as
     separate args. pydantic-ai emits model IDs as `"anthropic:claude-haiku-4-5-20251001"`.
   - What's unclear: Whether `calc_price(Usage(...), model_ref="anthropic:claude-haiku-4-5-20251001")`
     (no explicit `provider_id`) works, or raises LookupError.
   - Recommendation: Wave 0 micro-task — a 5-line script that imports `genai-prices` and calls
     `calc_price` on both `"claude-haiku-4-5-20251001"` alone, and `"anthropic:claude-haiku-4-5-20251001"`,
     and logs which worked. Takes 30 seconds; removes the last risk. If split is needed, repo's
     `_compute_cost` splits on the first `:`.

2. **Does CONTEXT.md D-06 mean `BigInt` (literally) or does it mean "whatever type `users.id` is"?**
   - What we know: `users.id` is `Integer`, not `BigInteger` (verified via `\d users`).
     Declaring the FK as `BigInteger` will fail Postgres DDL validation on `alembic upgrade`.
   - What's unclear: Whether the user's intent in D-06 was "match users.id" (correct → Integer)
     or "BigInt period" (wrong, but maybe intentional? No — FK must match referenced column type).
   - Recommendation: Use `Integer`. Flag in PLAN.md as a correction to CONTEXT.md D-06 so the
     planner surfaces it and the user can confirm during discuss. No blocking: default to
     `Integer` — if the user disagrees and wants BigInt, they'd need to first migrate
     `users.id` to BigInteger which is out of scope.

3. **Should `tests/` stay flat or adopt D-09's nested layout?**
   - What we know: Current convention is flat; only one subdirectory exists (`tests/services/`)
     added post-Phase-63.
   - What's unclear: Whether CONTEXT.md D-09's nested proposal is a preference or a structure
     decision.
   - Recommendation: Flat, unless the planner or user objects. Nested is future-proof but one
     phase's worth of nesting doesn't move the needle.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL 18 | Migration + tests + repo | ✓ | 18 (Docker, dev DB running) | — |
| `uv` | Python package management | ✓ | (already used) | — |
| Python 3.13 | Project runtime | ✓ (pyproject `requires-python = ">=3.13"`) | — | — |
| `alembic` | Migration generation + smoke test | ✓ | ≥ 1.13.0 in pyproject | — |
| `pytest-asyncio` | Async test runner | ✓ | ≥ 0.23.0 in pyproject | — |
| `genai-prices` | Cost computation | ✗ (not yet in pyproject) | — | **ADD via `uv add genai-prices`** as first task of the phase |
| Network access to PyPI | Install `genai-prices` | Assumed ✓ (CI has it) | — | If offline, `uv add` fails → block plan start until resolved |

**Missing dependencies with no fallback:** None — `genai-prices` is addable.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x + `asyncio_mode = "auto"` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_llm_log_repository.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOG-01 | Alembic migration creates table + all 17 columns + all 5 indexes | integration (against flawchess_test) | `uv run pytest tests/test_llm_logs_migration.py -x` | ❌ Wave 0 |
| LOG-02 | Every cache-miss call writes exactly one row, including success and failure paths | unit (repo) | `uv run pytest tests/test_llm_log_repository.py::test_create_llm_log_inserts_and_returns_row -x` | ❌ Wave 0 |
| LOG-02 | Cost is computed internally and stored at write time | unit (repo) | `uv run pytest tests/test_llm_log_repository.py::test_create_llm_log_inserts_and_returns_row -x` (asserts `row.cost_usd > 0`) | ❌ Wave 0 |
| LOG-02 (SC #4) | `cost_unknown:<model>` fallback on genai-prices LookupError, cost_usd=0 | unit (repo) | `uv run pytest tests/test_llm_log_repository.py::test_unknown_model_records_cost_unknown_and_zero_cost -x` | ❌ Wave 0 |
| LOG-02 (SC #4 cont'd) | `cost_unknown` appends to existing error with `; ` separator | unit (repo) | `uv run pytest tests/test_llm_log_repository.py::test_unknown_model_appends_to_existing_error -x` | ❌ Wave 0 |
| LOG-03 | All 5 indexes are named correctly + created on the right columns (DESC preserved on 3) | integration | `uv run pytest tests/test_llm_logs_migration.py -x` (inspect.get_indexes) + `psql -c "\d llm_logs"` manual verification for DESC | ❌ Wave 0 |
| LOG-04 (SC #3) | User delete cascades to llm_logs rows | integration (cascade) | `uv run pytest tests/test_llm_log_cascade.py -x` | ❌ Wave 0 |
| LOG-04 | Repo error messages contain no f-string interpolation of user-provided variables (except the LOCKED `cost_unknown:<model>` marker which is a stable prefix) | static analysis | `uv run ruff check app/repositories/llm_log_repository.py` + code review (no automated test; covered by review checklist) | N/A |
| ty compliance | All new code passes `uv run ty check app/ tests/` with zero errors | static | `uv run ty check app/ tests/` | N/A |
| ruff | All new code passes `uv run ruff check .` + `uv run ruff format --check .` | static | `uv run ruff check . && uv run ruff format --check .` | N/A |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_llm_log_repository.py tests/test_llm_log_cascade.py tests/test_llm_logs_migration.py -x`
- **Per wave merge:** `uv run pytest` (full suite, ~950 tests, runtime < 30s per Phase 63 data)
- **Phase gate:** Full suite green + `uv run ty check app/ tests/` zero errors + `uv run ruff check .` clean before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_llm_log_repository.py` — covers LOG-02 + SC #4 (insert round-trip + cost_unknown)
- [ ] `tests/test_llm_log_cascade.py` — covers LOG-04 (cascade + no-error-interpolation)
- [ ] `tests/test_llm_logs_migration.py` — covers LOG-01 + LOG-03 (table + 5 indexes exist)
- [ ] `tests/conftest.py` — add `fresh_test_user` fixture (see Pitfall 5 recommended pattern)
- [ ] `app/repositories/llm_log_repository.py` — Wave 0 scaffold: module docstring only, empty stubs that raise NotImplementedError. Tests against empty stubs fail loudly; implementation fills them in Wave 1
- [ ] `app/schemas/llm_log.py` — Wave 0 scaffold: `LlmLogEndpoint` + `LlmLogCreate` shell. Schema locked-and-shipped in Wave 0 so the repo and tests compile against a stable DTO
- [ ] `app/models/llm_log.py` — Wave 0 scaffold: ORM class
- [ ] `alembic/env.py` — Wave 0 edit: add `from app.models.llm_log import LlmLog  # noqa: F401`
- [ ] `alembic/versions/<timestamp>_<hash>_create_llm_logs.py` — Wave 0: autogenerate then hand-edit for JSONB + DESC
- [ ] Wave 0 one-liner: `uv run python -c "from genai_prices import Usage, calc_price; print(calc_price(Usage(100, 100), model_ref='anthropic:claude-haiku-4-5-20251001'))"` — confirms the pydantic-ai model-string format is accepted by genai-prices. Resolves Open Question #1.

## Security Domain

> Phase 64 is backend-internal DB infrastructure. No user-facing endpoint, no new auth surface.
> ASVS still applies; most categories are inherited from the broader stack (FastAPI-Users, etc.)
> and have no Phase 64-specific work.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Inherited from FastAPI-Users (Phase 64 adds no endpoint) |
| V3 Session Management | no | Inherited (no endpoint) |
| V4 Access Control | yes | FK + ON DELETE CASCADE ensures logs are scoped to user ownership; Phase 65 is responsible for only-logging-own-user, not Phase 64 |
| V5 Input Validation | yes | Pydantic v2 `LlmLogCreate` validates all fields at repo boundary |
| V6 Cryptography | no | No crypto operations in Phase 64 (`findings_hash` is produced by Phase 63, stored as-is) |
| V8 Data Protection | yes | GDPR cascade on user delete via FK `ondelete="CASCADE"`; no PII stored in prompts per SEED-003 §Privacy |
| V13 API & Web Service | no | No API endpoint in Phase 64 |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via `filter_context` JSONB | Tampering | SQLAlchemy parameterized queries; JSONB is typed; asyncpg refuses raw string injection |
| Logging sensitive data in `user_prompt` / `system_prompt` / `response_json` | Information disclosure | SEED-003 §Privacy confirms prompts contain chess stats only, no PGN/opponent names. Document this invariant; if future LLM features log game text, revisit redaction |
| Disk fill via log accumulation | DoS | Retention explicitly deferred (SEED-003). Non-blocker: current volume projection is ≤ 3 cache misses / user / hour × <100 beta users = <7.2k rows/day. Table stays small for months |
| Unbounded `response_json` size | DoS | pydantic-ai's `EndgameInsightsReport` schema caps overview at ~150 words; output size is bounded by provider token limits, typically ≤ 1KB per row |
| Log row survives caller rollback (D-02) by design | — | Confirm tests validate this explicitly — that the log row persists even when the caller's session rolls back mid-flight |

## Sources

### Primary (HIGH confidence)

- **Context7 `/pydantic/genai-prices`** — `calc_price` signature, `Usage` dataclass, `PriceCalculation` return type. Verified 2026-04-20.
- **Context7 `/pydantic/pydantic-ai`** — `provider:model` model string format locked. Verified 2026-04-20.
- **genai-prices source `data_snapshot.py::Snapshot.calc`** — `raise LookupError(f'Unable to find model with {model_ref=!r} in {provider.id}')`. Fetched 2026-04-20.
- **PyPI** — `genai-prices` latest version `0.0.56` released `2026-03-20`. Fetched 2026-04-20.
- **Codebase** — `app/models/base.py`, `app/models/import_job.py`, `app/models/position_bookmark.py`, `app/models/game_position.py`, `app/repositories/import_job_repository.py`, `app/core/database.py`, `app/services/import_service.py` (lines 64-74), `alembic/env.py`, `alembic/versions/20260414_184435_179cfbd472ef_*.py`, `tests/conftest.py`, `app/models/user.py`, `app/models/__init__.py`.
- **Dev DB schema** — `psql \d users` confirms `users.id` is `integer`; `\d import_jobs` confirms `user_id` is `integer`. Queried 2026-04-20.
- **pyproject.toml** — confirms Python 3.13, sqlalchemy[asyncio]>=2.0, alembic>=1.13, pydantic>=2.0, asyncpg>=0.29 all present.
- **CONTEXT.md `.planning/phases/64-llm-logs-table-async-repo/64-CONTEXT.md`** — D-01 through D-09 locked decisions + Claude's Discretion scope.
- **CLAUDE.md** — §Coding Guidelines, §Database Design Rules, §Critical Constraints, §Error Handling & Sentry.

### Secondary (MEDIUM confidence)

- **Alembic upstream issue tracker** — issues [#1166](https://github.com/sqlalchemy/alembic/issues/1166), [#1213](https://github.com/sqlalchemy/alembic/issues/1213), [#1285](https://github.com/sqlalchemy/alembic/issues/1285) documenting the DESC-on-autogenerate limitation. Confirmed via web search 2026-04-20.
- **SEED-003 `.planning/seeds/SEED-003-llm-based-insights.md`** — §Observability (lines 120-170) sketches the SQLAlchemy model; §Privacy + §Retention motivate cascade + no-redaction.
- **REQUIREMENTS.md** §LOG-01..LOG-04 — locked column set, indexes, cost-compute source.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — genai-prices version verified via PyPI, calc_price error behavior verified in source, pydantic-ai format verified in upstream docs.
- Architecture: HIGH — D-01..D-09 locked in CONTEXT.md; own-session pattern has a direct precedent in `import_service.cleanup_orphaned_jobs`.
- Pitfalls: HIGH for pitfalls 1-4 (each verified in the codebase or upstream docs); MEDIUM for pitfall 5 (based on reading `conftest.py` logic, not observed in a running test).

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (30 days — stack is stable; only genai-prices changes frequently but the LookupError semantics are unlikely to regress)

---

*Phase: 64-llm-logs-table-async-repo*
*Research completed: 2026-04-20*
