---
gsd_state_version: 1.0
milestone: none
milestone_name: "(planning v1.15 via /gsd-new-milestone)"
status: "v1.14 shipped 2026-04-29"
last_updated: "2026-04-29T10:50:00.000Z"
last_activity: "2026-04-29 -- v1.14 milestone closed"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State: FlawChess

## Current Position

Milestone: v1.14 SHIPPED 2026-04-29
Next: open v1.15 via `/gsd-new-milestone`
Last activity: 2026-04-29 — v1.14 milestone closed (Score-Based Opening Insights; Phases 75, 76, 77; INSIGHT-UI-04 descoped)

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-29 after v1.14 close)
Core value: Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary on endgame performance and an auto-generated opening-strengths/weaknesses report (now score-based with low/medium/high confidence calibration).
Current focus: v1.15 unselected — pick direction via `/gsd-new-milestone`. SEED-002 (benchmark population baselines) and SEED-006 (zone recalibration) remain dormant, gated on full benchmark ingest. LLM narration of opening insights is the natural next consumer of the v1.14 calibrated data plumbing (effect size + confidence + p_value).

## Milestone Progress

Fourteen milestones complete (v1.0–v1.14). v1.14 Score-Based Opening Insights shipped 2026-04-29 with 3 phases (75, 76, 77), 16 plans, delivered via PRs #69, #70, #71 (inline confidence-mute hotfix), #72, #73 (quick task). Stats: 123 files changed, +18,701 / -787 lines over 2 days since v1.13 (commit f15b3cc → fa5ac64). 73 phases total (+4 inserted: 27.1, 28.1, 41.1, 57.1, 71.1).

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, Google SSO, guest sessions, admin impersonation)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (4 vCPUs, 7.6 GB RAM + 2 GB swap)
- v1.11 LLM stack: pydantic-ai Agent with env-var-driven model selection (`PYDANTIC_AI_MODEL_INSIGHTS`), `genai-prices` for cost accounting, generic `llm_logs` Postgres table
- v1.12 Benchmark DB: separate PostgreSQL 18 instance on port 5433 — dormant (gated on full ingest); SEED-002 / SEED-006 still pending
- v1.14 score plumbing: trinomial Wald 95% half-width drives `confidence: "low" | "medium" | "high"`; `OpeningInsightFinding` and `NextMoveEntry` payloads expose `score`, `confidence`, `p_value`. `compute_confidence_bucket` is the single shared helper (CI structural assertion). `arrowColor.ts` and backend constants are kept in lock-step by `tests/services/test_opening_insights_arrow_consistency.py`. Natural next consumer: LLM narration of opening insights.

## Accumulated Context

### Deferred Items

Acknowledged at v1.14 milestone close on 2026-04-29:

| Category | Item | Status |
|----------|------|--------|
| requirements | INSIGHT-UI-04 (soften titles per SEED-008) | Descoped 2026-04-28 (Phase 76 D-04 — severity word never user-facing; confidence badge + sort cover SEED-008 intent) |
| uat | Phase 77 HUMAN-UAT — 3 open scenarios | Deferred — phase shipped via PR #72; remaining scenarios in `77-HUMAN-UAT.md`, not blocking close |
| verification | Phase 77 VERIFICATION — `human_needed` | Deferred — automated gates green; manual verification not blocking close |
| audit | 9 stale debug session entries (diagnosed/awaiting_human_verify, March-April) | Carried forward; not relevant to v1.14 active work |
| audit | 133 quick-task directory entries without status frontmatter | Historical archive (already merged in git); audit misclassifies as open |
| todos | bitboard-storage-for-partial-position-queries (database) | Carried forward — long-range idea |
| todos | phase-70-requirements-roadmap-amendments (planning) | Already landed in Plan 70-05; todo file not pruned |
| seeds | SEED-002 (benchmark population baselines), SEED-006 (zone recalibration) | Dormant — gated on full benchmark ingest |
| future | LLM narration of opening insights | Future seed — v1.14 shipped the calibrated data plumbing (effect size + confidence + p_value) that LLM narration would consume |
| tech debt | Pre-existing ORM/DB column drift (`game_positions.clock_seconds`, `games.white_accuracy`, `games.black_accuracy`) | Carried forward from v1.11 — cleanup migration outstanding |

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

- v1.0–v1.14 shipped (see .planning/MILESTONES.md)
- v1.14 shipped 2026-04-29 with 3 phases (75, 76, 77), 16 plans, delivered via PRs #69, #70, #71 (inline confidence-mute hotfix), #72, #73 (quick task). INSIGHT-UI-04 descoped per Phase 76 D-04.
- 2026-04-28: Phase 77 (troll-opening watermark) added off-roadmap-scope under v1.14 — frontend-only follow-on with no v1.15 dependency.
- 2026-04-28: Phase 75 amended INSIGHT-SCORE-04 from binomial Wilson → trinomial Wald (D-05) and INSIGHT-SCORE-06 to add `p_value` alongside `confidence` (D-09). REQUIREMENTS.md updated in Plan 75-04.

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
| 260428-oxr | Replace Wald CI half-width confidence buckets with p-value thresholds and N>=10 gate | 2026-04-28 | f29617d | [260428-oxr-replace-wald-ci-half-width-confidence-bu](./quick/260428-oxr-replace-wald-ci-half-width-confidence-bu/) |
| 260428-tgg | Sort opening insights findings by Wald CI bound (direction-aware tiebreak replacing effect-size) | 2026-04-28 | 45c5a20 | [260428-tgg-sort-opening-insights-findings-by-wald-c](./quick/260428-tgg-sort-opening-insights-findings-by-wald-c/) |
| 260428-v9i | Switch opening insights ranking from Wald CI bound to Wilson score interval bound | 2026-04-28 | 0715fda | [260428-v9i-switch-opening-insights-ranking-from-wal](./quick/260428-v9i-switch-opening-insights-ranking-from-wal/) |
| 260429-gmj | Insights finding cards: arrow for after-move on mini board | 2026-04-29 | de187ed | [260429-gmj-insights-finding-cards-arrow-for-after-m](./quick/260429-gmj-insights-finding-cards-arrow-for-after-m/) |

---
Last activity: 2026-04-29 — v1.14 milestone closed. Score-Based Opening Insights shipped (Phases 75, 76, 77; 16 plans; INSIGHT-UI-04 descoped). Next: open v1.15 via `/gsd-new-milestone`.
