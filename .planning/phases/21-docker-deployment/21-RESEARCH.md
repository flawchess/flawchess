# Phase 21: Docker & Deployment - Research

**Researched:** 2026-03-21
**Domain:** Docker Compose, Caddy reverse proxy, uv multi-stage builds, VPS deployment
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Hosting Platform**
- Hetzner Cloud server, CPX22 (2 vCPU, 4GB RAM, 80GB disk, ~€5.99/mo)
- Regular performance (shared vCPU) — sufficient for I/O-bound web app workload
- Can resize within CX/CPX line if needed (CPX32 at €10.49/mo next step up)
- Ubuntu 24.04 LTS as the server OS

**Docker Architecture**
- Multi-stage Dockerfile for frontend: Node build stage outputs static files to a shared volume, Caddy serves them at runtime — no separate frontend container running
- Backend Dockerfile: `python:3.13-slim` base image with uv installed in build stage, copy lockfile, install deps. Small image (~150MB)
- Single Uvicorn worker (async) — FastAPI handles concurrency via async I/O, no Gunicorn needed at this scale
- Frontend build happens inside Docker (multi-stage) for reproducible builds and CI/CD readiness

**Compose & Networking**
- Caddyfile configuration (not JSON or Docker labels) — simple, readable, ~15 lines
- Caddy serves static frontend files at root, reverse-proxies `/api/*` to backend container
- Caddy handles auto-TLS via Let's Encrypt — just set the domain name
- CORS middleware removed in production (same-origin via Caddy) — keep only for `ENVIRONMENT=development`
- Named Docker volumes for PostgreSQL data and Caddy TLS state (not bind mounts)
- Alembic migrations run automatically via backend container entrypoint script (`alembic upgrade head` before Uvicorn starts). If migration fails, container fails to start.

**Server Provisioning**
- Cloud-init YAML script checked into repo at `deploy/cloud-init.yml` — already created by user
- Cloud-init installs Docker, configures UFW (ports 22/80/443 only), enables fail2ban, creates deploy user, hardens SSH (key-only, no root)
- Unattended-upgrades enabled for automatic security patches
- Cloud-init to be simplified: remove bind-mount directory creation (pgdata, caddy_data, caddy_config) since we're using named Docker volumes. Keep /opt/flawchess for docker-compose.yml and .env
- Fix .env template heredoc whitespace (leading spaces from YAML indentation)
- Consider adding `reboot: true` at end of cloud-init for kernel updates

**DNS & TLS**
- A record at domain registrar pointing flawchess.com to Hetzner VPS IP (manual step, documented)
- Caddy auto-TLS handles Let's Encrypt certificate provisioning and renewal automatically

**Secrets Management**
- `.env` file manually SCP'd to server during initial setup — secrets never touch git or CI
- Required variables documented in `.env.example` in the repo
- Production .env lives at `/opt/flawchess/.env` on the server

### Claude's Discretion
- Exact Caddyfile syntax and routing rules
- Docker Compose service names and network configuration
- Entrypoint script implementation details
- Container health check configuration
- Whether to add `reboot: true` to cloud-init or leave it out

