# Phase 23: Launch Readiness - Research

**Researched:** 2026-03-22
**Domain:** Public homepage (React), SEO static files, privacy policy page, asyncio rate limiter, README
**Confidence:** HIGH

## Summary

Phase 23 has five independent workstreams: a public homepage at `/`, SEO fundamentals (OG tags, robots.txt, sitemap.xml), a privacy policy page at `/privacy`, a shared per-platform rate limiter for concurrent import jobs, and a professional README. All decisions are locked in CONTEXT.md — this research verifies implementation paths and documents the integration points needed for planning.

The current routing in `App.tsx` treats `/` as a protected `HomeRedirect` — that must change. `/` and `/privacy` need to be placed outside `ProtectedLayout` so unauthenticated visitors can access them. The rate limiter is a module-level `asyncio.Semaphore` shared across all concurrent jobs for a given platform, wrapping individual API calls in the existing client functions. robots.txt and sitemap.xml are served as static files in the Vite `public/` directory; Caddy already serves everything in `/srv` before the SPA fallback, so no Caddy config change is required.

**Primary recommendation:** Implement all five workstreams in separate waves. Routing surgery first (it unblocks the homepage and privacy), then homepage content, then SEO/static files, then rate limiter (backend only), then README last.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Homepage (replaces About page — CONT-01)**
- D-01: `/` is the public homepage for unauthenticated visitors; authenticated users auto-redirect to `/openings`
- D-02: No separate `/about` route — the homepage IS the about page
- D-03: 5 headline feature sections (Find weaknesses, Scout opponents, Interactive move explorer, Cross-platform analysis, Powerful filters)
- D-04: One prominent "Sign up free" CTA button; login button in the header
- D-05: 1-2 screenshots of the UI (manual asset — user will provide)
- D-06: Tagline: "Engines are flawless, humans play FlawChess"
- D-07: "Open source and free" and "Mobile friendly" as smaller callouts, not headline features
- D-08: FAQ section (5 questions defined verbatim in CONTEXT.md)

**SEO (CONT-02)**
- D-09: Static meta tags in `index.html` — no head management library
- D-10: `<title>`: "FlawChess — Chess Opening Analysis"
- D-11: Open Graph image: screenshot with logo (1200x630px, manual asset, referenced in meta tags)
- D-12: `robots.txt` allowing `/` and `/privacy`, disallowing everything else
- D-13: `sitemap.xml` with just `/` and `/privacy`
- D-14: Privacy page title: "Privacy Policy | FlawChess"

**Privacy policy (CONT-03)**
- D-15: Plain language — "What we collect", "Who we share it with", "Your rights"
- D-16: Route: `/privacy` — public, no auth required
- D-17: Data collected: chess.com/lichess username, game data, Google email (if OAuth), email/hashed password
- D-18: Third-party processors: Sentry, Hetzner
- D-19: Right to deletion via support@flawchess.com
- D-20: Open source mention with link to GitHub

**Import queue (STAB-01)**
- D-21: All concurrent import jobs run simultaneously — no serialization of entire jobs
- D-22: Shared per-platform rate limiter throttles individual API calls across concurrent jobs
- D-23: Show info when multiple users importing: "X other users are importing from chess.com/lichess, it may take a while"
- D-24: 3-hour timeout per import job — mark failed with message "Import timed out — re-sync to continue where it left off"
- D-25: Partial completion handled naturally via incremental sync (already implemented)

**README (BRAND-05)**
- D-26: Professional README with description, feature highlights, screenshots, tech badges, setup instructions

### Claude's Discretion
- Homepage layout and visual design (spacing, sections, responsive behavior)
- FAQ accordion/collapse component choice
- Rate limiter implementation details (token bucket, sliding window, etc.)
- robots.txt and sitemap.xml serving mechanism (Caddy static files or backend endpoint)
- README structure and badge selection
- Privacy policy exact wording

