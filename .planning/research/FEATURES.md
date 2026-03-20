# Feature Research

**Domain:** Mobile PWA — data-heavy chess analysis SPA
**Researched:** 2026-03-20
**Confidence:** HIGH (PWA mechanics, nav patterns), MEDIUM (chess-specific mobile touch UX)

---

> This file covers features for v1.2: Mobile & PWA.
> v1.0 and v1.1 features are already shipped (import, analysis, bookmarks, move explorer, openings hub, game cards).
> Core layouts already collapse to single-column on mobile. Chessboard scales via ResizeObserver. Nav header has no mobile menu.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist for a mobile-installable app. Missing these makes it feel unfinished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Hamburger / mobile nav menu | Horizontal nav bar is invisible or overflows at <640px. Users expect a drawer on phones. | LOW | shadcn Sheet is the canonical pattern. Trigger: hamburger icon button. Slides from left. Closes on link tap. Active route highlighted. Logout in sheet. |
| PWA manifest (installable) | "Add to Home Screen" requires a valid manifest. Without it, Chrome/Safari show no install option. | LOW | `vite-plugin-pwa` generates manifest + injects it automatically. Required: `name`, `short_name`, `start_url`, `display: standalone`, `theme_color`, `background_color`, icon set (192×192 + 512×512 PNG). Need custom chess icons — current favicon is vite.svg. |
| Service worker (fast repeat load) | Repeat visits on mobile networks should feel instant. Without SW, every load re-fetches all JS/CSS. | MEDIUM | `vite-plugin-pwa` generates SW via Workbox `generateSW` strategy (zero config for this use case). Precaches all built assets. API routes must be excluded from interception (network-first or bypass). |
| Touch-friendly tap targets | iOS/Android: minimum 44×44px tap targets. Filter pills and board control buttons may be undersized. | LOW | Audit all interactive elements. Tailwind `min-h-11 min-w-11` = 44px. shadcn `size="sm"` is 36px — bump affected controls. 8px gap between adjacent targets. |
| No horizontal scroll | Mobile users expect content within viewport. Wide filter panels or move tables cause horizontal scroll. | LOW | Wrap tables in `overflow-x-auto`. Verify OpeningsPage filter sidebar and move explorer table on narrow screen. Game cards already use 3-row layout. |
| Dev tunnel for phone testing | Devs must test on real device during iteration. Vite proxy routes complicate LAN-only approaches. | LOW | One command: `npx cloudflared tunnel --url http://localhost:5173`. Free, no account, HTTPS automatic, stable. Cloudflare Tunnel is the strongest free option in 2025. |

### Differentiators (Competitive Advantage)

Features that make mobile experience meaningfully better than competitors' mobile web apps.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| PWA install prompt (custom UI) | In-app "Install App" button after user engagement beats relying on browser's dismissable prompt. | MEDIUM | Listen for `beforeinstallprompt` (Chromium only). Store event, show button in nav or post-login. Call `prompt()` on gesture. Safari has no API — show a tooltip with manual "Share → Add to Home Screen" instructions on iOS. vite-plugin-pwa's `useRegisterSW` handles SW updates; install prompt is separate custom logic. |
| Offline-capable shell (app shell pattern) | UI appears immediately even on flaky connections, then data loads. Matches native app feel. | LOW | This is free from Workbox precaching. No extra code once SW is configured with the correct asset scope. |
| Chessboard click-to-click on mobile | Drag-and-drop piece movement is unreliable on touch. Click-source then click-target is already configured and works reliably on mobile. | DONE | react-chessboard v5 advertises "Mobile support". Existing project uses `clearArrowsOnPositionChange: false` workaround. Verify drag works on touch; click-to-click is the confirmed fallback and already works. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Offline API data caching | "Works offline" sounds compelling | Chess data is user-specific + authenticated. Caching API responses risks stale analysis after logout/user-switch. IndexedDB-based sync adds major complexity. Users need network to import games anyway — offline analysis provides marginal value. | Cache only static assets (JS, CSS, icons). TanStack Query's in-memory stale-while-revalidate handles session-level caching. |
| Push notifications for import completion | "Tell me when my import finishes" | Requires Web Push API backend (VAPID keys), background SW messaging, permission prompts. Import jobs already show progress bars and poll via TanStack Query. | Existing polling + progress bar on Import page is sufficient. Flag for v2 if user demand is clear. |
| Background sync for imports | Retry failed imports when back online | Web Background Sync API has limited support. Import jobs run server-side — SW retrying is redundant. | Server-side jobs persist. User refreshes Import page to resume. |
| Swipe-to-navigate between tabs | Native-feeling navigation | Conflicts with chessboard drag-and-drop. Horizontal swipe on a touch chess board will misfire when users intend to drag pieces. | Standard tap navigation. |
| Full offline mode | Native app parity | Architecturally incompatible. Position analysis requires PostgreSQL Zobrist hash queries. Cannot replicate the DB client-side. | App shell + graceful error state informing user that analysis requires connectivity. |
| Bottom navigation bar | Thumb-reach ergonomics on large phones | Conflicts with existing top header pattern, adds layout complexity, and requires moving logout. The hamburger sheet is simpler and less disruptive. | Hamburger Sheet covers the same nav needs. Revisit in v2 only if UX testing reveals top-nav is a pain point. |

