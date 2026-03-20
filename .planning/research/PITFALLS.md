# Pitfalls Research

**Domain:** Adding PWA, mobile navigation, and responsive polish to existing Vite 5 + React 19 SPA with interactive chessboard
**Researched:** 2026-03-20
**Confidence:** HIGH (service worker/Vite behavior, iOS storage isolation), MEDIUM (react-chessboard touch specifics, iOS auth OAuth edge cases)

---

## Critical Pitfalls

### Pitfall 1: Service Worker Caches API Responses, Breaking Real-Time Analysis Data

**What goes wrong:**
The default `generateSW` strategy in vite-plugin-pwa precaches all built assets and, if runtime caching is configured carelessly, intercepts and caches API responses. Users see stale win/draw/loss stats, position data, or game lists after importing new games — with no indication the data is outdated. TanStack Query's invalidation fires correctly but the service worker silently serves the old response from cache before TanStack Query can compare ETags.

**Why it happens:**
Developers configure runtime caching broadly to make the app "offline capable" without distinguishing between cacheable static assets and dynamic REST API data. A `StaleWhileRevalidate` strategy applied to all routes looks correct — it serves fast and updates in the background — but for analysis data that changes after every import, serving stale content is a correctness bug, not a performance trade-off.

**How to avoid:**
Explicitly exclude all API routes from caching using the `denylist` or `urlPattern` options in workbox runtime caching. Use `NetworkOnly` for every `/api/` route:
```js
runtimeCaching: [
  {
    urlPattern: ({ url }) => url.pathname.startsWith('/api/'),
    handler: 'NetworkOnly',
  },
]
```
Cache only: static assets (JS/CSS bundles with content-hashed filenames), the app shell (`index.html`), and chess piece images. Everything from the FastAPI backend must bypass the service worker entirely.

**Warning signs:**
- Opening Openings page shows data from a previous session after a game import
- TanStack Query invalidation fires (confirmed via devtools) but UI does not update
- Network tab shows fetch requests served from `ServiceWorker` with `(from cache)` for `/api/` endpoints

**Phase to address:**
PWA setup phase — define the caching strategy exhaustively before writing any service worker configuration. This is easier to get right upfront than to diagnose and fix post-deployment.

---

### Pitfall 2: Users Stuck on Old App Version After Deployment

**What goes wrong:**
A new deployment ships updated JS/CSS bundles with bug fixes or new features. The service worker serves the old precached assets indefinitely. Users who installed the PWA to their home screen see the old UI until they manually clear the browser cache and re-add to home screen. The new service worker registers in the background and enters `waiting` state, but never activates because the old service worker stays active as long as any tab with the app is open.

**Why it happens:**
Service workers only activate after all tabs using the old version are closed. In an installed PWA opened from the home screen, the tab is rarely closed fully. Without an explicit update flow, the new service worker waits forever.

**How to avoid:**
Use `workbox-window` with vite-plugin-pwa's built-in `ReloadPrompt` pattern. On `onNeedRefresh`, show a toast notification ("Update available") with a "Reload" button that calls `updateServiceWorker(true)`. This posts a `SKIP_WAITING` message to the waiting service worker and reloads the page.

Do not auto-reload silently — this breaks in-progress analysis sessions where the user has a position and filters set.

At the server/hosting level, set `Cache-Control: no-cache` on the `sw.js` response so browsers always check for a new service worker on every page load rather than serving a cached copy of the old one.

**Warning signs:**
- Deployed a bug fix but users report the bug persists
- Chrome DevTools Application > Service Workers shows status "waiting to activate"
- No update notification appears in the installed PWA after deploying

**Phase to address:**
PWA setup phase — build the update notification flow before shipping the first PWA version. Retrofitting it later requires users to manually clear their cache to escape the stale version.

---

### Pitfall 3: Vite Dev Server Blocks Requests from ngrok Tunnel

**What goes wrong:**
When exposing the Vite dev server through ngrok for phone testing, the app completely fails to load on the phone. The browser shows a Vite error page: "Blocked request. This host is not allowed." Even if that is resolved, HMR does not work — code changes on the desktop do not trigger live reloads on the phone.

**Why it happens:**
Since Vite 5.4.12+ / 6.0+, Vite checks the `Host` header against an allowlist as a DNS rebinding attack protection. The ngrok subdomain (e.g., `abc123.ngrok-free.app`) is not in the default allowlist. Separately, Vite's HMR websocket client defaults to connecting back to `localhost:5173`, which is unreachable from the phone via ngrok — the HMR client must be told to use the tunnel's port (443 for HTTPS tunnels) instead.

