# Architecture Research

**Domain:** Production deployment — Docker, Caddy, CI/CD, monitoring, analytics for FastAPI + React SPA
**Researched:** 2026-03-21
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Hetzner Cloud VPS                         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Caddy (port 80/443)                     │    │
│  │  - Auto-SSL via Let's Encrypt                        │    │
│  │  - Serves /dist static files (SPA + PWA assets)     │    │
│  │  - Proxies API routes → backend:8000                 │    │
│  │  - SPA fallback: try_files → /index.html            │    │
│  └──────────┬───────────────────────────────────────────┘   │
│             │ /auth /analysis /games /imports etc.           │
│  ┌──────────▼──────────┐   ┌──────────────────────────┐    │
│  │  FastAPI + Uvicorn  │   │     PostgreSQL 16         │    │
│  │  (backend:8000)     │──▶│  (db:5432)               │    │
│  │  - 4 Uvicorn workers│   │  - asyncpg driver         │    │
│  │  - Alembic on start │   │  - named volume           │    │
│  └─────────────────────┘   └──────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Docker volumes (persistent)               │   │
│  │   caddy_data (Let's Encrypt certs)                   │   │
│  │   postgres_data (DB files)                           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

             ┌──────────────────────────────┐
             │  GitHub Actions (CI/CD)      │
             │  1. test + lint              │
             │  2. build images → push GHCR │
             │  3. SSH → VPS               │
             │     docker compose pull      │
             │     docker compose up -d     │
             └──────────────────────────────┘

             ┌──────────────────────────────┐
             │  External Services           │
             │  - Sentry (errors + perf)    │
             │  - Plausible (analytics)     │
             └──────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| Caddy | TLS termination, reverse proxy, static file serving | Serves pre-built `/srv` directly; auto-renews Let's Encrypt certs stored in `caddy_data` volume |
| FastAPI backend | API logic, auth, chess game import, analysis | uv multi-stage Docker build; Alembic runs migrations before app starts |
| PostgreSQL | Persistent data store | `postgres:16-alpine`; named volume; healthcheck gates backend startup |
| GitHub Actions | CI: test + lint; CD: build images, push to GHCR, SSH-deploy | Secrets: `GHCR_TOKEN`, `VPS_SSH_KEY`, `VPS_HOST` |
| Sentry | Error tracking + performance monitoring | Python SDK in FastAPI; `@sentry/react` in React; single project, two DSNs |
| Plausible / GA | Page view tracking | Script tag in `index.html`; no build-time code changes needed |

---

## Recommended Project Structure

New files to add to the existing repo:

```
flawchess/                          # repo root (after rename)
├── Dockerfile                      # NEW: backend multi-stage build (uv)
├── docker-compose.yml              # NEW: production services
├── .env.example                    # NEW: template for production secrets
├── caddy/
│   └── Caddyfile                   # NEW: reverse proxy + SPA config
├── frontend/
│   ├── Dockerfile                  # NEW: frontend multi-stage → Caddy image
│   └── ...                         # existing files
└── .github/
    └── workflows/
        └── deploy.yml              # NEW: CI/CD pipeline
```

### Structure Rationale

- **`Dockerfile` at repo root** — builds the backend; stays next to `pyproject.toml` and `uv.lock` for clean COPY paths
- **`frontend/Dockerfile`** — separate from backend; builds the React SPA into `/dist` then into a Caddy image
- **`caddy/Caddyfile`** — isolated from compose; mounted as a bind-mount so Caddy config can be updated without rebuilding any image
- **`docker-compose.yml`** — single production compose file; no dev overrides needed
- **`.env.example`** — documents all required env vars; `.env` on VPS is gitignored

---

## Architectural Patterns

### Pattern 1: Caddy Serving SPA + API on Same Domain

**What:** Caddy serves pre-built React static files from `/srv` and reverse-proxies all API route prefixes to the FastAPI container. SPA client-side routing is handled via `try_files` fallback to `/index.html`.

**When to use:** Always for this deployment — same-domain SPA + API eliminates CORS entirely in production. Browser makes API calls to the same origin it loaded the app from.

**Trade-offs:** Routing table in Caddyfile must stay in sync with FastAPI route prefixes. The Vite dev proxy (`vite.config.ts`) mirrors this same routing table for local development.

**Caddyfile:**
```
flawchess.com {
    encode gzip

    # API routes — proxy to backend (must match vite.config.ts proxy config)
    handle /auth/* {
        reverse_proxy backend:8000
    }
    handle /analysis/* {
        reverse_proxy backend:8000
    }
    handle /games/* {
        reverse_proxy backend:8000
    }
    handle /imports/* {
        reverse_proxy backend:8000
    }
    handle /position-bookmarks/* {
        reverse_proxy backend:8000
    }
    handle /stats/* {
        reverse_proxy backend:8000
    }
    handle /users/* {
        reverse_proxy backend:8000
    }
    handle /health {
        reverse_proxy backend:8000
    }

    # SPA fallback — serve static assets with index.html fallback for client-side routing
    handle {
        root * /srv
        try_files {path} /index.html
        file_server
    }
}
```

**CORS change needed:** Because frontend and API share the same origin in production, CORS is only needed for development. `app/main.py` currently hardcodes `allow_origins=["http://localhost:5173"]`. This needs to read from `Settings` so production can configure it via env var.

### Pattern 2: uv Multi-Stage Backend Dockerfile

**What:** Two-stage Docker build. Builder stage installs deps with uv. Runtime stage copies only `.venv` and app source. No uv, pip, or build tools in the final image.

**When to use:** Always — the official uv Docker recommendation. Layer caching on `uv.lock` + `pyproject.toml` means the deps layer is only re-built when dependencies change, not on every code commit.

**Backend `Dockerfile`:**
```dockerfile
# --- Builder ---
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Deps layer (cached until uv.lock or pyproject.toml changes)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

# App source
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# --- Runtime ---
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"

# Entrypoint: run migrations then start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]
```

### Pattern 3: Frontend Multi-Stage Build Into Caddy Image

**What:** Two-stage frontend Dockerfile. Stage 1: Node.js runs `npm ci && npm run build`. Stage 2: Caddy image with the built `/dist` copied to `/srv` and the Caddyfile copied in.

**When to use:** This approach bundles the static assets and Caddy config into a single versioned image — clean rollbacks, no separate `rsync` step.

**`VITE_` vars are baked in at build time.** The API URL is not needed as a `VITE_` var because the SPA and API are same-origin (Caddy proxies both). Only public-safe values belong in `VITE_`: Sentry DSN (public key), analytics domain.

**`frontend/Dockerfile`:**
```dockerfile
# Stage 1: Build SPA
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_SENTRY_DSN
ARG VITE_PLAUSIBLE_DOMAIN
RUN npm run build

# Stage 2: Caddy serves the built output
FROM caddy:2-alpine
COPY --from=builder /app/dist /srv
COPY caddy/Caddyfile /etc/caddy/Caddyfile
```

### Pattern 4: PostgreSQL Healthcheck Gates Backend Start

**What:** `depends_on: condition: service_healthy` ensures PostgreSQL is accepting connections before the backend container starts. The backend entrypoint runs `alembic upgrade head` — this needs a live database.

**When to use:** Always. Without this, the backend container starts immediately, `alembic upgrade head` fails with a connection error, and the app never comes up on first boot.

**`docker-compose.yml` excerpt:**
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  backend:
    image: ghcr.io/${GITHUB_OWNER}/flawchess-backend:${IMAGE_TAG}
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  caddy:
    image: ghcr.io/${GITHUB_OWNER}/flawchess-caddy:${IMAGE_TAG}
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - caddy_data:/data
    depends_on:
      - backend

volumes:
  postgres_data:
  caddy_data:
```

### Pattern 5: Sentry Integration — Minimal Touch Points

**What:** Sentry SDK initialized once in `app/main.py` (backend) and `frontend/src/main.tsx` (frontend). FastAPI integration is automatic when `sentry-sdk` is installed and `sentry_sdk.init()` is called. React integration adds browser tracing.

**When to use:** Both integrations are guarded by a null check on `SENTRY_DSN` — development runs without Sentry noise.

**Backend — modify `app/main.py`:**
```python
import sentry_sdk
from app.core.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,  # 10% sampling; raise to 1.0 for debugging
    )
