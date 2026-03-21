# Feature Research

**Domain:** Production deployment, monitoring, analytics, SEO, and public launch for FastAPI + React SPA (FlawChess v1.3)
**Researched:** 2026-03-21
**Confidence:** HIGH (Docker/Caddy/Sentry mechanics); MEDIUM (GDPR requirements, import queue design, CI/CD patterns); LOW (exact chess.com/lichess rate-limit thresholds — community-reported, not officially documented)

---

> This file covers features for v1.3: Project Launch.
> v1.0–v1.2 features are already shipped (import, analysis, bookmarks, move explorer, game cards, PWA, mobile nav).
> Focus: Docker deployment, Caddy, Hetzner, CI/CD, Sentry, About page, SEO, analytics, privacy policy, import queue, rename.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that a publicly launched web app must have. Missing these = product feels unfinished or legally non-compliant.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Docker Compose deployment | Standard production packaging; reproducible across environments | MEDIUM | Separate services: FastAPI backend, PostgreSQL, Caddy (serves React dist + proxies /api). Multi-stage Dockerfiles: backend (Python slim), frontend (Node build stage → Caddy/nginx copy). |
| Caddy reverse proxy with auto-TLS | HTTPS non-negotiable for any public app; Caddy provisions Let's Encrypt certs automatically with no cert management overhead | LOW | Single `Caddyfile`. Routes `/api/*` to uvicorn. Serves React `dist/` as static files with SPA fallback (`try_files {path} /index.html`). Auto-HTTPS on domain. |
| Environment variable configuration | Production must not hardcode secrets or API DSNs in source | LOW | `.env` on server injected at compose runtime. `VITE_*` vars at frontend build time (baked into bundle). Pydantic `BaseSettings` already supports env on backend. |
| PostgreSQL volume persistence | DB data must survive container restarts and redeploys | LOW | Named Docker volume, not bind mount. `pg_data` volume in `docker-compose.yml`. |
| Alembic migrations on startup | Schema must be current before app accepts traffic — especially important for zero-downtime redeploys | LOW | Backend entrypoint: `alembic upgrade head && uvicorn app.main:app ...`. Idempotent, safe to run on every start. |
| GitHub Actions CI/CD | Automated deploy on push to main; eliminates risky manual SSH deploys over time | MEDIUM | Workflow: run tests → build images → push to GHCR → SSH into Hetzner → `docker compose pull && docker compose up -d`. SSH private key and secrets stored in GitHub Secrets. |
| Sentry error monitoring (backend) | Unhandled exceptions in production must be captured with request context and stack traces | LOW | `sentry-sdk[fastapi]` auto-instruments FastAPI. One `sentry_sdk.init(dsn=..., traces_sample_rate=0.1)` call. DSN from environment variable. |
| Sentry error monitoring (frontend) | JS errors and unhandled promise rejections must surface with component stack | LOW | `@sentry/react` with `Sentry.init()` and `<ErrorBoundary>` wrapping the app. React Router integration for transaction names. |
| About / landing page | New visitors must understand what FlawChess does before registering; the only SEO-indexable page | MEDIUM | Explains Zobrist-hash position matching USP vs chess.com/lichess categorization. FAQ covering: what is it, how does it work, data sources, privacy. CTA: Register / Log in. Fully public (no auth required). |
| Professional README | GitHub visitors judge project quality and credibility by the README | LOW | Project name + description, feature list, screenshots, tech stack badges, quick local setup (Docker Compose), links to live app. |
| Privacy policy page | GDPR legally requires disclosing what data is collected and how it's used whenever collecting personal data or using third-party analytics | MEDIUM | Static page at `/privacy`. Covers: auth data, imported game data (stored server-side), Sentry error tracking, Plausible analytics (no cookies, no PII), user rights (deletion), contact. |
| SEO fundamentals | About page must be discoverable in search engines for FlawChess to grow organically | MEDIUM | `react-helmet-async` for per-route `<title>` and `<meta description>`. Open Graph tags on About page. `robots.txt` (allow all, point to sitemap). `sitemap.xml` listing `/` and `/about` with lastmod. Canonical URL tag. |
| FlawChess rename / branding | Consistent brand identity before public launch; "Chessalytics" is a working title | LOW | Update: repo name, all code string references, PWA manifest (`name`, `short_name`), About page copy, README, Sentry project name, Plausible site name, `CLAUDE.md`. |