Note: `allowedHosts: true` has a known bug in Vite 6.0.9 where it is silently ignored — use the string `'all'` or an explicit list of hostnames.

**How to avoid:**
Add to `vite.config.ts` (conditionally, via env variable):
```ts
server: {
  host: true,                    // listen on all interfaces, not just localhost
  hmr: { clientPort: 443 },     // HTTPS ngrok tunnels terminate at port 443
  allowedHosts: 'all',          // or list the specific *.ngrok-free.app domain
}
```
Never commit `allowedHosts: 'all'` as the default — use an environment variable (`NGROK_TUNNEL=true`) to activate this config only during phone testing sessions.

**Warning signs:**
- Phone browser shows "Blocked request" Vite error page at the ngrok URL
- Page loads on phone but code edits on desktop do not trigger page reload
- Browser console on phone shows `WebSocket connection failed: ws://localhost:5173`

**Phase to address:**
Dev workflow / phone testing setup phase — must be working before any mobile UX testing begins. Wasted time is the primary cost.

---

### Pitfall 4: react-chessboard Drag-and-Drop Broken on iOS Safari

**What goes wrong:**
Users on iPhone cannot drag chess pieces. The board responds to taps (squares highlight) but dragging a piece does nothing — the piece snaps back immediately or the gesture is interpreted as a page scroll instead.

**Why it happens:**
HTML5 Drag-and-Drop API (`dragstart`/`dragover`/`drop` events) is not implemented in iOS Safari. This is a fundamental platform limitation. react-chessboard v5 uses HTML5 DnD for piece dragging. The library is advertised as "responsive" but responsive layout and touch DnD support are separate concerns — the former is present, the latter is not via HTML5 DnD.

**How to avoid:**
Disable drag entirely on touch devices and rely on click-to-move (two taps: source square then destination square). react-chessboard supports this natively via `onSquareClick`. Implement a two-click selection pattern in the parent component: first tap selects the piece (apply a highlight to the source square), second tap on a valid destination moves it. This is the standard mobile chess interface pattern used by chess.com and lichess.

```tsx
<Chessboard
  arePiecesDraggable={!isTouchDevice()}
  onSquareClick={handleSquareClick}
/>
```

Do not add a touch DnD polyfill — these add meaningful bundle size and complexity for minimal gain when click-to-move already works.

The project's known existing workaround (`clearArrowsOnPositionChange: false`) must continue to work alongside the mobile click-to-move implementation. Test arrow behavior after adding the click-to-move state.

**Warning signs:**
- Pieces do not move on iPhone/iPad in Safari
- No `dragstart` events fire in Safari mobile devtools
- Android Chrome works but iOS Safari does not (confirms the platform gap, not a library bug)

**Phase to address:**
Mobile UX polish phase — this is the single most critical chessboard interaction fix for mobile users.

---

### Pitfall 5: iOS PWA Standalone Mode Has Isolated Storage — Auth Does Not Transfer from Safari

**What goes wrong:**
A user visits the app in Safari, logs in, then installs the PWA via "Add to Home Screen." When they open the PWA from the home screen icon, they are not logged in — the login page appears again. JWT tokens stored in `localStorage` in Safari are not visible to the PWA standalone `WKWebView`. These are completely isolated storage contexts.

A secondary issue: if the app redirects to Google SSO for authentication, iOS drops out of standalone mode and opens the OAuth provider in full Safari. After the OAuth callback, the user is returned to Safari (not the standalone PWA), and the token is in Safari's storage, not the PWA's.

**Why it happens:**
On iOS, the installed PWA runs in an isolated `WKWebView` that shares no cookies, `localStorage`, `sessionStorage`, or service worker instance with Safari. This has been a fundamental iOS architectural limitation since PWA support was introduced, and remains true as of iOS 18 (2025).

The project uses JWT tokens stored in `localStorage` (inferred from `useAuth` hook and `ProtectedLayout` token check in `App.tsx`). This storage does not cross the Safari-to-PWA boundary.

