---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Mobile & PWA
status: unknown
last_updated: "2026-03-20T16:04:35.344Z"
last_activity: 2026-03-20
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 2
  completed_plans: 2
---

# Project State: Chessalytics

## Current Position

Phase: 18 (mobile-navigation) — COMPLETE
Plan: 1 of 1 (all complete)

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Phase 17 — PWA Foundation + Dev Workflow

## Phase Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 17. PWA Foundation + Dev Workflow | 1/1 | Complete | 2026-03-20 |
| 18. Mobile Navigation | 1/1 | Complete | 2026-03-20 |
| 19. Mobile UX Polish + Install Prompt | 0/TBD | Not started | - |

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

---
Last activity: 2026-03-20 - Completed quick task 260320-nku: Fix lichess import
Last session: 2026-03-20T16:04:35.342Z
