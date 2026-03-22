# Milestones: FlawChess

## v1.3 Project Launch (Shipped: 2026-03-22)

**Phases completed:** 4 phases, 10 plans, 12 tasks

**Key accomplishments:**

- Full codebase renamed from Chessalytics to FlawChess across 20 files — PWA manifest, logo, GitHub org transfer
- Complete Docker Compose stack (FastAPI + Caddy 2.11.2 + PostgreSQL) deployed to Hetzner VPS with auto-TLS
- GitHub Actions CI/CD pipeline: test + lint + SSH deploy + health check polling
- Sentry error monitoring on backend (sentry-sdk[fastapi]) and frontend (@sentry/react) with Docker build-time DSN injection
- Public homepage with feature sections, FAQ, and register/login CTA; SEO meta tags, sitemap.xml, robots.txt
- Per-platform rate limiter (asyncio.Semaphore) protecting chess.com/lichess imports from concurrent bans
- Privacy policy page at /privacy; professional README with screenshots and self-hosting instructions

---

## v1.2 Mobile & PWA (Shipped: 2026-03-21)

**Phases:** 17–19 (3 phases, 5 plans)

Made the application work great on smartphones as an installable PWA with mobile-optimized navigation, touch interactions, and dev workflow for phone testing.

**Key accomplishments:**

- Installable PWA with service worker, chess-themed icons, and Workbox caching (NetworkOnly for API routes)
- Mobile bottom navigation bar with direct tabs and slide-up "More" drawer (vaul-based)
- Click-to-move chessboard on touch devices with sticky board layout on Openings page
- 44px touch targets on all interactive elements, no horizontal scroll at 375px
- Android/iOS in-app install prompts (beforeinstallprompt + manual iOS instructions)
- Cloudflare Tunnel dev workflow for HTTPS phone testing

---

## v1.1 — Opening Explorer & UI Restructuring

**Shipped:** 2026-03-20
**Phases:** 11–16 (6 phases, 15 plans)

Added interactive move explorer with W/D/L stats per position, restructured UI with tabbed Openings hub and dedicated Import page, enriched game import data, and redesigned game cards.

**Key accomplishments:**

- Move explorer with next-move W/D/L stats, click-to-navigate, transposition handling
- Chessboard arrows showing next moves with win-rate color coding
- UI restructured: tabbed Openings hub (Moves/Games/Statistics) + dedicated Import page
- Enhanced import: clock data, termination reason, time control fix, multi-username sync
- Game cards redesigned: 3-row layout with icons, hover/tap minimap showing final position
- Data isolation fixes, Google SSO last_login, cache clearing on auth transitions

---

## v1.0 — Initial Platform

**Shipped:** 2026-03-15
**Phases:** 1–10

Built the complete multi-user chess analysis platform: game import from chess.com/lichess, Zobrist hash position matching, interactive board with W/D/L analysis, position bookmarks with auto-suggestions, game cards, rating/stats pages, and browser automation optimization.

**Key capabilities:**

- Import pipeline with incremental sync (chess.com + lichess)
- Position analysis via precomputed Zobrist hashes (white/black/full)
- Position bookmarks with drag-reorder, mini boards, piece filter
- Auto-generated bookmark suggestions from most-played openings
- Game cards with rich metadata and pagination
- Rating history, global stats, openings W/D/L charts
- Multi-user auth with data isolation
