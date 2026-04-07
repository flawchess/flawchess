---
gsd_state_version: 1.0
milestone: v1.9
milestone_name: Advanced Analytics
status: executing
last_updated: "2026-04-07T19:24:44.530Z"
last_activity: 2026-04-07
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 100
---

# Project State: FlawChess

## Current Position

Phase: 49
Plan: Not started
Milestone: v1.8 Guest Access — SHIPPED 2026-04-06
Status: Executing Phase 48
Last activity: 2026-04-07

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

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260406-rzt | Guide new users post-import: success CTA, pulsing bookmark dot, improved empty state | 2026-04-06 | 4dbdea0 | [260406-rzt-guide-new-users-post-import-success-cta-](./quick/260406-rzt-guide-new-users-post-import-success-cta-/) |

---
Last activity: 2026-04-06 - Completed quick task 260406-rzt: Guide new users post-import: success CTA linking to Openings, pulsing dot on Bookmarks tab, improved bookmarks empty state hint
