# Milestones: FlawChess

## v1.21 Time-Control-Aware Endgame Metrics (Shipped: 2026-05-31)

**Phases completed:** 4 phases (97, 98, 99, 99.1), 15 plans. Delivered via PRs #160 (Phase 97), #163/#164 (Phase 98), #167 (Phase 99), #168 (Phase 99.1); benchmark-generator side work in #166.
**Stats:** ~383 files changed, +156,697 / -101,643 lines (dominated by the Phase 99 cohort-CDF regen and the Phase 99.1 demotion of that generated data), 54 commits over 3 days (2026-05-29 → 2026-05-31) since v1.20 (commit `dcd22fef` → `83fe9f01`).
**Milestone goal:** Make the entire Endgame Metrics and Endgame Type Breakdown reporting time-control-aware, so a player is judged against the norms of the speed they actually play rather than a blended average.

**Key accomplishments:**

- **Phase 97 — Endgame Metrics by Time Control** (PR #160): replaced the single aggregated Conversion/Parity/Recovery cards with one card per time control (bullet/blitz/rapid/classical), each carrying its own gauge trifecta, WDL bar, and Score Gap chart. Conversion/Recovery gauges use TC-specific neutral bands (benchmark TC d≈0.9); Parity and Score Gap keep the shared global band (both collapse on TC). Cards self-suppress below a per-TC games floor. New backend `_compute_per_tc_metric_cards` + a `TC_METRIC_BANDS` registry codegen'd into `endgameZones.ts`.
- **Phase 98 — Per-TC Collapsible Endgame Type Cards** (PR #163, release #164): restructured the Endgame Type Breakdown from a 3-col grid of five per-type cards into full-width vertically-stacked collapsible cards, one per TC, primary TC (time-weighted) expanded by default. Each card holds a 2×2 grid of four type tiles (rook/minor_piece/pawn/queen — Mixed dropped); Conv/Recov gauges return, banded against each card's own per-(class × TC) IQR, Score Gap banded per-TC for one consistent card grammar.
- **Phase 99 — Percentile Badges for Conversion, Parity, and Recovery** (PR #167): added peer-relative percentile chips to the per-TC Conv/Parity/Recov rate cards. 12 new per-(metric, TC) ENUM values computed via the shared pooled-per-user `canonical_slice_sql.py` builder parameterised by TC, cohort-matched on the per-(user, TC) rating anchor, 4-bullet disclosure tooltip. Prod backfill deferred to deploy (todo `2026-05-31-phase-99-prod-backfill-rate-percentiles`).
- **Phase 99.1 — Move Cohort CDF Out of Source into a DB Table** (PR #168; INSERTED): relocated the generated `COHORT_PERCENTILE_CDF` registry (3.1 MB / ~130k lines) out of `app/services/global_percentile_cdf.py` into a `benchmark_cohort_cdf` DB table seeded from a compact `app/data/` artifact via `scripts/seed_cohort_cdf.py`; the module shrank to ~250 lines. Internal refactor, byte-for-byte chip parity, no behaviour change. Closes SEED-030 Track B.

**Tech debt (carried forward, informational):**

- Prod backfill of the 12 new rate-percentile metrics deferred to deploy.
- SEED-030 Track A (split oversized multi-concern modules) remains open.

See `.planning/milestones/v1.21-ROADMAP.md`. No formal requirements (all phases standalone endgame-stats UX refinements / internal refactor — no requirement IDs); REQUIREMENTS.md continues to track the pending v1.22 LLM Statistical Reasoning scope.

---

## v1.20 Import Pipeline Hardening Follow-Up and Readiness (Shipped: 2026-05-29)

**Phases completed:** 2 phases (95, 96), 5 plans. Delivered via PRs #148/#149 (Phase 95) and #151 (Phase 96). Two standalone phases regrouped post-hoc into a milestone on 2026-05-30.
**Milestone goal:** Finish closing the FLAWCHESS-3Q OOM family (asyncpg COPY for the heaviest import write) and replace the eval-coverage auto-reload hack with an honest per-page readiness gate.

**Key accomplishments:**

- **Phase 95 — asyncpg COPY for `bulk_insert_positions`**: switched the heaviest INSERT in the import pipeline to asyncpg binary `copy_records_to_table`, the SEED-027 Thread B follow-up to the Thread A container-memory-budget hotfix (PR #144). Enrolled in the active session transaction for atomicity; `bulk_insert_games` keeps its `ON CONFLICT DO NOTHING` path.
- **Phase 96 — Import Readiness Gate**: replaced the `window.location.reload()`-on-eval-complete hack with a two-tier per-page gate — Tier 1 (hot lane drained) unlocks Openings + Overview, Tier 2 (evals drained + Stage A/B percentiles persisted) unlocks Endgames. Consolidated eval-progress UI into a single global header.

See `.planning/milestones/v1.20-ROADMAP.md`. No requirements archive (both phases standalone hardening/UX — no requirement IDs).

---

## v1.19 Endgame Percentiles (Shipped: 2026-05-27)

**Phases completed:** 6 phases (93, 94, 94.1, 94.2, 94.3, 94.4). 26/26 PCTL/TPCTL/PRPCR requirements satisfied. Final phase merged via PR #145.
**Milestone goal:** Surface peer-relative percentile annotations on Endgame metrics so users see how their performance compares to same-rated cohort peers.

**Key accomplishments:**

- **Phase 93 — Global Percentile Benchmark Artifact** and **Phase 94 — Backend & Frontend Percentile Annotations**: the cohort-percentile pipeline + the `PercentileChip` primitive.
- **Phase 94.1/94.2 — Canonical-Slice / Pooled-Per-User Percentile Materialisation**: redesigned per-user percentile computation so CDF construction and per-user lookup share one SQL path (drift structurally impossible).
- **Phase 94.3 — Per-TC Percentile Chips on Time Pressure Cards** (INSERTED, SEED-025) and **Phase 94.4 — Peer-Relative Percentile Chip Refinement** (INSERTED, SEED-026 v2 + D-12 reversal): the per-TC chip pattern later reused by Phase 99.

Phase 95 (LLM Statistical Reasoning) was split out into v1.20 on 2026-05-27 (commit `dd88ffda`) before milestone close. Audit at `.planning/v1.19-MILESTONE-AUDIT.md`; traceability in `.planning/milestones/v1.19-REQUIREMENTS.md`.

---

## v1.18 Import Pipeline Hardening (Shipped: 2026-05-22)

**Phases completed:** 3 phases (90, 91, 92), 17 plans, delivered via PRs #130, #137, #138 (plus the production-branch hotfix #139 capping DB pool / max_connections / container memory for FLAWCHESS-3Q).
**Stats:** 240 files changed, +30,193 / -9,406 lines, 54 commits over 3 days (2026-05-19 → 2026-05-22) since v1.17 (commit 114211c2 → f5224b4f).
**Source:** Two prod-side OOM recurrences after v1.17 (FLAWCHESS-56 2026-05-16, FLAWCHESS-3Q 2026-05-21) — single-import RSS climbing linearly under heavy fetch, Postgres OOM-killed when one uvicorn process fanned out to 13 active backends. Seeds SEED-017/018/022/023 captured the diagnostic; this milestone retired all four.

**Key accomplishments:**

- **Phase 90 — Import pipeline memory leak fix + resilience** (PR #130): replaced the literal `case()`+`IN` bulk UPDATE in `_flush_batch` Stage 5 with bound-parameter `executemany` (root cause of the linear RSS climb — a per-batch unique SQL statement that the prepared-statement cache kept forever). Scoped `AsyncSession` per batch in `run_import`. Promoted `cleanup_orphaned_jobs()` from a startup-only call to a periodic + on-DB-reconnect reaper so a Postgres-only restart no longer strands jobs `in_progress`. Bounded-retry-with-backoff around the failure-state UPDATE.
- **Phase 91 — Two-lane import: defer Stockfish eval to in-process cold drain** (PR #137 + follow-on #134/#135): added `games.evals_completed_at` + partial index. Hot path now does fetch → parse → insert positions → commit with no Stockfish work; a separate `run_eval_drain()` lifespan coroutine picks 10 games per tick from the partial index and evaluates outside any session scope. Frontend Stockfish-coverage header bar + per-metric "based on N of M eligible games" caveat on every eval-dependent stat. Dual-20k stress-test harness in `scripts/measure_dual_import_rss.py`.
- **Phase 92 — Custom date range filter** (PR #138): replaced the closed `Recency` string union on the API wire with `from_date` / `to_date` params; added a 9th "Custom range…" entry to the recency dropdown with a desktop Popover + mobile nested Drawer, shadcn Calendar component installed. `Recency` → `RecencyPreset` UI-only type. LLM insights prompts derive human window labels from absolute dates. Closes a pending bookmark-timeseries cleanup todo (`2026-05-02-remove-recency-from-bookmark-timeseries`).
- **Hotfix PR #139 (FLAWCHESS-3Q)**: SQLAlchemy pool 20+30 → 10+10, Postgres `max_connections` 100 → 30, backend/db container `mem_limit` + `memswap_limit` set, Hetzner CPX32 → CPX42 (4→8 vCPU, 7.6→16 GB RAM). Postgres tuned for the 16 GB host (`shared_buffers=4GB`, `effective_cache_size=12GB`, `work_mem=16MB`).

**Tech debt (carried forward, informational):**

- SEED-024 (`ProcessPoolExecutor` for chess.com fetch lane) planted but deferred — pure throughput win, blocked on per-worker RSS measurement after the CPX42 RAM upgrade.
- Concurrent-import admission control (SEED-022 option F), scheduled backend-restart cadence (option G), and idempotent `on_game_fetched` (option A′) intentionally not shipped — hot-lane batches now too cheap to OOM under realistic concurrent load.

---

## v1.17 Endgame Stats Card Redesign (Shipped: 2026-05-19)

**Phases completed:** 13 phases (84, 85, 85.1, 86, 87, 87.1, 87.2, 87.4, 87.5, 87.6, 88, 88.3, 88.4), ~54 plans. Phase 87.3 superseded by 87.4; Phase 89 (Polish) dropped from scope. Delivered via PRs #89–#117.
**Stats:** 603 files changed, +82,473 / -9,393 lines, 203 commits over 8 days (2026-05-11 → 2026-05-19) since v1.16 (commit 4075431d → 114211c2).
**Known deferred items at close:** 164 open audit items acknowledged and deferred (see STATE.md Deferred Items) — same historical carry-forward as v1.11–v1.16 (155 misclassified quick-task dirs, 1 diagnosed debug session, 5 long-range todos, 3 dormant SEED-002/006 seeds).

**Definition of done:** Three table-driven Endgames-page sections replaced with the WDL + ScoreBullet card pattern, plus a full statistical-rigor pass (eval-based ΔES Score Gap, hypothesis tests + CIs, Endgame Skill dropped, Endgame ELO rebuilt, Time Pressure reworked).

**Key accomplishments:**

- **Section 1 (Phase 85/85.1)** — 3-card composite (Middlegame / At Entry / Endgame results) replacing the perf table + Start-vs-End twin-tile; two-sample z + paired one-sample z hypothesis tests with 95% CI whiskers on the Score Gap rows.
- **Section 2 (Phase 86/87.2)** — 4-card Endgame Metrics layout; retired the mathematically degenerate rate-based mirror-bucket peer-diff (Conv-Gap ≡ Recov-Gap) for an eval-based ΔES Score Gap anchored to the Stockfish baseline.
- **Section 3 (Phase 87/87.1)** — 5 per-type breakdown cards (rook/minor/pawn/queen/mixed) with Conv+Recov gauges, WDL bar, sig-gated chess-score bullet, per-span ΔES Score Gap row, `?type=` deep-links.
- **Endgame ELO rebuilt (Phase 87.4→87.5→87.6)** — Endgame Skill concept dropped end-to-end; timeline rebuilt as a logistic stretch around Actual ELO (`endgame_elo + non_endgame_elo == 2·actual_elo`), eliminating the sigmoid bias and the violated "Actual ELO between the lines" invariant.
- **Time Pressure rework (Phase 88/88.4)** — per-TC cards with benchmark-calibrated zones, 3-stat header row, and a zone-banded zero-centered line chart with CI whiskers replacing the stacked per-bucket bullets.
- **Viz polish (Phase 88.3)** — inactivity-gap break annotations on all 6 ordinal-axis timeline charts; ELO Timeline defaults to the single most-active series; Overall Performance restructured into one responsive 2-column card.

---

## v1.16 Stockfish Eval Analyses (Shipped: 2026-05-11)

**Phases completed:** 5 phases (80, 80.1, 81, 82, 83), 24 plans, delivered via PRs #80, #82, #85, #86, #88.
**Stats:** 267 files changed, +47,752 / -4,427 lines, 118 commits over 7 days (2026-05-05 → 2026-05-11) since v1.15 (commit 64441744 → 46f78231).

**Definition of done:** Downstream consumers of v1.15 Stockfish evals (endgame span-entry + middlegame-entry `eval_cp`/`eval_mate` on `game_positions`), plus opportunistic UX fixes that fall in the same area.

**Key accomplishments:**

- **Phase 80** — Opening Stats subtab: avg eval at middlegame entry ± std (user POV) with one-sample t-test confidence pill and CI-whisker MiniBulletChart; later restructured into a two-column card grid (quick task `260506-rtk`) replacing MostPlayedOpeningsTable.
- **Phase 80.1** — Move Explorer + Opening Insights WDL/score now reflect resulting-position (transposition-inclusive) instead of move-played only. New `query_transposition_wdl` + `query_resulting_position_wdl` repo helpers; `game_count` and the n≥10 surfacing gate stay move-played for honest disclosure.
- **Phase 81** — Endgame Start vs End twin-tile section above the WDL table: entry-eval (cp, sig-tested vs 0) + endgame score (sig-tested vs 50%), three-state color with Wald-z / Wilson tests, n≥10 gate, "we can't tell" framing for non-significant verdicts.
- **Phase 82** — LLM prompt pipeline (`endgame_v23` → `endgame_v24`) gains awareness of both Phase 81 metrics: `MetricId` + `SubsectionId` Literal extensions, `ZONE_REGISTRY` entries for `entry_eval_pawns` (band ±0.5 after D-08 tightening) + `endgame_score` (band [0.45, 0.55]); fixed two `_SECTION_LAYOUT` / `_format_zone_bounds` regressions during live UAT.
- **Phase 83** — Stockfish-baseline predicted endgame score (Lichess sigmoid k=0.00368208) with 2x2 grid restructure of Start vs End; `entry_expected_score` + `_n` / `_p_value` / `_ci_low` / `_ci_high` schema fields; LLM narrates achievable-vs-achieved gap as headline diagnostic (`endgame_v25` → `endgame_v26`). Closes SEED-014.

**Tech debt (carried forward, informational):**

- Phase 80: 8 informational UAT scenarios on UI superseded by two-column card grid (quick task `260506-rtk`).
- Phases 80.1 + 82: clerical `VALIDATION.md status=draft` / `nyquist_compliant=false` despite passing verification with all required tests in place.
- Pre-existing: stale `test_min_games_per_candidate_floor_at_10` (Phase 79 raised floor 10→20); project-wide `ruff format` drift on 89 files (not CI-gated).

---

## v1.15 Eval-Based Endgame Classification (Shipped: 2026-05-03)

**Phases completed:** 2 phases (78, 79), 10 plans, delivered via PR #78 (combined Phase 78 + Phase 79 cutover) plus follow-on PR #79 (`EnginePool` parallelisation).
**Stats:** 214 files changed, +21,125 / -4,336 lines, 68 commits over 5 days (2026-04-29 → 2026-05-03) since v1.14 (commit 50c16e5 → 42cddf5).
**Source:** `reports/conv-recov-validation-2026-05-02.md` flagged the material-imbalance + 4-ply persistence proxy at ~81.5% agreement vs Stockfish on the populated subset, missing ~24% of substantive material-edge sequences (queen + pawnless classes underperformed structurally).

**Key accomplishments:**

- Endgame Conversion / Parity / Recovery classification migrated from material-imbalance + 4-ply persistence proxy to direct Stockfish-eval thresholding (±100 cp on `eval_cp`, color-flipped to user perspective; `eval_mate` short-circuits to ±1,000,000 cp). Hard cutover, proxy code path removed entirely. Closes the structural gap on Queen and pawnless classes where the proxy underperformed (Phase 78 REFAC-01..03)
- Pinned Stockfish sf_17 AVX2 binary in the backend Docker image with SHA-256 supply-chain verification (later bumped to sf_18); CI installs `stockfish` via apt; `STOCKFISH_PATH` env var threaded end-to-end (Phase 78 ENG-01)
- `app/services/engine.py` — async-friendly Stockfish wrapper with FastAPI lifespan integration (`start_engine` / `stop_engine`, idempotent, depth-15 `evaluate()` API). Shared by import path and backfill script (Phase 78 ENG-02, ENG-03)
- `scripts/backfill_eval.py` — idempotent + resumable CLI driver (skip-where-NULL, COMMIT-every-100, `--db dev/benchmark/prod`, `--user-id`, `--limit`, `--dry-run`, `--workers N` for parallel evaluation). FILL-02 relaxed mid-plan to drop `full_hash` dedup — added complexity for marginal CPU savings on a one-shot backfill (Phase 78 FILL-01..04)
- Import-time eval pass: per-class span-entry rows + middlegame entry row populated on every new import in `_flush_batch` between `bulk_insert_positions` and the `move_count` UPDATE, in the same transaction. Adds well under 1s to the typical-game import path (Phase 78 IMP-01..02; Phase 79 PHASE-IMP-02)
- Alembic `c92af8282d1a` reshapes `ix_gp_user_endgame_game INCLUDE` from `material_imbalance` to `eval_cp` / `eval_mate` so rewritten endgame queries stay index-only. `_classify_endgame_bucket(eval_cp, eval_mate, user_color)` is the single helper; SQL projects raw white-perspective eval, service applies the user-color sign flip (Phase 78 REFAC-04, REFAC-02)
- Phase 79: `game_positions.phase` SmallInteger column (0=opening, 1=middlegame, 2=endgame) computed via Python port of [lichess `Divider.scala`](https://github.com/lichess-org/scalachess/blob/master/core/src/main/scala/Divider.scala) using existing `piece_count`, `backrank_sparse`, `mixedness` inputs — no second board scan. 11 Divider-sourced parity assertions in `tests/test_position_classifier.py` lock output to lichess reference (Phase 79 CLASS-01..02, SCHEMA-01..02; Alembic `1efcc66a7695`)
- Phase 79: Middlegame entry position (`MIN(ply)` of `phase = 1` per game) Stockfish-evaluated at depth 15 alongside endgame span-entry positions, populated into the same `eval_cp` / `eval_mate` columns. Substrate for v1.16 opening-stats analyses (Phase 79 PHASE-IMP-02, PHASE-FILL-02)
- Combined Phase 78 + Phase 79 operator cutover (D-79-10): single benchmark + prod backfill pass, single PR #78, single deploy. Saved an operational round-trip and consolidated the deployment risk window (Phase 79 plan 79-04)
- Follow-on PR #79 (quick task 260503-pool): import-time eval pass parallelised via module-level `EnginePool` of `STOCKFISH_POOL_SIZE` workers (default 1, prod ships 2 via `docker-compose.yml`). `import_service.py` collects eval targets across an import batch and fans them out via `asyncio.gather`. Sequential callers see no change; parallel callers gain ~POOL_SIZE× throughput
- Inline quick tasks during the milestone window: 260501-s0u (endgame UI rebuild from benchmark report — clock-pressure neutral band ±10pp → ±5pp, recovery typical band [25%, 35%] → [25%, 40%], grouped WDL chart replaced with six per-class Conversion/Recovery mini-gauges, LLM endgame insights prompt v18 reframes Conv/Recov as delta-from-class-baseline); 260503 (gauge typical bands recalibrated from the 2026-05-03 benchmark report); 260503-fef (`/benchmarks` skill applies equal-footing opponent filter `abs(opp_rating - user_rating) ≤ 100`); 260503-0t8 (`backfill_eval.py` parallelised via `EnginePool`)
- VAL-01 / PHASE-VAL-01 rescinded as moot 2026-05-03: once REFAC-03 deleted the proxy code path, the agreement metric became undefined. The `/conv-recov-validation` skill was deleted

**Known deferred items at close: 5**

- VAL-01 / PHASE-VAL-01 — rescinded, not deferred (see above)
- `STOCKFISH_POOL_SIZE` defaults to 1 outside prod; prod ships 2. No autotune. Worth re-visiting if import latency p99 regresses
- `STOCKFISH_PATH` env-var setup is ad-hoc for standalone runs (documented in CLAUDE.md). A wrapper in `bin/` could harden the local-dev experience
- Carried forward: 9 stale debug session entries (March-April), 135 quick-task directory entries without status frontmatter (audit misclassifies as open — both historical), 5 long-range todos, 1 dormant seed
- SEED-002 (benchmark population baselines) and SEED-006 (zone recalibration) — dormant, gated on full benchmark ingest. SEED-010 (Library milestone) now eligible to open post-v1.15

---

## v1.14 Score-Based Opening Insights (Shipped: 2026-04-29)

**Phases completed:** 3 phases (75, 76, 77), 16 plans, delivered via PRs #69, #70, #71 (inline confidence-mute hotfix), #72, #73 (quick task).
**Stats:** 123 files changed, +18,701 / -787 lines over 2 days (2026-04-28 → 2026-04-29) since v1.13 (commit f15b3cc → fa5ac64).
**Source:** SEED-007 (Option A only — Wilson on score, 0.50 pivot, no user-baseline) + SEED-008 (label reframe). Both seeds folded into this milestone and closed.

**Key accomplishments:**

- Migrated Opening Insights and Move Explorer color coding from loss-rate to chess score `(W + 0.5·D)/N`. Score is now the canonical metric in `opening_insights_service.py`, `openings_repository.py`, `arrowColor.ts`, and the `NextMoveEntry` / `OpeningInsightFinding` API payloads. `loss_rate` / `win_rate` removed cleanly. Effect-size gate against a 0.50 pivot with strict `≤`/`≥` boundaries — minor at 0.45/0.55, major at 0.40/0.60 (Phase 75)
- Trinomial Wald 95% confidence interval per finding using the actual variance of the chess result distribution `X ∈ {0, 0.5, 1}` — `(W + 0.25·D)/N − score²` rather than the binomial Wilson approximation that over-states uncertainty when draws are common (standard formula in BayesElo / Ordo). Pure-Python `math` only, no scipy dependency. Half-width buckets `≤ 0.10 → high`, `≤ 0.20 → medium`, else `low`. Pivoted from Wilson per Phase 75 D-05 (Phase 75)
- API contract extended with both `confidence: "low" | "medium" | "high"` (the half-width bucket, user-facing badge) and `p_value: float` (two-sided Z-test of observed score vs 0.50, tooltip-grade significance). `severity` retained so the frontend renders effect size + precision + significance per finding without overloading any one cue. `MIN_GAMES_PER_CANDIDATE` dropped 20 → 10 to enable discovery framing (Phase 75)
- Frontend score-based coloring shipped end-to-end: `arrowColor.ts` migrated to score (effect-size only, no confidence cue on arrows); Move Explorer moves-list row tint by score with extended mute rule `(game_count < 10 OR confidence === 'low')`; new Conf column with sort key `(confidence DESC, |score - 0.50| DESC)`; `OpeningFindingCard` renders score-based prose with level-specific confidence indicator and directional p-value tooltip; `UNRELIABLE_OPACITY` mute applied when `n_games < 10` OR `confidence === 'low'`. Mobile parity at 375px (Phase 76)
- Four `InfoPopover` triggers on `OpeningInsightsBlock` section headers cover the score / sample-size / confidence framing (Phase 76 D-17)
- INSIGHT-UI-04 descoped 2026-04-28 per Phase 76 D-04: severity word never appears as user-facing text (only drives border color); confidence badge + sort calibration deliver SEED-008's intent without rewriting "Weakness/Strength" titles
- Post-Phase-76 inline hotfix (PR #71): force grey arrow + skip row tint when `confidence === 'low'`. Board reads cleaner; low-confidence findings still surface in the table with the badge but don't visually claim authority on the board
- Phase 77 troll-opening watermark — frontend-only matching via side-only FEN piece-placement key (no backend schema, no Zobrist hash, no API contract change). `troll-face.svg` renders as 30%-opacity bottom-right watermark on `OpeningFindingCard` (mobile + desktop) and a small inline icon next to qualifying SAN rows in `MoveExplorer` (desktop only via `hidden sm:inline-block`). Curation is offline via a Node/TS script that emits per-ply candidates (both colors) for human pruning per CONTEXT.md D-01. Decorative `<img>` idiom (`alt=""` + `aria-hidden="true"`, `pointer-events-none`) keeps the asset cacheable and out of the accessibility tree (Phase 77)
- Single `compute_confidence_bucket` shared module across `opening_insights_service` and the move-explorer payload — CI structural test asserts there's only one implementation. CI consistency test `test_opening_insights_arrow_consistency` updated to enforce score-based threshold lock-step between backend classification and `frontend/src/lib/arrowColor.ts`
- Inline quick tasks during the milestone window: 260428-doc-framing-refresh (PROJECT/CLAUDE/README lead sections), 260428-oxr (replaced Wald half-width buckets with p-value thresholds), 260428-tgg (sort by Wald CI bound), 260428-v9i (switched ranking from Wald to Wilson score interval bound), 260429-gmj (after-move arrow on insight finding mini board, PR #73)

**Known deferred items at close: 6**

- INSIGHT-UI-04 — descoped 2026-04-28 (Phase 76 D-04). Severity word never user-facing; confidence badge + sort carry SEED-008 intent.
- Phase 77 HUMAN-UAT (3 open scenarios) and VERIFICATION (`human_needed`) — automated gates green, phase shipped via PR #72; remaining UAT captured in `77-HUMAN-UAT.md`, not blocking close.
- LLM narration of opening insights — future seed; v1.14 shipped the calibrated data plumbing (effect size + confidence + p_value) that LLM narration would consume.
- Population-relative weakness signals — gated on full benchmark ingest (SEED-006). Deliberately not part of v1.14 because the design rejects user/population baselines.
- Carried forward: 9 stale debug session entries (March-April), 133 quick-task directory entries without status frontmatter (audit misclassifies as open — both historical), pre-existing ORM/DB column drift (`game_positions.clock_seconds`, `games.white_accuracy`, `games.black_accuracy`), 2 long-range todos (bitboard-storage; phase-70-amendments already landed but todo file not pruned).
- SEED-002 (benchmark population baselines) and SEED-006 (zone recalibration) — dormant, gated on full benchmark ingest.

---

## v1.13 Opening Insights (Shipped: 2026-04-27)

**Phases completed:** 3 phases (70, 71, 71.1), 14 plans, delivered via PRs #66, #67, #68 (squash merges). Phases 72, 73, 74 descoped 2026-04-27.
**Stats:** 106 files changed, +19,246 / -561 lines over 2 days (2026-04-26 → 2026-04-27)
**Source:** SEED-005 — Opening weakness and strength insights, fulfilled by templated/rule-based v1; LLM narration deferred.

**Key accomplishments:**

- Backend `opening_insights_service` with `POST /api/insights/openings` — single SQL transition aggregation per (user, color) over `game_positions` for entry plies in [3, 16], LAG-window CTE + `array_agg` over windowed rows passes `entry_san_sequence` straight to the service. Strict `>` 0.55 win/loss threshold, `MIN_GAMES_PER_CANDIDATE = 20` evidence floor, severity tier major (≥ 0.60) / minor (Phase 70)
- Two-pass attribution with parent-prefix Zobrist lookup (ctypes c_int64 signed-int64 conversion to match python-chess polyglot hashes). Findings with neither direct nor parent-lineage match are dropped, never surfaced as `<unnamed line>` placeholders. Sentry tag captures unmatched drops for diagnosis (Phase 70)
- Database migration `80e22b38993a_add_gp_user_game_ply_index` — first project use of `postgresql_concurrently=True` + `autocommit_block`. Partial composite covering index `ix_gp_user_game_ply (user_id, game_id, ply) INCLUDE (full_hash, move_san) WHERE ply BETWEEN 1 AND 17` keeps the LAG-window scan an Index Only Scan with Heap Fetches: 0 at ~9% of table size (Phase 70)
- Frontend `OpeningInsightsBlock` on Openings → Stats subtab — per-finding cards (`OpeningFindingCard`) with severity-accented border (DARK_RED / LIGHT_RED / DARK_GREEN / LIGHT_GREEN from `arrowColor.ts` for stroke-aligned colors), shared `LazyMiniBoard` thumbnail extracted from `GameCard`, dual mobile/desktop layout, four-state rendering (loading skeleton, error, empty, populated). CI test `test_opening_insights_arrow_consistency` enforces backend/frontend threshold lock-step (Phase 71)
- Deep-link wiring — clicking a finding's Moves link replays `entry_san_sequence` through `chess.loadMoves()`, flips the board if the finding is for the black side, applies the matching color filter with `matchSide: 'both'`, navigates to Openings → Move Explorer pre-positioned at the entry FEN with the candidate move highlighted (sticky severity tint + one-shot pulse from quick-task 260427-j41) (Phase 71)
- Openings page subnav layout refactor — desktop subnav lifts above `SidebarLayout` to span the full board+main columns mirroring Endgames; mobile gains a sticky 4-tab subnav with filter button, board becomes non-sticky on Moves+Games and hidden on Stats+Insights, chevron-fold collapsible removed entirely. Subtab switching resets scroll to top on both desktop and mobile (Phase 71.1)
- Pre-v1.13 quick task PRE-01 — dropped the parity filter from `query_top_openings_sql_wdl`, surfacing 1599 of 3301 white-defined ECO openings in the black top-10 (e.g. Hillbilly Attack — 816 black games previously invisible). Off-color rows now prefixed with `vs.` for clarity

**Known deferred items:**

- INSIGHT-MOVES-01..03 (inline weakness/strength bullets on Moves subtab), INSIGHT-META-01 (meta-recommendation aggregate finding), INSIGHT-BADGE-01 (bookmark-card weakness badge) — all descoped 2026-04-27. Move Explorer row tinting via `getArrowColor` already conveys the signal at the displayed position; per-finding cards in Phase 71 deliver the actionable signal at finer granularity than an aggregate; bookmark-badge density risked alert fatigue with Endgames + Openings nav dots already present
- Phase 71 UAT (18 open scenarios), Phase 71.1 HUMAN-UAT (9 open scenarios), Phase 71.1 VERIFICATION (`human_needed`) — automated gates green, deferred for asynchronous review; phases shipped via PRs #67 and #68
- LLM narration of opening insights — revisit as v1.13.x or v1.14 once templated findings are in real users' hands and we know which findings are worth narrating
- Population-relative weakness signals — gated on full benchmark ingest (SEED-006); deliberately not part of v1.13 because book-move equality makes population baselines redundant for opening insights
- Carried forward: 8 stale debug session entries (March-April), 129 quick-task directory entries without status frontmatter (audit misclassifies as open — both historical), pre-existing ORM/DB column drift, `_compute_score_gap_timeline` / `_finding_time_pressure_vs_performance` grep noise from v1.11

---

## v1.12 Benchmark DB Infrastructure & Ingestion Pipeline (Shipped: 2026-04-26)

**Phases completed:** 1 phase (69), 6 plans (5 fully executed + 1 with descoped sub-tasks), delivered via PR #65 (squash merge).
**Stats:** 98 files changed, +13,440 / -1,740 lines, 51 commits over 2 days (2026-04-24 → 2026-04-26)
**Scope-down (2026-04-26):** Originally Phases 69-73. Phases 70-73 (classifier validation at scale, rating-stratified offsets, Parity validation, `/benchmarks` skill upgrade & zone recalibration) moved to SEED-006, gated on the full benchmark ingest. Pipeline correctness is the v1.12 deliverable; populating the DB is ops.

**Key accomplishments:**

- Isolated `flawchess-benchmark` PostgreSQL 18 container on port 5433, deployed via `docker-compose.benchmark.yml` with read-only MCP role `flawchess_benchmark_ro`, lifecycle script `bin/benchmark_db.sh` (start/stop/reset), and Alembic-driven schema parity with dev/prod/test (Phase 69-01)
- Third read-only MCP server `flawchess-benchmark-db` registered and documented in `CLAUDE.md` Database Access section alongside the existing two MCP DB servers (Phase 69-03)
- Eval-presence pre-filter via streaming `zgrep` scan over the Lichess monthly PGN dump, so the ~85% of dump games without `[%eval` headers never reach the python-chess parser, dropping selection-scan walltime by an order of magnitude (Phase 69-04)
- Stratified subsampling at the player-opportunity level on (rating_bucket × time_control). 5 rating buckets × 4 TCs, with separate `WhiteElo` / `BlackElo` bucketing per side (no game-level rating rollup); 90M games scanned, 491k qualifying, 8,628 distinct players persisted across 20 cells, 17/20 hitting the 500-user cap (Phase 69-04)
- Resumable ingest orchestrator with per-user checkpoint table, idempotent inserts via the existing `(platform, platform_game_id)` unique constraint, SIGINT + SIGKILL safe. Pending in-flight users are picked up first on resume; 0 duplicate game rows verified (Phase 69-05)
- Smoke-test ingest at `--per-cell 3` ran end-to-end against the live Lichess `/api/games/user` endpoint. 60 terminal rows: 56 completed, 3 over_20k_games skips, 1 unexplained failure deferred to SEED-006; 274,143 games and 19.4M positions imported in 3h 6min wall-clock (Phase 69-06)
- Pipeline-correctness verification report at `reports/benchmark-db-phase69-verification-2026-04-26.md` covering all four Dimension-8 evidence sections (selection scan, smoke ingest, resumability, eval coverage) plus storage budget projection (~205 GB at full `--per-cell 100` ingest, flagged for SEED-006 disk sizing) (Phase 69-06)
- Hot-patch mid-plan: dropped `games.eval_depth` and `games.eval_source_version` columns (added in plan 69-02 migration `b11018499e4f`, dropped in `6809b7c79eb3`) after the smoke confirmed Lichess's `/api/games/user` endpoint emits bare `[%eval cp]` annotations with no depth field. Both columns were dead weight; reintroduce when an actual second eval source exists. INGEST-06 reduced to "centipawn convention verified", already covered by `tests/test_benchmark_ingest.py::test_centipawn_convention_signed_from_white` running in CI (Phase 69-06)
- Centipawn convention verified, signed from white's POV (`pov.white().score()` / `.mate()`): centipawns vs pawn-units (`[%eval 2.35]` → +235 cp), mate annotations (`[%eval #4]` → mate=4) all asserted via the centipawn-convention test in CI

**Known deferred items:**

- Plan 69-06 sub-tasks 06-05 (`--per-cell 30` interim ingest) and 06-08 (manual cleanup of the 2026-03 Lichess dump file from local disk), descoped per the 2026-04-26 v1.12 scope-down. Full-scale population is operational ops work, not a milestone gate.
- VAL-01 from v1.11 (insights snapshot test), explicitly out of v1.12 scope per REQUIREMENTS.md. Promote via `/gsd-quick` when ready (no dependency on benchmark infra).
- Phases 70-73, moved to SEED-006 (benchmark population zone recalibration). Surface when full benchmark ingest completes.
- Pre-existing ORM/DB column drift (`game_positions.clock_seconds`, `games.white_accuracy`, `games.black_accuracy` REAL→Float), deferred again from v1.11 close. Deserves a dedicated cleanup migration.

---

## v1.11 LLM-first Endgame Insights (Shipped: 2026-04-24)

**Phases completed:** 5 phases (63, 64, 65, 66, 68), 23 plans, delivered via PR #61 (squash merge). Phase 67 (Validation & Beta Rollout) descoped — insights enabled for all users via commit `c91478e` instead of the beta-cohort validation loop. Phase 68 was added mid-milestone after UAT feedback.
**Stats:** 166 files changed, +42,078 / -262 lines, ~190 commits over 5 days (2026-04-20 → 2026-04-24)

**Key accomplishments:**

- LLM-backed Endgame Insights: `POST /api/insights/endgame` returns a structured `EndgameInsightsReport` (overview paragraph + up to 4 Section insights) produced by a pydantic-ai Agent, cached on a findings hash, rate-limited to 3 misses/hr/user, with soft-fail to the last cached report (Phase 65)
- Deterministic findings pipeline: `compute_findings` turns `/api/endgames/overview` into per-subsection-per-window `EndgameTabFindings` with zone/trend/sample-quality annotations and three cross-section flags (baseline-lift mutes score gap, clock-entry advantage/no-advantage) so the LLM reasons over pre-validated numbers (Phase 63)
- Shared zone registry as single source of truth: `app/services/endgame_zones.py` drives both narrative and chart visuals; Python→TypeScript codegen with CI drift guard so frontend gauge constants can never silently diverge (Phase 63)
- Generic `llm_logs` Postgres table (18 columns, BigInteger PK, JSONB for filter_context and response_json, FK CASCADE to users, 5 indexes including 3 composites with `created_at DESC`) designed to host every future LLM feature. Async repository with `genai-prices`-powered per-call cost accounting and `cost_unknown:<model>` soft-fallback (Phase 64)
- Provider-agnostic model selection via `PYDANTIC_AI_MODEL_INSIGHTS` env var; backend refuses to start if env var is missing/invalid. System prompt loaded from `app/prompts/endgame_insights.md` at startup — no string literals in `.py` files (Phase 65)
- Frontend `EndgameInsightsBlock` with parent-lifted mutation state pattern (Endgames.tsx holds one `useEndgameInsights` mutation; EndgameInsightsBlock + 4 SectionInsightSlot instances observe the same state without a context provider). Single retry affordance on any failure path (Phase 66)
- Dual-line "Endgame vs Non-Endgame Score over Time" chart replaces the single-line Score Gap chart — both absolute Score series rendered with a colored shaded area between them (green when endgame leads, red when trails). Prompt's `score_gap` framing rule simplified since the chart makes gap composition self-evident (Phase 68)
- Pre-merge milestone cohesion review — critical failing frontend test fixed, dead codegen pipeline completed (Phase 66 switchover finished: 3 FE chart components now import from generated zone constants), stale `Filters:` prompt reference removed (bumped to `endgame_v15`)

**Known deferred items:**

- Phase 67 descoped — VAL-01 (ground-truth regression test against SEED-001 canonical user fixture) and VAL-02 (admin-impersonation eyeball validation across 5 real user profiles) not executed. Insights were enabled for all users via commit `c91478e`. Recommended follow-up in v1.12: retrofit snapshot test against one real production user fixture.

---

## v1.10 Advanced Analytics (Shipped: 2026-04-19)

**Phases completed:** 11 phases (48, 52-55, 57, 57.1, 59-62), 28 plans, delivered via PRs #38, #43, #47, #49, #50, #51, #52 — all squash merged. Phase 56 cancelled, Phase 58 moved to backlog (999.6).
**Stats:** 249 files changed, +54835 / -1852 lines, 124 commits over ~12 days (2026-04-07 → 2026-04-19)

**Key accomplishments:**

- Endgame tab performance — 8 per-class timeline queries collapsed into 2, consolidated `/api/endgames/overview` serving every endgame chart in one round trip on a single AsyncSession, deferred filter apply on desktop (Phase 52)
- Endgame Score Gap & Material Breakdown — signed endgame vs non-endgame score difference plus material-stratified WDL table (ahead/equal/behind at endgame entry, later renamed Conversion/Parity/Recovery) with Good/OK/Bad verdict calibration (Phases 53, 59)
- Opponent-based self-calibrating baseline for Conv/Parity/Recov bullet charts — opponent's rate against the user replaces global average, muted when sample < 10 games (Phase 60)
- Time pressure analytics — per-time-control clock stats table (Phase 54) + two-line user-vs-opponents score chart across 10 time-remaining buckets with backend aggregation (Phase 55 + iteration via quick tasks)
- Endgame ELO Timeline — skill-adjusted rating per (platform, time-control) combination with paired Endgame ELO / Actual ELO lines, asof-join anchor on user's real rating, weekly volume bars for data-weight transparency (Phases 57 + 57.1)
- Conversion/recovery persistence filter — material imbalance required at endgame entry AND 4 plies later, threshold lowered 300cp → 100cp, validated against Stockfish eval analysis (Phase 48)
- Test suite hardening — `flawchess_test` TRUNCATE on session start, deterministic 15-game `seeded_user` fixture, aggregation sanity tests (WDL perspective, material tally, rolling windows, filter intersections, recency boundaries, within-game dedup, endgame transitions), router integration tests asserting exact integer counts (Phase 61)
- Admin user impersonation — superusers can impersonate any user via a new /admin page with shadcn Command+Popover search, single auth_backend + ClaimAwareJWTStrategy wrapper (zero call-site changes), last_login/last_activity frozen during impersonation, persistent impersonation pill in header with × to end session (Phase 62)
- Sentry Error Test moved from Global Stats to Admin tab; superuser-gated nav entry

---

## v1.9 UI/UX Restructuring (Shipped: 2026-04-10)

**Phases completed:** 3 phases (49-51), 7 plans, delivered via PRs #40, #41, #42
**Stats:** 57 files changed, +8692 / -1602 lines, ~21-hour execution window

**Key accomplishments:**

- Openings desktop sidebar — collapsible left-edge 48px icon strip + 280px on-demand Filters/Bookmarks panel with overlay/push behavior at the 1280px breakpoint, live filter apply on desktop
- Openings mobile unified control row — Tabs | Color | Bookmark | Filter lifted outside the board collapse region so controls stay visible when the board is collapsed; 44px tappable collapse handle; backdrop-blur translucent sticky surface
- Endgames mobile visual alignment — 44px backdrop-blur sticky row with 44px filter button matching the Openings mobile pattern (EGAM-01)
- Global Stats filters wired end-to-end — `opponent_type` and `opponent_strength` through `/stats/global` and `/stats/rating-history`, plus hooks/API client layer; bot games now excluded by default
- Stats subtab layout restructuring — 2-column Bookmarked Openings: Results on desktop (lg breakpoint), stacked WDLChartRows for mobile Most Played replacing the cramped 3-col table
- Homepage 2-column desktop hero — left=hero content, right=Interactive Opening Explorer preview (heading + screenshot + bullets), pills row removed, Opening Explorer removed from FEATURES list
- Global Stats rename — "Stats" → "Global Stats" across desktop nav, mobile bottom bar, More drawer, mobile header, plus new page h1; FilterPanel opponent controls enabled

---

## v1.8 Guest Access (Shipped: 2026-04-06)

**Phases completed:** 4 phases (44-47), delivered via PR #37
**Stats:** 56 files changed, +3915 / -1294 lines, 3 new test files (1193 lines of tests)

**Key accomplishments:**

- Guest session foundation — `is_guest` User model, JWT-based guest sessions with 30-day auto-refresh, IP rate limiting
- Guest frontend — "Use as Guest" buttons on homepage and auth page, persistent guest banner indicating limited access
- Email/password promotion — backend promotion service, register-page promotion flow preserving all imported data
- Google SSO promotion — OAuth promotion route with guest identity preservation across redirect, email collision handling
- Security fix — patched Google OAuth for CVE-2025-68481 CSRF vulnerability (double-submit cookie validation)
- UX polish — import page guest guard, auth page logo linking, delete button disabled during active imports

---

## v1.7 Consolidation, Tooling & Refactoring (Shipped: 2026-04-03)

**Phases completed:** 6 phases, 11 plans, 17 tasks

**Key accomplishments:**

- Astral `ty` static type checker integrated into CI — zero backend type errors, all functions annotated
- Knip dead export detection + `noUncheckedIndexedAccess` — zero dead code, strict TypeScript index safety
- Import pipeline ~2x faster — unified single-pass PGN processing, bulk CASE UPDATE, batch size 10→28
- SQL aggregation (COUNT().filter()) replacing Python-side W/D/L counting loops
- Consistent naming and deduplication — router prefixes, shared apply_game_filters, frontend buildFilterParams
- Dead code removal — 7 dead files deleted, unused shadcn/ui re-exports cleaned, -1522 lines
- CSS variable brand buttons (.btn-brand) replacing JS constant, typed Pydantic response models on all endpoints

---

## v1.6 UI Polish & Improvements (Shipped: 2026-03-30)

**Phases completed:** 6 phases, 11 plans

**Key accomplishments:**

- Centralized theme system with CSS variables, charcoal containers with SVG noise texture, brand subtab highlighting
- Shared WDLChartRow component replacing all inconsistent WDL chart implementations across the app
- Openings reference table (3641 entries from TSV) with SQL-side WDL aggregation and filter support
- Most Played Openings redesign: top 10 per color, dedicated table UI with minimap popovers
- Opening Statistics rework: smart default chart data from most-played openings, chart-enable toggles on bookmarks
- Mobile drawer sidebars for filters and bookmarks with deferred filter apply on close

---

## v1.3 Project Launch (Shipped: 2026-03-22)

**Phases completed:** 4 phases, 10 plans, 12 tasks

**Key accomplishments:**

- Full codebase renamed from Chessalytics to FlawChess across 20 files — PWA manifest, logo, GitHub org transfer
- Complete Docker Compose stack (FastAPI + Caddy 2.11.2 + PostgreSQL) deployed to Hetzner VPS with auto-TLS
- GitHub Actions CI/CD pipeline: test + lint + SSH deploy + health check polling
- Sentry error monitoring on backend (sentry-sdk[fastapi]) and frontend (@sentry/react) with Docker build-time DSN injection
- Public homepage with feature sections, FAQ, and register/login CTA; SEO meta tags, sitemap.xml, robots.txt
- Per-platform rate limiter (asyncio.Semaphore) protecting chess.com/lichess imports from concurrent bans
- Privacy policy page at /privacy; professional README with screenshots and self-hosting instructions

---

## v1.2 Mobile & PWA (Shipped: 2026-03-21)

**Phases:** 17–19 (3 phases, 5 plans)

Made the application work great on smartphones as an installable PWA with mobile-optimized navigation, touch interactions, and dev workflow for phone testing.

**Key accomplishments:**

- Installable PWA with service worker, chess-themed icons, and Workbox caching (NetworkOnly for API routes)
- Mobile bottom navigation bar with direct tabs and slide-up "More" drawer (vaul-based)
- Click-to-move chessboard on touch devices with sticky board layout on Openings page
- 44px touch targets on all interactive elements, no horizontal scroll at 375px
- Android/iOS in-app install prompts (beforeinstallprompt + manual iOS instructions)
- Cloudflare Tunnel dev workflow for HTTPS phone testing

---

## v1.1 — Opening Explorer & UI Restructuring

**Shipped:** 2026-03-20
**Phases:** 11–16 (6 phases, 15 plans)

Added interactive move explorer with W/D/L stats per position, restructured UI with tabbed Openings hub and dedicated Import page, enriched game import data, and redesigned game cards.

**Key accomplishments:**

- Move explorer with next-move W/D/L stats, click-to-navigate, transposition handling
- Chessboard arrows showing next moves with win-rate color coding
- UI restructured: tabbed Openings hub (Moves/Games/Statistics) + dedicated Import page
- Enhanced import: clock data, termination reason, time control fix, multi-username sync
- Game cards redesigned: 3-row layout with icons, hover/tap minimap showing final position
- Data isolation fixes, Google SSO last_login, cache clearing on auth transitions

---

## v1.0 — Initial Platform

**Shipped:** 2026-03-15
**Phases:** 1–10

Built the complete multi-user chess analysis platform: game import from chess.com/lichess, Zobrist hash position matching, interactive board with W/D/L analysis, position bookmarks with auto-suggestions, game cards, rating/stats pages, and browser automation optimization.

**Key capabilities:**

- Import pipeline with incremental sync (chess.com + lichess)
- Position analysis via precomputed Zobrist hashes (white/black/full)
- Position bookmarks with drag-reorder, mini boards, piece filter
- Auto-generated bookmark suggestions from most-played openings
- Game cards with rich metadata and pagination
- Rating history, global stats, openings W/D/L charts
- Multi-user auth with data isolation
