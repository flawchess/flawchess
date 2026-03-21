# Project Research Summary

**Project:** FlawChess (formerly Chessalytics) v1.3 — Project Launch
**Domain:** Production deployment, DevOps, monitoring, analytics, SEO, public launch
**Researched:** 2026-03-21
**Confidence:** HIGH

## Executive Summary

FlawChess v1.3 is a production launch milestone for an already-functional chess analysis platform. The core application (game import, Zobrist-hash position analysis, bookmarks, move explorer, PWA) was shipped in v1.0–v1.2. This milestone focuses entirely on making that application publicly launchable: containerizing and deploying it to a Hetzner VPS, adding error monitoring, analytics, SEO, and an import queue that prevents chess.com rate-limit bans at concurrent load. The recommended approach is a single-VPS Docker Compose deployment with Caddy as reverse proxy — no orchestration, no managed services, no Kubernetes — appropriate for a solo developer launching to an initial user base.

The recommended stack additions are minimal: Docker + Docker Compose, Caddy 2.11.2 (auto-TLS, SPA routing, API proxying in ~10 lines of Caddyfile), sentry-sdk 2.55.0 + @sentry/react 10.45.0 for error tracking, Plausible Cloud for GDPR-safe analytics (no cookie consent required), and react-helmet-async 3.0.0 for SEO meta tags. The frontend is served as static files from Caddy, not from a separate running container in production — this eliminates a container while simplifying TLS and routing. GitHub Actions drives CI/CD with SSH deployment to Hetzner.

The three most critical risks for this milestone are: (1) the chess.com import rate-limit problem — concurrent BackgroundTasks will trigger IP bans at 4+ simultaneous users, requiring a global asyncio.Semaphore before launch; (2) Caddy directive ordering — `try_files` silently rewrites API calls to `/index.html` unless `handle` blocks are ordered correctly; and (3) the Sentry initialization order bug — calling `sentry_sdk.init()` after `app = FastAPI()` silently disables error capture. The rename from Chessalytics to FlawChess must be done first and verified with grep before any other work, as stale references create silent mismatches in Sentry projects, Docker image tags, and CI/CD scripts.

## Key Findings

### Recommended Stack

The base stack (FastAPI 0.115.x, React 19, PostgreSQL, SQLAlchemy async, TanStack Query, Tailwind, vite-plugin-pwa) is already in production and is not re-evaluated. New additions for v1.3 are deliberately minimal. Caddy is the clear choice over Nginx for a single-server SPA+API deployment: automatic Let's Encrypt TLS with zero configuration, native `try_files` SPA fallback, and a single-file reverse proxy config. The uv multi-stage Docker build pattern keeps the backend image lean by excluding uv and build tools from the runtime layer. Sentry v2.x (not the 3.0 alpha) auto-activates FastAPI and Starlette integrations when initialized at module top-level. Plausible Cloud at $9/month is preferred over Google Analytics because it requires no cookie consent banner (no cookies, no PII) — this eliminates an entire category of GDPR complexity and frontend code.

**Core technologies (new for v1.3):**
- **Docker + Docker Compose 2.x**: Containerization and orchestration with `service_healthy` startup ordering — prevents Alembic running before Postgres is ready
- **Caddy 2.11.2**: Reverse proxy + auto-TLS + static file serving — eliminates certbot, handles SPA routing, ~10 line Caddyfile
- **sentry-sdk 2.55.0**: Backend error tracking — auto-instruments FastAPI; init before `app = FastAPI()` is critical
- **@sentry/react 10.45.0**: Frontend error tracking with `browserTracingIntegration`; source maps via `@sentry/vite-plugin`
- **react-helmet-async 3.0.0**: Per-route `<title>` and `<meta>` for SEO — v3 is React 19-native, delegates to React's built-in metadata hoisting
- **vite-plugin-sitemap 0.8.2**: Build-time `sitemap.xml` and `robots.txt` generation
- **Hetzner Cloud CX32**: 4 vCPU / 8 GB RAM / €6.80/mo — CX32 over CX22 for PostgreSQL + FastAPI + Caddy headroom
- **GitHub Actions + ghcr.io**: CI/CD with free GHCR registry; avoids Docker Hub rate limits

### Expected Features

All table-stakes features are P1 — none are optional for a credible public launch.

