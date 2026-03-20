# Phase 17: PWA Foundation + Dev Workflow - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the app installable as a PWA with correct service worker caching strategy, custom chess-themed icons, and a phone testing workflow (LAN + HTTPS tunnel). No mobile layout changes — those are Phase 18 and 19.

</domain>

<decisions>
## Implementation Decisions

### App Identity & Icons
- Knight silhouette as the app icon — most distinctive chess piece, instantly recognizable
- Generate 192px and 512px PNG icons (required for PWA installability)
- Replace current `vite.svg` favicon with the chess knight icon
- Dark theme color (#0a0a0a or similar) matching existing dark UI — status bar blends seamlessly
- App name: "Chessalytics", short_name: "Chessalytics"

### Service Worker Update Strategy
- Auto-update on next visit — new service worker activates silently on next page load
- No reload toast or manual update prompt
- Use `skipWaiting` + `clientsClaim` so the new SW takes control immediately on next navigation
- Simpler for users; acceptable that one visit may see stale static assets

### Dev Tunnel Workflow
- Easiest-to-set-up tunnel wins — Claude picks between Cloudflare Tunnel and ngrok based on simplicity
- Also add `vite --host` script for same-network LAN testing (no HTTPS, but faster iteration)
- Vite proxy routes need `allowedHosts` config for tunnel compatibility (Vite 5.4.12+ DNS rebinding protection)

### PWA Install Scope
- `start_url: "/"` — hits auth check, redirects to /openings if logged in (Claude's discretion)
- `scope: "/"` — keeps OAuth callbacks within PWA scope
- `display: "standalone"` — no browser chrome
- Accept re-login on iOS — storage isolation between Safari and installed PWA is a platform constraint, no special handling needed
- No warning banner for iOS re-login — keep it simple

### Service Worker Caching
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### PWA Setup
- `.planning/research/STACK.md` — vite-plugin-pwa version, configuration approach, generateSW rationale
- `.planning/research/ARCHITECTURE.md` — PWA integration with Vite 7, service worker routing, manifest config
- `.planning/research/PITFALLS.md` — Vite allowedHosts bug, iOS storage isolation, SW API route exclusion

### Project Context
- `.planning/research/SUMMARY.md` — Synthesized research findings and phase ordering rationale
- `.planning/PROJECT.md` — Proxy routes list (all need NetworkOnly exclusion), auth setup (FastAPI-Users JWT + Google SSO)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None directly reusable — this phase adds new infrastructure

### Established Patterns
- `vite.config.ts`: Two plugins (react, tailwindcss), path alias `@`, 8 proxy routes to localhost:8000
- `index.html`: Minimal head — only charset, viewport, title, vite.svg favicon. Dark class on html element
- `package.json`: Scripts are `dev`, `build`, `lint`, `preview`. No PWA dependencies
- `public/`: Contains `openings.tsv` (368KB static data) and `vite.svg` only

### Integration Points
- `vite.config.ts` — Add vite-plugin-pwa plugin configuration
- `index.html` — Add theme-color meta, apple-touch-icon link (vite-plugin-pwa injects manifest link automatically)
- `src/main.tsx` — Register service worker via vite-plugin-pwa's virtual module
- `public/` — Add icon PNGs (192px, 512px)
- `package.json` — Add vite-plugin-pwa devDependency, add dev:mobile and dev:tunnel scripts

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants simplest setup that works.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 17-pwa-foundation-dev-workflow*
*Context gathered: 2026-03-20*