**How to avoid:**
- Accept that first-time login is required in standalone mode even if the user is logged in on Safari. Document this in any installation instructions.
- Test the Google SSO OAuth flow specifically in standalone mode on a physical iPhone. Ensure the OAuth callback URL (`/auth/callback`) is within the PWA manifest's `scope` — if the callback navigates outside scope, iOS drops into full Safari and the session is lost.
- Set manifest `scope: "/"` and `start_url: "/"` to keep all navigation within standalone mode.
- Verify the OAuth redirect URI registered with Google matches the production HTTPS domain, not localhost.

**Warning signs:**
- User installs PWA, opens it, sees login page despite being logged in on Safari
- Google SSO redirects open a new Safari tab instead of staying within the PWA
- After OAuth, the redirect returns to `https://yourdomain.com/auth/callback` but the page opens in Safari rather than the standalone PWA

**Phase to address:**
PWA setup phase — manifest `scope` must be correct from day one. Auth flow testing on a physical iPhone is required. Desktop browser PWA testing does not reproduce iOS storage isolation.

---

### Pitfall 6: Missing `viewport-fit=cover` Leaves Notch Gaps on iPhone

**What goes wrong:**
On iPhones with a notch or Dynamic Island (iPhone X through iPhone 16), the app shows a colored gap at the top (status bar area) or content is hidden under the home indicator at the bottom when running as a standalone PWA. The navigation header and bottom spacing look wrong.

**Why it happens:**
Without `viewport-fit=cover`, iOS constrains the viewport to the "safe area," leaving the device's OS chrome colors visible outside it. With `viewport-fit=cover` but without `env(safe-area-inset-*)` padding applied to layout elements, content bleeds under the notch or Dynamic Island.

**How to avoid:**
Set the viewport meta tag in `index.html`:
```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```
Then apply safe area insets in global CSS (`index.css`):
```css
body {
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
}
```
Or apply specifically to the nav header (`padding-top: env(safe-area-inset-top)`) and any bottom navigation element. The safe area values are `0` in regular browser mode, so this CSS is harmless on desktop and Android.

With Tailwind, use arbitrary value utilities: `pt-[env(safe-area-inset-top)]` or define a CSS custom property in `:root`.

**Warning signs:**
- The nav header overlaps the notch/Dynamic Island in PWA standalone mode on iPhone 12+
- A colored gap appears below the nav header or above any bottom navigation
- Safe area appears only in standalone mode, not in Safari (this is expected and correct behavior)

