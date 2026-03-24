# FlawChess

## What This Is

FlawChess — a multi-user chess analysis platform that lets players import their games from chess.com and lichess, then analyze win/draw/loss rates for specific board positions. It solves the problem of inconsistent opening categorization on existing platforms — instead of relying on opening names, users define positions visually and filter by actual piece placement. Includes an interactive move explorer showing next moves with W/D/L stats per position. Works as an installable PWA on mobile with touch-optimized UI.

## Core Value

Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## Requirements

### Validated

- ✓ Import games from chess.com and lichess via API by username — v1.0
- ✓ On-demand re-sync to fetch latest games — v1.0
- ✓ Store all available game metadata for future analyses — v1.0
- ✓ Interactive chess board to specify search positions by playing moves — v1.0
- ✓ Filter analysis by white/black/both position matching — v1.0
- ✓ Filter by time control, rated/casual, recency, color, opponent type — v1.0
- ✓ Display win/draw/loss rates for matching games — v1.0
- ✓ Display matching games as cards with metadata and platform links — v1.0
- ✓ Multi-user support with data isolation — v1.0
- ✓ Position bookmarks with auto-suggestions, mini boards, drag-reorder — v1.0
- ✓ Rating history and global stats pages — v1.0
- ✓ Move explorer showing next moves with W/D/L stats per move — v1.1
- ✓ Store move SAN in game_positions with index for performant lookups — v1.1
- ✓ Dedicated Import page replacing import modal — v1.1
- ✓ Merged Openings tab with Move Explorer / Games / Statistics sub-tabs — v1.1
- ✓ Shared filter sidebar across Openings sub-tabs — v1.1
- ✓ Enhanced game import: clock data, termination, time control fix — v1.1
- ✓ Game cards with 3-row layout, icons, hover minimap — v1.1
- ✓ PWA setup (manifest, service worker, installable, chess knight icons) — v1.2
- ✓ Dev workflow for phone testing (LAN + Cloudflare tunnel) — v1.2
- ✓ Mobile-first navigation with bottom bar, "More" drawer, responsive header — v1.2
- ✓ Click-to-move chessboard on touch devices with sticky mobile layout — v1.2
- ✓ 44px touch targets on all interactive elements, no horizontal scroll at 375px — v1.2
- ✓ Android/iOS in-app PWA install prompts — v1.2
- ✓ CI/CD pipeline (GitHub Actions: test + SSH deploy + health check) — v1.3
- ✓ Sentry error monitoring (backend + frontend) — v1.3
- ✓ Full rebrand from Chessalytics to FlawChess (code, PWA, GitHub org) — v1.3
- ✓ Docker Compose production deployment on Hetzner with Caddy auto-TLS — v1.3
- ✓ Public homepage with feature sections, FAQ, register/login CTA — v1.3
- ✓ SEO fundamentals (meta tags, Open Graph, sitemap.xml, robots.txt) — v1.3
- ✓ Privacy policy page at /privacy — v1.3
- ✓ Per-platform import rate limiter preventing chess.com/lichess bans — v1.3
- ✓ Professional README with screenshots and self-hosting instructions — v1.3

### Active

- [x] System computes game phase (opening/middlegame/endgame) for every position during import — Validated in Phase 27: import-wiring-backfill
- [x] System computes material signature, material imbalance, and endgame class for every position during import — Validated in Phase 27: import-wiring-backfill
- [ ] System imports existing engine analysis data (eval, accuracy, move quality) from chess.com/lichess when available
- [ ] User can view endgame performance statistics in a dedicated Endgames tab
- [ ] User can filter endgame stats by endgame type (rook, minor piece, pawn, queen endgames, etc.)
- [ ] User can filter endgame stats by material configuration (e.g., KRP vs KR)
- [ ] User can see conversion stats (win rate when up material) broken down by game phase
- [ ] User can see recovery stats (draw/win rate when down material) broken down by game phase

### Out of Scope

- Manual PGN file upload — API import only
- In-app game viewer — link to chess.com/lichess instead
- Human-like engine analysis — future: engine evaluation filtered by human move plausibility at target Elo (see Maia Chess approach)
- Offline API data caching — chess data is user-specific + authenticated; caching risks stale analysis
- Swipe-to-navigate between tabs — conflicts with chessboard touch gestures

