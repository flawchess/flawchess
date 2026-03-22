---
phase: 24-web-analytics
plan: 01
subsystem: infra
tags: [umami, analytics, docker, caddy, postgresql]

# Dependency graph
requires:
  - phase: 23-launch
    provides: Docker Compose stack and Caddyfile that this extends
provides:
  - Umami self-hosted analytics service in Docker Compose sharing existing PostgreSQL
  - analytics.flawchess.com reverse proxy via Caddy with auto-TLS
  - Environment variable documentation for Umami credentials
affects: [24-web-analytics plan 02, future infra phases]

# Tech tracking
tech-stack:
  added: [umami (ghcr.io/umami-software/umami:postgresql-latest)]
  patterns:
    - Umami shares existing db service via DATABASE_URL pointing to db:5432/umami
    - Internal-only services use expose not ports; Caddy is sole internet-facing entry point
    - NODE_OPTIONS max-old-space-size caps Node.js heap for resource-constrained VPS

key-files:
  created: []
  modified:
    - docker-compose.yml
    - deploy/Caddyfile
    - .env.example

key-decisions:
  - "Umami connects to existing db service (no separate PostgreSQL container) per D-02"
  - "Node.js heap capped at 256 MB via NODE_OPTIONS to guard VPS memory (3.7 GB RAM + 2 GB swap)"
  - "No Caddy-level auth on analytics subdomain — Umami handles its own login per D-04/D-05"
  - "caddy service depends_on umami to ensure Umami is available before Caddy accepts traffic"

patterns-established:
  - "Analytics subdomain as separate Caddyfile server block for clean TLS isolation"

requirements-completed: [ANLY-04, ANLY-05]

# Metrics
duration: 5min
completed: 2026-03-22
---

# Phase 24 Plan 01: Web Analytics Infrastructure Summary

**Umami analytics service added to Docker Compose sharing existing PostgreSQL, proxied via Caddy at analytics.flawchess.com with 256 MB Node.js heap cap**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-22T17:20:00Z
- **Completed:** 2026-03-22T17:21:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added Umami service to docker-compose.yml connected to existing db container (no separate DB)
- Added analytics.flawchess.com server block to Caddyfile for auto-TLS reverse proxy to umami:3000
- Documented UMAMI_DB_USER, UMAMI_DB_PASSWORD, UMAMI_APP_SECRET in .env.example

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Umami service to Docker Compose and update .env.example** - `e9a11ff` (feat)
2. **Task 2: Add analytics subdomain to Caddyfile** - `b699dec` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `docker-compose.yml` - Added umami service with shared db, 256 MB heap cap, and updated caddy depends_on
- `deploy/Caddyfile` - Added analytics.flawchess.com server block with reverse_proxy to umami:3000
- `.env.example` - Added Umami analytics section with UMAMI_DB_USER, UMAMI_DB_PASSWORD, UMAMI_APP_SECRET

## Decisions Made

- Umami shares existing db PostgreSQL container — no new container added, matching decision D-02
- NODE_OPTIONS set to --max-old-space-size=256 to guard memory on the resource-constrained VPS
- No basicauth on Caddy level — Umami has built-in login, first run creates default admin account
- caddy depends_on includes umami so Caddy does not start before Umami is available

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

Before deploying to production, the operator must:

1. Create the `umami` PostgreSQL database and user:
   ```sql
   CREATE USER umami WITH PASSWORD '<UMAMI_DB_PASSWORD>';
   CREATE DATABASE umami OWNER umami;
   ```
2. Set the following in `/opt/flawchess/.env` on the server:
   - `UMAMI_DB_USER=umami`
   - `UMAMI_DB_PASSWORD=<generated with openssl rand -hex 16>`
   - `UMAMI_APP_SECRET=<generated with openssl rand -hex 32>`
3. Add DNS A record: `analytics.flawchess.com` pointing to the server IP
4. Deploy and verify: `https://analytics.flawchess.com` should show Umami login page

Umami will auto-create its schema on first startup. Default credentials: `admin` / `umami` — change immediately.

## Next Phase Readiness

- Infrastructure is ready for Plan 02 (tracking script integration into the frontend)
- analytics.flawchess.com will be live once deployed with correct env vars and DNS record

---
*Phase: 24-web-analytics*
*Completed: 2026-03-22*
