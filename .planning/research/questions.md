# Open Research Questions

Open questions surfaced during exploration that need data or investigation before they
can be settled. Append new entries at the bottom; mark resolved entries with **Resolved:**
and a one-line answer + link to where the answer lives.

---

## Q-001: Effective independent test count for opening insights, post-dedupe

**Asked:** 2026-04-28 (during `/gsd-explore` on opening-insight statistical framing)

**Context:** The Phase 70/71 opening-insights classifier scans every `(entry_hash, candidate_san)` transition with `N >= 20` across plies 3..16, then collapses results via `_dedupe_within_section` (deepest-opening wins per `resulting_full_hash`) and `_dedupe_continuations` (drop downstream chains). The remaining surface is what users see.

If we ever apply multiple-comparisons correction (BH-FDR or similar — see SEED-007), we need to know roughly how many *effectively independent* tests survive dedupe per user. This sets the corrected per-test alpha needed to keep overall FDR ≤ 10%.

Anecdotally Adrian estimated 5-30 lines per typical user. We want a real distribution.

**How to answer:** One SQL query against `flawchess-prod-db` (read-only, via `mcp__flawchess-prod-db__query`):

1. For each user with ≥1000 games, replicate the `query_opening_transitions` aggregate (HAVING `N >= 20` AND `(L/N > 0.55 OR W/N > 0.55)`) for both colors under default filters (no time-control restriction, no recency cutoff, opponent_strength=any).
2. Approximate dedupe by counting distinct `resulting_full_hash` values surviving the HAVING clause (cheap proxy — the actual `_dedupe_continuations` chain-collapse is harder to express in SQL, so the count is an overcount, but a useful upper bound).
3. Report: median, p90, p99 of surviving tuple count per user, broken out by total game count (1k / 3k / 10k+).

**Why deferred:** Today the surface is positioned as "candidate hint, not diagnosis", so per-test FDR isn't load-bearing. The question becomes load-bearing when SEED-007 fires (LLM narration over opening findings, or feedback shows over-claiming).

**Resolved:** _(open)_

---

## Q-002: Per-ply signed material balance — stored or computed?

**Asked:** 2026-05-01 (during `/gsd-explore` on Library page milestone, SEED-010)

**Context:** SEED-010's new material-delta filter ("show games where I reached ≥+X material sustained ≥4 plies, anywhere") is filtered on-the-fly from `game_positions` rather than via precomputed columns on `games`. The query needs per-ply signed material balance from one side's POV.

If the value is already a column on `game_positions`, the filter is a window function over an indexed integer column — cheap. If it's computed at query time from board state (FEN/hashes), the filter cost balloons and we should consider materializing it as a column.

**How to answer:**
1. Read `app/models/game_position.py` to inspect columns.
2. If absent, grep `app/services/import_service.py` and `app/services/normalization*` for any current material-balance computation that could be persisted.
3. If absent and not derived elsewhere, the SEED-010 milestone planner should add a `material_balance_white_pov SmallInteger` column on `game_positions` populated at import + backfilled via `reclassify_positions.py`.

**Why deferred:** answer determines milestone phase decomposition for SEED-010 (with vs. without a data-prep phase that adds the column). Not needed until that milestone starts.

**Resolved:** _(open)_

---

## Q-003: Middlegame transition definition for phase markers

**Asked:** 2026-05-01 (during `/gsd-explore` on Library page milestone, SEED-010)

**Context:** The Analysis page viewer shows phase markers (opening / middlegame / endgame) on the timeline. Endgame transition is already classified at import (`endgame_start_ply` or similar). Middlegame transition is less obvious — common definitions:

- "Out of book" (last ply matching an opening in the openings table)
- Fixed move number (e.g. ply ≥ 20)
- Both castled or both committed kings
- Some heuristic on minor-piece development

**How to answer:**
1. Inspect `app/models/game.py` and `app/services/normalization*` to confirm whether `middlegame_start_ply` or equivalent already exists.
2. If not, the SEED-010 milestone needs to pick a definition. Lowest-friction: derive from "out of book" using the openings table (we already track the deepest opening match per game). Falls back to a fixed-move-number floor (e.g. ply 16) if a game never matches an opening.

**Why deferred:** determines whether SEED-010 needs a new column + reimport. Not needed until that milestone starts.

**Resolved:** _(open)_

---

## Q-004: Per-ply clock storage — confirmed for both chess.com and lichess?

**Asked:** 2026-05-01 (during `/gsd-explore` on Library page milestone, SEED-010)

**Context:** The Analysis viewer shows remaining clock per ply for both players. chess.com PGN provides `%clk` annotations; lichess provides `clk` arrays. Both should be stored on `game_positions` at import.

