# Stack Research

**Domain:** Production deployment, DevOps, monitoring, analytics, SEO — FlawChess v1.3 Project Launch
**Researched:** 2026-03-21
**Confidence:** HIGH (all versions verified via PyPI, npm, or official docs — see Sources)

## Scope Note

This document covers ONLY additions and changes needed for v1.3. The base stack
(FastAPI, React 19, PostgreSQL, SQLAlchemy async, TanStack Query, Vite, Tailwind,
shadcn/ui, python-chess, vite-plugin-pwa) is validated and in production.
Those choices are not re-evaluated here.

---

## Recommended Stack

### Core Technologies (New for v1.3)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Docker Engine | 27.x | Containerization of backend + frontend | Multi-stage builds via official `astral-sh/uv` pattern produce lean images. Standard for reproducible server deploys. |
| Docker Compose v2 | 2.x (bundled with Docker Desktop / Engine) | Multi-container orchestration (backend, db, caddy) | Native `depends_on: condition: service_healthy` solves FastAPI-waits-for-Postgres ordering. Single `compose.yml` for the whole stack. |
| Caddy | 2.11.2 | Reverse proxy + automatic TLS termination | Zero-config Let's Encrypt TLS renewal — no certbot cron, no manual cert management. Built-in SPA `try_files` support. Caddyfile is ~10 lines for this stack. Current stable as of 2026-03-06. |
| sentry-sdk | 2.55.0 | Backend error tracking + performance monitoring | First-party FastAPI integration auto-activates when `fastapi` is present — no extra wiring. Supports traces, profiling, log forwarding. Do NOT use 3.0.x alpha. |
| @sentry/react | 10.45.0 | Frontend error capture + session replay | Official SDK. `ErrorBoundary` wraps the React tree. Source map upload via `@sentry/vite-plugin` makes production stack traces readable. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-helmet-async | 3.0.0 | Per-route `<title>` and `<meta>` tags for SEO | v3 is React 19-native: detects React 19 at runtime and delegates to React's built-in metadata hoisting. No DOM hacks. Use for About page, homepage, and any public route. |
| vite-plugin-sitemap | 0.8.2 | Generate `sitemap.xml` + `robots.txt` at build time | Minimal config: pass `hostname` and static routes. Emits both files into `dist/` automatically. |
| react-cookie-consent | 10.0.1 | GDPR cookie consent banner | Lightweight, fully customizable, no dependencies beyond React. Gates analytics script loading on user acceptance. |
| @sentry/vite-plugin | latest (auto-configured) | Upload source maps to Sentry at build | Required alongside `@sentry/react`. Run `npx @sentry/wizard@latest -i sourcemaps` once — it writes the plugin config into `vite.config.ts`. |

### Development & Deployment Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| GitHub Actions | CI/CD: build image, push to registry, SSH-deploy to Hetzner | Pattern: build → push to ghcr.io → SSH `docker compose pull && docker compose up -d` on server. |
| ghcr.io (GitHub Container Registry) | Docker image registry | Free for public/private repos. No pull rate limits in GitHub Actions workflows. Avoids Docker Hub rate limits. |
| Hetzner Cloud CX32 | VPS hosting | 4 vCPU / 8 GB RAM / 80 GB NVMe / 20 TB transfer / €6.80/mo. CX32 recommended over CX22 (4 GB RAM) because PostgreSQL + FastAPI + Caddy under real load needs headroom. CX22 is viable for very low traffic. |

---

## Installation

```bash
# Backend — add to pyproject.toml
uv add "sentry-sdk[fastapi]"

# Frontend
npm install @sentry/react
npm install react-helmet-async
npm install react-cookie-consent

# Frontend dev dependencies
npm install -D @sentry/vite-plugin vite-plugin-sitemap

# Sentry source map wizard (run once, writes vite.config.ts changes)
npx @sentry/wizard@latest -i sourcemaps
```

---

## Key Configuration Patterns

### Docker: Multi-Stage Python Build with uv

Official pattern from `astral-sh/uv-docker-example`. The uv binary is copied from
the official distroless image — it is not present in the final runtime layer.

```dockerfile
# Build stage: install deps into .venv
FROM python:3.13-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# Dependency layer (cached unless pyproject.toml or uv.lock changes)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev
# Source layer
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# Runtime stage: minimal image, no uv binary
FROM python:3.13-slim-bookworm
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker: Multi-Stage Vite Build

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
# dist/ is copied into the Caddy image or mounted as a volume
```

The frontend does not need its own running container in production — Caddy serves the
`dist/` output directly as static files.

