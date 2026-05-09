---
gsd_state_version: 1.0
milestone: v1.15
milestone_name: Eval-Based Endgame Classification
status: executing
last_updated: "2026-05-09T14:46:23.048Z"
last_activity: 2026-05-09 -- Phase 81 planning complete
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 15
  completed_plans: 10
  percent: 67
---

# Project State: FlawChess

## Current Position

Phase: 81
Plan: Not started
Status: Ready to execute
Last activity: 2026-05-09 -- Phase 81 planning complete
Resume file: .planning/phases/81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table/81-CONTEXT.md

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
| 260504-rvh | Remove eval color-baseline centering: MG-entry bullet chart and backend stats now anchor on 0 cp (engine-balanced); per-color baseline (+0.315 / −0.189) becomes a tick reference instead of the chart center | 2026-05-04 | e1e55bb | [260504-rvh-remove-eval-color-baseline-centering-fro](./quick/260504-rvh-remove-eval-color-baseline-centering-fro/) |
| 260504-ttq | Add current-position score-vs-50% bullet chart under "Results played as White/Black" WDL bar in Openings → Moves tab; muted when n<10 to double as a sample-size trust indicator for the WDL bar above | 2026-05-04 | 6e3cc51 | [260504-ttq-add-a-current-position-score-vs-50-bulle](./quick/260504-ttq-add-a-current-position-score-vs-50-bulle/) |
| 260504-acl | Simplify Moves-tab arrow palette from 5 effect-size buckets to 3 score zones (red <=0.45 / blue 0.45-0.55 / green >=0.55); replace HOVER_BLUE with grey for hovered arrows + row tints; update chessboard InfoPopover to describe Score = (W + 0.5·D)/N | 2026-05-04 | 9f586db | [260504-acl-simplify-arrow-color-from-5-to-3-categories](./quick/260504-acl-simplify-arrow-color-from-5-to-3-categories/) |
| 260505-uzp | Unify Moves-tab arrow + Score column + row background tint on one score-zone signal. Low-data/low-conf rows render in blue (was grey). Blue arrows fade to 0.30 opacity. Hover keeps arrow color, just amplifies size+opacity. Deep-link pulse uses grey alpha levels and lands on the row's natural score-zone tint | 2026-05-05 | 0b3da1f | [260505-uzp-unified-score-zone-palette](./quick/260505-uzp-unified-score-zone-palette/) |
| 260506-rtk | Replace Openings → Stats subtab table with two-column card grid (white left, black right) mirroring Insights tab. New OpeningStatsCard reuses Insights card shell: permanent miniboard, header, WDL chart row, eval bullet chart, Moves + Games links. Drops MostPlayedOpeningsTable and MinimapPopover (hover preview replaced by always-on miniboard) | 2026-05-06 | b08512c5 | [260506-rtk-change-openings-stats-page-layout-to-two](./quick/260506-rtk-change-openings-stats-page-layout-to-two/) |
| 260506-u2b | Align Openings Insights card with Stats card layout: replace MiniBulletChart score bullet with shared WDLChartRow, add MG-entry eval bullet row below it (mirrors OpeningStatsCard), abbreviate prose to "Score X% after <move>". Card border + on-board arrow keep score-zone tint. Backend extends OpeningInsightFinding with eval_* fields and adds per-color eval_baseline_pawns to OpeningInsightsResponse, computed via the existing query_opening_phase_entry_metrics_batch helper (no duplicated SQL) | 2026-05-06 | 37c37bb4 | [260506-u2b-align-openings-insights-card-with-stats-](./quick/260506-u2b-align-openings-insights-card-with-stats-/) |
| 260507-aw5 | Complete Wilson migration on score side: replace trinomial Wald p-value in score_confidence.py with Wilson score-test p-value (null SE = 0.5/sqrt(n)). CI bounds were already Wilson; the test is now the inversion of the CI so they agree by construction. SE=0 degeneracy at all-wins/all-losses gone. Tooltips, Field comments, and module docstrings updated. Eval-side stays on Wald-z (Wilson is binomial-specific) | 2026-05-07 | b47505be | [260507-aw5-complete-wilson-migration-on-score-side-](./quick/260507-aw5-complete-wilson-migration-on-score-side-/) |
| 260507-t4r | Add score bullet chart to Openings Stats and Insights tabs (SEED-011): WDL + Score bullet + Eval bullet 3-row layout, score-zone left border (reliability-gated), neutral light-grey bar mode opt-in on MiniBulletChart, drop "Score X% after [move]" prose (move anchor moves to caption under miniboard), unified single-column card layout on every viewport | 2026-05-07 | b816adf7 | [260507-t4r-add-score-bullet-chart-to-openings-stats](./quick/260507-t4r-add-score-bullet-chart-to-openings-stats/) |
| 260508-dcp | Neutralize non-significant zone fonts on Openings tabs (Score % and Eval only carry zone color when confidence != 'low' AND value is in red/green zone), neutralize all Openings + Endgames Stats MiniBulletChart bars, and recolor the categorical neutral board arrow from blue to transparent grey via new ARROW_NEUTRAL theme token | 2026-05-08 | 4a409726 | [260508-dcp-neutralize-non-significant-zone-fonts-us](./quick/260508-dcp-neutralize-non-significant-zone-fonts-us/) |
| 260508-f9o | Add MG-entry eval bullet chart to Openings → Moves "Results played as" section: backend extends WDLStats + OpeningsResponse with eval_* fields via existing query_opening_phase_entry_metrics_batch helper; frontend restructures section into three same-width chart rows (WDL / Score / Eval) with chart-left, indicator-right (mirrors OpeningStatsCard / OpeningFindingCard layout) | 2026-05-08 | c0b6d6dc | [260508-f9o-in-the-openings-moves-tab-section-result](./quick/260508-f9o-in-the-openings-moves-tab-section-result/) |
| 260508-q1z | Auto-load cached LLM endgame report on Endgames page mount and filter change: new GET /insights/endgame/cached cache-only endpoint (mirrors Tier-1 structural lookup, never invokes LLM, no rate-limit accounting, 200/cache_hit or 404); new useCachedEndgameInsights TanStack query hook (returns null on 404, silent); Endgames.tsx upserts result into existing insightsCache so matchingInsights renders without a Generate click. Existing POST/Generate flow unchanged | 2026-05-08 | (uncommitted) | [260508-q1z-auto-load-cached-llm-endgame-report](./quick/260508-q1z-auto-load-cached-llm-endgame-report/) |
| 260508-r61 | Score info icons and last-played in tooltips: backend threads MAX(played_at) as last_played_at through 4 score-confidence query paths (query_next_moves, query_wdl_counts, query_opening_transitions, OpeningStatsCard query) plus Pydantic schemas + services; frontend new relativeDate.ts helper, WdlConfidenceTooltip renders "Last played: X ago" line; MoveExplorer Score column gains per-row HelpCircle popover (replaces hover-only tooltip; touch-friendly via Radix popover with stopPropagation); troll/sunglasses icon converted to same popover pattern (mobile tap now shows tooltip instead of selecting row); selected-row class gets Tailwind `!` important so highlight is visible on green/red tinted rows | 2026-05-08 | c2483929 | [260508-r61-score-info-icons-and-last-played-in-tool](./quick/260508-r61-score-info-icons-and-last-played-in-tool/) |
| 260509-gm9 | Refactor top-3 bloated functions identified in code-quality scan: `compute_insights` (223 → 41 logic LOC, depth 5 → 2) extracts `_collect_attribution_hashes` / `_fetch_position_wdl_per_color` / `_build_sections` + 2 dataclasses; `_flush_batch` (171 → 59 logic LOC, depth 5 → 2) extracts `_collect_position_rows` / `_collect_midgame_eval_targets` / `_collect_endgame_span_eval_targets` / `_apply_eval_results` + 2 island helpers; `OpeningsPage` (~395 → ~316 non-JSX logic LOC, depth ~6 → ≤4) split into 4 hooks (`useDeepLinkHighlight`, `useSidebarState`, `useTabReset`, `useOpeningsHandlers`) + 4 tab subcomponents (`ExplorerTab`, `StatsTab`, `GamesTab`, `InsightsTab`) under `frontend/src/pages/openings/`. Behavior-preserving only — no API changes, no logic changes, no new tests. All 57 `data-testid` values preserved; mobile drawer + desktop sidebar parity preserved. Branch `refactor/top3-bloated-functions` (4 commits ahead of main, ready for PR). Backend ruff/ty clean, 1268 tests passed. Frontend lint/knip clean, 311 tests passed, build succeeded | 2026-05-09 | 9bc65c71 | [260509-gm9-refactor-top-3-bloated-functions-opening](./quick/260509-gm9-refactor-top-3-bloated-functions-opening/) |

