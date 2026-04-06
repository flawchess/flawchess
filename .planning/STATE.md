---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Guest Access
status: active
last_updated: "2026-04-06T00:00:00.000Z"
last_activity: 2026-04-06
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State: FlawChess

## Current Position

Phase: 47 of 50 in v1.8 (Guest Session Foundation)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-04-06 — v1.8 roadmap created (phases 47-50)

Progress: [░░░░░░░░░░] 0% (v1.8 phases)

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-06)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.8 Guest Access — Phase 47 Guest Session Foundation

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (4 vCPUs, 7.6 GB RAM + 2 GB swap)

## Accumulated Context

### Decisions

- v1.8: Bearer transport for guest JWTs (not CookieTransport) — avoids dual-transport complexity and OAuth redirect issues in Safari/Firefox ETP
- v1.8: Guest as first-class User row with is_guest=True — promotion is single-row UPDATE, no FK migration needed
- v1.8: Conversion optimization (CONV-01/02/03) deferred to post-launch Future Requirements
- Phase 44: Endgame ELO per-(platform, time-control) breakdown — no cross-platform normalization
- Phase 44: Formula adjusts user's actual rating using conv/recov vs fixed baselines; NOT opponent rating
- Phase 46: Opening risk = variance of material_imbalance at opening→middlegame transition

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions

### Blockers/Concerns

- Phase 47: Check whether `slowapi` is installed before using for rate limiting — lightweight manual alternative avoids new dep if not
- Phase 47: Align on guest email sentinel domain (`@guest.local` vs `@guest.flawchess.internal`) before implementation
- Phase 50: New callback URI `/api/auth/guest/promote/google/callback` must be registered in Google Cloud Console — manual action before Phase 50 can be tested end-to-end
- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)

---
Last activity: 2026-04-06 — v1.8 roadmap created, Phase 47 ready to plan
