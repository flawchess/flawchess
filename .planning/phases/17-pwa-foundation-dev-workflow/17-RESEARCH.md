# Phase 17: PWA Foundation + Dev Workflow - Research

**Researched:** 2026-03-20
**Domain:** Vite PWA setup (vite-plugin-pwa), service worker caching strategy, web app manifest, icon generation, phone testing workflow (LAN + HTTPS tunnel)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**App Identity & Icons**
- Knight silhouette as the app icon — most distinctive chess piece, instantly recognizable
- Generate 192px and 512px PNG icons (required for PWA installability)
- Replace current `vite.svg` favicon with the chess knight icon
- Dark theme color (#0a0a0a or similar) matching existing dark UI — status bar blends seamlessly
- App name: "Chessalytics", short_name: "Chessalytics"

**Service Worker Update Strategy**
- Auto-update on next visit — new service worker activates silently on next page load
- No reload toast or manual update prompt
- Use `skipWaiting` + `clientsClaim` so the new SW takes control immediately on next navigation
- Simpler for users; acceptable that one visit may see stale static assets

**Dev Tunnel Workflow**
- Easiest-to-set-up tunnel wins — Claude picks between Cloudflare Tunnel and ngrok based on simplicity
- Also add `vite --host` script for same-network LAN testing (no HTTPS, but faster iteration)
- Vite proxy routes need `allowedHosts` config for tunnel compatibility (Vite 5.4.12+ DNS rebinding protection)

**PWA Install Scope**
- `start_url: "/"` — hits auth check, redirects to /openings if logged in
- `scope: "/"` — keeps OAuth callbacks within PWA scope
- `display: "standalone"` — no browser chrome
- Accept re-login on iOS — storage isolation between Safari and installed PWA is a platform constraint, no special handling needed
- No warning banner for iOS re-login — keep it simple

**Service Worker Caching**
- `generateSW` mode via vite-plugin-pwa — zero manual service worker code
- Precache all static assets (JS, CSS, fonts, icons)
- `NetworkOnly` for all API routes: `/auth`, `/analysis`, `/games`, `/imports`, `/position-bookmarks`, `/stats`, `/users`, `/health`
- `openings.tsv` in public/ should be precached (368KB, static chess opening data)

### Claude's Discretion
- Exact tunnel tool choice (Cloudflare Tunnel vs ngrok) — pick easiest setup
- Level of documentation (scripts + README section vs scripts-only)
- Icon generation approach (SVG source → PNG conversion method)
- Exact dark theme hex color for manifest
- start_url: `/` vs `/openings` — pick what works best with auth flow

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PWA-01 | App has a web manifest with name, icons, theme color, and display:standalone | vite-plugin-pwa `manifest` config object in `VitePWA()` plugin generates `manifest.webmanifest` automatically at build; injected into `index.html` via plugin |
| PWA-02 | Service worker precaches static assets for fast repeat loads (NetworkOnly for API routes) | `generateSW` mode with workbox `runtimeCaching` using `NetworkOnly` handler for all 8 API route prefixes; static assets precached automatically via Workbox's asset manifest |
| PWA-03 | App has custom chess-themed icons (192px + 512px PNG) replacing default Vite favicon | Create `public/icons/icon-192.png` and `public/icons/icon-512.png` from SVG source; update `index.html` favicon link and add `apple-touch-icon`; reference icons in manifest config |
| DEV-01 | npm script exposes Vite dev server on LAN for same-network phone testing | Add `"dev:mobile": "vite --host"` to `package.json`; Vite prints LAN IP; `server.host: true` in `vite.config.ts` |
| DEV-02 | Documented one-command Cloudflare Tunnel setup for HTTPS phone testing | `cloudflared tunnel --url http://localhost:5173`; add `allowedHosts: 'all'` + `hmr.clientPort: 443` via `TUNNEL=true` env guard in `vite.config.ts`; document in README |
</phase_requirements>

---

## Summary

Phase 17 adds PWA installability and a phone testing workflow to an existing Vite 7 + React 19 SPA. The work is entirely frontend — no backend changes. The existing project has no PWA infrastructure: `package.json` has no `vite-plugin-pwa`, `vite.config.ts` has only react and tailwindcss plugins, and `index.html` has the default Vite favicon.

The standard tool for this stack is `vite-plugin-pwa` v1.2.0 (current as of 2026-03-20, verified via npm). It wraps Workbox's `generateSW` approach: configure the plugin once in `vite.config.ts`, and at build time it emits `sw.js` (service worker) and `manifest.webmanifest` (web app manifest) into the dist. Zero hand-written service worker code. The user has locked `generateSW` mode, `autoUpdate` register type, and `NetworkOnly` for all API routes — these choices are all correct for this app.

The dev workflow additions are a one-liner script (`vite --host`) for LAN testing and Cloudflare Tunnel (`cloudflared`) for HTTPS phone testing. Cloudflare Tunnel is the right choice over ngrok: no session time limit, no account required for ephemeral URLs, and higher throughput. The Vite `allowedHosts` pitfall (DNS rebinding protection added in Vite 5.4.12+) must be handled via an env-guarded override — never committed as the default.

**Primary recommendation:** Install `vite-plugin-pwa@^1.2.0`, configure `VitePWA()` in `vite.config.ts` with the manifest and `NetworkOnly` workbox rules, create PNG icons in `public/icons/`, update `index.html`, and add `dev:mobile` and `dev:tunnel` scripts to `package.json`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vite-plugin-pwa | ^1.2.0 | PWA manifest + service worker generation via Workbox | De facto standard for Vite PWA; zero-config `generateSW` mode; Vite 7 compatible; workbox v7 peer dep |
| workbox-window | ^7.4.0 | SW registration helper (peer dep, auto-installed) | Installed automatically by vite-plugin-pwa; provides `virtual:pwa-register` import |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `vite --host` | Expose dev server on all LAN interfaces | Built into Vite; no install needed |
| cloudflared | HTTPS tunnel for off-network phone testing | Free, no account for ephemeral URLs, no session limit |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cloudflared | ngrok | ngrok free tier has 2-hour session limit and random URL per restart; cloudflared is faster and free with no limit |
| `generateSW` | `injectManifest` | injectManifest allows custom SW code — only needed for push notifications or background sync (not required here) |
| `registerType: 'autoUpdate'` | `registerType: 'prompt'` | prompt mode requires building a reload UI; autoUpdate is correct for a data analysis tool with no in-flight work to lose |

**Installation:**
```bash
npm install -D vite-plugin-pwa

# cloudflared (for dev tunnel — no npm package)
# Linux: curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared.deb
# macOS: brew install cloudflared
```

**Version verification (confirmed 2026-03-20):**
```bash
npm view vite-plugin-pwa version   # → 1.2.0
npm view workbox-window version    # → 7.4.0
```

---

## Architecture Patterns

### Recommended Project Structure (additions only)

```
frontend/
├── vite.config.ts              # MODIFY — add VitePWA plugin, server.host: true, allowedHosts guard
├── index.html                  # MODIFY — theme-color meta, apple-touch-icon, favicon → /icons/icon-192.png
├── package.json                # MODIFY — add dev:mobile and dev:tunnel scripts
├── public/
│   ├── manifest.webmanifest    # AUTO-GENERATED by vite-plugin-pwa at build (do not create manually)
│   └── icons/
│       ├── icon-192.png        # NEW — required for Android install prompt
│       └── icon-512.png        # NEW — required for Android install prompt (maskable)
└── src/
    └── main.tsx                # NO CHANGE — vite-plugin-pwa auto-registers SW via virtual module
```

### Pattern 1: VitePWA Plugin Configuration

**What:** Add `VitePWA()` to the plugins array in `vite.config.ts`. At build time the plugin emits `sw.js` and injects the manifest link into `index.html`. In dev mode with `devOptions: { enabled: true }` the SW runs in development, enabling SW testing without a production build.

**When to use:** Always — this is the only change needed to enable PWA behavior.

**Source:** vite-pwa-org.netlify.app/guide/ (HIGH confidence)

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',         // skipWaiting + clientsClaim — matches locked decision
      devOptions: { enabled: true },      // SW active in dev mode for testing
      manifest: {
        name: 'Chessalytics',
        short_name: 'Chessalytics',
        description: 'Chess opening analysis by position',
        theme_color: '#0a0a0a',
        background_color: '#0a0a0a',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',   // maskable needed for Android adaptive icons
          },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        runtimeCaching: [
          {
            // All 8 proxy routes must be NetworkOnly — dynamic, authenticated data
            urlPattern: /^\/(?:auth|analysis|games|imports|position-bookmarks|stats|users|health)\//,
            handler: 'NetworkOnly',
          },
        ],
      },
    }),
  ],
  server: {
    // ... existing proxy config (unchanged)
    host: true,                           // expose on all interfaces for LAN testing (DEV-01)
    hmr: {
      clientPort: 443,                    // required when behind HTTPS tunnel (DEV-02)
    },
    // allowedHosts: 'all' added conditionally via env — see Pattern 3
  },
})
```

**Note on `registerType: 'autoUpdate'`:** This sets `skipWaiting: true` and `clientsClaim: true` in the generated Workbox config, matching the locked user decision. The new service worker activates immediately on the next navigation, silently replacing the old one.

### Pattern 2: Icon Generation

**What:** Create SVG of a chess knight, export to 192×512 PNG. The 512px icon needs a safe zone (content within the central 80%) for Android maskable icon cropping.

**Approach (Claude's discretion — recommended):** Generate SVG inline using a Unicode chess knight or a simple path, then convert to PNG using Inkscape CLI, sharp (npm), or an online tool. The simplest reliable path for a developer without design tools:

```bash
# Option A: Use sharp (npm) to convert SVG to PNG
# Option B: Create PNG directly in any image editor at 192x192 and 512x512
# The key constraint: PNG format, not SVG — iOS home screen requires PNG
```

The icon must have adequate padding for maskable cropping. Recommended: center the knight on a dark (#0a0a0a) background with the knight occupying ~70% of the canvas.

### Pattern 3: Dev Tunnel Workflow

**What:** Two npm scripts for phone testing.

```json
// package.json scripts additions
{
  "dev:mobile": "vite --host",
  "dev:tunnel": "cloudflared tunnel --url http://localhost:5173"
}
```

**`dev:mobile`** — same network LAN testing. Vite prints the LAN IP (`http://192.168.x.x:5173`). Phone and laptop must be on the same WiFi. No HTTPS — suitable for layout iteration but not PWA install testing.

