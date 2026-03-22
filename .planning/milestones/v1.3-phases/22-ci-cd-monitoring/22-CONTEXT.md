# Phase 22: CI/CD & Monitoring - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Automate deploys via GitHub Actions (test → build on server → health check) and add Sentry error tracking for both backend (FastAPI) and frontend (React). No analytics (Phase 23), no content pages (Phase 23), no import queue (Phase 23).

</domain>

<decisions>
## Implementation Decisions

### CI/CD Pipeline Design
- Trigger: push to `main` triggers full pipeline (test → deploy)
- PR checks: run tests + linters on pull_request events targeting main (no deploy step)
- Test step: pytest (with PostgreSQL service container), ruff check, npm run lint
- No frontend tests yet — linting only for now
- Build happens on the server, not in CI — no GHCR registry needed

### Deploy Strategy
- SSH into VPS, `git pull origin main`, `docker compose up -d --build`
- Only rebuilds changed images, recreates affected containers (not full down/up)
- Post-deploy health check: curl `/api/health` endpoint, fail CI job if no response within 60s
- On deploy failure: pipeline fails visibly in GitHub Actions — no automatic rollback. Manual investigation via SSH
- Sentry DSN passed to frontend build via `docker compose build` args reading from `.env` on server — no extra CI secrets for DSN

### Sentry Integration
- Single Sentry project for FlawChess (one DSN for both backend and frontend)
- Backend: sentry-sdk with FastAPI integration, captures unhandled exceptions with request context
- Backend: performance traces enabled at low sample rate (e.g., 10%) for request latency visibility
- Frontend: @sentry/react SDK with Sentry.ErrorBoundary wrapping app
- Frontend: ErrorBoundary shows "Something went wrong" fallback UI with reload button on crash
- Frontend DSN: VITE_SENTRY_DSN env var baked into JS bundle at build time (standard Vite pattern)
- Environment tagging: distinguish production vs development errors in Sentry

### Secret Management in CI
- Dedicated SSH key pair for CI deploys (not personal key) — public key in deploy@server authorized_keys, private key as GitHub Actions secret `SSH_PRIVATE_KEY`
- Server host and SSH user stored as GitHub Secrets: `SSH_HOST`, `SSH_USER`
- Production `.env` stays on server only — CI never touches app secrets (DB password, auth secrets, etc.)
- Only CI secrets needed: `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`

### Claude's Discretion
- GitHub Actions workflow YAML structure and job naming
- Sentry SDK initialization details (traces_sample_rate value, ignored errors list)
- ErrorBoundary fallback UI design
- SSH known_hosts handling in CI (ssh-keyscan or strict host checking)
- Health check retry logic (poll interval, timeout)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — DEPLOY-07 (CI/CD pipeline), MON-01 (backend Sentry), MON-02 (frontend Sentry)

### Existing deployment infrastructure
- `docker-compose.yml` — Production Compose with backend, db, caddy services
- `Dockerfile` — Backend multi-stage build (python:3.13-slim + uv)
- `frontend/Dockerfile` — Frontend multi-stage build (Node → Caddy)
- `deploy/entrypoint.sh` — Backend entrypoint running Alembic migrations before Uvicorn
- `deploy/Caddyfile` — Caddy config serving frontend + reverse-proxying /api/*
- `deploy/cloud-init.yml` — Server provisioning (Docker, UFW, fail2ban, deploy user)

### Backend configuration
- `app/core/config.py` — Pydantic BaseSettings (add SENTRY_DSN, ENVIRONMENT here)
- `app/main.py` — FastAPI app setup (Sentry SDK init goes here)
- `pyproject.toml` — Python dependencies (add sentry-sdk here)

### Frontend configuration
- `frontend/vite.config.ts` — Vite config (VITE_SENTRY_DSN env var access)
- `frontend/package.json` — Node dependencies (add @sentry/react here)
- `frontend/src/main.tsx` — App entry point (Sentry.init goes here)

### Prior phase context
- `.planning/phases/21-docker-deployment/21-CONTEXT.md` — Docker architecture decisions, server setup, secrets approach

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/core/config.py` — Pydantic BaseSettings already reads from .env; add SENTRY_DSN and ENVIRONMENT fields
- `/api/health` endpoint already exists in `app/main.py` — deploy health check can target this
- `deploy/entrypoint.sh` — existing entrypoint pattern for backend container startup
- `.env.example` — template for environment variables, needs SENTRY_DSN and VITE_SENTRY_DSN added

### Established Patterns
- Backend uses uv for dependency management (pyproject.toml + uv.lock)
- Frontend uses npm (package.json + package-lock.json)
- Docker Compose builds on server with `docker compose up -d --build`
- All config via environment variables / .env file (Pydantic BaseSettings)

### Integration Points
- `app/main.py` — Sentry SDK init before FastAPI app creation
- `frontend/src/main.tsx` — Sentry.init before React render
- `frontend/src/App.tsx` — Sentry.ErrorBoundary wrapping main app content
- `.github/workflows/` — new directory for CI/CD workflow YAML
- `docker-compose.yml` — may need build args for VITE_SENTRY_DSN passthrough
- `.env.example` — document new SENTRY_DSN and VITE_SENTRY_DSN variables

</code_context>

<specifics>
## Specific Ideas

- Build on server (git pull + docker compose build) matches the existing manual deploy flow from Phase 21
- Single Sentry project keeps things simple for a solo developer — backend/frontend errors distinguished by platform tag
- Performance traces included from the start to get request latency visibility in Sentry without needing a separate APM tool

</specifics>

<deferred>
## Deferred Ideas

- Sentry session replay (error-only mode) — tracked as MON-04 in v1.x requirements
- Structured JSON logging with Sentry trace ID correlation — tracked as MON-05 in v1.x requirements
- GHCR-based image builds — revisit if server build times become a bottleneck
- Automatic rollback on failed deploy — revisit if deploy failures become frequent
- Branch protection rules — can add later to enforce PR workflow

</deferred>

---

*Phase: 22-ci-cd-monitoring*
*Context gathered: 2026-03-21*