### Caddy: SPA + API Reverse Proxy (Caddyfile)

```caddyfile
flawchess.io {
    # API routes → FastAPI
    handle /api/* {
        reverse_proxy backend:8000
    }

    # SPA: serve static files, fall back to index.html for client-side routing
    handle {
        root * /srv/frontend
        try_files {path} /index.html
        file_server
    }
}
```

Caddy auto-provisions and renews TLS from Let's Encrypt. No certbot, no cron.
`try_files {path} /index.html` is the canonical Caddy SPA pattern.

### Docker Compose: Startup Ordering with Health Checks

```yaml
services:
  db:
    image: postgres:17
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s

  backend:
    build:
      context: ./backend
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SENTRY_DSN=${SENTRY_DSN}

  caddy:
    image: caddy:2.11.2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./frontend/dist:/srv/frontend
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend

volumes:
  caddy_data:   # Persists TLS certs — critical, do not lose
  caddy_config:
```

### Sentry: FastAPI Initialization

```python
# app/main.py — before app = FastAPI()
import sentry_sdk

sentry_sdk.init(
    dsn=settings.sentry_dsn,          # empty string disables Sentry
    traces_sample_rate=0.2,            # 20% in production; 1.0 in staging
    send_default_pii=False,            # avoid capturing PII by default
    environment=settings.environment,  # "production" / "staging" / "development"
)
```

FastAPI and Starlette integrations activate automatically when those packages are present.
No explicit `FastApiIntegration()` instantiation required unless customizing options.

### Sentry: React + Vite Initialization

```typescript
// src/instrument.ts — imported FIRST in main.tsx before any other import
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  integrations: [Sentry.browserTracingIntegration()],
  tracesSampleRate: 0.2,
  environment: import.meta.env.MODE,
});
```

```tsx
// main.tsx
import "./instrument";  // must be first import
import React from "react";
// ... rest of app
```

### SEO: react-helmet-async with React 19

In React 19, react-helmet-async v3 delegates to React's native metadata hoisting.
`HelmetProvider` is a no-op passthrough in React 19 (still include it for compat).

```tsx
import { Helmet } from "react-helmet-async";

// In the About / landing page component:
<Helmet>
  <title>FlawChess — Chess Position Win Rate Analyzer</title>
  <meta
    name="description"
    content="Analyze your win/draw/loss rates for any chess opening position, filtered by your actual piece placement."
  />
  <link rel="canonical" href="https://flawchess.io/" />
</Helmet>
```

For authenticated pages (Dashboard, Openings) meta tags provide minimal SEO value —
focus effort on the homepage and About page.

### Analytics: Google Analytics 4 with Cookie Consent Gate

GA4 with consent gating avoids cookie consent requirements for analytics-only tracking
if using consent mode v2. The simplest integration: load `gtag.js` conditionally.