### Differentiators (Competitive Advantage)

Features that go beyond table stakes and improve quality, trust, or stability at launch.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Import queue with per-platform serialization | Prevents 429 errors when multiple users import simultaneously. chess.com enforces ~3 concurrent connections; lichess recommends 1 request at a time. Without a queue, concurrent users will get rate-limited and see import failures. | MEDIUM | Two options: (1) `asyncio.Queue` singleton in FastAPI process — simple, zero dependencies, lost on restart but imports are re-triggerable; (2) ARQ + Redis — durable, restartable, adds Redis container. Recommend starting with asyncio.Queue. Two separate queues: one per platform (chess.com, lichess). Each worker drains its queue sequentially with the existing per-platform delay logic. |
| Plausible analytics (privacy-first) | Understand real usage without cookie consent banner, Google data sharing, or GDPR complexity. Plausible uses no cookies and collects no PII, making it exempt from ePrivacy cookie consent requirements. | LOW | Plausible Cloud: $9/mo for 10K pageviews. Single `<script>` tag in `index.html`. SPA-compatible: tracks `pushState` navigation automatically. Recommended over Google Analytics for this project's scale and privacy posture. |
| Sentry session replay (error-only mode) | When a frontend error occurs, a replay shows exactly what the user did — invaluable for debugging chess board interactions and position state. | LOW | Set `replaysOnErrorSampleRate: 1.0`, `replaysSessionSampleRate: 0.0`. Capture replay only on errors — zero cost when no errors occur. Sentry masks all DOM text/images by default, so game data does not leak. |
| Import status + queue position in UI | Users know whether their import is queued, running, or complete — prevents "is this broken?" confusion when many users import simultaneously | MEDIUM | Backend: import status response includes `queued_position` field. Frontend: poll `/imports/status`, show "Queued (#N)" state with estimated wait. Builds on existing Import page polling. |
| Structured JSON logging | Correlate Sentry error reports with server-side logs across container restarts | LOW | Python `logging` with JSON formatter or `structlog`. Include Sentry trace ID in log records. Docker Compose log driver collects stdout JSON. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Google Analytics (with cookie consent banner) | Industry default, familiar reports | Requires GDPR-compliant cookie consent UI — banner must give equal prominence to "Accept" and "Reject". Adds frontend complexity, risks GDPR fines if misconfigured, data goes to Google. Overkill for a small app. | Plausible: no cookies, no consent banner required, GDPR-compliant by design. |
| Celery for import queue | Familiar Python task queue | Requires broker (Redis/RabbitMQ) + result backend + worker process + beat scheduler. For the simple "serialize outbound API calls" use case, this is 10x the complexity needed. | `asyncio.Queue` in the FastAPI process for v1.3. Migrate to ARQ + Redis only if queue durability proves necessary after launch. |
| SSR / Next.js for SEO | SPAs have SEO limitations | Complete rewrite of all existing React code. The only SEO-critical page is the About/landing page. Authenticated analysis pages don't need indexing. | `react-helmet-async` for meta tags on About page. Googlebot handles modern SPAs (Vite + React Router) adequately for this use case. |
| Kubernetes / container orchestration | "Production-grade" framing | Catastrophically over-engineered for a single Hetzner VPS with low initial traffic. Adds enormous operational complexity. | Docker Compose on a single server is the correct level. Upgrade path to Swarm or K8s exists if demand grows. |
| Separate staging environment | Best practice | Doubles Hetzner cost and deployment complexity for a solo developer. | Test with local Docker Compose before pushing. Feature branches with local testing are sufficient for this project's risk profile. |
| Email notifications for import completion | Good UX for long imports | Requires transactional email service (SendGrid/SES), email templates, unsubscribe handling — significant scope creep for v1.3. | In-app polling on the Import page is sufficient. Queue position display closes the feedback gap. |
| Full cookie consent manager (CookieHub, OneTrust) | GDPR compliance | If using Plausible (no cookies) and Sentry (functional, not tracking cookies), no cookie consent banner is legally required. Third-party consent managers are expensive ($50-200/mo), add JS weight, and are unnecessary here. | Plausible replaces tracking cookies entirely. Privacy policy page covers the remaining disclosure requirements. |