### Deferred Ideas (OUT OF SCOPE)
- Analytics (MON-03) — Plausible or similar tracking deferred
- Cookie consent banner — not needed without analytics cookies
- Import status queue position UI (STAB-02)
- Durable import queue with ARQ + Redis (STAB-03)
- Account self-service deletion UI
- BRAND-04 (GitHub org transfer)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONT-01 | Public homepage at `/` explaining USP, features, FAQ, register CTA | Routing pattern identified; shadcn Card/Button/Accordion components confirmed available |
| CONT-02 | SEO: OG tags in index.html, robots.txt, sitemap.xml | Static file delivery via Vite public/ confirmed; OG tag structure documented |
| CONT-03 | Privacy policy page at `/privacy` | Public route pattern identical to homepage; content requirements locked |
| STAB-01 | Shared per-platform rate limiter for concurrent imports | asyncio.Semaphore at module level confirmed; integration points in chesscom_client and lichess_client identified |
| BRAND-05 | Professional README | No code changes; content documented |
| MON-03 | Analytics (DEFERRED) | Out of scope per CONTEXT.md |
</phase_requirements>

---

## Standard Stack

### Core (already in project — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React Router DOM | 7.13.1 | Public/protected route split | Already in use; `<Route>` outside `ProtectedLayout` is the standard pattern |
| shadcn/ui (Radix) | 1.4.3 | Card, Button, Accordion for homepage | Already installed; Accordion needs `npx shadcn add accordion` |
| Tailwind CSS | project standard | Responsive homepage layout | Already in use for all pages |
| asyncio.Semaphore | stdlib | Shared rate limiter | Zero-dependency; same event loop as the import tasks |

### New Component Needed

| Component | Install Command | Purpose |
|-----------|-----------------|---------|
| shadcn Accordion | `npx shadcn@latest add accordion` (run from `frontend/`) | FAQ collapsible sections |

**Verification:** The project uses `radix-ui ^1.4.3` (the unified package), and shadcn Accordion wraps `@radix-ui/react-accordion`. The `npx shadcn add` command generates `frontend/src/components/ui/accordion.tsx` — no separate npm install needed beyond what the unified radix-ui package provides.

### No New Backend Dependencies

The rate limiter is implemented with Python's standard `asyncio.Semaphore` — no new packages. The 3-hour timeout uses `asyncio.wait_for()` or `asyncio.timeout()` context manager (Python 3.11+, confirmed — project uses Python 3.13).

---

## Architecture Patterns

### Recommended Project Structure

**Frontend additions:**
```
frontend/
├── public/
│   ├── robots.txt          # NEW — served by Caddy as static file
│   ├── sitemap.xml         # NEW — served by Caddy as static file
│   └── og-image.jpg        # NEW — manual asset (user provides 1200x630)
├── src/
│   ├── pages/
│   │   ├── Home.tsx        # NEW — public homepage
│   │   └── Privacy.tsx     # NEW — public privacy policy
│   └── components/
│       └── layout/
│           └── PublicHeader.tsx  # NEW — header for public pages (logo + login btn)
```

**Backend additions:**
```
app/
├── core/
│   └── rate_limiters.py    # NEW — module-level asyncio.Semaphore instances
└── services/
    ├── chesscom_client.py  # MODIFIED — acquire semaphore before each archive fetch
    └── lichess_client.py   # MODIFIED — acquire semaphore for initial connection (streaming is one call)
```

### Pattern 1: Public Routes Outside ProtectedLayout

The current `App.tsx` places `/` inside `ProtectedLayout`. This must be restructured:

```tsx
// App.tsx — restructured routes
<Routes>
  {/* Public routes — no auth required */}
  <Route path="/" element={<HomePage />} />
  <Route path="/privacy" element={<PrivacyPage />} />
  <Route path="/login" element={<AuthPage />} />
  <Route path="/auth/callback" element={<OAuthCallbackPage />} />

  {/* Protected layout wraps all authenticated pages */}
  <Route element={<ProtectedLayout />}>
    <Route path="/import" element={<ImportPage ... />} />
    <Route path="/openings/*" element={<OpeningsPage />} />
    <Route path="/global-stats" element={<GlobalStatsPage />} />
    <Route path="/rating" element={<Navigate to="/global-stats" replace />} />
  </Route>

  {/* Catch-all — keep redirecting unknown routes */}
  <Route path="*" element={<Navigate to="/" replace />} />
</Routes>
```

**Critical change:** The `HomeRedirect` component and the `/` route inside `ProtectedLayout` are removed. Instead, `HomePage` handles the redirect itself: if `token` is present, render `<Navigate to="/openings" replace />` immediately. This avoids touching `ProtectedLayout` logic.

```tsx
// Home.tsx — simplified redirect logic
export function HomePage() {
  const { token } = useAuth();
  if (token) return <Navigate to="/openings" replace />;
  return <HomePageContent />;
}
```

### Pattern 2: Public Header for Unauthenticated Pages

The existing `NavHeader` in `App.tsx` is tightly coupled to authenticated state (uses `logout`, renders nav items). Homepage and privacy page need a separate minimal header:

```tsx
// PublicHeader.tsx
export function PublicHeader() {
  return (
    <header data-testid="public-header" className="border-b border-border bg-background px-6">
      <div className="mx-auto flex max-w-7xl items-center justify-between py-2">
        <Link to="/" className="flex items-center gap-1.5">
          <img src="/icons/logo-128.png" alt="" className="h-10 w-10" aria-hidden="true" />
          <span className="text-lg tracking-tight font-brand">FlawChess</span>
        </Link>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" asChild data-testid="nav-login">
            <Link to="/login">Log in</Link>
          </Button>
          <Button size="sm" asChild data-testid="nav-signup">
            <Link to="/login?tab=register">Sign up free</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
```

### Pattern 3: Shared Per-Platform asyncio.Semaphore

The rate limiter is module-level so it persists across all concurrent `asyncio.create_task()` jobs:

```python
# app/core/rate_limiters.py
import asyncio

# Limits concurrent outbound archive fetches to chess.com across ALL users.
# Community-reported threshold: ~3-4 concurrent requests triggers 429s.
# Semaphore value of 2 provides headroom. Tune post-launch via CHESSCOM_SEMAPHORE_LIMIT.
CHESSCOM_SEMAPHORE_LIMIT = 2
LICHESS_SEMAPHORE_LIMIT = 3  # Lichess is more permissive; streaming is one connection per job

_chesscom_semaphore: asyncio.Semaphore | None = None
_lichess_semaphore: asyncio.Semaphore | None = None


def get_chesscom_semaphore() -> asyncio.Semaphore:
    global _chesscom_semaphore
    if _chesscom_semaphore is None:
        _chesscom_semaphore = asyncio.Semaphore(CHESSCOM_SEMAPHORE_LIMIT)
    return _chesscom_semaphore


def get_lichess_semaphore() -> asyncio.Semaphore:
    global _lichess_semaphore
    if _lichess_semaphore is None:
        _lichess_semaphore = asyncio.Semaphore(LICHESS_SEMAPHORE_LIMIT)
    return _lichess_semaphore
```

**Integration in chesscom_client.py** — wrap each archive fetch (the per-month HTTP call):

```python
# Inside the `for archive_url in archive_urls:` loop in fetch_chesscom_games()
async with get_chesscom_semaphore():
    await asyncio.sleep(0.15)  # keep existing delay
    resp = await client.get(archive_url, headers=_HEADERS)
    # ... rest of existing logic
```

**Integration in lichess_client.py** — wrap the streaming call itself (one connection per job):

```python
# lichess streams in one HTTP connection — wrap the outer async with
async with get_lichess_semaphore():
    async with client.stream("GET", url, params=params, headers=headers, timeout=300.0) as response:
        # ... existing streaming logic
```

