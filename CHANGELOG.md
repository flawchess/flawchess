# Changelog

All notable changes to FlawChess are documented here.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with releases aligned to GSD milestones rather than individual phases. Dates are
in `YYYY-MM-DD` (Europe/Zurich).

## [Unreleased]

### Added
- Phase 79: Per-position `phase` column on `game_positions` (`0=opening`, `1=middlegame`, `2=endgame`) computed via a Python port of [lichess `Divider.scala`](https://github.com/lichess-org/scalachess/blob/master/core/src/main/scala/Divider.scala) using existing `piece_count`, `backrank_sparse`, and `mixedness` inputs (no second board scan). Populated on every new import and backfilled across benchmark + prod.
- Phase 79: Middlegame entry position (`MIN(ply)` of `phase = 1` per game) is now Stockfish-evaluated at depth 15 alongside endgame span-entry positions, populated into the existing `eval_cp` / `eval_mate` columns. Substrate for v1.16 opening-stats analyses.
- Phase 78: Pinned Stockfish sf_17 AVX2 binary in the backend Docker image (SHA-256 `6c9aaaf4...341cdde`); CI installs `stockfish` via apt so engine wrapper tests run. `STOCKFISH_PATH` env var threaded end-to-end.
- Phase 78: `app/services/engine.py` — async-friendly Stockfish wrapper with FastAPI lifespan integration (`start_engine` / `stop_engine`, idempotent, depth-15 `evaluate()` API).
- Phase 78: `scripts/backfill_eval.py` — idempotent + resumable backfill driver (skip-where-NULL, COMMIT-every-100, `--db dev/benchmark/prod`, `--user-id`, `--limit`, `--dry-run`, `--workers N` for parallel evaluation, `--timeout` per-eval override).

### Changed
- Phase 78: Endgame Conversion / Parity / Recovery classification migrated from the material-imbalance + 4-ply persistence proxy to direct Stockfish-eval thresholding (±100 cp on `eval_cp`, color-flipped to user perspective; `eval_mate` short-circuits to ±1 000 000 cp). Hard cutover, proxy code path removed entirely. Closes the structural gap on Queen and pawnless classes where the proxy underperformed (~24% miss rate on substantive material-edge sequences per the 2026-05-02 baseline).
- Phase 78: New game imports populate `eval_cp` / `eval_mate` on per-class span-entry rows during the import pass (post-`bulk_insert_positions`, same transaction). Adds well under 1 s to the typical-game import path. Existing lichess `%eval` annotations preserved, never overwritten.
- Phase 78: `_classify_endgame_bucket(eval_cp, eval_mate, user_color)` is now the single helper for endgame conv/parity/recov classification. SQL projects raw white-perspective eval; service layer applies the user-color sign flip.
- Phase 78: Alembic `c92af8282d1a` reshapes `ix_gp_user_endgame_game INCLUDE` from `material_imbalance` to `eval_cp` / `eval_mate` so rewritten endgame queries stay index-only.
- Quick task 260501-s0u: Clock-pressure neutral band tightened from ±10pp to ±5pp based on pooled benchmark data (reports/benchmarks-2026-05-01.md).
- Quick task 260501-s0u: Recovery gauge typical band widened from [25%, 35%] to [25%, 40%] across all endgame classes based on pooled p25/p75 from benchmark data.
- Quick task 260501-s0u: Endgame type breakdown replaces grouped WDL bar chart with six per-class Conversion/Recovery mini-gauge cards, each using class-specific typical bands sourced from benchmark data (Queen Conversion ~78%, Minor Piece Recovery ~36%, etc.).
- Quick task 260501-s0u: LLM endgame insights prompt (v18) reframes Conversion/Recovery narration as delta-from-class-baseline rather than absolute percentages, so observations like "65% Conversion" are contextualised against the class-specific typical midpoint.
- Quick task 260503: Endgame gauge typical bands recalibrated from the 2026-05-03 benchmark report (recovery upper bound 0.40 → 0.36, endgame_skill 0.45 → 0.47 lower bound, per-class rook + pawn recovery and pawn conversion bands tightened in lockstep).
- Quick task 260503-fef: `/benchmarks` skill §2/§3/§6 now apply an equal-footing opponent filter (`abs(opp_rating - user_rating) ≤ 100`) so population baselines reflect peer-vs-peer matchups rather than mixed-strength noise.
- Quick task 260503-0t8: `scripts/backfill_eval.py` parallelised via a new `EnginePool` (`--workers N`), batched UPDATE writes, and group-by-game PGN parsing.
- Quick task 260503-pool: Import-time eval pass parallelised. The module-level engine now wraps an `EnginePool` of `STOCKFISH_POOL_SIZE` workers (default 1, prod ships 2 via `docker-compose.yml`) and `app/services/import_service.py` collects eval targets across an import batch and fans them out via `asyncio.gather`. Sequential `await` callers see no change; parallel callers gain ~`POOL_SIZE`× throughput. Behaviour preserved: lichess `%eval` precedence, bounded Sentry context, same UPDATE shape per row.

### Removed
- Phase 78: `_MATERIAL_ADVANTAGE_THRESHOLD`, `PERSISTENCE_PLIES`, and the `array_agg(... ORDER BY ply)[PERSISTENCE_PLIES + 1]` contiguity case-expression — no proxy-classification path remains in the codebase. `material_imbalance` column retained on `game_positions` for other consumers (e.g. `tests/test_aggregation_sanity.py`).
- Quick task 260501-s0u: Win Rate by Endgame Type timeline chart removed from the Endgame page.

### Tests
- Phase 78: TDD coverage for `app/services/engine.py` (idempotent start/stop, restart-failure swallow, evaluate-without-start contract); for `scripts/backfill_eval.py` (idempotency, dry-run, resume); for the import-time eval pass (`tests/services/test_import_service_eval.py`).
- Phase 79: 11 Divider-sourced parity assertions in `tests/test_position_classifier.py` (matches lichess `Divider.scala` output on a curated FEN fixture set); Wave-0 RED/GREEN tests for `PlyData.phase` (`tests/test_zobrist.py`) and bulk-insert phase writes (`tests/test_import_service.py`).

## [v1.14] Score-Based Opening Insights — 2026-04-29

Replaces the loss/win-rate framing of v1.13 with a calibrated discovery surface
built on chess score `(W + 0.5·D)/N`. Effect size decides what shows up,
confidence annotates how sure we are. Trinomial Wald 95% half-width drives a
low/medium/high confidence badge surfaced on Insights cards and Move Explorer
moves-list rows. `MIN_GAMES_PER_CANDIDATE` drops 20 → 10 — the badge calibrates
trust where the hard floor used to gate. Phase 77 adds a frontend-only
troll-opening watermark on Insights cards and Move Explorer rows. INSIGHT-UI-04
(soften titles per SEED-008) descoped on close: severity word never appeared
as user-facing text; confidence badge + sort calibration deliver SEED-008's
intent without rewriting "Weakness/Strength" titles.

### Added
- Phase 75: Trinomial Wald 95% confidence interval per opening insight finding using the actual variance of the chess result distribution `X ∈ {0, 0.5, 1}` — variance `(W + 0.25·D)/N − score²`, not the binomial-Wilson approximation. Pure-Python `math` only, no scipy. Half-width buckets `≤ 0.10 → high`, `≤ 0.20 → medium`, else `low`.
- Phase 75: `OpeningInsightFinding` API contract extended with `confidence: "low" | "medium" | "high"` and `p_value: float` (two-sided Z-test of observed score vs 0.50, tooltip-grade significance). `severity` retained.
- Phase 76: Move Explorer "Conf" column showing low / med / high confidence per move so you can tell how well-sampled each next-move statistic is.
- Phase 76: `NextMoveEntry` API contract extended with `score`, `confidence`, and `p_value` for moves-list parity with Insights findings.
- Phase 76: Opening Insights cards each show a "Confidence: low / medium / high" line with a hover tooltip explaining how to read it.
- Phase 76: Opening Insights section titles each gain a small `?` icon that opens a popover explaining score, the 5%-from-pivot effect-size gate, and what confidence means.
- Phase 77: Troll-opening watermark — `troll-face.svg` renders as a 30%-opacity bottom-right watermark on Opening Insights cards (mobile + desktop) and a small inline icon next to qualifying SAN rows in Move Explorer (desktop only). Pure visual easter egg; matching is frontend-only via a side-only FEN piece-placement key — no backend schema, no API contract change.

### Changed
- Phase 75: Opening insight classification migrated from loss/win rate to chess score `(W + 0.5·D)/N`. Effect-size gate against a 0.50 pivot with strict `≤`/`≥` boundaries — minor at `score ≤ 0.45` / `≥ 0.55`, major at `≤ 0.40` / `≥ 0.60`. Symmetric on weakness and strength sides, eliminating the prior `loss_rate > 0.55` asymmetry.
- Phase 75: `MIN_GAMES_PER_CANDIDATE` dropped 20 → 10 to enable discovery framing — confidence badge replaces hard-floor gate.
- Phase 76: Move Explorer arrows and row tints now reflect chess score `(W + 0.5·D)/N` rather than separate win/loss rates. Color encoding stays effect-size only — arrows show how far from a 50% break-even your performance sits.
- Phase 76: Opening Insights card prose reframed from "You lose / win X%" to "You score X% as &lt;color&gt; after &lt;move&gt;" — same form for both weakness and strength sections.
- Phase 76: Opening Insights cards within each section now sort by confidence first, then by distance from 50% — high-confidence findings rise to the top.
- Phase 76: Low-confidence (or low-game-count) Move Explorer rows and Opening Insights cards are visually muted at 50% opacity to flag treat-as-a-hint findings without hiding them.
- Quick task 260428-v9i: Opening Insights ranking now uses the Wilson 95% score interval bound instead of Wald. Fixes degeneracy at boundary scores (Wald upper bound for 0/11 was 0.000; Wilson is ~0.259) and demotes small-N extreme findings in favor of large-N moderate findings within each section. Backend constant `OPENING_INSIGHTS_WALD_Z_95` renamed to `OPENING_INSIGHTS_CI_Z_95` (value unchanged at 1.96). The trinomial Wald p-value in `score_confidence.py` (separate procedure for the confidence badge) is unchanged.
- PR #71 (post-Phase-76 inline hotfix): Move Explorer arrows for low-confidence moves are forced grey and the row tint is skipped — board reads cleaner; low-confidence findings still surface in the table with the badge but don't visually claim authority on the board.
- Quick task 260429-gmj (PR #73): Opening Insights cards now render an arrow on the mini board showing the after-move position rather than the entry position — clearer at-a-glance read of which candidate move the finding is about.

### Fixed
- Phase 76: Opening Insights cards no longer break when the backend stops returning the (now removed) `loss_rate` / `win_rate` fields — cards read `score` directly per the Phase 75 contract.

### Removed
- Phase 75: `loss_rate` and `win_rate` fields removed from the `OpeningInsightFinding` API payload. Score is the canonical metric; raw `w / d / l / n_games` remain as the literal-data display.

### Tests
- Phase 75: CI consistency test `tests/services/test_opening_insights_arrow_consistency.py` rewritten to assert score-based threshold lock-step between backend classification and `frontend/src/lib/arrowColor.ts`.
- Phase 76: CI structural assertion ensures `compute_confidence_bucket` has only one implementation across the codebase. `arrowColor.ts` boundary tests cover all six effect-size regions; `OpeningFindingCard` tests cover confidence indicator + tooltip + opacity mute; `OpeningInsightsBlock` tests cover the four `InfoPopover` triggers.
- Phase 77: 9 new test cases under `OpeningFindingCard.test.tsx` (`describe('Phase 77 — Troll-opening watermark')`) asserting watermark gating per CONTEXT.md decisions D-02..D-05; Move Explorer inline-icon tests under `MoveExplorer.test.tsx`.

## [v1.13] Opening Insights — 2026-04-27

First user-facing analytics layer for openings. Each user gets a curated list of
their opening weaknesses (loss rate > 55%) and strengths (win rate > 55%) with
deep-links into the Move Explorer pre-positioned at the implicated entry FEN
and the candidate move highlighted. Pure templated/rule-based; LLM narration
is deliberately deferred. v1.13 also restructures the Openings page subnav to
match the Endgames pattern. Phases 72 (inline bullets on Moves), 73
(meta-recommendation, stretch), and 74 (bookmark-card weakness badge, stretch)
were descoped on close after the live UI showed Phases 70 + 71 + 71.1 already
delivered the actionable signal.

### Added
- Phase 70: `POST /api/insights/openings` returning `OpeningInsightFinding[]`. Single SQL transition aggregation per (user, color) over `game_positions` for entry plies in `[3, 16]`, `MIN_GAMES_PER_CANDIDATE = 20` evidence floor enforced at SQL HAVING level, strict `>` 0.55 win/loss boundary classifying weakness / strength, severity tier major (`>= 0.60`) / minor in `(0.55, 0.60)`. Two-pass attribution (direct hash lookup plus parent-prefix walk via `ctypes.c_int64`-converted polyglot Zobrist hashes) drops findings that match neither rather than surfacing `<unnamed line>` placeholders. Findings are deduplicated by entry hash with deepest-opening attribution and ranked by `(severity desc, n_games desc)` capped at 5 weaknesses + 3 strengths per color.
- Phase 70: Alembic migration `80e22b38993a_add_gp_user_game_ply_index` — partial composite covering index `ix_gp_user_game_ply (user_id, game_id, ply) INCLUDE (full_hash, move_san) WHERE ply BETWEEN 1 AND 17`. First project use of `postgresql_concurrently=True` + `autocommit_block`. Keeps the LAG-window scan an Index Only Scan with Heap Fetches: 0 at ~9% of `game_positions` size.
- Phase 71: `OpeningInsightsBlock` component on Openings → Stats subtab — charcoal-texture card with four-state rendering (loading skeleton, error, empty block with threshold copy, populated four-section grid: white weaknesses, black weaknesses, white strengths, black strengths).
- Phase 71: `OpeningFindingCard` per-finding card with severity-accented border (DARK_RED / LIGHT_RED / DARK_GREEN / LIGHT_GREEN from `frontend/src/lib/arrowColor.ts`), dual mobile/desktop layout, opening name + ECO + entry SAN sequence prose, and explicit "Moves" + "Games" deep-links.
- Phase 71: `LazyMiniBoard` shared module extracted from the inline `GameCard` definition into `frontend/src/components/board/LazyMiniBoard.tsx` for reuse by `OpeningFindingCard` and future insight surfaces. IntersectionObserver lazy render preserved byte-for-byte.
- Phase 71: `useOpeningInsights` TanStack Query hook + `frontend/src/lib/openingInsights.ts` helpers (`trimMoveSequence`, `getSeverityBorderColor`, threshold copy constants).
- Phase 71: Deep-link wiring in `Openings.tsx` — clicking the Moves link replays `entry_san_sequence` through `chess.loadMoves()`, flips the board if the finding is for the black side, applies the matching color filter with `matchSide: 'both'`, navigates to Openings → Move Explorer, and scrolls to top.
- Phase 71.1: Openings page subnav restructured to match the Endgames pattern. Desktop: `<Tabs>` now wraps `<SidebarLayout>` with `<TabsList>` spanning the full board column + main content above. Mobile: sticky 4-tab subnav with an icon-only filter button on the right edge; the chevron-fold collapsible board is gone; the board, controls, and moves field are non-sticky on Moves + Games and hidden entirely on Stats + Insights. Subtab switching resets scroll to top on both viewports.
- Phase 71.1: Notification dot on the Openings tab gated behind first-import state (lights up after first game import completes); Endgames-tab dot similarly gated. Non-Import tabs lock until first game import completes.
- Tests: `tests/services/test_opening_insights_service.py` covers classification boundaries, evidence floor, deduplication, attribution (direct and parent-prefix), ranking formula, caps per color, color-optimization short-circuits, and bookmarks-not-consumed regression. `tests/services/test_opening_insights_arrow_consistency.py` enforces backend/frontend threshold lock-step via a CI gate. Plus `tests/repositories/test_opening_insights_repository.py` and `tests/routers/test_insights_openings.py`.

### Changed
- "Most Played Openings as White/Black" info popovers describe position-based counting, the 3-half-move minimum, and the `vs.` prefix introduced by PRE-01.
- Endgames repository: replaced fragile self-joins with `array_agg` aggregation for endgame-class series queries, prepping the analytics layer for further per-class breakdowns.
- Backend: opening-insights algorithm reframed mid-Phase-70 from a top-10-most-played × per-position next-moves scan to a single first-principles SQL transition aggregation over `game_positions` for entry plies in `[3, 16]` with `n_games >= 20` evidence floor. Classifier `score = (W + D/2)/n >= 0.55` replaced by separate `loss_rate > 0.55` (weakness) / `win_rate > 0.55` (strength) thresholds aligned with `frontend/src/lib/arrowColor.ts`. Bookmarks no longer consumed by the discovery algorithm.

### Fixed
- PRE-01: Top-10 most-played openings now include opponent-defined openings (e.g. `vs. Caro-Kann Defense: Hillbilly Attack` for a Black user) which were previously hidden by a ply-parity filter. Off-color rows render with a `vs. ` prefix; same-color rows are unchanged. 1599 of 3301 white-defined ECO openings were previously invisible in the black top-10 (and vice versa).
- PRE-01 follow-up: Top-10 most-played openings now rank by position-based game count (games passing through the named position, including games that continued into deeper variations), matching the count displayed in the UI. `MIN_PLY_WHITE` and `MIN_PLY_BLACK` raised from 1/2 to 3/3 so trivial trunks like `1.d4` and `1.e4` don't dominate the new ranking.
- Opening insights `IllegalMoveError` when `entry_san_sequence` does not start from the initial position (#71 hotfix). Quick task `260427-g4a`.
- Mobile: Moves/Games links beside the mini board in `OpeningFindingCard` (whole-card target reverted to explicit links). Quick task `260427-h3u`.
- Move Explorer: candidate row carries a sticky severity-colored border and one-shot pulsating arrow when arriving from an Insights deep-link; highlight clears on position or filter change. Quick task `260427-j41`.

### Removed
- Database: dropped the redundant `ix_gp_user_full_hash` and the unused `ix_gp_user_endgame_class` indexes.
- Frontend: chevron-fold collapsible board state on Openings mobile (`boardCollapsed`, `setBoardCollapsed`, `touchStartY`, `handleHandleTouchStart`, `handleHandleTouchEnd`, `MIN_SWIPE_DISTANCE`) removed entirely along with the associated swipe-handler logic.

## [v1.12] Benchmark DB Infrastructure & Ingestion Pipeline — 2026-04-26

Developer-facing infrastructure milestone with no user-visible changes. Ships the
groundwork for SEED-006 (population-based zone recalibration): a separate
`flawchess-benchmark` PostgreSQL 18 instance, a third read-only MCP server, and a
resumable Lichess monthly-dump ingestion pipeline that subsamples players
stratified on (rating × time_control). v1.12 was scoped down from the original
five-phase plan to Phase 69 only — the multi-day full ingest is operational, not
a milestone gate, and the analytics phases (classifier validation, Parity
proxy validation, zone recalibration, `/benchmarks` skill upgrade) move to a
future SEED-006 milestone once the populated DB is ready.

### Added
- Phase 69: Isolated `flawchess-benchmark` PostgreSQL 18 container on `localhost:5433`
  via `docker-compose.benchmark.yml`, with `bin/benchmark_db.sh start/stop/reset`
  lifecycle wrapper. Same Alembic migration chain as dev/prod/test (no
  benchmark-only schema additions on canonical tables). Read-only role
  `flawchess_benchmark_ro` (SELECT-only, with `ALTER DEFAULT PRIVILEGES` for future tables).
- Phase 69: Third MCP server `flawchess-benchmark-db` (read-only, queryable via
  `mcp__flawchess-benchmark-db__query`) documented in CLAUDE.md §Database Access.
  RO password lives in user-level `~/.claude.json` only; committed
  `deploy/init-benchmark-db.sql` keeps a `<PASSWORD>` placeholder.
- Phase 69: `scripts/select_benchmark_users.py` — streaming Lichess monthly-dump
  scan (zstandard) that buckets players by median Elo and modal time control,
  then persists a stratified selection into `benchmark_selected_users`.
- Phase 69: `scripts/import_benchmark_users.py` — SIGINT-safe orchestrator that
  re-uses the production import pipeline against synthetic stub users and
  `import_jobs` rows, with checkpoint resume tracked in
  `benchmark_ingest_checkpoints` (terminal-status idempotency).
- Phase 69: `BenchmarkSelectedUser` and `BenchmarkIngestCheckpoint` ORM models
  (benchmark-DB only, isolated from canonical schema).
- Phase 69: `zstandard>=0.22` added to dev dependency group for streaming
  decompression of Lichess monthly dumps.
- Phase 69: Smoke-test verification report at
  `reports/benchmark-db-phase69-verification-2026-04-26.md` (20-cell selection
  ≈ 8.6k players, ~274k games, ~19.4M positions; pipeline correctness verified
  in lieu of multi-day full ingest).

### Tests
- Phase 69: `tests/test_benchmark_ingest.py` — Wave-0 unit tests covering
  centipawn convention, (Elo × TC) bucketing including boundaries, dump-scan PGN
  parser, and ingest-orchestrator scaffolding.

## [v1.11] LLM-first Endgame Insights — 2026-04-24

First LLM-backed feature. On-demand Endgame Insights via `POST /api/insights/endgame`,
backed by a deterministic findings pipeline, a generic `llm_logs` Postgres table,
and a dual-line Endgame vs Non-Endgame Score timeline chart. Phase 67
(Validation & Beta Rollout) was descoped — insights shipped to all users rather
than behind a beta cohort flag.

### Added
- LLM-backed endgame insights endpoint (`POST /api/insights/endgame`) returning a structured `EndgameInsightsReport` (overview + up to 4 section insights). Cached on a findings hash, rate-limited to 3 misses/hr/user, soft-fails to the last cached report (Phase 65).
- Phase 63: Findings pipeline foundation for LLM Endgame Insights — deterministic `compute_findings` service produces per-subsection-per-window `EndgameTabFindings` with zone, trend, and sample-quality annotations over the existing `/api/endgames/overview` data
- Phase 63: Shared zone registry (`app/services/endgame_zones.py`) as the single source of truth for thresholds and the 3-zone schema (weak/typical/strong) that backs both narrative and chart visuals
- Phase 63: Python→TypeScript zone codegen (`scripts/gen_endgame_zones_ts.py`) with CI drift guard so frontend gauge constants can never silently diverge from the Python registry
- Phase 64: Generic `llm_logs` Postgres table (18 columns, BigInteger PK, JSONB for filter_context/flags/response_json, FK CASCADE to users) with 5 indexes, designed to host every future LLM feature (not endgame-specific)
- Phase 64: Async `LlmLogRepository.create_llm_log` that opens its own session scope, so log rows persist even when the caller's request-scoped transaction rolls back; `get_latest_log_by_hash` stub ready for Phase 65's findings-hash cache
- Phase 64: Automatic per-call cost accounting via `genai-prices` with `LookupError` soft-fallback (`cost_usd=0`, `error=cost_unknown:<model>`) so unknown models never break logging

### Changed
- `SubsectionFinding` gains optional `series: list[TimePoint] | None` for the four timeline subsections, populated with weekly (last_3mo) or monthly weighted-mean (all_time) resampled points (Phase 65).
- Phase 63: Recovery gauge typical band re-centered to 0.25–0.35 per D-10 (previously 0.3–0.4)
- Endgame insights prompt bumped to `endgame_v6`: rate/percent metrics rendered on the 0-100 scale end-to-end so narration matches the page (no more `0.65` prose next to `65%` charts); pawnless findings filtered from the LLM payload to match the hidden UI row; system prompt rewritten with a UI-vocabulary block, a `win_rate`-citation ban, and rules for staleness, latest-bucket anchoring, activity-gap narration, intra-type asymmetry hunting, grounding checks, and within-noise delta handling.
- Endgame insights payload now ships precomputed signals so the LLM stops redoing math: `## Payload summary` header, `STALE:` markers on series trailing >6mo behind the newest bucket, `# trend:` direction tags under every series, `# asymmetry` flags on opposing-zone Conversion/Recovery pairs per endgame type, `# low-time gap` scalar on the time-pressure chart, `# delta` annotations for paired all_time↔last_3mo scalars with a `within-noise` flag on small-sample shifts.
- Endgame insights prompt bumped to `endgame_v7`: all rate/percent values rendered as whole-number `%` in both prompt and UI (drops the confusing `pp` unit); `net_timeout_rate` switched to `higher_is_better` with no internal sign flip (positive raw = strong, matching the UI's coloring); the within-noise rule promoted to a global constraint that binds the overview paragraph text as well as bullets; new precomputed tags (`# weakest type`, `# recovery pattern`, `[near edge]` proximity hints inline on bullets); flat-trend series collapsed to a single stable-around line; stale `endgame_elo_gap` combo series blocks dropped when a live combo exists; redundant `last_3mo` scalar bullets dropped when the delta is within-noise; prompt intensifier forbidden list expanded to block "severe"/"critical"/"drastic"-style overclaims; system prompt redundancy trimmed and Series-interpretation rules consolidated.
- Endgame insights prompt bumped to `endgame_v9`: `EndgameInsightsReport` gains first-class `player_profile` (paragraph) and `recommendations` (2-4 short bullets) fields, surfaced as stacked top-of-page cards above the data-analysis overview; recommendations are allowed to be more directive than the overview but stay grounded in weak/typical-zone metrics with a register calibrated to the most-played combo's Elo (theory jargon ≥1200, named positions ≥1800). The `score_gap` scalar bug is fixed: the misleading `score_gap (all_time)` bullet inside `score_gap_timeline` (which was actually the latest weekly-bucket value mislabeled as an aggregate) is dropped, and the `## Subsection: overall` scalar always emits alongside the `overall_wdl` chart so the all-time number matches the chart row math. Payload format cleaned up: dropped the always-on `Filters:` header (only `## Scoping caveat` remains, when opponent_strength is set) and the redundant `Conversion/Recovery asymmetries detected: N` count.
- Endgame page: "Time Pressure at Endgame Entry" table and mobile cards gain a weighted "All time controls" aggregate row when multiple time controls are present, mirroring the weighted mean the LLM narrates so users can reconcile the written summary with the visible data.
- Phase 68: Endgame tab now shows a dual-line "Endgame vs Non-Endgame Score over Time" chart (both absolute Score series, with a shaded band between them, green when endgame leads, red when it trails) in place of the old single-line "Score Gap over Time" chart. The backend subsection was renamed from `score_gap_timeline` to `score_timeline` and now emits three findings per window — one each for `endgame_score`, `non_endgame_score`, and `score_gap` — each with its own `[summary …]` + `[series …]` block (deterministic order: endgame_score, non_endgame_score, score_gap). Prompt bumped to `endgame_v14`, dropping the now-redundant `score_gap` framing rule (the two-line chart makes gap composition self-evident) and introducing a `[n=<N> for every point]` disclosure that replaces per-point `(n=<N>)` suffixes when N is constant across a series. The info popover drops the "Score Gap is a comparison, not an absolute measure" caveat.
- v1.11 cleanup pass: `endgame_v15` prompt bump drops the stale `Filters:` header reference from the `avg_clock_diff_pct` glossary entry (the header itself was removed in v9). Zone-threshold consolidation finishes the Phase 66 switchover — three chart components now import numeric zone boundaries from `frontend/src/generated/endgameZones.ts` (codegen'd from `app/services/endgame_zones.py`) instead of maintaining inline duplicates; gauge band colors moved to `frontend/src/lib/theme.ts`.

## [v1.10] Advanced Analytics — 2026-04-19

Endgame-focused advanced analytics pass: score gaps, material breakdowns,
time-pressure analysis, skill-adjusted Endgame ELO, plus test hardening and
admin impersonation.

### Added

- Endgame Score Gap & Material Breakdown — signed endgame vs non-endgame score
  difference plus material-stratified WDL table (Conversion / Parity / Recovery)
  with Good / OK / Bad verdict calibration (Phases 53, 59).
- Opponent-based self-calibrating baseline for Conv / Parity / Recov bullet
  charts — opponent's rate against the user replaces global average, muted when
  sample < 10 games (Phase 60).
- Time pressure analytics — per-time-control clock stats table (Phase 54) and
  two-line user-vs-opponents score chart across 10 time-remaining buckets with
  backend aggregation (Phase 55).
- Endgame ELO Timeline — skill-adjusted rating per (platform, time-control)
  combination with paired Endgame ELO / Actual ELO lines, asof-join anchor on
  user's real rating, weekly volume bars for data-weight transparency (Phases
  57, 57.1).
- Admin user impersonation — superusers can impersonate any user via new
  `/admin` page with shadcn Command+Popover search, single `auth_backend` +
  `ClaimAwareJWTStrategy` wrapper (zero call-site changes), last_login /
  last_activity frozen during impersonation, persistent impersonation pill in
  header (Phase 62).

### Changed

- Endgame tab performance — 8 per-class timeline queries collapsed into 2,
  consolidated `/api/endgames/overview` serving every endgame chart in one
  round trip on a single `AsyncSession`, deferred filter apply on desktop
  (Phase 52).
- Conversion / recovery persistence filter — material imbalance required at
  endgame entry AND 4 plies later, threshold lowered 300cp → 100cp, validated
  against Stockfish eval analysis (Phase 48).
- Sentry Error Test moved from Global Stats to Admin tab; superuser-gated nav
  entry.

### Tests

- Test suite hardening — `flawchess_test` TRUNCATE on session start,
  deterministic 15-game `seeded_user` fixture, aggregation sanity tests (WDL
  perspective, material tally, rolling windows, filter intersections, recency
  boundaries, within-game dedup, endgame transitions), router integration tests
  asserting exact integer counts (Phase 61).

## [v1.9] UI/UX Restructuring — 2026-04-10

Responsive sidebar restructuring for Openings, mobile control-row alignment,
Stats subtab redesign, and a global Stats → Global Stats rename with opponent
filters wired end-to-end.

### Added

- Openings desktop sidebar — collapsible left-edge 48px icon strip + 280px
  on-demand Filters / Bookmarks panel with overlay / push behavior at the
  1280px breakpoint, live filter apply on desktop.
- Openings mobile unified control row — Tabs | Color | Bookmark | Filter
  lifted outside the board collapse region so controls stay visible when the
  board is collapsed; 44px tappable collapse handle; backdrop-blur translucent
  sticky surface.
- Global Stats filters — `opponent_type` and `opponent_strength` wired
  end-to-end through `/stats/global` and `/stats/rating-history`, bot games
  excluded by default.

### Changed

- Endgames mobile visual alignment — 44px backdrop-blur sticky row with 44px
  filter button matching the Openings mobile pattern.
- Stats subtab layout — 2-column Bookmarked Openings: Results on desktop (lg
  breakpoint), stacked WDLChartRows for mobile Most Played replacing the
  cramped 3-col table.
- Homepage 2-column desktop hero — left = hero content, right = Interactive
  Opening Explorer preview (heading + screenshot + bullets); pills row removed,
  Opening Explorer removed from FEATURES list.
- Stats renamed to "Global Stats" across desktop nav, mobile bottom bar, More
  drawer, mobile header, plus new page h1.

## [v1.8] Guest Access — 2026-04-06

Free try-before-signup: users can play with FlawChess as a guest, then promote
their guest account into a full account without losing any imported data.

### Added

- Guest session foundation — `is_guest` User model, JWT-based guest sessions
  with 30-day auto-refresh, IP rate limiting on guest creation.
- Guest frontend — "Use as Guest" buttons on homepage and auth page,
  persistent guest banner indicating limited access.
- Email / password promotion — backend promotion service, register-page
  promotion flow preserving all imported data.
- Google SSO promotion — OAuth promotion route with guest identity
  preservation across redirect, email collision handling.

### Security

- Patched Google OAuth for CVE-2025-68481 CSRF vulnerability (double-submit
  cookie validation).

### Fixed

- Import page guest guard, auth page logo linking, delete button disabled
  during active imports.

## [v1.7] Consolidation, Tooling & Refactoring — 2026-04-03

Tooling and code-quality consolidation: static type checking, dead-code
detection, import pipeline speedup, and naming cleanup.

### Added

- Astral `ty` static type checker in CI — zero backend type errors, all
  functions annotated.
- Knip dead export detection + TypeScript `noUncheckedIndexedAccess` — zero
  dead code, strict index-access safety.

### Changed

- Import pipeline ~2x faster — unified single-pass PGN processing, bulk CASE
  UPDATE, batch size 10 → 28.
- SQL aggregation (`COUNT().filter()`) replacing Python-side W/D/L counting
  loops.
- Consistent naming and deduplication — router prefixes, shared
  `apply_game_filters`, frontend `buildFilterParams`.
- CSS variable brand buttons (`.btn-brand`) replacing JS constant, typed
  Pydantic response models on all endpoints.

### Removed

- 7 dead files deleted, unused shadcn/ui re-exports cleaned, -1522 lines.

## [v1.6] UI Polish & Improvements — 2026-03-30

Centralized theme system, shared WDL chart component, a new Openings reference
table from 3641 curated openings, and mobile drawer sidebars.

### Added

- Centralized theme system with CSS variables, charcoal containers with SVG
  noise texture, brand subtab highlighting.
- Shared `WDLChartRow` component replacing all inconsistent WDL chart
  implementations.
- Openings reference table (3641 entries from TSV) with SQL-side WDL
  aggregation and filter support.
- Most Played Openings redesign — top 10 per color, dedicated table UI with
  minimap popovers.
- Mobile drawer sidebars for filters and bookmarks with deferred filter apply
  on close.

### Changed

- Opening Statistics — smart default chart data from most-played openings,
  chart-enable toggles on bookmarks.

## [v1.5] Endgame Analytics & Engine Data — 2026-03-28

Game phase classification at import, material signatures for endgame
categorization, engine analysis metrics ingestion, and the first cut of the
Endgames tab.

### Added

- Game phase classification (opening / middlegame / endgame) per position at
  import.
- Material signature, imbalance, and endgame class per position at import.
- Engine analysis data import (eval, accuracy, move quality) from chess.com
  and lichess.
- Endgame performance statistics in a dedicated Endgames tab, filterable by
  type (rook, minor piece, pawn, queen, mixed).
- Conversion stats (win rate when up material) with timeline charts.
- Recovery stats (draw / win rate when down material) with timeline charts.
- Homepage refresh with feature showcase, FAQ, and acknowledgements.

## [v1.4] Web Analytics — 2026-03-28

### Added

- Web analytics via self-hosted Umami.

## [v1.3] Project Launch — 2026-03-22

Production launch: rebrand to FlawChess, Hetzner deployment, CI/CD, Sentry,
public homepage, rate limiting, and privacy policy.

### Added

- Complete Docker Compose stack (FastAPI + Caddy 2.11.2 + PostgreSQL) deployed
  to Hetzner VPS with auto-TLS.
- GitHub Actions CI/CD pipeline — test + lint + SSH deploy + health check
  polling.
- Sentry error monitoring on backend (`sentry-sdk[fastapi]`) and frontend
  (`@sentry/react`) with Docker build-time DSN injection.
- Public homepage with feature sections, FAQ, and register / login CTA; SEO
  meta tags, sitemap.xml, robots.txt.
- Per-platform rate limiter (`asyncio.Semaphore`) protecting chess.com /
  lichess imports from concurrent bans.
- Privacy policy page at `/privacy`; professional README with screenshots and
  self-hosting instructions.

### Changed

- Full codebase renamed from Chessalytics to FlawChess across 20 files — PWA
  manifest, logo, GitHub org transfer.

## [v1.2] Mobile & PWA — 2026-03-21

Installable PWA with mobile-first navigation, touch interactions, and a phone
testing dev workflow.

### Added

- Installable PWA with service worker, chess-themed icons, Workbox caching
  (NetworkOnly for API routes).
- Mobile bottom navigation bar with direct tabs and slide-up "More" drawer
  (vaul-based).
- Click-to-move chessboard on touch devices with sticky board layout on
  Openings page.
- 44px touch targets on all interactive elements, no horizontal scroll at
  375px.
- Android / iOS in-app install prompts (`beforeinstallprompt` + manual iOS
  instructions).
- Cloudflare Tunnel dev workflow for HTTPS phone testing.

## [v1.1] Opening Explorer & UI Restructuring — 2026-03-20

Interactive move explorer with W/D/L stats per position, tabbed Openings hub,
dedicated Import page, enriched import data, and redesigned game cards.

### Added

- Move explorer with next-move W/D/L stats, click-to-navigate, transposition
  handling.
- Chessboard arrows showing next moves with win-rate color coding.
- Tabbed Openings hub (Moves / Games / Statistics) and dedicated Import page.
- Enhanced import — clock data, termination reason, time control fix,
  multi-username sync.
- Game cards — 3-row layout with icons, hover / tap minimap showing final
  position.

### Fixed

- Data isolation bugs between users.
- Google SSO last_login not being updated.
- Stale cache on auth transitions.

## v1.0 Initial Platform — 2026-03-15

First public version of FlawChess: multi-user chess analysis with game import
from chess.com and lichess, Zobrist-hash position matching, interactive board,
bookmarks, game cards, and rating / stats pages.

### Added

- Import pipeline with incremental sync (chess.com + lichess).
- Position analysis via precomputed Zobrist hashes (white / black / full) for
  indexed integer equality lookups.
- Interactive chess board to specify search positions by playing moves.
- Filters: time control, rated / casual, recency, color, opponent type,
  position color.
- Position bookmarks with drag-reorder, mini boards, piece filter.
- Auto-generated bookmark suggestions from most-played openings.
- Game cards with rich metadata and pagination.
- Rating history, global stats, openings W/D/L charts.
- Multi-user auth with data isolation.

[Unreleased]: https://github.com/flawchess/flawchess/compare/v1.14...HEAD
[v1.14]: https://github.com/flawchess/flawchess/compare/v1.13...v1.14
[v1.13]: https://github.com/flawchess/flawchess/compare/v1.12...v1.13
[v1.12]: https://github.com/flawchess/flawchess/compare/v1.11...v1.12
[v1.11]: https://github.com/flawchess/flawchess/compare/v1.10...v1.11
[v1.10]: https://github.com/flawchess/flawchess/compare/v1.9...v1.10
[v1.9]: https://github.com/flawchess/flawchess/compare/v1.8...v1.9
[v1.8]: https://github.com/flawchess/flawchess/compare/v1.7...v1.8
[v1.7]: https://github.com/flawchess/flawchess/compare/v1.6...v1.7
[v1.6]: https://github.com/flawchess/flawchess/compare/v1.5...v1.6
[v1.5]: https://github.com/flawchess/flawchess/compare/v1.4...v1.5
[v1.4]: https://github.com/flawchess/flawchess/compare/v1.3...v1.4
[v1.3]: https://github.com/flawchess/flawchess/compare/v1.2...v1.3
[v1.2]: https://github.com/flawchess/flawchess/compare/v1.1...v1.2
[v1.1]: https://github.com/flawchess/flawchess/compare/47cca4c...v1.1
