---
id: SEED-004
status: closed_superseded_by_phase_65
planted: 2026-04-21
planted_during: v1.11 LLM-first Endgame Insights (executing, Phase 64 complete, Phase 65 next)
trigger_when: Phase 65 discuss begins (LLM Endpoint with pydantic-ai Agent)
scope: phase
---

# SEED-004: Trend texture (volatility + recent-shift) for LLM insights

> **Closed 2026-04-21 — superseded by Phase 65 D-01.** The raw-series approach (D-01: feed weekly/monthly TimePoint arrays to the LLM) obviates the `volatility_cv` / `recent_vs_prior_delta` schema additions this seed proposed. See `.planning/phases/65-llm-endpoint-with-pydantic-ai-agent/65-CONTEXT.md`.

## Why This Matters

Phase 63 locked `_compute_trend` as a stdlib linear regression with two gates (count ≥ 20 weekly points, |slope|/stdev ≥ 0.5), emitting a single 4-value label `improving | declining | stable | n_a` (D-15, D-13). That label is the only trend signal the LLM receives in Phase 65, and it erases three phenomena that matter for chess-learning narratives:

1. **Volatility vs. stability.** A player with high weekly variance around a flat mean is "stable" under linear regression. That is statistically correct and narratively wrong — the LLM has no field for "inconsistent," so it cannot distinguish a stable-and-consistent player from a stable-but-high-variance one. This shows up most on Score Gap and Clock Diff, where week-to-week swings are real and diagnostic.
2. **Regime shifts / stable-then-sudden-rise.** With ~52+ weekly points in the all-time window, a genuine 8-week rise gets diluted by 44 weeks of prior flat data. The label returns `stable` or `n_a` even when the last two months clearly improved. For a product where users expect to see the effect of recent study or rating jumps, this is the biggest practical miss.
3. **Tilt / recent emotional swings.** Short-term variance isn't a trend at all; it's a recent property. A 52-week regression is the wrong lens for it.

**The bottleneck is the schema, not the algorithm.** Whatever math produces the trend label — linear regression, Mann-Kendall, PELT — the LLM still sees one word. Replacing the algorithm without enriching `SubsectionFinding` changes nothing downstream. This seed proposes additive schema fields, not a replacement algorithm. The existing `_compute_trend` stays in place as the `is_headline_eligible` gate; the new fields give the LLM the texture to describe what's actually happening.

There's also a knock-on design smell worth resolving in Phase 65: `is_headline_eligible` is gated entirely by trend for the three timeline subsections. For `last_3mo`, the count gate always fails (~13 weekly points), so that window is effectively headline-ineligible regardless of signal strength. If recent-shift data existed, the last-3-months window could become first-class.

## When to Surface

**Trigger:** Phase 65 discuss begins (LLM Endpoint with pydantic-ai Agent).

This seed should be presented during `/gsd-discuss-phase` for Phase 65 when:
- The phase scope touches the LLM prompt contract, `SubsectionFinding` consumption, or `findings_hash` versioning.
- Prompt design asks "what deterministic trend inputs are load-bearing for the narrative?"
- The `is_headline_eligible` gating behavior comes up.

Phase 65 is already in the v1.11 roadmap under SEED-003 (LLM-first Insights MVP). This seed extends the findings pipeline at the moment Phase 65 locks the prompt contract — schema additions are cheapest there, before Phase 66 frontend and Phase 67 validation pin the shape.

Do NOT surface during Phase 63 retro or Phase 64 follow-ups — Phase 63's MVP is deliberately locked, and Phase 64 logs payloads as-is.

## Scope Estimate

**Phase-sized** — additive schema change plus two stdlib helpers. Expected decomposition:

1. Add `volatility_cv: float | None` to `SubsectionFinding` (coefficient of variation across weekly points). Lets the LLM say "stable but high-variance" vs. "stable and consistent."
2. Add `recent_vs_prior_delta: float | None` (mean of last N weeks minus mean of prior N weeks, N ≈ 8 — tune at Phase 65 discuss). Captures regime shifts and recent form that linear regression dilutes. Addresses most "stable-then-sudden-rise" cases without true changepoint detection.
3. Optional third field `last_value_vs_window_mean: float | None` for end-of-window bias (tilt signal). Decide at Phase 65 discuss — may be redundant with `recent_vs_prior_delta`.
4. Compute in `insights_service.py` using `statistics.stdev` / `statistics.mean`; bump `findings_hash` version string.
5. Update prompt builder (Phase 65) to pass new fields to the LLM.
6. Decide whether a large `recent_vs_prior_delta` should force `is_headline_eligible=True` even when linear trend is `n_a`.

**Explicitly out of scope** for this seed (and strongly discouraged as follow-ups):
- PELT / kernel changepoint detection, Mann-Kendall, Bayesian changepoint. Any external dependency.
- Replacing `_compute_trend` or removing the slope/stdev ratio gate.
- Per-game point arrays in `SubsectionFinding` (would balloon the log payload and the LLM context).
- Additional smoothing (EMA, LOESS, Savitzky-Golay). Weekly bucketing in `endgame_service.py` already averages within each week, so the series fed to `_compute_trend` is pre-smoothed. Further smoothing would blunt the recent-shift signal `recent_vs_prior_delta` is meant to catch.

## Breadcrumbs

Related code and decisions in the current codebase:

- `app/services/insights_service.py:881-915` — `_compute_trend` implementation (the locked linear-regression gate)
- `app/services/insights_service.py` callers: `_finding_score_gap_timeline` (L234), `_finding_clock_diff_timeline` (L559), `_findings_type_win_rate_timeline` (L822) — the three subsections whose `is_headline_eligible` is gated by trend
- `app/services/endgame_zones.py:88-93` — `TREND_MIN_WEEKLY_POINTS = 20`, `TREND_MIN_SLOPE_VOL_RATIO = 0.5` (placeholder, tuning deferred)
- `app/schemas/insights.py` — `SubsectionFinding` schema (additive fields land here)
- `tests/services/test_insights_service.py:113-191` — `TestComputeTrend` suite; new fields need parallel test class
- `.planning/phases/63-findings-pipeline-zone-wiring/63-CONTEXT.md` — D-13 (headline eligibility) and D-15 (two-gate trend lock) — the constraints this seed works within
- `.planning/phases/63-findings-pipeline-zone-wiring/63-04-SUMMARY.md` — `SubsectionFinding` field inventory
- `.planning/seeds/SEED-001-endgame-tab-insights-section.md` — reserves `lookback_role` / `lookback_behavior` / stability-pattern fields; overlaps conceptually but is v1.12+ scope. Phase 65 discuss should check whether SEED-004's `recent_vs_prior_delta` is a lightweight precursor to SEED-001's stability pattern or a conflicting design.
- `.planning/seeds/SEED-003-llm-based-insights.md` — v1.11 MVP framing; SEED-004 extends within its MVP spirit (stdlib-only, additive, LLM-centric).

## Notes

Seed planted after a discussion triggered by a direct reading of `_compute_trend`. The user (data scientist background) flagged that real chess phenomena — ups/downs, volatility, tilt, regime shifts — don't fit a single-slope linear model. Agreed the concern is real; disagreed that the algorithm is the right lever. The schema exposes one label; enriching the math doesn't reach the LLM.

Open questions to resolve at Phase 65 discuss:
- Does the Phase 65 prompt receive raw weekly points, or only aggregated fields? If points are in-prompt, `volatility_cv` is redundant (LLM can compute it). If not, the field earns its keep.
- Does a large `recent_vs_prior_delta` force `is_headline_eligible=True` even when linear trend is `n_a`? This would rescue the `last_3mo` window.
- `N` for `recent_vs_prior_delta`: 8 weeks is a guess. Benchmark against SEED-001's regression fixture if available by Phase 65.
- Keep `volatility_cv` bounded (signed or absolute? guard divide-by-zero for zero-mean metrics like Score Gap).
