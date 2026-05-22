# Requirements: FlawChess — v1.19 Endgame Percentiles & LLM Statistical Reasoning

**Defined:** 2026-05-22
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary on endgame performance and an auto-generated opening-strengths/weaknesses report.

**Milestone goal:** Close SEED-019 by surfacing global percentile annotations on Tier-1 / Tier-2 Endgame metrics, and rework the endgame-insights LLM prompt + payload so it can reason explicitly over the v1.17 metric set (Endgame Score Gap, Achievable Score Gap, Section 2 ΔES Score Gap family, time-pressure hypothesis tests) using p-values, confidence interval bounds, and percentiles, with prompt guardrails that prevent narrating small-but-significant findings.

**Source:** `.planning/seeds/SEED-019-global-percentile-annotations-on-endgame-metrics.md` (open) and recent v1.17 statistical-rigor work (Phase 85.1, 86, 87.2, 87.6, 88) that exposed new server-side test statistics not currently surfaced to the LLM.

**Scope discipline:** The requirements below are directional and category-level. Per-phase scope (which Tier-1/Tier-2 metrics ship in the first cut, whether Tier-4 is in/out, whether to pass raw CIs vs. derived narration tags, LLM prompt version pivots) is refined in `/gsd:discuss-phase` for the relevant phase. No requirement here is locked to a specific implementation; every PCTL-* and LLM-* line below is "user-facing behavior X must exist by milestone close" not "phase Y ships exactly this design."

## v1 Requirements

### Endgame Percentile Annotations (PCTL)

Surfaces global "top X% / bottom Y%" annotations on selected Endgame metrics, scoped to the SEED-019 Tier-1 / Tier-2 set. Renders only when the user's sample size clears a metric-specific reliability gate; the raw value always stays — the chip is additive social context, not a replacement metric.

- [ ] **PCTL-01**: A global empirical-CDF benchmark artifact exists for each in-scope Endgame metric (Tier-1 skill-isolating gap metrics + Tier-2 raw rates) — produced through the canonical `/benchmarks` CTE (lichess_username join, `bic.status='completed'`, sparse-cell `(2400, classical)` exclusion, equal-footing opponent filter) and locked into `app/services/endgame_zones.py` with TS codegen drift-guard.
- [ ] **PCTL-02**: For each in-scope metric, the backend interpolates the user's value against the CDF and emits a nullable `{metric}_percentile` field (0–100) alongside existing value / CI / zone fields. The field is `null` when the user's sample size falls below the metric's reliability gate.
- [ ] **PCTL-03**: Each in-scope Endgame card renders a compact percentile chip beside the metric value when `{metric}_percentile != null`. Phrasing is asymmetric ("top X%" above median, "bottom Y%" below) with a neutral fallback near the median; rounding is honest (no spurious decimals).
- [ ] **PCTL-04**: Tier-2 (raw rate) percentile chips carry honest popover copy: the chip is bragging context, not a skill-isolating signal, and largely tracks the user's rating tier. Tier-1 (gap / ΔES) chips frame the percentile as skill-isolating because eval-baseline adjustment removes the rating proxy.
- [ ] **PCTL-05**: Percentile annotations render with desktop and mobile parity across every affected card (per CLAUDE.md mobile-parity rule) and use theme-driven colors (no hard-coded colors).
- [ ] **PCTL-06**: A misleading percentile is worse than none. Every in-scope metric has an explicit minimum-N reliability gate; below the gate, no chip renders and no percentile is emitted to the LLM.

### LLM Statistical Reasoning (LLM)

Reworks the endgame-insights LLM payload + prompt so the model can reason over the v1.17 statistical-rigor metric set (Endgame Score Gap, Achievable Score Gap, Section 2 ΔES Score Gap family, Time Pressure hypothesis tests) using p-values, confidence intervals, and the new percentile annotations, while preserving the prior decision that the cohort `zone` field — not significance — gates whether a metric is narrated.

- [ ] **LLM-01**: The endgame-insights payload exposes per-metric p-values, confidence interval bounds, and percentile fields for the v1.17 statistical-rigor metric set, alongside the existing `zone` + `sample_quality` fields. Existing metrics retain their current shape; the additions are non-breaking optional fields.
- [ ] **LLM-02**: The endgame-insights system prompt teaches the LLM to reason over CIs and percentiles explicitly — e.g. "your value sits at X with 95% CI [Y, Z], placing you in the top P% of all players" — without re-licensing the small-but-significant narration pattern that motivated `feedback_llm_significance_signal.md`. The cohort `zone` field remains the gate for whether a metric is narrated at all; CIs and p-values inform *how* the narration is phrased once a zone-driven decision to narrate has been made.
- [ ] **LLM-03**: The prompt resolves the tension with `feedback_llm_significance_signal` by either (a) tightening cohort bands further so the zone signal already captures practical significance, or (b) passing raw p-values + CIs with explicit guardrail copy in the system prompt forbidding "small but significant" framings. Final choice deferred to the LLM phase's `/gsd:discuss-phase`; both must be considered with rationale recorded in the decision log.
- [ ] **LLM-04**: The endgame-insights prompt narrates the Phase 85.1 / 87.2 / 87.6 / 88 metrics with the new statistical depth where the existing prompt has either silence or generic templating — at least Section 1 Endgame Score Gap & Achievable Score Gap, Section 2 ΔES Score Gap family, and Time Pressure score-curve verdicts must benefit measurably from the rework.
- [ ] **LLM-05**: Where percentile annotations (PCTL-02) are emitted on in-scope metrics, the LLM payload includes them and the prompt teaches the model to weave the percentile into narration naturally without doubling up on the cohort zone signal.
- [ ] **LLM-06**: The endgame-insights prompt version bumps cleanly (current is `endgame_v35`); cache invalidation is automatic via the `_PROMPT_VERSION` cache key. Backwards compatibility with older cached reports is preserved (do not retroactively invalidate prior reports beyond the prompt-version cache mechanism already in place).
- [ ] **LLM-07**: At least one UAT pass against real production users (the same `endgame_v23` → `endgame_v35` UAT cadence used in v1.16 / v1.17) verifies the rework lands an observable improvement on a representative sample — short-history users, sparse-section users, and full-history users included.

## Future Requirements

- Tier-4 per-type breakdown percentiles (per-class Conv / Recov / Score / Score Gap) — deferred unless per-user samples deepen materially. Captured in SEED-019 §Tier 4.
- Opening insights percentile annotations and LLM reasoning rework — out of scope for v1.19, candidate for a future Opening Insights v2 milestone.

## Out of Scope

- Re-introducing the retracted Phase 87.3 percentile composite — superseded by Phase 87.6 (logistic stretch around Actual ELO). v1.19 *annotates* metrics with percentiles, does not *replace* any metric's value with one.
- Per-user-ELO-cell comparison pools for percentile annotations — SEED-019 deliberately ships global-only comparison; the bragging-rights framing is the explicit product call.
- A separate "verdict" field on LLM payloads alongside `zone` — prior decision (`feedback_llm_significance_signal.md`) stands. The LLM phase resolves the tension via prompt guardrails on raw CIs/p-values, not via a parallel verdict signal.
- Tactics / per-move-quality narration — gated on client-side Stockfish or eval coverage expansion (SEED-012), out of v1.19 scope.

## Traceability

To be filled by `gsd-roadmapper` when the v1.19 roadmap is generated.
