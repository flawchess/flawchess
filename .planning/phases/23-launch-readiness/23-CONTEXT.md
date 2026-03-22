# Phase 23: Launch Readiness - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Public homepage, SEO fundamentals, privacy policy, import rate-limit protection, and polished README. Analytics (Plausible/GA) deferred — not shipping in this phase. No new app features, no UI changes to existing authenticated pages.

</domain>

<decisions>
## Implementation Decisions

### Homepage (replaces About page — CONT-01)
- **D-01:** `/` is the public homepage for unauthenticated visitors; authenticated users auto-redirect to `/openings`
- **D-02:** No separate `/about` route — the homepage IS the about page
- **D-03:** 5 headline feature sections, each with heading + short description:
  1. **Find weaknesses in your openings** — Discover which moves you struggle against, which gambits work for you, and how your repertoire performs at different rating levels
  2. **Scout your opponents** — Prepare for a match by exploring their opening weaknesses and tendencies
  3. **Interactive move explorer** — Step through any position and see your win/draw/loss rate for every move you've played
  4. **Cross-platform analysis** — Import games from chess.com and lichess into one place — analyze your complete history regardless of platform
  5. **Powerful filters** — Slice your games by time control, rating range, color, opponent type, and time period to find exactly the patterns you're looking for
- **D-04:** One prominent "Sign up free" CTA button; login button in the header
- **D-05:** 1-2 screenshots of the UI (manual asset — user will provide)
- **D-06:** Tagline on the page: "Engines are flawless, humans play FlawChess"
- **D-07:** "Open source and free" and "Mobile friendly" as smaller callouts, not headline features
- **D-08:** FAQ section on homepage:
  - "What data do you access from my chess.com/lichess account?" — just games, no passwords
  - "Is it free?" — yes, free to use
  - "Can I use it on mobile?" — yes, installable PWA
  - "Where can I make feature requests?" — GitHub link
  - "Who develops this?" — link to flawchess/flawchess GitHub org, contributions/feedback/feature requests welcome, support@flawchess.com

### SEO (CONT-02)
- **D-09:** Static meta tags in `index.html` — no head management library
- **D-10:** `<title>`: "FlawChess — Chess Opening Analysis" (SEO-functional)
- **D-11:** Open Graph image: screenshot of UI with FlawChess logo on top (1200x630px, manual asset — user will provide, referenced in meta tags)
- **D-12:** `robots.txt` allowing `/` and `/privacy`, disallowing everything else
- **D-13:** `sitemap.xml` with just `/` and `/privacy`
- **D-14:** Privacy page title: "Privacy Policy | FlawChess"

### Privacy policy (CONT-03)
- **D-15:** Plain language, not legalese — clear sections ("What we collect", "Who we share it with", "Your rights")
- **D-16:** Route: `/privacy` — public, no auth required
- **D-17:** Data collected:
  - Chess.com/lichess username (public, entered by user)
  - Game data imported from those platforms (publicly available via their APIs)
  - Google account email (if using Google SSO)
  - Email/password if using email registration (hashed, never stored plain)
- **D-18:** Third-party processors:
  - Sentry (error monitoring — may capture IP, browser info in error reports)
  - Hetzner (hosting — server in EU/Germany)
- **D-19:** "Right to deletion" section — contact support@flawchess.com to request account deletion
- **D-20:** Mention open source — users can verify data handling by reading the code, link to flawchess/flawchess GitHub

### Import queue (STAB-01)
- **D-21:** All concurrent import jobs run simultaneously — no serialization/queuing of entire jobs
- **D-22:** Shared per-platform rate limiter throttles individual API calls across all concurrent jobs — more users importing = each progresses slower, but nobody waits idle
- **D-23:** When multiple users are importing, show info: "X other users are importing their games from chess.com/lichess, it may take a while"
- **D-24:** 3-hour timeout per import job — mark as failed with message "Import timed out — re-sync to continue where it left off"
- **D-25:** Partial completion handled naturally: batches are persisted as they complete, `last_synced_at` tracked per username, re-import picks up where it left off

