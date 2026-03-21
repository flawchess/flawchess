---
phase: quick
plan: 260321-txu
subsystem: backend, frontend, infra
tags: [api-prefix, routing, caddy, vite, fastapi]
dependency_graph:
  requires: []
  provides: [api-prefix-routing]
  affects: [backend-routes, frontend-api-calls, vite-proxy, caddy-config]
tech_stack:
  added: []
  patterns: [single /api/* reverse proxy rule]
key_files:
  created: []
  modified:
    - app/main.py
    - app/routers/auth.py
    - frontend/src/api/client.ts
    - frontend/vite.config.ts
    - deploy/Caddyfile
    - tests/test_imports_router.py
    - tests/test_stats_router.py
    - tests/test_users_router.py
    - tests/test_auth.py
decisions:
  - "Used include_router(prefix='/api') in main.py — no router file changes needed, routers stay reusable"
  - "baseURL: '/api' in Axios client — all existing hook/page paths require no changes since Axios prepends baseURL"
  - "Removed /auth/callback Caddyfile special handle — no longer needed since /api/* does not collide with frontend /auth/callback route"
metrics:
  duration: ~10m
  completed: "2026-03-21"
  tasks_completed: 3
  files_changed: 9
---

# Quick Task 260321-txu: Add /api Prefix to All Backend Routes Summary

**One-liner:** Unified all FastAPI routes under `/api/` prefix via `include_router(prefix='/api')`, enabling a single `/api/*` Caddy reverse proxy rule instead of enumerating every route path.

## Tasks Completed

| # | Task | Commit |
|---|------|--------|
| 1 | Add /api prefix to all backend routes | fd9a13c |
| 2 | Update frontend API calls, Vite proxy, and Caddyfile | 86e1647 |
| 3 | Update backend tests to use /api-prefixed routes | 8b7b5a2 |

## What Was Done

### Task 1: Backend route prefix

`app/main.py` — changed all `app.include_router(...)` calls to add `prefix="/api"` and updated the health endpoint to `/api/health`. No individual router files were modified.

`app/routers/auth.py` — updated both OAuth callback URL constructions from `BACKEND_URL/auth/google/callback` to `BACKEND_URL/api/auth/google/callback`.

### Task 2: Frontend and infrastructure

`frontend/src/api/client.ts` — set `baseURL: '/api'`. All existing hook/page API calls require no changes since Axios prepends baseURL. Also updated the 401 interceptor auth route check from `/auth/` to `/api/auth/`.

`frontend/vite.config.ts` — replaced 7 per-route proxy rules with a single `/api` proxy rule. Updated workbox `runtimeCaching` pattern from the multi-route alternation regex to `/^\/api\//`.

`deploy/Caddyfile` — removed the `@backend` named matcher enumerating all route prefixes and the special `/auth/callback` SPA handle. Replaced with a single `handle /api/* { reverse_proxy backend:8000 }` block.

### Task 3: Test updates

Updated all route paths in `test_imports_router.py`, `test_stats_router.py`, `test_users_router.py`, and `test_auth.py` to include the `/api` prefix. All 29 router tests pass.

## User Action Required

**Google OAuth Console** — update the authorized redirect URI:
- Dev: `http://localhost:8000/auth/google/callback` → `http://localhost:8000/api/auth/google/callback`
- Prod: `https://flawchess.com/auth/google/callback` → `https://flawchess.com/api/auth/google/callback`

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- app/main.py modified with /api prefix: FOUND
- app/routers/auth.py callback URLs updated: FOUND
- frontend/src/api/client.ts baseURL set to '/api': FOUND
- frontend/vite.config.ts single /api proxy rule: FOUND
- deploy/Caddyfile single handle /api/* rule: FOUND
- Commits fd9a13c, 86e1647, 8b7b5a2: FOUND
- 29 router tests passing: VERIFIED
- Frontend build successful: VERIFIED