### Pattern 4: Job Timeout with asyncio.timeout()

Python 3.13 has `asyncio.timeout()` (added in 3.11). Wrap `run_import()` body:

```python
# import_service.py — inside run_import(), wrap the main try block
IMPORT_TIMEOUT_SECONDS = 3 * 60 * 60  # 3 hours

async def run_import(job_id: str) -> None:
    job = _jobs.get(job_id)
    if job is None:
        return
    job.status = JobStatus.IN_PROGRESS
    try:
        async with asyncio.timeout(IMPORT_TIMEOUT_SECONDS):
            # ... existing import logic
    except TimeoutError:
        job.status = JobStatus.FAILED
        job.error = "Import timed out — re-sync to continue where it left off"
        # best-effort DB update (same pattern as existing except block)
    except Exception as exc:
        # ... existing exception handling
```

`asyncio.timeout()` raises `TimeoutError` (not `asyncio.TimeoutError` — they unified in 3.11). The existing `except Exception` block would catch it, so `TimeoutError` must be caught first.

### Pattern 5: Concurrent Importer Count API

Decision D-23 requires showing "X other users are importing from chess.com". The count comes from the in-memory `_jobs` registry:

```python
# import_service.py — new function
def count_active_platform_jobs(platform: str, exclude_user_id: int) -> int:
    """Return count of active jobs for a platform from other users (not the requesting user)."""
    return sum(
        1 for job in _jobs.values()
        if job.platform == platform
        and job.status in (JobStatus.PENDING, JobStatus.IN_PROGRESS)
        and job.user_id != exclude_user_id
    )
```

Expose via the existing `GET /imports/{job_id}` response or a new field in `ImportStatusResponse`. The frontend can show the message when `other_importers > 0`.

**Simpler alternative:** Expose count as a field in `ImportStatusResponse` — the frontend already polls job status every 2 seconds, so it naturally picks up the count.

### Pattern 6: Static Files (robots.txt, sitemap.xml)

The existing Caddyfile uses `@static file` — any file that exists on disk at `/srv` is served directly before the SPA fallback:

```
@static file
handle @static {
    root * /srv
    file_server
}
```

Files placed in `frontend/public/` are copied to `/srv` during the Vite build. **No Caddyfile change needed.** Just create the files:

```
frontend/public/robots.txt
frontend/public/sitemap.xml
```

### Pattern 7: Open Graph Meta Tags in index.html

Static OG tags go directly in `frontend/index.html` `<head>`. No library needed (D-09):

```html
<title>FlawChess — Chess Opening Analysis</title>
<meta name="description" content="Analyze your chess openings by position, not just name. Import games from chess.com and lichess to discover where you really lose." />

<!-- Open Graph -->
<meta property="og:title" content="FlawChess — Chess Opening Analysis" />
<meta property="og:description" content="Analyze your chess openings by position, not just name. Import games from chess.com and lichess to discover where you really lose." />
<meta property="og:image" content="https://flawchess.com/og-image.jpg" />
<meta property="og:url" content="https://flawchess.com/" />
<meta property="og:type" content="website" />

<!-- Twitter/X Card -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:image" content="https://flawchess.com/og-image.jpg" />
```

**Note on SPA + social crawlers:** Social media crawlers (Facebook, Twitter, LinkedIn, Slack) fetch raw HTML and cannot execute JavaScript. Static OG tags in `index.html` are visible to all crawlers without SSR because they're in the static HTML shell. This is the correct approach for a React SPA where only the root URL needs to be shared — the decision to skip SSR is appropriate given only `/` and `/privacy` need indexing.

### Anti-Patterns to Avoid

