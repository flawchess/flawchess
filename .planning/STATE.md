---
gsd_state_version: 1.0
milestone: v1.15
milestone_name: Eval-Based Endgame Classification
status: executing
last_updated: "2026-05-03T18:08:32.598Z"
last_activity: 2026-05-03 -- Phase 80 execution started
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 6
  completed_plans: 0
  percent: 0
---

# Project State: FlawChess

## Current Position

Phase: 80 (opening-stats-middlegame-entry-eval-and-clock-diff-columns) — EXECUTING
Plan: 1 of 6
Status: Executing Phase 80
Last activity: 2026-05-03 -- Phase 80 execution started

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-02 for v1.15 open)
Core value: Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary on endgame performance and an auto-generated opening-strengths/weaknesses report (now score-based with low/medium/high confidence calibration).
Current focus: v1.15 cutover landing — combined Phase 78 + Phase 79 PR #78 awaits CI green + bin/deploy.sh + post-deploy UI smoke. After deploy, every game_positions row carries a `phase` SmallInteger (0=opening, 1=middlegame, 2=endgame) and the middlegame entry + endgame span-entry rows carry Stockfish eval at depth 15. v1.16 (Stockfish Eval Analyses) opens immediately after — first phase is Phase 80 (opening-stats columns: avg eval at middlegame entry ± std, t-test confidence, avg clock diff). SEED-002 / SEED-006 / SEED-010 remain orthogonal (gated on full benchmark ingest, not on v1.15).

## Milestone Progress

Fourteen milestones complete (v1.0–v1.14). v1.15 Eval-Based Endgame Classification (Phases 78 + 79) — 9 plans across both phases, all code commits landed; combined operator cutover (rounds 1-3) complete; draft PR #78 open against main awaiting deploy + post-deploy UI smoke. v1.14 Score-Based Opening Insights shipped 2026-04-29 with 3 phases (75, 76, 77), 16 plans, delivered via PRs #69, #70, #71 (inline confidence-mute hotfix), #72, #73 (quick task). 73 phases total before v1.15 (+4 inserted: 27.1, 28.1, 41.1, 57.1, 71.1); v1.15 adds 2 more (78, 79) for 75 total.

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, Google SSO, guest sessions, admin impersonation)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (4 vCPUs, 7.6 GB RAM + 2 GB swap)
- v1.11 LLM stack: pydantic-ai Agent with env-var-driven model selection (`PYDANTIC_AI_MODEL_INSIGHTS`), `genai-prices` for cost accounting, generic `llm_logs` Postgres table
- v1.12 Benchmark DB: separate PostgreSQL 18 instance on port 5433 — used by v1.15 as the first backfill target before prod; SEED-002 / SEED-006 still pending full ingest
- v1.14 score plumbing: trinomial Wald 95% half-width drives `confidence: "low" | "medium" | "high"`; `OpeningInsightFinding` and `NextMoveEntry` payloads expose `score`, `confidence`, `p_value`. `compute_confidence_bucket` is the single shared helper (CI structural assertion). `arrowColor.ts` and backend constants are kept in lock-step by `tests/services/test_opening_insights_arrow_consistency.py`.
- v1.15 outputs (post-cutover, on benchmark + prod): every `game_positions` row carries a `phase` SmallInteger (0=opening, 1=middlegame, 2=endgame) computed from existing `piece_count` + `backrank_sparse` + `mixedness` via Python port of lichess Divider.scala. Endgame span-entry rows (`MIN(ply)` per `(game_id, endgame_class)` with `count(ply) ≥ ENDGAME_PLY_THRESHOLD`) and middlegame entry rows (`MIN(ply)` per game where `phase = 1`) carry Stockfish eval at depth 15 in `eval_cp` / `eval_mate`. Endgame classification thresholds directly on eval (±100 cp, color-flipped to user perspective) — proxy code path removed entirely.
- v1.15 source report: `reports/conv-recov-validation-2026-05-02.md` (historical baseline that motivated the cutover — proxy held at ~81.5% agreement vs Stockfish, missed ~24% of substantive material-edge sequences). Post-cutover comparison is moot: proxy is gone (REFAC-05), so `/conv-recov-validation` Skill was deleted on 2026-05-03 and PHASE-VAL-01 / VAL-01 marked rescinded.
- v1.15 deployed code: `app/services/engine.py` (async Stockfish wrapper, lifespan-managed); `scripts/backfill_eval.py` (idempotent + resumable backfill driver, parallelised via `EnginePool` per quick-task `260503-0t8`); `_classify_endgame_bucket(eval_cp, eval_mate, user_color)` in endgame service; alembic heads `1efcc66a7695` (phase column) + `c92af8282d1a` (ix_gp_user_endgame_game reshape).

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
- 2026-05-03: Phase 80 added to v1.15 — first downstream consumer of Phase 79 data. Adds three columns to Openings → Stats subtab tables (bookmarked + most-played): avg eval at middlegame entry ± std (user-perspective), one-sample t-test confidence (low/medium/high, 10-game minimum threshold reused from opening insights), and avg clock diff at middlegame entry (mirrors endgame-entry pattern). Depends on Phase 79 backfill landing on prod. Source brainstorm: `.planning/notes/phase-aware-analytics-ideas.md`.
- 2026-05-03: Phase 80 moved out of v1.15 into a new milestone **v1.16 Stockfish Eval Analyses** (planned, multi-phase). Rationale: keep v1.15 focused on the eval-based endgame classification cutover (78+79 backfill+deploy), and bundle downstream consumers of the new Stockfish evals (endgame span-entry + middlegame-entry `eval_cp`/`eval_mate`) into a dedicated milestone so v1.15 can ship as soon as the cutover is verified. v1.16 entry criterion: v1.15 shipped (Phase 79 backfill landed on prod). Phase 80 is the first slot; further phases will be added from `.planning/notes/phase-aware-analytics-ideas.md` and other brainstorms.
- 2026-05-03: v1.15 cutover (Phases 78 + 79) — combined operator cutover ran rounds 1 (dev DB smoke, user 28), 2 (benchmark DB full backfill — phase column UPDATE pass + endgame span-entry eval pass + middlegame entry eval pass; PHASE-INV-01 = 0), 3 (prod DB full backfill via SSH tunnel; PHASE-INV-01 = 0). Draft PR #78 opened against main (40+ commits, +7093 / −2176, 54 files). PHASE-VAL-01 / VAL-01 rescinded as moot — proxy removed in Phase 78 REFAC, so the proxy-vs-Stockfish agreement metric is undefined; `/conv-recov-validation` Skill deleted from `~/.claude/skills/`. PHASE-VAL-02 (operational sanity that backfill populated rows correctly) satisfied by PHASE-INV-01 = 0. Remaining: bin/deploy.sh on the merge, post-deploy UI smoke (VAL-02 / VAL-03) on 3-5 representative test users.
- 2026-05-03: B-1 ordering deviation — prod backfill (Round 3) ran before the combined PR + bin/deploy.sh, against the 79-04-PLAN sequence. Operator confirmed "already handled, no action" via /gsd-progress dispatcher. Mitigation specifics (paused traffic / delta backfill / minimal window) not documented in 79-04-SUMMARY (TBD on milestone retro).

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions

### Blockers/Concerns

- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)
- Prod backfill sequencing concern (FILL-03) is closed for v1.15 — prod backfill ran post-benchmark on 2026-05-03. For future eval-style backfills, keep the benchmark-first → operator-validates → prod ordering as the default.
- v1.15 deploy outstanding — until `bin/deploy.sh` lands the combined PR #78, prod has the new alembic heads (1efcc66a7695, c92af8282d1a) applied (manually during Round 3) but is still running pre-cutover code. Any prod-side schema-aware code change before deploy should account for this temporary mismatch.

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
| 260503-0t8 | Speed up scripts/backfill_eval.py with parallel Stockfish EnginePool, batched UPDATE, and group-by-game PGN parsing (--workers N, default 1) | 2026-05-03 | d1346b4 | [260503-0t8-speed-up-scripts-backfill-eval-py-with-p](./quick/260503-0t8-speed-up-scripts-backfill-eval-py-with-p/) |
| 260503-fef | Add equal-footing opponent filter (abs(opp - user) <= 100) to /benchmarks SKILL §2/§3/§6 + capture framing decision in note (gsd-fast, no quick/ dir) | 2026-05-03 | 6773475 | n/a |
| 260504-my2 | Center opening-stats eval bullet chart on color-specific baseline; recalibrate engine-asymmetry baselines from medians (28/-20) to per-game means (31.5/-18.9) | 2026-05-04 | 147b883 | [260504-my2-eval-bullet-chart-baseline-centering-and](./quick/260504-my2-eval-bullet-chart-baseline-centering-and/) |

---
Last activity: 2026-05-04 — Completed quick task 260504-my2: eval bullet chart baseline-centering and per-game-mean recalibration (chart now centers on color-specific baseline, white +0.32 / black -0.19 / mixed 0; neutral zone widened to ±0.25 pawns; baselines recalibrated to per-game means per the 2026-05-04 Lichess benchmark).
| 2026-05-04 | fast | Mute opening row when total games < 20; drop confidence-based muting | ✅ |