---
Last activity: 2026-05-08 — Completed quick task 260508-r61: Score info icons in MoveExplorer Move list + last-played date in all WDL score tooltips. Backend (commit `14def5bd`): added MAX(played_at) as last_played_at to four query paths — query_next_moves, query_wdl_counts (parent FEN parent score on Openings stats-board, replacing the planned query_resulting_position_wdl), query_opening_transitions (insights white+black), and the OpeningStatsCard path; propagated through NextMoveEntry / WDLStats / OpeningInsightFinding Pydantic schemas, openings_service / opening_insights_service / stats_service mappers, and TS types (api.ts, insights.ts, stats.ts). Frontend (commit `c5fd7312`): new `frontend/src/lib/relativeDate.ts` (Just now / X minutes/hours/days/weeks/months/years ago, with absolute date in `title`); WdlConfidenceTooltip extended with `lastPlayedAt: string | null` prop — renders "Last played: 3 days ago" between confidence line and italic methodology block, omits when null; ScoreConfidencePopover threads the prop through to all four call sites (MoveExplorer per-move, Openings.tsx stats-board position, OpeningFindingCard, OpeningStatsCard). MoveExplorer (commit `c2483929`): replaced hover-only `<Tooltip>` on Score % with new ScoreInfo component — HelpCircle popover mirroring TranspositionInfo pattern (Radix Popover, 100ms hover delay desktop, tap toggles mobile, `e.stopPropagation()` on trigger so icon tap doesn't play the move), `data-testid="move-explorer-score-info-${move_san}"`; troll/sunglasses icon converted to same popover (fixes mobile-tap-selects-row bug); selected-row class `bg-foreground/10` → `bg-foreground/10!` (Tailwind v4 important suffix) so selection highlight beats inline score-zone tint on green/red rows. Tests added: WdlConfidenceTooltip.test.tsx, relativeDate.test.ts, MoveExplorer popover behavior tests; backend tests for last_played_at in query_next_moves and query_opening_transitions. Backend gates: ruff/ty/pytest 1268 passed / 6 skipped. Frontend gates: lint/knip clean, 311 tests passed, build clean. One out-of-scope follow-up logged in SUMMARY: synthetic OpeningWDL rows in Openings.tsx:buildBookmarkRows lack played_at because the time-series endpoint doesn't carry it; bookmark cards silently omit the line. Previously: 2026-05-08 — Completed quick task 260508-q1z: auto-load cached LLM endgame report on Endgames page mount and filter change. Backend: GET /insights/endgame/cached mirrors the Tier-1 structural cache lookup (`get_latest_successful_log_for_user` + `get_latest_completed_import_with_games_at` staleness check + `_maybe_strip_overview`), returns 200/cache_hit or 404. Never invokes `compute_findings`, never the LLM, no rate-limit accounting; non-default filters and custom opponent gaps just naturally 404 (no `_validate_full_history_filters` gate). Frontend: extracted shared `buildInsightsParams` helper from `useEndgameInsights`, added `useCachedEndgameInsights` TanStack `useQuery` hook (returns the cached response on 200, `null` on 404 silently, no retry, 5-min staleTime, no refetchOnWindowFocus). Endgames.tsx fires the hook with `appliedFilters` and upserts hits into the existing `insightsCache` so `matchingInsights` renders cached reports without a Generate click — POST/Generate path untouched. Tests: 6 backend tests (`TestCachedEndpoint` covering auth, cache_hit with `compute_findings` spy, miss, non-default filter 404, custom-gap 404, import-invalidation 404) + 2 frontend hook tests (200 returns response, 404 returns null silently). Backend `uv run pytest` 1267 passed / 6 skipped, frontend `npm test` 291 passed, ruff/ty/eslint/tsc/knip clean. Previously: 2026-05-08 — Completed quick task 260508-dcp: neutralize non-significant zone fonts on every Openings subtab (Score %/Eval text only paints red/green when confidence is `'medium'` or `'high'`, not `'low'`, AND value falls in colored zone), pass `barColor="neutral"` to the Moves "current position" bullet + all six Endgames Stats MiniBulletCharts, and recolor the categorical neutral board arrow from blue to transparent grey via new `ARROW_NEUTRAL` theme token (`#6B7280`). New `frontend/src/lib/significance.ts` exports `isConfident(confidence)` — gate keys on the categorical bucket so the underlying p-value thresholds in `scoreConfidence.ts` (currently medium <0.05, high <0.01) can move without touching call sites. `DARK_BLUE` constant kept (now re-exports `ARROW_NEUTRAL`) so all `=== DARK_BLUE` categorical equality checks keep working — name change deferred to a future quick task. Frontend pipeline green: lint, knip, build, 283 tests (one redundant artificial low-data test deleted). Commits `912aa058`, `fb8ca37a`, `4a67a901`, `4a409726`. Previously: 2026-05-07 — Completed quick task 260507-t4r: Add score bullet chart to Openings Stats and Insights tabs (SEED-011). Previously: Phase 80.1 (4/4 plans). Plan 80.1-04 closed the regression matrix: backend pytest 1254 passed / 6 skipped / 1 deselected in 16.47s, ty + ruff clean, dedicated transposition tests 16 passed in 0.30s; frontend npm test 281 passed in 1.51s, lint + knip clean, build success in 4.99s. D-09 prod sanity check (read-only via `bin/prod_db_tunnel.sh`) on 3 representative users — heavy (4: 23,225 games), light (18: 261 games), moderate (35: 1,450 games) — verdict PASS: pre 40/2/16, post 40/3/14, all within the planner's 50–200% band, no zero-flip, no recalibration warranted (D-07 honored). New `scripts/prodcheck_80_1.py` committed for future regression checks. CHANGELOG entry queued under `## [Unreleased]` → `### Changed` for v1.16 milestone close. Project-wide ruff format drift (89 files) logged in `deferred-items.md` as out-of-scope follow-up. Commits `a35514f2`, `4e4fa514`, `ab29a3d9`, `7bb10cc0`, `47fe2dc5`. Phase 80.1 ready for PR. Next: open PR for Phase 80.1, then queue Phase 81.
| 2026-05-04 | fast | Mute opening row when total games < 20; drop confidence-based muting | ✅ |
| 2026-05-04 | fast | Score zone color in Moves tab + per-move list; drop severity row tint; bump mobile games-count font size | ✅ |
