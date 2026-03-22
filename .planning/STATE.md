---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Project Launch
status: unknown
stopped_at: Completed 23-04-PLAN.md
last_updated: "2026-03-22T10:20:33.445Z"
last_activity: 2026-03-22
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 10
  completed_plans: 9
---

# Project State: FlawChess

## Current Position

Phase: 24
Plan: Not started

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-21)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Phase 20 — Rename & Branding

## Phase Progress

| Phase | Status |
|-------|--------|
| 20. Rename & Branding | Not started |
| 21. Docker & Deployment | Not started |
| 22. CI/CD & Monitoring | Not started |
| 23. Launch Readiness | Not started |

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- v1.2 was frontend-only — no backend changes, no new API routes

## Accumulated Context

### Decisions

- [v1.3 roadmap]: Plausible Cloud chosen over Google Analytics — no cookie consent required, eliminates GDPR complexity
- [v1.3 roadmap]: Single Hetzner VPS (CX32) with Docker Compose + Caddy — no orchestration overhead for solo dev
- [v1.3 roadmap]: Rename must be Phase 20 — Sentry/Plausible project names embed at creation time and are hard to change
- [v1.3 roadmap]: BRAND-05 (README) in Phase 23 — screenshots need live domain and final branding in place
- [Phase 20]: CSRF cookie renamed from chessalytics_oauth_csrf to flawchess_oauth_csrf — pre-production, acceptable
- [Phase 20]: apple-touch-icon.png is a copy of icon-192.png as placeholder — user will provide final 180x180 asset
- [Phase 21]: Backend expose-only (no ports) — Caddy is sole internet-facing entry point, no direct backend access from host
- [Phase 21]: CORS disabled in production — Caddy routes frontend and API on same origin (flawchess.com)
- [Phase 21]: Caddy build context is project root with dockerfile: frontend/Dockerfile so COPY deploy/Caddyfile paths work
- [Phase 22-ci-cd-monitoring]: pip install uv in CI over astral-sh/setup-uv action — simpler, avoids third-party action uncertainty
- [Phase 22-ci-cd-monitoring]: command_timeout: 10m on SSH deploy action — cold docker builds take 3-5 min and need headroom
- [Phase 22-ci-cd-monitoring]: Sentry disabled by default (SENTRY_DSN empty string) — no noise in dev, no console errors
- [Phase 22-ci-cd-monitoring]: Single Sentry project for backend and frontend — same DSN value for SENTRY_DSN and VITE_SENTRY_DSN
- [Phase 22-ci-cd-monitoring]: VITE_SENTRY_DSN baked into frontend bundle at Docker build time via ARG/ENV in Dockerfile and args: in docker-compose.yml
- [Phase 23-02]: Semaphore lazy-init at call time avoids asyncio event loop not started error (Python 3.10+)
- [Phase 23-02]: TimeoutError caught before Exception in run_import — Python 3.11+ TimeoutError is subclass of Exception, ordering matters
- [Phase 23-02]: Lichess semaphore held for entire stream duration — limits connections, not individual requests
- [Phase 23-01]: Inlined feature sections and FAQ items to ensure literal data-testid strings are present in source for grep-based acceptance criteria
- [Phase 23-01]: Kept useUserProfile import in App.tsx — consumed by MobileMoreDrawer, not only by removed HomeRedirect
- [Phase 23-03]: Static meta tags in index.html — no head management library (D-09 compliant)
- [Phase 23-03]: document.title via useEffect in PrivacyPage — no react-helmet dependency needed
- [Phase 23-03]: robots.txt and sitemap.xml in public/ — served automatically as static files by Vite/Caddy
- [Phase 23-04]: MON-03 (analytics) acknowledged as deferred — no Plausible/analytics implementation in phase 23
- [Phase 23-04]: Concurrent importer notice placed inside ImportProgressBar component (per-job, not global)

### Roadmap Evolution

- Phase 24 added: Theme Management — unified color theme across Tailwind, react-chessboard, charts, branded buttons

### Blockers/Concerns

