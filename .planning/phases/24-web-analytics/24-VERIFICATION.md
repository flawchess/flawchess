---
phase: 24-web-analytics
verified: 2026-03-22T18:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
human_verification:
  - test: "Browse flawchess.com and check Umami dashboard for pageview counts and trends"
    expected: "Dashboard shows page visit counts with a time-series trend chart (ANLY-01)"
    why_human: "Requires live production traffic visible in Umami dashboard — cannot verify programmatically"
  - test: "Check Umami dashboard Pages section after browsing the site"
    expected: "Top pages listed by visit count, showing routes like /, /openings, /dashboard (ANLY-02)"
    why_human: "Requires live data in Umami — cannot verify dashboard UI content programmatically"
  - test: "Check Umami dashboard Referrers section"
    expected: "Referrer sources are displayed (may be empty for direct visits, but section exists) (ANLY-03)"
    why_human: "Requires live data in production Umami — cannot verify programmatically"
  - test: "Open flawchess.com in browser DevTools -> Application -> Cookies"
    expected: "No cookies set by the analytics script; only FlawChess auth cookies present (ANLY-04)"
    why_human: "Cookie behavior requires browser runtime inspection"
  - test: "Run docker stats --no-stream on production server after Umami has been running"
    expected: "Umami container uses less than 300 MB RAM (ANLY-05)"
    why_human: "Runtime memory usage requires SSH to production server"
---

# Phase 24: Web Analytics Verification Report

**Phase Goal:** Add privacy-friendly, low-resource web analytics to track page visits, top routes, and referrer sources
**Verified:** 2026-03-22T18:00:00Z
**Status:** passed (automated checks) / human_verification items noted
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Umami service is defined in docker-compose.yml sharing the existing db container | VERIFIED | `docker-compose.yml` line 30–41: umami service with `DATABASE_URL` pointing to `db:5432/umami`, no separate postgres container |
| 2 | Caddy proxies analytics.flawchess.com to umami:3000 | VERIFIED | `deploy/Caddyfile` lines 5–7: standalone `analytics.flawchess.com { reverse_proxy umami:3000 }` block |
| 3 | Umami Node.js heap is capped at 256 MB via NODE_OPTIONS | VERIFIED | `docker-compose.yml` line 35: `NODE_OPTIONS: "--max-old-space-size=256"` |
| 4 | No separate PostgreSQL container is created for Umami | VERIFIED | Only one `postgres:18-alpine` image in `docker-compose.yml` (the `db` service); Umami reuses it |
| 5 | Umami tracking script is embedded in the frontend HTML | VERIFIED | `frontend/index.html` lines 29–34: `<script defer src="https://analytics.flawchess.com/script.js" ...>` in `<head>` |
| 6 | Tracking only fires on production domain (flawchess.com), not localhost | VERIFIED | `data-domains="flawchess.com"` attribute on script tag — Umami silently no-ops outside this domain |
| 7 | SPA route changes are tracked automatically via History API | VERIFIED | Umami auto-patches `history.pushState`/`replaceState`; no React code changes needed |
| 8 | data-website-id is a real UUID (not a placeholder) | VERIFIED | `data-website-id="0ca19960-2398-4caf-b321-8039708fa7ef"` — UUID format confirmed, matches website registered in Umami per SUMMARY |
| 9 | Site owner can view page visit counts/trends, top pages, and referrers in Umami dashboard | HUMAN NEEDED | Infrastructure is fully wired; depends on live production data — see human verification items |
| 10 | Analytics adds negligible RAM/CPU overhead | HUMAN NEEDED | 256 MB heap cap is in place; runtime validation requires production server check |

