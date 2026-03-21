---
phase: quick
plan: 260321-txu
type: execute
wave: 1
depends_on: []
files_modified:
  - app/main.py
  - app/routers/auth.py
  - app/routers/analysis.py
  - app/routers/position_bookmarks.py
  - app/routers/stats.py
  - frontend/src/api/client.ts
  - frontend/src/hooks/useAuth.ts
  - frontend/src/hooks/useAnalysis.ts
  - frontend/src/hooks/useNextMoves.ts
  - frontend/src/hooks/useImport.ts
  - frontend/src/hooks/useUserProfile.ts
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/Import.tsx
  - frontend/src/pages/Dashboard.tsx
  - frontend/src/components/auth/LoginForm.tsx
  - frontend/src/components/auth/RegisterForm.tsx
  - deploy/Caddyfile
  - frontend/vite.config.ts
autonomous: true
requirements: []

must_haves:
  truths:
    - "Every backend route is reachable at /api/<original-path>"
    - "No route is reachable at the old path without /api prefix"
    - "Frontend API calls use /api-prefixed paths"
    - "Caddyfile proxies /api/* to backend:8000"
    - "Vite dev proxy forwards /api/* to localhost:8000"
    - "Google OAuth callback URL uses /api/auth/google/callback"
    - "All tests pass with updated route paths"
  artifacts:
    - path: "app/main.py"
      provides: "FastAPI app with /api prefix applied via root_path or include_router prefix"
    - path: "deploy/Caddyfile"
      provides: "Single /api/* reverse_proxy rule"
    - path: "frontend/vite.config.ts"
      provides: "Single /api proxy rule replacing per-route rules"
    - path: "frontend/src/api/client.ts"
      provides: "baseURL set to /api"
  key_links:
    - from: "frontend/src/api/client.ts"
      to: "app/main.py"
      via: "baseURL: '/api' + router prefixes"
    - from: "deploy/Caddyfile"
      to: "backend:8000"
      via: "handle /api/* { reverse_proxy backend:8000 }"
---

<objective>
Add `/api` prefix to all backend routes so the Caddyfile can use a single `/api/*` reverse proxy rule instead of enumerating every route path.

Purpose: Simplify Caddy config and eliminate the risk of adding new routes that don't get proxied. All traffic to `/api/*` goes to FastAPI; everything else is the SPA.
Output: Backend serves all routes under `/api/`, frontend uses `/api`-prefixed calls, Caddyfile and Vite proxy reduced to one rule each.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add /api prefix to all backend routes</name>
  <files>app/main.py, app/routers/auth.py, app/routers/analysis.py, app/routers/position_bookmarks.py, app/routers/stats.py</files>
  <action>
The cleanest approach is to set `root_path="/api"` on the FastAPI app OR apply a prefix in `include_router()`. Use `include_router()` prefix in `app/main.py` — it requires no router file changes and keeps the routers reusable.

In `app/main.py`, change all `app.include_router(...)` calls to add `prefix="/api"`:

```python
app.include_router(auth.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(position_bookmarks.router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(users_router, prefix="/api")
```

Also update the `/health` endpoint in `app/main.py`:
```python
@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

**Critical — Google OAuth callback URL:** In `app/routers/auth.py`, the callback URL is hardcoded as:
```python
redirect_url = f"{settings.BACKEND_URL}/auth/google/callback"
```
This must become:
```python
redirect_url = f"{settings.BACKEND_URL}/api/auth/google/callback"
```
Both occurrences in the file (in `google_authorize` and `google_callback` functions) must be updated.

**Note for user:** The Google OAuth Console authorized redirect URI must also be updated to `https://flawchess.com/api/auth/google/callback` (and the dev equivalent if configured). Flag this in the task output — it's a manual step in the Google Cloud Console.