**`dev:tunnel`** — HTTPS tunnel via Cloudflare. The `cloudflared` binary creates an ephemeral URL like `https://random-name.trycloudflare.com`. That URL is publicly accessible from any phone with internet access.

**`allowedHosts` guard in `vite.config.ts`:**

```typescript
// vite.config.ts — conditional allowedHosts, NEVER commit 'all' as default
server: {
  host: true,
  hmr: { clientPort: 443 },
  allowedHosts: process.env.TUNNEL ? 'all' : [],
  proxy: { /* existing proxy config unchanged */ },
}
```

Start tunnel session:
```bash
TUNNEL=true npm run dev &
npm run dev:tunnel
```

**Why `allowedHosts: 'all'` and not `true`:** Vite 6.0.9 has a known bug where `allowedHosts: true` (boolean) is silently ignored. Use the string `'all'` or an explicit list. Source: Vite GitHub discussions (MEDIUM confidence).

### Pattern 4: index.html Updates

**What:** Three changes to the existing `index.html`:

```html
<!-- Replace existing favicon link -->
<link rel="icon" type="image/png" href="/icons/icon-192.png" />

<!-- Add apple-touch-icon (iOS home screen — NOT covered by manifest link) -->
<link rel="apple-touch-icon" href="/icons/icon-192.png" />

<!-- Add theme-color meta (browser toolbar color on Android) -->
<meta name="theme-color" content="#0a0a0a" />

<!-- Update viewport for safe-area support (needed in Phase 18 for notch) -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
```

