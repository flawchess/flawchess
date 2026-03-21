# Pitfalls Research

**Domain:** Production deployment + monitoring + analytics + SEO + launch infrastructure for FastAPI + React SPA + PostgreSQL
**Researched:** 2026-03-21
**Confidence:** HIGH (critical pitfalls verified via official docs + community postmortems); MEDIUM (scale thresholds from community experience)

---

## Critical Pitfalls

### Pitfall 1: Caddy Directive Ordering Breaks API Routing

**What goes wrong:**
When Caddy serves the React SPA (static files + `try_files` fallback) and also proxies `/api/*` to FastAPI, the `try_files` directive has a higher internal priority than `reverse_proxy`. Without explicit ordering control, all requests — including API calls — get rewritten to `/index.html` before `reverse_proxy` can match. API calls return the HTML shell instead of JSON, and the app silently fails to load any data.

**Why it happens:**
Caddyfile directive ordering is implicit and non-obvious. Developers configure directives in logical reading order (proxy first, then SPA fallback), but Caddy sorts them by its own internal priority table, not declaration order.

**How to avoid:**
Wrap all directives in a `route {}` block, or use two `handle` blocks: one for `/api*` targeting `reverse_proxy`, one as a catch-all fallback with `file_server` + `try_files`. The `route` block preserves declaration order:
```
route {
  reverse_proxy /api/* localhost:8000
  file_server
  try_files {path} /index.html
}
```

**Warning signs:**
- API calls return HTTP 200 with `Content-Type: text/html` instead of `application/json`
- React app loads but all TanStack Query requests fail with JSON parse errors

**Phase to address:** Docker + Caddy deployment phase (phase 1)

---

### Pitfall 2: PostgreSQL Data Loss via Missing Named Volume

**What goes wrong:**
`docker compose down` followed by `docker compose up --build` destroys all PostgreSQL data. If the `db` service uses an anonymous volume or no volume, data lives only in the container's writable layer — removed with the container. All user games and position data wiped on every redeploy.

**Why it happens:**
Docker containers are ephemeral by design. Tutorials frequently omit volume declarations for brevity. The `postgres` image stores data at `/var/lib/postgresql/data` inside the container — without a named volume mounted there, data does not persist.

**How to avoid:**
Declare a named volume in `docker-compose.yml`:
```yaml
volumes:
  postgres_data:

services:
  db:
    image: postgres:17
    volumes:
      - postgres_data:/var/lib/postgresql/data
```
Use `docker compose down` (without `-v`) in all deployment scripts. Never run `docker compose down -v` in production automation.

**Warning signs:**
- Volume declaration uses a relative host path with no top-level `volumes:` entry (brittle)
- Deploy script runs `docker compose down` without confirming named volume exists first

**Phase to address:** Docker + Caddy deployment phase (phase 1)

---

### Pitfall 3: Alembic Migrations Race Condition at Container Startup

**What goes wrong:**
The FastAPI app container starts and immediately tries to connect to PostgreSQL before the database is ready to accept connections (PG needs 3-10s to initialize on first run). Either the app crashes on startup, or — if `alembic upgrade head` runs from within FastAPI's lifespan — multiple replicas attempt migrations simultaneously, causing schema corruption.

**Why it happens:**
`depends_on: db` in Docker Compose only waits for the container process to start, not for PostgreSQL to be ready. The `pg_isready` health check is the correct gate but is frequently omitted. Running migrations from within `asyncio` lifespan also has a known issue: the Alembic context variable is sometimes `None` when using an async engine.

**How to avoid:**
1. Add a `healthcheck` to the `db` service and `depends_on: condition: service_healthy` for the app.
2. Run `alembic upgrade head` as a one-off step before the app starts (e.g., `command: sh -c "alembic upgrade head && uvicorn app.main:app ..."`), not inside the FastAPI lifespan.
```yaml
db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U $POSTGRES_USER"]
    interval: 5s
    retries: 5

app:
  depends_on:
    db:
      condition: service_healthy
```

**Warning signs:**
- App container restarts once, then succeeds — masks the race condition
- `sqlalchemy.exc.OperationalError: could not connect to server` in early logs

**Phase to address:** Docker + Caddy deployment phase (phase 1)

---

### Pitfall 4: Service Worker Serves Stale App After Deployment