---

## Feature Dependencies

```
Docker Compose deployment
    └──requires──> Multi-stage Dockerfiles (backend + frontend)
    └──requires──> Environment variable config (.env on server)
    └──requires──> Alembic migrations on startup

Caddy reverse proxy
    └──requires──> Docker Compose deployment
    └──requires──> Domain DNS pointing to Hetzner IP

GitHub Actions CI/CD
    └──requires──> Docker Compose deployment
    └──requires──> Container registry (GHCR, free for public repos)
    └──requires──> SSH key in GitHub Secrets
    └──enhances──> All deployment features (automates them)

Sentry (frontend)
    └──requires──> FlawChess rename (consistent project naming in DSN)
    └──enhances──> About page (ErrorBoundary wraps whole app including landing)

Sentry session replay
    └──requires──> Sentry frontend (same SDK, additional config)

Plausible analytics
    └──requires──> About page deployed (page views to track)
    └──conflicts──> Google Analytics + cookie consent (pick one)

Privacy policy page
    └──requires──> Plausible analytics chosen (policy covers what data is collected)
    └──requires──> Sentry listed as error tracking third-party

SEO fundamentals
    └──requires──> About page (only public page worth indexing)
    └──requires──> react-helmet-async installed

About page
    └──requires──> FlawChess rename (correct brand name in copy)

Import queue
    └──requires──> asyncio.Queue or ARQ worker setup
    └──requires──> Existing per-platform delay constants (already in codebase)
    └──enhances──> Import status UI (queue position data)

Import status UI
    └──requires──> Import queue (queue position field in status response)
    └──requires──> Existing Import page polling (already implemented)

FlawChess rename
    └──requires──> Update PWA manifest (name, short_name)
    └──requires──> Update all "chessalytics" string references in code/config
    └──must precede──> About page copy, README, Sentry/Plausible project setup
```

### Dependency Notes

- **Import queue: asyncio.Queue vs ARQ:** `asyncio.Queue` lives in the FastAPI process — if the server restarts during an import, that job is lost. Users can re-trigger imports, so this is acceptable for v1.3. ARQ + Redis adds durability but also a Redis container and worker management. Start simple.
- **CI/CD requires GHCR:** GitHub Container Registry is free for public repos. Use `ghcr.io/[owner]/[repo]-backend:latest` and `ghcr.io/[owner]/[repo]-frontend:latest`. Avoids Docker Hub rate limits and account management.
- **Plausible must be chosen before privacy policy is written:** The privacy policy must accurately describe what analytics data is collected. Lock in the analytics tool first.
- **rename must happen before Sentry/Plausible setup:** Both services have a site/project name configured at creation time. Creating them as "FlawChess" from the start avoids a rename step later.

---

## MVP Definition

### Launch With (v1.3)

All of the following are required for a credible public launch. None are optional.

- [ ] FlawChess rename (code, manifest, README, CLAUDE.md)
- [ ] Multi-stage Dockerfiles for backend and frontend
- [ ] Docker Compose with Caddy, FastAPI, PostgreSQL services
- [ ] Alembic migrations on container startup
- [ ] Environment variable config (.env, no hardcoded secrets)
- [ ] GitHub Actions CI/CD (test → build → push GHCR → SSH deploy)
- [ ] Sentry backend (sentry-sdk[fastapi], DSN from env)
- [ ] Sentry frontend (@sentry/react, ErrorBoundary)
- [ ] About page with FlawChess USPs, FAQ, and CTA
- [ ] Professional README with screenshots and setup instructions
- [ ] Privacy policy page (/privacy)
- [ ] SEO: react-helmet-async, meta tags on About, robots.txt, sitemap.xml
- [ ] Plausible analytics (script tag, site registered)
- [ ] Import queue (asyncio.Queue per platform, serialized outbound calls)

### Add After Validation (v1.x)

