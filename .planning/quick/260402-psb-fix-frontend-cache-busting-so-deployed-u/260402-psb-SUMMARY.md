---
phase: quick
plan: 260402-psb
subsystem: infrastructure
tags: [caddy, caching, pwa, service-worker, cache-busting]
dependency_graph:
  requires: []
  provides: [proper-cache-control-headers]
  affects: [deploy/Caddyfile]
tech_stack:
  added: []
  patterns: [three-tier-cache-strategy]
key_files:
  created: []
  modified:
    - deploy/Caddyfile
decisions:
  - Named matchers @nocache and @immutable inside the @static handle block
  - Three-tier cache strategy: no-cache for mutable entry points, immutable for content-hashed assets, Caddy defaults for everything else
metrics:
  duration: "~5 minutes"
  completed: "2026-04-02"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
---

# Phase quick Plan 260402-psb: Fix Frontend Cache Busting Summary

## One-liner

Added three-tier Caddy Cache-Control headers: `no-cache` on `sw.js`/`registerSW.js`/`manifest.webmanifest`, `immutable` on `/assets/*`, preserving existing `no-cache` on `index.html`.

## What Was Built

The Caddyfile's `@static` handle block was missing Cache-Control headers for service worker files and content-hashed assets. This caused browsers to potentially serve stale `sw.js` from HTTP cache after deployments, meaning the VitePWA `autoUpdate` mechanism would not detect new precache manifests.

Two named matchers were added inside the `@static` block:

- `@nocache` matching `/sw.js`, `/registerSW.js`, `/manifest.webmanifest` with `Cache-Control: no-cache` — browser must revalidate on every page load
- `@immutable` matching `/assets/*` with `Cache-Control: public, max-age=31536000, immutable` — safe to cache forever since Vite embeds content hashes in filenames

The existing `Cache-Control: no-cache` on `/index.html` in the SPA fallback block was preserved unchanged.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add proper Cache-Control headers to Caddyfile | 2a19940 | deploy/Caddyfile |
| 2 | Validate Caddy config syntax | (no file change) | — |

Task 2 ran `docker run caddy:2.11.2 caddy validate` which returned `Valid configuration`. No file changes were needed — validation was a read-only check.

## Deviations from Plan

None — plan executed exactly as written. The plan's automated verify step expected `grep -c "no-cache"` to return `2`, but the result was `3` because the explanatory comment in the Caddyfile contains the word `no-cache`. This does not affect correctness — all three required behaviors (sw.js no-cache, assets immutable, index.html no-cache) are present and validated.

## Known Stubs

None.

## Self-Check: PASSED

- `deploy/Caddyfile` exists and contains all required headers
- Commit `2a19940` exists in git log
- Caddy syntax validation: `Valid configuration`