## Current Milestone: v1.5 Game Statistics & Endgame Analysis

**Goal:** Enrich imported games with per-position metadata (game phase, material, endgame classification) and surface endgame performance analytics through a new Endgames tab.

**Target features:**
- Position metadata at import: game phase, material signature, material imbalance, endgame class
- Import existing engine analysis from chess.com/lichess APIs when available
- Endgame analytics tab with filters and W/D/L statistics per endgame category
- Material-based conversion & recovery statistics by game phase

## Current State

v1.3 shipped 2026-03-22. FlawChess is live at flawchess.com with automated CI/CD and Sentry monitoring. v1.4 (Web Analytics, Password Reset) in progress. Phase 27 complete — classify_position wired into live import pipeline, backfill script created for existing games. All new imports populate 7 position metadata columns automatically.

## Context

- **Current state:** v1.3 shipped. 23 phases complete across 4 milestones. Live at flawchess.com with CI/CD and Sentry.
- **Stack:** FastAPI + React 19/TS/Vite 5 + PostgreSQL + python-chess + TanStack Query + Tailwind + shadcn/ui
- **Auth:** FastAPI-Users (JWT + Google SSO)
- **Core algorithm:** Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import for indexed integer equality lookups
- **PWA:** vite-plugin-pwa + Workbox (NetworkOnly for API routes), vaul drawer, tailwindcss-safe-area
- **Known issues:** react-chessboard v5 arrow clearing workaround (clearArrowsOnPositionChange: false), BoardArrow local type definition, touch drag disabled (click-to-move only on mobile)

## Constraints

- **Tech stack**: Python backend (FastAPI), uv for package management
- **Database**: PostgreSQL with asyncpg — must support efficient position-based queries across thousands of games
- **Deployment**: Must work locally and be deployable to a server
- **Libraries**: Use established open-source libraries (python-chess, etc.) rather than reinventing
- **HTTP client**: httpx async only — never use requests or berserk

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI for backend | User expertise, async support, modern Python | ✓ Good |
| API-only import (no PGN upload) | Simpler v1, covers primary use case | ✓ Good |
| Interactive board over FEN input | Better UX for target users | ✓ Good |
| uv for package management | Fast, modern Python tooling | ✓ Good |
| React 19 + TypeScript + Vite 5 | react-chessboard 5.x requires React 19 | ✓ Good |
| PostgreSQL (no SQLite) | Multi-user concurrent writes, BIGINT index, asyncpg | ✓ Good |
| DB wipe for v1.1 | No migration needed — reimport after schema change | ✓ Good |
| Zobrist hash position matching | 64-bit integer equality vs FEN string comparison | ✓ Good |
| move_san ply semantics | SAN on ply N = move played FROM that position | ✓ Good |
| DISTINCT + GROUP BY for transpositions | COUNT(DISTINCT g.id) prevents double-counting | ✓ Good |
| Filter state in OpeningsPage parent | Survives tab switches without reset | ✓ Good |
| QueryClient singleton in lib/ | Shared across 401 interceptor and auth transitions | ✓ Good |
| vite-plugin-pwa with generateSW | Zero-config, Vite 7 compatible, Workbox managed | ✓ Good |
| vaul for mobile drawer | Handles scroll lock, backdrop, iOS momentum natively | ✓ Good |
| Click-to-move only on mobile | HTML5 DnD absent on iOS Safari; drag causes black screen | ✓ Good |
| Duplicate mobile Openings layout | Sticky board incompatible with sidebar's flex-column | ⚠️ Revisit |
| Hetzner CX32 + Docker Compose + Caddy | Simple single-VPS deployment for solo dev | ✓ Good |
| Plausible over Google Analytics | No cookie consent required, GDPR-simple | ✓ Good |
| Sentry for both backend + frontend | Single project, DSN baked at Docker build time | ✓ Good |
| asyncio.Semaphore rate limiter | Per-platform concurrency control without Redis/Celery | ✓ Good |
| Backend expose-only (no ports) | Caddy is sole internet-facing entry point | ✓ Good |

---
*Last updated: 2026-03-24 after Phase 27 completion*
