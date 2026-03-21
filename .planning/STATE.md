---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Mobile & PWA
status: unknown
last_updated: "2026-03-21T08:41:41.435Z"
last_activity: 2026-03-21
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 5
  completed_plans: 5
---

# Project State: Chessalytics

## Current Position

Phase: 19 (mobile-ux-polish-install-prompt) — COMPLETE
Plan: 3 of 3

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Phase 17 — PWA Foundation + Dev Workflow

## Phase Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 17. PWA Foundation + Dev Workflow | 1/1 | Complete | 2026-03-20 |
| 18. Mobile Navigation | 1/1 | Complete | 2026-03-20 |
| 19. Mobile UX Polish + Install Prompt | 3/3 | Complete | 2026-03-21 |

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- v1.2 scope: frontend-only — no backend changes, no new API routes

## Accumulated Context

### Key Decisions (v1.2)

- Use `vite-plugin-pwa ^1.2.0` with `generateSW` mode — zero-config, Vite 7 compatible
- `NetworkOnly` strategy mandatory for all API routes — prevents stale analysis data
- Cloudflare Tunnel preferred over ngrok — faster, free, no session time limit
- Disable `arePiecesDraggable` on touch devices — HTML5 DnD absent on iOS Safari; click-to-move fallback
- iOS PWA requires re-login after install — WKWebView storage isolation; manifest `scope: "/"` keeps OAuth in PWA
- `allowedHosts: true` (boolean, not string 'all') — Vite 7 uses correct typed value; TUNNEL env guard keeps it secure
- vaul (via shadcn) for bottom drawer — handles scroll lock, backdrop, iOS momentum without manual DOM manipulation
- tailwindcss-safe-area plugin for pb-safe/pt-safe — avoids hardcoded pixel offsets for notch/home-indicator clearance
- Pure Tailwind sm: breakpoints for mobile/desktop switching — no JS-based detection to avoid hydration mismatches
- min-h-11 sm:min-h-0 on ToggleGroupItems individually (not ToggleGroup wrapper) for per-item 44px height on mobile
- h-11 w-11 sm:h-8 sm:w-8 on icon Buttons for 44px mobile touch targets, 32px desktop
- `allowDragging: false` on react-chessboard — disables drag globally to fix black screen on mobile; click-to-move via onSquareClick fires natively on touch (no onPointerUp fallback needed)
- Mobile Openings layout duplicates sidebar JSX intentionally — sticky board structure incompatible with sidebar's flat flex-column
- isOpeningsRoute = pathname.startsWith('/openings') in ProtectedLayout hides MobileHeader on Openings route only
- isMobile userAgent guard on showAndroidPrompt prevents desktop Chrome install drawer (bug found during verification)
- Full Android/iOS PWA install testing deferred to post-deployment (HTTPS required for beforeinstallprompt)

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions
- **Display opening name from lichess chess-openings database** (ui) — ECO code + opening name via prefix-match

### Blockers/Concerns

- [Phase 17]: Cloudflare Tunnel + Vite proxy compatibility not yet verified end-to-end
- [Phase 17]: Google SSO OAuth in PWA standalone on iOS needs physical device testing
- [Phase 19]: react-chessboard touch drag on Android Chrome unverified — click-to-move is confirmed fallback

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260320-nku | Fix lichess import: games fetched but not saved when lichess username was previously imported by another user | 2026-03-20 | 08d7016 | [260320-nku-fix-lichess-import-games-fetched-but-not](./quick/260320-nku-fix-lichess-import-games-fetched-but-not/) |
| 260320-oiu | Sort board arrows grey->red->green so win/loss arrows are never hidden beneath neutral grey arrows | 2026-03-20 | 69d2bab | [260320-oiu-draw-grey-arrows-first-then-red-then-gre](./quick/260320-oiu-draw-grey-arrows-first-then-red-then-gre/) |
| 260320-ouo | Replace all info icon tooltips with click-based InfoPopover (Radix Popover) to fix mobile tap flash-close | 2026-03-20 | 76b998e | [260320-ouo-fix-mobile-tooltip-info-icons-flashing-a](./quick/260320-ouo-fix-mobile-tooltip-info-icons-flashing-a/) |
| 260321-erm | Mobile UX: GameCard shows opponent-only on mobile; BookmarkCard shows mini board at all sizes with wrapping label | 2026-03-21 | 2d91c57 | [260321-erm-mobile-ux-hide-player-name-in-game-card-](./quick/260321-erm-mobile-ux-hide-player-name-in-game-card-/) |
| 260321-f2h | Reorder board controls: move buttons directly below chessboard with bg-muted background, info icon in controls row, sticky on mobile | 2026-03-21 | ab02e1f | [260321-f2h-reorder-chessboard-controls-move-buttons](./quick/260321-f2h-reorder-chessboard-controls-move-buttons/) |
| 260321-ftk | Rename Openings sub-tab Statistics->Compare, Global Stats->Statistics in top nav, add icons to desktop nav and Openings tabs | 2026-03-21 | bf9009b | [260321-ftk-rename-statistics-sub-tab-to-compare-ren](./quick/260321-ftk-rename-statistics-sub-tab-to-compare-ren/) |

---
Last activity: 2026-03-21 - Completed quick task 260321-ftk: Rename Statistics sub-tab to Compare, rename Global Stats tab to Statistics, add icons to desktop tabs
Last session: 2026-03-21T10:23:28.065Z
