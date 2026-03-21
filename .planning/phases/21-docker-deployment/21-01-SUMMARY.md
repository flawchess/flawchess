---
phase: 21-docker-deployment
plan: 01
subsystem: infra
tags: [docker, caddy, postgres, uvicorn, alembic, uv, nginx-alternative]

# Dependency graph
requires: []
provides:
  - "Backend multi-stage Dockerfile with uv and pinned Python 3.13"
  - "Frontend Dockerfile with Node 24 build stage and Caddy 2.11.2 serve stage"
  - "docker-compose.yml orchestrating db/backend/caddy with healthcheck ordering"
  - "Caddyfile proxying 8 API route prefixes + SPA fallback"
  - "deploy/entrypoint.sh running alembic migrations before uvicorn"
  - "Conditional CORS (development only) — production uses same-origin via Caddy"
  - ".env.example documenting all production variables"
affects: [22-ci-cd-monitoring, 23-launch-readiness]

# Tech tracking
tech-stack:
  added: [caddy:2.11.2, postgres:16-alpine, node:24-alpine, ghcr.io/astral-sh/uv:0.10.9]
  patterns:
    - "uv multi-stage Docker build: deps layer (bind mount) then source layer"
    - "Backend expose-only (no ports) — only Caddy is internet-facing"
    - "Service-healthy healthcheck gate: backend waits for db to be ready"
    - "entrypoint.sh pattern: migrate-then-exec for zero-downtime migration"

key-files:
  created:
    - Dockerfile
    - frontend/Dockerfile
    - docker-compose.yml
    - deploy/Caddyfile
    - deploy/entrypoint.sh
    - .dockerignore
    - frontend/.dockerignore
  modified:
    - .env.example
    - app/main.py

key-decisions:
  - "Backend has expose: not ports: — internal only, Caddy is sole entry point"
  - "Caddy build context is project root with dockerfile: frontend/Dockerfile so COPY deploy/ paths work"
  - "443:443/udp added to caddy ports for HTTP/3 support"
  - "CORS disabled in production — Caddy routes frontend and API on same origin"

patterns-established:
  - "API routes proxied individually (no /api/ prefix) matching vite.config.ts proxy config"
  - "docker-compose $$ syntax for shell variable interpolation in healthcheck test string"

requirements-completed: [DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05]

# Metrics
duration: 2min
completed: 2026-03-21
---

# Phase 21 Plan 01: Docker Infrastructure Summary

**Complete Docker Compose stack with uv multi-stage backend, Caddy 2.11.2 frontend/proxy, Postgres healthcheck ordering, and conditional CORS for development vs production**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T17:42:46Z
- **Completed:** 2026-03-21T17:44:58Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Backend Dockerfile using ghcr.io/astral-sh/uv:0.10.9 for cached dependency install then project copy (two-stage uv pattern)
- docker-compose.yml with healthcheck-gated startup: db must be healthy before backend starts; alembic runs before uvicorn accepts traffic
- Caddyfile proxies all 8 API route prefixes individually (matching vite.config.ts proxy configuration), then catches everything else for SPA index.html fallback

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Dockerfiles, entrypoint, and .dockerignore files** - `8d024cd` (feat)
2. **Task 2: Create docker-compose.yml and Caddyfile** - `27043b4` (feat)
3. **Task 3: Update .env.example and make CORS conditional on ENVIRONMENT** - `bee47e3` (feat)

## Files Created/Modified

- `Dockerfile` - Backend multi-stage build: uv deps layer (cacheable) + project source layer, runtime on python:3.13-slim
- `frontend/Dockerfile` - Node 24 Alpine build stage compiles SPA, Caddy 2.11.2 runtime serves /srv
- `docker-compose.yml` - 3-service orchestration with postgres:16-alpine healthcheck, backend expose-only, caddy on 80/443/443-udp
- `deploy/Caddyfile` - Reverse proxy: 8 API prefixes to backend:8000, SPA catch-all with index.html fallback
- `deploy/entrypoint.sh` - `set -e; alembic upgrade head; exec uvicorn ...` startup sequence
- `.dockerignore` - Excludes .venv, .git, frontend/node_modules, .planning, .claude, dev artifacts from build context
- `frontend/.dockerignore` - Excludes node_modules, dist, .env from frontend context
- `.env.example` - Documents all production variables including POSTGRES_USER/PASSWORD/DB and DATABASE_URL pointing to db:5432
- `app/main.py` - CORS middleware now conditional: only active when ENVIRONMENT=development

## Decisions Made

- Backend uses `expose:` not `ports:` — the backend is internal-only, Caddy is the sole internet-facing entry point. This is correct for security: no direct backend access from host.
- Caddy build context is project root (`.`) with `dockerfile: frontend/Dockerfile` so the `COPY deploy/Caddyfile` instruction inside the Dockerfile can reach the deploy/ directory.
- HTTP/3 enabled via `443:443/udp` — Caddy handles QUIC natively, no extra config needed.
- CORS disabled in production: Caddy routes `/auth/*`, `/analysis/*` etc. to the backend and everything else to the SPA, so frontend and API share the same origin (`flawchess.com`). CORS would be redundant and slightly reduces security surface.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The VPS provisioning (cloud-init.yml) was already created in phase context research.

## Next Phase Readiness

- All Docker infrastructure files are ready for `docker compose build` and `docker compose up` on the Hetzner VPS
- Phase 22 (CI/CD) can now reference these files for GitHub Actions workflows
- Phase 23 (Launch Readiness) can deploy using these files once the VPS is provisioned

---
*Phase: 21-docker-deployment*
*Completed: 2026-03-21*

## Self-Check: PASSED

- All 8 files created/modified confirmed present on disk
- All 3 task commits confirmed in git log (8d024cd, 27043b4, bee47e3)