Do NOT change any individual router files (`analysis.py`, `position_bookmarks.py`, `stats.py`) — their route decorators (`@router.get("/analysis/...")`) stay as-is because the prefix stacks.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run python -c "from app.main import app; routes = [r.path for r in app.routes]; assert any('/api/auth' in p for p in routes), f'Missing /api/auth: {routes}'; assert any('/api/stats' in p for p in routes), 'Missing /api/stats'; assert any('/api/health' in p for p in routes), 'Missing /api/health'; print('Route prefix OK:', [p for p in routes if p.startswith('/api')])"</automated>
  </verify>
  <done>All FastAPI routes are registered under /api/ prefix. Google OAuth callback URL updated in auth.py.</done>
</task>

<task type="auto">
  <name>Task 2: Update frontend API calls, Vite proxy, and Caddyfile</name>
  <files>
    frontend/src/api/client.ts,
    frontend/src/hooks/useAuth.ts,
    frontend/src/hooks/useAnalysis.ts,
    frontend/src/hooks/useNextMoves.ts,
    frontend/src/hooks/useImport.ts,
    frontend/src/hooks/useUserProfile.ts,
    frontend/src/pages/Openings.tsx,
    frontend/src/pages/Import.tsx,
    frontend/src/pages/Dashboard.tsx,
    frontend/src/components/auth/LoginForm.tsx,
    frontend/src/components/auth/RegisterForm.tsx,
    frontend/vite.config.ts,
    deploy/Caddyfile
  </files>
  <action>
**frontend/src/api/client.ts** — Set `baseURL: '/api'`. This automatically prefixes every `apiClient.get('/auth/...')` call with `/api`. Also update the 401 interceptor's auth route check:
```typescript
const isAuthRoute = (error.config?.url ?? '').startsWith('/auth/');
```
becomes:
```typescript
const isAuthRoute = (error.config?.url ?? '').startsWith('/api/auth/');
```

With `baseURL: '/api'`, all existing apiClient calls in hooks and pages need NO changes — Axios prepends the baseURL automatically. The paths like `/auth/jwt/login`, `/imports/active`, `/stats/global` etc. remain as-is in the hooks/pages because Axios combines `baseURL + path`.

However, **direct fetch() calls** bypass Axios and need manual update. Check `frontend/src/components/auth/LoginForm.tsx` and `RegisterForm.tsx` — they use `apiClient.get('/auth/google/available')` and `apiClient.get('/auth/google/authorize')` which are already via apiClient, so they're covered by baseURL change. Verify no raw `fetch('/auth/...')` calls exist in any frontend file.