### Deferred Ideas (OUT OF SCOPE)
- CI/CD pipeline (GitHub Actions: test → build → push → SSH deploy) — Phase 22
- Sentry error monitoring — Phase 22
- Cloudflare DNS/CDN proxy — not needed at launch, revisit if DDoS becomes a concern
- Hetzner Cloud Firewall (layered on top of UFW) — can add later for defense-in-depth
- Gunicorn multi-worker setup — revisit if CPU becomes bottleneck under load
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEPLOY-01 | Multi-stage Dockerfiles for backend (Python/uv) and frontend (Node build → Caddy) | uv official Docker guide; multi-stage with `ghcr.io/astral-sh/uv:0.10.9` binary copy; Node 24 → Caddy 2.11.2 pattern |
| DEPLOY-02 | Docker Compose orchestrating FastAPI, PostgreSQL, and Caddy services with named volumes | Compose `depends_on: condition: service_healthy`; `pg_isready` healthcheck; named volumes `pgdata`, `caddy_data`, `caddy_config` |
| DEPLOY-03 | Caddy reverse proxy serving frontend static files and proxying /api to backend with auto-TLS | Caddyfile `handle /api/*` + `handle` block with `root /srv`, `try_files`, `file_server`; ports 80+443 open via UFW |
| DEPLOY-04 | Alembic migrations run automatically on container startup before accepting traffic | Entrypoint script `alembic upgrade head && exec uvicorn ...`; DB healthcheck ensures postgres is ready before backend starts |
| DEPLOY-05 | Environment variable configuration via .env file with Pydantic BaseSettings (no hardcoded secrets) | `.env` already gitignored; Pydantic BaseSettings already reads from `.env`; `.env.example` needs production vars added; CORS needs `ENVIRONMENT` conditional |
| DEPLOY-06 | Application deployed and accessible at flawchess.com | Hetzner CPX22 + cloud-init + DNS A record + Caddy auto-TLS |
</phase_requirements>

---

## Summary

Phase 21 containerizes a FastAPI + React/Vite + PostgreSQL application for production on a Hetzner VPS. The architecture is straightforward: three services in Docker Compose (backend, db, caddy), with Caddy acting as the single entry point — serving static frontend files and proxying `/api/*` requests to the FastAPI backend. No orchestration overhead, no separate frontend runtime container.

The key architectural decision (already locked) is using multi-stage Docker builds: a Node build stage produces the `dist/` directory, which Caddy serves from `/srv`. The backend uses a two-stage build — a builder stage with `python:3.13-slim` + uv for dependency installation, and a slim runtime stage copying only the `.venv`. Alembic migrations run at container startup before Uvicorn accepts traffic, with the backend depending on a healthy PostgreSQL healthcheck.

The main implementation work is: writing the Dockerfiles and `docker-compose.yml`, writing the Caddyfile (~15 lines), writing an entrypoint shell script, conditionalizing CORS in `app/main.py`, expanding `.env.example` with all production vars, and updating `deploy/cloud-init.yml` (minor cleanup). The server provisioning script already exists — it just needs the bind-mount directory creation removed and heredoc whitespace fixed.

**Primary recommendation:** Build services in this order — db → backend → caddy — writing healthchecks and dependency ordering first so the entrypoint script never races postgres.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python:3.13-slim` | 3.13 | Backend base image | Matches project Python version; slim removes build tools |
| `ghcr.io/astral-sh/uv` | 0.10.9 | Copy uv binary into builder stage | Official uv Docker pattern; avoids installing uv via pip |
| `node` | 24-alpine | Frontend build stage base | LTS line; alpine minimizes image size for build-only stage |
| `caddy` | 2.11.2 | Static file server + reverse proxy + auto-TLS | One binary replaces nginx + certbot; auto-TLS with Let's Encrypt |
| `postgres` | 16-alpine | Database | Alpine variant for smaller image; stable major version |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `uvicorn` | 0.41.0 (locked) | ASGI server (already in pyproject.toml) | Single worker, async FastAPI — no Gunicorn wrapper needed |
| Docker Compose plugin | v2 (bundled with Docker CE) | Orchestration | Ships with Docker CE on Ubuntu 24.04 via cloud-init |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Caddy auto-TLS | nginx + certbot | Certbot requires cron setup, renewal scripts; Caddy handles all of it automatically |
| Named volumes | Bind mounts | Named volumes are Docker-managed, survive `docker compose down -v` accidents less likely; no permission issues on host |
| Single Uvicorn worker | Gunicorn + Uvicorn | Gunicorn adds complexity; async I/O handles concurrency without multiple workers at this scale |

**Installation (cloud-init already handles server-side Docker install):**
```bash
# Verified versions from Docker Hub and local uv version
# Backend: python:3.13-slim (latest 3.13)
# uv binary: ghcr.io/astral-sh/uv:0.10.9
# Frontend build: node:24-alpine
# Caddy: caddy:2.11.2
# DB: postgres:16-alpine
```

---

## Architecture Patterns

### Recommended Project Structure
```
/                          # project root
├── Dockerfile             # backend multi-stage (builder + runtime)
├── frontend/
│   └── Dockerfile         # frontend multi-stage (node build → caddy serve)
├── deploy/
│   ├── cloud-init.yml     # Hetzner VPS provisioning (exists, needs minor fixes)
│   ├── Caddyfile          # ~15-line Caddy config
│   └── entrypoint.sh      # migration + uvicorn start script
├── docker-compose.yml     # 3 services: backend, db, caddy
├── .env.example           # all production vars documented, no values
└── .env                   # gitignored, SCP'd to server
```

### Pattern 1: Backend Multi-Stage Dockerfile (uv)

**What:** Two stages — `builder` installs deps into `.venv` using uv, `runtime` copies only the `.venv` and app code.

**When to use:** Always — this is the canonical uv Docker pattern.

```dockerfile
# Source: https://docs.astral.sh/uv/guides/integration/docker/
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

