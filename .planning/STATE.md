---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Guest Access
status: complete
last_updated: "2026-04-06T00:00:00.000Z"
last_activity: 2026-04-06
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 0
  completed_plans: 0
  percent: 100
---

# Project State: FlawChess

## Current Position

Milestone: v1.8 Guest Access — SHIPPED 2026-04-06
Status: Complete — ready for v1.9 planning
Last activity: 2026-04-06 — milestone archived, git tagged

Progress: [██████████] 100% (v1.8 phases)

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-06)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Planning next milestone (v1.9 Advanced Analytics)

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, Google SSO, guest sessions)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (4 vCPUs, 7.6 GB RAM + 2 GB swap)

## Accumulated Context

### Decisions

- v1.8: Bearer transport for guest JWTs (not CookieTransport) — avoids dual-transport complexity and OAuth redirect issues in Safari/Firefox ETP
- v1.8: Guest as first-class User row with is_guest=True — promotion is single-row UPDATE, no FK migration needed
- v1.8: Register-page promotion flow instead of separate PromotionModal — cleaner UX
- v1.8: Conversion optimization (CONV-01/02/03) deferred to post-launch Future Requirements

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions

### Blockers/Concerns

- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)

---
Last activity: 2026-04-06 — v1.8 milestone archived and tagged