**Phase to address:**
Mobile navigation / viewport setup phase — fix the viewport meta tag before building the responsive nav. This is a one-line HTML change with significant visual impact on notched iPhones.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `allowedHosts: 'all'` committed as default in vite.config.ts | ngrok works without setup | DNS rebinding vulnerability in shared or CI environments | Never — use env variable or separate config override |
| Skip update notification UI for PWA | Faster initial shipping | Users stuck on stale versions indefinitely after any deployment | Never — defeats the core benefit of service worker versioning |
| Hard-code `arePiecesDraggable={true}` with no mobile fallback | Simpler code | Broken chess piece interaction on all iOS devices | Never for a chess analysis app |
| Cache API responses with StaleWhileRevalidate | Faster perceived loads, offline read support | Users see wrong analysis stats after importing games | Never for analysis data; acceptable only for user profile metadata |
| Single 512x512 PNG icon in manifest | Less asset work | PWA install prompt suppressed on some Android versions; ugly pixelated home screen icon | Never — generating icon sizes is 30 minutes of work |
| Implementing body scroll lock without `position: fixed` | Simpler CSS | On iOS Safari, `overflow: hidden` alone does not prevent background scroll | Never on iOS — must combine `overflow: hidden` + `position: fixed` |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| ngrok + Vite HMR | Default config, expect HMR to work through tunnel | Set `server.hmr.clientPort: 443` and `server.host: true`; add ngrok domain to `allowedHosts` |
| ngrok + FastAPI backend | Assume Vite's `/api` proxy forwards correctly through ngrok | The Vite proxy forwards to `localhost:8000` regardless of ngrok — the backend is reached via the local network, not through ngrok. Phone must reach the Vite dev server via ngrok; the Vite server then proxies to the local FastAPI. This works if both are on the same machine. |
| vite-plugin-pwa + TanStack Query | Assume the two caches don't conflict | They are independent layers. SW precache serves static assets; TanStack Query manages API data. Explicitly exclude all `/api/*` from SW caching. |
| iOS Safari + Google SSO in standalone mode | Expect OAuth redirect to return to PWA | Test OAuth on physical iPhone in standalone mode; ensure `/auth/callback` is within manifest `scope`; accept that first login requires separate session in standalone context |
| Service worker + Vite dev server (devOptions enabled) | Register SW in dev and expect same behavior as production | Dev SW has empty precache and behaves differently. Disable runtime caching in dev with `disableRuntimeConfig: true`. Prefer testing the production build for service worker behavior. |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Precaching large or unnecessary assets | First PWA install takes 10+ seconds on mobile; blank screen during install | Inspect the generated precache manifest in `sw.js` after build; exclude large files not needed for initial render | Any slow mobile connection |
| Awaiting service worker registration before first render | App hangs 2-3 seconds before showing anything; poor LCP score | Never `await navigator.serviceWorker.register()` before mounting React; registration is a background task | Every first load |
| Board re-rendering on mobile filter changes | Board flickers or resets arrow state when filter chips are tapped | Memoize `position` and `boardOrientation` props; the existing `clearArrowsOnPositionChange: false` workaround must be preserved | Already partially mitigated in v1.1; verify with mobile testing |
| Mobile menu keeping body scroll locked after navigation | Scrolling broken after closing menu via nav link | Use `useEffect(() => setMenuOpen(false), [location.pathname])` to close menu on route change; remove `overflow: hidden` + `position: fixed` from body in the same cleanup | iOS Safari specifically — this trap is iOS-only |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing `allowedHosts: 'all'` or `allowedHosts: true` to main vite.config.ts | DNS rebinding attack exposes source code to attacker-controlled pages | Activate via env variable only: `allowedHosts: process.env.VITE_NGROK ? 'all' : []` |
| Caching authenticated API responses in service worker | User A's analysis data served from cache if User B logs in on the same device | Enforce `NetworkOnly` for all `/api/` routes; never cache JWT-protected responses |
| Overly broad manifest `scope` allowing attacker-controlled subpaths | Attacker-controlled page within scope can masquerade as the PWA | Set `scope: "/"` — intentionally broad for a SPA. This is acceptable since the entire origin is controlled. |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Touch targets smaller than 44x44px | Frequent mis-taps on filter chips, nav items, board controls on mobile | Enforce `min-h-11 min-w-11` (Tailwind = 44px) on all interactive elements; use `touch-action: manipulation` to eliminate 300ms tap delay |
| Hamburger menu opens but no backdrop overlay | Users tap the chessboard area intending to close the menu and accidentally move a piece | Full-screen semi-transparent overlay behind the slide-out menu; close on overlay tap |
| No PWA install prompt or instructions on iOS | Users never discover the app can be installed; worse experience than necessary | Add a persistent but dismissible "Add to Home Screen" banner on iOS Safari; implement the `beforeinstallprompt` flow for Android |
| Page scroll conflict when finger is on chessboard | Attempting to scroll the page while touching the board scrolls the board's container instead | Set `touch-action: none` on the board container element; test by placing a finger on the board and attempting to scroll the page |
| Hamburger menu stays open after navigating | Menu appears on top of destination page; user must close it manually | Close menu on route change via `useEffect(() => setMenuOpen(false), [location.pathname])` |
| Horizontal overflow from chessboard on narrow screens | Entire page gains horizontal scroll; layout breaks below the board | Never set a fixed pixel width for the board; use `min(100vw - 2rem, 600px)` or a percentage-based constraint |

## "Looks Done But Isn't" Checklist