**What goes wrong:**
This project already uses `vite-plugin-pwa` with Workbox. After a new deployment, returning users continue to run the old app version — including stale API request shapes that may be incompatible with the updated FastAPI backend. The user sees no error; the app silently fails or returns wrong data because the old JS bundle sends requests the new API no longer recognizes.

**Why it happens:**
Workbox precaches all assets at build time. The service worker update cycle requires: (1) browser detects a new `sw.js`, (2) new SW installs, (3) user closes all tabs or accepts a prompt. Step 3 often never happens in an installed PWA where the tab is never fully closed.

**How to avoid:**
- Implement the `onNeedRefresh` callback from `vite-plugin-pwa`'s `useRegisterSW` hook to show a "New version available — reload?" banner.
- Do not use `skipWaiting: true` silently — this interrupts in-progress analysis sessions.
- Set `Cache-Control: no-cache` on `index.html` in Caddy (assets in `/assets/` with content-hashed filenames can use `immutable` caching safely).

**Warning signs:**
- Users report seeing old UI after a deploy
- Sentry shows API errors affecting only a subset of users (those on cached version)
- `sw.js` gets a new hash in the deploy but affected users do not reload

**Phase to address:** Docker + Caddy deployment phase (cache headers for `index.html`); also part of CI/CD phase (update banner verification)

---

### Pitfall 5: GDPR Violation — Analytics Fires Before Consent

**What goes wrong:**
Google Analytics (or any tracking script) initializes on page load before the consent banner is shown or accepted. The banner's presence does not constitute consent — under GDPR, data collection must not begin until explicit user consent is given. Firing GA before consent is a violation regardless of whether a banner exists.

**Why it happens:**
The most natural implementation puts `gtag` initialization in `index.html` or a top-level React `useEffect`. Both fire immediately on every page load, including first visits where no consent has been given.

**How to avoid:**
- Gate `gtag` initialization behind stored consent state: only initialize after the user explicitly accepts analytics cookies.
- On subsequent visits, check the stored consent flag on app load and re-initialize GA if previously accepted (so returning users who consented are tracked without seeing the banner again).
- Implement Google Consent Mode v2 — mandatory since March 2024 for EU users of Google services. Without it, Google stops processing conversion data from EEA users.
- Alternatively: use Plausible Analytics or Umami (privacy-friendly, no cookies, no PII). These do not require a consent banner at all, eliminating this pitfall category entirely. Recommended given this project's developer audience.

**Warning signs:**
- Network tab shows `google-analytics.com` requests on first page load before any user interaction
- Analytics consent cookie is absent when analytics network requests fire

**Phase to address:** Analytics + privacy policy phase

---

### Pitfall 6: GitHub Actions Secrets Leaked via Third-Party Actions

**What goes wrong:**
CI/CD workflows using third-party GitHub Actions run with the same permissions as the workflow. In 2025, multiple supply-chain incidents compromised widely-used actions by rewriting mutable version tags (`@v3`, `@v4`) to serve malicious code that exfiltrates secrets from the runner — including `DATABASE_URL`, `SSH_PRIVATE_KEY`, and Docker registry tokens.

**Why it happens:**
Version tags like `@v3` are mutable. An attacker who compromises the action maintainer's account can reassign the tag to a different commit. Pinning to `@v3` provides no integrity guarantee.

**How to avoid:**
- Pin all third-party actions to a full commit SHA: `uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` (not `@v4`).
- Minimize secret scope: use environment-scoped secrets rather than repository-wide where possible.
- Use `--password-stdin` for Docker registry login rather than inline token arguments (process args can be visible via `ps` on a self-hosted runner).
- Never run `echo $SECRET` in `run:` steps — GitHub's automatic redaction is not guaranteed after all transformations.

**Warning signs:**
- Workflow files use `@v3` or `@main` style action references
- `DATABASE_URL` or `SSH_PRIVATE_KEY` passed as environment variables without review of the action's source

**Phase to address:** CI/CD pipeline phase

---

### Pitfall 7: Import Queue Starvation Under Concurrent Users

**What goes wrong:**
Currently each user import is a FastAPI `BackgroundTask`. Under concurrent users, multiple imports run simultaneously — each making sequential HTTP requests to chess.com/lichess with embedded rate-limit delays. Chess.com enforces roughly 3-4 concurrent connections per server IP; the fourth concurrent import receives HTTP 429 and either silently fails or triggers a temporary IP-level ban. With 5+ simultaneous importing users, the platform can ban the server's IP for 24 hours.