---

## Feature Dependencies

```
PWA installable
    └──requires──> Web App Manifest (name, icons, theme, display)
    └──requires──> Service Worker (registered + active fetch handler)
    └──requires──> HTTPS (localhost exempt for dev; tunnel provides HTTPS automatically)

Custom install prompt
    └──requires──> PWA manifest + SW (browser will not fire beforeinstallprompt otherwise)
    └──platform split──> Chromium: beforeinstallprompt event
                         Safari/iOS: manual "Share → Add to Home Screen" instructions

Mobile nav (hamburger Sheet)
    └──requires──> shadcn Sheet (already in project via shadcn/ui)
    └──enhances──> touch targets (Sheet menu items need adequate tap size)

Dev tunnel workflow
    └──requires──> Vite dev server running on localhost:5173 (already works)
    └──independent from all other features

Touch target audit
    └──independent──> Can be done in any order relative to nav or PWA work
```

### Dependency Notes

- **Installability criteria (Chrome):** valid manifest with 192px+ icon, registered SW with fetch handler, served over HTTPS. All three required simultaneously. Lighthouse PWA audit validates this.
- **beforeinstallprompt is Chromium-only:** Safari/iOS uses its own flow with no JS event. Design install UI with platform detection — show native instructions on Safari. Do not assume the event fires.
- **HTTPS for SW on real device:** All tunnel options (Cloudflare, ngrok, localtunnel) provide HTTPS automatically. localhost is SW-exempt in dev. No extra config needed.
- **Vite proxy routes must be excluded from SW interception:** The `vite.config.ts` proxies `/auth`, `/analysis`, `/games`, `/imports`, `/position-bookmarks`, `/stats`, `/users`, `/health` to the FastAPI backend. These must not be intercepted by the Workbox SW (use `navigateFallbackDenylist` or runtime cache patterns with `networkOnly` strategy). Otherwise the SW intercepts API calls and serves stale cached responses — a hard-to-debug failure mode.
- **react-chessboard touch:** Library advertises mobile support. Click-to-click (two-click) move entry already works and is reliable. Drag-and-drop on touch should be tested on a real device but click-to-click is the confirmed fallback.

---

## MVP Definition

### Launch With (v1.2)

Minimum to deliver a working mobile PWA experience.

- [ ] Mobile nav — hamburger Sheet with all nav links + logout, closes on tap, active route highlighted
- [ ] PWA manifest — app name "Chessalytics", custom icons (192px + 512px PNG), theme color, `display: standalone`
- [ ] Service worker — Workbox precache of static assets; API routes bypass SW (network-first or excluded)
- [ ] Touch target audit — all buttons, filter pills, and board controls meet 44×44px minimum
- [ ] No horizontal scroll on any page at 375px viewport width (iPhone SE baseline)
- [ ] Dev tunnel doc/script — one command to expose Vite dev server to phone

### Add After Validation (v1.x)

- [ ] Custom install prompt — show in-app "Install" button after confirming Lighthouse PWA audit passes in production
- [ ] Safari install instructions tooltip — for iOS users who cannot receive the beforeinstallprompt event