- **Don't put the semaphore inside the client function as a local variable.** It must be module-level so all concurrent jobs share the same instance.
- **Don't use `asyncio.wait_for(run_import(job_id), timeout=...)` at the call site.** The task is already scheduled via `asyncio.create_task()`. Wrap `asyncio.timeout()` inside `run_import()` itself.
- **Don't use a `<head>` management library** (react-helmet, etc.) — D-09 locks to static tags in `index.html`.
- **Don't serve robots.txt/sitemap.xml from a FastAPI endpoint.** Caddy static file serving is simpler and doesn't add API surface.
- **Don't add public routes inside `ProtectedLayout`.** `ProtectedLayout` redirects unauthenticated users to `/login` — placing public routes there breaks unauthenticated access.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FAQ collapsible UI | Custom toggle logic | shadcn Accordion (`npx shadcn add accordion`) | Keyboard accessible, animated, already styled to project theme |
| Rate limiting | Token bucket from scratch | `asyncio.Semaphore` (stdlib) | Correct semantics for cooperative async, zero deps |
| Job timeout | Manual timestamp comparison | `asyncio.timeout()` (stdlib, Python 3.11+) | Proper cancellation propagation, clean error handling |
| OG tag injection | react-helmet or dynamic JS | Static `<meta>` in index.html | Crawlers can't run JS; static tags work correctly |
| robots.txt HTTP endpoint | FastAPI route | Vite `public/` static file | Caddy already serves public/ files; no code needed |

---

## Common Pitfalls

### Pitfall 1: Semaphore Created Outside Event Loop
**What goes wrong:** If `asyncio.Semaphore()` is called at module import time (top-level, before `uvicorn` starts the event loop), Python 3.10+ warns or errors depending on context.
**Why it happens:** Semaphores are tied to the running event loop. Module-level initialization at import time happens before `uvicorn` creates its event loop.
**How to avoid:** Use lazy initialization (as in Pattern 3 above) — create the Semaphore on first call inside a running coroutine, not at module import. Alternatively, create in `app/main.py` `lifespan` event and store in app state.
**Warning signs:** `DeprecationWarning: There is no current event loop` at startup.

### Pitfall 2: TimeoutError Swallowed by Broad Exception Handler
**What goes wrong:** The existing `except Exception` in `run_import()` will catch `TimeoutError` before any dedicated timeout handler, writing a confusing error message.
**Why it happens:** `TimeoutError` is a subclass of `Exception` in Python 3.11+.
**How to avoid:** Catch `TimeoutError` specifically before `Exception` in the try/except chain.

### Pitfall 3: Catch-All Route Redirecting to `/openings` Instead of `/`
**What goes wrong:** The current catch-all `<Route path="*" element={<Navigate to="/openings" replace />} />` sends unknown routes to `/openings`, which requires auth and causes a redirect loop for unauthenticated users.
**Why it happens:** With the new public homepage, the correct catch-all destination for unknown routes is `/` (the public homepage), not an authenticated page.
**How to avoid:** Change catch-all to redirect to `/`.

### Pitfall 4: Semaphore Blocking Lichess Streaming Unnecessarily
**What goes wrong:** If the lichess semaphore is held for the entire streaming duration (potentially hours), it blocks all other users' lichess imports while streaming completes.
**Why it happens:** Lichess is one long HTTP stream, not multiple short calls. Holding the semaphore for the full stream defeats the purpose.
**How to avoid:** For lichess, the semaphore protects concurrent *connections*, not streaming duration. The semaphore limit of 3 means at most 3 users can be streaming from lichess simultaneously. This is the intended behavior per D-22 ("more users = each progresses slower"). Document this clearly in code.

### Pitfall 5: og:image Path Must be Absolute URL
**What goes wrong:** Setting `og:image` to a relative path like `/og-image.jpg` — Facebook and some crawlers require an absolute URL.
**Why it happens:** OG spec requires absolute URLs for `og:image`.
**How to avoid:** Use `https://flawchess.com/og-image.jpg` as the value.

### Pitfall 6: sitemap.xml Needs Correct XML Declaration and Namespace
**What goes wrong:** Sitemap without correct xmlns causes Google Search Console warnings.
**How to avoid:** Use standard format:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://flawchess.com/</loc></url>
  <url><loc>https://flawchess.com/privacy</loc></url>