**Why it happens:**
`BackgroundTasks` has no global concurrency limit or coordination across user sessions. Each import is an independent async task with no awareness of other running imports.

**How to avoid:**
- Implement a global `asyncio.Semaphore` limiting concurrent outbound import tasks (e.g., `asyncio.Semaphore(3)` for chess.com, separate one for lichess).
- Return an immediate "queued" status to the frontend; poll for progress via a status endpoint.
- Persist import state in the DB (queued / running / complete / failed) so status survives app restarts.
- Do not introduce Celery — it adds Redis + worker infrastructure disproportionate to this use case. A semaphore-based asyncio queue is sufficient at current scale.

**Warning signs:**
- Import works for solo testing but fails when two users import simultaneously
- Chess.com 429 errors in logs with no retry logic
- Users see no feedback after clicking "Import" — task silently dropped

**Phase to address:** Import queue phase

---

### Pitfall 8: Sentry Initialization Order Silently Breaks Error Capture

**What goes wrong:**
If `sentry_sdk.init()` is called after the FastAPI app is instantiated or after middleware is added, the ASGI integration hooks are never registered. Errors occur and are logged, but nothing appears in the Sentry dashboard. The app appears to be working normally while errors go untracked.

**Why it happens:**
Sentry is often added as an afterthought and dropped inside a function or after `app = FastAPI()`. The `FastApiIntegration` must hook into the app at construction time; late initialization misses the middleware chain. A known GitHub issue (`sentry-python #2353`) documents exactly this: "When initialized before FastAPI app, sentry doesn't capture errors" — the fix is initialization at module top-level, unconditionally before `app = FastAPI()`.

**How to avoid:**
Call `sentry_sdk.init(...)` at module top-level in `main.py`, unconditionally, before `app = FastAPI(...)`. Use `FastApiIntegration` and `AsyncioIntegration` (the latter required for correct async task context propagation). Verify with a deliberate test route.

**Warning signs:**
- Sentry dashboard shows zero events despite confirmed unhandled exceptions in logs
- Test route `GET /api/debug/sentry-test` raises but no event appears in Sentry within 60 seconds

**Phase to address:** Monitoring + Sentry phase

---

### Pitfall 9: SEO — SPA Returns Empty HTML Shell to Crawlers

**What goes wrong:**
Googlebot fetches `index.html` and receives `<div id="root"></div>` — nothing. React has not run. There are no `<meta>` description tags, no `<title>`, no visible text. The app is invisible to search engines for all routes, including the About/landing page that is critical for organic discovery.

**Why it happens:**
Client-side rendering defers all content to JavaScript execution. Google's crawl pipeline does execute JavaScript, but with delays of days to weeks and no guaranteed success rate. Even when Google does render the page, dynamic meta tags set via React are often missed on the first crawl pass.

**How to avoid:**
For a chess analysis tool whose primary SEO value is the landing/About page (not per-user analysis pages), the pragmatic approach is:
- Use `react-helmet-async` to set `<title>` and `<meta description>` on the About, Login, and root pages.
- Pre-render the About/landing page as static HTML at build time — either a simple `/about.html` served by Caddy, or using `vite-ssg` for selective pre-rendering. This gives crawlers real content without full SSR infrastructure.
- Generate a `sitemap.xml` and `robots.txt` served as static files.
- Do not add Next.js or full SSR for this milestone — complexity is disproportionate. Focus on the marketing pages only.

**Warning signs:**
- `curl https://flawchess.com/about` returns `<div id="root"></div>` with no visible text in `<body>`
- Google Search Console shows pages as "Discovered — currently not indexed" after weeks

**Phase to address:** SEO fundamentals phase

---

### Pitfall 10: Rename Leaves Stale References Causing Silent Mismatches

**What goes wrong:**
Renaming Chessalytics to FlawChess is easy in visible branding (HTML title, README) but incomplete in code. Old names persist in: Python `pyproject.toml` metadata, environment variable names (e.g., `CHESSALYTICS_SECRET_KEY` in deployment scripts), Alembic migration comment headers, Docker image tags, GitHub Actions workflow names, Sentry project DSN configuration, and `package.json` `name` field. These rarely cause immediate failures but create confusion and silent mismatches — Sentry events tagged to the wrong project, CI alerts referencing the wrong app name.

**Why it happens:**
Renames are treated as a visible-strings find-and-replace, but structural references baked into deployment scripts, env var names, CI secrets, and container registry paths are missed.