- [Phase 21]: Confirm Hetzner CX32 pricing at hetzner.com before provisioning
- [Phase 21]: Hosting platform decision deferred to phase planning (Hetzner CX32 recommended)
- [Phase 23]: Analytics tool final decision in phase planning — affects privacy policy wording (Plausible recommended)
- [Phase 22]: GitHub Actions secrets require VPS to exist (Phase 21 prerequisite)
- [Research]: chess.com rate-limit threshold ~3-4 concurrent (community-reported, unverified) — tune semaphore post-launch

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions
- **Display opening name from lichess chess-openings database** (ui) — ECO code + opening name via prefix-match
- **Refactor button brand colors to CSS variables** (ui) — move PRIMARY_BUTTON_CLASS from theme.ts to @theme inline CSS variables

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260320-nku | Fix lichess import: games fetched but not saved when lichess username was previously imported by another user | 2026-03-20 | 08d7016 | [260320-nku-fix-lichess-import-games-fetched-but-not](./quick/260320-nku-fix-lichess-import-games-fetched-but-not/) |
| 260320-oiu | Sort board arrows grey->red->green so win/loss arrows are never hidden beneath neutral grey arrows | 2026-03-20 | 69d2bab | [260320-oiu-draw-grey-arrows-first-then-red-then-gre](./quick/260320-oiu-draw-grey-arrows-first-then-red-then-gre/) |
| 260320-ouo | Replace all info icon tooltips with click-based InfoPopover (Radix Popover) to fix mobile tap flash-close | 2026-03-20 | 76b998e | [260320-ouo-fix-mobile-tooltip-info-icons-flashing-a](./quick/260320-ouo-fix-mobile-tooltip-info-icons-flashing-a/) |
| 260321-erm | Mobile UX: GameCard shows opponent-only on mobile; BookmarkCard shows mini board at all sizes with wrapping label | 2026-03-21 | 2d91c57 | [260321-erm-mobile-ux-hide-player-name-in-game-card-](./quick/260321-erm-mobile-ux-hide-player-name-in-game-card-/) |
| 260321-f2h | Reorder board controls: move buttons directly below chessboard with bg-muted background, info icon in controls row, sticky on mobile | 2026-03-21 | ab02e1f | [260321-f2h-reorder-chessboard-controls-move-buttons](./quick/260321-f2h-reorder-chessboard-controls-move-buttons/) |
| 260321-ftk | Rename Openings sub-tab Statistics->Compare, Global Stats->Statistics in top nav, add icons to desktop nav and Openings tabs | 2026-03-21 | bf9009b | [260321-ftk-rename-statistics-sub-tab-to-compare-ren](./quick/260321-ftk-rename-statistics-sub-tab-to-compare-ren/) |
| 260321-gdd | Add min-h-11 sm:min-h-0 to Time Control and Platform filter buttons for uniform 44px mobile touch targets | 2026-03-21 | 389b8e9 | [260321-gdd-make-filter-toggle-buttons-same-height-a](./quick/260321-gdd-make-filter-toggle-buttons-same-height-a/) |
| 260321-gy2 | Bookmark saves position at current ply instead of final position | 2026-03-21 | 72b6637 | [260321-gy2-bookmark-saves-position-at-current-ply-i](./quick/260321-gy2-bookmark-saves-position-at-current-ply-i/) |
| 260321-txu | Add /api prefix to all backend routes for single Caddy /api/* reverse proxy rule | 2026-03-21 | 8b7b5a2 | [260321-txu-add-api-prefix-to-all-backend-routes](./quick/260321-txu-add-api-prefix-to-all-backend-routes/) |
| 260322-c36 | Brown chessboard squares (#8B6914/#D4A843) and warm primary buttons (#8B5E3C) to match detective horse logo branding | 2026-03-22 | 5584500 | [260322-c36-brown-chessboard-and-warm-primary-button](./quick/260322-c36-brown-chessboard-and-warm-primary-button/) |

---
Last activity: 2026-03-22
Last session: 2026-03-22T10:17:04.356Z
Stopped at: Completed 23-04-PLAN.md
