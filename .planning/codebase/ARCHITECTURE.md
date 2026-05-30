<!-- refreshed: 2026-05-30 -->
# Architecture

**Analysis Date:** 2026-05-30

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          Browser (PWA)                               │
│   React 19 + Vite SPA · TanStack Query · react-router-dom           │
│   `frontend/src/pages/*`  `frontend/src/components/*`               │
├─────────────────────────────────────────────────────────────────────┤
│   API layer  `frontend/src/api/client.ts`  (axios instance)        │
│   Query hooks `frontend/src/hooks/use*.ts`                          │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │  HTTP /api/*  (same-origin via Caddy)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI app  `app/main.py`                        │
│   CORS (dev only) · LastActivityMiddleware · Sentry · lifespan      │
├─────────────────────────────────────────────────────────────────────┤
│   Routers (HTTP only)        `app/routers/*.py`                     │
│   ───────────────────────────────────────────────────────────────  │
│   Services (business logic)  `app/services/*.py`                    │
│   ───────────────────────────────────────────────────────────────  │
│   Repositories (DB access)   `app/repositories/*.py`               │
└──────────┬──────────────────────────────────┬──────────────────────┘
           │                                  │
           ▼                                  ▼
┌──────────────────────────┐    ┌─────────────────────────────────────┐
│  PostgreSQL 18 (asyncpg) │    │  External services                  │
│  SQLAlchemy 2.x async    │    │  chess.com API · lichess API        │
│  `app/models/*.py`       │    │  LLM via pydantic-ai (Google model) │
│  Alembic migrations      │    │  Stockfish UCI (EnginePool)         │
└──────────────────────────┘    └─────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app + lifespan | App assembly, middleware, router mounting, startup/shutdown of engine + background tasks | `app/main.py` |
| Routers | HTTP layer only: validate request, call service, shape response. No business logic | `app/routers/*.py` |
| Services | Business logic: import, classification, stats, endgames, insights, engine, normalization | `app/services/*.py` |
| Repositories | All DB access (SQLAlchemy `select()`); no SQL in services | `app/repositories/*.py` |
| Shared query filters | Single implementation of game filters (TC, platform, rated, opponent, recency, color, opponent gap) | `app/repositories/query_utils.py` |
| Models | SQLAlchemy ORM tables, FK constraints, indexes; declarative `Base` | `app/models/*.py`, `app/models/base.py` |
| Schemas | Pydantic v2 request/response models + internal TypedDicts | `app/schemas/*.py` |
| Auth (FastAPI-Users) | UserManager, JWT auth backend, impersonation strategy, `current_active_user` deps | `app/users.py` |
| DB session/engine | Async engine + `get_async_session` dependency | `app/core/database.py` |
| Zobrist hashing | Position fingerprinting (white/black/full hash) for indexed position matching | `app/services/zobrist.py` |
| Engine pool | Long-lived Stockfish UCI process pool for eval | `app/services/engine.py` |
| Frontend pages | Top-level route screens (Openings, Endgames, Overview, Import) | `frontend/src/pages/*` |
| Frontend API + hooks | Typed axios clients and TanStack Query hooks | `frontend/src/api/client.ts`, `frontend/src/hooks/use*.ts` |

## Pattern Overview

**Overall:** Layered (router → service → repository) FastAPI backend with an async SQLAlchemy data layer, fronted by a React SPA that talks to it over a JSON `/api` surface. Background async tasks (import, eval drain, orphan reaper) run inside the FastAPI process via the lifespan context manager.

**Key Characteristics:**
- Strict three-layer separation: routers do HTTP, services do logic, repositories do SQL. SQL never appears in services; logic never appears in routers.
- Position matching by precomputed 64-bit Zobrist integer hashes (`white_hash`/`black_hash`/`full_hash`), not FEN comparison. Position queries are indexed integer equality lookups.
- Single source of truth for cross-cutting filters in `query_utils.apply_game_filters()` — every repository imports it.
- Async end-to-end: asyncpg + SQLAlchemy 2.x async, httpx async clients, FastAPI async handlers. Never `asyncio.gather` on one `AsyncSession`.
- Frontend is server-state-driven: TanStack Query owns API state; component-local state is UI-only.

## Layers

**Frontend (React SPA):**
- Purpose: render UI, manage UI state, call the API
- Location: `frontend/src/`
- Contains: pages, components, hooks (TanStack Query), the axios API client, theme/lib utilities
- Depends on: `/api` HTTP surface
- Used by: end users (browser, installable PWA)

**Router layer (HTTP):**
- Purpose: parse/validate request (Pydantic), call a service, shape the response
- Location: `app/routers/`
- Contains: `APIRouter(prefix="/resource", tags=["resource"])` with relative decorator paths
- Depends on: services, schemas, `app/users.py` (auth deps), `app/core/database.py` (session dep)
- Used by: `app/main.py` (`include_router(..., prefix="/api")`)

**Service layer (business logic):**
- Purpose: import pipelines, classification, WDL/endgame/time stats, LLM insights, engine eval, percentile computation
- Location: `app/services/`
- Contains: orchestration, aggregation, external API calls (httpx), Stockfish, LLM agents
- Depends on: repositories, models, schemas, zobrist, engine
- Used by: routers, background tasks, `scripts/`

**Repository layer (DB access):**
- Purpose: all SQLAlchemy queries against the models
- Location: `app/repositories/`
- Contains: `select()`-based queries, importing `apply_game_filters()` from `query_utils.py`
- Depends on: models, `query_utils.py`
- Used by: services only

**Data layer:**
- Purpose: persistence schema and migrations
- Location: `app/models/`, `alembic/` (63 migration versions), declarative `Base` in `app/models/base.py`
- Engine/session: `app/core/database.py` (`create_async_engine`, `pool_size=10, max_overflow=10, pool_pre_ping=True`, `expire_on_commit=False`). `get_async_session` commits at the end of each request.

## Data Flow

### Primary Request Path (Opening position lookup)

1. User moves on the board; `OpeningsPage` / `MoveExplorer` triggers a query hook (`frontend/src/hooks/useOpenings.ts`)
2. Hook calls the axios client (`frontend/src/api/client.ts`, `POST /api/openings/positions`)
3. Router validates `OpeningsRequest` and the current user dependency (`app/routers/openings.py:27`)
4. Router delegates to `app/services/openings_service.py` → `app/repositories/openings_repository.py`, which builds a `select()` and applies `apply_game_filters()` (`app/repositories/query_utils.py:12`)
5. Postgres returns matching `game_positions` rows by indexed hash equality; the service aggregates WDL
6. Router returns `OpeningsResponse` (FEN for display, never internal hashes); TanStack Query caches it

### Game Import (background async)

1. `POST /api/imports` creates a job, then schedules `run_import()` (`app/services/import_service.py:538`)
2. Per platform: chess.com fetches monthly archives sequentially with rate-limit delays (`app/services/chesscom_client.py`); lichess streams NDJSON line-by-line (`app/services/lichess_client.py`). Both normalize to a unified schema (`app/services/normalization.py`).
3. Each game's PGN is replayed; for every half-move the three Zobrist hashes are computed (`app/services/zobrist.py`) and `GamePosition` rows are written in batches (`_BATCH_SIZE`, `_flush_batch` at `app/services/import_service.py:686`; prod lowers the batch size to contain Postgres memory)
4. Endgame spans are classified (`app/services/position_classifier.py`); Stockfish eval is filled via the cold-lane drain (`app/services/eval_drain.py`)
5. Orphaned `in_progress` jobs are reclaimed at startup (`cleanup_orphaned_jobs()`, `app/services/import_service.py:141`) and by the periodic reaper (`run_periodic_reaper()`, `:276`)

### LLM Insights

1. `POST /api/insights/endgame` or `/api/insights/openings` (`app/routers/insights.py`)
2. The service gathers stats from repositories, builds the prompt (`app/prompts/endgame_insights.md`), and invokes the cached pydantic-ai `Agent` (`app/services/insights_llm.py:285` `get_insights_agent()`)
3. The narrated result is persisted (`app/models/llm_log.py`) and returned

**State Management:**
- Server state: TanStack Query (`frontend/src/lib/queryClient.ts`), with global error capture in `QueryCache.onError` / `MutationCache.onError`
- DB sessions: per-request via `get_async_session()` dependency; one session = one connection, used sequentially
- Background tasks: created in the `lifespan` context and cancelled on shutdown before `stop_engine()`

## Key Abstractions

**Zobrist position hash:**
- Purpose: exact position identity independent of move order / opening name
- Examples: `app/services/zobrist.py` (`compute_hashes`, `process_game_pgn`), columns `white_hash`/`black_hash`/`full_hash` on `GamePosition`
- Pattern: precompute at import time, query by indexed integer equality. `white_hash`/`black_hash` enable "my pieces only" system-opening queries

**`apply_game_filters()`:**
- Purpose: one definition of all game filtering
- Examples: `app/repositories/query_utils.py`, imported across repositories
- Pattern: takes a `Select`, returns a filtered `Select`; never duplicated

**EnginePool:**
- Purpose: manage the long-lived Stockfish UCI process(es)
- Examples: `app/services/engine.py` (`class EnginePool`, `start_engine`, `stop_engine`)
- Pattern: module-level singleton `_pool`; started/stopped in lifespan; sized by `STOCKFISH_POOL_SIZE` (default 1)

**Insights Agent:**
- Purpose: LLM narration of stats
- Examples: `app/services/insights_llm.py` (`get_insights_agent` returns `Agent[None, EndgameInsightsReport]`)
- Pattern: cached pydantic-ai `Agent` over an explicit Google model; validated at startup as a deploy-blocker

## Entry Points

**Backend ASGI app:**
- Location: `app/main.py` (`app = FastAPI(...)`)
- Triggers: Uvicorn (`uv run uvicorn app.main:app`); Docker via `deploy/entrypoint.sh` (runs Alembic then Uvicorn)
- Responsibilities: Sentry init, middleware, router mounting under `/api`, lifespan startup/shutdown

**Frontend SPA:**
- Location: `frontend/src/main.tsx` → `frontend/src/App.tsx`
- Triggers: Vite (`npm run dev`) / built bundle served by Caddy
- Responsibilities: mount React under `QueryClientProvider` + `Sentry.ErrorBoundary`, set up `BrowserRouter` with a `ProtectedLayout` wrapping authenticated routes

**Background tasks:**
- Location: `lifespan` in `app/main.py`
- Triggers: app startup; `run_periodic_reaper()` and `run_eval_drain()` run for the app lifetime

**CLI scripts:**
- Location: `scripts/*.py` (seeding, reimport, reclassify, benchmark ingest, eval backfill, CDF generation)
- Triggers: manual `uv run python scripts/...`

## Architectural Constraints

- **Threading:** Single-process async event loop (Uvicorn). No worker threads for app logic. Stockfish runs as a separate UCI subprocess pool.
- **AsyncSession concurrency:** Never `asyncio.gather` queries on the same `AsyncSession` — it is not concurrency-safe and shares one connection. Execute sequentially.
- **Global state:** Module-level singletons — SQLAlchemy `engine`/`async_session_maker` (`app/core/database.py`), the `EnginePool` `_pool` (`app/services/engine.py`), the cached insights `Agent` (`app/services/insights_llm.py`), and in-process import `JobState` registry (`app/services/import_service.py`).
- **DB pool ceiling:** `pool_size=10 + max_overflow=10 = 20` per process; Postgres `max_connections=30` in prod (memory-tuned after repeated OOM incidents; see comment block in `app/core/database.py`).
- **Connection/memory pressure:** Import batch size and Stockfish pool size are deliberately small in prod to avoid Postgres OOM during large imports (`_BATCH_SIZE` in `import_service.py`, `STOCKFISH_POOL_SIZE` env).
- **HTTP client:** `httpx.AsyncClient` only; never `requests` or `berserk` (they block the event loop).

## Anti-Patterns

### SQL in the service layer

**What happens:** Queries written with `select()` inside `app/services/`.
**Why it's wrong:** Breaks the layered contract; makes filters drift and queries untestable in isolation.
**Do this instead:** Put every query in a repository (`app/repositories/`) and call it from the service.

### Re-implementing game filters

**What happens:** A repository rebuilds time-control / platform / recency `where` clauses inline.
**Why it's wrong:** Filter semantics diverge across endpoints; bug fixes only land in one place.
**Do this instead:** Import and call `apply_game_filters()` from `app/repositories/query_utils.py`.

### Resource prefix embedded in route paths

**What happens:** `@router.post("/openings/positions")` while the router already has `prefix="/openings"`.
**Why it's wrong:** Duplicates the prefix on every route and produces `/openings/openings/...`.
**Do this instead:** `APIRouter(prefix="/openings")` + relative decorator paths like `@router.post("/positions")` (see `app/routers/openings.py:24`).

### Comparing positions via full FEN

**What happens:** Using `board.fen()` (includes castling/en passant/clocks) to match positions.
**Why it's wrong:** Equivalent positions reached differently won't match, defeating Zobrist matching.
**Do this instead:** Use `board.board_fen()` for piece placement, and match on the precomputed Zobrist hashes.

### Duplicate TanStack Query Sentry capture

**What happens:** Adding `Sentry.captureException` inside a component that already uses `useQuery`/`useMutation`.
**Why it's wrong:** Double-reports — the global `QueryCache`/`MutationCache` handlers already capture these.
**Do this instead:** Rely on the global handlers in `frontend/src/lib/queryClient.ts`; only capture manual axios/fetch catches.

## Error Handling

**Strategy:** Capture in Sentry at the service/router boundary; let transient retry failures propagate and capture once at the top.

**Patterns:**
- Backend: `sentry_sdk.capture_exception()` in non-trivial `except` blocks in services/routers; variable data via `set_context`/`set_tag`, never interpolated into the message (preserves Sentry grouping). Transient DB connection errors are fingerprinted into one issue via `_sentry_before_send` (`app/main.py:31`).
- Frontend: global capture in `frontend/src/lib/queryClient.ts`; a 401 response interceptor in `frontend/src/api/client.ts` clears the cache and redirects to `/login`. Every `useQuery` render chain must include an `isError` branch.

## Cross-Cutting Concerns

**Logging:** `logging.getLogger(__name__)` per module; Sentry for error reporting (both stacks).
**Validation:** Pydantic v2 at the HTTP boundary (`app/schemas/`); TypedDicts for internal structured data; `Literal[...]` for fixed value sets.
**Authentication:** FastAPI-Users with a JWT auth backend in `app/users.py` (`current_active_user`, plus an impersonation-aware JWT strategy for admin "act as" sessions). `LastActivityMiddleware` (`app/middleware/last_activity.py`) tracks activity. Frontend auth via `frontend/src/hooks/useAuth.ts`; the axios interceptor attaches the bearer token from `localStorage`.

---

*Architecture analysis: 2026-05-30*
