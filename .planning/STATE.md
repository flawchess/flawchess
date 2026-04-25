---
gsd_state_version: 1.0
milestone: v1.12
milestone_name: Benchmark DB & Population Baselines
status: defining-requirements
last_updated: "2026-04-25T14:30:00Z"
last_activity: 2026-04-25 -- Milestone v1.12 opened from SEED-002 (benchmark DB & population baselines)
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State: FlawChess

## Current Position

Milestone: v1.12 Benchmark DB & Population Baselines
Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-25 — Milestone v1.12 opened from SEED-002

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-24)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.12 Benchmark DB & Population Baselines (SEED-002). Defining requirements before roadmap.

## Milestone Progress

v1.12 active (defining requirements). Twelve milestones shipped (v1.0-v1.11).

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
| 260425-nlv | Restructure GameCard and PositionBookmarkCard layouts (full-width identifier line on top, board left + content right below) | 2026-04-25 | 5a7ad30 | [260425-nlv-restructure-gamecard-and-positionbookmar](./quick/260425-nlv-restructure-gamecard-and-positionbookmar/) |

---
Last activity: 2026-04-25 — Completed quick task 260425-nlv: GameCard and PositionBookmarkCard restructured so the identifier line (player names + platform link / bookmark label) spans the full card width on top, with the mini chessboard below-left and remaining content below-right; mobile-only opponent variant and JS truncateLabel helper removed in favor of CSS truncation.
| 2026-04-25 | fast | Mobile full-width Overview rating charts | done |