**Note:** The manifest link is auto-injected by vite-plugin-pwa — do not add it manually.

### Anti-Patterns to Avoid

- **Caching API routes:** The `runtimeCaching` config MUST explicitly match all 8 API route prefixes with `NetworkOnly`. Omitting this causes stale analysis data after imports — a correctness bug, not a performance trade-off.
- **Committing `allowedHosts: 'all'` as default:** DNS rebinding vulnerability. Always gate behind an env variable.
- **SVG-only icons in the manifest:** iOS requires PNG for home screen icons. The existing `vite.svg` cannot serve as the PWA icon.
- **Using `allowedHosts: true` (boolean):** Silent bug in Vite 6.0.9 — use the string `'all'` instead.
- **Manually creating `manifest.webmanifest` in `public/`:** vite-plugin-pwa auto-generates it from the `manifest` config option. A manually created file will conflict.
- **Registering the service worker manually in `main.tsx`:** `registerType: 'autoUpdate'` handles registration automatically via the plugin's virtual module. No code changes to `main.tsx` are needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Service worker generation | Custom `sw.js` with fetch event listeners | `vite-plugin-pwa` generateSW | Asset manifest versioning, cache invalidation, SPA navigation fallback, and Workbox strategies are extremely subtle — Workbox handles them correctly; custom SWs miss edge cases |
| Web app manifest | Manual `public/manifest.webmanifest` JSON | `manifest` option in `VitePWA()` | Plugin auto-injects the link tag, handles dev vs prod paths, and validates required fields |
| HTTPS tunnel | Custom reverse proxy or SSH tunnel | `cloudflared` | Free, zero-config, handles TLS termination; rolling your own requires certificate management |