```

**Add to `app/core/config.py`:**
```python
SENTRY_DSN: str = ""
CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]
```

**Update CORS in `app/main.py`:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Frontend — modify `frontend/src/main.tsx`:**
```typescript
import * as Sentry from "@sentry/react";

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
  });
}
```

**Install:**
```bash
# Backend
uv add sentry-sdk

# Frontend
npm install @sentry/react
npm install -D @sentry/vite-plugin  # optional: for source map upload
```

### Pattern 6: CI/CD via GitHub Actions with SSH Deploy

**What:** GitHub Actions runs tests and lint on every push. On push to `main`, it builds both Docker images, pushes to GitHub Container Registry (GHCR), SSHs into the VPS, pulls the new images, and restarts services.

**When to use:** Standard pattern for single-server deployments. No orchestration layer needed for this scale.

**`.github/workflows/deploy.yml` (outline):**
```yaml
on:
  push:
    branches: [main]

jobs:
  test:
    steps:
      - uv run pytest
      - uv run ruff check .
      - npm run lint (frontend)

  build-and-deploy:
    needs: test
    steps:
      - Log in to GHCR
      - Build backend image with docker build → push to ghcr.io/owner/flawchess-backend:sha
      - Build frontend (with VITE_SENTRY_DSN build arg) → push to ghcr.io/owner/flawchess-caddy:sha
      - SSH into VPS:
          echo "IMAGE_TAG=${sha}" > .env.deploy
          docker compose --env-file .env --env-file .env.deploy pull
          docker compose --env-file .env --env-file .env.deploy up -d
