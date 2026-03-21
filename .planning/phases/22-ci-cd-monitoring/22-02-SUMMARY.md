---
phase: 22-ci-cd-monitoring
plan: 02
subsystem: infra
tags: [sentry, error-monitoring, fastapi, react, docker, vite]

# Dependency graph
requires:
  - phase: 21-docker-deployment
    provides: docker-compose.yml caddy service with frontend Dockerfile build

provides:
  - sentry-sdk[fastapi] integrated into FastAPI backend with env-guarded init
  - @sentry/react integrated into frontend with instrument.ts, ErrorBoundary, and React 19 error hooks
  - VITE_SENTRY_DSN passed as Docker build arg through docker-compose.yml to frontend Dockerfile
  - SENTRY_DSN and VITE_SENTRY_DSN documented in .env.example

affects: [23-launch-readiness]

# Tech tracking
tech-stack:
  added: [sentry-sdk[fastapi]>=2.54.0, @sentry/react]
  patterns:
    - Sentry init guarded by empty-string DSN check (disabled in dev by default)
    - Frontend instrument.ts imported first in main.tsx before any app code
    - React 19 createRoot error hooks (onUncaughtError, onCaughtError, onRecoverableError) wired to Sentry.reactErrorHandler()
    - Vite VITE_SENTRY_DSN baked into bundle at Docker build time via ARG/ENV

key-files:
  created:
    - frontend/src/instrument.ts
  modified:
    - pyproject.toml
    - uv.lock
    - app/core/config.py
    - app/main.py
    - .env.example
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/Dockerfile
    - docker-compose.yml

key-decisions:
  - "Sentry disabled by default (SENTRY_DSN empty string) — no noise in dev, no console errors"
  - "10% traces_sample_rate on both backend and frontend — performance visibility without volume overhead"
  - "send_default_pii=False on backend — no user emails or IPs sent to Sentry"
  - "Single Sentry project for both backend and frontend — simpler setup, SENTRY_DSN == VITE_SENTRY_DSN"
  - "ErrorBoundary placed inside AuthProvider (not outside) — auth context available in fallback UI if needed"

patterns-established:
  - "Pattern: Instrument first — instrument.ts imported as the very first import in main.tsx"
  - "Pattern: Docker build-time env injection — ARG/ENV in Dockerfile, args: block in docker-compose.yml"

requirements-completed: [MON-01, MON-02]

# Metrics
duration: 3min
completed: 2026-03-21
---

# Phase 22 Plan 02: Sentry Monitoring Integration Summary

**sentry-sdk[fastapi] and @sentry/react wired into both FastAPI and React with Docker build-time DSN injection, React 19 error hooks, and ErrorBoundary fallback UI**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-21T21:29:20Z
- **Completed:** 2026-03-21T21:32:18Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Backend: `sentry-sdk[fastapi]` installed, `sentry_sdk.init()` called before FastAPI app creation with SENTRY_DSN guard, environment tagging, 10% trace sampling, and PII exclusion
- Frontend: `@sentry/react` installed, `instrument.ts` initializes Sentry first, `main.tsx` wires React 19 createRoot error hooks, `App.tsx` wraps content in `Sentry.ErrorBoundary` with "Something went wrong" fallback and reload button
- Docker: `VITE_SENTRY_DSN` passed from `docker-compose.yml` build args through `frontend/Dockerfile` ARG/ENV into the Vite build bundle
- Config: `SENTRY_DSN` and `VITE_SENTRY_DSN` documented in `.env.example`

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend Sentry integration** - `463f378` (feat)
2. **Task 2: Frontend Sentry integration + Docker build arg passthrough** - `8cff497` (feat)

**Plan metadata:** _(to be added in final commit)_

## Files Created/Modified

- `frontend/src/instrument.ts` - Sentry.init with VITE_SENTRY_DSN, browserTracingIntegration, 10% tracesSampleRate
- `app/main.py` - import sentry_sdk + guarded init before app = FastAPI(...)
- `app/core/config.py` - SENTRY_DSN: str = "" field added to Settings
- `pyproject.toml` + `uv.lock` - sentry-sdk[fastapi]>=2.54.0 added
- `frontend/src/main.tsx` - instrument.ts first import, React 19 error hooks on createRoot
- `frontend/src/App.tsx` - Sentry.ErrorBoundary wrapping AppRoutes + Toaster inside AuthProvider
- `frontend/Dockerfile` - ARG VITE_SENTRY_DSN + ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN before npm run build
- `docker-compose.yml` - args: [VITE_SENTRY_DSN=${VITE_SENTRY_DSN}] under caddy build section
- `.env.example` - SENTRY_DSN= and VITE_SENTRY_DSN= documented with comment

## Decisions Made

- Sentry disabled by default via empty-string DSN — no noise in dev, no console warnings
- 10% traces_sample_rate on both backend and frontend — visibility without volume overhead
- `send_default_pii=False` on backend — no user emails or IPs sent to Sentry
- Single Sentry project for both tiers — same DSN value for SENTRY_DSN and VITE_SENTRY_DSN
- ErrorBoundary placed inside AuthProvider so auth context is available in fallback UI

## Deviations from Plan

None — plan executed exactly as written.

**Note on pre-existing lint failures:** `npm run lint` has pre-existing failures in files not touched by this plan (App.tsx useRef-during-render, shadcn UI component exports, SuggestionsModal setState-in-effect, generated dev-dist/workbox files). These are documented in `deferred-items.md`. The new files `instrument.ts` and `main.tsx` lint cleanly.

## Issues Encountered

None significant. `uv add "sentry-sdk[fastapi]"` resolved immediately (package already in registry). `npm install @sentry/react` added 7 packages. Frontend build succeeded in 3.73s.

## User Setup Required

**External service requires manual configuration.** To enable Sentry monitoring in production:

1. Create a Sentry project at sentry.io:
   - Go to sentry.io → Create Project → select **Python** platform → name `flawchess`
   - Go to Settings → Client Keys (DSN) → copy the DSN URL

2. Add to `/opt/flawchess/.env` on the production server:
   ```
   SENTRY_DSN=https://...@sentry.io/...
   VITE_SENTRY_DSN=https://...@sentry.io/...
   ```
   (Both values are the same DSN — single project covers both backend and frontend)

3. Rebuild and redeploy:
   ```bash
   ssh flawchess "cd /opt/flawchess && git pull origin main && docker compose up -d --build"
   ```

## Next Phase Readiness

- Sentry monitoring is fully wired and will activate as soon as SENTRY_DSN is added to production .env
- Phase 23 (Launch Readiness) can proceed — monitoring is in place for production launch

---
*Phase: 22-ci-cd-monitoring*
*Completed: 2026-03-21*
