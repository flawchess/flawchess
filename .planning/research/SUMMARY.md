# Project Research Summary

**Project:** Chessalytics v1.2 — Mobile & PWA
**Domain:** Mobile PWA enhancement for existing chess analysis SPA
**Researched:** 2026-03-20
**Confidence:** HIGH

## Executive Summary

Chessalytics v1.2 is a focused mobile and PWA milestone on top of a fully operational v1.1 platform. The existing stack (React 19, Vite 7, Tailwind v4, shadcn/ui, FastAPI backend) is production-validated and requires no changes. The entire scope is frontend-only: a hamburger nav drawer for mobile viewports, PWA installability via `vite-plugin-pwa`, service worker asset caching, and responsive polish (touch target sizing, overflow fixes). The backend is untouched — no new API routes, no schema changes.

The recommended approach is minimal and additive: one new npm dev dependency (`vite-plugin-pwa`), one new shadcn component (`Sheet`), one new React component (`MobileNav`), and targeted modifications to `vite.config.ts`, `App.tsx`, and `index.html`. The architecture is well-understood — `generateSW` mode handles all precaching automatically, and the `NetworkOnly` service worker strategy for all API routes is mandatory to prevent stale chess analysis data from being served from cache.

The primary risks are iOS-specific: storage isolation between Safari and the installed PWA standalone context means users must log in again after installing, and the HTML5 Drag-and-Drop API is absent on iOS Safari, breaking piece dragging. Both are well-documented platform limitations with clear mitigations — explicit installation instructions and click-to-move as the mobile move-entry pattern. PWA service worker caching of API routes is the most dangerous technical pitfall and must be explicitly prevented from day one; get this wrong and users see stale analysis data after importing new games.

## Key Findings

### Recommended Stack

The stack additions for v1.2 are minimal. Only one new npm package is required: `vite-plugin-pwa ^1.2.0`, which is fully compatible with the project's current Vite 7.3.1. The `shadcn Sheet` component is added via the shadcn CLI (no new npm package). `workbox-window` is installed automatically as a peer dependency. For phone testing during development, Cloudflare Tunnel (`cloudflared`) is preferred over ngrok — it is faster (5.8 MB/s vs 1.1 MB/s), completely free with no session time limit, and requires no account for ephemeral HTTPS URLs.

**Core technologies:**
- `vite-plugin-pwa ^1.2.0`: PWA manifest + service worker generation — de facto Vite-native standard; zero-config `generateSW` mode covers 100% of this use case
- `shadcn Sheet`: Mobile navigation drawer — built on Radix UI Dialog already in project; left-side slide-in is the conventional hamburger nav pattern
- Cloudflare Tunnel (`cloudflared`): Phone dev testing over HTTPS — required to test PWA install prompt and service worker on real devices

**What NOT to add:**
- React Native, Capacitor, or any native wrapper — PWA is the stated goal and sufficient
- Offline API caching (IndexedDB, TanStack Query persistence adapter) — chess data is user-specific, authenticated, and must always be fresh
- Custom hand-written service worker — `generateSW` covers 100% of v1.2 requirements with less surface area

### Expected Features

**Must have (table stakes):**
- Hamburger nav drawer — horizontal nav is invisible or overflows at <640px; blocking usability gap on mobile
- PWA manifest — required for "Add to Home Screen" on Android Chrome and iOS Safari; must use PNG icons (not SVG)
- Service worker with Workbox precaching — repeat visits on mobile networks must feel instant; all static assets precached, all API routes `NetworkOnly`
- Touch target audit — minimum 44×44px on all interactive elements; current shadcn `size="sm"` buttons are 36px — too small
- No horizontal scroll at 375px viewport — iPhone SE baseline; verify Openings filter sidebar and move explorer table
- Dev tunnel workflow — one-command HTTPS exposure for phone testing (`cloudflared tunnel --url http://localhost:5173`)

**Should have (competitive):**
- Custom PWA install prompt — in-app "Install" button after Lighthouse PWA audit confirms installability; `beforeinstallprompt` for Android Chrome; manual "Share → Add to Home Screen" instructions for iOS Safari
- Safari install instructions tooltip — iOS users have no programmatic install event; a dismissible banner improves discoverability

**Defer (v2+):**
- TanStack Query persistence adapter — only if analysis queries create noticeable latency on slow mobile connections
- Bottom navigation bar — only if UX testing shows hamburger is a persistent pain point
- Push notifications for import completion — only if user demand is explicit; requires VAPID keys and background SW messaging

### Architecture Approach

The architecture for v1.2 is a frontend-only overlay on the existing SPA. The Vite build gains a PWA plugin that emits `sw.js` and `manifest.webmanifest` at build time — no runtime code to maintain. The `NavHeader` in `App.tsx` gains a responsive split: desktop keeps the horizontal link bar (`hidden md:flex`), mobile gets a new `MobileNav` component wrapping a shadcn `Sheet` with the same nav links as large touch targets. All existing pages remain structurally unchanged; the single-column mobile layout is already implemented. The FastAPI backend is completely unaffected.