**How to answer:** inspect `app/models/game_position.py` for clock column(s), and confirm both `app/services/import_service.py` paths (chess.com vs. lichess) populate them. Sample a few imported games of each platform in the dev DB to verify presence.

**Why deferred:** if either path doesn't store per-ply clocks today, SEED-010 needs a backfill phase. Not needed until that milestone starts.

**Resolved:** _(open)_

---

## Q-005: Lichess imported Stockfish eval coverage — what % of games?

**Asked:** 2026-05-01 (during `/gsd-explore` on Library page milestone, SEED-010)

**Context:** Tactical filters (missed forks/pins, blunder-driven losses) are deferred from SEED-010 v1, gated on imported Stockfish eval coverage being high enough to make the feature reliable. Today only a minority of lichess games have evals (chess.com imports never do). The eval-bar / eval-timeline UI in the v1 viewer also only renders when the loaded game has evals.

We need a real number on prod: across imported lichess games, what fraction have per-ply evals? Broken out by user (some users may have a much higher fraction if they enable lichess server analysis).

**How to answer:** one SQL query against `flawchess-prod-db` (read-only, via `mcp__flawchess-prod-db__query`):

1. Count `game_positions` rows with non-null Stockfish eval, grouped by `games.platform`.
2. Compute coverage = (positions with eval) / (total positions) per platform, and per user for the top-N most active users.
3. Also report: % of *games* with at least one eval (vs. just position-level coverage).

**Why deferred:** sizes the eventual tactical-filter feature. If coverage is <10% across users, tactical filters need the client-side engine pipeline before they're useful. If coverage is 30%+ for engaged users, an "evals-only" tactical filter could ship without the engine pipeline.

**Resolved:** _(open)_

---

## Q-006: DataFrame + plotting lib choice for the `analysis/` marimo environment

**Asked:** 2026-05-27 (during `/gsd-explore` on analysis environment setup)

**Context:** SEED-028 sets up an `analysis/` uv workspace member with marimo notebooks for data exploration against the three Postgres instances (dev/benchmark/prod). Two open library choices block "writing the first real notebook":

1. **DataFrame:** polars vs pandas
2. **Plotting:** plotly vs altair vs matplotlib

Current leanings (not validated):
- **polars** — faster on large benchmark queries (1.3M games, 95M positions), `pl.read_database` reads directly from a connection string, lazy frames are well-suited to "filter cohort → aggregate → chart" pipelines. Downside: less ecosystem (no native sklearn/seaborn integration), and the polars API differs enough from pandas that muscle memory transfers poorly.
- **plotly** — interactive HTML out of the box, marimo renders plotly figures natively (`mo.ui.plotly` etc.), good for "scrub a slider, see the chart update" workflows. Downside: heavyweight (~3MB JS), and the API is verbose for simple charts.
- **altair** — declarative grammar-of-graphics, marimo docs use altair in many examples, integrates with `mo.ui.altair_chart` for selections-as-state. Downside: Vega-Lite renderer can be slow on >10k points; no easy escape hatch to matplotlib quality.

**How to answer:** When SEED-028 germinates, spike a 30-min comparison:
1. Write the same chart (e.g. "distribution of conversion-rate scores per ELO bucket, faceted by TC") three ways: polars+plotly, polars+altair, pandas+plotly.
2. Compare: lines of code, render speed on the full benchmark dataset, how natural the marimo reactive bindings feel.
3. Pick one combo as the default; document in `analysis/README.md`.

**Why deferred:** No analysis notebook exists yet to drive the decision. Pre-emptive lib choice without a real workload risks optimizing the wrong axis (e.g. picking polars for speed when the actual workload is plot-iteration time, not query time).

**Resolved:** _(open)_

---

## Q-007: Flaw-stats opponent comparison — per-user game-count distribution & benchmark delta-IQR feasibility

**Asked:** 2026-06-09 (during `/gsd-explore` on the flaw-stats opponent-comparison rework — see [SEED-040](../seeds/closed/SEED-040-flaw-stats-opponent-comparison.md))

**Context:** SEED-040 plots, per flaw tag, a paired per-game *delta* (you − opponents) with a confidence interval, against a benchmark "typical" zone = the IQR of that delta across ELO-matched peers. Two unknowns gate the design before the milestone is scoped:

1. **Section-gate floor + CI usefulness.** The comparison is computed over the user's own analyzed games (≥90% eval coverage). We need the *distribution of per-user analyzed-game counts* to (a) set the section-level "analyze more games to unlock comparison" floor N, and (b) judge whether the median user's paired-delta CIs are tight enough to be useful — especially for the curated combos (`hasty+miss`, `low-clock+miss`), whose intersection counts may be a dozen events even for active users.
2. **Benchmark delta-IQR computability + TC-collapse.** Confirm the delta-IQR zone is computable on current benchmark-DB eval coverage for the eval-only families (tempo/phase/opportunity/impact), given the 11–62% per-cell coverage in `reports/benchmark/benchmark-eval-coverage-2026-05-25.md`. For each flaw-delta metric, run the established `/benchmarks` Cohen's-d collapse verdict to decide whether the zone needs cell-specific bounds or collapses across TC (and/or ELO).

**How to answer:**
1. Against `flawchess-prod-db` (read-only): distribution (median, p25, p90) of *analyzed* games per user (apply the ≥90% eval-coverage gate), broken out by total-game-count tier. Cross with typical per-game event rates for the rarest v1 bullets (the two combos) to estimate CI half-widths at the median user.
2. Against `flawchess-benchmark-db` (after opponent-flaw materialization is run there): per (ELO bucket × TC) cell, count cohort users with enough analyzed games to contribute a stable per-user delta; confirm each cell clears the established K-user floor for a quartile estimate.
3. Run the `/benchmarks` collapse verdict per flaw-delta metric.

**Why deferred:** Sizes the section gate and confirms the benchmark zone is viable before committing the milestone. Not needed until the SEED-040 milestone is scoped; the benchmark half specifically requires phase 1 (opponent-flaw materialization) to have run against the benchmark DB.

**Partial answer (2026-06-09) — prod analyzed-game distribution (half 1a only):**

Ran against `flawchess-prod-db`. "Analyzed" = full eval present, proxied by `white_blunders IS NOT NULL OR black_blunders IS NOT NULL` (the summary-column proxy the eval-coverage report validated to ~0.13% of the ≥90%-coverage definition). `game_flaws` is **absent in prod** (v1.24 unshipped) so combo event rates were NOT measured.

103 of 126 users have games. Per-user analyzed-game counts are **strongly bimodal**, not uniformly low:

| Metric | Value |
|---|---|
| Median analyzed games/user | **6** |
| p75 | 511 |
| p90 | 1,062 |
| max | 5,133 |
| Avg % of a user's games analyzed | 12.2% |
| Users ≥20 analyzed | 51 |
| ≥50 | 48 |
| ≥100 | 41 |
| ≥200 | 37 |

**Implications for SEED-040:**
- Two populations: a bottom half with almost nothing (median = 6, mostly chess.com / analysis-off lichess) and a top ~37–51 users with hundreds-to-thousands; almost no middle (median 6 → p75 511).
- The **section gate is load-bearing**: at a ~20-analyzed-game floor, ~half of active users (51/103) ever see the comparison. Frame the feature as "for engaged-analysis users"; the empty state must sell "enable analysis / import more."
- **Combos remain the open risk.** Even an above-gate user with ~50 analyzed games has few `hasty+miss` events (rare intersection), so those two bullets likely straddle zero for all but the ~37 heaviest users. Quantifying needs per-game combo event rates from `game_flaws`.

**Still open (need opponent-flaw materialization first):** (1b) combo CI widths at scale, and (2) benchmark delta-IQR computability + TC-collapse per cell. Both deferred until milestone phase 1 (materialization) has run against the benchmark DB. The dev DB has `game_flaws` for users 28 & 44 only — a 2-user estimate is available but too thin to set thresholds.

**Resolved:** _(partial — half 1a answered above; halves 1b + 2 deferred to post-materialization)_

---

## Q-008: Full-game eval drain — prod 1M-node throughput + catch-up queue sizing

**Asked:** 2026-06-12 (during `/gsd-explore` on prioritizing Stockfish analysis of chess.com games — see [SEED-012](../seeds/SEED-012-client-side-stockfish-tactics.md), 2026-06-12 amendment)

**Context:** SEED-012's server-first v1 locked a fixed **1,000,000-node NNUE** search per position (Lichess fishnet parity, D-6) for the all-ply eval drain. All throughput planning rests on a napkin estimate (~1–2 min core-time/game, ~4–8k games/day on ~6 SCHED_IDLE cores). Two unknowns gate the milestone's queue/window sizing:

1. **Real 1M-node latency on the CPX42.** Benchmark Stockfish (the prod binary/version) at `nodes=1_000_000`, NNUE, multiPV=1, hash per `engine.py` config, across a representative mix of opening/middlegame/endgame positions — on the prod box under SCHED_IDLE, both idle and while normal traffic runs. Output: seconds/position (p50/p90), effective games/day for pool sizes 4–6, and confirmation SCHED_IDLE keeps API latency unaffected at full tilt.
2. **Catch-up queue size.** Against `flawchess-prod-db`: count of recently-active users (e.g. activity within 30/60/90 days) × their last-100/200/500 game counts *lacking full eval coverage* (chess.com games + analysis-off lichess games). Output: total games in the tier-2 automatic catch-up at each candidate window size, and the implied catch-up duration at the measured throughput from half 1.

