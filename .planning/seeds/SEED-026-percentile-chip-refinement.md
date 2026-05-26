---
id: SEED-026
status: planted
planted: 2026-05-25
last_updated: 2026-05-26
planted_during: /gsd-explore session — reflecting on shipped percentile chips (Phases 93/94.2/94.3) after observing the mobile chip is too large and that low-percentile chips on elite users may undermine credibility. Triggered re-examination of SEED-019's global-pool decision against the Lichess Tutor cohort-based alternative; the cross-platform rating-scale constraint reaffirmed global-pool and shifted the refinement to UX + metric eligibility instead of cohort restructuring.
updated_during: /gsd-explore session 2026-05-26 — (a) steelmanned the case for peer-relative percentiles and inverted the previous rejection; the "global percentile ≈ what the zone band already shows" insight is the load-bearing flip; cross-platform rating-scale concerns addressed via Lichess-precedence + chessgrandmonkey-style chess.com → Lichess conversion at ±100-Elo accuracy; sample-size concerns addressed via 200-user/cell selection (up from 100) + 50-Elo interpolation between anchors; latency was never a real constraint (we precompute at import). (b) Unified the TC-aggregated-metric cohort handling with the TC-stratified-metric handling — both now use per-(metric, ELO, TC) cohort CDFs and per-TC user scalars; the TC-aggregated chip becomes a game-count-weighted average of per-TC sub-percentiles. Removes the cross-TC-rating-anchor question by not needing one.
scope: phase (single, ~2-3 plans) — build per-cohort CDF family, add rating-anchor lookup at import time, rework chip UX (shrink + tooltip), revisit metric eligibility under the new framing
depends_on: SEED-019 phases shipped (93 CDF artifact, 94.2 chip rendering, 94.3 per-TC TimePressure chips). Production data on real elite users would sharpen the credibility evidence but isn't a hard prerequisite. Validating a chess.com → Lichess conversion table at FlawChess's ELO buckets is a research-question prerequisite before locking the rating-anchor logic.
supersedes_decisions_in: SEED-019 § "Final Tier-1 chip set" — the empirical tier table needs revisiting under peer-relative semantics; metrics previously dropped for ELO coupling (Conversion, Recovery, Time Pressure at rapid) may rescue under peer-relative since within-cohort comparison removes the rating-echo failure mode. Also supersedes this seed's own prior global-pool-preserving stance (see "Why global-pool percentiles are now rejected" below).
---

# SEED-026: Percentile chip refinement — peer-relative pivot

> **One-line summary (v2, 2026-05-26):** The chip pivots from global-pool ("vs all FlawChess benchmark users") to peer-relative ("vs same-rated-cohort users"), because global percentile is largely redundant with what the zone band already shows visually, while peer-relative carries information not visible elsewhere on the page. Cohort assignment uses a single rating anchor *per (user, TC)* — median rating over the user's latest ~1000 games at that TC, Lichess rating wins precedence over chess.com (chess.com gets converted via a published Elo-conversion table where Lichess data is absent). All metrics — TC-stratified and previously-TC-aggregated alike — use per-(metric, ELO, TC) cohort CDFs with 50-Elo interpolation between 400-wide ELO bucket centers. For previously-TC-aggregated metrics (`score_gap`, `achievable_score_gap`, the two Section-2 metrics), the chip is a game-count-weighted average of per-TC sub-percentiles; per-TC scalars are looked up against per-TC cohort CDFs and aggregated user-side. Chip UX (shrink to `23%`/`p23` pill, tooltip-only, drop ambiguous-direction metrics) survives unchanged from v1. Metric eligibility is re-opened — peer-relative may rescue Conversion / Recovery / Endgame Score Gap chips that the v1 framing dropped.
>
> **One-line summary (v1, 2026-05-25, superseded):** The chip's job narrows from "verdict on skill" to "diagnostic hint that surfaces anomalies worth investigating." Metrics that fail an ELO-coupling sanity check lose their chip; surviving chips shrink to a small `23%`/`p23` pill with tooltip-only explanation; tooltip copy acknowledges global-pool framing with rating-correlation honesty per metric. Cohort-based ("vs same-rating peers") percentiles are explicitly *not* adopted — the cross-platform rating-scale constraint kills that architecture for FlawChess.

## What changed between v1 and v2

