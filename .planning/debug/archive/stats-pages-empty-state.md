---
status: diagnosed
trigger: "Rating page and Global Stats page show empty states despite having imported games from both platforms"
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Focus

hypothesis: Vite proxy is missing a `/stats` entry, so API calls to `/stats/rating-history` and `/stats/global` are served by the Vite dev server (returning the SPA HTML) instead of being forwarded to the FastAPI backend
test: Compare vite.config.ts proxy entries against API paths used by the frontend
expecting: `/stats` is absent from the proxy config
next_action: N/A - root cause confirmed

## Symptoms

expected: Rating page shows rating charts for Chess.com and Lichess; Global Stats page shows W/D/L bar charts by time control and by color
actual: Both pages show empty states ("No Chess.com games imported", "No Lichess games imported", "No data available")
errors: No console errors reported (Axios likely gets a 200 with HTML content which parses to empty/undefined)
reproduction: Navigate to Rating or Global Stats page in dev mode
started: Since stats pages were first added

## Eliminated

(none needed - root cause found on first hypothesis)

## Evidence

- timestamp: 2026-03-14T00:00:00Z
  checked: vite.config.ts proxy configuration (lines 15-29)
  found: Proxy entries exist for /auth, /analysis, /games, /imports, /bookmarks, /health. There is NO entry for /stats.
  implication: Frontend API calls to /stats/rating-history and /stats/global are NOT proxied to the backend.

- timestamp: 2026-03-14T00:00:00Z
  checked: frontend/src/api/client.ts statsApi (lines 72-81)
  found: statsApi calls `/stats/rating-history` and `/stats/global` using relative URLs via the shared Axios client (baseURL is empty)
  implication: These requests go to the Vite dev server which has no proxy rule for /stats, so Vite serves the SPA index.html instead

- timestamp: 2026-03-14T00:00:00Z
  checked: frontend/src/App.tsx line 102
  found: There is a frontend route `<Route path="/stats" ...>` which means Vite's SPA fallback will match /stats/* paths and return HTML
  implication: The Axios GET to /stats/rating-history returns HTML (the SPA), not JSON. Axios parses the response but the data structure doesn't match RatingHistoryResponse, so `data` is undefined/empty.

- timestamp: 2026-03-14T00:00:00Z
  checked: Backend router, service, repository chain
  found: All backend code is correct. Router registers endpoints at /stats/rating-history and /stats/global. Service and repository logic is sound. Queries filter by user_id and return proper data structures.
  implication: Backend is not the problem.

- timestamp: 2026-03-14T00:00:00Z
  checked: Frontend hooks and components
  found: useRatingHistory and useGlobalStats hooks correctly call statsApi. Components use `?? []` fallback on data, so when data is undefined (due to HTML response), they get empty arrays and show empty states.
  implication: Frontend display logic is correct - it correctly shows empty state when it receives no data. The problem is upstream (no data arrives).

## Resolution

root_cause: The Vite dev server proxy in `frontend/vite.config.ts` is missing a `/stats` entry. All other API path prefixes (/auth, /analysis, /games, /imports, /bookmarks, /health) are proxied to `http://localhost:8000`, but `/stats` was never added. When the frontend makes API calls to `/stats/rating-history` or `/stats/global`, Vite serves the SPA HTML instead of forwarding to the FastAPI backend. The Axios client receives HTML instead of JSON, the response doesn't match the expected type, and components fall through to empty-array defaults, showing empty states.
fix: (not applied - diagnosis only)
verification: (not applied - diagnosis only)
files_changed: []
