# Phase 21: Docker & Deployment - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Containerize FlawChess (FastAPI backend + React frontend + PostgreSQL) with Docker Compose, deploy to a Hetzner cloud server with Caddy auto-TLS, ensure persistent data and automatic migrations on startup. No CI/CD automation (Phase 22), no monitoring (Phase 22), no analytics/content pages (Phase 23).

</domain>

<decisions>
## Implementation Decisions

### Hosting Platform
- Hetzner Cloud server, CPX22 (2 vCPU, 4GB RAM, 80GB disk, ~€5.99/mo)
- Regular performance (shared vCPU) — sufficient for I/O-bound web app workload
- Can resize within CX/CPX line if needed (CPX32 at €10.49/mo next step up)
- Ubuntu 24.04 LTS as the server OS

### Docker Architecture
- Multi-stage Dockerfile for frontend: Node build stage outputs static files to a shared volume, Caddy serves them at runtime — no separate frontend container running
- Backend Dockerfile: `python:3.13-slim` base image with uv installed in build stage, copy lockfile, install deps. Small image (~150MB)
- Single Uvicorn worker (async) — FastAPI handles concurrency via async I/O, no Gunicorn needed at this scale
- Frontend build happens inside Docker (multi-stage) for reproducible builds and CI/CD readiness

### Compose & Networking
- Caddyfile configuration (not JSON or Docker labels) — simple, readable, ~15 lines
- Caddy serves static frontend files at root, reverse-proxies `/api/*` to backend container
- Caddy handles auto-TLS via Let's Encrypt — just set the domain name
- CORS middleware removed in production (same-origin via Caddy) — keep only for `ENVIRONMENT=development`
- Named Docker volumes for PostgreSQL data and Caddy TLS state (not bind mounts)
- Alembic migrations run automatically via backend container entrypoint script (`alembic upgrade head` before Uvicorn starts). If migration fails, container fails to start.

### Server Provisioning
- Cloud-init YAML script checked into repo at `deploy/cloud-init.yml` — already created by user
- Cloud-init installs Docker, configures UFW (ports 22/80/443 only), enables fail2ban, creates deploy user, hardens SSH (key-only, no root)
- Unattended-upgrades enabled for automatic security patches
- Cloud-init to be simplified: remove bind-mount directory creation (pgdata, caddy_data, caddy_config) since we're using named Docker volumes. Keep /opt/flawchess for docker-compose.yml and .env
- Fix .env template heredoc whitespace (leading spaces from YAML indentation)
- Consider adding `reboot: true` at end of cloud-init for kernel updates

### DNS & TLS
- A record at domain registrar pointing flawchess.com to Hetzner VPS IP (manual step, documented)
- Caddy auto-TLS handles Let's Encrypt certificate provisioning and renewal automatically

### Secrets Management
- `.env` file manually SCP'd to server during initial setup — secrets never touch git or CI
- Required variables documented in `.env.example` in the repo
- Production .env lives at `/opt/flawchess/.env` on the server

### Claude's Discretion
- Exact Caddyfile syntax and routing rules
- Docker Compose service names and network configuration
- Entrypoint script implementation details
- Container health check configuration
- Whether to add `reboot: true` to cloud-init or leave it out

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Deployment requirements
- `.planning/REQUIREMENTS.md` — DEPLOY-01 through DEPLOY-06 define containerization and deployment scope

### Existing deployment assets
- `deploy/cloud-init.yml` — User-created cloud-init script for Hetzner VPS provisioning (needs minor updates: remove bind-mount dirs, fix heredoc whitespace)

### Backend configuration
- `app/core/config.py` — Pydantic BaseSettings reading from .env (DATABASE_URL, SECRET_KEY, BACKEND_URL, FRONTEND_URL, ENVIRONMENT, Google OAuth)
- `app/main.py` — FastAPI app with CORS middleware (needs production conditional), health endpoint at `/health`
- `alembic.ini` — Alembic migration configuration
- `pyproject.toml` — Python dependencies and project metadata
- `.env.example` — Environment variable template

### Frontend build
- `frontend/vite.config.ts` — Vite + PWA plugin config (build output goes to dist/)
- `frontend/package.json` — Node dependencies and build scripts

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy/cloud-init.yml` — Server provisioning already scripted, needs minor cleanup
- `app/core/config.py` — Pydantic BaseSettings already reads all config from environment/`.env`
- `/health` endpoint already exists in `app/main.py` — satisfies success criteria 3

### Established Patterns
- Backend uses `uv` for dependency management (pyproject.toml + uv.lock)
- Frontend uses npm (package.json + package-lock.json)
- CORS middleware in `app/main.py` currently hardcoded to localhost:5173 — needs environment-conditional logic

### Integration Points
- `app/main.py` CORS middleware — must be conditional on ENVIRONMENT setting
- `.env.example` — needs to document all production-required variables
- `alembic/` — migrations directory, entrypoint script must run `alembic upgrade head`
- Frontend `dist/` output — Caddy needs to serve this directory

</code_context>

<specifics>
## Specific Ideas

- User has hands-on Hetzner experience (deployed Superset instance) — comfortable with VPS management
- Cloud-init approach preferred over manual setup for reproducibility
- Server is a "dumb Docker host" — all app logic in containers, server just needs Docker + SSH + firewall
- User already created cloud-init.yml — plan should build on it, not recreate

</specifics>

<deferred>
## Deferred Ideas

- CI/CD pipeline (GitHub Actions: test → build → push → SSH deploy) — Phase 22
- Sentry error monitoring — Phase 22
- Cloudflare DNS/CDN proxy — not needed at launch, revisit if DDoS becomes a concern
- Hetzner Cloud Firewall (layered on top of UFW) — can add later for defense-in-depth
- Gunicorn multi-worker setup — revisit if CPU becomes bottleneck under load

</deferred>

---

*Phase: 21-docker-deployment*
*Context gathered: 2026-03-21*