### Future Consideration (v2+)

- [ ] TanStack Query persistence adapter — persist query cache to localStorage/IndexedDB for faster re-renders on slow mobile connections (only if analysis queries create noticeable latency)
- [ ] Bottom navigation bar — only if UX testing shows hamburger is a persistent pain point
- [ ] Push notifications for import completion — only if user demand is explicit

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Mobile nav (hamburger Sheet) | HIGH | LOW | P1 |
| PWA manifest | HIGH | LOW | P1 |
| Service worker (Workbox precache) | HIGH | MEDIUM | P1 |
| Touch target audit | MEDIUM | LOW | P1 |
| Horizontal overflow fixes | MEDIUM | LOW | P1 |
| Dev tunnel workflow | MEDIUM (dev only) | LOW | P1 |
| Custom install prompt | MEDIUM | MEDIUM | P2 |
| Safari install instructions | LOW | LOW | P2 |
| Bottom navigation bar | LOW | MEDIUM | P3 |
| Offline API caching | LOW | HIGH | Anti-feature |
| Push notifications | LOW | HIGH | Anti-feature |
| Background sync | LOW | HIGH | Anti-feature |

**Priority key:**
- P1: Must have for v1.2 launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Lichess mobile web | Chess.com mobile web | Chessalytics v1.2 plan |
|---------|-------------------|---------------------|------------------------|
| Mobile nav | Hamburger slide-in | Bottom tab bar | Hamburger Sheet (shadcn) |
| PWA installable | Yes (manifest + SW) | Redirects to native app | vite-plugin-pwa |
| Offline capability | Partial (puzzles) | None | App shell only (static assets) |
| Touch targets | Good (large buttons) | Good | Audit + fix to 44px min |
| Install prompt | Native browser prompt | Push to App Store | Custom beforeinstallprompt + Safari fallback instructions |
| Dev testing workflow | n/a | n/a | Cloudflare Tunnel one-liner |

---

## Implementation Notes (Phasing Guidance)

**Phase 1 — Nav + PWA foundation:** Mobile nav hamburger + manifest + SW setup. These are independent and can be done in parallel within the same phase. Nav is frontend-only. PWA setup is `vite.config.ts` + `package.json`.

**Phase 2 — Polish:** Touch target audit across all pages (Import, Openings filter sidebar, board controls, Global Stats). Horizontal overflow fixes. Test on real device via tunnel.

**Phase 3 — Install prompt:** After Phase 1 confirms PWA is installable (Lighthouse PWA audit passing in CI or production). beforeinstallprompt + Safari instructions.

**Icon generation note:** Need to create 192×192 and 512×512 PNG icons from scratch (or generate from an SVG). Vite's current favicon is `vite.svg` — must be replaced with a chess-themed icon or at minimum a styled Chessalytics icon.

---

## Sources

- [vite-plugin-pwa Official Guide](https://vite-pwa-org.netlify.app/guide/) — HIGH confidence
- [vite-plugin-pwa GitHub](https://github.com/vite-pwa/vite-plugin-pwa) — HIGH confidence
- [MDN: Making PWAs Installable](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable) — HIGH confidence
- [MDN: beforeinstallprompt](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeinstallprompt_event) — HIGH confidence
- [MDN: PWA Caching](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Caching) — HIGH confidence
- [shadcn Sheet / Mobile Menu Pattern](https://www.shadcn.io/patterns/sheet-navigation-1) — HIGH confidence
- [react-chessboard GitHub (Clariity)](https://github.com/Clariity/react-chessboard) — MEDIUM confidence (mobile specifics from README only)
- [Cloudflare Tunnel / ngrok Alternatives 2025](https://pinggy.io/blog/best_ngrok_alternatives/) — MEDIUM confidence
- [Touch Target UX Best Practices 2025](https://edesignify.com/blogs/tap-targets-and-touch-zones-mobile-ux-that-works) — MEDIUM confidence
- Existing codebase: `frontend/src/App.tsx`, `frontend/vite.config.ts`, `frontend/package.json` — HIGH confidence

---

*Feature research for: Chessalytics v1.2 — Mobile & PWA*
*Researched: 2026-03-20*
