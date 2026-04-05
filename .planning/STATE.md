---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Advanced Analytics
status: active
last_updated: "2026-04-04T00:00:00.000Z"
last_activity: 2026-04-04
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State: FlawChess

## Current Position

Phase: 44 of 46 (Endgame ELO — Backend + Breakdown Table)
Plan: —
Status: Ready to plan
Last activity: 2026-04-04 — v1.8 roadmap created, 3 phases defined (44-46)

Progress: [░░░░░░░░░░] 0%

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.8 Advanced Analytics — Phase 44

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (2 vCPUs, 3.7 GB RAM + 2 GB swap)

## Accumulated Context

### Decisions

- Phase 44: Endgame ELO uses per-(platform, time-control) breakdown — NO cross-platform normalization (dropped in favor of honest native-scale display)
- Phase 44: Endgame ELO formula inverts the original 999.5 approach: start with user's actual rating per combo, adjust by how user's conv/recov compares to FIXED baselines (e.g. ~85% conv, ~15% recov) to produce Endgame ELO
- Phase 44: Uses user's own rating (from games table, per-combo), NOT opponent rating — so opponent color inversion pitfall does not apply
- Phase 44: Baseline constants are flagged as calibration values — refine post-launch based on empirical data
- Phase 44: UI is a breakdown TABLE (Actual ELO | Endgame ELO | Gap per combo), not a gauge — no gauge-domain decision needed
- Phase 44: Minimum rated-game threshold per combo; "Insufficient data" fallback when nothing qualifies
- Phase 45: Timeline shows paired color-matched lines per combo (bright = Endgame ELO, dark = Actual ELO)
- Phase 46: Opening risk = variance of `material_imbalance` at opening→middlegame transition positions (NOT WDL entropy — rejected as unhelpful to users)
- Phase 46: Opening drawishness = draw rate of games that ended during opening phase (never reached middlegame), using existing `game_phase` classification from v1.5; muted display for low samples

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions

### Blockers/Concerns

- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)
- bulk_insert_positions chunk_size tuning required when adding columns — asyncpg 32767 arg limit
- Phase 44: Fixed baseline constants for conv/recov need to be reasonable starting values — refine after launch based on observed Endgame ELO numbers vs user intuition
- Phase 46: Material imbalance variance may still conflate with blunders at low ELO — treat as relative within-player metric, not absolute cross-player comparison

---
Last activity: 2026-04-04 - v1.8 roadmap created (phases 44-46)