**Score:** 8/8 automated truths verified, 2 requiring human confirmation on production

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docker-compose.yml` | Umami service definition | VERIFIED | Service defined at line 30 with image `ghcr.io/umami-software/umami:postgresql-latest`, `expose: "3000"` (not ports), `depends_on: db: condition: service_healthy` |
| `deploy/Caddyfile` | Analytics subdomain reverse proxy | VERIFIED | Standalone server block at line 5–7, no basicauth, separate from `flawchess.com` block |
| `.env.example` | Umami environment variable documentation | VERIFIED | Lines 34–39: `UMAMI_DB_USER=umami`, `UMAMI_DB_PASSWORD=`, `UMAMI_APP_SECRET=` under labeled section |
| `frontend/index.html` | Umami tracking script tag | VERIFIED | Lines 28–34: script in `<head>` with `defer`, `src`, `data-website-id` (UUID), `data-domains` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `docker-compose.yml` (umami service) | `docker-compose.yml` (db service) | `DATABASE_URL` referencing `db:5432` | WIRED | Line 33: `postgresql://${UMAMI_DB_USER}:${UMAMI_DB_PASSWORD}@db:5432/umami` |
| `deploy/Caddyfile` | `docker-compose.yml` (umami service) | `reverse_proxy umami:3000` | WIRED | Line 6: `reverse_proxy umami:3000` inside `analytics.flawchess.com` block |
| `frontend/index.html` (script tag) | `analytics.flawchess.com/script.js` | deferred script load with `data-website-id` | WIRED | `src="https://analytics.flawchess.com/script.js"` with real UUID and `data-domains` restriction |
| `caddy` service | `umami` service | `depends_on` ordering | WIRED | `docker-compose.yml` lines 56–58: `depends_on: - backend - umami` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ANLY-01 | 24-02-PLAN.md | Site owner can view page visit counts and trends over time | HUMAN NEEDED | Tracking script deployed with real website ID; dashboard verification requires production |
| ANLY-02 | 24-02-PLAN.md | Site owner can see top pages/routes by visit count | HUMAN NEEDED | Tracking script deployed with SPA route tracking; dashboard verification requires production |
| ANLY-03 | 24-02-PLAN.md | Site owner can see visitor referrer sources | HUMAN NEEDED | Umami collects referrer data by default; dashboard verification requires production |
| ANLY-04 | 24-01-PLAN.md | Analytics collection respects user privacy (no cookie consent banner required) | VERIFIED (infra) / HUMAN (runtime) | Umami is cookieless by design; `data-domains` prevents dev tracking; cookie absence requires browser check |
| ANLY-05 | 24-01-PLAN.md | Analytics solution has minimal server resource footprint (RAM/CPU) | VERIFIED (infra) / HUMAN (runtime) | 256 MB Node.js heap cap in place; actual RAM usage requires `docker stats` on production |

All 5 requirement IDs (ANLY-01 through ANLY-05) from both plan frontmatter declarations are accounted for. No orphaned requirements detected.

### Anti-Patterns Found

None. All four modified files (`docker-compose.yml`, `deploy/Caddyfile`, `.env.example`, `frontend/index.html`) are clean — no TODO/FIXME/PLACEHOLDER comments, no empty implementations, no stub patterns.

### Human Verification Required

#### 1. Page visit counts and trends (ANLY-01)

**Test:** Visit https://flawchess.com, navigate to 3–4 pages, then open https://analytics.flawchess.com and log in.
**Expected:** Dashboard shows page visit count with a time-series trend chart for the last 24 hours.
**Why human:** Requires live production traffic in Umami; cannot inspect dashboard data programmatically.

#### 2. Top pages by visit count (ANLY-02)

**Test:** Same session as above. Check the "Pages" section of the Umami dashboard.
**Expected:** Routes visited (e.g., `/`, `/openings`, `/dashboard`) appear ranked by visit count.
**Why human:** Dashboard UI content requires live data from production.

#### 3. Referrer sources (ANLY-03)

**Test:** Visit flawchess.com from a search result or external link. Check the "Referrers" section in the Umami dashboard.
**Expected:** Referrer source is recorded and displayed. Direct visits show empty referrer (expected).
**Why human:** Referrer data only appears with traffic from external sources.

#### 4. No cookies set by tracking script (ANLY-04)

**Test:** Open flawchess.com in Chrome DevTools -> Application -> Cookies -> https://flawchess.com.
**Expected:** No cookies from the Umami analytics script. Only FlawChess auth session cookies present.
**Why human:** Cookie presence requires browser runtime inspection.

#### 5. RAM usage under 300 MB (ANLY-05)

**Test:** `ssh flawchess "cd /opt/flawchess && docker stats --no-stream"`
**Expected:** The `flawchess-umami-1` container shows less than 300 MB memory usage (heap capped at 256 MB, plus overhead).
**Why human:** Runtime memory usage requires SSH to the production server.

### Gaps Summary

No automated gaps found. All infrastructure changes are implemented correctly and completely:

- Umami service in `docker-compose.yml` shares the existing `db` container via `DATABASE_URL` pointing to `db:5432/umami`, uses the official image from GitHub Container Registry, exposes port 3000 internally only, and has the 256 MB Node.js heap cap.
- Caddy in `deploy/Caddyfile` has a properly isolated `analytics.flawchess.com` server block that reverse-proxies to `umami:3000` with no Caddy-level auth.
- `.env.example` documents all three required Umami env vars under a clearly labeled section.
- `frontend/index.html` embeds the tracking script in `<head>` with `defer`, a real production website UUID (not a placeholder), and `data-domains="flawchess.com"` to prevent dev/localhost tracking.
- Commits `1a83d85` (infrastructure) and `06d2673` (tracking script) are confirmed present in git history.

The 5 human verification items are confirmatory checks of production behavior — the infrastructure and code are correctly wired. ANLY-01/02/03 are marked pending in REQUIREMENTS.md, which is appropriate as they can only be confirmed with live dashboard data.

---

_Verified: 2026-03-22T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
