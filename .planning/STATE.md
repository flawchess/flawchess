---
gsd_state_version: 1.0
milestone: none
milestone_name: (between milestones)
status: idle
last_updated: "2026-04-25T13:55:00Z"
last_activity: 2026-04-25 -- Completed quick task 260425-lwz: month-enumeration fallback when chess.com archives-list 404s for real users
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State: FlawChess

## Current Position

Milestone: (between milestones)
Phase: none
Plan: none
Status: v1.11 shipped 2026-04-24. Awaiting `/gsd-new-milestone` to open the next cycle.
Last activity: 2026-04-24 -- v1.11 LLM-first Endgame Insights milestone shipped (PR #61 squash-merged, tagged v1.11)

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-24)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Awaiting next milestone. v1.12 candidates (from v1.11 deferred work): retrofit VAL-01 snapshot test; explore Insights for Openings and Global Stats tabs; rating-stratified population baselines (SEED-002).

## Milestone Progress

No active milestone. Twelve shipped (v1.0-v1.11).

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, Google SSO, guest sessions, admin impersonation)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (4 vCPUs, 7.6 GB RAM + 2 GB swap)
- v1.11 LLM stack: pydantic-ai Agent with env-var-driven model selection (`PYDANTIC_AI_MODEL_INSIGHTS`), `genai-prices` for cost accounting, generic `llm_logs` Postgres table as prompt-engineering harness

## Accumulated Context

### Deferred Items

Accepted at v1.11 milestone close on 2026-04-24:

| Category | Item | Status |
|----------|------|--------|
| requirements | VAL-01 ground-truth regression test | Deferred to v1.12 |
| requirements | VAL-02 admin-impersonation eyeball validation | Replaced by public rollout (commit c91478e) |
| tech debt | Pre-existing ORM/DB column drift (game_positions.clock_seconds, games.white_accuracy, games.black_accuracy) | Deferred — cleanup migration |
| tech debt | `_compute_score_gap_timeline` helper kept old name after subsection rename | Grep noise, not a bug |
| tech debt | `_finding_time_pressure_vs_performance` emits filtered-out finding solely for hash effect | Either drop or promote chart payload |

### Roadmap Evolution

- v1.0–v1.11 shipped (see .planning/MILESTONES.md)
- v1.11 shipped 2026-04-24 with 5 phases (63-66, 68), 23 plans. Phase 67 descoped — insights rolled out to all users instead of beta cohort.

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions

### Blockers/Concerns

- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260425-dxh | Replace endgame insights findings_hash cache with structural cache | 2026-04-25 | 9029f7e | [260425-dxh-implement-endgame-insights-structural-ca](./quick/260425-dxh-implement-endgame-insights-structural-ca/) |
| 260425-lii | Fix misleading "chess.com user not found" error during import | 2026-04-25 | 22d561f | [260425-lii-fix-misleading-chess-com-user-not-found-](./quick/260425-lii-fix-misleading-chess-com-user-not-found-/) |
| 260425-lwz | Fallback to month enumeration when chess.com archives-list endpoint 404s for an existing user | 2026-04-25 | af64f66 | [260425-lwz-fallback-to-month-enumeration-when-chess](./quick/260425-lwz-fallback-to-month-enumeration-when-chess/) |

---
Last activity: 2026-04-25 — Completed quick task 260425-lwz: when chess.com's archives-list endpoint silently 404s for a real account (e.g. wasterram), the import client now enumerates monthly archive URLs from the player's joined date and feeds them into the existing per-archive fetch loop, recovering imports that previously failed with "couldn't return games right now".
| 2026-04-25 | fast | Mobile full-width Overview rating charts | done |
