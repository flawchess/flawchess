# Technology Stack

**Analysis Date:** 2026-05-30

## Languages

**Primary:**
- Python 3.13 - Backend API, services, import pipeline, chess analysis (`app/`). Pinned in `.python-version` (`3.13`) and `pyproject.toml` (`requires-python = ">=3.13"`).
- TypeScript ~5.9.3 - Frontend SPA (`frontend/src/`). Strict mode with `noUncheckedIndexedAccess` enabled.

**Secondary:**
- SQL - Alembic migrations (`alembic/versions/`), DB init scripts (`deploy/init-dev-db.sql`).
- Shell - Operational scripts (`bin/*.sh`, `deploy/entrypoint.sh`).

## Runtime

**Backend:**
- Python 3.13 (CPython, `python:3.13-slim` in Docker)
- Uvicorn (`uvicorn[standard]>=0.30.0`) as the ASGI server
- ASGI app: `app.main:app` (FastAPI)

**Frontend:**
- Node.js 24 (build-time only; `node:24-alpine` in `frontend/Dockerfile`, CI uses `node-version: 24`)
- Served as static assets by Caddy in production (no Node runtime in prod)

**Package Managers:**
- Backend: `uv` (Astral, image pinned 0.10.9). Lockfile: `uv.lock` present (`uv sync --locked` in CI/Docker).
- Frontend: `npm`. Lockfile: `frontend/package-lock.json` present (`npm ci` in CI/Docker).

## Frameworks

**Backend Core:**
- FastAPI `fastapi[standard]>=0.115.0` - HTTP API framework. App constructed in `app/main.py`.
- SQLAlchemy `sqlalchemy[asyncio]>=2.0.0` - Async ORM (2.x `select()` API). Engine in `app/core/database.py`.
- Alembic `>=1.13.0` - Database migrations (`alembic.ini`, `alembic/`).
- Pydantic `pydantic>=2.0.0` + `pydantic-settings>=2.0.0` - Validation and typed settings (`app/core/config.py`, `app/schemas/`).
- FastAPI-Users `fastapi-users[oauth,sqlalchemy]>=15.0.4` (resolved 15.0.4) - Auth (`app/users.py`, `app/routers/auth.py`).

**Frontend Core:**
- React 19 (`react`/`react-dom` ^19.2.0) - UI library.
- Vite ^7.3.1 - Build tool and dev server (`frontend/vite.config.ts`).
- TanStack Query `@tanstack/react-query` ^5.90.21 - Server state / data fetching.
- React Router `react-router-dom` ^7.13.1 - Client routing.
- Tailwind CSS ^4.2.1 (`@tailwindcss/vite`) - Styling.
- radix-ui ^1.4.3 + shadcn (generator) - Component primitives.

**Chess-specific:**
- python-chess (`chess>=1.10.0`) - Backend PGN parsing, board logic, Zobrist hashing.
- chess.js ^1.4.0 - Frontend move validation / board logic.
- react-chessboard ^5.10.0 - Interactive board UI.

**AI / LLM:**
- pydantic-ai `pydantic-ai-slim[anthropic,google]>=1.85,<2.0` - Insights agent (`app/services/insights_llm.py`). Model selected via `PYDANTIC_AI_MODEL_INSIGHTS` (Anthropic or Google Gemini).
- genai-prices `>=0.0.56,<0.1.0` - LLM cost attribution (`app/services/insights_*.py`, persisted to `app/models/llm_log.py`).

**Testing:**
- Backend: pytest `>=8.0.0` + pytest-asyncio `>=0.23.0` (`asyncio_mode = "auto"`) + pytest-cov `>=7.1.0`.
- Frontend: Vitest ^4.1.1 + @testing-library/react ^16.3.2 + jsdom ^25.0.1 + @vitest/coverage-v8.

**Build/Dev/Quality:**
- Backend: ruff `>=0.4.0` (lint + format, line-length 100), ty `>=0.0.26` (type checker, zero-error gate in CI).
- Frontend: ESLint ^9.39.1 (flat config, `typescript-eslint`, react-hooks, react-refresh), knip ^6.2.0 (dead-code detection, CI gate), `tsc -b` (build-time type check).
- PWA: vite-plugin-pwa ^1.2.0 (installable mobile app).
- Prerender: vite-prerender-plugin ^0.5.13 (static prerendering of marketing routes).

## Key Dependencies

