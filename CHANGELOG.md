# Changelog

All notable changes to FlawChess are documented here.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
with releases aligned to GSD milestones rather than individual phases. Dates are
in `YYYY-MM-DD` (Europe/Zurich).

## [Unreleased]

### Added

- **Conversion and Recovery gauges back in Endgame Type Breakdown** (Phase 98). Each endgame type tile (Rook, Minor Piece, Pawn, Queen) now shows its Conversion and Recovery gauges again, this time banded against the correct per-(class x time control) benchmark range so a bullet player is judged against bullet norms, not slow-game ones.

### Changed

- **Endgame Type Breakdown restructured into collapsible per-TC cards** (Phase 98). The 3-column grid of five per-type cards is replaced by full-width vertically-stacked accordion cards, one per time control (Bullet, Blitz, Rapid, Classical). Your primary time control (the one weighted by game count and typical duration) expands by default; others start collapsed. Mixed is no longer shown; each TC card with fewer than 20 games is suppressed. The accordion resets to your primary TC whenever you change filters.
- **Simpler Endgame Type Breakdown cards** (quick-260529-une). Each per-type card (Rook, Minor Piece, Pawn, Queen, Mixed) drops its Conversion and Recovery gauges, leaving the win/draw/loss bar, the type Score, and the Score Gap bullet. The Score Gap already captures conversion and defensive performance in a single engine-adjusted number, and the removed gauges were the only metrics on the card that shifted with time control, so they could mispaint a bullet player against slow-game expectations. AI insights still use the full conversion/recovery breakdown.

### Fixed

- **Endgame Type Breakdown showed "no data" despite a game count** (Phase 98). The per-time-control type cards displayed their header game count but an empty tile grid ("No endgame type data for this time control"). The per-(class x TC) breakdown was computed from one row per game classified by the *first* endgame position, which is almost always a mixed-material position, so nearly every game landed in Mixed (which the cards intentionally drop) and the Rook/Minor/Pawn/Queen tiles came up empty. It now aggregates the same per-class endgame spans the pooled stats use, and Mixed and pawnless are excluded from the computation so each card's header count equals the sum of its four tiles.
- **Endgames page locked forever for users with too few games** (quick-260529). A user with games but fewer than the 30-game per-time-control anchor floor (e.g. 13 imported games) produces no rating anchors and therefore no percentile rows by design, so the readiness gate kept the page on the "Analyzing endgames" screen permanently even after Stockfish finished. The gate now recognises a below-floor user as fully processed and unlocks the page once evals are drained, alongside the existing empty-account escape.

## [v1.20] Import Pipeline Hardening Follow-Up and Readiness — 2026-05-29

Two follow-ups to the v1.18 import hardening and v1.19 percentile work, regrouped into a milestone after the fact. Phase 95 closed the last thread of the FLAWCHESS-3Q out-of-memory family by switching the heaviest import write to a binary COPY. Phase 96 replaced the brittle "reload the page when Stockfish finishes" hack with an honest per-page readiness gate, so users land on already-correct openings immediately while endgame analysis finishes in the background.

### Added

- **Import readiness gate** (Phase 96). The app no longer force-reloads the page when background analysis finishes. On a first import you stay on the import screen, which now reads as a live state machine (fetching → importing → "Explore openings" → analyzing endgames X / Y → ready); openings unlock as soon as games are in, and an "Explore endgames" toast reaches you wherever you are once Stockfish eval and percentiles are done. On a later incremental import, Openings and Overview stay usable throughout and only the Endgames page waits, since partial-eval endgame stats would mislead. The Stockfish progress bar now shows on every page during analysis, and each eval-based Openings metric sits behind a pulsating placeholder until its data is ready instead of showing a half-computed value.

### Changed

- **Honest completion messaging and consolidated eval-progress UI** (Phase 96). No message claims full completion while Stockfish is still running. Eval progress is a single global header rather than scattered per-surface banners, and the running eval counter inside the per-metric tooltips was removed (the progress bar and placeholders carry that signal now).
- **Binary COPY for bulk position inserts** (Phase 95). The heaviest insert in the import pipeline (`bulk_insert_positions`) now uses asyncpg's binary `copy_records_to_table` instead of a parameterized multi-row `INSERT`, cutting per-connection Postgres memory during large dual-platform imports. This is the SEED-027 Thread B follow-up to the v1.19 container memory-budget hotfix (PR #144) and finishes closing the FLAWCHESS-3Q OOM family. Behaviour is unchanged; `bulk_insert_games` keeps its `ON CONFLICT DO NOTHING` path and the COPY enrolls in the same transaction so it rolls back atomically.
- **Percentile chip tooltip shows the matched rating anchor inline** (quick-260529-l1i). Each time-control breakdown row now displays the anchor it was matched against ("Bullet — anchored at ~1525 Lichess Elo"), and the separate platform-blend anchor note was dropped.

### Fixed

- **Percentile-compute query optimization** (quick-260529-cum). The five per-TC builders (`score_gap`, `achievable_score_gap`, `time_pressure_score_gap`, `clock_gap`, `net_flag_rate`) and their shared `endgame_entry_clocks` helper now scope `game_positions` aggregation to the selected user's recent games only. Previously each query scanned the full `game_positions` table and discarded nearly all rows in a later join. Cut is result-equivalent: only `recent_capped` games survive the downstream joins regardless. Addresses the ~6 s/call, ~58 min cumulative server time flagged by the /db-report for the import and eval-drain hot paths.

- **Stale Stage B percentiles after Stage-5c-covered imports** (quick-260527-u3u). The 7 eval-dependent percentile metric families (`achievable_score_gap`, `score_gap_conv`, `score_gap_parity`, `recovery_score_gap`, `clock_gap`, `net_flag_rate`, `time_pressure_score_gap`) now refresh on import completion when the user has no pending evals, not only on Stockfish cold-drain completion. Previously, an incremental import where every new game already carried lichess `%eval` annotations (Stage 5c marked them `evals_completed_at = NOW()` at import time) refreshed `score_gap` via the Stage A trigger but left the 7 eval-dependent families stale until the next drain tick on that user. The existing cold-drain trigger in `eval_drain.py` is unchanged; both sites are idempotent.

## [v1.19] Endgame Percentiles — 2026-05-27

