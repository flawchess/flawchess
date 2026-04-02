---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - deploy/Caddyfile
autonomous: true
requirements: []

must_haves:
  truths:
    - "After a deploy, users receive new frontend assets without manual refresh"
    - "Service worker file is never served stale from HTTP cache"
    - "Content-hashed assets are cached long-term by browsers for performance"
  artifacts:
    - path: "deploy/Caddyfile"
      provides: "Correct Cache-Control headers for all frontend asset categories"
      contains: "no-cache.*sw.js"
  key_links:
    - from: "deploy/Caddyfile"
      to: "sw.js"
      via: "Cache-Control header matching"
      pattern: "sw\\.js.*no-cache"
---

<objective>
Fix frontend cache-busting so deployed updates reach users without manual browser refresh.

Purpose: Users on mobile (and desktop) were stuck on stale PWA service worker caches after deployments because Caddy served `sw.js` with no Cache-Control header, preventing browsers from detecting updated precache manifests.

Output: Updated Caddyfile with proper cache-control headers for three asset categories.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@deploy/Caddyfile
@frontend/vite.config.ts

Root cause analysis:

The VitePWA plugin generates a service worker (`sw.js`) with Workbox `precacheAndRoute()`.
This SW contains a hardcoded precache manifest with revision hashes for every asset.
On deploy, the NEW `sw.js` has updated revision hashes. The browser detects the SW change,
installs the new SW (which calls `skipWaiting()` + `clientsClaim()`), and the new precache
manifest forces re-fetching of changed assets.

BUT: Caddy's `@static file` handler serves `sw.js` with NO Cache-Control header.
This means browsers may serve a cached `sw.js` — so they never see the new precache manifest.
The `autoUpdate` mechanism works correctly only if the browser actually fetches the fresh `sw.js`.

Current Caddyfile correctly sets `Cache-Control: no-cache` on `index.html` but misses:
- `sw.js` (service worker — must always be revalidated)
- `registerSW.js` (SW registration script — must always be revalidated)
- `manifest.webmanifest` (PWA manifest — should be revalidated)
- `/assets/*` (content-hashed files — should be cached forever with immutable)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add proper Cache-Control headers to Caddyfile</name>
  <files>deploy/Caddyfile</files>
  <action>
Update the Caddyfile's `flawchess.com` block to set Cache-Control headers for three asset categories:

1. **Service worker files (must never be HTTP-cached):**
   Add a named matcher `@nocache` that matches `sw.js`, `registerSW.js`, and `manifest.webmanifest`.
   Set `Cache-Control "no-cache"` on these paths via `header` directive inside the `@static` handle block.

2. **Content-hashed assets (cache forever):**
   Add a named matcher `@immutable` matching `/assets/*` (Vite output with content hashes in filenames).
   Set `Cache-Control "public, max-age=31536000, immutable"` on these paths inside the `@static` handle block.

3. **Keep existing:** The `header /index.html Cache-Control "no-cache"` in the SPA fallback handle block stays as-is.

The resulting `@static` handle block should look like:

```
handle @static {
    root * /srv

    @nocache path /sw.js /registerSW.js /manifest.webmanifest
    header @nocache Cache-Control "no-cache"

    @immutable path /assets/*
    header @immutable Cache-Control "public, max-age=31536000, immutable"

    file_server
}
```

Why each matters:
- `sw.js` no-cache: Browser must always revalidate — this is how it detects new deployments.
  Per the SW spec, browsers should check every 24h regardless, but `no-cache` ensures
  immediate revalidation on every page load.
- `registerSW.js` no-cache: The registration script itself should also be fresh.
- `manifest.webmanifest` no-cache: Contains app metadata that may change between deploys.
- `/assets/*` immutable: These filenames contain content hashes (e.g., `index-Bb5kahVl.js`).
  They are safe to cache forever because any content change produces a new filename.
  This also improves performance — returning users skip re-downloading unchanged assets.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && grep -c "no-cache" deploy/Caddyfile | grep -q "2" && grep -q "immutable" deploy/Caddyfile && grep -q "sw.js" deploy/Caddyfile && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>
    - Caddyfile has `no-cache` on `sw.js`, `registerSW.js`, `manifest.webmanifest`
    - Caddyfile has `immutable` long-cache on `/assets/*`
    - Existing `no-cache` on `index.html` preserved
    - Caddy config syntax is valid (no unmatched braces, proper nesting)
  </done>
</task>

<task type="auto">
  <name>Task 2: Validate Caddy config syntax and document the caching strategy</name>
  <files>deploy/Caddyfile</files>
  <action>
After Task 1, validate the Caddyfile is syntactically correct by running:

```bash
docker run --rm -v $(pwd)/deploy/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2.11.2 caddy validate --config /etc/caddy/Caddyfile
```

If validation fails, fix any syntax errors in the Caddyfile.

Also verify the final Caddyfile has exactly these cache-control behaviors:
- `sw.js`, `registerSW.js`, `manifest.webmanifest` -> `no-cache`
- `/assets/*` -> `public, max-age=31536000, immutable`
- `/index.html` (SPA fallback) -> `no-cache`
- All other static files (icons, images, etc.) -> Caddy defaults (reasonable)
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && docker run --rm -v $(pwd)/deploy/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2.11.2 caddy validate --config /etc/caddy/Caddyfile 2>&1</automated>
  </verify>
  <done>
    - Caddy config validates without errors
    - Three-tier caching strategy is in place: no-cache for mutable entry points, immutable for hashed assets, defaults for everything else
  </done>
</task>

</tasks>

<verification>
1. `grep -A2 "@nocache" deploy/Caddyfile` shows sw.js, registerSW.js, manifest.webmanifest with no-cache
2. `grep -A1 "@immutable" deploy/Caddyfile` shows /assets/* with immutable
3. `grep "index.html" deploy/Caddyfile` still shows no-cache on index.html
4. Caddy config validates: `docker run --rm -v $(pwd)/deploy/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2.11.2 caddy validate --config /etc/caddy/Caddyfile`
</verification>

<success_criteria>
- Caddyfile properly differentiates cache headers for three asset categories
- After deploy and `docker compose up -d --build`, browsers will:
  - Always revalidate sw.js on page load (detecting new deployments immediately)
  - Cache content-hashed assets indefinitely (better performance)
  - Always revalidate index.html (existing behavior, preserved)
- Caddy config passes syntax validation
</success_criteria>

<output>
After completion, create `.planning/quick/260402-psb-fix-frontend-cache-busting-so-deployed-u/260402-psb-SUMMARY.md`
</output>