**Critical (backend):**
- asyncpg `>=0.29.0` - Async PostgreSQL driver (the only DB driver; no SQLite).
- httpx `>=0.27.0` - Async HTTP client for chess.com / lichess / OAuth. The project forbids `requests`/`berserk`.
- httpx-oauth `>=0.16.1` - Google OAuth2 client (`GoogleOAuth2` in `app/routers/auth.py`).
- sentry-sdk `sentry-sdk[fastapi]>=2.54.0` - Error tracking (`app/main.py`).
- python-dotenv `>=1.0.0` - Loads `.env` into `os.environ` so provider SDKs (e.g. Gemini reading `GOOGLE_API_KEY`) see keys (`app/core/config.py`).
- Stockfish (system binary, not a Python package) - UCI engine pool in `app/services/engine.py`. Installed via apt in Docker; path from `STOCKFISH_PATH` (default `/usr/local/bin/stockfish` (set by `STOCKFISH_PATH` in the Docker image)).

**Critical (frontend):**
- axios ^1.15.0 - HTTP client; single instance in `frontend/src/api/client.ts` (`baseURL: '/api'`, cookie credentials).
- @sentry/react ^10.45.0 - Error tracking (`frontend/src/instrument.ts`).
- recharts ^2.15.4 - Charts (WDL, ELO timeline, gauges).
- @dnd-kit/* - Drag-and-drop (bookmark reordering).
- date-fns ^4.2.1, react-day-picker ^10.0.1 - Date handling / recency filter.
- vaul ^1.1.2 - Mobile drawer (filter/bookmark sidebars).
- lucide-react, sonner (toasts), cmdk (command menu), next-themes (dark mode).

**Infrastructure:**
- zstandard `>=0.22` (dev group) - Decompresses Lichess monthly PGN dumps for benchmark seeding (`scripts/select_benchmark_users.py`).

## Configuration

**Environment:**
- Backend settings via `app/core/config.py` (`Settings(BaseSettings)`, `env_file=".env"`, `extra="ignore"`).
- `.env` (gitignored) for local/prod secrets; `.env.example` documents required keys; `.prod.env` synced via 1Password (`bin/download_1password.sh`).
- Frontend build-time env via Vite `VITE_*` vars (e.g. `VITE_SENTRY_DSN`, `VITE_SENTRY_TRACES_SAMPLE_RATE`) injected as Docker build args.
- Never read `.env` contents — secrets only.

**Key backend settings (from `app/core/config.py`):**
- `DATABASE_URL` / `TEST_DATABASE_URL` (asyncpg DSNs), `DB_ECHO`
- `SECRET_KEY` (JWT signing), `ENVIRONMENT` (`development` toggles CORS + drops cookie Secure flag)
- `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`, `BACKEND_URL`, `FRONTEND_URL`
- `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`
- `PYDANTIC_AI_MODEL_INSIGHTS` (LLM model string; empty = unconfigured, aborts startup), `INSIGHTS_HIDE_OVERVIEW`
- Gemini knobs: `GEMINI_THINKING_LEVEL`, `GEMINI_THINKING_BUDGET`, `GEMINI_INCLUDE_THOUGHTS`
- `STOCKFISH_POOL_SIZE` (number of UCI worker processes), `STOCKFISH_PATH`

**Build:**
- Backend: `pyproject.toml` (deps, ruff, ty, pytest config), `uv.lock`. Dockerfile is multi-stage (uv builder → Stockfish stage → `python:3.13-slim` final).
- Frontend: `frontend/vite.config.ts`, `tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json`, `eslint.config.js`, `knip.json`, `components.json` (shadcn).
- Dependency automation: `renovate.json` at repo root.

**Database connection pooling (`app/core/database.py`):**
- `create_async_engine(pool_size=10, max_overflow=10, pool_pre_ping=True)` — 20-connection ceiling per uvicorn process (deliberately bounded after 2026-05-21 Postgres OOM; see CLAUDE.md).

## Platform Requirements

**Development:**
- Python 3.13 + uv; Node 22 + npm.
- Docker for the dev PostgreSQL 18 database: `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` (required before backend/tests).
- Optional Stockfish system binary for engine-dependent tests.

**Production:**
- Hetzner Cloud CPX42 (8 vCPU / 16 GB RAM / 4 GB swap), Docker Compose stack (`docker-compose.yml`):
  - `db`: `postgres:18-alpine` (tuned `shared_buffers=2GB`, `max_connections=30`, `pg_stat_statements`)
  - `backend`: built from root `Dockerfile` (FastAPI/Uvicorn + bundled Stockfish)
  - `umami`: `ghcr.io/umami-software/umami:postgresql-latest` (privacy-friendly analytics)
  - `caddy`: built from `frontend/Dockerfile` (Caddy 2.11.2 serving the prerendered SPA + reverse proxy, auto-TLS)
- Domain flawchess.com; Caddy handles TLS and same-origin routing (no CORS in prod).
- Deploy: `production` branch via GitHub Actions SSH job, triggered by `bin/deploy.sh`. Alembic migrations run on backend container start (`deploy/entrypoint.sh`).

---

*Stack analysis: 2026-05-30*