The first peer-relative percentile chips on the Endgames page. The chip compares each user against same-rated-cohort peers (per-(metric, ELO anchor, TC) cohort CDFs built from the Phase 93 / 94.2 pooled benchmark cohort), making the percentile a stable *trait* of the user rather than a *view* of their currently-filtered data. Phases 93 + 94 shipped the underlying CDF + chip primitive (initial global-pool framing); Phase 94.1 made the chip filter-independent via a materialized `user_benchmark_percentiles` table; Phase 94.2 collapsed the per-cell stratified methodology into a one-point-per-user pooled model; Phase 94.3 extended chips to the Time Pressure cards (12 per-TC chips); Phase 94.4 pivoted the framing from global-pool to peer-relative cohort with rating-anchor disclosure and rescued Recovery Score Gap from the v1 drop list.

### Added

- **Recovery Score Gap chip slot on the Endgames page** (Phase 94.4). Rescued from the v1 drop list under peer-relative framing. Cohort comparison normalises the opponent-rating selection bias that drove the v1 drop, surfacing how a user recovers from material deficit vs other same-rated players.
- **Rating-anchor disclosure in the chip tooltip** (Phase 94.4). Tooltip bullet 4 discloses the per-platform anchor composition: mixed-platform users see "blending N chess.com games (median X, converted) with M lichess games (median Y)"; pure-platform users see a shortened single-platform form. chess.com ratings are converted to Lichess-equivalent via a hardcoded ChessGoals snapshot (2026-05-26).
- **Per-TC percentile chips on Time Pressure cards** (Phase 94.3). Each `TimePressureTcCard` (bullet / blitz / rapid / classical) now renders three chips on its header: Clock Gap, Net Flag Rate, and Time Pressure Score Gap. 12 new per-TC metrics added to `user_benchmark_percentiles` with the pooled-per-user methodology parameterised by TC. Net Flag Rate chips bind a `lower_is_better` direction (fewer net timeouts → higher percentile band).
- **Percentile annotations on 4 endgame ΔES rows** (Phase 94). A "Top X%" chip appears next to four metrics: Endgame Score Gap, Achievable Score Gap, Section 2 Conversion ΔES, Section 2 Parity ΔES. Banded color (red <25 / blue 25..75 / green >75), Radix popover with metric-aware copy. Backend gates each percentile at `n ≥ 10` (existing `PVALUE_RELIABILITY_MIN_N` reliability floor); chips don't render when the field is null. Raw % gauges (Conv/Parity/Recov), per-type cards, and any row below the floor keep their existing IQR zone bands and get no chip.
- **Global empirical-CDF benchmark artifact** (Phase 93). `app/services/global_percentile_cdf.py` ships the underlying CDF tables (p1..p99 breakpoints per metric) produced by `scripts/gen_global_percentile_cdf.py` against the benchmark DB. `/benchmarks` SKILL.md gains Chapter 4 documenting the methodology + SQL templates + report shape. Phase 94.4 later replaces the pooled `GLOBAL_PERCENTILE_CDF` with a per-(metric, ELO anchor, TC) `COHORT_PERCENTILE_CDF` family (~1,050 CdfTable instances under 50-Elo sliding-window protocol).
- **Materialized `user_benchmark_percentiles` table + two-stage compute** (Phase 94.1, 94.2). Each user's canonical-slice value and percentile per in-scope metric are persisted (PK widened to `(user_id, metric, time_control_bucket)` at Phase 94.4). Stage A computes the eval-independent `score_gap` at import-job completion (background task); Stage B computes the eval-dependent metrics (`achievable_score_gap`, `score_gap_conv`, `score_gap_parity`, `recovery_score_gap`, the 3 Time Pressure metrics × 4 TCs) at Stockfish cold-drain completion. Chips light up incrementally — `score_gap` is available within seconds-to-minutes of import completion, eval-dependent chips when cold drain wraps. `scripts/backfill_user_percentiles.py --target dev|prod` populates existing users on rollout.
- **`user_rating_anchors` table** (Phase 94.4). Per-(user, TC) rating anchor used to look up the user's cohort CDF cell. Anchor is the game-weighted blended median over the union of converted-chess.com + native-lichess game ratings, with full per-platform game counts and per-platform medians stored for tooltip disclosure. chess.com Daily games dropped at the SQL level.

### Changed

- **Endgame percentile chip pivoted from global-pool to peer-relative cohort framing** (Phase 94.4). The chip now compares each user against same-rated-cohort peers (per-(metric, ELO anchor, TC) cohort CDFs, K=200 sliding windows at 50-Elo anchors). Chip face shrinks to a bare `p23` pill (no flame icons, no direction word); color band (red <25 / neutral / green >75) carries direction. 2400-rated users no longer see globally-low percentiles that misframe honest skill; the percentile is now relative to other 2400s. Tooltip rewrites to a 4-bullet peer-relative form including rating-anchor disclosure.
- **Percentile chip is a trait, not a view** (Phase 94.1). Toggling Recency / Opponent Strength / TC / Platform / Rated / Opponent Type filters no longer changes the chip — it reflects the user's canonical-slice value computed once per Stage A/B trigger from a fixed cohort definition (status='completed' + ±100 ELO opponent at game time + sparse-cell exclusion + 36-month recency + standard variant). The row's filter-applied metric value continues to display per the existing per-request compute; the chip stays still.
- **Pooled-per-user methodology** (Phase 94.2). Phase 94.1's per-cell stratified methodology is replaced with a one-point-per-user pooled model on both the CDF construction side and the per-user lookup side. Games are pooled across TCs (cap 1000/TC, ≤36 months) and the metric is computed once per user; the CDF is `percentile_cont` over those values. Single ≥30-games inclusion floor on the pool.
- **Percentile chip anchor: game-weighted blended median for mixed-platform users** (Phase 94.4 amendment, D-12 reversal). Per-game ChessGoals conversion for chess.com + native passthrough for lichess, pooled median over the union. Mixed-platform users now see an anchor that reflects their full play distribution, not just their lichess ladder position. Pure-platform users are unaffected (median commutativity within the ChessGoals snapshot). See `.planning/notes/percentile-anchor-d12-reversal.md` for the rationale.
- **`ScoreGapRow` layout** (Phase 94). Non-`hasSlots` callers now render via CSS Grid so the new percentile chip can sit at the right edge of the value row on desktop (≥640 px) and on its own line below the bullet chart, left-aligned, on mobile (<640 px). `EndgameTypeCard`'s 3-column variant (`hasSlots`) is unchanged.

