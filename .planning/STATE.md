---
gsd_state_version: 1.0
milestone: v1.15
milestone_name: Eval-Based Endgame Classification
status: Phase 78 ready for code review; awaiting Phase 79 (lichess Divider phase column + middlegame eval) before combined backfill on benchmark + prod and deploy
last_updated: "2026-05-02T17:30:00.000Z"
last_activity: 2026-05-02 -- Phase 79 context gathered (4 implementation decisions, 13 SPEC requirements locked); ready for /gsd-plan-phase 79
---

# Project State: FlawChess

## Current Position

Phase: 78 (Stockfish-Eval Cutover for Endgame Classification) — CODE COMPLETE (operational rollout deferred)
Plan: 6 of 6 (78-06 ran with slimmed scope: dev-DB smoke for user 28 only; benchmark/prod backfill, VAL-01, deploy, VAL-02 deferred)
Status: Phase 78 ready for code review; awaiting Phase 79 (lichess Divider phase column + middlegame eval) before combined backfill on benchmark + prod and deploy
Last activity: 2026-05-02 -- Phase 79 context gathered (4 implementation decisions, 13 SPEC requirements locked); ready for /gsd-plan-phase 79

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-02 for v1.15 open)
Core value: Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary on endgame performance and an auto-generated opening-strengths/weaknesses report (now score-based with low/medium/high confidence calibration).
Current focus: v1.15 Phase 78 — replace the material-imbalance + 4-ply persistence proxy for endgame conv/recov classification with Stockfish eval (depth 15) populated into existing `eval_cp` / `eval_mate` columns. Backfill benchmark + prod, refactor endgame queries, hard cutover. SEED-010 Library milestone gated until v1.15 ships. SEED-002 / SEED-006 still dormant, gated on full benchmark ingest.

## Milestone Progress

Fourteen milestones complete (v1.0–v1.14). v1.15 opened 2026-05-02 with a single phase (78). v1.14 Score-Based Opening Insights shipped 2026-04-29 with 3 phases (75, 76, 77), 16 plans, delivered via PRs #69, #70, #71 (inline confidence-mute hotfix), #72, #73 (quick task). 73 phases total before v1.15 (+4 inserted: 27.1, 28.1, 41.1, 57.1, 71.1).

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, Google SSO, guest sessions, admin impersonation)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (4 vCPUs, 7.6 GB RAM + 2 GB swap)
- v1.11 LLM stack: pydantic-ai Agent with env-var-driven model selection (`PYDANTIC_AI_MODEL_INSIGHTS`), `genai-prices` for cost accounting, generic `llm_logs` Postgres table
- v1.12 Benchmark DB: separate PostgreSQL 18 instance on port 5433 — used by v1.15 as the first backfill target before prod; SEED-002 / SEED-006 still pending full ingest
- v1.14 score plumbing: trinomial Wald 95% half-width drives `confidence: "low" | "medium" | "high"`; `OpeningInsightFinding` and `NextMoveEntry` payloads expose `score`, `confidence`, `p_value`. `compute_confidence_bucket` is the single shared helper (CI structural assertion). `arrowColor.ts` and backend constants are kept in lock-step by `tests/services/test_opening_insights_arrow_consistency.py`.
- v1.15 inputs: `eval_cp` / `eval_mate` columns already exist on `game_positions` (white-perspective, set in `app/services/zobrist.py:170-220` from lichess `%eval`). Only ~22% of prod positions have eval today (lichess subset). Backfill targets endgame span entries only — `MIN(ply)` of each `(game_id, endgame_class)` group with `count(ply) ≥ ENDGAME_PLY_THRESHOLD`.
- v1.15 source report: `reports/conv-recov-validation-2026-05-02.md` — proxy holds at ~81.5% agreement vs Stockfish on the populated subset, but misses ~24% of substantive material-edge sequences. Queen and pawnless classes underperform structurally. ~1.5M positions × 35 ms at depth 15 ≈ 2 hours on 8 cores for the benchmark backfill.

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
- 2026-05-02: v1.15 opened — single-phase milestone (Phase 78). Source: `reports/conv-recov-validation-2026-05-02.md`. All 16 v1.15 requirements (ENG-01..03, FILL-01..04, IMP-01..02, REFAC-01..05, VAL-01..02) mapped to Phase 78. SEED-010 Library gated until v1.15 ships.
- 2026-05-02: Phase 79 added to v1.15 — position-phase classifier (opening/middlegame/endgame) via lichess Divider port plus middlegame Stockfish eval. Phase 78's operational backfill (benchmark + prod) and deploy moved to a single combined run after phase 79 ships, so one backfill pass populates both endgame and middlegame eval entries. Phase 78 stays unmerged in the meantime.

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions

### Blockers/Concerns

- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)
- Prod backfill run sequencing: benchmark first → operator validates → prod (FILL-03). Do not run prod backfill blindly.

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
| 260429-ty5 | Replace Opponent Strength ToggleGroup with dual-handle range slider + 4 preset chips (Spike 001) | 2026-04-29 | 124237b | [260429-ty5-opponent-strength-slider](./quick/260429-ty5-opponent-strength-slider/) |

---
Last activity: 2026-05-02 — Plan 78-05 (endgame refactor, eval_cp/eval_mate) complete. _classify_endgame_bucket added; three repository queries rewritten; Alembic migration c92af8282d1a created. Current plan: 2 of 6 (78-06 cutover execution is next).