**How to avoid:**
- Before declaring the rename PR complete, run `grep -ri chessalytics . --include="*.py" --include="*.ts" --include="*.json" --include="*.yml"` and resolve all hits.
- Update explicitly: `package.json` `name`, `pyproject.toml` `[project] name`, any env vars with the old name, Docker image tag in compose and CI scripts, Sentry project name, GitHub repo name (creates automatic redirects for ~1 year — still update your local remote immediately with `git remote set-url`).

**Warning signs:**
- `grep -ri chessalytics` returns hits after the rename PR merges
- Sentry events land in a project named "chessalytics" post-launch

**Phase to address:** Rename/rebrand phase — should be the first or a standalone phase before other phases introduce new references to the new name

---

### Pitfall 11: FastAPI Docs Endpoint Exposed in Production

**What goes wrong:**
FastAPI's auto-generated `/docs` (Swagger UI) and `/redoc` endpoints are enabled by default. In production, these expose the full API schema, all endpoint signatures, request/response models, and authentication flows to any visitor. This enables targeted enumeration and attack construction.

**Why it happens:**
Default FastAPI configuration enables docs for developer convenience. There is no framework-level nudge to disable them in production.

**How to avoid:**
Configure the app with docs disabled in production:
```python
app = FastAPI(
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
)
```

**Warning signs:**
- `GET https://flawchess.com/docs` returns a Swagger UI page in production
- `/openapi.json` endpoint returns the full schema publicly

**Phase to address:** Docker + Caddy deployment phase (production config)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| No Docker health check — rely on `depends_on` service name only | Simpler compose file | Intermittent startup failures; app crashes before DB is ready | Never in production |
| Run `alembic upgrade head` inside FastAPI async lifespan | Single deployment artifact | Race condition with multiple replicas; async engine context bugs | Never |
| Hardcode `DATABASE_URL` in `docker-compose.yml` | No secrets setup required | Credentials in VCS history | Never |
| GA without Consent Mode v2 | Simpler implementation | GDPR violation; Google stops processing EEA conversions | Never for EU-accessible apps |
| `BackgroundTasks` for concurrent imports with no semaphore | No extra infrastructure | chess.com IP ban at 4+ concurrent users | MVP only if max concurrent users is known to be < 3 |
| No PWA `onNeedRefresh` update banner | One fewer UI component | Users run stale version indefinitely after deploys | Never — app has API contract coupling between frontend and backend versions |
| Pin GitHub Actions to `@v3` tags instead of commit SHA | Readable workflow files | Supply-chain attack vector (multiple incidents in 2025) | Never for workflows handling production secrets |
| Leave `/docs` and `/redoc` enabled in production | Convenient for debugging | API schema enumeration by attackers | Never in production |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Caddy + React SPA | `try_files` rewrites API calls to `/index.html` | Wrap in `route {}` block; put `reverse_proxy /api/*` first |
| Caddy + `index.html` | Long `Cache-Control: max-age` on `index.html` | `Cache-Control: no-cache` on `index.html`; `immutable` caching safe only for `/assets/` content-hashed files |
| Sentry + FastAPI | `sentry_sdk.init()` called after `app = FastAPI()` | Init at module top-level before app instantiation; use `FastApiIntegration` + `AsyncioIntegration` |
| Sentry + React | Using `SENTRY_DSN` env var (not exposed by Vite) | Use `VITE_SENTRY_DSN` (public prefix required for Vite to expose to browser bundle) |
| Google Analytics + GDPR | `gtag` in `<head>` fires before consent | Gate initialization on consent state; implement Consent Mode v2; or use Plausible to skip consent entirely |
| chess.com API + concurrent users | Multiple simultaneous imports hit 429 or trigger IP ban | Global `asyncio.Semaphore(3)` shared across all user import tasks |
| Docker + PostgreSQL | Container data in writable layer — lost on `down` | Named volume in `docker-compose.yml` top-level `volumes:` |
| Docker + json-file logging | Unbounded log file growth exhausts disk | Set `logging: driver: local` or `--log-opt max-size=10m max-file=3` |
| GitHub Actions + Docker registry | `--password` argument visible in `ps` output | Use `--password-stdin` with piped input |
| vite-plugin-pwa + deployments | No update notification — users stay on old version | Implement `useRegisterSW` with `onNeedRefresh` reload banner |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No DB connection pool config | App works in dev, timeouts under load in prod | Set `pool_size`, `max_overflow`, `pool_timeout` in SQLAlchemy async engine | ~20 concurrent requests |
| Docker json-file log driver, no rotation | Host disk exhausts; app becomes unresponsive | `logging: driver: local` in compose, or `--log-opt max-size=10m` | After days of moderate traffic |
| No Hetzner volume for PostgreSQL | Data in container layer — lost on VM restart | Mount Hetzner volume at `/mnt/data`, bind-mount into container | Any VM restart |
| `index.html` cached by CDN or browser with long TTL | New deployments not picked up by returning users | `Cache-Control: no-cache` on `index.html` specifically in Caddy | Any deployment after the first |
| Import task state not persisted | User import disappears with no status if app restarts | Store import state (queued / running / done / failed) in DB | Any app restart during an active import |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `SECRET_KEY` or `DATABASE_URL` committed to `.env` in VCS | Credential exposure in public repo | `.env` in `.gitignore`; use `.env.example` with placeholders; pass secrets via GitHub Actions secrets |
| FastAPI `/docs` and `/redoc` enabled in production | API schema enumeration; targeted attacks | `docs_url=None, redoc_url=None` in production config |
| No rate limiting on `/auth/login` | Brute-force credential stuffing | Add `slowapi` or Caddy rate limiting on auth endpoints |
| Docker container port bound to `0.0.0.0:8000` | FastAPI directly reachable, bypassing Caddy | Bind to `127.0.0.1:8000`; only Caddy faces the internet |
| Frontend `VITE_SENTRY_DSN` treated as secret | Unnecessary secret management overhead | Frontend DSN is intentionally public; only the backend DSN needs protection. Use separate Sentry projects for frontend and backend. |
| Third-party GitHub Actions at mutable version tags | Supply-chain attack exfiltrates production secrets | Pin all actions to full commit SHA |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No import queue status — "Import" click gives no feedback | User clicks multiple times; duplicate imports queued | Immediate "queued" status response; disable button while running; poll for completion |
| Cookie consent banner blocks the entire viewport on mobile | First-time mobile users cannot see the app at all | Compact bottom banner; "Accept" + "Manage" buttons only; never full-screen overlay |
| PWA update banner fires aggressively during active session | Users are interrupted mid-analysis | Show banner only when user is idle or navigates; allow dismissal |
| Privacy policy linked only in footer on desktop | Mobile users never find it; GDPR requires accessible link | Link in the consent banner itself; also in the mobile "More" drawer |

