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

