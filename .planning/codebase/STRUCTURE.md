# Codebase Structure

**Analysis Date:** 2026-05-30

## Directory Layout

```
flawchess/
├── app/                      # FastAPI backend (Python 3.13)
│   ├── main.py               # ASGI app, middleware, router mounting, lifespan
│   ├── users.py              # FastAPI-Users config: UserManager, auth backend, deps
│   ├── core/                 # config, database (engine/session), rate limiters, opponent strength
│   ├── routers/              # HTTP layer only (one module per resource)
│   ├── services/             # business logic (import, stats, endgames, insights, engine)
│   ├── repositories/         # DB access (SQLAlchemy select()), query_utils shared filters
│   ├── models/               # SQLAlchemy ORM tables (+ base.py declarative Base)
│   ├── schemas/              # Pydantic v2 request/response + internal TypedDicts
│   ├── middleware/           # ASGI middleware (last_activity)
│   ├── prompts/              # LLM prompt templates (endgame_insights.md)
│   └── data/                 # static data (openings.tsv)
├── frontend/                 # React 19 + TypeScript + Vite PWA
│   └── src/
│       ├── main.tsx          # React entry (mounts QueryClientProvider + App)
│       ├── App.tsx           # BrowserRouter + routes + nav/layout shells
│       ├── instrument.ts     # Sentry init (must import first)
│       ├── pages/            # top-level route screens (+ openings/ sub-tabs & hooks)
│       ├── components/       # feature + ui components (grouped by domain)
│       ├── hooks/            # TanStack Query hooks (use*.ts)
│       ├── api/              # axios client + typed resource APIs (client.ts)
│       ├── lib/              # queryClient, theme, chess/stat utils
│       ├── data/             # static lookup tables (trollOpenings.ts)
│       ├── generated/        # generated TS (endgameZones.ts — do not hand-edit)
│       └── types/            # shared TS types per resource
├── alembic/                  # migrations (env.py + versions/, 63 revisions)
├── scripts/                  # CLI maintenance scripts (seed, reimport, benchmark, eval, CDF)
├── bin/                      # shell ops scripts (deploy, db tunnels, 1password, hooks)
├── deploy/                   # Caddyfile, entrypoint.sh, init-*-db.sql, cloud-init.yml
├── tests/                    # pytest backend tests (mirrors app/ layout)
├── docs/ reports/ logo/ screenshots/   # docs, generated reports, assets
├── docker-compose*.yml       # dev / benchmark / prod compose files
├── Dockerfile                # backend image
├── pyproject.toml / uv.lock  # backend deps (uv)
└── CLAUDE.md                 # project conventions (authoritative)
```

## Directory Purposes

**`app/routers/`:**
- Purpose: HTTP endpoints only; validate, call service, shape response
- Contains: one module per resource — `admin.py`, `auth.py`, `endgames.py`, `imports.py`, `insights.py`, `openings.py`, `position_bookmarks.py`, `stats.py`, `users.py`
- Key files: `app/routers/openings.py` (canonical router-prefix pattern)

**`app/services/`:**
- Purpose: all business logic and external integrations (the largest layer, ~30 modules)
- Contains: `import_service.py` (import pipeline + reaper), `endgame_service.py`, `stats_service.py`, `openings_service.py`, `opening_insights_service.py`, `insights_service.py`, `insights_llm.py` (pydantic-ai agent), `engine.py` (Stockfish pool), `eval_drain.py`, `position_classifier.py`, `normalization.py`, `zobrist.py`, `chesscom_client.py`, `lichess_client.py`, `chesscom_to_lichess.py`, percentile/CDF modules, `admin_service.py`, `guest_service.py`
- Key files: `app/services/zobrist.py`, `app/services/engine.py`, `app/services/import_service.py`
- Note: `app/services/global_percentile_cdf.py` is a very large generated/data module (~97k lines) — treat as data, not hand-edited logic

**`app/repositories/`:**
- Purpose: DB queries; no SQL anywhere else
- Contains: `*_repository.py` per domain + `query_utils.py`
- Key files: `app/repositories/query_utils.py` (`apply_game_filters()` — shared filter source of truth)

**`app/models/`:**
- Purpose: SQLAlchemy ORM tables with mandatory FK constraints; declarative `Base` in `app/models/base.py`
- Key files: `app/models/game.py` (`Game`; `GamePosition` lives in `app/models/game_position.py` with `white_hash`/`black_hash`/`full_hash`), `user.py`, `oauth_account.py`, `position_bookmark.py`, `opening.py`, `import_job.py`, `llm_log.py`, `user_benchmark_percentile.py`, `user_rating_anchors.py`, `benchmark_selected_user.py`, `benchmark_ingest_checkpoint.py`

**`app/core/`:**
- Purpose: app-wide infrastructure
- Key files: `config.py` (settings), `database.py` (engine + `get_async_session`), `rate_limiters.py`, `ip_rate_limiter.py`, `opponent_strength.py`. (Auth deps are NOT here — they live in `app/users.py`.)

**`frontend/src/components/`:**
- Purpose: React components grouped by feature domain
- Contains: `admin/`, `auth/`, `board/`, `charts/` (largest, ~22 files), `filters/`, `icons/`, `insights/`, `install/`, `layout/`, `move-explorer/`, `popovers/`, `position-bookmarks/`, `results/`, `stats/`, `ui/` (24 shadcn-style primitives), plus two root-level shells (`EndgamesProcessingState.tsx`, `EvalCoverageHeader.tsx`)
- Feature dirs co-locate `__tests__/` folders

