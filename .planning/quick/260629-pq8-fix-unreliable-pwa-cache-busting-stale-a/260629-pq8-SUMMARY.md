---
quick_id: 260629-pq8
slug: fix-unreliable-pwa-cache-busting-stale-a
description: Fix unreliable PWA cache-busting (stale app shell on installed Android PWA)
status: complete
date: 2026-06-29
commit: 8c3400dc
---

# Quick Task 260629-pq8: Fix unreliable PWA cache-busting — Summary

## What changed

Two-part service-worker fix for installed Android PWAs launching a many-deploys-old
layout (the app shell was served from the SW precache, which could be stale).

1. **`frontend/vite.config.ts`** — Workbox config:
   - `globIgnores` now includes `'**/*.html'`, dropping `index.html` (and the prerendered
     `privacy/index.html` + Google verification HTML) from the precache. This removes the
     cache-first precache route that was serving `/` as a stale shell.
   - Added a `NetworkFirst` runtime route for navigations
     (`request.mode === 'navigate' && !url.pathname.startsWith('/api/')`) into an
     `html-shell` cache (`cacheableResponse: { statuses: [200] }`, no `networkTimeoutSeconds`).
     Online launches now always fetch a fresh `index.html` (→ current hashed assets);
     true-offline falls back to the last cached shell.
   - Kept `navigateFallback: null` and the `/^\/api\//` `NetworkOnly` route **first**, so
     the Google OAuth callback is unaffected.

2. **`frontend/src/main.tsx`** — resume-aware SW update checks:
   - Replaced the bare hourly `setInterval` with a debounced `checkForSwUpdate()`
     (`SW_UPDATE_INTERVAL_MS`, `SW_UPDATE_DEBOUNCE_MS`) wired to the interval **plus**
     `document visibilitychange` (→ `visible`) and `window focus` — the events that fire
     when Android resumes a frozen PWA. Kept the existing `controllerchange` auto-reload
     and `registerType: 'autoUpdate'` (no prompt UI).

3. **`CHANGELOG.md`** — `### Fixed` bullet under `## [Unreleased]`.

## Verification

- `npm run lint` — 0 errors (3 pre-existing warnings in generated `coverage/`, unrelated).
- `npm test -- --run` — 105 files, 1237 tests pass.
- `npm run build` — succeeds; PWA precache dropped from 14 → 11 entries.
- Inspected generated `dist/sw.js`:
  - No `*.html` entries in `precacheAndRoute` (confirmed).
  - `NetworkFirst` + `html-shell` cache present; `/api/` `NetworkOnly` present.
  - Hashed `assets/*`, engine JS, icons, `manifest.webmanifest` still precached.

## Out of scope / unchanged

- `deploy/Caddyfile` — verified already correct (`no-cache` on HTML/SW/manifest,
  `immutable` on `/assets/*`); no change.

## HUMAN follow-up (manual, can't be automated here)

Real installed Android PWA test: install build A, background it, deploy build B with a
visible nav change, resume from the launcher (not a cold start) → the new layout should
appear without a manual reload (visibility/focus fires `update()`; NetworkFirst serves the
fresh shell). Worth confirming after the next deploy.

## Risks (low)

- Reload loops: `update()` only installs when `sw.js` bytes change; `refreshing` guard caps
  reloads at one per page lifetime.
- Double-fetch: NetworkFirst navigations always hit the network for the tiny `no-cache`
  HTML doc — intended; hashed assets remain precached/immutable.
- Dev-mode SW (`devOptions.enabled`): nav route also registers in dev, but the Vite dev
  server never "fails" so NetworkFirst always returns fresh; HMR unaffected.
