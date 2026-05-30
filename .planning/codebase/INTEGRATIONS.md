# External Integrations

**Analysis Date:** 2026-05-30

## APIs & External Services

**Chess game sources (import pipeline):**
- chess.com Public API - Imports user game archives.
  - Client: `app/services/chesscom_client.py` (httpx async)
  - Base URL: `https://api.chess.com/pub/player`
  - Auth: none (public API), but requires a descriptive `User-Agent` header (`FlawChess/1.0 (github.com/flawchess/flawchess)`) or chess.com returns 403.
  - Behavior: fetches monthly archives sequentially with a ~150ms delay (`_ARCHIVE_DELAY_SECONDS`), 3 retries with 2s backoff. Normalized via `app/services/normalization.py`.
- lichess API - Imports user games (rated standard, with clocks/openings).
  - Client: `app/services/lichess_client.py` (httpx async)
  - Base URL: `https://lichess.org`
  - Auth: none required for public game export (no API token).
  - Behavior: streams NDJSON line-by-line; `since`/`until` use millisecond timestamps; 30s/60s timeouts, 3 retries. Only `Standard` variant games are kept.

**LLM providers (insights narration):**
- Anthropic Claude and/or Google Gemini - AI-narrated endgame and opening insights.
  - Client: pydantic-ai (`app/services/insights_llm.py`, `insights_endgame.py`, `insights_openings.py`)
  - Model selected by `PYDANTIC_AI_MODEL_INSIGHTS` (e.g. `anthropic:claude-haiku-4-5-...`, `google-gla:gemini-2.5-flash`).
  - Auth: provider API keys read from environment (`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`) via `pydantic-ai-slim[anthropic,google]`. `python-dotenv` loads `.env` into `os.environ` so provider SDKs see keys.
  - Endpoints served: `POST /api/insights/endgame`, `POST /api/insights/openings`.
  - Cost tracking: `genai-prices` computes per-call cost; persisted to `llm_logs` table (`app/models/llm_log.py`).
  - Tests use pydantic-ai's built-in `test` provider (`PYDANTIC_AI_MODEL_INSIGHTS=test`).

**Chess engine (local binary, not a network API):**
- Stockfish - Position evaluation (`eval_cp` / `eval_mate`) for endgame analysis.
  - Integration: `app/services/engine.py` (long-lived UCI process pool, `STOCKFISH_POOL_SIZE` workers under Linux SCHED_IDLE).
  - Binary path: `STOCKFISH_PATH` (Docker sets `/usr/local/bin/stockfish`; module default in `engine.py` also `/usr/local/bin/stockfish`). Pinned official release sf_18 downloaded with SHA-256 verification in the Dockerfile (not apt).

## Data Storage

**Databases:**
- PostgreSQL 18 (the only database; no SQLite by project rule).
  - Driver: asyncpg via SQLAlchemy 2.x async (`app/core/database.py`).
  - Connection: `DATABASE_URL` (e.g. `postgresql+asyncpg://...`).
  - Migrations: Alembic (`alembic/`), auto-run on backend container start (`deploy/entrypoint.sh`).
  - Environments: dev (Docker `localhost:5432`), benchmark (Docker `localhost:5433`), prod (containerized, read-only tunnel on `localhost:15432` via `bin/prod_db_tunnel.sh`).
  - Also hosts the `umami` analytics database (same Postgres instance, separate DB).

**File Storage:**
- Local filesystem only. No object storage (S3/GCS) integration.
- Static seed data: `app/data/openings.tsv` (openings with precomputed Zobrist hashes).
- Benchmark seeding reads Lichess monthly PGN dumps (`.pgn.zst`) from disk (`scripts/select_benchmark_users.py`).

**Caching:**
- No external cache (no Redis/Memcached). In-process `functools.lru_cache` is used (e.g. the insights agent factory in `app/services/insights_llm.py`).

## Authentication & Identity

**Auth Provider:**
- FastAPI-Users 15.0.4 (`app/users.py`, `app/routers/auth.py`).
  - Strategy: Bearer-token JWT (`BearerTransport` + `ClaimAwareJWTStrategy`), 7-day default lifetime, signed with `SECRET_KEY`. The frontend stores the token (delivered via the OAuth redirect URL fragment) and sends it as a Bearer header.
  - Guest sessions get a 30-day Bearer JWT (`/api/auth/guest/create`), refreshable and promotable to a full account.
  - Impersonation: `ImpersonationJWTStrategy` issues short-lived (1h) admin act-as tokens; `ClaimAwareJWTStrategy` dispatches per-token. User model: `app/models/user.py` (integer primary keys, `IntegerIDMixin`).
- Google OAuth2 (`httpx_oauth.clients.google.GoogleOAuth2`).
  - Configured in `app/routers/auth.py` with `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`.
  - Flow: `GET /api/auth/google/authorize` returns the auth URL; callback `GET /api/auth/google/callback` exchanges the code, issues a JWT, and redirects to `{FRONTEND_URL}/auth/callback#token=...`. CSRF double-submit cookie (`flawchess_oauth_csrf`) protects the state round-trip (CVE-2025-68481 fix). `associate_by_email=True`, `is_verified_by_default=True`. A guest-promotion variant uses `/api/auth/google/callback-promote`.
  - Only active when credentials are configured (frontend degrades gracefully if unavailable).