### README (BRAND-05)
- **D-26:** Professional README with project description, feature highlights, screenshots (from live site), tech badges, local setup instructions

### Claude's Discretion
- Homepage layout and visual design (spacing, sections, responsive behavior)
- FAQ accordion/collapse component choice
- Rate limiter implementation details (token bucket, sliding window, etc.)
- robots.txt and sitemap.xml serving mechanism (Caddy static files or backend endpoint)
- README structure and badge selection
- Privacy policy exact wording

</decisions>

<specifics>
## Specific Ideas

- Homepage tagline: "Engines are flawless, humans play FlawChess"
- The homepage should make it immediately clear what FlawChess does and why someone should sign up — the current login page gives zero context
- Feature descriptions position FlawChess as an improved OpeningTree.com — focus on openings analysis, not global stats
- System openings / own-piece-placement filter is a differentiator but niche — fold into move explorer or filters description
- Privacy policy should feel honest and readable, not corporate

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — CONT-01 (About/homepage), CONT-02 (SEO), CONT-03 (privacy policy), STAB-01 (import queue), BRAND-05 (README)

### Frontend routing and layout
- `frontend/src/App.tsx` — Current route definitions, `ProtectedLayout` wrapper, `HomeRedirect` component (needs rework for public homepage)
- `frontend/src/components/layout/NavHeader.tsx` — Header component (login button goes here for unauthenticated visitors)

### Import pipeline
- `app/services/import_service.py` — Current import orchestration, `_jobs` registry, batch processing, `_BATCH_SIZE = 50`
- `app/routers/imports.py` — Import API endpoints, `asyncio.create_task()` launch point
- `app/services/chesscom_client.py` — chess.com API calls with rate-limit delays
- `app/services/lichess_client.py` — lichess NDJSON streaming

### Existing infrastructure
- `frontend/index.html` — Current meta tags (needs OG tags, description)
- `deploy/Caddyfile` — Static file serving config (robots.txt/sitemap.xml serving)
- `.env.example` — Environment variable template

### Prior phase context
- `.planning/phases/22-ci-cd-monitoring/22-CONTEXT.md` — CI/CD and Sentry decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ProtectedLayout` in `App.tsx` — wraps authenticated pages; homepage and privacy page need a separate public layout or no layout wrapper
- `NavHeader` / `MobileHeader` / `MobileBottomBar` — existing nav components; header needs conditional rendering for unauthenticated visitors (show login button, hide app nav)
- shadcn/ui components — Accordion for FAQ, Card for feature sections, Button for CTA
- `import_service.py` batch processing — already persists incrementally, natural partial-completion support

### Established Patterns
- React Router v7 with `BrowserRouter` — add public routes outside `ProtectedLayout`
- Pydantic BaseSettings for config — rate limiter constants can go in `app/core/config.py`
- Tailwind CSS + responsive breakpoints — homepage must be mobile-friendly per project constraints

### Integration Points
- `App.tsx` routing — new public routes for `/` (homepage) and `/privacy`
- `index.html` — static OG meta tags and description
- `import_service.py` — add shared rate limiter wrapping outbound API calls
- `Caddyfile` — serve `robots.txt` and `sitemap.xml` as static files from frontend build

</code_context>

<deferred>
## Deferred Ideas

- **Analytics (MON-03)** — Plausible or similar tracking deferred until there's user interest to justify it
- **Cookie consent banner** — not needed without analytics cookies; revisit if tracking is added
- **Import status queue position UI (STAB-02)** — showing queue position and estimated wait time
- **Durable import queue with ARQ + Redis (STAB-03)** — replacing asyncio-based rate limiter
- **Account self-service deletion** — currently manual via support email; could add UI later
- **BRAND-04 (GitHub org transfer)** — not in this phase, tracked separately

</deferred>

---

*Phase: 23-launch-readiness*
*Context gathered: 2026-03-22*