**Major components:**
1. `MobileNav` (new) — Sheet-based slide-out drawer; self-contained; shares `NAV_ITEMS` and `isActive()` with the desktop nav
2. `VitePWA()` plugin (new, build-time) — generates service worker and manifest; configured with `NetworkOnly` for all backend API paths
3. `public/icons/` (new assets) — 192×192 and 512×512 PNG icons; must be PNG; 512px must include `purpose: "any maskable"` with safe-zone content
4. Touch target sizing (modified) — `BoardControls.tsx`, `FilterPanel.tsx`, possibly `MoveList.tsx`; responsive height classes to reach 44px minimum on mobile

### Critical Pitfalls

1. **SW caches API responses** — configure `NetworkOnly` for all `/auth /analysis /games /imports /position-bookmarks /stats /users /health` paths in Workbox `runtimeCaching`; verify via Network tab that no API request shows `(ServiceWorker)` source after SW installs
2. **Users stuck on stale app version** — use `workbox-window` update notification: on `onNeedRefresh`, show a toast with a "Reload" button calling `updateServiceWorker(true)`; set `Cache-Control: no-cache` on `sw.js` at the server level; do not auto-reload silently (breaks in-progress analysis sessions)
3. **iOS PWA auth session isolation** — iOS standalone `WKWebView` has completely separate storage from Safari; JWT tokens do not transfer; accept that first login is required in standalone mode, ensure manifest `scope: "/"` keeps OAuth callback within the PWA, test Google SSO on a physical iPhone in standalone mode
4. **react-chessboard drag broken on iOS Safari** — HTML5 DnD API is absent on iOS; disable `arePiecesDraggable` on touch devices and rely on click-to-move (`onSquareClick`) which already works; do not add a touch DnD polyfill
5. **Vite blocks tunnel requests** — Vite 5.4.12+ rejects unknown `Host` headers; add `allowedHosts: 'all'` and `hmr.clientPort: 443` via env variable only; never commit `allowedHosts: 'all'` as the default (DNS rebinding risk)

## Implications for Roadmap

Based on research, the v1.2 work naturally groups into three phases ordered by dependency and risk:

### Phase 1: PWA Foundation + Dev Workflow

**Rationale:** The PWA manifest and service worker are prerequisites for installability and must be correct before any other PWA-related work. The `NetworkOnly` API caching strategy must be locked in before the SW ships — retrofitting it post-deployment is painful. Dev workflow setup (Vite `server.host`, Cloudflare Tunnel) enables phone testing for all subsequent phases. This phase also sets the manifest `scope: "/"` correctly, preventing the iOS OAuth pitfall.

**Delivers:** Installable PWA passing Lighthouse audit, fast repeat loads via Workbox precaching, SW update notification toast, phone testing capability via Cloudflare Tunnel

**Addresses:** PWA manifest (P1), service worker (P1), dev tunnel workflow (P1)

**Avoids:** SW caches API responses (Pitfall 1), stale app version (Pitfall 2), iOS auth session isolation (Pitfall 3 — manifest scope set correctly here), Vite tunnel blocking (Pitfall 5)

### Phase 2: Mobile Navigation

**Rationale:** Mobile nav is independent of the PWA layer but benefits from having a testable phone workflow from Phase 1. Adding the hamburger Sheet is a contained change to `App.tsx` with a new `MobileNav` component. The viewport-fit/safe-area fix belongs here as a prerequisite for the nav header looking correct on notched iPhones (iPhone X through iPhone 16).

**Delivers:** Functional hamburger nav on all mobile viewports, correct iOS notch/Dynamic Island safe-area handling, `MobileNav` component with full `data-testid` coverage

**Addresses:** Mobile nav (P1), viewport-fit / safe-area insets (PITFALLS.md Pitfall 6)

**Avoids:** Hamburger menu staying open after navigation (close on route change via `useEffect([location.pathname])`), background scroll lock on iOS (must use `position: fixed` + `overflow: hidden`), replacing desktop nav universally (keep `hidden md:flex` breakpoint split)

### Phase 3: Mobile UX Polish + Install Prompt

**Rationale:** Touch target audit and overflow fixes can only be validated on a real device — requires Phase 1 dev workflow. The custom install prompt is deferred to after the Lighthouse PWA audit passes in production, ensuring installability criteria are met before building UI around it. The iOS chessboard drag fix belongs here as the most critical chessboard interaction fix for mobile users.

**Delivers:** All interactive elements at 44px minimum tap target, no horizontal scroll at 375px, iOS Safari install instructions, Android Chrome install prompt, reliable piece movement on iOS via click-to-move

**Addresses:** Touch target audit (P1), horizontal overflow fixes (P1), custom install prompt (P2), Safari install instructions (P2)