WORKDIR /app

# Install dependencies (cacheable — changes rarely)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

# Copy source and install project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.13-slim AS runtime
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

### Pattern 2: Frontend Multi-Stage Dockerfile (Node → Caddy)

**What:** Node stage builds `dist/`, Caddy stage serves it. No Node runtime in final image.

**When to use:** Vite/React SPA with Caddy serving static files.

```dockerfile
# Source: Caddy community + Docker multi-stage pattern
FROM node:24-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM caddy:2.11.2 AS runtime
COPY --from=builder /app/dist /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
```

### Pattern 3: Caddyfile — SPA + API Proxy

**What:** Route `/api/*` to backend container, serve SPA at root with `try_files` fallback.

**When to use:** Single domain, Caddy handles TLS automatically when real domain is set.

```caddy
# Source: https://caddyserver.com/docs/caddyfile/patterns
flawchess.com {
    encode gzip

    handle /api/* {
        reverse_proxy backend:8000
    }

    handle /health {
        reverse_proxy backend:8000
    }

    handle {
        root * /srv
        try_files {path} /index.html
        file_server
    }
}
```

**Note:** `{path}` is the Caddy placeholder syntax (not a shell variable). The `handle` blocks are evaluated in order — first match wins. `health` endpoint must also proxy to backend (it's part of the API, not a frontend route).

### Pattern 4: Entrypoint Script (Migrations + Start)

**What:** Shell script runs `alembic upgrade head`, exits with error code if migrations fail (container won't start), then `exec` hands off to uvicorn (PID 1 replacement).

```bash
#!/bin/sh
# Source: common Docker entrypoint pattern for DB migration on startup
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Critical:** `exec` replaces the shell with uvicorn — signals (SIGTERM) go directly to uvicorn, not the shell. Without `exec`, `docker stop` would kill the shell and orphan uvicorn.

### Pattern 5: Docker Compose Service Order

**What:** Backend must wait for PostgreSQL to be ready (not just started — actually accepting connections).

```yaml
# Source: https://docs.docker.com/compose/how-tos/startup-order/
services:
  db:
    image: postgres:16-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  backend:
    depends_on:
      db:
        condition: service_healthy
```

**Critical:** `depends_on: condition: service_healthy` only works when the dependency defines a `healthcheck`. Without it, the backend starts immediately and Alembic migrations fail with "could not connect to server."

### Pattern 6: CORS Conditional on ENVIRONMENT

**What:** In production, Caddy routes frontend and backend under the same origin — no cross-origin requests. CORS middleware only needed in development (Vite dev server on port 5173).

```python
# app/main.py — change from hardcoded to conditional
from app.core.config import settings

if settings.ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

### Anti-Patterns to Avoid

- **`depends_on` without healthcheck condition:** Docker Compose by default only waits for the container to start, not for the service to be ready. Always use `condition: service_healthy` for database dependencies.
- **`CMD` instead of `exec` in entrypoint:** Without `exec`, signals are not forwarded to the application process. Use `exec uvicorn ...` not `uvicorn ...`.
- **Bind-mounting `.env` into containers:** Pass env vars via `env_file: .env` in Compose, not volume mounts. The `env_file` directive reads vars into the container environment cleanly.
- **`caddy:latest` in production:** Pin to `caddy:2.11.2` for reproducible deployments.
- **Serving `index.html` without Cache-Control:** Browsers may cache the entrypoint and miss Vite content-hashed asset updates. Add `header /index.html Cache-Control "no-cache"` to the Caddyfile.
- **Not persisting Caddy's `/data` volume:** Without a named volume for `/data`, Caddy re-requests certificates on every restart and may hit Let's Encrypt rate limits (50 certs/domain/week).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TLS certificate provisioning + renewal | Custom certbot cron job | Caddy auto-TLS | Caddy handles ACME challenge, renewal, and rate-limit throttling automatically |
| "Wait for DB" logic in entrypoint | Shell `nc -z` polling loops | Compose `depends_on: condition: service_healthy` + `pg_isready` | pg_isready is reliable; healthcheck handles start_period grace period |
| Static file serving with SPA routing | Custom nginx config | Caddy `try_files {path} /index.html` | One directive handles the common SPA 404 → index.html pattern |
| Multi-arch build complexity | Manual QEMU setup | Docker Buildx (if needed in Phase 22) | Not needed for Phase 21 — build on the server's native arch |

**Key insight:** Caddy's auto-TLS is the single biggest value-add here. What historically required certbot install, cron jobs, renewal scripts, and nginx config is reduced to one line: `flawchess.com {`.

---

## Common Pitfalls

### Pitfall 1: Let's Encrypt Rate Limits During Testing
**What goes wrong:** If you provision the server, configure Caddy, then tear it down and reprovision multiple times, you may hit Let's Encrypt's limit of 5 failed validations per domain per hour.
**Why it happens:** Each Caddy startup with a real domain triggers a certificate request if no cached cert exists.
**How to avoid:** Use Caddy's ACME staging server during testing: add `tls { ca https://acme-staging-v02.api.letsencrypt.org/directory }` block while iterating. Remove it for final deployment.
**Warning signs:** Caddy logs show "too many certificates already issued" errors.

### Pitfall 2: Alembic Can't Connect to DB — Wrong URL Format
**What goes wrong:** `alembic upgrade head` fails with asyncpg driver error when run synchronously.
**Why it happens:** `alembic.env.py` uses `async_engine_from_config` with `asyncpg` — this already works correctly in this project. The risk is the `DATABASE_URL` uses `@db:5432` (Docker Compose service name), not `@localhost:5432`.
**How to avoid:** Ensure the production `.env` uses `DATABASE_URL=postgresql+asyncpg://flawchess:PASSWORD@db:5432/flawchess` — the cloud-init template already has this correct.
**Warning signs:** "connection refused" during migration step in container logs.

### Pitfall 3: Frontend Build Stage Missing `VITE_*` Environment Variables
**What goes wrong:** Frontend builds with placeholder or undefined API URLs baked in.
**Why it happens:** Vite inlines `VITE_*` variables at build time. But this project uses Caddy same-origin routing — no `VITE_API_URL` variable is needed. Vite proxies `/api/*` in dev; Caddy routes in production. No env vars needed for the frontend build.
**How to avoid:** Confirm there are no `import.meta.env.VITE_*` references that would need production values. Current codebase uses relative API paths (`/api/...`), so this is not an issue.
**Warning signs:** API calls in production go to `undefined/api/...`.

### Pitfall 4: Caddy Can't Reach Backend — Wrong Docker Network
**What goes wrong:** Caddy's `reverse_proxy backend:8000` returns 502 Bad Gateway.
**Why it happens:** Services must be on the same Docker network to resolve each other by name.
**How to avoid:** Define a shared custom network in `docker-compose.yml` and attach all services to it. Or rely on Compose's default network (all services in the same Compose file share a default network automatically — this is safe to rely on).
**Warning signs:** Caddy logs show "dial tcp: lookup backend: no such host".

### Pitfall 5: cloud-init Heredoc Whitespace
**What goes wrong:** The `.env` file written by cloud-init has leading spaces on every line.
**Why it happens:** YAML block scalars preserve indentation. The existing cloud-init.yml uses `content: |` with indented content, so those spaces become part of the file content.
**How to avoid:** Check the existing cloud-init.yml's `write_files` section — the content already uses `content: |` with correct left-alignment (lines start at column 0 within the block scalar). If spaces appear, fix by dedenting the heredoc content in the YAML.
**Warning signs:** PostgreSQL fails to start because password has leading spaces; Pydantic validation errors for malformed `DATABASE_URL`.

### Pitfall 6: Port 8000 Exposed to Public
**What goes wrong:** FastAPI backend accessible directly at `http://server-ip:8000`, bypassing Caddy's TLS and routing.
**Why it happens:** `ports: "8000:8000"` in docker-compose.yml exposes the port to the host and thus the internet.
**How to avoid:** Do NOT add `ports` to the backend service. Use `expose: ["8000"]` (container-internal only) or nothing — Caddy reaches the backend via Docker's internal network. UFW blocks external access to 8000 anyway, but defence-in-depth means not binding it.

---

## Code Examples

Verified patterns from official sources:

### Docker Compose Named Volumes + healthcheck
```yaml
# Source: https://docs.docker.com/compose/how-tos/startup-order/
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  backend:
    build: .
    env_file: .env
    expose:
      - "8000"
    depends_on:
      db:
        condition: service_healthy

  caddy:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"   # HTTP/3
    volumes:
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend

volumes:
  pgdata:
  caddy_data:
  caddy_config:
```

### Complete Caddyfile (SPA + API)
```caddy
# Source: https://caddyserver.com/docs/caddyfile/patterns
flawchess.com {
    encode gzip

    handle /api/* {
        reverse_proxy backend:8000
    }

    handle /health {
        reverse_proxy backend:8000
    }

    handle {
        root * /srv
        header /index.html Cache-Control "no-cache"
        try_files {path} /index.html
        file_server
    }
}
```

### CORS Conditional (app/main.py)
```python
# Only enable CORS in development — Caddy provides same-origin in production
if settings.ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| nginx + certbot + cron | Caddy auto-TLS | Caddy v2 (2020+) | TLS setup is zero-config once domain is set |
| `wait-for-it.sh` scripts | `depends_on: condition: service_healthy` + pg_isready | Docker Compose v2 (2021+) | No extra scripts; built into Compose |
| `pip install` in Dockerfile | uv sync --locked with cache mount | uv 0.1+ (2024) | 10-100x faster installs; lockfile-pinned |
| `docker-compose` (v1, Python) | `docker compose` (v2, Go plugin) | Docker CLI plugin 2022 | `docker-compose` deprecated; use `docker compose` |

**Deprecated/outdated:**
- `docker-compose` command: replaced by `docker compose` (v2 plugin). Cloud-init installs `docker-compose-plugin` — correct.
- `CMD ["python", "-m", "uvicorn"]` without exec: replaced by `ENTRYPOINT ["sh", "-c", "exec uvicorn ..."]` or an entrypoint script with `exec`.

---

## Open Questions

1. **Caddy Dockerfile placement**
   - What we know: frontend Dockerfile does the Node build + Caddy serve in one multi-stage build. The Caddyfile needs to be in the Docker build context.
   - What's unclear: whether to put the Caddyfile in `deploy/Caddyfile` (and COPY from there) or `frontend/Caddyfile`.
   - Recommendation: `deploy/Caddyfile` — deployment config belongs in `deploy/`, not `frontend/`. The build context for `frontend/Dockerfile` needs to be set to the project root (not `frontend/`) so it can `COPY deploy/Caddyfile`.

2. **`reboot: true` in cloud-init**
   - What we know: cloud-init runs `package_upgrade: true`, which may install a new kernel. The new kernel only takes effect after reboot.
   - What's unclear: whether this is needed for security (kernel-level patches) or an unnecessary delay.
   - Recommendation: Add `reboot: true` — a one-time reboot during provisioning ensures the latest kernel is active before the server goes live. Delay is ~30 seconds; acceptable at setup time.

3. **PostgreSQL version pin**
   - What we know: using `postgres:16-alpine` is proposed. The project has no existing deployed DB to migrate from.
   - What's unclear: whether to pin to `16` or `16.x` for more reproducibility.
   - Recommendation: `postgres:16-alpine` is fine for Phase 21. Phase 22 can pin to a patch version once CI/CD is in place.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_auth.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEPLOY-01 | Docker images build without error | smoke | `docker build -f Dockerfile .` | ❌ Wave 0 (Dockerfiles) |
| DEPLOY-02 | docker compose up starts all services | smoke | `docker compose up -d && docker compose ps` | ❌ Wave 0 (docker-compose.yml) |
| DEPLOY-03 | Caddy serves static files and proxies /api | manual-only | Browser + `curl https://flawchess.com/api/health` | N/A |
| DEPLOY-04 | Migrations run on startup | manual-only | Verify in `docker compose logs backend` | N/A |
| DEPLOY-05 | No secrets in images/repo | manual-only | `docker inspect` + `git log --all` scan | N/A |
| DEPLOY-06 | App accessible at flawchess.com over HTTPS | manual-only | `curl https://flawchess.com/api/health` | N/A |

**Note:** DEPLOY-03 through DEPLOY-06 require a live server with a real domain and valid TLS — they cannot be automated in unit/integration tests. The existing test suite covers application logic; deployment verification is inherently manual for Phase 21.

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_auth.py -x` (existing auth tests verify app still starts correctly after CORS change)
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `Dockerfile` — backend multi-stage build (required for DEPLOY-01)
- [ ] `frontend/Dockerfile` — frontend build + Caddy stage (required for DEPLOY-01)
- [ ] `docker-compose.yml` — 3-service orchestration (required for DEPLOY-02)
- [ ] `deploy/Caddyfile` — routing config (required for DEPLOY-03)
- [ ] `deploy/entrypoint.sh` — migration + uvicorn start (required for DEPLOY-04)

*(No new test files needed — existing pytest suite covers application logic. Docker builds are smoke-tested manually.)*

---

## Sources

### Primary (HIGH confidence)
- `https://docs.astral.sh/uv/guides/integration/docker/` — uv Docker multi-stage pattern, `--locked`, `--no-dev`, cache mounts
- `https://caddyserver.com/docs/caddyfile/patterns` — SPA with API proxy Caddyfile pattern, `try_files`, `handle` blocks
- `https://caddyserver.com/docs/automatic-https` — Auto-TLS requirements: port 80+443 open, persistent `/data` volume, DNS A record
- `https://docs.docker.com/compose/how-tos/startup-order/` — `depends_on: condition: service_healthy`, pg_isready healthcheck
- Local codebase inspection — `app/core/config.py`, `app/main.py`, `alembic/env.py`, `deploy/cloud-init.yml`, `pyproject.toml`

### Secondary (MEDIUM confidence)
- `https://hub.docker.com/_/caddy` (via Docker Hub API) — Caddy 2.11.2 is current stable version
- `https://github.com/astral-sh/uv-docker-example` — Canonical uv Docker single-stage example; multi-stage pattern extrapolated from official docs
- WebSearch results for Caddy + Vite + Django (analogous pattern to FastAPI) — verified against official Caddy docs

### Tertiary (LOW confidence)
- Community examples for Caddy + Docker Compose static files — patterns verified against official Caddy documentation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against Docker Hub API and local installed versions
- Architecture: HIGH — patterns verified against official uv and Caddy documentation
- Pitfalls: HIGH — sourced from official Docker Compose docs + Caddy rate limit docs + direct code inspection

**Research date:** 2026-03-21
**Valid until:** 2026-06-21 (stable infra tools; Caddy/uv versions may update but patterns are stable)