- [ ] Import queue UI feedback (queue position on Import page) — add after queue is live and users report confusion
- [ ] Sentry session replay (error-only) — enable after confirming error capture is working in production
- [ ] Structured JSON logging — add if debugging production issues without log correlation proves painful
- [ ] Blog or changelog page — only if SEO strategy expands

### Future Consideration (v2+)

- [ ] ARQ + Redis for durable import queue — only if lost-on-restart jobs become a real user complaint
- [ ] Social sharing (shareable position analysis links) — requires public/anonymous URL design
- [ ] Horizontal scaling (Docker Swarm, K8s) — only if VPS capacity is demonstrably insufficient

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| FlawChess rename | MEDIUM | LOW | P1 |
| Docker + Caddy deployment | HIGH | MEDIUM | P1 |
| Alembic on startup | HIGH | LOW | P1 |
| Environment variable config | HIGH | LOW | P1 |
| GitHub Actions CI/CD | HIGH | MEDIUM | P1 |
| Sentry backend | HIGH | LOW | P1 |
| Sentry frontend | HIGH | LOW | P1 |
| About page | HIGH | MEDIUM | P1 |
| README | MEDIUM | LOW | P1 |
| Privacy policy | HIGH (legal) | LOW | P1 |
| SEO fundamentals | MEDIUM | LOW | P1 |
| Plausible analytics | MEDIUM | LOW | P1 |
| Import queue | HIGH (stability) | MEDIUM | P1 |
| Import queue UI feedback | MEDIUM | MEDIUM | P2 |
| Sentry session replay | MEDIUM | LOW | P2 |
| Structured JSON logging | LOW | LOW | P2 |

**Priority key:**
- P1: Must have for v1.3 launch
- P2: Should have, add when time permits
- P3: Nice to have, future consideration

---

## Ecosystem Comparison

| Feature | chess.com Insights | lichess Analysis | FlawChess approach |
|---------|-------------------|------------------|--------------------|
| Opening analysis | By ECO name, not position | By opening name/moves | By exact board position (Zobrist hash) — handles transpositions |
| Analytics | Google Analytics | Self-hosted Matomo | Plausible (no cookies, GDPR-compliant) |
| Deployment | Cloud SaaS | Open source / self-hosted | Single Hetzner VPS, Docker Compose |
| Error monitoring | Not visible | Not visible | Sentry (backend + frontend) |
| Mobile | Native apps | PWA + native apps | PWA (already shipped in v1.2) |

---

## Sources

- [FastAPI Deployment Concepts](https://fastapi.tiangolo.com/deployment/concepts/) — HIGH confidence
- [FastAPI Docker Guide](https://fastapi.tiangolo.com/deployment/docker/) — HIGH confidence
- [Caddy + FastAPI Docker Compose](https://github.com/GrantBirki/caddy-fastapi) — MEDIUM confidence
- [Sentry FastAPI Integration](https://docs.sentry.io/platforms/python/integrations/fastapi/) — HIGH confidence
- [Sentry React SDK + Session Replay](https://docs.sentry.io/platforms/javascript/guides/react/session-replay/) — HIGH confidence
- [Plausible Privacy-Focused Analytics](https://plausible.io/privacy-focused-web-analytics) — HIGH confidence
- [ARQ + FastAPI background tasks](https://davidmuraya.com/blog/fastapi-background-tasks-arq-vs-built-in/) — MEDIUM confidence
- [GDPR Cookie Consent Requirements 2025](https://secureprivacy.ai/blog/gdpr-cookie-consent-requirements-2025) — MEDIUM confidence
- [React + Vite SEO with react-helmet-async](https://dev.to/ali_dz/optimizing-seo-in-a-react-vite-project-the-ultimate-guide-3mbh) — MEDIUM confidence
- [GitHub Actions + Hetzner SSH Deploy](https://infocusdata.com/blog/devops/ci-cd-docker-github-actions-hetzner-deployment) — MEDIUM confidence
- [chess.com API rate limiting](https://www.chess.com/clubs/forum/view/rate-limiting) — LOW confidence (community forum, not official API docs)
- [Lichess API tips](https://lichess.org/page/api-tips) — MEDIUM confidence (official Lichess page)

---

*Feature research for: FlawChess v1.3 — production deployment, monitoring, analytics, SEO, public launch*
*Researched: 2026-03-21*