**`frontend/src/pages/`:**
- Purpose: top-level route screens
- Key files: `Openings.tsx`, `Endgames.tsx`, `GlobalStats.tsx`, `Import.tsx`, `Home.tsx`, `Auth.tsx`, `Admin.tsx`, `Privacy.tsx`, `OAuthCallbackPage.tsx`; `pages/openings/` holds tab subcomponents (`ExplorerTab`, `GamesTab`, `InsightsTab`, `StatsTab`) and page-local hooks

**`frontend/src/hooks/`:**
- Purpose: TanStack Query hooks, one per API resource
- Key files: `useOpenings.ts`, `useEndgames.ts`, `useStats.ts`, `useImport.ts`, `useOpeningInsights.ts`, `useEndgameInsights.ts`, `usePositionBookmarks.ts`, `useAuth.ts`, `useUserProfile.ts`, `useReadiness.ts`, `useFilterStore.ts`

**`frontend/src/api/`:**
- Purpose: axios instance and typed resource APIs (all in one file)
- Key files: `client.ts` (the `apiClient` axios instance, bearer-token interceptor, 401 redirect, `buildFilterParams`, and `positionBookmarksApi` / `statsApi` / `endgameApi` / `timeSeriesApi` objects)

## Key File Locations

**Entry Points:**
- `app/main.py`: FastAPI ASGI app + lifespan
- `frontend/src/main.tsx`: React root mount
- `frontend/src/App.tsx`: client routes, nav, layout guards
- `deploy/entrypoint.sh`: container start (Alembic migrate → Uvicorn)

**Configuration:**
- `app/core/config.py`: backend settings (env-driven)
- `pyproject.toml` / `uv.lock`: backend deps
- `frontend/package.json` / `vite.config.ts` / `tsconfig.json`: frontend build
- `alembic.ini`: migration config
- `.env` / `.env.example`: env vars (never commit real secrets)

**Core Logic:**
- `app/services/import_service.py`: import pipeline + orphan reaper
- `app/services/zobrist.py`: position hashing
- `app/repositories/query_utils.py`: shared game filters
- `app/services/engine.py`: Stockfish EnginePool
- `app/users.py`: auth backend + `current_active_user` dependency

**Testing:**
- `tests/`: backend pytest (mirrors `app/`)
- `frontend/src/**/__tests__/`: co-located frontend tests

## Naming Conventions

**Files:**
- Backend modules: `snake_case.py`; repositories end `_repository.py`; most services end `_service.py` (utility services use descriptive names, e.g. `zobrist.py`, `engine.py`, `normalization.py`)
- Frontend components: `PascalCase.tsx`; hooks: `useXxx.ts`; API/libs/types: `camelCase.ts` / `snake_case.ts` (types mirror backend resource names, e.g. `position_bookmarks.ts`)
- Tests: backend `test_*.py`; frontend `*.test.ts(x)` (co-located, often under `__tests__/`)

**Directories:**
- Backend layers are flat by role: `routers/`, `services/`, `repositories/`, `models/`, `schemas/`
- Frontend component groups are kebab-case by feature: `move-explorer/`, `position-bookmarks/`

## Where to Add New Code

**New API resource (end-to-end):**
- Model: `app/models/<resource>.py` (+ Alembic migration via `uv run alembic revision --autogenerate`)
- Schema: `app/schemas/<resource>.py` (Pydantic v2; use `Literal[...]` for fixed value sets)
- Repository: `app/repositories/<resource>_repository.py` (use `apply_game_filters()` for game queries)
- Service: `app/services/<resource>_service.py` (business logic)
- Router: `app/routers/<resource>.py` with `APIRouter(prefix="/<resource>", tags=["<resource>"])`, then `include_router(..., prefix="/api")` in `app/main.py`
- Frontend: add a typed API call in `frontend/src/api/client.ts`, a `frontend/src/hooks/use<Resource>.ts`, components under `frontend/src/components/<feature>/`, and a type module in `frontend/src/types/`

**New frontend feature/component:**
- Implementation: `frontend/src/components/<feature>/<Component>.tsx`
- Tests: `frontend/src/components/<feature>/__tests__/<Component>.test.tsx`
- Add `data-testid` to all interactive/layout elements; theme colors via `frontend/src/lib/theme.ts`

**New page/route:**
- `frontend/src/pages/<Name>.tsx`, wired into `frontend/src/App.tsx` (under `ProtectedLayout` for authenticated pages, behind `ImportRequiredRoute`/`SuperuserRoute` where appropriate)

**Shared helpers:**
- Backend: a service module, or `app/repositories/query_utils.py` for query filters
- Frontend: `frontend/src/lib/`

**Migrations:**
- `uv run alembic revision --autogenerate -m "..."` → review the file in `alembic/versions/`

## Special Directories

**`frontend/src/generated/`:**
- Purpose: machine-generated TS (`endgameZones.ts` from `app/services/endgame_zones.py` via `scripts/gen_endgame_zones_ts.py`)
- Generated: Yes — CI fails on drift; regenerate after editing the Python registry, do not hand-edit
- Committed: Yes

**`alembic/versions/`:**
- Purpose: 63 migration revisions; applied automatically on container start by `deploy/entrypoint.sh`
- Generated: Partly (autogenerate); Committed: Yes

**`scripts/`:**
- Purpose: manual maintenance/benchmark CLIs (seed openings, reimport, reclassify, benchmark ingest, eval backfill, CDF + percentile generation, stress tests)
- Generated: No; Committed: Yes

**`reports/`, `screenshots/`, `htmlcov/`, `logs/`, `temp/`:**
- Purpose: generated reports / captures / coverage HTML / runtime logs / scratch
- Generated: Yes (mostly); Committed: varies (coverage/temp/logs typically gitignored)

---

*Structure analysis: 2026-05-30*