**Must have (table stakes for v1.3 launch):**
- FlawChess rename — branding consistency before Sentry/Plausible projects are created with the correct name
- Docker Compose deployment (backend, db, Caddy) with named volumes and health checks
- Alembic migrations in Docker CMD before uvicorn starts (not inside FastAPI lifespan)
- Environment variable configuration (.env on VPS, never hardcoded, never committed)
- GitHub Actions CI/CD (test → build → push GHCR → SSH deploy)
- Sentry backend + frontend (error capture with DSN-guarded init)
- About/landing page with Zobrist-hash USP explanation, FAQ, and registration CTA
- Professional README with screenshots and Docker Compose setup instructions
- Privacy policy page at `/privacy` covering auth data, Sentry, Plausible, user rights
- SEO fundamentals: react-helmet-async meta tags, robots.txt, sitemap.xml on About page
- Plausible analytics (single script tag, no cookie consent required)
- Import queue (asyncio.Semaphore per platform to prevent chess.com IP ban)

**Should have (add after v1.3 validates):**
- Import queue UI feedback showing queued position — add when users report confusion
- Sentry session replay (error-only, `replaysOnErrorSampleRate: 1.0`) — enable after confirming error capture works in production
- Structured JSON logging for log-Sentry correlation — add when production debugging proves painful

**Defer (v2+):**
- ARQ + Redis for durable import queue — only if lost-on-restart jobs become a real user complaint
- Social sharing of position analysis — requires public/anonymous URL design
- Horizontal scaling (Docker Swarm, K8s) — only if single VPS is demonstrably insufficient

### Architecture Approach

The deployment architecture is a single Hetzner VPS running three Docker Compose services: Caddy (ports 80/443), FastAPI backend (internal only), and PostgreSQL (internal only). Caddy is the sole internet-facing ingress: it terminates TLS, proxies explicit API route prefixes (`/auth/*`, `/analysis/*`, `/games/*`, `/imports/*`, etc.) to the backend, and serves the pre-built React `dist/` as static files with `try_files` fallback for client-side routing. Same-domain deployment eliminates CORS in production — the current hardcoded `allow_origins=["http://localhost:5173"]` must be moved to a `CORS_ALLOWED_ORIGINS` settings field. GitHub Actions runs tests on every push and deploys on push to main by building images, pushing to GHCR, and SSH-executing `docker compose pull && docker compose up -d`.

**Major components:**
1. **Caddy**: TLS termination, static SPA serving, API reverse proxy — only internet-facing service
2. **FastAPI + Uvicorn (4 workers)**: All API logic; starts only after PostgreSQL health check passes; Alembic runs in CMD before uvicorn
3. **PostgreSQL**: Persistent data on named `postgres_data` volume; `depends_on: service_healthy` gates backend startup
4. **GitHub Actions**: CI (test + lint) on every push; CD (build → GHCR → SSH deploy) on push to main
5. **Import queue (asyncio.Semaphore)**: Global per-platform semaphore limits concurrent outbound import tasks; prevents chess.com 429 / IP ban
6. **Sentry (backend + frontend)**: Backend init at `main.py` module top-level before `app = FastAPI()`; frontend init before React renders

### Critical Pitfalls

1. **Caddy `try_files` rewrites API calls to `/index.html`** — Use two explicit `handle` blocks: one for each API route prefix with `reverse_proxy`, one catch-all with `file_server + try_files`. Verify with `curl /api/health` returning JSON, not HTML.

2. **Sentry init order silently disables error capture** — Call `sentry_sdk.init()` at module top-level in `main.py` unconditionally before `app = FastAPI()`. Verify with a deliberate test exception route; if nothing appears in Sentry within 60 seconds, init order is wrong.

3. **Import queue starvation causes chess.com IP ban** — Replace uncoordinated `BackgroundTasks` with a global `asyncio.Semaphore(3)` for chess.com and a separate one for lichess. At 4+ concurrent users without this, the server IP gets banned for 24 hours.

4. **PostgreSQL data loss via `docker compose down -v`** — Use a named `postgres_data` volume declared in the top-level `volumes:` section. Never use the `-v` flag in production deployment scripts. Verify persistence by running `down && up` and confirming row count.

5. **Alembic race condition at startup** — Run `alembic upgrade head` in the Docker `CMD` as a shell command before uvicorn, not inside FastAPI's async lifespan. Add a `pg_isready` health check with `depends_on: condition: service_healthy` to prevent the app from starting before Postgres accepts connections.

6. **Stale rename references** — The Chessalytics → FlawChess rename must be the first phase. Run `grep -ri chessalytics` across all file types before declaring the PR complete. Create Sentry and Plausible projects after the rename — not before — since project names are hard to change.

## Implications for Roadmap

Based on the dependency chain identified in ARCHITECTURE.md and the rename-first constraint from PITFALLS.md, a 4-phase structure is recommended:

### Phase 1: Rename + Infra Foundation
**Rationale:** The rename must happen before any external services (Sentry, Plausible) are created using the project name. Docker + Caddy must be validated before CI/CD can be built on top of it. This phase proves end-to-end deployment before adding monitoring complexity.
**Delivers:** FlawChess branding throughout codebase, working Docker Compose stack on Hetzner with auto-TLS, PostgreSQL persistence, Alembic-on-startup, and FastAPI docs disabled in production.
**Features addressed:** FlawChess rename, Docker Compose deployment, Caddy reverse proxy, environment variable config, PostgreSQL volume persistence, Alembic migrations on startup, CORS from settings.
**Pitfalls avoided:** Stale rename references, PostgreSQL data loss, Alembic race condition, Caddy directive ordering, FastAPI docs exposed in production, hardcoded CORS origins.

### Phase 2: CI/CD + Backend Hardening + Sentry Backend
**Rationale:** CI/CD requires Docker images to exist (phase 1 prerequisite). Sentry backend requires a working production environment with the correct domain in the Sentry project. GitHub Actions secrets must be configured after the VPS is provisioned.
**Delivers:** Automated deploy pipeline (push to main → tests → build → GHCR → SSH deploy), Sentry backend error capture, structured config settings.
**Features addressed:** GitHub Actions CI/CD, Sentry backend, SENTRY_DSN in settings, PWA `onNeedRefresh` update banner (critical — API contract coupling between frontend/backend versions).
**Pitfalls avoided:** Sentry init order (init before `app = FastAPI()`), GitHub Actions secrets leakage via SHA-pinned action refs, stale PWA after deployment.

### Phase 3: Frontend Monitoring + Analytics + SEO + Public Pages
**Rationale:** These are all frontend/content concerns that depend on a live production domain (phase 1). Analytics and privacy policy must be decided together — Plausible must be locked in before the privacy policy is written. The About page requires the FlawChess brand to be in place.
**Delivers:** Frontend Sentry error tracking, Plausible analytics (no cookie consent needed), About/landing page, privacy policy page, SEO meta tags + sitemap + robots.txt, professional README.
**Features addressed:** Sentry frontend, Plausible analytics, About page, README, privacy policy, SEO fundamentals.
**Pitfalls avoided:** GDPR analytics-before-consent (eliminated entirely via Plausible), SPA invisible to crawlers (react-helmet-async + sitemap), `index.html` cached with long TTL (Caddy cache headers).

### Phase 4: Import Queue
**Rationale:** Import queue is architecturally independent of infra and CI/CD — it can be done at any point. Placed last because it is a backend-only concern with no deployment dependencies. However, it is P1 for launch — a chess.com IP ban at launch would be catastrophic.
**Delivers:** Global asyncio.Semaphore-based import queue preventing concurrent chess.com rate-limit violations; immediate "queued" status response to frontend.
**Features addressed:** Import queue (asyncio.Semaphore per platform), import status response with queued state.
**Pitfalls avoided:** Import queue starvation / chess.com IP ban.

### Phase Ordering Rationale

- The rename must be atomic and complete before Sentry/Plausible projects are created — those services embed the project name at creation time and are hard to rename.
- Docker + Caddy must be validated manually before CI/CD automates it — you cannot debug a broken pipeline if you have not first confirmed the deployment works manually.
- Sentry backend must be in place before the first real users arrive — silent errors after launch are worse than no error tracking during the build phase.
- Plausible must be chosen before the privacy policy is drafted — the policy must accurately name data processors.
- Import queue is P1 but infrastructure-independent, so it slots cleanly into a final phase without creating ordering risk.

### Research Flags

All four phases have established patterns. No phase requires `/gsd:research-phase`:

- **Phase 1 (Rename + Infra):** Docker Compose + Caddy patterns are well-documented with official sources. uv multi-stage Dockerfile from official astral-sh docs is directly applicable.
- **Phase 2 (CI/CD + Sentry):** GitHub Actions + GHCR deploy pattern is well-documented. Sentry FastAPI init placement is covered by official docs and a specific verified GitHub issue.
- **Phase 3 (Frontend + SEO + Analytics):** react-helmet-async v3 + React 19 compatibility confirmed. Plausible integration is a single script tag. Sentry React follows the same SDK patterns as backend.
- **Phase 4 (Import Queue):** asyncio.Semaphore pattern is standard Python. No novel integration required.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via PyPI, npm CLI, and official GitHub releases. uv Docker pattern from official astral-sh docs. |
| Features | HIGH (infra/monitoring) / MEDIUM (GDPR requirements) | Docker/Caddy/Sentry mechanics HIGH. GDPR legal status MEDIUM — jurisdiction-dependent; Plausible approach eliminates most risk. |
| Architecture | HIGH | Patterns verified against official Caddy, uv, Sentry, Docker Compose docs. Codebase analyzed directly for CORS and config patterns. |
| Pitfalls | HIGH | Critical pitfalls verified via official docs and linked GitHub issues (Sentry #2353, vite-plugin-pwa #33). Community postmortems on PostgreSQL volume loss and Alembic race conditions. |

**Overall confidence:** HIGH

### Gaps to Address

- **GDPR legal status of Google Analytics in specific EU jurisdictions**: MEDIUM confidence only. The recommended approach (Plausible) sidesteps this entirely — but if GA4 is chosen instead, verify current national DPA guidance before launch. Legal position is fluid jurisdiction-by-jurisdiction.
- **Hetzner pricing**: Verified via third-party aggregator (costgoat.com), not hetzner.com directly. Confirm CX32 pricing on hetzner.com before provisioning.
- **chess.com rate-limit thresholds**: Community-reported at ~3-4 concurrent connections; not officially documented. The `asyncio.Semaphore(3)` recommendation is conservative. Monitor 429 responses after launch and tune the semaphore value if needed.
- **PWA `onNeedRefresh` update banner**: Identified as critical (API contract coupling between frontend and backend versions exists in this project) but not listed in the v1.3 MVP feature list in FEATURES.md. Should be explicitly added to Phase 2 scope.

## Sources

### Primary (HIGH confidence)
- [PyPI sentry-sdk](https://pypi.org/project/sentry-sdk/) — version 2.55.0 confirmed
- [Sentry FastAPI integration docs](https://docs.sentry.io/platforms/python/integrations/fastapi/) — auto-activation, init placement
- [Sentry React docs](https://docs.sentry.io/platforms/javascript/guides/react/) — Vite setup, source maps, session replay
- [Caddy GitHub releases](https://github.com/caddyserver/caddy/releases) — v2.11.2 latest stable
- [Caddy try_files docs](https://caddyserver.com/docs/caddyfile/directives/try_files) — SPA fallback pattern
- [Caddy route directive docs](https://caddyserver.com/docs/caddyfile/directives/route) — declaration order preservation
- [uv Docker integration guide](https://docs.astral.sh/uv/guides/integration/docker/) — multi-stage Dockerfile pattern
- [Docker Compose startup order docs](https://docs.docker.com/compose/how-tos/startup-order/) — `service_healthy` condition
- [Vite env variables docs](https://vite.dev/guide/env-and-mode) — VITE_ prefix build-time baking
- [react-helmet-async GitHub issue #238](https://github.com/staylor/react-helmet-async/issues/238) — React 19 v3 compatibility confirmed
- [Sentry sentry-python issue #2353](https://github.com/getsentry/sentry-python/issues/2353) — init order bug documented
- [vite-plugin-pwa issue #33](https://github.com/vite-pwa/vite-plugin-pwa/issues/33) — stale cache update handling
- Direct codebase analysis: `app/main.py`, `app/core/config.py`, `frontend/vite.config.ts`, `pyproject.toml`

### Secondary (MEDIUM confidence)
- [Caddy + FastAPI Docker Compose example](https://github.com/GrantBirki/caddy-fastapi)
- [CI/CD to Hetzner with GitHub Actions](https://infocusdata.com/blog/devops/ci-cd-docker-github-actions-hetzner-deployment)
- [ARQ + FastAPI background tasks comparison](https://davidmuraya.com/blog/fastapi-background-tasks-arq-vs-built-in/)
- [GDPR Cookie Consent Requirements 2025](https://secureprivacy.ai/blog/gdpr-cookie-consent-requirements-2025)
- [Plausible vs Umami 2025 comparison](https://vemetric.com/blog/plausible-vs-umami)
- [Hetzner pricing (costgoat.com)](https://costgoat.com/pricing/hetzner) — verify on hetzner.com before provisioning
- [Lichess API tips](https://lichess.org/page/api-tips)
- [GitHub Actions: top 10 security pitfalls](https://arctiq.com/blog/top-10-github-actions-security-pitfalls-the-ultimate-guide-to-bulletproof-workflows)

### Tertiary (LOW confidence)
- [chess.com API rate limiting](https://www.chess.com/clubs/forum/view/rate-limiting) — community forum, not official; exact thresholds unverified
- WebSearch: GA4 GDPR status by EU jurisdiction (2026) — fluid, verify with current national DPA guidance before committing to GA4

---
*Research completed: 2026-03-21*
*Ready for roadmap: yes*