**Key insight:** Service worker caching logic has many subtle failure modes (cache versioning, SPA navigation fallback, scope resolution, update lifecycle). Workbox handles these correctly. The `generateSW` abstraction exists precisely to prevent developers from building broken custom service workers.

---

## Common Pitfalls

### Pitfall 1: API Routes Cached by Service Worker

**What goes wrong:** Users see stale win/draw/loss stats after importing new games. TanStack Query invalidation fires but the SW serves the cached response before the network reply arrives.

**Why it happens:** Default `generateSW` precaches Vite build output but does not know which URLs are API endpoints. Without explicit `NetworkOnly` rules, Workbox may apply a default strategy to API routes.

**How to avoid:** The `runtimeCaching` rule in Pattern 1 above covers all 8 proxy routes. Use the regex pattern `/^\/(?:auth|analysis|games|imports|position-bookmarks|stats|users|health)\//` — this matches all sub-paths under each prefix.

**Warning signs:** Network tab shows `(ServiceWorker)` source for `/analysis/*` or `/games/*` requests.

### Pitfall 2: Vite Blocks Tunnel Requests

**What goes wrong:** Phone browser shows "Blocked request. This host is not allowed." when accessing the ngrok/cloudflared URL.

**Why it happens:** Vite 5.4.12+ checks the `Host` header against an allowlist as DNS rebinding protection. The tunnel subdomain is not on the default list.

**How to avoid:** Guard `allowedHosts: 'all'` behind `process.env.TUNNEL`. See Pattern 3.

**Warning signs:** Vite error page on phone; page loads on desktop directly but not through tunnel URL.

### Pitfall 3: HMR Does Not Work Through Tunnel

**What goes wrong:** Page loads on phone via tunnel URL but code edits on desktop do not trigger live reloads.

**Why it happens:** Vite's HMR websocket client defaults to connecting to `localhost:5173`, which is unreachable from the phone. Behind an HTTPS tunnel, the HMR client must connect to port 443.

**How to avoid:** Set `server.hmr.clientPort: 443` in `vite.config.ts`. See Pattern 1.

**Warning signs:** Phone console shows `WebSocket connection failed: ws://localhost:5173`.

### Pitfall 4: PWA Not Installable — Missing Required Manifest Fields

**What goes wrong:** Android Chrome does not show the "Add to Home Screen" install prompt even though the app has a service worker.

**Why it happens:** Chrome's installability criteria require: valid manifest with `name`, `short_name`, `start_url`, `display: 'standalone'`, and at least one 192×192 PNG icon with `purpose: 'any'`. Missing any single field silently suppresses the prompt.

**How to avoid:** After building and previewing, run Lighthouse PWA audit (`npm run preview` then Lighthouse in DevTools). Fix all reported issues before testing on device.

