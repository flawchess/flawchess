---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Game Statistics & Endgame Analysis
status: defining_requirements
last_updated: "2026-03-23T00:00:00.000Z"
last_activity: 2026-03-23
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State: FlawChess

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-23 — Milestone v1.5 started

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-23)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Game Statistics & Endgame Analysis

## Phase Progress

(No phases yet — defining requirements)

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (2 vCPUs, 3.7 GB RAM + 2 GB swap)

## Accumulated Context

### Decisions

- [v1.4 roadmap]: Analytics tool choice deferred to phase planning — candidates: Plausible, Umami, GoAccess
- [Phase 24-web-analytics]: Umami shares existing db PostgreSQL container (no separate DB); Node.js heap capped at 256 MB; no Caddy-level auth on analytics subdomain

### Roadmap Evolution

- Phase 25 added: Add password reset functionality

### Blockers/Concerns

(None)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260323-pkf | Gradient arrow colors: green from 55-65% win rate, red from 45-35% loss rate | 2026-03-23 | 698c37b | [260323-pkf-gradient-arrow-colors-green-from-55-65-w](./quick/260323-pkf-gradient-arrow-colors-green-from-55-65-w/) |
| 260323-q89 | Categorical arrow colors and fix arrow render order | 2026-03-23 | e9afcf3 | [260323-q89-categorical-arrow-colors-and-fix-renderi](./quick/260323-q89-categorical-arrow-colors-and-fix-renderi/) |
| 260323-rtg | Create better Android and iOS app icons with padded, separate any/maskable PWA icons | 2026-03-23 | b60e1c4 | [260323-rtg-create-better-android-and-ios-app-icons-](./quick/260323-rtg-create-better-android-and-ios-app-icons-/) |

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions
- **Display opening name from lichess chess-openings database** (ui) — ECO code + opening name via prefix-match
- **Refactor button brand colors to CSS variables** (ui) — move PRIMARY_BUTTON_CLASS from theme.ts to @theme inline CSS variables

---
Last activity: 2026-03-23 — Milestone v1.5 started