---

## "Looks Done But Isn't" Checklist

- [ ] **Docker volume:** Named volume declared AND verified to survive `docker compose down` + `up` — check with `docker volume ls` and query row count post-cycle
- [ ] **Caddy SPA routing:** Deep-link URL (e.g., `/openings`) works on hard refresh — not just root navigation
- [ ] **Caddy SSL:** Certificate auto-renewed — check Caddy logs for ACME challenge success; verify with `curl -I https://flawchess.com`
- [ ] **Alembic on deploy:** Migrations complete before app starts (confirmed via `docker compose logs` ordering)
- [ ] **Sentry FastAPI:** Test exception route raises — event appears in Sentry dashboard within 60 seconds
- [ ] **Sentry React:** Frontend JS error triggered — stack trace appears sourcemapped (not minified) in Sentry
- [ ] **Analytics GDPR:** Network tab on first visit shows zero requests to `google-analytics.com` before the consent "Accept" action
- [ ] **PWA update banner:** Deploy a visible change, reload the installed PWA — update notification appears within one background check cycle
- [ ] **SEO:** `curl https://flawchess.com/about` returns non-empty visible text in `<body>` (not just `<div id="root">`)
- [ ] **Rename complete:** `grep -ri chessalytics . --include="*.py" --include="*.ts" --include="*.json" --include="*.yml"` returns zero hits
- [ ] **Import queue:** Two simultaneous imports from different browser sessions complete without chess.com 429 errors
- [ ] **FastAPI docs disabled:** `GET /docs` returns 404 in production

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| PostgreSQL data loss (no volume) | HIGH | Restore from Hetzner snapshot if configured; otherwise ask users to re-import; set up named volume immediately |
| Service worker serving stale version | LOW-MEDIUM | Deploy a self-destroying service worker that immediately unregisters; users get fix on next browser check; add `onNeedRefresh` banner going forward |
| chess.com IP ban from concurrent imports | MEDIUM | Wait out the ban (typically 24 hours); implement semaphore immediately; consider Hetzner floating IP as emergency alternative |
| Sentry not capturing errors (wrong init order) | LOW | Fix init order, redeploy; only cost is a gap in error history |
| GA firing before consent (GDPR) | HIGH | Immediate: disable GA entirely; medium-term: reimplement behind consent gate or switch to Plausible |
| GitHub Actions secret leaked via compromised action | HIGH | Rotate all exposed secrets immediately; audit action versions; pin all actions to SHA; review recent workflow run logs for unauthorized commands |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Caddy directive ordering breaks API routing | Docker + Caddy deployment | `curl /api/health` returns JSON; `/openings` hard-refresh returns SPA |
| PostgreSQL data loss (no volume) | Docker + Caddy deployment | `docker compose down && docker compose up` preserves all rows |
| Alembic startup race condition | Docker + Caddy deployment | Clean deploy from scratch completes without container restart loops |
| Stale PWA after deployment | Docker + Caddy (cache headers) + CI/CD (update banner) | Redeploy while PWA is open; update notification appears |
| FastAPI docs exposed in production | Docker + Caddy deployment | `GET /docs` returns 404 in production |
| Analytics fires before GDPR consent | Analytics + privacy policy phase | Network tab shows zero GA requests before consent action |
| GitHub Actions secrets supply-chain risk | CI/CD pipeline phase | All third-party actions pinned to commit SHA in workflow files |
| Import queue starvation (chess.com 429) | Import queue phase | Concurrent 3-user import test completes without 429 errors |
| Sentry init order | Monitoring + Sentry phase | Test exception route triggers Sentry event within 60s |
| SPA invisible to crawlers | SEO fundamentals phase | `curl /about` returns meaningful text content in response body |
| Stale rename references | Rename/rebrand phase (first) | `grep -ri chessalytics` returns zero hits after PR merges |