</urlset>
```

### Pitfall 7: D-23 Count Includes Current User's Own Jobs
**What goes wrong:** Showing "1 other user importing" when the count actually includes the current user's own job.
**How to avoid:** The `count_active_platform_jobs()` function must exclude `job.user_id == requesting_user_id`.

---

## Code Examples

### robots.txt content
```
User-agent: *
Allow: /
Allow: /privacy
Disallow: /import
Disallow: /openings
Disallow: /global-stats
Disallow: /api/

Sitemap: https://flawchess.com/sitemap.xml
```

### asyncio.Semaphore lazy initialization (confirmed Python 3.13 compatible)
```python
# Source: Python stdlib asyncio documentation
import asyncio

_semaphore: asyncio.Semaphore | None = None

def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(2)
    return _semaphore
```

### asyncio.timeout() usage (Python 3.11+)
```python
# Source: Python 3.11+ stdlib docs
import asyncio

try:
    async with asyncio.timeout(10800):  # 3 hours
        await long_running_task()
except TimeoutError:
    # handle timeout
    pass
```

### shadcn Accordion for FAQ
```tsx
// After: npx shadcn@latest add accordion (run from frontend/)
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';

<Accordion type="single" collapsible data-testid="faq-accordion">
  <AccordionItem value="data" data-testid="faq-item-data">
    <AccordionTrigger>What data do you access from my chess.com/lichess account?</AccordionTrigger>
    <AccordionContent>Only your games — no passwords or personal information.</AccordionContent>
  </AccordionItem>
</Accordion>
```

---

## Validation Architecture

`nyquist_validation` is enabled in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, asyncio_mode=auto) |
| Quick run command | `uv run pytest tests/test_import_service.py tests/test_imports_router.py -x` |
| Full suite command | `uv run pytest` (313 tests collected) |

Frontend has no automated test framework configured — manual browser verification is the test mechanism for homepage/privacy UI.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| STAB-01 | Semaphore limits concurrent chess.com archive fetches | unit | `uv run pytest tests/test_chesscom_client.py -x` | ✅ (extend) |
| STAB-01 | Semaphore limits concurrent lichess connections | unit | `uv run pytest tests/test_lichess_client.py -x` | ✅ (extend) |
| STAB-01 | 3-hour timeout marks job as failed with correct message | unit | `uv run pytest tests/test_import_service.py -x` | ✅ (extend) |
| STAB-01 | D-23 count excludes requesting user's own jobs | unit | `uv run pytest tests/test_import_service.py -x` | ✅ (extend) |
| CONT-01 | `/` returns 200 for unauthenticated request | smoke | manual browser / curl | N/A |
| CONT-02 | `robots.txt` served at correct path | smoke | `curl https://flawchess.com/robots.txt` | N/A |
| CONT-02 | `sitemap.xml` served at correct path | smoke | `curl https://flawchess.com/sitemap.xml` | N/A |
| CONT-03 | `/privacy` accessible without auth | smoke | manual browser | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_import_service.py tests/test_chesscom_client.py tests/test_lichess_client.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- None for backend — existing test files cover all modules being modified
- Frontend has no test framework — UI verification is manual-only (acceptable per project pattern)

---

## Integration Points Summary