- Guest usage supported (analyze without an account).

## Monitoring & Observability

**Error Tracking:**
- Sentry (org `flawchess`, project ID 4511084868272208, region de.sentry.io).
  - Backend: `sentry-sdk[fastapi]` initialized in `app/main.py` (gated on `SENTRY_DSN`; `send_default_pii=False`; custom `before_send` groups transient DB-connection errors).
  - Frontend: `@sentry/react` in `frontend/src/instrument.ts` (gated on `VITE_SENTRY_DSN`, browser tracing).
  - Sampling: `SENTRY_TRACES_SAMPLE_RATE` / `VITE_SENTRY_TRACES_SAMPLE_RATE` (0.0 in dev).

**Analytics:**
- Umami (self-hosted, `ghcr.io/umami-software/umami:postgresql-latest` in `docker-compose.yml`).
  - Script loaded in `frontend/index.html` (`<script defer src="https://analytics.flawchess.com/script.js" data-website-id=...>`). Caddy reverse-proxies `analytics.flawchess.com` → `umami:3000` (`deploy/Caddyfile`); backed by a `umami` DB on the shared Postgres instance. Cookieless / privacy-friendly.

**Logs:**
- Standard Python `logging` to stdout (`PYTHONUNBUFFERED=1`); viewed via `docker compose logs backend` on the prod host. `logs/` directory present locally.
- Postgres `pg_stat_statements` enabled for query monitoring.

## CI/CD & Deployment

**Hosting:**
- Hetzner Cloud CPX42; Docker Compose stack (Postgres 18 + FastAPI/Uvicorn + Umami + Caddy 2.11.2). Domain flawchess.com with Caddy auto-TLS.

**CI Pipeline:**
- GitHub Actions (`.github/workflows/ci.yml`), runs on push/PR to `main` and `production`.
  - Single `test` job (Python 3.13 + Node 24): `postgres:18-alpine` service, `uv sync --locked`, endgame-zone drift check, pip-audit, ruff check + format check, ty check, Stockfish install, pytest; then `npm ci`, npm audit, eslint, build (`tsc -b && vite build`), vitest, knip; finally a Docker image build with Trivy HIGH/CRITICAL scan.
  - `deploy` job: gated on `workflow_dispatch` against `production`; deploys via SSH (`appleboy/ssh-action`) — `git reset --hard origin/production`, `docker compose build --no-cache backend caddy`, `docker compose up -d`, then a `/api/health` poll.
- CodeQL security scanning: `.github/workflows/codeql.yml`.
- Dependency automation: Renovate (`renovate.json`).
- Deploy entrypoint: `bin/deploy.sh` (promotes/deploys the `production` branch). GitLab Flow: `main` = trunk, `production` = exactly-deployed branch.

## Environment Configuration

**Required env vars (backend, from `app/core/config.py` / `.env.example`):**
- `DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT`, `BACKEND_URL`, `FRONTEND_URL`
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
- `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`
- `PYDANTIC_AI_MODEL_INSIGHTS`, provider keys (`ANTHROPIC_API_KEY` and/or `GOOGLE_API_KEY`), Gemini thinking knobs
- `STOCKFISH_POOL_SIZE`, `STOCKFISH_PATH`
- Compose-level: `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`, `UMAMI_DB_USER` / `UMAMI_DB_PASSWORD` / `UMAMI_APP_SECRET`

**Frontend (build-time `VITE_*`):**
- `VITE_SENTRY_DSN`, `VITE_SENTRY_TRACES_SAMPLE_RATE` (injected as Docker build args).

**Secrets location:**
- Local/prod: `.env` (gitignored), prod `.env` at `/opt/flawchess/.env` on the server.
- Synced to/from the FlawChess 1Password vault via `bin/download_1password.sh` / `bin/upload_1password.sh`.
- CI: GitHub Actions secrets (`VITE_SENTRY_DSN`, SSH deploy creds).
- The benchmark DB read-only password lives only in the local working tree (`deploy/init-benchmark-db.sql`, assume-unchanged).

## Webhooks & Callbacks

**Incoming:**
- None. No third-party webhook endpoints. The only callback route is the OAuth redirect handled client-side at `{FRONTEND_URL}/auth/callback`.

**Outgoing:**
- None (no outbound webhooks). External calls are all request/response: chess.com, lichess, and LLM provider APIs.

## API Surface (internal, served by backend)

All routers are mounted under `/api` (`app/main.py`). Frontend axios client targets `baseURL: '/api'` (`frontend/src/api/client.ts`), proxied same-origin by Caddy in prod.
- `/api/auth` (+ `/api/auth/google`), `/api/imports`, `/api/openings`, `/api/position-bookmarks`,
  `/api/stats`, `/api/endgames`, `/api/insights`, `/api/users`, `/api/admin`, `/api/health`.

---

*Integration audit: 2026-05-30*