### Fixed

- **Postgres container memory budget** (hotfix PR #144, FLAWCHESS-3Q recurrence). Third post-v1.18 occurrence of the same OOM family: user 109's concurrent chess.com + lichess import on 2026-05-26 14:18-14:24 UTC OOM-killed Postgres inside its 10 GB container cgroup. Root cause was a docker-compose misalignment introduced by PR #139, Postgres remained tuned for the 16 GB host (`shared_buffers=4GB`, `effective_cache_size=12GB`) while the container was capped at 10 GB, leaving only ~6 GB of cgroup budget for per-backend work. With 20 active backends during the dual-platform bulk INSERT burst, that budget was exhausted. Hotfix re-tunes Postgres to the container budget and raises the cap: `shared_buffers` 4GB → 2GB, `effective_cache_size` 12GB → 8GB, `mem_limit` / `memswap_limit` 10g → 12g. Per-backend anon-rss headroom grows from ~6 GB to ~10 GB. Also bumps `starlette` 0.52.1 → 1.1.0 to clear PYSEC-2026-161 (transitive dep, surfaced by the CI pip-audit gate). See SEED-027 for Thread B (asyncpg COPY for bulk position insert), which addresses the per-backend pressure side directly and ships as a parallel small phase.

## [v1.18] Import Pipeline Hardening — 2026-05-22

Reactive milestone driven by two production OOM recurrences after v1.17 (FLAWCHESS-56 on 2026-05-16, FLAWCHESS-3Q on 2026-05-21). Phase 90 eliminated the per-batch unique-SQL leak in `_flush_batch` Stage 5 and shipped DB-recovery retry plus a periodic orphan-job reaper. Phase 91 split the import pipeline into two lanes so Stockfish eval no longer blocks the hot path — users see opening explorer, raw WDL, and flag rates within seconds of import start, with eval-dependent metrics filling in via a background cold-drain coroutine. Phase 92 replaced the closed `Recency` string union on the API wire with explicit `from_date` / `to_date` params and added a Custom range… picker. Hotfix PR #139 capped the SQLAlchemy pool, Postgres `max_connections`, and container memory; the production host was upgraded from Hetzner CPX32 to CPX42 (8 vCPU / 16 GB RAM).

### Added

- **Custom date range filter** (Phase 92). A 9th "Custom range..." item in the Recency dropdown opens a two-month range Calendar on desktop (Radix Popover anchored to the Select trigger, auto-closes on full range pick) and a single-month Calendar in a nested Vaul bottom sheet on mobile (Apply CTA, backdrop = cancel). The trigger label updates to the resolved date range once both bounds are set.
- **Eval-coverage banner + per-metric pending caveats** (Phase 91). New `useEvalCoverage` hook polls `GET /api/imports/eval-coverage` every 10 s while Stockfish work is outstanding and stops automatically at 100%. An amber progress banner appears at the top of Endgames Stats, Openings Stats, Openings Explorer, and Openings Insights while engine coverage is incomplete. Stockfish-dependent metric popovers show an AlertTriangle-icon caveat citing the metric's current sample size and the remaining pending count.
- **Dual-import stress harness** (Phase 91). `scripts/measure_dual_import_rss.py` — dev-only acceptance gate that triggers two concurrent imports, polls Postgres + RSS + swap + coverage every 30 s, and exits non-zero on any bound violation.
- Openings and Endgames *Games* subtabs now show the Score and Eval bullet charts below the WDL chart, matching the move explorer's "Results played as" panel. The Endgames Games subtab reports per-category Wilson score and the eval at endgame entry.
- Endgame Type Breakdown cards now show per-type Start and End predicted scores flanking the Gap row (Start on the left with a Cpu icon, Gap centered with its info popover, End on the right). End − Start reconciles exactly with the Gap.

### Changed

- **Two-lane import pipeline** (Phase 91). The import hot path no longer runs Stockfish. Game ingestion (fetch → parse → insert positions → commit) is now eval-free, and a separate in-process cold-drain coroutine (`run_eval_drain`, spawned in the FastAPI lifespan alongside the orphan-job reaper) evaluates entry plies in the background. Opening explorer, raw WDL, endgame type breakdowns, flag rates, and time-per-move are available within seconds of import start; conversion, recovery, score-gap, and time-pressure-vs-performance metrics fill in over the following minutes with honest per-metric sample-size labels. Structurally prevents the 2026-05-16 / 2026-05-20 hot-lane-Stockfish OOM regression — a CI regression guard (`TestHotLaneNoEvalCalls`) fails the build if any future edit reintroduces `engine.evaluate` inside `_flush_batch`.
- **API filter shape** (Phase 92). The closed Recency string union (`week` / `month` / `3months` / `6months` / `year` / `3years` / `5years` / `all`) on the wire is replaced by two optional ISO date params `from_date` / `to_date`. The frontend converts preset labels to dates in the user's local timezone via a shared `presetToDates` utility. Internal LLM windowing (`insights_service.py`) preserves existing semantics via fixed date offsets independent of the dashboard filter.
- **Production OOM hardening + Hetzner CPX42 upgrade** (hotfix, FLAWCHESS-3Q). SQLAlchemy pool reduced from `pool_size=20, max_overflow=30` (50 max) to `10 + 10` (20 max) in `app/core/database.py`. Postgres `max_connections` capped at 30 (was the upstream default of 100). Host upgraded from Hetzner CPX32 (4 vCPU / 7.6 GB RAM) to CPX42 (8 vCPU / 16 GB RAM); Postgres memory settings retuned accordingly (`shared_buffers=4GB`, `effective_cache_size=12GB`, `work_mem=16MB`, `maintenance_work_mem=512MB`). Backend, db, and umami containers given explicit `mem_limit` (4g / 10g / 384m) with `memswap_limit = mem_limit` on backend and db to disable swap and force a contained OOM-restart (~3 s Postgres auto-recovery) instead of host-wide swap thrash. Root cause of the 2026-05-21 13:42 Postgres OOM (job 72a4ca0d, single chess.com import for user 101) was the post-Phase-91 fetch rate doubling, which let a single uvicorn process fan out to 13 active Postgres backends and exhaust host RAM + 4 GB swap.
- The Eval popover on the Endgames Games subtab now reads "average Stockfish eval at the position where the endgame begins" (instead of the openings phrasing), matching the Stats-tab "Endgame Entry Eval" metric.
- **Score Gap by Remaining Time tooltip splits You/Opp game counts** (post-v1.17 polish). The per-bucket hover tooltip now shows your score and your opponents' score on two separate lines, each with its own game count (`You: 38.0% (40 games)` / `Opp: 55.0% (37 games)`). The two figures come from independent clock-pressure splits of the same game-set, so the counts can legitimately differ; the previous single line showed only one count.
- **Time Pressure card help moved to per-section info popovers** (post-v1.17 polish). The single card-title info popover is gone. Each of the two sections now carries its own info trigger next to its subtitle: "Remaining Time at Endgame Entry" explains the pre-endgame time-management stats and net flag rate; "Score Gap by Remaining Time" explains the same-pressure opponent comparison and what the marker size encodes (how many of the bucket's games were yours).
- **Score Gap by Remaining Time markers scale with your sample size** (post-v1.17 polish). Each datapoint dot is now sized by the user/opponent game-count ratio (`n / n_opp`), clamped to a capped range. A bigger marker means more of that bucket's games were yours, so the user-side score is the better-sampled side of the comparison.
- **Endgame chart axis/tooltip label consistency** (post-v1.17 polish). The "Score Gap by Remaining Time" x-axis caption now renders as an HTML caption matching the "Clock Gap at Endgame Entry" chart, so it is the same size on mobile. The Clock Gap chart's datapoint tooltip label was renamed "Avg clock diff" → "Clock Gap" to match the metric name used elsewhere.

### Fixed

- **Import pipeline OOM root cause** (Phase 90, FLAWCHESS-56 / FLAWCHESS-3Q). The 2026-05-16 production OOM-kill is closed out by eliminating the per-batch unique-SQL leak in `_flush_batch` Stage 5: the old `case()+IN` UPDATE, whose SQL text varied with every game-id set, is replaced by two `bindparam` executemany groups against `Game.__table__` whose SQL text is invariant across batches. SQLAlchemy's compile cache and asyncpg's prepared-statement LRU no longer grow unboundedly during long imports. Locally verified: post-warmup RSS plateau at 577 MB across +1044 games (≈0 MB/game), vs the pre-fix ~0.48 MB/game linear growth.
- **Per-batch session scoping** (Phase 90). `run_import` is restructured into three `AsyncSession` scopes — bootstrap, per-batch, completion. The identity map, transaction state, and per-connection statement cache are now released after every batch, capping the secondary accumulation surface alongside the Stage 5 fix.
- **DB-recovery window no longer strands import jobs** (Phase 90). Adds a bounded-retry helper (`_record_failure_with_retry`, 5 attempts, 2/4/8/16 s backoff with `engine.dispose()` pool invalidation between retries) so a brief Postgres restart no longer leaves a job stuck `in_progress`. The retriable-error classifier covers `sqlalchemy.exc.OperationalError`, `InterfaceError`, `DBAPIError`, raw asyncpg `CannotConnectNowError` / `ConnectionDoesNotExistError`, and OS-level `ConnectionRefusedError`. Sentry capture fires only on final exhaustion (last-attempt rule).
- **Periodic orphan-job reaper** (Phase 90). A new background task (`run_periodic_reaper`, 5-minute tick, 3-hour age threshold) wired into the FastAPI lifespan picks up any `in_progress` job left stranded by an outage longer than the retry budget. `fail_orphaned_jobs` accepts an `orphan_age_threshold` so the reaper does not touch live healthy imports; the startup-time call is unchanged (no threshold).

### Removed

- **Bookmark time-series `recency` field** (Phase 92, D-19). The `TimeSeriesRequest` schema and its corresponding frontend type no longer accept a `recency` field. The time-series endpoint always covers the full game history; the field was unused at the UI call boundary.

### Security

- Bumped transitive dependency `idna` 3.11 → 3.15 to clear CVE-2026-45409 (flagged by the CI `pip-audit --strict` gate). Lockfile-only; no behavior change.

### Tests

- **Real-DB regression coverage for the import pipeline** (Phase 90). New `TestFlushBatchStage5RealDb` (rollback-scoped `db_session` fixture) pins the Stage 5 Table-level executemany contract against actual SQLAlchemy execution; the previous mock-only tests could not catch the ORM bulk-update fragility this PR resolves. New `TestRecordFailureWithRetryDbOutage` (6 tests) pins each retriable exception class plus the pool-invalidation and dispose-failure-resilience contracts.
- **Date-filter boundary integration tests** (Phase 92). Seven new tests cover `from_date` inclusive lower bound, `to_date` inclusive-of-full-day upper bound, game exclusion for dates past `to_date`, no-filter pass-through, 422 validation on `from_date > to_date` via the Pydantic body path (POST /openings/positions) and via the inline HTTPException path (GET /stats/global), and the insights LLM gate blocking message "Clear Custom date range filter" when any date filter is active.

## [v1.17] Endgame Stats Card Redesign — 2026-05-19

### Added

- **Inactivity-gap annotations on all timeline charts** (Phase 88.3). Every ordinal-by-activity timeline chart now marks long inactive stretches with a palm-tree break glyph plus a compact label ("1.1y", "3mo") at each gap longer than 8 weeks, so a flat stretch on the x-axis no longer reads as continuous play. Applied consistently to six charts: Endgame Score Gap over Time, Endgame ELO Timeline, Bookmarked Openings Score over Time, Average Clock Gap over Time, and the Chess.com and Lichess rating charts. Charts with no long gap are unaffected.
- **Endgames page: restored the "Average Clock Difference over Time" line chart** (Phase 88-15, post-UAT polish). Plots the rolling 100-game mean of (your clock minus opponent's clock) at endgame entry, per ISO week, with per-week game volume bars behind the line and three zone-tinted bands (danger / neutral / success). White line with zone-colored dots. Y-axis auto-expands past the ±30% baseline when a real point would otherwise sit at the edge. Vertical "Clock diff %" Y-axis label on desktop (hidden on mobile). Sits ABOVE the Time Pressure cards grid so the trend story reads first and the per-TC cards act as drilldown. User-approved scope amendment to ROADMAP Phase 88 SC #1 ("replace the line chart with bullet cards"): the bullet-card grid is retained as the primary surface, and the line chart returns alongside as a complementary trend view that the cards (a single time-window snapshot) cannot show.
- **Endgame Type Score Gap row on each per-type card** (Phase 87.1). Each Endgame Type Breakdown card (rook, minor piece, pawn, queen, mixed) gains a new "Score Gap" row showing the average per-span gap between exit score and Stockfish-baseline expected score at span entry. Positive means the user outperformed expectation in that endgame type; negative means they gave back expected score. The new row uses the same `ScoreGapRow` bullet primitive as the page-level Achievable Score Gap (Phase 85.1), with per-class typical bands and a `MetricStatPopover` info trigger. LLM Insights now references the per-type Score Gap per class; prompt version bumps `endgame_v28` → `endgame_v29` to invalidate cached reports so newly generated narration uses the new metric.
- **Endgame Type Breakdown: 5 per-type cards** (Phase 87). Replaces the grouped `EndgameWDLChart` and the gauge-only `EndgameConvRecovChart` with a new "Endgame Type Breakdown" section: 5 per-type cards (rook / minor_piece / pawn / queen / mixed; pawnless hidden) in a 1 / 2 / 3-col responsive grid. Each card carries side-by-side Conv + Recov gauges (per-class p25/p75 bands from `PER_CLASS_GAUGE_ZONES`), a WDL bar (toggle `SHOW_WDL_BAR_IN_TYPE_CARDS`), a Games deep-link to `/endgames/games?type=<slug>`, and a per-class chess-score bullet ((W + 0.5·D)/N vs 50%, Wilson 95% whiskers, Wilson score-test p-value gating the sig-paint triple). The page-level h2 carries an `InfoPopover` covering the taxonomy, Conv/Recov definitions, gauge-band explainer, and per-type one-sentence descriptions. `?type=<slug>` URL hydration pre-seeds the type filter on direct visits and SPA navigations. Design deviation: the original SC1 called for two peer bullets per card (Conv peer diff + Recov peer diff); these were collapsed into a single chess-score bullet because the mirror identity (`oppConv = recovery_losses/recovery_games` and its symmetric Recov counterpart) makes the two bullets render the same magnitude — two rows, one signal. Backend exposes `EndgameCategoryStats.score_p_value: float | None` (null when `total < PVALUE_RELIABILITY_MIN_N` = 10).
- **Endgame Score Differences: hypothesis tests + 95% CI whiskers** (Phase 85.1). The Endgame Score Gap (Endgame Score − Non-Endgame Score) and the Achievable Score Gap (Endgame Score − Achievable Score) now report a two-sided p-value vs 0 and a 95% CI on the difference. CI whiskers render around the bullet on both `ScoreGapRow` rows. Achievable Score Gap is now server-computed from per-game `(actual, expected)` pairs via a paired one-sample z-test (replaces the previous client-side `endgame_score − achievable_score` derivation). Independent n-gates apply per signal: p-value gated to None when `n < 10`; CI gated to None when `n < 2`. Font coloring stays zone-only (Phase 85 D-04 kept) — the CI whiskers carry the new uncertainty signal.

### Changed

- **Time Pressure cards redesigned for readability** (Phase 88.4). The per-time-control Time Pressure cards now use a responsive grid (full-width 3×1 or 2×2 with multiple cards, half-width with a single card, no horizontal scroll at any width). "Remaining Time at Endgame Entry" is now a single three-stat header row directly above the Clock Gap bullet — your time left, the gap (with its info popover), and your opponent's time — with Net flag rate unchanged below. The four stacked per-bucket "Score Gap by Remaining Time" bullets are replaced by one zone-banded, zero-centered line chart across the four time-pressure buckets, with confidence-interval whiskers on each point and the per-bucket numbers surfaced in a hover tooltip (the old per-bucket info icons are gone). Same underlying numbers, clearer layout.
- **Endgame ELO Timeline now defaults to your most-active series** (Phase 88.3). On first render the chart shows only the single most-active (platform × time-control) series instead of stacking several at once; every other series stays one click away in the existing legend. No tabs added; behaviour is unchanged when only one series exists.
- **"Endgame Overall Performance" restructured into one responsive card** (Phase 88.3). The arrow-flow layout and the empty black flanking boxes are gone, replaced by a single bordered card: two equal-height columns split by a vertical divider on desktop ("Games without / with Endgame" and "Eval at Endgame Entry / Endgame Score Differences"), stacking with horizontal dividers on mobile. Pure layout change, no metric or chart-content change.
- **Time Pressure cards: restored the per-card top zone with my avg clock time, opp avg clock time, and net flag rate** (Phase 88-14). User-approved scope amendment to Phase 88 SC #1: these three stats were deleted with the old Time Pressure at Endgame Entry table in Phase 88-07 and are now restored on each per-TC card as a top zone above the quintile bullets. The Clock Gap bullet sits in the same top zone; a thin horizontal separator divides the zone from the per-quintile score-delta bullets below. The net flag rate cell zone-tints green or red when it crosses the calibrated `NEUTRAL_TIMEOUT_THRESHOLD` (5%), and renders an em-dash when no game in the time control has clock data.
- **Time Pressure cards: qualitative labels, hidden 80-100% bin, wider axis, separate per-TC containers** (Phase 88-13). The per-quintile rows on each Time Pressure card now use qualitative names — post-UAT relabel format is "0-20% | High Pressure", "20-40% | Medium Pressure", "40-60% | Low Pressure", "60-80% | Very Low Pressure" (range reads first, qualitative as an annotation). The 80-100% clock-remaining bin is intentionally hidden as a low-signal tail (backend keeps computing it; the filter is frontend only). The score-delta bullet axis widens from ±20% to ±30% so real-world deltas exceeding ±20% are no longer clipped (the ±0.06 neutral band is unchanged, so the colored side-zones grow). Each TC card now sits in its own charcoal container instead of being nested inside an outer section wrap. Post-UAT structural refinements layered on top: time-control icon next to the TC label in the card title, "Remaining Time at Endgame Entry" subtitle on the top section, "Score by Remaining Time" subtitle on the quintile-bullets section, redundant `(N games)` suffix dropped from the Clock gap row, MiniBulletChart bars rendered with `barColor="neutral"` to match the Endgame Type / Opening Stats cards.
- **Calibrated time-pressure card zones** (Phase 88.8). `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` (4 TC × 5 quintiles = 20 cells) and the `clock_gap_pct` neutral band are now set from the Lichess benchmark cohort (2026-05-17 snapshot, n=1,743–1,912 users depending on cell). Bands are pooled across ELO inside each (TC, quintile); the ELO gradient inside the band surfaces as visibly higher (greener) values for stronger players, which is the intended behavior — stronger players score better against their opponents at every TC. Cap of ±0.06 half-width applied symmetrically around p50 (activated in 12 of 20 cells). `clock_gap_pct` band updated from symmetric ±5% to the calibrated asymmetric (−6.5%, +4.7%) because users tend to enter endgames with a slight clock deficit.

- **Phase 87.6: Endgame ELO Timeline hides rarely-played combos by default.** With up to 8 platform/TC combinations on one chart the timeline got crowded. The chart now defaults to showing the top 3 combos by total games, after filtering out combos whose active weeks fall below 33% of the leader's active weeks (active week = ISO week with at least one qualifying endgame game). Active-weeks-not-games as the denominator keeps a legitimately co-played rapid/classical line from being drowned out by bullet/blitz volume. Hidden combos still appear in the legend (dimmed + line-through) and can be re-activated by clicking; switching filters resets the default.
- **Phase 87.6: Endgame ELO and Non-Endgame ELO now sit symmetrically around your Actual ELO.** Amends the initial Phase 87.6 FIDE Performance Rating mapping (UAT against prod showed it violated the "Actual ELO surrounded by the two lines" invariant in ~88% of weekly points because the 100-game trailing PR estimator lagged the live Glicko snapshot). Both sides are now derived from a logistic stretch around Actual ELO — `endgame_elo + non_endgame_elo == 2 * actual_elo` for every emitted point. The "lifting / holding back" sign convention and the Non-Endgame ELO data point introduced in 87.6 are preserved; the chart popover and LLM glossary are rewritten to drop Performance Rating framing. Prompt version bumps `endgame_v34` → `endgame_v35` to invalidate cached reports.
- **Phase 87.5: Endgame ELO Timeline rebuilt on Endgame Score Gap.** The timeline now uses an additive formula `endgame_elo = round(actual_elo + K · eg_score_gap)` where `eg_score_gap` is the per-week windowed difference between endgame and non-endgame game scores (the same series that drives the Endgame Score Gap over Time chart). This replaces the Phase 87.4 Conv ΔES + affine recenter input and the Phase 57 multiplicative formula, eliminating the sigmoid bias that caused strong players' chart values to diverge from actual ELO by hundreds of points (benchmark §3.2.2 Conv ΔES ELO Cohen's d = 1.62 vs §3.1.6 Endgame Score Gap d = 0.17). At `eg_score_gap = 0` the chart shows the value equal to Actual ELO; positive Endgame Score Gap means your endgame is lifting your rating, negative means it is holding it back. The chart is renamed back to "Endgame ELO Timeline" and relocated from the "Endgame Metrics and ELO" section to "Endgame Overall Performance", directly below the "Endgame Score Gap over Time" chart. LLM Insights updated end-to-end; prompt version bumps `endgame_v32` → `endgame_v33` so prior cached reports regenerate with the restored "lifts up / holds back" framing. See `.planning/notes/endgame-elo-rebuild-on-score-gap.md` for the full rationale.
- **Phase 87.4: Endgame ELO Timeline renamed to Conversion ELO Timeline.** The timeline is now fed by the Conversion Score Gap (Phase 87.2) routed through a frozen affine recenter into the unchanged Phase 57 formula. Conversion ELO answers: what your ELO would be if everyone played the way you do when up material. LLM Insights prompt updated end-to-end; prompt version bumps `endgame_v31` → `endgame_v32` so prior cached reports regenerate with the new framing. See `.planning/notes/endgame-skill-dropped-conversion-elo.md` for the full rationale.
- **Phase 87.4: Conversion, Parity, and Recovery Score Gap bullets are now display-centered on the typical-population result.** A display-only affine shift is applied to each bullet (Conversion −0.055, Recovery +0.06, Parity 0) so a player at the cohort midpoint renders at the chart center instead of the top of the band. Underlying LLM zone bands, cohort thresholds, and zone-color cutoffs are unchanged.
- **Phase 87.2: Section 2 cards (Conversion, Parity, Recovery, Endgame Skill) now show a per-bucket Score Gap bullet anchored to the Stockfish baseline instead of the previous rate-based peer-diff bullet.** Conversion shows score gap on spans you entered ahead; Recovery on spans you entered behind; Parity on balanced spans; Skill is the equal-weighted average of the three. Auto-generated endgame insights reference the new Section 2 Score Gap family.
- **Endgame Stats: concept terminology title-cased.** The "Endgame statistics concepts" panel and every reference to the panel's terms across the Endgames Stats page (concept accordion, info popovers, aria-labels, headings, gauge labels, Home page FAQ) now uses title case for the named concepts: Endgame Phase, Endgame Type(s), Endgame Sequence, Endgame Entry Eval, Achievable Score, Endgame Score, Non-Endgame Score. The LLM Insights prompt is updated to match (UI-label table + glossary + prose) and the prompt version bumps `endgame_v27` → `endgame_v28` to invalidate cached reports so newly generated narration uses the capitalized terms.
- **Endgame "Overall Performance" section redesigned as 3-card composite (Phase 85).** Replaces the legacy `EndgamePerformanceSection` table and the "Start vs End" twin-tile layout with three cards: "Games ending in Middlegame" (WDL + score), "At Endgame Entry" (entry eval + Stockfish achievable score, no WDL), and "Endgame results" (WDL + score). The Endgame Score Gap tile sits under Card 2 on desktop and stacks at the bottom on mobile. Card scores use sig-gated tinting (Wilson confidence on n>=10 cohorts) and per-row info popovers explain Endgame Score Gap and Achievable Score Gap. Backend exposes `non_endgame_score_p_value` alongside the existing endgame p-value for symmetric gating.

### Removed

- **Phase 87.4: Endgame Skill concept dropped end-to-end.** No composite definition (arithmetic mean, percentile composite, rate aggregate) survived scrutiny on cohort de-confounding, individual absolute-skill interpretation, per-window temporal stability, and the Phase 57 median-coincide invariant. The Endgame Skill card, the Skill Score Gap card, the `endgame_skill` / `section2_score_gap_skill` LLM payload findings, and the Endgame Skill glossary entries in the LLM prompt are all removed. The Conversion ELO Timeline now stands in as the headline composite measure of endgame strength. See `.planning/notes/endgame-skill-dropped-conversion-elo.md` for the full rationale.
- **Phase 87.2: Rate-based peer-diff bullet on Section 2 cards (the `You / Opp / Gap` row).** The prior framing produced mathematically identical Conversion and Recovery values by construction; the new Stockfish-anchored framing yields genuinely independent per-bucket signals.

### Fixed

- **Game imports could fail or hang during large/concurrent imports.** A Postgres OOM-kill mid-import (driven by an oversized import batch size combined with the per-batch Stockfish evaluation pass) could drop the database connection, failing the import and in some cases leaving the job stuck "in progress". Reduced the import batch size and per-engine memory, and raised production swap, to keep imports within the server's memory budget. Hotfix shipped via the new GitLab Flow `production` branch. (Further resilience improvements — automatic recovery of stuck jobs and prevention of duplicate concurrent imports — are tracked as a follow-up.)
- **Opening Insights query plan regression for small users.** The `query_opening_transitions` standard-start filter used a correlated `EXISTS` subquery. For users with a few hundred games the planner picked `ix_gp_user_white_hash` for the inner scan (only `user_id` as index cond, row-by-row filter on `ply=0 AND full_hash=STARTING_HASH`), scanning ~25k rows per outer row × ~8k outer rows ≈ 188M shared buffer hits and ~88 s wall time. Heavy users (~20k+ games) coincidentally landed on `ix_gp_user_full_hash_move_san` and ran in ~1 s. Rewriting as an explicit `INNER JOIN` to a subquery pins the planner to the right index for both regimes: ~65 ms on the 499-game test user, equal-or-faster on a 23k-game user (928 ms vs 988 ms warm-cache).
- **Opening Insights timeout fully resolved via planner extended statistics.** PR #89's JOIN-over-EXISTS fix addressed index choice on a 499-game test user but left a separate planner pathology on adjacent cardinality bands (e.g. user 84 with 718 games / ~50k positions, 137 s wall time, 400M shared buffer hits). The PG planner estimated `rows=1` for `(user_id=X, ply BETWEEN 0 AND 17)` because column-level stats treat `user_id` and `ply` as independent, which cascaded into Nested Loop joins at every level of the opening transitions query. Two `CREATE STATISTICS ... (dependencies, ndistinct, mcv)` objects on `game_positions (user_id, ply)` and `games (user_id, user_color)` give the planner correct cardinality (12,834 rows estimated vs `rows=1` before), which flips the cascading Nested Loops into Index Scans on the primary key. Same query goes from 137 s → 36 ms (~3,800× speedup). No code or index changes; pure statistics fix shipped as Alembic migration `e925558020b9`.

## [v1.16] Stockfish Eval Analyses — 2026-05-11

Downstream consumers of v1.15's Stockfish eval substrate (endgame span-entry + middlegame-entry `eval_cp` / `eval_mate` on `game_positions`). Adds opening-stats eval bullets with t-test confidence, transposition-inclusive Move Explorer + Opening Insights WDL, the Endgame Start vs End twin-tile section with 2×2 grid for Stockfish-baseline achievable score, and LLM narration of all three new metrics. Five phases (80, 80.1, 81, 82, 83) shipped via PRs #80, #82, #85, #86, #88.

### Added

- **Endgames: Stockfish-baseline achievable score** (Phase 83): the "Endgame Start vs End" section restructures into a 2×2 grid. Tile 1 "Where you start" gains a second row showing each user's mean **achievable score** at endgame entry: the Lichess winning-chances sigmoid applied to the Stockfish eval at the first endgame ply (mate positions map directly to 0 or 1, mate-INCLUDED), aggregated per user, sig-tested against 50% via the same Wilson code path as Tile 2's achieved score. Tile 2 "What you do with it" gains a top-row mini WDL bar; bottom row stays the existing W+0.5D score bullet. The two bottom rows share the same axis (`SCORE_BULLET_CENTER`) and cohort band (`[0.45, 0.55]`, calibrated from `reports/benchmarks-2026-05-11.md` §7), so the **achievable-vs-achieved gap** reads directly across the two tiles — a user can see "the engine baseline predicts 49% from these positions, you scored 52%" at a glance. Backend `EndgamePerformanceResponse` gains five `entry_expected_score*` fields. LLM narrates the new metric from day one (`_PROMPT_VERSION` bumped to `endgame_v25`, new "Achievable score" vocab entry, gap framing). New shared `app/services/eval_utils.py` module (Lichess sigmoid + mate→0/1, no business logic). New `ENTRY_EXPECTED_SCORE_ZONES` registry entry; `entryExpectedScoreZoneColor` codegen'd to `frontend/src/generated/endgameZones.ts`.

- **Endgames: "Endgame Start vs End" twin-tile section** (Phase 81): new section above the existing Endgame Overall Performance WDL table renders two tiles — Tile 1 "Where you start" (avg Stockfish eval at endgame entry, in pawns from your perspective, sig-tested against 0 via Wald-z) and Tile 2 "What you do with it" (absolute endgame score, sig-tested against 50% via Wilson score test). Both tiles use three-state color (sig positive → green, sig negative → red, not sig → neutral) at p<0.05 and reuse the Openings score-bullet visual. The concept-explainer accordion gains paragraphs for both new tested metrics with "we can't tell" framing for non-significant results. Mobile: tiles stack with entry-eval first (chronological setup → execution); per-tile chart drops below the label-row for full-width readability. Backend `EndgamePerformanceResponse` gains six fields (entry-eval mean, n, p-value, CI low/high, endgame-score p-value); aggregation runs against bucket_rows so `entry_eval_n + mate_excluded + null_excluded == endgame_wdl.total` by construction. WDL table, Score Gap column, and time-series chart unchanged.

- **Endgame Insights LLM narrates "Endgame Start vs End" tiles** (Phase 82): the LLM-generated Endgame Overall Performance narration now mentions both Phase 81 tiles, `entry_eval_pawns` ("where you start") and `endgame_score` ("what you do with it"), alongside the existing Conv / Parity / Recovery and score-gap-timeline narration. The pair frames as "setup → execution"; the prompt cross-links to the Time Pressure section so a user with strong entry-eval but weak endgame-score reads as "may be losing on the clock, not the board". Closes the gap left by Phase 81 (which shipped the visible tiles but not the LLM hookup). Internal: a new `endgame_start_vs_end` subsection in the insights pipeline; `_PROMPT_VERSION` bumped to `endgame_v23` (auto-invalidates v22 caches).

- **Openings: Stats subtab** (Phase 80): five new column cells on bookmarked-openings and most-played-openings tables -- average Stockfish evaluation at middlegame entry (signed from your perspective, with 95% CI whisker on a bullet chart), one-sample t-test confidence pill for the middlegame metric, average clock difference at middlegame entry (% of base time + absolute seconds), average Stockfish evaluation at endgame entry (parallel bullet chart with its own wider domain), and a separate confidence pill for the endgame metric. Outlier evaluations (>= 20 pawns) are trimmed from the means. Mobile rows get two stacked lines: middlegame triple (bullet + pill + clock-diff) and endgame pair (bullet + pill). The chess board is hidden on the Stats subtab on desktop to make horizontal room.

### Changed

- **Openings significance discipline + neutral bullet bars + grey neutral arrows** (quick task 260508-dcp): on every Openings subtab, Score % and Stockfish eval text only render in zone color (red/green) when the value falls in the red/green zone AND the result is in a confident bucket (confidence is `'medium'` or `'high'`, not `'low'`); otherwise it reads in the default foreground. The gate keys on the categorical confidence bucket so the underlying p-value thresholds in `scoreConfidence.ts` can move without touching every call site. Bullet-chart bars on the Openings Moves "current position" panel and across all three Endgames Stats sections (WDL, Performance, Score Gap) now use the neutral light-grey bar mode that was already applied on the Stats and Insights cards. The categorical "neutral" Move Explorer board arrow (used for the in-between band, low-data, or low-confidence rows) was recolored from blue to a transparent grey so reliable red/green arrows dominate visually.
- **Code organization** (Phase 80): extracted `<ConfidencePill>` to a shared component (used by Opening Insights cards and the new Openings Stats columns) and extracted clock-formatting helpers (`formatSignedSeconds`, `formatSignedPct1`) to `frontend/src/lib/clockFormat.ts` so the two clock-diff cells across the app render identically.
- **Openings: Insights tab** evidence floor raised from n=10 to n=20 per (entry, candidate) transition. The SQL pre-filter on score <= 0.45 OR score >= 0.55 selects on the same statistic the Wald p-value then tests, so at small n the score-vs-50% test is anti-conservative; n>=20 mitigates the worst of that post-selection inflation. The explorer's arrow-color threshold (`MIN_GAMES_FOR_COLOR`) stays at 10 — the two thresholds are now decoupled.
- **Score-confidence p-value migrated from trinomial Wald to Wilson score test.** The Wilson 95% CI (`wilson_bounds`) was already used for ranking and display; the p-value driving the confidence bucket was still trinomial Wald, which produced internal inconsistency (CI/test could disagree at boundary scores) and a degenerate SE=0 case at all-wins / all-losses. Wilson's null SE = 0.5/sqrt(n) is well-defined for any n > 0, so the special-case branch is gone and the CI and test are now inversions of each other. Bucket thresholds (p<0.01 high, p<0.05 medium) and the n>=10 gate are unchanged. Tooltips and Field doc-comments updated. Eval-side (`eval_confidence.py`) intentionally stays on Wald-z — Wilson does not apply to continuous one-sample mean tests.
- Move Explorer rows and Opening Insights findings now show win/draw/loss stats and score across all games reaching the resulting position (including transpositions), so the row's headline matches the position summary on click-through. (Phase 80.1)
- **Endgame Start vs End: tile color rule + tightened neutral band** (Phase 82): the entry-eval tile's neutral band tightens from ±0.75 to ±0.5 pawns (cohort-IQR was wider, but half-a-pawn average swings at endgame entry are narratable). The tile-color rule changes from "significant → green/red, not significant → neutral" (Phase 81) to "value in green/red zone AND p < 0.05 → colored, otherwise neutral". Result: borderline-but-significant cases (e.g. +0.46 pawns at p<0.001) now read as neutral on the tile AND are not narrated as "above null" by the LLM, so the tile and the prose agree on what counts as a meaningful pattern. The endgame-score tile reuses the existing Openings score-bullet 45–55% band for visual parity.
- **MetricId rename: `endgame_score` → `endgame_score_timeline`, `non_endgame_score` → `non_endgame_score_timeline`** (Phase 82): the score_timeline subsection's two metrics get a `_timeline` suffix to free the clean `endgame_score` name for the new `endgame_start_vs_end` subsection. User-facing impact: none directly (these names appear only in the internal LLM prompt). Internal: glossary entries renamed in `app/prompts/endgame_insights.md`; finding `metric=` Literal values updated in `_findings_score_timeline`; `_PROMPT_VERSION` bump invalidates v22 caches automatically.

## [v1.15] Eval-Based Endgame Classification — 2026-05-03

Replaces the material-imbalance + 4-ply persistence proxy for endgame
conversion / parity / recovery classification with direct Stockfish-eval
thresholding (±100 cp on `eval_cp`, color-flipped to user perspective;
`eval_mate` short-circuits to ±1,000,000 cp). Hard cutover, proxy code path
removed entirely. Closes the structural gap on Queen and pawnless classes
(~24% miss rate on substantive material-edge sequences per the 2026-05-02
baseline). Phase 79 folds in a per-position `phase` SmallInteger column
(0=opening, 1=middlegame, 2=endgame) computed via a Python port of lichess
`Divider.scala`, plus middlegame-entry Stockfish eval — substrate for v1.16
opening-stats analyses. Combined Phase 78 + Phase 79 cutover delivered via
PR #78; follow-on PR #79 parallelises the import-time eval pass via
`EnginePool`. VAL-01 / PHASE-VAL-01 (re-run `/conv-recov-validation` for
~100% agreement) rescinded as moot — once the proxy was deleted the
agreement metric became undefined; the `/conv-recov-validation` skill was
deleted.

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

[Unreleased]: https://github.com/flawchess/flawchess/compare/v1.20...HEAD
[v1.20]: https://github.com/flawchess/flawchess/compare/v1.19...v1.20
[v1.19]: https://github.com/flawchess/flawchess/compare/v1.18...v1.19
[v1.18]: https://github.com/flawchess/flawchess/compare/v1.17...v1.18
[v1.17]: https://github.com/flawchess/flawchess/compare/v1.16...v1.17
[v1.16]: https://github.com/flawchess/flawchess/compare/v1.15...v1.16
[v1.15]: https://github.com/flawchess/flawchess/compare/v1.14...v1.15
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
