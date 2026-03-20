---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Mobile & PWA
status: unknown
stopped_at: Completed 17-01-PLAN.md
last_updated: "2026-03-20T14:22:37.789Z"
last_activity: "2026-03-20 — Phase 17 Plan 01 complete: all 3 tasks done; user verified PWA manifest, service worker, cache storage, and API NetworkOnly routing in Chrome DevTools"
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 1
  completed_plans: 1
---

# Project State: Chessalytics

## Current Position

Phase: 17 (pwa-foundation-dev-workflow) — COMPLETE
Plan: 1 of 1 (all plans complete)
Stopped at: Completed 17-01-PLAN.md

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Phase 17 — PWA Foundation + Dev Workflow

## Phase Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 17. PWA Foundation + Dev Workflow | 1/1 | Complete | 2026-03-20 |
| 18. Mobile Navigation | 0/TBD | Not started | - |
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

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions
- **Display opening name from lichess chess-openings database** (ui) — ECO code + opening name via prefix-match

### Blockers/Concerns

- [Phase 17]: Cloudflare Tunnel + Vite proxy compatibility not yet verified end-to-end
- [Phase 17]: Google SSO OAuth in PWA standalone on iOS needs physical device testing
- [Phase 19]: react-chessboard touch drag on Android Chrome unverified — click-to-move is confirmed fallback

---
Last activity: 2026-03-20 — Phase 17 Plan 01 complete: all 3 tasks done; user verified PWA manifest, service worker, cache storage, and API NetworkOnly routing in Chrome DevTools
