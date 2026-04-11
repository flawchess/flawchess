---
gsd_state_version: 1.0
milestone: v1.10
milestone_name: Advanced Analytics
status: executing
last_updated: "2026-04-11T08:17:32.708Z"
last_activity: 2026-04-11
progress:
  total_phases: 8
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 100
---

# Project State: FlawChess

## Current Position

Phase: 999.5
Plan: Not started
Status: Executing Phase 52
Last activity: 2026-04-11

Progress: [██████████] 100% (4/4 v1.9 phases complete)

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-09)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.9 UI/UX Restructuring — layout improvements across desktop and mobile

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
- v1.9 roadmap: Old v1.9 Advanced Analytics phases (49-51) renumbered to 52-54 under v1.10; new v1.9 phases start at 49
- v1.9 roadmap: Phase 50 (mobile subtab relocation) depends on Phase 49 — subtab placement TBD, needs discussion before planning

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions

### Blockers/Concerns

- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)

### Recently Resolved

- MMOB-01 (subtab placement TBD) resolved 2026-04-10: unified row holding Tabs | color toggle | bookmark | filter inside sticky wrapper but outside the board collapse region — see `.planning/phases/50-mobile-layout-restructuring/50-CONTEXT.md`

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260406-rzt | Guide new users post-import: success CTA, pulsing bookmark dot, improved empty state | 2026-04-06 | 4dbdea0 | [260406-rzt-guide-new-users-post-import-success-cta-](./quick/260406-rzt-guide-new-users-post-import-success-cta-/) |
| 260408-snn | Implement Opponent Strength filter (Any/+100/±100/-100) on Openings and Endgames pages | 2026-04-08 | ac883c6 | [260408-snn-implement-opponent-strength-filter-with-](./quick/260408-snn-implement-opponent-strength-filter-with-/) |
| 260411-fcs | Add Reset Filters button, deferred-apply hint, and pulsing modified indicator across filter panels | 2026-04-11 | c106fc9 | [260411-fcs-add-reset-filters-button-deferred-apply-](./quick/260411-fcs-add-reset-filters-button-deferred-apply-/) |
| 260411-ni2 | Global Reset (except color), uniform modified-dot via FILTER_DOT_FIELDS, secondary button, Openings mobile drawer cleanup | 2026-04-11 | 595bd3b | [260411-ni2-global-reset-filters-matchside-exempt-fr](./quick/260411-ni2-global-reset-filters-matchside-exempt-fr/) |

---
Last activity: 2026-04-11 - Completed quick task 260411-ni2: global Reset (except Played-as), uniform modified-dot, Openings mobile drawer cleanup
| 2026-04-10 | fast | Match Global Stats mobile filter button size to Endgames | done |
| 2026-04-10 | ship | Phase 51 shipped — PR #42 merged into main | done |
| 2026-04-11 | fast | Preserve Openings board position across main tab navigation | ✅ |
