---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Opening Explorer & UI Restructuring
current_plan: —
status: ready_to_plan
stopped_at: —
last_updated: "2026-03-16T00:00:00.000Z"
last_activity: "2026-03-16 — Roadmap v1.1 created (phases 11-14)"
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State: Chessalytics

## Current Phase
Phase: 11 of 14 (Schema and Import Pipeline)
Plan: —
Status: Ready to plan
Last activity: 2026-03-16 — Roadmap v1.1 created (phases 11-14)

Progress: [░░░░░░░░░░] 0%

## Project Reference
See: .planning/PROJECT.md (updated 2026-03-16)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.1 — Opening Explorer & UI Restructuring

## Phase Progress
| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 11 | Schema and Import Pipeline | Not started | TBD |
| 12 | Backend Next-Moves Endpoint | Not started | TBD |
| 13 | Frontend Move Explorer Component | Not started | TBD |
| 14 | UI Restructuring | Not started | TBD |

## Key Context
- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- DB wipe accepted for v1.1 — no backfill migration needed for move_san

## Accumulated Context

### Key Decisions
- **DB wipe for v1.1**: No migration needed — reimport after schema change (settled in PROJECT.md)
- **move_san ply semantics**: move_san on ply N = move played FROM position at ply N (leading to ply N+1); final position row has NULL; ply-0 has NULL
- **DISTINCT + GROUP BY for next-moves**: use COUNT(DISTINCT g.id) not COUNT(*) — transpositions cause same position at multiple plies in one game; mirrors existing _build_base_query discipline
- **Filter state lifted to OpeningsPage**: all shared filter state must live in OpeningsPage parent — not inside sub-tab components — to survive tab switches without reset
- **positionFilterActive gating**: Move Explorer should only activate when at least 1 move played or bookmark loaded (avoids overwhelming starting-position list)
- **Import page cache invalidation**: handleJobDone callbacks must invalidate ['games'], ['gameCount'], ['userProfile'] on the new ImportPage — same as current Dashboard modal

### Pending Todos
- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions for querying pieces on specific squares
- **Display opening name from lichess chess-openings database** (ui) — Show ECO code + opening name on interactive board via prefix-match
- **GamesTab pagination offset survival**: Phase 14 planning should decide whether page offset survives tab switches (lift to OpeningsPage state)

### Blockers/Concerns
None.

---
Last activity: 2026-03-16 — Roadmap v1.1 created (phases 11-14)