**Warning signs:** Lighthouse PWA audit shows installability failures. No install banner on Android Chrome.

### Pitfall 5: iOS Re-Login After PWA Install

**What goes wrong:** User installs PWA on iPhone, opens it from home screen, sees login page despite being logged in on Safari.

**Why it happens:** iOS PWA runs in an isolated WKWebView with no shared storage with Safari. JWT tokens in `localStorage` are not visible to the installed PWA. This is a permanent iOS platform constraint.

**How to avoid:** Accept and document this behavior. Ensure OAuth callback URL (`/auth/callback`) is within `scope: "/"` so the flow stays in standalone mode. Do NOT attempt to work around this with shared cookies or server-side sessions in Phase 17 — it is out of scope.

**Warning signs:** Only reproducible on physical iPhone in standalone mode; Safari DevTools emulation does not reproduce it.

---

## Code Examples

### VitePWA Full Configuration (verified pattern)

Source: vite-pwa-org.netlify.app/guide/

```typescript
VitePWA({
  registerType: 'autoUpdate',
  devOptions: { enabled: true },
  manifest: {
    name: 'Chessalytics',
    short_name: 'Chessalytics',
    description: 'Chess opening analysis by position',
    theme_color: '#0a0a0a',
    background_color: '#0a0a0a',
    display: 'standalone',
    start_url: '/',
    scope: '/',
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
    ],
  },
  workbox: {
    navigateFallback: '/index.html',
    runtimeCaching: [
      {
        urlPattern: /^\/(?:auth|analysis|games|imports|position-bookmarks|stats|users|health)\//,
        handler: 'NetworkOnly',
      },
    ],
  },
})
```

### Verifying Service Worker Caching (post-build check)

```bash
npm run build
npm run preview
# Open DevTools → Application → Service Workers → confirm registered
# Open DevTools → Application → Cache Storage → confirm static assets precached
# Open DevTools → Network → make an API call → confirm source is NOT "(ServiceWorker)"
```

### Lighthouse PWA Audit

