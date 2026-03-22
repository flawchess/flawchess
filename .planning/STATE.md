---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Improvements
status: in_progress
stopped_at: null
last_updated: "2026-03-22T00:00:00.000Z"
last_activity: "2026-03-22 - Started v1.4 Improvements milestone"
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State: FlawChess

## Current Position

Phase: 24 — Web Analytics
Plan: —
Status: Not started (phase needs planning)
Last activity: 2026-03-22 — Milestone v1.4 started

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-22)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Web Analytics

## Phase Progress

| Phase | Status |
|-------|--------|
| 24. Web Analytics | Not started |

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (2 vCPUs, 3.7 GB RAM + 2 GB swap)

## Accumulated Context

### Decisions

- [v1.4 roadmap]: Analytics tool choice deferred to phase planning — candidates: Plausible, Umami, GoAccess

### Roadmap Evolution

(None yet)

### Blockers/Concerns

(None)

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions
- **Display opening name from lichess chess-openings database** (ui) — ECO code + opening name via prefix-match
- **Refactor button brand colors to CSS variables** (ui) — move PRIMARY_BUTTON_CLASS from theme.ts to @theme inline CSS variables

---
Last activity: 2026-03-22