```

**GitHub Secrets required:**
- `GHCR_TOKEN` — GitHub personal access token with `write:packages`
- `VPS_SSH_KEY` — private key for the deploy user on the VPS
- `VPS_HOST` — IP or hostname of the Hetzner VPS
- `VITE_SENTRY_DSN` — public Sentry DSN for frontend bundle (safe to put in CI)

---

## Data Flow

### Production Request Flow

```
Browser
  │
  ▼
Caddy:443 (TLS termination, gzip)
  │
  ├─ /auth /analysis /games /imports /stats /users /health
  │     ──▶ FastAPI:8000 ──▶ PostgreSQL:5432
  │              │
  │         (async response with JSON)
  │
  └─ all other paths (/, /openings, /bookmarks, etc.)
        ──▶ /srv/index.html  (React Router handles client routing)
              │
         /srv/assets/*.js|css|png  (static, content-hashed, cached by browser)
```

### Deploy Flow

```
git push main
  │
  ▼
GitHub Actions CI: uv run pytest → uv run ruff → npm run lint
  │ (pass)
  ▼
docker build backend → push ghcr.io/owner/flawchess-backend:${sha}
docker build frontend (with VITE_SENTRY_DSN) → push ghcr.io/owner/flawchess-caddy:${sha}
  │
  ▼
SSH into VPS
  │  docker compose pull   (pulls new images)
  │  docker compose up -d  (restarts changed services)
  ▼
backend entrypoint: alembic upgrade head → uvicorn start (4 workers)
```

### Environment Variable Flow

```
VPS: /root/flawchess/.env  (gitignored, manually provisioned once)
  │
  ▼ (docker-compose env_file)
  ├─▶ backend: DATABASE_URL, SECRET_KEY, GOOGLE_OAUTH_CLIENT_ID,
  │             GOOGLE_OAUTH_CLIENT_SECRET, SENTRY_DSN, ENVIRONMENT=production,
  │             CORS_ALLOWED_ORIGINS=["https://flawchess.com"]
  └─▶ db: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

Build-time (GitHub Actions secrets → docker build --build-arg):
  VITE_SENTRY_DSN → baked into JS bundle (public key, not secret)
  VITE_PLAUSIBLE_DOMAIN → baked into JS bundle (optional, for self-hosted Plausible)
```

---

## New vs Modified Components

| Component | New or Modified | What Changes |
|-----------|----------------|--------------|
| `Dockerfile` | **New** | Backend uv multi-stage build |
| `frontend/Dockerfile` | **New** | Node multi-stage build → Caddy image |
| `docker-compose.yml` | **New** | Orchestrates backend, db, caddy |
| `caddy/Caddyfile` | **New** | Reverse proxy + SPA + API routing |
| `.env.example` | **New** | Documents all required env vars |
| `.github/workflows/deploy.yml` | **New** | CI/CD pipeline |
| `app/main.py` | **Modified** | Add Sentry init; read CORS origins from settings |
| `app/core/config.py` | **Modified** | Add `SENTRY_DSN`, `CORS_ALLOWED_ORIGINS` fields |
| `frontend/src/main.tsx` | **Modified** | Add Sentry init |
| `frontend/vite.config.ts` | **Modified** | FlawChess branding in PWA manifest |
| `frontend/index.html` | **Modified** | Add analytics script tag (Plausible or GA) |
| `pyproject.toml` | **Modified** | Add `sentry-sdk` dependency |
| `frontend/package.json` | **Modified** | Add `@sentry/react` |

### What Does NOT Change

| Item | Why unchanged |
|------|---------------|
| SQLAlchemy models / Alembic migrations | No schema changes in this milestone |
| FastAPI routers, services, repositories | Business logic untouched |
| React page components | No new pages except About; SEO is meta tags in `index.html` |
| TanStack Query / Axios setup | API URL is same-origin in production; no `baseURL` needed |
| PWA service worker config | Workbox `NetworkOnly` patterns already correct |

---

## Integration Points

### External Service Integration

| Service | Integration Point | What to Add | Notes |
|---------|-------------------|-------------|-------|
| Sentry (backend) | `app/main.py` | `sentry_sdk.init()` call | Auto-detects FastAPI; no per-route changes needed |
| Sentry (frontend) | `frontend/src/main.tsx` | `Sentry.init()` + `browserTracingIntegration()` | Source maps: add `@sentry/vite-plugin` to `vite.config.ts` (optional but recommended) |
| Let's Encrypt | `caddy/Caddyfile` | Domain name in Caddyfile | Zero config; Caddy handles cert issuance and renewal; `caddy_data` volume must persist |
| Plausible analytics | `frontend/index.html` | `<script>` tag | Cookie-free, GDPR compliant, ~1KB script; add to `<head>` |
| GHCR | `.github/workflows/deploy.yml` | `docker/login-action` + push step | Free for public repos; `ghcr.io/[owner]/[repo]` naming |
| Hetzner VPS | `.github/workflows/deploy.yml` | SSH deploy step | Deploy key (not personal SSH key) added to VPS `~/.ssh/authorized_keys` |

### Internal Boundaries After This Milestone

| Boundary | Communication | Change Required |
|----------|---------------|-----------------|
| Frontend → Backend (prod) | Same-origin HTTP via Caddy | No `baseURL` needed; relative `/auth/...` paths work |
| Frontend → Backend (dev) | Vite proxy to `localhost:8000` | No change — dev workflow unchanged |
| Backend → PostgreSQL | `asyncpg` TCP on Docker internal network | `DATABASE_URL` host changes from `localhost` to `db` (Docker service name) |
| Caddy → Backend | HTTP on Docker internal network | Backend port `8000` not published externally — Caddy is the only ingress |
| GitHub Actions → VPS | SSH with deploy key | New deploy key pair; public key on VPS, private key in GitHub secrets |

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Current single-VPS monolith is fine; Hetzner CX22 (2 vCPU / 4GB RAM) sufficient |
| 1k-10k users | Increase Uvicorn workers; upgrade VPS size; add PgBouncer for connection pooling |
| 10k+ users | Move DB to managed PostgreSQL (Hetzner Managed DB or Neon); CDN for static assets (Cloudflare free tier); Redis for import queue |

### Scaling Priorities

1. **First bottleneck:** PostgreSQL connection pool — `pool_size=10, max_overflow=20` is conservative; add PgBouncer before scaling worker count
2. **Second bottleneck:** Import pipeline CPU (Zobrist hash computation per half-move) — move to background worker (Celery + Redis) if import times degrade under concurrent users

---

## Anti-Patterns

### Anti-Pattern 1: Building Frontend Inside the Backend Docker Image

**What people do:** Copy all frontend source into the backend image, run `npm run build` there, and serve `/dist` from FastAPI static files.

**Why it's wrong:** Makes the backend image enormous (node_modules), conflates two independent build pipelines, prevents independent deployment and rollback of frontend vs backend.

**Do this instead:** Separate `Dockerfile` for frontend. Serve pre-built `/dist` from Caddy. FastAPI serves only API routes — it should never serve static files in production.

### Anti-Pattern 2: Hardcoding `allow_origins=["http://localhost:5173"]` in Production

**What people do:** The current `app/main.py` hardcodes the dev origin. Many projects leave this unchanged when deploying.

**Why it's wrong:** In production all requests are same-origin (no CORS needed), but the hardcoded localhost origin is useless and leaks dev infrastructure detail. If `allow_credentials=True` is combined with `allow_origins=["*"]`, browsers reject it as insecure.

**Do this instead:** Read `CORS_ALLOWED_ORIGINS` from `Settings`. In production, set it to `["https://flawchess.com"]`. The existing `Settings` pattern in `app/core/config.py` already supports this.

### Anti-Pattern 3: Running Alembic Migrations in the FastAPI Lifespan

**What people do:** Call `alembic upgrade head` inside the FastAPI `lifespan` async context. Seems convenient — the app migrates on every start.

**Why it's wrong:** If two containers start simultaneously (even two rapid restarts), they race to acquire Alembic's version lock. Also, `lifespan` is async — Alembic's upgrade command is synchronous and should not block the event loop.

**Do this instead:** Run `alembic upgrade head` in the Docker `CMD` before starting uvicorn: `sh -c "alembic upgrade head && uvicorn app.main:app ..."`. Synchronous, sequential, correct.

### Anti-Pattern 4: Deleting the `caddy_data` Volume

**What people do:** Run `docker compose down -v` to "clean up" before redeploying.

**Why it's wrong:** The `caddy_data` volume stores Let's Encrypt TLS certificates. Let's Encrypt rate-limits issuance to 5 certs per domain per week. Losing the volume and immediately reprovisioning will hit the rate limit quickly.

**Do this instead:** Use `docker compose down` (without `-v`) for all deployments. Document explicitly: `down -v` only for intentional full reprovisioning from scratch.

### Anti-Pattern 5: Storing OAuth Client Secret in VITE_ Variables

**What people do:** Accidentally put `VITE_GOOGLE_OAUTH_CLIENT_SECRET=...` in a GitHub Actions build arg.

**Why it's wrong:** Anything prefixed `VITE_` is embedded in the JavaScript bundle and is visible to anyone who visits the site. There is no runtime access control on it.

**Do this instead:** Only public-safe values in `VITE_`: Sentry DSN (public key only, safe by design), analytics tracking domain, feature flags. `GOOGLE_OAUTH_CLIENT_SECRET` lives only in the backend `.env` file, never near the frontend build. The existing architecture already handles OAuth server-side via FastAPI-Users — no change needed.

---

## Build Order for This Milestone

Dependencies between components:

```
1. FlawChess rename (code + branding)
   └─ Foundation: all subsequent work uses the new name

2. Docker + Caddy + PostgreSQL stack
   └─ Proves the deployment end-to-end; required before:
      - OAuth redirect URLs (need production domain)
      - Sentry (needs production environment)
      - CI/CD (needs images to build and deploy)

3. Backend config hardening (CORS from env, SENTRY_DSN field)
   └─ Required for: correct production behavior

4. Sentry integration (both SDKs)
   └─ Depends on: working deployment URL for Sentry project config

5. Analytics + SEO + About page
   └─ Depends on: live production domain

6. CI/CD automation (GitHub Actions)
   └─ Depends on: Docker images buildable, VPS accessible, secrets configured

7. Import queue (concurrent rate-limit safety)
   └─ Independent of infra — can be done at any point
```

Recommended phase grouping:
- **Phase A:** Rename + Docker + Caddy + PostgreSQL (infra foundation)
- **Phase B:** Backend hardening + Sentry backend + CI/CD
- **Phase C:** Frontend Sentry + analytics + SEO + About page + privacy/cookie
- **Phase D:** Import queue

---

## Sources

- [Caddy Caddyfile Patterns — Official Docs](https://caddyserver.com/docs/caddyfile/patterns) — `try_files` + `handle` blocks for SPA + API — HIGH confidence
- [Serving SPAs and API With Caddy v2](https://haykot.dev/blog/serving-spas-and-api-with-caddy-v2/) — exact `handle @proxied` + `try_files` pattern — HIGH confidence
- [uv Docker Integration — Official Docs](https://docs.astral.sh/uv/guides/integration/docker/) — multi-stage Dockerfile, `UV_COMPILE_BYTECODE`, `.venv` copy pattern — HIGH confidence
- [FastAPI Sentry Integration — Official Docs](https://docs.sentry.io/platforms/python/integrations/fastapi/) — auto-detection, `sentry_sdk.init()` placement — HIGH confidence
- [Sentry React + Vite Docs](https://docs.sentry.io/platforms/javascript/guides/react/) — `@sentry/react`, `@sentry/vite-plugin`, `browserTracingIntegration()` — HIGH confidence
- [Docker Compose Healthchecks — Official Docs](https://docs.docker.com/compose/how-tos/startup-order/) — `service_healthy` condition for PostgreSQL readiness — HIGH confidence
- [Vite env variables — Official Docs](https://vite.dev/guide/env-and-mode) — `VITE_` prefix baked at build time, not runtime — HIGH confidence
- [Plausible vs Umami 2025](https://vemetric.com/blog/plausible-vs-umami) — Umami Docker self-hosting viable; Plausible CE is heavier (Elixir + ClickHouse) — MEDIUM confidence
- [CI/CD to Hetzner with GitHub Actions](https://infocusdata.com/blog/devops/ci-cd-docker-github-actions-hetzner-deployment) — SSH deploy pattern, GHCR image push — MEDIUM confidence
- Direct codebase analysis: `app/main.py`, `app/core/config.py`, `frontend/vite.config.ts`, `pyproject.toml`, `frontend/package.json` — HIGH confidence

---
*Architecture research for: Chessalytics v1.3 Production Deployment*
*Researched: 2026-03-21*
