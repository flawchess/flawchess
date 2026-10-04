---
quick_id: 261004-rmc
mode: quick
type: execute
files_modified:
  - frontend/src/lib/autoReload.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/stalePreloadReload.ts
  - frontend/src/main.tsx
  - frontend/src/lib/__tests__/autoReload.test.ts
  - frontend/src/lib/__tests__/analytics.test.ts
  - frontend/src/lib/__tests__/stalePreloadReload.test.ts
---

# Quick 261004-rmc: Suppress the Umami pageview after automatic reloads

## Problem

Idle open tabs reload themselves after every deploy: the hourly service-worker
update check (`SW_UPDATE_INTERVAL_MS`) finds the new SW, `controllerchange`
fires, and `main.tsx` calls `window.location.reload()`. Umami records each
reload as a fresh pageview with no events. Prod evidence (2026-10-04): session
8ebbb412 on /train reloaded at 04:18/05:18/09:18/14:18/15:18/16:18 UTC, the
first hourly tick after each of that day's six releases. The `vite:preloadError`
stale-chunk recovery reload (`stalePreloadReload.ts`) has the same effect.

Umami has no server-side setting for this; the tracker's `data-before-send`
hook cancels a send when it returns a falsy value (verified in the served
script.js). A pageview is `type === 'event'` with no `name`.

## Task 1: autoReload helper + reload sites

- New `frontend/src/lib/autoReload.ts`:
  - `reloadAutomatically()`: write a sessionStorage marker (`flawchess:auto-reload`,
    try/catch) then `window.location.reload()`.
  - `consumeAutoReloadMarker(): boolean`: read and remove the marker (try/catch, false on error).
- `main.tsx` controllerchange handler and `handleVitePreloadError` call
  `reloadAutomatically()` instead of `window.location.reload()`.
- User-initiated reloads (App.tsx error button, Analysis.tsx) stay untouched.

## Task 2: drop the landing pageview after an automatic reload

- `analytics.ts`: `installUmamiBeforeSend()` consumes the marker at boot (once per
  page load, so a leftover marker can never eat a later real pageview when the
  tracker is blocked), and installs `umamiBeforeSend`, which returns `null` for
  the first pageview of that page load and otherwise delegates to
  `scrubUmamiPayload`. Custom events and identify calls always pass.

## Task 3: tests

- autoReload: marker set before reload; consume returns true once then false;
  storage throwing does not block the reload.
- analytics: flagged boot drops exactly one pageview; custom events and identify
  pass while flagged; no marker = passthrough (scrubbed).
- stalePreloadReload: recovery reload sets the auto-reload marker.

## Verify

`cd frontend && npx vitest run src/lib/__tests__/{autoReload,analytics,stalePreloadReload}.test.ts && npm run lint && npm run build && npm run knip`
