---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Game Statistics & Endgame Analysis
status: ready_to_plan
last_updated: "2026-03-23T00:00:00.000Z"
last_activity: 2026-03-23
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State: FlawChess

## Current Position

Phase: 26 of 29 (Position Classifier & Schema) — ready to plan
Plan: —
Status: Ready to plan
Last activity: 2026-03-23 — v1.5 roadmap created (Phases 26-29)

Progress: [░░░░░░░░░░] 0%

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-23)
Core value: Users can determine their success rate for any opening position they specify
Current focus: Game Statistics & Endgame Analysis (v1.5)

## Phase Progress

| Phase | Goal | Status |
|-------|------|--------|
| 26. Position Classifier & Schema | Classifier + 4-column migration | Not started |
| 27. Import Wiring & Backfill | Wire classifier + backfill existing rows | Not started |
| 28. Endgame Analytics | Backend API + Endgames tab frontend | Not started |
| 29. Engine Analysis Import | chess.com accuracy + lichess per-move evals | Not started |

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
- [v1.5 roadmap]: CONV requirements folded into Phase 28 alongside ENDGM — conversion/recovery stats share the same backend infrastructure (endgames repository + service + router)
- [v1.5 roadmap]: Phase 29 (Engine Analysis Import) is independent of Phase 28 — can be deferred or parallelized; P2 feature

### Critical v1.5 Constraints

- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)
- Backfill must run as standalone script, NOT inside Alembic migration
- All engine analysis columns must be nullable — chess.com accuracy absent for ~95% of games
- Every endgame aggregation query must use COUNT(DISTINCT game_id), not COUNT(*)
- Material signature must be canonical: stronger side first; if equal, lexicographic
- bulk_insert_positions chunk_size must be updated (8 → 12 columns = 2730 rows max)

### Roadmap Evolution

- Phase 25 added: Password reset functionality
- Phases 26-29 added: v1.5 Game Statistics & Endgame Analysis

### Blockers/Concerns

- [Phase 27] Backfill performance on production data unknown — validate batch_size=10 against production DB snapshot with docker stats monitoring before deploying
- [Phase 29] lichess bulk export may omit analysis data — enrichment job design (when to trigger, how to surface status) needs explicit decision before implementation

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions
- **Display opening name from lichess chess-openings database** (ui) — ECO code + opening name via prefix-match
- **Refactor button brand colors to CSS variables** (ui) — move PRIMARY_BUTTON_CLASS from theme.ts to @theme inline CSS variables

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260323-pkf | Gradient arrow colors: green from 55-65% win rate, red from 45-35% loss rate | 2026-03-23 | 698c37b | [260323-pkf-gradient-arrow-colors-green-from-55-65-w](./quick/260323-pkf-gradient-arrow-colors-green-from-55-65-w/) |
| 260323-q89 | Categorical arrow colors and fix arrow render order | 2026-03-23 | e9afcf3 | [260323-q89-categorical-arrow-colors-and-fix-renderi](./quick/260323-q89-categorical-arrow-colors-and-fix-renderi/) |
| 260323-rtg | Create better Android and iOS app icons with padded, separate any/maskable PWA icons | 2026-03-23 | b60e1c4 | [260323-rtg-create-better-android-and-ios-app-icons-](./quick/260323-rtg-create-better-android-and-ios-app-icons-/) |

---
Last activity: 2026-03-23 — v1.5 roadmap created, Phases 26-29 defined