- [ ] **PWA installable:** Passes Lighthouse PWA audit — verify icons at 192x192 and 512x512 with `purpose: "any maskable"`, HTTPS, service worker registered, valid manifest
- [ ] **iOS standalone auth:** Tested on physical iPhone in standalone mode (not Safari DevTools emulation) — emulation does not reproduce iOS storage isolation or OAuth redirect behavior
- [ ] **Chessboard touch:** Pieces move via click-to-move on actual iPhone and Android, not just desktop browser with touch emulation enabled in DevTools
- [ ] **Service worker update flow:** Deploy a visible UI change, reload the installed PWA, confirm update notification toast appears and the "Reload" button activates the new version
- [ ] **API routes bypass SW:** After service worker installs, verify in Network tab that `/api/` requests show server timing, not `(from cache)` or `(ServiceWorker)`
- [ ] **Safe area insets:** Check on iPhone 12+ in standalone mode — nav header clears the notch/Dynamic Island; no content hidden under home indicator
- [ ] **Hamburger scroll lock:** Open mobile menu on iPhone, attempt to scroll the background page — confirm background does not scroll
- [ ] **ngrok HMR:** Edit a component text on desktop, confirm the change hot-reloads on the phone within 3 seconds
- [ ] **Manifest scope and OAuth:** Confirm Google SSO OAuth callback lands back in the PWA standalone mode on iOS (does not jump to Safari)

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SW caching API responses (discovered post-ship) | MEDIUM | Add `NetworkOnly` config for `/api/`, rebuild, deploy; existing cached responses expire on next network request or user can clear app cache |
| Users stuck on stale version (no update notification shipped) | HIGH | Deploy a "poison pill" service worker that immediately unregisters itself; users get the fix on next browser check; notify users to refresh |
| iOS PWA auth broken (manifest scope misconfigured) | LOW | Update `manifest.webmanifest` scope, redeploy; existing installs need to re-add to home screen to pick up manifest change |
| Vite blocks ngrok requests (discovered during testing session) | LOW | Add `allowedHosts` and `hmr.clientPort` config, restart dev server; no code changes needed |
| Chessboard drag broken on iOS (missed in desktop testing) | LOW | Set `arePiecesDraggable={false}` conditionally or unconditionally; redeploy |
| Missing safe-area-inset CSS (discovered on device) | LOW | Add one-line CSS to `index.css` and one attribute to `index.html` viewport meta; redeploy |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SW caches API responses | PWA setup | Lighthouse audit + Network tab inspection after SW installs |
| Stale app shell after deploy | PWA setup | Deploy a visible change, reload installed PWA, confirm update notification |
| ngrok HMR blocked | Dev workflow setup | Edit a component on desktop, verify live reload fires on phone |
| react-chessboard drag broken on iOS | Mobile UX polish | Tap and drag a piece on physical iPhone — piece must move or click-to-move must work |
| iOS PWA auth session isolation | PWA setup | Install PWA on iPhone, open from home screen, verify login state and OAuth flow |
| Missing viewport-fit / safe-area insets | Mobile nav / responsive layout | Open app on iPhone 12+ in standalone mode, inspect nav header and bottom edge |
| Touch targets too small | Mobile UX polish | Chrome DevTools accessibility audit + physical thumb testing on narrow phone |
| Body scroll lock on iOS hamburger menu | Mobile navigation | Open hamburger menu on iPhone, attempt to scroll page behind it |

## Sources

- [Vite PWA development mode — official docs](https://vite-pwa-org.netlify.app/guide/development)
- [Vite server.allowedHosts — ngrok discussion](https://github.com/vitejs/vite/discussions/5399)
- [Vite blocked request host not allowed — GitHub discussion](https://github.com/vitejs/vite/discussions/19426)
- [Vite server options reference](https://vite.dev/config/server-options)
- [iOS Safari PWA storage isolation — Netguru](https://www.netguru.com/blog/how-to-share-session-cookie-or-state-between-pwa-in-standalone-mode-and-safari-on-ios)
- [PWA iOS limitations 2025/2026 — MagicBell](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide)
- [iOS safe-area-inset and viewport-fit — WebKit blog](https://webkit.org/blog/7929/designing-websites-for-iphone-x/)
- [PWA update strategy — web.dev](https://web.dev/learn/pwa/update)
- [React SPA service worker update handling — Medium](https://medium.com/@leybov.anton/how-to-control-and-handle-last-app-updates-in-pwa-with-react-and-vite-cfb98499b500)
- [react-chessboard — GitHub (Clariity)](https://github.com/Clariity/react-chessboard)
- [HTML5 DnD not supported on iOS — known platform limitation, MDN](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API)
- [PWA bugs tracker — pwa-police/pwa-bugs](https://github.com/PWA-POLICE/pwa-bugs)
- [PWA installability checklist — MDN](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable)
- [iOS body scroll lock with overflow:hidden — Medium](https://medium.com/@rio.alexandre33/css-burger-menu-for-mobile-devices-with-blocked-body-scrolling-dbbd2eaa37c7)
- [Tailwind/headlessui body scroll discussion — GitHub](https://github.com/tailwindlabs/headlessui/discussions/744)
- [Codebase inspection: frontend/src/App.tsx, frontend/src/pages/, CLAUDE.md]

---
*Pitfalls research for: Chessalytics v1.2 — Mobile PWA, responsive navigation, and phone dev workflow*
*Researched: 2026-03-20*