**How to answer:**
1. A ~10-minute spike: small script (à la `scripts/backfill_eval.py`) or one-off invocation of `EnginePool` with a `chess.engine.Limit(nodes=1_000_000)` over ~50 sampled prod-shaped positions; run on the prod host (or measure locally and scale by a one-position prod calibration run).
2. Read-only queries via `flawchess-prod-db` (tunnel required), reusing the Q-007 "analyzed" proxy inverted (games where the eval columns are NULL across plies).

**Why deferred:** Pins the automatic-window size (D-3) and the expected catch-up duration before the milestone commits to UX copy ("your games will be analyzed within ~X") and queue tier design. Not needed until SEED-012 is promoted via `/gsd-new-milestone`.

**Resolved (2026-06-12):** Both halves answered by spikes 001–003 (`.planning/spikes/`).

1. **Throughput (spikes 001+002):** 1M-node NNUE = mean **0.98 s/position on the prod CPX42** (depth ~22 reached, budget always fully consumed). Six concurrent SCHED_IDLE workers scale near-perfectly (no per-position penalty) → **5.83 positions/s ≈ 8.4k games/day**; API latency unaffected at full tilt (p50 65→67 ms). Tier-1 single-game fan-out across 6 workers ≈ **10 s wall-clock**. Surprise: Lichess parity costs ~10× depth-15 (not the estimated 3–5×) — recorded in spike 001; does not overturn D-6 (calibration argument). Hash 32 vs 64 MB: no difference at this budget.
2. **Queue sizing (spike 003):** 93% of prod games (558k of 598k) lack per-ply evals. Tier-2 catch-up for 30d-active users (56 with games): w100 ≈ **0.5 days**, w200 ≈ **0.9 days**, w500 ≈ **2.1 days**; the 31–60d cohort adds ~55%. Tier-3 idle drain reaches full-DB coverage in ~66 days. Caveat: `users.last_activity` was backfilled ~2026-03-22, so activity windows >60d are meaningless. Real evaluated-plies/game ≈ 53 (vs 60 assumed — projections mildly conservative).

**Implication:** set the automatic window at 200 (or even 500) games; UX copy can promise same-day/next-day analysis for newly active users.

---

## Q-009: Weighted-lottery tier-3 drain — partial-index perf for the DISTINCT-users candidate scan

**Asked:** 2026-06-14 (during `/gsd-explore` on replacing the winner-take-all tier-3 ordering — see [SEED-046](../seeds/closed/SEED-046-tier3-weighted-lottery-drain.md))

**Context:** SEED-046 replaces the strict `users.last_activity DESC` top key in `_claim_tier3_derived` (`app/services/eval_queue_service.py:185-241`) with a recency-weighted lottery over **users**. Each claim (~every 10s) the drain must pick a user weighted by recency from the set of users with genuine engine backlog, then pick that user's best game. The candidate-user set is:

```sql
SELECT DISTINCT user_id FROM games
WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NULL
```

(the `needs_engine_full_evals` predicate, `app/models/game.py:223-238`). The weighted pick then applies Efraimidis–Spirakis ordering: `ORDER BY -ln(random()) / weight LIMIT 1` over those distinct users (joined to `users.last_activity`).

On a large `games` table (~598k rows prod, 93% lacking evals per Q-008), `SELECT DISTINCT user_id` over a non-covering predicate is a scan. Run every claim, that could become the drain's hot cost.

**How to answer:**
1. Add a candidate **partial index**: `CREATE INDEX ... ON games (user_id) WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NULL` (index-only DISTINCT scan). Confirm via `EXPLAIN ANALYZE` against `flawchess-prod-db` (tunnel) that the DISTINCT-users + ES pick stays sub-100ms per claim at prod scale.
2. Confirm the candidate-user count is bounded by user count (hundreds), not game count — so the ES sort is small once the DISTINCT is cheap.
3. Decide whether a periodic materialized "users-with-engine-backlog" snapshot (refreshed every N claims) is worth it, or whether the partial index alone suffices (likely the latter at current scale).

**Why deferred:** Pins the migration + query shape before the SEED-046 phase is scoped. Not needed until SEED-046 is promoted (which is itself gated on Phase 118 shipping and the strict-recency drain being observed in prod).

**Resolved:** _(open)_