**Avoids:** react-chessboard drag broken on iOS (Pitfall 4 — `arePiecesDraggable` conditional set here), touch targets too small, page scroll conflict with chessboard touch

### Phase Ordering Rationale

- PWA foundation must come first because the service worker caching strategy is the hardest mistake to undo post-deployment, and because later phases need a testable phone environment
- Mobile nav is cleanly separable from the PWA layer — no shared code — but benefits from the dev workflow being in place for device testing
- Polish is last because it requires real-device testing and is incremental by nature; the install prompt is gated on Lighthouse audit confirmation from Phase 1

### Research Flags

All three phases have standard, well-documented patterns. No phase requires deeper research via `research-phase`:

- **Phase 1 — PWA Foundation:** `vite-plugin-pwa` is comprehensively documented; `generateSW` mode is the standard SPA approach; configuration patterns are directly available in official docs
- **Phase 2 — Mobile Navigation:** shadcn Sheet pattern is documented with example code; `hidden md:flex` breakpoint split is standard; safe-area CSS is a one-line addition
- **Phase 3 — Mobile Polish:** Touch target sizing is mechanical (audit + bump to 44px); overflow fixes are standard Tailwind; install prompt patterns are MDN-documented

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against vite-plugin-pwa releases and npm; Vite 7 compatibility confirmed from release metadata; actual project `package.json` inspected directly |
| Features | HIGH | PWA mechanics from MDN; shadcn Sheet from official docs; iOS limitations consistent across multiple authoritative sources |
| Architecture | HIGH | Based on direct codebase analysis of `App.tsx`, `vite.config.ts`, `package.json`, `Openings.tsx`; no inferred structure |
| Pitfalls | HIGH (SW/iOS/Vite), MEDIUM (react-chessboard touch specifics) | iOS storage isolation and Vite Host header behavior are verified from GitHub discussions and official docs; react-chessboard mobile specifics from README only |

**Overall confidence:** HIGH

### Gaps to Address

- **react-chessboard touch drag on Android Chrome:** Library advertises mobile support but touch drag vs. click-to-move behavior on Android has not been verified on a real device. Mitigate by testing on physical Android during Phase 3; click-to-move is the confirmed fallback regardless of drag outcome.
- **Google SSO OAuth in PWA standalone on iOS:** The storage isolation pitfall is well-documented but the specific OAuth callback behavior with the project's FastAPI-Users + Google SSO setup has not been tested on a physical iPhone. Requires hands-on validation during Phase 1. The mitigation (manifest `scope: "/"`) is correct; acceptance that re-login is required should be documented in any installation instructions.
- **Cloudflare Tunnel + Vite proxy compatibility:** The tunnel routes to Vite, which proxies `/api/*` to FastAPI on localhost. This should work (both on same machine) but has not been verified end-to-end with this specific proxy configuration. Test during Phase 1 dev workflow setup before relying on it for all subsequent phone testing.

## Sources

### Primary (HIGH confidence)
- [vite-plugin-pwa GitHub + official guide](https://vite-pwa-org.netlify.app/guide/) — installation, generateSW strategy, workbox config, v1.2.0 Vite 7 compatibility
- [MDN: Making PWAs Installable](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable) — manifest requirements, HTTPS requirement, localhost exception
- [MDN: beforeinstallprompt](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeinstallprompt_event) — Chromium-only; iOS has no equivalent event
- [shadcn Sheet docs + mobile nav pattern](https://ui.shadcn.com/docs/components/sheet) — Sheet component, `side` prop, install command
- [iOS PWA limitations — MagicBell 2025/2026](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide) — storage isolation, OAuth redirect behavior
- [iOS safe-area-inset — WebKit blog](https://webkit.org/blog/7929/designing-websites-for-iphone-x/) — viewport-fit=cover, env(safe-area-inset-*)
- Codebase: `frontend/src/App.tsx`, `frontend/vite.config.ts`, `frontend/package.json`, `frontend/src/pages/Openings.tsx` — direct structural analysis
- [Vite server.allowedHosts — GitHub discussions](https://github.com/vitejs/vite/discussions/19426) — Host header blocking behavior with tunnels

### Secondary (MEDIUM confidence)
- [Cloudflare Tunnel vs ngrok 2025 benchmark](https://www.localcan.com/blog/ngrok-vs-cloudflare-tunnel-vs-localcan-speed-test-2025) — Cloudflare Tunnel performance advantage (5.8 MB/s vs 1.1 MB/s)
- [react-chessboard GitHub (Clariity)](https://github.com/Clariity/react-chessboard) — mobile support claim, click-to-move via `onSquareClick`
- [Touch target UX best practices 2025](https://edesignify.com/blogs/tap-targets-and-touch-zones-mobile-ux-that-works) — 44px minimum recommendation

### Tertiary (LOW confidence)
- ngrok free tier session limits — 2-hour limit noted; prefer Cloudflare Tunnel to avoid this constraint entirely

---
*Research completed: 2026-03-20*
*Ready for roadmap: yes*