The v1 seed accepted global-pool as the architectural floor and worked around its weaknesses (drop ELO-coupled metrics, shrink the chip, rewrite the tooltip). The v2 pivot replaces global-pool with peer-relative and keeps the v1 UX moves on top.

Two arguments did the work:

1. **Global percentile is roughly redundant with the zone band.** The blue zone band on each metric card is centered on the benchmark population's typical range, so a value inside the band *is by construction* near the global median; a value at the band edge *is* near p10/p90. A global percentile chip then mostly numericizes a visual signal the user already has. Peer-relative carries genuinely new information — your position *within your own rating cohort* — that the band cannot express.
2. **Peer-relative gives a coherent signal across every metric.** Under global, the chip is most informative on rating-invariant metrics (Endgame Score Gap, Parity) and most misleading on rating-coupled metrics (Conversion, Recovery, Time Pressure at rapid), where it just echoes the user's rating. The v1 seed handled this by *dropping* the coupled-metric chips. Peer-relative *fixes* them — within-cohort comparison removes the rating-echo failure mode.

The v1 seed's rejection of peer-relative cited five reasons. v2 addresses each:

| v1 rejection reason | v2 resolution |
|---|---|
| Cross-platform rating-scale incompatibility | Lichess rating wins precedence per TC when both platforms have games; chess.com → Lichess-equivalent conversion via a published table (e.g. chessgrandmonkey-style). Conversion accuracy of ±100 Elo is sufficient at 50-Elo interpolation between anchors. |
| No bulk chess.com benchmark data | Restated honestly: this is "we picked Lichess because their PGN dumps include Stockfish evals," not "no bulk endpoint exists." Either way the consequence is the same — Lichess is canonical. Going peer-relative locks that assumption in more visibly, but global-pool already had the same assumption baked in invisibly. |
| Sparse cells at 2400 | 200 users/cell now (up from 100), and the 2400-classical cell stays suppressed as it already is. Mid-buckets carry ~150-280 users per (ELO, TC) cell which is comfortable for CDF estimation. |
| Latency | Never a real constraint — we precompute at import time and store the scalar percentile. Cohort lookup is one extra dict access per (user, metric) at compute time. |
| Smaller benchmark population than Lichess Tutor | True, but Tutor recomputes at request time over a 5,000-game peer sample. We're precomputing against a fixed cohort CDF of ~150-280 users. Different operating regime; the n still supports stable CDF estimation. |

## What's load-bearing in v2

### Conceptual framing: the chip is a within-cohort comparator

The v1 "ELO is the strength metric, the chip is for anomalies vs population" framing was a workaround for global-pool's redundancy with the band. v2 reframes more straightforwardly:

| Surface | Job |
|---|---|
| Endgame ELO Timeline | "How strong are you, longitudinally?" |
| Zone band on metric value | "Is this value typical for the benchmark population?" (population-wide, not cohort-specific) |
| Percentile chip (v2) | "Where do you stand on this specific metric vs other players at your rating?" |
| Metric value itself | "What did your play actually produce?" |

Under v2, a 2400 user landing at `p15` on Endgame Score Gap reads as "even compared to other 2400s, your endgame is unusually unbalanced relative to your non-endgame play" — a genuine informative verdict within their peer group, not a misleading "you're bad at chess" verdict against the whole population. The credibility problem dissolves through honest cohort comparison rather than through chip-as-anomaly-hint reframing.

### Cohort definition and rating anchor

**Single anchor per (user, TC)**, computed at import time (or recomputed when the user re-imports). The same rule applies to every metric — there is no TC-aggregated special case:

- For each TC the user has games in: median rating over the user's latest ~1000 games at that TC, Lichess rating wins precedence over chess.com.
- For chess.com-only TCs: convert chess.com rating to Lichess-equivalent via a published conversion table (chessgrandmonkey-style, validated at FlawChess's ELO buckets — see open research question).
- TCs below the per-metric games floor: skipped silently for that metric (graceful degradation, same as how chips suppress today below floor).

This collapses the entire "what rating to use" question to a single per-TC rule.

### Cohort CDF family

Replaces `GLOBAL_PERCENTILE_CDF` (one 99-breakpoint table per metric) with a family indexed by `(metric, ELO anchor, TC)` — the same shape for every chip-eligible metric, including the four currently-TC-aggregated metrics (`score_gap`, `achievable_score_gap`, `section2_score_gap_conv`, `section2_score_gap_parity`). ELO anchors at the 5 benchmark bucket centers (800/1200/1600/2000/2400), with 50-Elo linear interpolation between adjacent anchors at lookup time along the ELO axis; no interpolation across TCs. The user's per-TC anchor rating slots into the nearest two bucket centers; the per-TC percentile is a weighted blend of the two cohort-CDF lookups.

Implementation: regenerate the CDF artifact (or add a parallel one) where each metric carries up to 5 × 4 = 20 CdfTable instances (one per (ELO anchor, TC) cell, minus sparse / below-floor cells). Same `interpolate_percentile` shape, two additional dimensions to the registry. The 2400-classical sparse cell stays suppressed exactly as today — the CDF at (metric, 2400, classical) is just absent, lookups for users at that anchor return None for that TC, and the metric falls back to whatever per-TC sub-percentiles do meet the floor.

### Per-TC sub-percentile aggregation for currently-TC-aggregated metrics

For the four metrics that today emit a single chip across all TCs, v2 computes per-TC sub-percentiles under the hood and aggregates user-side:

1. For each TC the user has above-floor games in, compute the user's per-TC scalar (the existing per-user CTE, restricted to that TC — Phase 94.3 already added this pattern for the time-pressure family).
2. Look up the per-TC scalar against the per-(metric, ELO, TC) cohort CDF at the user's per-TC anchor rating.
3. Get up to 4 sub-percentiles per metric.
4. Aggregate to one chip-displayed percentile via game-count-weighted mean, where the weight is the same N that drives the per-TC floor for that metric (endgame games for `score_gap`, endgame-entry games with non-null `d_i` for `achievable_score_gap`, spans-in-bucket for the Section-2 metrics).
5. Below-floor TCs drop out silently; if all TCs are below floor, the chip suppresses (existing behavior).

This keeps `user_benchmark_percentiles` storage shape unchanged — still one scalar `percentile` per `(user_id, metric)` row. The per-TC sub-percentiles are intermediate; only the aggregated value is stored. (If we want to surface "your chip averages bullet p35 + rapid p55 ..." in the tooltip later, the per-TC sub-percentiles can be added to storage cheaply at that point — out of scope for v2.)

## What's in scope

### 1. Cohort CDF generation script update

Extend `scripts/gen_global_percentile_cdf.py` (or add a sibling `gen_cohort_percentile_cdf.py`) to emit per-(metric, ELO anchor, TC) CDF tables computed from the same canonical-slice CTE, partitioned by game-time ELO bucket × `tc_bucket`. Currently-TC-aggregated metrics gain the TC dimension; currently-TC-stratified metrics keep their existing TC dimension. Sample floors per anchor stay at the existing ≥30 / ≥20 thresholds; cells below the floor (and the 2400-classical sparse cell) are absent from the table.

Approximate CDF count after this change: ~16 chip-eligible metrics × 5 ELO anchors × 4 TCs, minus sparse / below-floor cells — order ~250-300 CdfTable instances total. Each table is a tuple of 99 floats; memory and load-time impact is trivial.

### 2. Rating-anchor compute at import time

Add a per-(user, TC) rating-anchor compute that runs alongside (or inside) Stage A / Stage B. Reads from `games.white_rating` / `games.black_rating` for the user's latest ~1000 games per TC, applies Lichess-first precedence, falls back to chess.com → Lichess conversion via a table constant. Produces up to 4 anchors per user (one per TC the user has games in). Stores the resolved anchors (could live on a small `user_rating_anchors` table or be computed transiently and only the percentile is stored; debugging visibility argues for storage).

### 3. Percentile lookup change

In `compute_stage_a` / `compute_stage_b`, replace the single `interpolate_percentile(metric, value)` call with:

- **TC-stratified metrics** (per-TC chip): one cohort-aware lookup, `interpolate_cohort_percentile(metric, per_tc_value, elo_anchor_for_tc, tc)`. Output shape unchanged.
- **Previously-TC-aggregated metrics** (single chip): up to 4 per-TC lookups (one per above-floor TC the user has data in), then a game-count-weighted mean. Output shape unchanged — still one scalar `percentile` per `(user_id, metric)` row.

Per-TC user scalars for the currently-TC-aggregated metrics need a new per-TC CTE flavor. Phase 94.3 already established the pattern (it added per-TC CTEs for the time-pressure family); this just extends it to the four `_score_gap` metrics. Mechanical.

### 4. Metric eligibility revisit under peer-relative

The v1 seed dropped Conversion Score Gap, Recovery Score Gap, and Endgame Score Gap from the chip set. Under peer-relative, the dropping rationale weakens:

- **Conversion / Recovery Score Gap** — v1 dropped because sigmoid bias pulls everyone negative/positive structurally and "the better direction isn't reading-honest." Under peer-relative, the chip means "you convert/recover better or worse than peers at your rating," which is honest regardless of the underlying sign convention. **Lean: rescue.**
- **Endgame Score Gap** — v1 dropped because a low chip on an elite user reads as "FlawChess thinks I'm bad" under global. Under peer-relative, a low chip means "your endgame is unusually unbalanced even compared to other 2400s," which is the genuinely useful diagnostic. **Lean: rescue.**
- **Time Pressure Score Gap at rapid** — v1 considered dropping because of heavy ELO coupling (d=0.73). Under peer-relative, ELO coupling is absorbed by the cohort — the chip becomes "you handle time pressure worse/better than peers at your rating at rapid." **Lean: rescue all four TCs of the time-pressure family.**

The Spearman-ρ recomputation from v1 is no longer load-bearing — peer-relative makes ELO coupling a non-issue for chip interpretability. The "clear direction (higher/lower is better)" eligibility rule still applies and would still reject something like a signed-balance metric where neither direction is unambiguously "good."

Best guess at the v2 surviving set (subject to peer-relative tooltip-copy honesty check):

- ✅ Endgame Score Gap (rescued — peer-relative makes elite-user reading honest).
- ✅ Achievable Score Gap.
- ✅ Parity Score Gap.
- ✅ Conversion Score Gap (rescued).
- ✅ Recovery Score Gap (rescued).
- ✅ Clock Gap per TC.
- ✅ Net Flag Rate per TC.
- ✅ Time Pressure Score Gap per TC (all four — rescued).

That expands the chip surface from ~3-5 chips in v1 to ~7-12 chips in v2. The v1 UX moves (shrink to pill, tooltip-only) become *more* important under v2 because the chip count goes up.

### 5. Chip UX shrink (unchanged from v1)

Replace `Bottom 23%` / `Top 5%` with `23%` or `p23` — small pill, ~24px tall, fits comfortably on mobile, reads as a side-note. Full "vs same-rated peers" explanation moves into the hover/tap tooltip. Visual emphasis stays on the metric value + zone band; chip is a diagnostic side-note.

### 6. Tooltip copy rework under peer-relative framing

Per the [percentile chip tooltip disclosure](../../memory/feedback_percentile_chip_tooltip_disclosure.md) feedback memory, the tooltip must disclose benchmark composition, recent-games basis, filter independence, and what cohort the chip compares against. New v2 requirements:

- Lead with the cohort framing ("Compared to other ~1600-rated players. Independent of your filter settings.").
- Disclose the rating anchor source ("Anchored on your Lichess rapid rating; chess.com ratings converted to Lichess-equivalent.") so multi-platform users know what's happening.
- Drop the v1 per-metric "this metric is roughly independent of rating" copy — under peer-relative it's no longer load-bearing, because cohort comparison absorbs the coupling.
- Keep "based on your most recent N games" disclosure.

### 7. SEED-019 tier table supersede

Mark SEED-019 § "Final Tier-1 chip set" as superseded by this seed once v2 lands. The Cohen's d / Spearman ρ analysis was load-bearing under global-pool framing; under peer-relative it becomes mostly irrelevant (the cohort absorbs coupling). Keep the analysis as historical context.

## What's explicitly NOT in scope

- **Per-game-rating bucket sub-percentiles** (5-way partition along the ELO axis, *within each TC*). Briefly considered during /gsd-explore 2026-05-26 — for each of U's games, compute a per-ELO-bucket sub-scalar against the cohort at that game's exact rating, then aggregate. Architecturally cleaner against the benchmark's own per-bucket build but materially more code than single-anchor lookup, and the precision gain over a single per-TC anchor median is negligible at integer-percentile resolution. **Single anchor per TC wins on Toyota grounds.** Note: this is a distinct partition from the per-TC sub-percentile aggregation v2 *does* adopt for currently-TC-aggregated metrics — that one is a 4-way partition along the TC axis (one sub-percentile per TC the user has data in), not a partition along the ELO axis within each TC.
- **Per-platform-restricted chips (chip only renders when filter is single-platform).** The current Phase 94 design is filter-independent and that property is preserved in v2 via the per-(user, TC) anchor stored at import time.
- **Letter grades or mine/peer numeric pairs (Lichess Tutor's UX).** Out of scope. Zone band + ELO timeline + percentile pill cover the same three jobs.
- **Stratified percentiles per rating bucket on the EXISTING (global) benchmark CDFs.** This was a half-measure considered in v1; v2 supersedes it with proper per-cohort CDFs.
- **Changes to the empirical CDF artifact's shape.** Same `CdfTable` shape per cohort, same `interpolate_percentile` interface; just one more dimension to the registry.
- **LLM payload changes (Phase 95).** The LLM payload still gets the scalar percentile; reframing it cohort-relative doesn't change the field. Tooltip copy changes may inform later prompt updates but aren't blocking.

## Open questions

1. **Does the chess.com → Lichess Elo conversion table hold across our ELO buckets?** The chessgrandmonkey-style published tables are approximations. Pre-planning research: take a sample of dual-platform users (chess.com + Lichess accounts linked), compute observed per-TC rating offsets, compare against the published table. If the table is within ±100 Elo at the bucket centers and ±150 Elo at the tails, ship it. If it drifts to ±300+ at the tails, build a FlawChess-specific calibration. This is the one factual unknown that should land *before* the implementation phase.
2. **What N for the "latest games" rating anchor?** 1000 per TC is a guess. Could be 500 (more recent / less stable) or 2000 (more stable / more historical). The recent-capped CTE already uses a cap; align with that.
3. **Where to store the per-TC rating anchors?** Options: (a) a small `user_rating_anchors` table keyed by `(user_id, tc_bucket)`; (b) extend `user_benchmark_percentiles` with an `elo_anchor` column (denormalized across rows of the same user); (c) compute transiently and only store the resolved percentile. Tooltip wants to disclose the anchor so the user can see why their chip is what it is — argues for (a) or (b). Lean: (a).
4. **Aggregation weight choice for previously-TC-aggregated metrics.** "Game-count weighted by the per-TC floor's N" is the proposal — but the floor N differs per metric (endgame games for `score_gap`, span counts for Section-2). Two sub-questions: (i) is that the right weight per metric, or should we use raw game count uniformly? (ii) Does the weighted mean of per-TC percentiles materially differ from the global-pool result on real data? Worth a small empirical pass during planning to sanity-check.
5. **Pill format: `23%` or `p23`?** Carried over from v1. `23%` familiar, `p23` unambiguous. Decide during planning.
6. **Tooltip-only is a discoverability risk on mobile.** Tap targets shrink with the pill. Onboarding hint or persistent secondary affordance may be needed.
7. **Do we drop Endgame Score Gap as the headline chip on the main Endgame Stats panel?** Under v2 it's rescued, so the visual-hierarchy concern from v1 goes away.

## Related decisions to verify

- [Percentile chip tooltip disclosure](../../memory/feedback_percentile_chip_tooltip_disclosure.md) — disclosure requirements stay; v2 changes the cohort phrasing and adds rating-anchor source disclosure.
- [Benchmarks are source of truth for "typical"](../../memory/feedback_benchmark_source_of_truth.md) — v2 still anchors tooltip copy to benchmark data; the cohort partition is just one more cut of that data.
- [Popover copy minimalism](../../memory/feedback_popover_copy_minimalism.md) — explicitly overridden for percentile chip tooltips per the disclosure memory. v2 keeps the override.
- SEED-019 § "Final Tier-1 chip set" — mark as superseded by v2 once shipped.
- This seed's own v1 stance (global-pool with metric-eligibility tightening) — explicitly superseded by v2; retain the v1 reasoning as historical context above.

## Trigger conditions

Promote when **any** of the following:

- The chess.com → Lichess rating conversion validation lands and confirms ±100-Elo accuracy at the bucket centers (the one prerequisite research question — see Open Questions #1).
- A real elite user (≥2200 on Lichess or ≥2050 on chess.com) reports the credibility concern in feedback.
- A v1.20 (or later) milestone with capacity for endgame-page polish opens.
- Mobile usability feedback specifically flags the chip size as a problem.
- A request lands for percentile chips on metrics currently dropped by v1 (Conversion / Recovery / Endgame Score Gap) — v2 rescues these and the promotion becomes net positive.