**frontend/vite.config.ts** — Replace the entire per-route proxy config with a single rule. Also update the `workbox.runtimeCaching` URL pattern. New proxy config:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    // /auth/callback is handled by the SPA, not the backend.
    // But /api/auth/callback doesn't exist — the OAuth callback is /api/auth/google/callback.
    // No bypass needed since frontend route is /auth/callback (no /api prefix).
  },
},
```

Also update the workbox `runtimeCaching` pattern in vite.config.ts from:
```typescript
urlPattern: /^\/(?:auth|analysis|games|imports|position-bookmarks|stats|users|health)\//,
```
to:
```typescript
urlPattern: /^\/api\//,
```

**deploy/Caddyfile** — Replace the `@backend` matcher with a simple `/api/*` rule. Remove the special `/auth/callback` frontend handle (it was needed because the old `/auth/*` backend rule would have caught it — with `/api/*` there's no collision):
```
flawchess.com {
    encode gzip

    # Frontend SPA — serve static files first
    @static file
    handle @static {
        root * /srv
        file_server
    }

    # Backend API — single rule, all backend routes are under /api/
    handle /api/* {
        reverse_proxy backend:8000
    }

    # SPA fallback — all remaining paths get index.html
    handle {
        root * /srv
        header /index.html Cache-Control "no-cache"
        try_files /index.html
        file_server
    }
}
```

Note: The special `/auth/callback` handle is removed because it was only needed to prevent the old `/auth/*` backend rule from catching the frontend route. With `/api/*` routing, `/auth/callback` (no `/api/` prefix) naturally falls through to the SPA fallback.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && npm --prefix frontend run build 2>&1 | tail -5</automated>
  </verify>
  <done>Frontend builds successfully. baseURL is '/api'. Vite proxy uses single /api rule. Caddyfile uses single handle /api/* rule. workbox pattern updated to /^\/api\//.</done>
</task>

<task type="auto">
  <name>Task 3: Update backend tests to use /api-prefixed routes</name>
  <files>
    tests/test_imports_router.py,
    tests/test_stats_router.py,
    tests/test_users_router.py,
    tests/test_auth.py
  </files>
  <action>
All test files use hardcoded route paths like `/auth/register`, `/auth/jwt/login`, `/imports/{id}`, `/stats/rating-history`, `/users/me/profile`. These must be updated to include the `/api` prefix.

Files to update and their patterns:

**tests/test_imports_router.py:**
- `/auth/register` → `/api/auth/register`
- `/auth/jwt/login` → `/api/auth/jwt/login`
- `/imports/{job_id}` → `/api/imports/{job_id}`
- `/imports/00000000-...` → `/api/imports/00000000-...`
- `/imports/some-db-job-id` → `/api/imports/some-db-job-id`

**tests/test_stats_router.py:**
- `/auth/register` → `/api/auth/register`
- `/auth/jwt/login` (search for this) → `/api/auth/jwt/login`
- `/stats/rating-history` → `/api/stats/rating-history`
- `/stats/global` → `/api/stats/global`

**tests/test_users_router.py:**
- `/auth/register` → `/api/auth/register`
- `/auth/jwt/login` (search for this) → `/api/auth/jwt/login`
- `/users/me/profile` → `/api/users/me/profile`

**tests/test_auth.py:** Check and update any route calls.

Do a comprehensive search before editing to make sure no route references are missed:
```bash
grep -rn "client\.\(get\|post\|put\|patch\|delete\)" tests/ | grep -v "/api/"
```
Any hit that references a backend route (not starting with `/api/`) must be updated.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/test_imports_router.py tests/test_stats_router.py tests/test_users_router.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>All router tests pass with /api-prefixed routes. No test calls routes without /api prefix.</done>
</task>

</tasks>

<verification>
After all tasks, verify end-to-end:

1. Backend route registration: `uv run python -c "from app.main import app; print([r.path for r in app.routes if hasattr(r,'path')])"` — all paths start with `/api/`
2. Tests pass: `uv run pytest tests/test_imports_router.py tests/test_stats_router.py tests/test_users_router.py -q`
3. Frontend build: `npm --prefix frontend run build` — exits 0
4. No stray non-prefixed backend calls: `grep -rn "apiClient\." frontend/src/ | grep -v "'/api\|\"\/api"` — should show empty or only relative paths that get baseURL prepended
5. Caddyfile has no `@backend` matcher — `grep "backend" deploy/Caddyfile` — only shows `reverse_proxy backend:8000`
6. Dev experience: `uv run uvicorn app.main:app --reload` and `npm --prefix frontend run dev` — `curl http://localhost:5173/api/health` returns `{"status":"ok"}`

**User action required after task 1:** Update the Google OAuth Console authorized redirect URI from `http://localhost:8000/auth/google/callback` to `http://localhost:8000/api/auth/google/callback` (dev) and `https://flawchess.com/api/auth/google/callback` (prod).
</verification>

<success_criteria>
- All FastAPI routes registered under /api/ prefix (verified by introspection)
- Single /api/* rule in Caddyfile (no enumerated @backend matcher)
- Single /api proxy rule in vite.config.ts
- frontend/src/api/client.ts has baseURL: '/api'
- All router tests pass
- Frontend builds without errors
</success_criteria>

<output>
After completion, create `.planning/quick/260321-txu-add-api-prefix-to-all-backend-routes/260321-txu-SUMMARY.md`
</output>
