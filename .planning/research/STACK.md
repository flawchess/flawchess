# Stack Research

**Domain:** Chess analysis platform — v1.2 Mobile & PWA
**Researched:** 2026-03-20
**Confidence:** HIGH

## Scope Note

This document covers ONLY additions and changes needed for v1.2. The base
stack (FastAPI, React 19, PostgreSQL, SQLAlchemy async, TanStack Query,
Tailwind v4, shadcn/ui, Recharts, react-chessboard, chess.js, python-chess)
is validated and in production. Those choices are not re-evaluated here.

The actual installed Vite version is **7.3.1** (not 5.x as stated in the
project's stated stack — the lockfile reflects the real version).

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| vite-plugin-pwa | ^1.2.0 | PWA manifest + service worker generation | De facto standard for Vite-based PWA setup; zero-config `generateSW` mode handles manifest, precaching, and service worker registration automatically; integrates directly into `vite.config.ts` |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| workbox-window | ^7.x | Service worker registration helper from the browser side | Installed automatically as a peer dep by vite-plugin-pwa; used via `virtual:pwa-register` import for the update-reload prompt |
| shadcn Sheet | (already in shadcn, not yet installed) | Slide-in drawer for hamburger navigation on mobile | Install via `npx shadcn@latest add sheet`; built on Radix UI Dialog primitives already in the project; `side="left"` opens from the left edge for a conventional mobile nav drawer |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Vite `--host` flag | Expose dev server to local network for phone testing on same Wi-Fi | Add `"dev:mobile": "vite --host"` to `package.json` scripts; Vite will print the LAN IP (e.g., `http://192.168.x.x:5173`); phone and laptop must be on the same network |
| ngrok (free tier) | Expose localhost over HTTPS to the internet for phone testing off-network | Free tier has a 2-hour session limit and random URL per restart; sufficient for occasional phone debugging sessions; install via `npm install -g ngrok` or system package manager |

---

## Installation

```bash
# Frontend — PWA plugin (one new package)
npm install -D vite-plugin-pwa

# shadcn Sheet component (no new npm package — shadcn copies source into project)
npx shadcn@latest add sheet

# Optional: ngrok for off-network phone testing
npm install -g ngrok
# OR: snap install ngrok / brew install ngrok
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| vite-plugin-pwa `generateSW` | `injectManifest` (manual service worker) | Only if custom SW logic is needed beyond precaching (push notifications, background sync); not needed for this milestone |
| vite-plugin-pwa | Manual `manifest.json` + hand-written service worker | Only for projects with unusual requirements; `vite-plugin-pwa` covers 100% of the v1.2 use case with less surface area |
| shadcn Sheet for mobile nav | shadcn Drawer (Vaul-based) | Drawer is bottom-up and feels more like a mobile action sheet; Sheet from the left edge is the conventional hamburger nav pattern |
| Vite `--host` (same network) | ngrok / Cloudflare Tunnel | Use tunnel when testing on a phone not on the same network, or when HTTPS is required for a specific PWA feature (e.g., install prompt on some browsers) |
| ngrok | Cloudflare Tunnel (`cloudflared`) | Cloudflare Tunnel is faster (5.79 MB/s vs ngrok's lower speeds) and free with no session time limit; use it for longer testing sessions or team collaboration; requires a Cloudflare account |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| A separate PWA framework (Workbox CLI, `@angular/service-worker`, etc.) | Adds a second toolchain alongside Vite; `vite-plugin-pwa` is already the Vite-native solution | `vite-plugin-pwa` |
| `vite-plugin-mkcert` for local HTTPS | Adds certificate management overhead; not needed because localhost is a secure origin for service workers, and same-network testing via `--host` works over HTTP on mobile Chrome/Safari for development | Vite `--host` for same-network, ngrok for HTTPS over the internet |
| Custom service worker caching for API responses | Dynamic chess data should NOT be cached stale — analysis results must always be fresh | Let Workbox's `generateSW` precache only static assets; API requests fall through to the network |
| React Native or Capacitor | PWA is the stated goal and sufficient for this use case; native wrappers add platform-specific build complexity | Standard PWA with `vite-plugin-pwa` |
| A React navigation library (React Navigation, etc.) | Existing react-router-dom already handles routing; a mobile nav drawer is a UI pattern, not a routing change | shadcn Sheet + existing react-router-dom `<Link>` components inside the drawer |

---

## PWA Configuration Notes

**`generateSW` strategy is correct for this project.** The app is a React SPA with JWT auth. Static shell assets (JS bundles, CSS, icons) should be precached. API calls to `/api/*` must not be cached — they are user-specific and time-sensitive.

**HTTPS for PWA install prompt:** PWAs can be installed from HTTPS origins only. On localhost the browser grants an exception, so development install testing works. For remote phone testing, use ngrok (provides HTTPS automatically) rather than bare `--host` (HTTP).

**iOS Safari limitations:** iOS supports PWA installation via "Add to Home Screen" but does not support the `beforeinstallprompt` event. An install prompt button in the UI will only work on Android Chrome. Consider showing a manual instruction banner for iOS users instead of a programmatic prompt.

**Service worker scope:** `vite-plugin-pwa` registers the service worker at the root scope by default. No configuration change needed.

---

## Version Compatibility

| Package | Current Version | v1.2 Compatibility | Notes |
|---------|----------------|---------------------|-------|
| vite | ^7.3.1 | vite-plugin-pwa ^1.2.0 requires Vite 5+; v7 is compatible | HIGH confidence |
| react | ^19.2.0 | vite-plugin-pwa is framework-agnostic; no peer dep on React version | HIGH confidence |
| @vitejs/plugin-react | ^5.1.1 | Used alongside vite-plugin-pwa in the same `plugins` array; no conflict | HIGH confidence |
| @tailwindcss/vite | ^4.2.1 | Used alongside vite-plugin-pwa; no conflict | HIGH confidence |
| radix-ui | ^1.4.3 | shadcn Sheet uses Radix Dialog under the hood; already present | HIGH confidence |

---

## Sources

- [vite-pwa/vite-plugin-pwa GitHub](https://github.com/vite-pwa/vite-plugin-pwa) — v1.2.0 release confirmed, Vite 5+ requirement from v0.17, workbox v7 from v0.16 — HIGH confidence
- [Vite PWA official guide](https://vite-pwa-org.netlify.app/guide/) — v1.2.0 shown in docs, `generateSW` vs `injectManifest` strategies — HIGH confidence
- [Vite PWA service worker strategies](https://vite-pwa-org.netlify.app/guide/service-worker-strategies-and-behaviors.html) — `generateSW` recommended default for SPAs — HIGH confidence
- [shadcn Sheet docs](https://ui.shadcn.com/docs/components/sheet) — Sheet component, `side` prop, Radix Dialog foundation, install command — HIGH confidence
- [shadcn Mobile Menu Sheet pattern](https://www.shadcn.io/patterns/sheet-navigation-1) — hamburger nav using Sheet confirmed as documented pattern — HIGH confidence
- [MDN: Making PWAs installable](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable) — HTTPS requirement, localhost exception — HIGH confidence
- [Vite --host network access discussions](https://github.com/vitejs/vite/discussions/15251) — same-network mobile testing via `--host` confirmed — HIGH confidence
- [ngrok pricing and limits](https://ngrok.com/docs/pricing-limits) — 2-hour free tier session limit confirmed — MEDIUM confidence
- [LocalCan: ngrok vs Cloudflare Tunnel speed test 2025](https://www.localcan.com/blog/ngrok-vs-cloudflare-tunnel-vs-localcan-speed-test-2025) — Cloudflare Tunnel performance advantage — MEDIUM confidence
- `frontend/package.json` codebase inspection — actual installed Vite version is 7.3.1; shadcn Sheet not yet present in `components/ui/` — HIGH confidence

---
*Stack research for: Chessalytics v1.2 Mobile & PWA*
*Researched: 2026-03-20*