```bash
npm run build && npm run preview
# Then in Chrome DevTools → Lighthouse → check "Progressive Web App" → Generate report
# Must pass: installability, service worker, manifest, icons
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-written service worker with `fetch` event listeners | `vite-plugin-pwa` + Workbox `generateSW` | 2020+ (Workbox 5+) | Eliminates entire class of cache versioning bugs |
| ngrok for dev tunnels | cloudflared (Cloudflare Tunnel) | ~2022 | Free, no session limit, higher throughput |
| `vite-plugin-pwa < 0.17` (Vite 4 support) | `vite-plugin-pwa ^1.2.0` (Vite 5-7 support) | v0.17 / v1.0 | Required upgrade for Vite 7 compatibility |
| `allowedHosts: true` (boolean) in Vite | `allowedHosts: 'all'` (string) | Vite 6.0.9 bug | Boolean silently ignored; use string |

**Deprecated/outdated:**
- **`vite.svg` as favicon:** Replaced by chess knight icon PNG in this phase.
- **Manual `navigator.serviceWorker.register()` in `main.tsx`:** Not needed with vite-plugin-pwa's `registerType`; the plugin handles this via a virtual module.

---

## Open Questions

1. **Icon generation tooling**
   - What we know: 192px and 512px PNG needed; knight silhouette on dark background; must have safe zone for maskable
   - What's unclear: Which tool is available in the dev environment (Inkscape, sharp, ImageMagick, etc.)
   - Recommendation: Use `sharp` npm package or an online SVG-to-PNG converter; document the generation command in the task so the icon can be regenerated if needed

2. **`openings.tsv` in precache**
   - What we know: 368KB static file in `public/`; user decision says it should be precached
   - What's unclear: Workbox's default `maximumFileSizeToCacheInBytes` is 2MB — `openings.tsv` at 368KB is within that limit and will be precached automatically as a `public/` asset
   - Recommendation: No special config needed; verify in Lighthouse that the SW precache includes it after build

3. **Google SSO OAuth in iOS standalone mode**
   - What we know: `scope: "/"` keeps OAuth callbacks in PWA; first login always required after install
   - What's unclear: Whether the OAuth redirect from Google back to `/auth/callback` stays in standalone mode on iOS 17/18
   - Recommendation: Flag this as requiring physical iPhone testing; it is a known limitation but the specific behavior with the existing FastAPI-Users Google OAuth implementation needs verification on device

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend); no frontend test framework currently installed |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

Phase 17 is entirely frontend infrastructure (PWA plugin, icons, manifest, dev scripts). There is no backend code change and no existing frontend test framework (vitest/jest not in `package.json`). All verification is manual or via tooling audits:

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PWA-01 | Web manifest has required fields (name, icons, theme_color, display) | build audit | `npm run build && ls frontend/dist/manifest.webmanifest` | ❌ Wave 0 — verify via build |
| PWA-02 | Service worker registered, static assets precached, API routes NetworkOnly | Lighthouse PWA audit | `npm run build && npm run preview` (manual Lighthouse) | ❌ Wave 0 — manual audit |
| PWA-03 | Custom icons in dist, favicon updated in index.html | file presence | `ls frontend/public/icons/` | ❌ Wave 0 — asset creation |
| DEV-01 | `dev:mobile` script in package.json | smoke test | `npm run dev:mobile --dry-run` (verify script exists) | ❌ Wave 0 — script addition |
| DEV-02 | Cloudflare Tunnel documented and `allowedHosts` guarded | manual verification | `grep -r "allowedHosts" frontend/vite.config.ts` | ❌ Wave 0 — config change |

### Sampling Rate

- **Per task commit:** `npm run build` — confirms no TypeScript errors and plugin generates correctly
- **Per wave merge:** `npm run build && npm run preview` — manual Lighthouse PWA audit
- **Phase gate:** Lighthouse PWA audit passes all installability criteria before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `frontend/public/icons/icon-192.png` — must be created before `npm run build` will produce a valid manifest
- [ ] `frontend/public/icons/icon-512.png` — same
- [ ] Backend test suite unchanged; `uv run pytest` continues to pass (regression guard)

*(No new test files needed — this phase adds build-time tooling and static assets, not business logic)*

---

## Sources

### Primary (HIGH confidence)
- [vite-plugin-pwa GitHub](https://github.com/vite-pwa/vite-plugin-pwa) — v1.2.0 release, Vite 5+ requirement
- [Vite PWA official guide](https://vite-pwa-org.netlify.app/guide/) — generateSW mode, workbox config, manifest options
- [MDN: Making PWAs installable](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable) — HTTPS requirement, manifest criteria
- `frontend/package.json` — confirmed Vite 7.3.1 installed, no vite-plugin-pwa present
- `frontend/vite.config.ts` — confirmed 8 proxy routes, no existing server.host or PWA config
- `frontend/index.html` — confirmed vite.svg favicon, minimal head, dark class
- `npm view vite-plugin-pwa version` — confirmed 1.2.0 (2026-03-20)
- `npm view workbox-window version` — confirmed 7.4.0 (2026-03-20)

### Secondary (MEDIUM confidence)
- [Vite server.allowedHosts bug — GitHub discussion](https://github.com/vitejs/vite/discussions/19426) — `allowedHosts: true` boolean silently ignored in 6.0.9; use string `'all'`
- [Cloudflare Tunnel vs ngrok speed benchmark](https://www.localcan.com/blog/ngrok-vs-cloudflare-tunnel-vs-localcan-speed-test-2025) — Cloudflare 5.79 MB/s vs ngrok 1.1 MB/s
- [PWA iOS limitations — MagicBell](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide) — iOS storage isolation, no beforeinstallprompt

### Tertiary (LOW confidence)
- None — all critical claims verified by primary sources

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — npm registry confirms vite-plugin-pwa 1.2.0 current; workbox 7.4.0 peer dep
- Architecture: HIGH — patterns derived from official vite-plugin-pwa docs and direct codebase inspection
- Pitfalls: HIGH (API caching, iOS storage isolation) / MEDIUM (allowedHosts boolean bug, iOS OAuth standalone behavior)

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable libraries; vite-plugin-pwa releases infrequently)
