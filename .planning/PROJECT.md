# FlawChess

## What This Is

FlawChess — a multi-user chess analysis platform that lets players import their games from chess.com and lichess, then analyze win/draw/loss rates for specific board positions. It solves the problem of inconsistent opening categorization on existing platforms — instead of relying on opening names, users define positions visually and filter by actual piece placement. Includes an interactive move explorer showing next moves with W/D/L stats per position, endgame performance analytics with conversion/recovery metrics, and a polished mobile PWA experience with drawer-based sidebars.

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
- ✓ Web analytics via self-hosted Umami — v1.4
- ✓ Game phase classification (opening/middlegame/endgame) per position at import — v1.5
- ✓ Material signature, imbalance, and endgame class per position at import — v1.5
- ✓ Engine analysis data import (eval, accuracy, move quality) from chess.com/lichess — v1.5
- ✓ Endgame performance statistics in dedicated Endgames tab — v1.5
- ✓ Endgame stats filterable by type (rook, minor piece, pawn, queen, mixed) — v1.5
- ✓ Conversion stats (win rate when up material) with timeline charts — v1.5
- ✓ Recovery stats (draw/win rate when down material) with timeline charts — v1.5
- ✓ Homepage with feature showcase, FAQ, acknowledgements — v1.5
- ✓ Centralized theme system (CSS variables, charcoal containers, noise texture) — v1.6
- ✓ Shared WDL chart component replacing all inconsistent implementations — v1.6
- ✓ Openings reference table (3641 entries from TSV) with SQL-side WDL aggregation — v1.6
- ✓ Most played openings (top 10 per color) with filter support and minimap popovers — v1.6
- ✓ Smart default chart data from most-played openings when no bookmarks exist — v1.6
- ✓ Chart-enable toggle on bookmark cards with localStorage persistence — v1.6
- ✓ Mobile drawer sidebars for filters and bookmarks with deferred apply — v1.6

### Active

- [ ] Static type checking with astral `ty` + CI/CD integration
- [ ] Type safety review & improvement (replace untyped dicts with TypedDicts/Pydantic models, add missing type hints)
- [ ] Evaluate knip.dev (or similar) for frontend dead export detection
- [ ] Naming improvements across codebase (API endpoints, routes, variables)
- [ ] Code deduplication (DRY principle)
- [ ] Dead code identification and removal
- [ ] DB query optimization (inefficient queries → aggregations)
- [ ] DB column type optimization (game_positions BIGINT/DOUBLE → SmallInteger/REAL)
- [ ] Refactor button brand colors to CSS variables
- [ ] API response schema consistency (consistent Pydantic models across all endpoints)
- [ ] Test coverage analysis (maybe)

### Out of Scope

- Manual PGN file upload — API import only
- In-app game viewer — link to chess.com/lichess instead
- Human-like engine analysis — future: engine evaluation filtered by human move plausibility at target Elo (see Maia Chess approach)
- Offline API data caching — chess data is user-specific + authenticated; caching risks stale analysis
- Swipe-to-navigate between tabs — conflicts with chessboard touch gestures
- Material configuration filter for endgames — deferred to future milestone

## Current Milestone: v1.7 Consolidation, Tooling & Refactoring

**Goal:** Clean up and tighten the codebase for long-term maintainability and extendability.

**Target features:**
- Static type checking with astral `ty` + CI/CD integration
- Type safety review & improvement (replace untyped dicts, add missing type hints)
- Evaluate knip.dev (or similar) for frontend dead export detection
- Naming improvements across codebase (API endpoints, routes, variables)
- Code deduplication (DRY principle)
- Dead code identification and removal
- DB query optimization (inefficient queries → aggregations)
- DB column type optimization (game_positions BIGINT/DOUBLE → SmallInteger/REAL)
- Refactor button brand colors to CSS variables
- API response schema consistency (consistent Pydantic models across all endpoints)
- Test coverage analysis (maybe)

## Current State

v1.6 shipped 2026-03-30. Seven milestones complete (v1.0–v1.6), 39 phases, live at flawchess.com. The platform has a polished, consistent UI with centralized theming, shared WDL chart components, an openings reference table with SQL-side aggregation, smart bookmark defaults, and mobile drawer sidebars. Starting v1.7 consolidation milestone.

## Context

- **Current state:** v1.6 shipped. 39 phases complete across 7 milestones. Live at flawchess.com with CI/CD and Sentry.
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
| CSS variables + Tailwind utilities for theme | Centralized colors without abandoning Tailwind workflow | ✓ Good |
| SVG feTurbulence noise texture | Lightweight CSS-only texture, no image assets | ✓ Good |
| Shared WDLChartRow component | Single source of truth for all WDL visualizations | ✓ Good |
| Openings reference table from TSV | 3641 curated openings with ECO/PGN/FEN for position lookup | ✓ Good |
| SQL-side WDL aggregation (func.count.filter) | Moves counting from Python loops to SQL for performance | ✓ Good |
| Deferred filter apply on mobile sidebar close | Prevents API spam while user adjusts multiple filters | ✓ Good |
| Vaul drawers for mobile sidebars | Consistent with existing More drawer pattern, good touch UX | ✓ Good |
| Hetzner CX32 + Docker Compose + Caddy | Simple single-VPS deployment for solo dev | ✓ Good |
| Plausible over Google Analytics | No cookie consent required, GDPR-simple | ✓ Good |
| Sentry for both backend + frontend | Single project, DSN baked at Docker build time | ✓ Good |
| asyncio.Semaphore rate limiter | Per-platform concurrency control without Redis/Celery | ✓ Good |
| Backend expose-only (no ports) | Caddy is sole internet-facing entry point | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-31 after v1.7 milestone start*
