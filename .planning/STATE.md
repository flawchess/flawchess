---
gsd_state_version: 1.0
milestone: v1.14
milestone_name: Score-Based Opening Insights
status: ready_to_plan
last_updated: "2026-04-28T10:10:06.113Z"
last_activity: 2026-04-28 -- Phase 75 execution started
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 0
  completed_plans: 0
---

# Project State: FlawChess

## Current Position

Phase: 999.1
Plan: Not started
Status: Ready to plan
Resume: .planning/phases/75-backend-score-metric-confidence-annotation/75-CONTEXT.md
Last activity: 2026-04-28

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-26)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.13 (SEED-005 Opening Insights). Roadmap covers Phases 70-74; pre-v1.13 quick task PRE-01 (top-10 parity-filter fix) landed 2026-04-26; Phase 70 ready to start. SEED-006 (Benchmark population zone recalibration) holds the deferred classifier-validation phases until full benchmark ingest completes.

## Milestone Progress

v1.12 shipped 2026-04-26 with 1 phase (69), 6 plans, delivered via PR #65. Twelve milestones complete (v1.0-v1.12). v1.13 opened 2026-04-26 with 5 phases (70-74), Phases 73-74 marked stretch. 0 plans committed yet (filled at `/gsd-plan-phase` time).

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, Google SSO, guest sessions, admin impersonation)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import — Phase 70 reuses this directly for finding deduplication
- Deployment: Docker Compose on Hetzner CX32 (4 vCPUs, 7.6 GB RAM + 2 GB swap)
- v1.11 LLM stack: pydantic-ai Agent with env-var-driven model selection (`PYDANTIC_AI_MODEL_INSIGHTS`), `genai-prices` for cost accounting, generic `llm_logs` Postgres table — v1.13 deliberately does NOT use the LLM layer (templated-only)
- v1.12 Benchmark DB: separate PostgreSQL 18 instance on port 5433 — v1.13 deliberately does NOT consume this (book-move equality makes population baselines redundant for opening insights, per SEED-005)
- v1.13 reuse points: `query_top_openings_sql_wdl` (must land PRE-01 fix first), `apply_game_filters`, `game_positions` Zobrist-hash schema, v1.11 in-tab insights placement idiom (red/green semantic colors, mobile drawer compatibility, EndgameInsightsBlock loading/error patterns)

## Accumulated Context

### Deferred Items

Acknowledged at v1.13 milestone close on 2026-04-27:

| Category | Item | Status |
|----------|------|--------|
| requirements | INSIGHT-MOVES-01..03, INSIGHT-META-01, INSIGHT-BADGE-01 | Descoped 2026-04-27 (covered by Move Explorer row tint + per-finding cards; alert-fatigue concern on bookmark badge) |
| uat | Phase 71 UAT — 18 open scenarios | Deferred — phase shipped via PR #67; remaining UAT scenarios captured in 71-UAT.md, not blocking close |
| uat | Phase 71.1 HUMAN-UAT — 9 open scenarios | Deferred — phase shipped via PR #68; remaining UAT scenarios captured in 71.1-HUMAN-UAT.md, not blocking close |
| verification | Phase 71.1 VERIFICATION — `human_needed` | Deferred — automated gates green; manual verification not blocking close |
| audit | 8 stale debug session entries (diagnosed/awaiting_human_verify, March-April) | Carried forward from v1.12; not relevant to v1.13 active work |
| audit | 129 quick-task directory entries without status frontmatter | Historical archive (already merged in git); audit misclassifies as open |
| todos | bitboard-storage-for-partial-position-queries (database) | Carried forward — long-range idea, not v1.14 candidate yet |
| todos | phase-70-requirements-roadmap-amendments (planning) | Closed — amendments landed in Plan 70-05 commit |
| seeds | SEED-002 (benchmark population baselines), SEED-006 (zone recalibration), SEED-005 (opening insights) | Dormant — SEED-005 fulfilled by v1.13; SEED-002/006 await full benchmark ingest |

Acknowledged at v1.12 milestone close on 2026-04-26:

| Category | Item | Status |
|----------|------|--------|
| requirements | Plan 69-06 sub-task 06-05 (`--per-cell 30` interim ingest) | Descoped — operational ops, not milestone gate (per 2026-04-26 v1.12 scope-down) |
| requirements | Plan 69-06 sub-task 06-08 (manual cleanup of 2026-03 Lichess dump file) | Pending manual cleanup on Adrian's local disk |
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
- 2026-04-26: v1.12 mid-milestone scope-down moved the originally-planned follow-on classifier-validation phases to SEED-006 (Benchmark Population Zone Recalibration), gated on full benchmark ingest. Phase-number range 70-74 was subsequently allocated to v1.13.
- 2026-04-26: v1.13 roadmap created — Phases 70-74, source SEED-005, 20/20 active requirements mapped, Phases 73-74 marked stretch.
- Phase 71.1 inserted after Phase 71: Openings subnav layout refactor — match Endgames pattern (frontend-only UI restructuring; design notes at .planning/notes/openings-subnav-refactor.md) (URGENT)

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
| 260426-pbo | Drop parity filter on top-10 openings, prefix off-color rows with "vs." (PRE-01) | 2026-04-26 | 3301ff5 | [260426-pbo-drop-parity-filter-on-top-10-openings-pr](./quick/260426-pbo-drop-parity-filter-on-top-10-openings-pr/) |
| 260427-g4a | Fix opening insights IllegalMoveError when entry_san_sequence does not start from initial position (#71 hotfix) | 2026-04-27 | 8bc4337 | [260427-g4a-fix-opening-insights-illegalmoveerror-wh](./quick/260427-g4a-fix-opening-insights-illegalmoveerror-wh/) |
| 260427-h3u | Replace OpeningFindingCard whole-card deeplink with explicit Moves + Games links (drops n=, ExternalLink icon) | 2026-04-27 | ae44c6e | [260427-h3u-in-opening-strengths-and-weaknesses-card](./quick/260427-h3u-in-opening-strengths-and-weaknesses-card/) |
| 260427-j41 | Highlight candidate move in Move Explorer when arriving via Insights Moves link (severity-colored row border, pulsating board arrow, auto-scroll, clear on position/filter change) | 2026-04-27 | b6c1f29 | [260427-j41-highlight-candidate-move-in-move-explore](./quick/260427-j41-highlight-candidate-move-in-move-explore/) |
| 260428-doc-framing-refresh | Refresh PROJECT/CLAUDE/README lead sections to match homepage's 5-feature framing (Endgame Analytics + Opening Insights + Time Management + Comparison + System Filter) | 2026-04-28 | ce250a4 | [260428-doc-framing-refresh](./quick/260428-doc-framing-refresh/) |

---
Last activity: 2026-04-27 — Phase 71.1 Plan 03 complete (cleanup gates green; phase ready for verification).
| 2026-04-27 | fast | Mobile: Moves/Games links beside mini board in OpeningFindingCard | ✅ |
| 2026-04-27 | fast | widen game card WDL left border | ✅ |