```tsx
// Load GA4 only after consent is granted
const handleAccept = () => {
  const script = document.createElement("script");
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
  script.async = true;
  document.head.appendChild(script);
};
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Caddy 2.11.2 | Nginx + certbot | Only if you need nginx-specific modules or complex caching headers. Caddy is strictly simpler for auto-TLS on a single VPS. |
| Caddy | Traefik | Traefik excels at Kubernetes/Docker Swarm label-based routing. Overkill for a single-VPS Compose deployment. |
| Google Analytics 4 | Plausible Analytics Cloud (~€9/mo) | Clean GDPR-by-default option if GA4 compliance is a blocker. No self-hosting overhead. |
| Google Analytics 4 | Umami (self-hosted) | Umami runs on the existing PostgreSQL instance (single Docker container, no ClickHouse). Good if you want self-hosted analytics without GA4's GDPR concerns. Slightly more ops than GA4. |
| Google Analytics 4 | Plausible CE (self-hosted) | Requires ClickHouse + Elixir in addition to Postgres. 3+ additional containers. Significant RAM overhead (≥2 GB for ClickHouse alone). Not worth it for a small project on a single VPS. |
| sentry-sdk 2.55.0 | sentry-sdk 3.0.x alpha | 3.0 alpha available (3.0.0a7 as of research date). Do not use in production. |
| react-helmet-async v3 | Native React 19 `<title>` / `<meta>` in JSX | React 19 supports native hoisting via `<title>` and `<meta>` in component JSX. For very simple static titles, react-helmet-async is unnecessary. Use it only when you need `og:*` tags, canonical links, or per-route dynamics in multiple components. |
| GitHub Actions + ghcr.io | Woodpecker CI (self-hosted) | Only worthwhile if GitHub Actions minutes become a cost concern. Adds operational overhead not justified at this project size. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Gunicorn + Uvicorn workers | Adds complexity without benefit on a single server. Docker horizontal scaling (replicas) is the right scale-out mechanism. Gunicorn as a process manager is redundant when Docker handles restarts. | Single `uvicorn` process per container |
| Nginx (for new work) | More config boilerplate vs Caddy for TLS + SPA routing. certbot renewal cron is a silent failure point. | Caddy |
| Plausible CE self-hosted | ClickHouse requires ≥2 GB RAM minimum; the whole Plausible CE stack (Postgres, ClickHouse, Elixir app) needs a dedicated VPS. Competes directly with the main app's resources. | Plausible Cloud or Umami or GA4 |
| `react-helmet` (original) | Unmaintained; known thread-safety issues; no React 18/19 support. | `react-helmet-async` v3 |
| Docker `latest` image tags in production | Non-reproducible: a registry update silently changes your deploy. Breaks rollback. | Pin to semantic version tags (e.g., `caddy:2.11.2`, `postgres:17`) |
| Storing TLS certs in a non-persistent volume | Caddy's `caddy_data` volume contains your Let's Encrypt certificates. If this volume is deleted, Caddy re-requests certs and you may hit LE rate limits (5 certs/domain/week). | Always define `caddy_data` as a named volume; back it up. |
| `requests` library (Python) | Already forbidden by project constraints. Blocks async event loop. | `httpx.AsyncClient` (already in use) |

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| react-helmet-async | 3.0.0 | React 19 | v3 detects React version at runtime; React 19 path uses native hoisting. API-compatible with v2; no code changes needed. |
| sentry-sdk | 2.55.0 | FastAPI 0.115.x, Python 3.13 | FastAPI ≥ 0.79.0 required. Python 3.13 supported. Auto-activates FastAPI + Starlette integrations. |
| @sentry/react | 10.45.0 | React 19, Vite 7 | Vite source map upload requires `@sentry/vite-plugin`. Must be initialized before React renders. |
| Caddy | 2.11.2 | Docker, any HTTP backend | Docker image tag: `caddy:2.11.2`. |
| vite-plugin-sitemap | 0.8.2 | Vite 5+ (Vite 7 in use) | Post-build hook; generates `sitemap.xml` and `robots.txt` in `dist/`. |
| react-cookie-consent | 10.0.1 | React 19 | Pure React component; no conflicting peer deps with React 19. |

---

## Sources

- [PyPI sentry-sdk](https://pypi.org/project/sentry-sdk/) — version 2.55.0 confirmed (released 2026-03-17). HIGH confidence.
- [Sentry FastAPI integration docs](https://docs.sentry.io/platforms/python/integrations/fastapi/) — auto-activation, config options verified. HIGH confidence.
- [Sentry React docs](https://docs.sentry.io/platforms/javascript/guides/react/) — Vite setup, wizard for source maps. HIGH confidence.
- [Caddy GitHub releases](https://github.com/caddyserver/caddy/releases) — v2.11.2 confirmed latest stable (2026-03-06). HIGH confidence.
- [Caddy try_files docs](https://caddyserver.com/docs/caddyfile/directives/try_files) — SPA fallback pattern verified. HIGH confidence.
- [uv Docker integration guide](https://docs.astral.sh/uv/guides/integration/docker/) — multi-stage pattern, ENV vars, layer caching, `uv-docker-example` reference. HIGH confidence.
- `npm info` (local CLI) — @sentry/react@10.45.0, react-helmet-async@3.0.0, react-cookie-consent@10.0.1, vite-plugin-sitemap@0.8.2 confirmed. HIGH confidence.
- [react-helmet-async GitHub issue #238/#239](https://github.com/staylor/react-helmet-async/issues/238) — React 19 compatibility in v3 confirmed. HIGH confidence.
- [Docker Compose startup order docs](https://docs.docker.com/compose/how-tos/startup-order/) — `condition: service_healthy` pattern. HIGH confidence.
- [Hetzner Cloud pricing (costgoat.com, March 2026)](https://costgoat.com/pricing/hetzner) — CX22/CX32 specs and pricing. MEDIUM confidence (third-party aggregator; verify on hetzner.com before provisioning).
- WebSearch: GA4 GDPR status, Plausible/Umami comparison (2026). LOW confidence on GDPR legal status — fluid jurisdiction-by-jurisdiction; verify current DPA guidance before committing to GA4.

---
*Stack research for: FlawChess v1.3 — production deployment, monitoring, analytics, SEO*
*Researched: 2026-03-21*
