---
phase: 17-pwa-foundation-dev-workflow
verified: 2026-03-20T14:30:00Z
status: human_needed
score: 8/8 must-haves verified
human_verification:
  - test: "Open Chrome DevTools > Application > Manifest and confirm name=Chessalytics, display=standalone, icons show chess knight images at 192 and 512"
    expected: "Manifest section shows Chessalytics app with knight icons, no missing icon errors"
    why_human: "Icon visual quality and manifest rendering require a browser"
  - test: "Open Chrome DevTools > Application > Service Workers after running npm run build && npm run preview; confirm sw.js is registered"
    expected: "Service worker registered and active, status shows 'activated and running'"
    why_human: "Service worker registration and activation state requires a live browser"
  - test: "In Chrome Network tab, trigger an API call (e.g. open Openings page); confirm /analysis/* requests do NOT show '(ServiceWorker)' in Size column"
    expected: "API routes bypass the service worker cache and always hit the network"
    why_human: "ServiceWorker cache bypass behavior requires Network tab inspection in a browser"
  - test: "Run npm run dev:mobile in frontend/, find the LAN IP printed by Vite, open it on a phone connected to the same Wi-Fi"
    expected: "Chessalytics app loads on the phone browser over LAN"
    why_human: "Requires physical phone and Wi-Fi network"
  - test: "Optional: install cloudflared CLI and run npm run dev:tunnel; open the printed HTTPS URL on a phone on a different network"
    expected: "Chessalytics app loads over Cloudflare Tunnel URL on phone"
    why_human: "Requires physical phone, cloudflared CLI, and external network"
---

# Phase 17: PWA Foundation & Dev Workflow — Verification Report

