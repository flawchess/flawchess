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
- ✓ Knip for frontend dead export detection with CI integration — v1.7
- ✓ Naming improvements (router prefixes, endpoint relocation) — v1.7
- ✓ Code deduplication (shared apply_game_filters, frontend buildFilterParams) — v1.7
- ✓ Dead code removal (7 dead files, unused hooks/types/exports, -1522 lines) — v1.7
- ✓ noUncheckedIndexedAccess TypeScript strictness (56 type errors fixed) — v1.7
- ✓ Static type checking with astral `ty` + CI/CD integration — v1.7
- ✓ DB query optimization (SQL aggregations replacing Python-side counting) — v1.7
- ✓ DB column types verified optimal (no migration needed) — v1.7
- ✓ Refactor button brand colors to CSS variables (.btn-brand) — v1.7
- ✓ Consistent Pydantic response models across all API endpoints — v1.7
- ✓ Import speed optimization (~2x throughput, single PGN parse, bulk UPDATE) — v1.7
- ✓ Guest access — "Use as Guest" button on homepage, JWT-based guest sessions with 30-day auto-refresh — v1.8
- ✓ Guest as first-class User row with is_guest=True, full platform access without special-casing — v1.8
- ✓ Account promotion via email/password or Google SSO, preserving all imported data — v1.8
- ✓ Guest UX — persistent guest banner, import page info box, auth page logo linking — v1.8
- ✓ OAuth CSRF fix (CVE-2025-68481) and guest creation IP rate limiting — v1.8
- ✓ Openings mobile: unified control row (Tabs | Color | Bookmark | Filter) outside the board collapse region, staying visible when the board is collapsed; enlarged board-action column buttons and 44px collapse handle; backdrop-blur translucent sticky surface (MMOB-01) — v1.9 Phase 50
- ✓ Endgames mobile: visual-alignment pass on the sticky top row to match the Openings unified row (backdrop-blur, 44px height, 44px filter button) (EGAM-01) — v1.9 Phase 50

### Active

- [ ] Openings desktop: 2-column layout with collapsible left-edge Filters/Bookmarks panels overlaying the board
- [ ] Stats subtab: 2-column bookmarked openings on desktop, stacked most-played on mobile
- [ ] Homepage: feature content visible without scrolling on desktop
- [ ] Stats page: relabel to "Global Stats" and enable more filters

### Future (v1.10)

- [ ] ELO-Adjusted Endgame Skill — opponent-strength-adjusted composite score with gauge + timeline
- [ ] Refine existing endgame statistics (conversion/recovery rates, performance gauges)
- [ ] New endgame statistics (TBD, added incrementally)
- [ ] Opening Risk and other new opening statistics (TBD, added incrementally)

### Out of Scope

- Manual PGN file upload — API import only
- In-app game viewer — link to chess.com/lichess instead
- Human-like engine analysis — future: engine evaluation filtered by human move plausibility at target Elo (see Maia Chess approach)
- Offline API data caching — chess data is user-specific + authenticated; caching risks stale analysis
- Swipe-to-navigate between tabs — conflicts with chessboard touch gestures
- Material configuration filter for endgames — deferred to future milestone

## Current Milestone: v1.9 UI/UX Restructuring

**Goal:** Restructure page layouts across desktop and mobile based on UI/UX expert recommendations — improve information hierarchy, reduce scrolling, and unify desktop/mobile interaction patterns.

**Target features:**
- Openings desktop: 2-column layout (board + content) with two collapsible left-edge panels (Filters / Bookmarks) that overlay the board
- Openings mobile: restructure subtab navigation placement (above board or bottom near nav — TBD)
- Stats subtab: 2-column "Bookmarked Openings: Results" on desktop; stack "Most Played" on mobile
- Endgames & Games mobile: layout adjustments consistent with Openings mobile changes
- Homepage: make feature content visible without scrolling on desktop (carousel, remove pills, or similar)
- Stats page: relabel to "Global Stats" and enable more existing filters

## Current State

v1.8 shipped 2026-04-06. Nine milestones complete (v1.0–v1.8), 48 phases (+2 inserted), live at flawchess.com. Guest access now lets visitors try the platform without signing up, with seamless promotion to full accounts via email/password or Google SSO. ~20K lines of code (8K Python, 12K TypeScript). Phase 48 complete — endgame conversion/recovery now uses persistence filter (imbalance must hold 4 plies) with lowered 100cp threshold. v1.9 in progress: Phase 50 complete — mobile Openings unified control row outside the board collapse region plus Endgames mobile visual alignment; Phases 49 and 51 still pending.

## Context

- **Current state:** v1.8 shipped. 47 phases complete across 9 milestones. Live at flawchess.com with CI/CD and Sentry.
- **Stack:** FastAPI + React 19/TS/Vite 5 + PostgreSQL + python-chess + TanStack Query + Tailwind + shadcn/ui
- **Auth:** FastAPI-Users (JWT + Google SSO + guest sessions with is_guest flag)
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
| astral ty for static type checking | Catches type errors at CI time, complements ruff | ✓ Good |
| Knip for dead export detection | Automated CI gate prevents dead code accumulation | ✓ Good |
| noUncheckedIndexedAccess in TS | Forces safe array/Record index access patterns | ✓ Good |
| Unified process_game_pgn | Single PGN walk per game instead of 3 separate passes | ✓ Good |
| Bulk CASE UPDATE for move_count/result_fen | One SQL statement per batch vs N per-game UPDATEs | ✓ Good |
| .btn-brand CSS class over JS constant | Styling concern in CSS, not JS import chain | ✓ Good |
| Bearer transport for guest JWTs | Avoids dual-transport complexity, Safari/Firefox ETP issues | ✓ Good |
| Guest as User row with is_guest=True | Promotion is single-row UPDATE, no FK migration needed | ✓ Good |
| Register-page promotion over modal | Cleaner UX, reuses existing register form, less code | ✓ Good |

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
*Last updated: 2026-04-10 after Phase 50 (Mobile Layout Restructuring) completion*
