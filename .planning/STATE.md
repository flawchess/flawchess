---
gsd_state_version: 1.0
milestone: v1.13
milestone_name: Opening Insights
status: planning
last_updated: "2026-04-26T15:44:20.159Z"
last_activity: 2026-04-26
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State: FlawChess

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-26 — Milestone v1.13 started

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-26)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Planning v1.13 (SEED-005 Opening Insights). SEED-006 (Benchmark population zone recalibration) holds Phases 70-73 until full benchmark ingest completes; v1.11 VAL-01 snapshot test is a pre-v1.13 `/gsd-quick` candidate.

## Milestone Progress

v1.12 shipped 2026-04-26 with 1 phase (69), 6 plans, delivered via PR #65. Twelve milestones complete (v1.0-v1.12). Phases 70-73 deferred to SEED-006 (full design preserved with rating-bucketed zone recalibration framing).

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, Google SSO, guest sessions, admin impersonation)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (4 vCPUs, 7.6 GB RAM + 2 GB swap)
- v1.11 LLM stack: pydantic-ai Agent with env-var-driven model selection (`PYDANTIC_AI_MODEL_INSIGHTS`), `genai-prices` for cost accounting, generic `llm_logs` Postgres table as prompt-engineering harness
- v1.12 Benchmark DB: separate PostgreSQL 18 instance on port 5433 (`docker-compose.benchmark.yml`), shares canonical Alembic chain with dev/prod/test, benchmark-only ops tables (`benchmark_selected_users`, `benchmark_ingest_checkpoints`) created via `Base.metadata.create_all()` against the benchmark engine on first invocation. Read-only MCP server `flawchess-benchmark-db` registered.

## Accumulated Context

### Deferred Items

Acknowledged at v1.12 milestone close on 2026-04-26:

| Category | Item | Status |
|----------|------|--------|
| requirements | Plan 69-06 sub-task 06-05 (`--per-cell 30` interim ingest) | Descoped — operational ops, not milestone gate (per 2026-04-26 v1.12 scope-down) |
| requirements | Plan 69-06 sub-task 06-08 (manual cleanup of 2026-03 Lichess dump file) | Pending manual cleanup on Adrian's local disk |
| requirements | VAL-01 from v1.11 (insights snapshot test) | Pre-v1.13 `/gsd-quick` candidate; no benchmark dependency |
| requirements | VAL-01 / VAL-02 / VAL-03 / VAL-04 / BENCH-01..04 | Moved to SEED-006 (gated on full benchmark ingest) |
| tech debt | Pre-existing ORM/DB column drift (game_positions.clock_seconds, games.white_accuracy, games.black_accuracy) | Deferred again — cleanup migration outstanding from v1.11 |
| ops | Full benchmark DB ingest (`--per-cell 100`, ~205 GB projected) | Operational task; entry criterion for SEED-006 |
| audit | 8 stale debug session entries (status=diagnosed/awaiting_human_verify) | Acknowledged at close; not relevant to active work |
| audit | 125 quick-task directory entries without status frontmatter | Historical archive (already merged in git); audit misclassifies as open |

Carried forward from v1.11 close (still relevant):

| Category | Item | Status |
|----------|------|--------|
| tech debt | `_compute_score_gap_timeline` helper kept old name after subsection rename | Grep noise, not a bug |
| tech debt | `_finding_time_pressure_vs_performance` emits filtered-out finding solely for hash effect | Either drop or promote chart payload |

### Roadmap Evolution

- v1.0–v1.12 shipped (see .planning/MILESTONES.md)
- v1.12 shipped 2026-04-26 with 1 phase (69), 6 plans (Plan 69-06 sub-tasks 06-05/06-08 descoped). PR #65.
- 2026-04-26: v1.12 mid-milestone scope-down moved Phases 70-73 to SEED-006 (Benchmark Population Zone Recalibration), gated on full benchmark ingest.

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
Last activity: 2026-04-26 — v1.12 Benchmark DB Infrastructure & Ingestion Pipeline shipped (PR #65 squash-merged). 1 phase, 6 plans. Phases 70-73 deferred to SEED-006. Next: `/gsd-new-milestone` for v1.13 (SEED-005 Opening Insights).