| File | Change Type | What Changes |
|------|-------------|--------------|
| `frontend/src/App.tsx` | MODIFY | Move `/` out of `ProtectedLayout`; add `/privacy`; change catch-all to `/`; remove `HomeRedirect` |
| `frontend/src/pages/Home.tsx` | CREATE | Public homepage component |
| `frontend/src/pages/Privacy.tsx` | CREATE | Privacy policy page |
| `frontend/src/components/layout/PublicHeader.tsx` | CREATE | Header with logo + login/signup buttons for public pages |
| `frontend/src/components/ui/accordion.tsx` | CREATE | Via `npx shadcn@latest add accordion` |
| `frontend/index.html` | MODIFY | Add `<title>`, `<meta description>`, OG tags |
| `frontend/public/robots.txt` | CREATE | Static file |
| `frontend/public/sitemap.xml` | CREATE | Static file |
| `frontend/public/og-image.jpg` | CREATE | Manual asset (user provides) |
| `app/core/rate_limiters.py` | CREATE | Module-level semaphore instances |
| `app/services/chesscom_client.py` | MODIFY | Acquire semaphore per archive fetch |
| `app/services/lichess_client.py` | MODIFY | Acquire semaphore per streaming connection |
| `app/services/import_service.py` | MODIFY | Add timeout wrapper; add `count_active_platform_jobs()` |
| `app/schemas/imports.py` | MODIFY | Add `other_importers: int` field to `ImportStatusResponse` |
| `app/routers/imports.py` | MODIFY | Populate `other_importers` count in status response |
| `README.md` | MODIFY | Full rewrite with badges, features, screenshots, setup |
| `deploy/Caddyfile` | NO CHANGE | Existing `@static file` matcher already serves public/ files |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `asyncio.wait_for()` for timeouts | `asyncio.timeout()` context manager | Python 3.11 | Cleaner syntax, same semantics |
| `asyncio.TimeoutError` | `TimeoutError` (builtin) | Python 3.11 | They are the same type now |
| react-helmet for meta tags | Static `<meta>` in index.html | 2023+ consensus for SPAs with limited public pages | No JS dependency, crawler-safe |

---

## Open Questions

1. **Semaphore initial limit values**
   - What we know: chess.com community reports 3-4 concurrent requests triggers 429s (unverified). Lichess is more permissive but has per-IP rate limits.
   - What's unclear: Exact safe concurrency limits for both platforms under production load.
   - Recommendation: Start conservative (chess.com: 2, lichess: 3). Extract as named constants so they can be tuned post-launch without code change.

2. **og-image.jpg placeholder during development**
   - What we know: User will provide the final 1200x630 asset.
   - What's unclear: Whether a placeholder should be committed so meta tags reference a real file.
   - Recommendation: Commit a 1x1px placeholder at the correct path so the build doesn't have a broken reference. The planner should note this as a task with "(awaiting asset from user)".

3. **D-23 frontend display placement**
   - What we know: The message "X other users importing" should appear on the Import page.
   - What's unclear: Whether it shows for each platform separately or as a combined count.
   - Recommendation: Per-platform — "2 other users are importing from chess.com" is more useful than a combined count.

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `App.tsx`, `import_service.py`, `chesscom_client.py`, `lichess_client.py`, `app/core/config.py`, `app/schemas/imports.py`, `app/routers/imports.py`, `deploy/Caddyfile`, `frontend/index.html`, `frontend/public/` directory
- Python 3.13 stdlib asyncio — `asyncio.Semaphore`, `asyncio.timeout()` confirmed available
- `.planning/phases/23-launch-readiness/23-CONTEXT.md` — all decisions read verbatim

### Secondary (MEDIUM confidence)
- WebSearch: asyncio.Semaphore patterns for shared rate limiting across concurrent tasks
- WebSearch: React Router v7 public/protected route patterns
- WebSearch: OG tags in static SPAs — confirmed static approach is correct for crawlers

### Tertiary (LOW confidence)
- Community-reported chess.com rate-limit threshold of 3-4 concurrent requests — unverified; flagged in Open Questions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project; confirmed via package.json and pyproject.toml
- Architecture patterns: HIGH — based on direct code reading of integration points
- Rate limiter: HIGH — asyncio.Semaphore is stdlib, pattern well-established
- Pitfalls: HIGH — derived from direct code inspection and known Python asyncio behavior
- Semaphore limits: LOW — community-reported, unverified

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable ecosystem; no fast-moving dependencies)