**Phase Goal:** PWA Foundation & Dev Workflow — installable PWA with service worker, custom icons, and phone testing dev workflow
**Verified:** 2026-03-20T14:30:00Z
**Status:** human_needed — all automated checks pass, human browser/device testing required
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `npm run build` produces `dist/manifest.webmanifest` with name, icons, theme_color, display:standalone | VERIFIED | Build exits 0; `dist/manifest.webmanifest` contains `"name":"Chessalytics"`, `"display":"standalone"`, `"theme_color":"#0a0a0a"`, both icon entries |
| 2 | `npm run build` produces `dist/sw.js` (generated service worker) | VERIFIED | `dist/sw.js` exists; contains `precacheAndRoute` with 7 entries (registerSW.js, index.html, JS, CSS, icons, manifest) |
| 3 | Custom chess knight icons exist at `public/icons/icon-192.png` and `public/icons/icon-512.png` | VERIFIED | `file` reports both as `PNG image data, 192 x 192` and `512 x 512` RGBA; `vite.svg` removed |
| 4 | `index.html` has theme-color meta, apple-touch-icon link, and PNG favicon (not vite.svg) | VERIFIED | All three present; `vite.svg` reference gone; `viewport-fit=cover` added |
| 5 | `npm run dev:mobile` script exists and starts Vite with `--host` flag | VERIFIED | `package.json` contains `"dev:mobile": "vite --host"` |
| 6 | `npm run dev:tunnel` script exists for Cloudflare Tunnel | VERIFIED | `package.json` contains `"dev:tunnel": "cloudflared tunnel --url http://localhost:5173"` |
| 7 | API routes are excluded from service worker caching via NetworkOnly strategy | VERIFIED | `dist/sw.js` line 1: `registerRoute(/^\/(?:auth\|analysis\|games\|imports\|position-bookmarks\|stats\|users\|health)\//, new e.NetworkOnly,"GET")` — all 8 prefixes wired |
| 8 | `allowedHosts` is guarded behind TUNNEL env variable, not committed as default | VERIFIED | `vite.config.ts` line 59: `allowedHosts: process.env.TUNNEL ? true : []` — guard in place; `true` (boolean) used instead of `'all'` (string) per Vite 7 type fix, behaviorally equivalent |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Purpose | Status | Details |
|----------|---------|--------|---------|
| `frontend/public/icons/icon-192.png` | 192x192 chess knight icon | VERIFIED | PNG 192x192 RGBA, non-interlaced |
| `frontend/public/icons/icon-512.png` | 512x512 chess knight icon (maskable) | VERIFIED | PNG 512x512 RGBA, non-interlaced |
| `frontend/vite.config.ts` | VitePWA plugin with manifest, workbox NetworkOnly, server.host, TUNNEL guard | VERIFIED | Contains `VitePWA`, `registerType: 'autoUpdate'`, `NetworkOnly`, `host: true`, TUNNEL guard, all existing proxy config preserved |
| `frontend/index.html` | PWA-ready HTML head | VERIFIED | Contains `theme-color`, `apple-touch-icon`, PNG favicon, `viewport-fit=cover`; no `vite.svg` |
| `frontend/package.json` | vite-plugin-pwa devDependency, dev:mobile and dev:tunnel scripts | VERIFIED | `"vite-plugin-pwa": "^1.2.0"` in devDependencies; both scripts present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/vite.config.ts` | `frontend/public/icons/` | manifest.icons src paths | VERIFIED | `src: '/icons/icon-192.png'` and `src: '/icons/icon-512.png'` in VitePWA manifest config |
| `frontend/vite.config.ts` | `dist/sw.js` | VitePWA generateSW at build time | VERIFIED | Build produces `dist/sw.js` with Workbox `precacheAndRoute` |
| `frontend/vite.config.ts` | workbox runtimeCaching | NetworkOnly handler for API routes | VERIFIED | `dist/sw.js` contains `registerRoute` with all 8 API prefixes and `NetworkOnly` handler |
| `frontend/index.html` | `frontend/public/icons/icon-192.png` | favicon and apple-touch-icon link tags | VERIFIED | Both `<link rel="icon" ... href="/icons/icon-192.png">` and `<link rel="apple-touch-icon" ...>` present |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| PWA-01 | App has a web manifest with name, icons, theme color, and display:standalone | SATISFIED | `dist/manifest.webmanifest` contains all four fields; VitePWA configured with matching values |
| PWA-02 | Service worker precaches static assets; NetworkOnly for API routes | SATISFIED (automated) / NEEDS HUMAN (cache behavior) | `dist/sw.js` precaches 7 entries; NetworkOnly regex covers all 8 API prefixes; actual cache behavior needs browser verification |
| PWA-03 | Custom chess-themed icons (192px + 512px PNG) replacing default Vite favicon | SATISFIED | Icons verified as valid PNG at correct dimensions; `vite.svg` deleted; manifest and index.html reference icons |
| DEV-01 | npm script exposes Vite dev server on LAN for same-network phone testing | SATISFIED (script) / NEEDS HUMAN (network test) | `"dev:mobile": "vite --host"` present; `server.host: true` in vite.config.ts enables LAN exposure; actual phone access needs human test |
| DEV-02 | Documented one-command Cloudflare Tunnel setup for HTTPS phone testing | SATISFIED | `"dev:tunnel": "cloudflared tunnel --url http://localhost:5173"` is the one-command interface; TUNNEL env guard configures allowedHosts and HMR clientPort for tunnel compatibility |

No orphaned requirements: all five requirement IDs (PWA-01, PWA-02, PWA-03, DEV-01, DEV-02) are claimed in plan 17-01 and mapped to verified artifacts.

---

### Anti-Patterns Found

None. No TODO/FIXME/HACK/placeholder comments in any modified file. No empty implementations. All modified files contain substantive, production-ready config.

---

### Notable Deviation (Non-Blocking)

The PLAN specified `allowedHosts: process.env.TUNNEL ? 'all' : []` but the implementation uses `process.env.TUNNEL ? true : []`. The SUMMARY documents this as an intentional fix: Vite 7 types define `allowedHosts` as `string[] | true | undefined` — the string `'all'` was a workaround for a Vite 6.0.9 bug. Using `true` (boolean) is the correct Vite 7 value with identical behavior. TypeScript passes. The security property (guard is env-conditional, never the committed default) is preserved.

---

### Human Verification Required

These items require a browser or physical device and cannot be verified programmatically.

#### 1. PWA Manifest in Chrome DevTools

**Test:** Run `cd frontend && npm run build && npm run preview`, open http://localhost:4173 in Chrome, open DevTools > Application > Manifest
**Expected:** Name "Chessalytics", display "standalone", two icon entries showing chess knight images at 192 and 512px with no broken image icons
**Why human:** Icon visual quality and manifest panel rendering require a live browser

#### 2. Service Worker Registration

**Test:** Same preview server, DevTools > Application > Service Workers
**Expected:** `sw.js` listed as registered and activated for the origin
**Why human:** Service worker lifecycle (install, activate, claim) requires a live browser

#### 3. API Routes Bypass Service Worker Cache

**Test:** Same preview server, DevTools > Network tab; navigate to trigger API calls (e.g. open Openings page)
**Expected:** Requests to `/analysis/*`, `/games/*`, etc. do NOT show "(ServiceWorker)" in the Size column — they show a byte count from the network
**Why human:** ServiceWorker size-column annotation requires Network tab inspection in a real browser

#### 4. LAN Phone Testing (DEV-01)

**Test:** Run `cd frontend && npm run dev:mobile`, find the LAN IP printed by Vite (e.g. `http://192.168.x.x:5173`), open it on a phone on the same Wi-Fi
**Expected:** Chessalytics app loads on the phone browser; hot-reload works
**Why human:** Requires physical phone and local Wi-Fi network

#### 5. Cloudflare Tunnel HTTPS Access (DEV-02, optional)

**Test:** Install `cloudflared` CLI if not present; run `cd frontend && TUNNEL=true npm run dev:mobile` in one terminal and `npm run dev:tunnel` in another; open the printed `*.trycloudflare.com` URL on a phone on a different network
**Expected:** Chessalytics app loads over HTTPS on the phone; no WebSocket/HMR errors
**Why human:** Requires cloudflared CLI, physical phone, and a network external to the dev machine

---

### Summary

All eight must-have truths are verified at all three levels (exists, substantive, wired). The build pipeline produces a valid PWA manifest and service worker with the correct NetworkOnly API-route strategy. All five requirements (PWA-01 through PWA-03, DEV-01, DEV-02) are satisfied by the codebase. No anti-patterns or stubs were found. The only open items are human-in-the-loop browser and device tests that cannot be verified programmatically. Automated confidence is high.

---

_Verified: 2026-03-20T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