---

## Sources

- [Caddy: route directive preserving declaration order](https://caddyserver.com/docs/caddyfile/directives/route)
- [Caddy community: React Router + reverse_proxy 404 issue](https://caddy.community/t/caddy-reverse-proxy-and-react-router/13013)
- [Configuring Client-Side Routing for React SPA with Caddy](https://blog.metters.dev/posts/caddy-routing-and-reload-safety-with-csr-on-spa/)
- [Docker: stop losing PostgreSQL data on container restart](https://dev.to/teguh_coding/docker-volumes-explained-stop-losing-data-every-time-you-restart-a-container-254g)
- [Solving the FastAPI, Alembic, Docker startup problem](https://hackernoon.com/solving-the-fastapi-alembic-docker-problem)
- [Sentry FastAPI integration — official docs](https://docs.sentry.io/platforms/python/integrations/fastapi/)
- [Sentry: initialized before FastAPI app — issue #2353](https://github.com/getsentry/sentry-python/issues/2353)
- [vite-plugin-pwa: automatic reload / update handling](https://vite-pwa-org.netlify.app/guide/auto-update.html)
- [GDPR cookie consent — what developers get wrong](https://dev.to/andreashatlem/gdpr-cookie-consent-implementation-what-most-developers-get-wrong-and-how-to-fix-it-1jpl)
- [Your cookie consent banner is probably breaking your analytics](https://dev.to/anjab/your-cookie-consent-banner-is-probably-breaking-your-analytics-5c4h)
- [Google Analytics GDPR compliance 2025](https://gdprlocal.com/google-analytics-gdpr-compliance/)
- [GitHub Actions: top 10 security pitfalls](https://arctiq.com/blog/top-10-github-actions-security-pitfalls-the-ultimate-guide-to-bulletproof-workflows)
- [FastAPI async task management pitfalls](https://leapcell.io/blog/understanding-pitfalls-of-async-task-management-in-fastapi-requests)
- [Why SPAs still struggle with SEO in 2025](https://dev.to/arkhan/why-spas-still-struggle-with-seo-and-what-developers-can-actually-do-in-2025-237b)
- [Docker logging driver disk exhaustion prevention](https://betterstack.com/community/guides/scaling-python/fastapi-docker-best-practices/)
- [Vite SPA PWA stale cache — vite-plugin-pwa issue #33](https://github.com/vite-pwa/vite-plugin-pwa/issues/33)

---
*Pitfalls research for: FlawChess / Chessalytics v1.3 — Production deployment, monitoring, analytics, SEO, and public launch*
*Researched: 2026-03-21*
