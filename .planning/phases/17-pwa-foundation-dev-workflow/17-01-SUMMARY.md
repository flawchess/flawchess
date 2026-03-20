---
phase: 17-pwa-foundation-dev-workflow
plan: "01"
subsystem: ui
tags: [pwa, vite-plugin-pwa, workbox, service-worker, web-manifest, icons, mobile]

# Dependency graph
requires: []
provides:
  - PWA manifest (manifest.webmanifest) generated at build time with name, icons, theme_color, display:standalone
  - Service worker (sw.js) with Workbox NetworkOnly for all 8 API routes
  - Chess knight PNG icons at public/icons/icon-192.png and public/icons/icon-512.png
  - index.html with theme-color meta, apple-touch-icon, PNG favicon, viewport-fit=cover
  - npm scripts dev:mobile (vite --host) and dev:tunnel (cloudflared) for phone testing
  - TUNNEL env guard on allowedHosts — never committed as default
affects: [18-mobile-navigation, 19-mobile-ux-polish]

# Tech tracking
tech-stack:
  added: [vite-plugin-pwa@1.2.0, workbox-window@7.4.0]
  patterns:
    - generateSW mode — zero hand-written service worker code
    - NetworkOnly Workbox strategy for API routes prevents stale cached responses
    - TUNNEL env guard for allowedHosts — DNS rebinding protection without blocking LAN testing

key-files:
  created:
    - frontend/public/icons/icon-192.png
    - frontend/public/icons/icon-512.png
  modified:
    - frontend/vite.config.ts
    - frontend/index.html
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "Use vite-plugin-pwa v1.2.0 with generateSW mode — zero-config, Vite 7 compatible"
  - "NetworkOnly strategy for all 8 API route prefixes prevents stale analysis data"
  - "allowedHosts: true (boolean) for Vite 7 — the 'all' string workaround was for Vite 6.0.9 bug, now fixed"
  - "TUNNEL env guard for allowedHosts — never committed as permissive default"
  - "registerType: autoUpdate — skipWaiting + clientsClaim, silent auto-update on next navigation"

patterns-established:
  - "Pattern 1: VitePWA plugin in vite.config.ts — single config point for manifest + service worker"
  - "Pattern 2: Env-guarded allowedHosts — TUNNEL=true enables tunnel-compatible config"

requirements-completed: [PWA-01, PWA-02, PWA-03, DEV-01, DEV-02]

# Metrics
duration: ~20min (including human-verify checkpoint)
completed: 2026-03-20
---

# Phase 17 Plan 01: PWA Foundation + Dev Workflow Summary

**vite-plugin-pwa installed with generateSW mode, chess knight icons at 192/512px, NetworkOnly workbox rules for 8 API routes, and dev:mobile/dev:tunnel scripts for phone testing**

## Performance

- **Duration:** ~20 min (including human-verify checkpoint)
- **Started:** 2026-03-20T13:34:20Z
- **Completed:** 2026-03-20T14:06:12Z
- **Tasks:** 3 of 3 complete
- **Files modified:** 5

## Accomplishments
- Generated 192x192 and 512x512 chess knight PNG icons on dark #0a0a0a background
- Installed vite-plugin-pwa v1.2.0 and configured VitePWA plugin in vite.config.ts
- Build produces dist/manifest.webmanifest and dist/sw.js with 7 precached assets (1188 KiB)
- All 8 API route prefixes use NetworkOnly Workbox strategy — prevents stale analysis data
- index.html updated with PWA meta tags (theme-color, apple-touch-icon, viewport-fit=cover)
- dev:mobile and dev:tunnel scripts added for LAN and Cloudflare Tunnel phone testing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create chess knight PWA icons** - `dd48c3b` (feat)
2. **Task 2: Configure vite-plugin-pwa, update index.html, add dev scripts** - `843059c` (feat)
3. **Task 3: Verify PWA build and manifest** - checkpoint:human-verify (approved by user)

## Files Created/Modified
- `frontend/public/icons/icon-192.png` - 192x192 chess knight icon (dark bg, light knight silhouette)
- `frontend/public/icons/icon-512.png` - 512x512 chess knight icon (maskable, for Android adaptive icons)
- `frontend/public/vite.svg` - deleted (replaced by chess knight icon)
- `frontend/vite.config.ts` - VitePWA plugin, server.host:true, TUNNEL-guarded allowedHosts, NetworkOnly workbox
- `frontend/index.html` - PNG favicon, apple-touch-icon, theme-color meta, viewport-fit=cover
- `frontend/package.json` - vite-plugin-pwa devDependency, dev:mobile and dev:tunnel scripts

## Decisions Made
- **allowedHosts: true (boolean) not string 'all'** — Vite 7.3.1's type signature is `string[] | true`. The `'all'` string workaround was for a Vite 6.0.9 bug. With Vite 7, `true` is the correct typed value. The TUNNEL env guard still prevents it from being the committed default.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used allowedHosts: true instead of 'all' string**
- **Found during:** Task 2 (Configure vite-plugin-pwa)
- **Issue:** Plan specified `allowedHosts: process.env.TUNNEL ? 'all' : []` but Vite 7 TypeScript types define `allowedHosts` as `string[] | true | undefined`. The string `'all'` caused TypeScript error TS2769. The `'all'` string was a workaround for a Vite 6.0.9 bug that is no longer present in Vite 7.
- **Fix:** Changed `'all'` to `true` — `process.env.TUNNEL ? true : []`
- **Files modified:** `frontend/vite.config.ts`
- **Verification:** `npm run build` exits 0, TypeScript passes
- **Committed in:** 843059c (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix necessary for TypeScript type correctness. Behavior identical — `true` allows all hosts when TUNNEL env is set. No scope creep.

## Issues Encountered
None beyond the allowedHosts type fix.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PWA infrastructure complete: manifest, service worker, icons, meta tags all in place
- User verified PWA in Chrome DevTools: manifest, service worker, cache storage, API NetworkOnly routing all confirmed working
- Google SSO redirect mismatch on vite preview port is expected (OAuth redirect URIs configured for dev port 5173 and prod — preview port 4173 is not a registered redirect)
- Ready for Phase 18: Mobile Navigation
- Cloudflare Tunnel: user must install `cloudflared` CLI if not already present; dev:tunnel script is ready

---
*Phase: 17-pwa-foundation-dev-workflow*
*Completed: 2026-03-20*
