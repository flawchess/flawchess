# Requirements: FlawChess — v1.19 Endgame Percentiles & LLM Statistical Reasoning

**Defined:** 2026-05-22
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary on endgame performance and an auto-generated opening-strengths/weaknesses report.

**Milestone goal:** Close SEED-019 by surfacing global percentile annotations on Tier-1 / Tier-2 Endgame metrics, and rework the endgame-insights LLM prompt + payload so it can reason explicitly over the v1.17 metric set (Endgame Score Gap, Achievable Score Gap, Section 2 ΔES Score Gap family, time-pressure hypothesis tests) using p-values, confidence interval bounds, and percentiles, with prompt guardrails that prevent narrating small-but-significant findings.

**Source:** `.planning/seeds/SEED-019-global-percentile-annotations-on-endgame-metrics.md` (open) and recent v1.17 statistical-rigor work (Phase 85.1, 86, 87.2, 87.6, 88) that exposed new server-side test statistics not currently surfaced to the LLM.

**Scope discipline:** The requirements below are directional and category-level. Per-phase scope (which Tier-1/Tier-2 metrics ship in the first cut, whether Tier-4 is in/out, whether to pass raw CIs vs. derived narration tags, LLM prompt version pivots) is refined in `/gsd:discuss-phase` for the relevant phase. No requirement here is locked to a specific implementation; every PCTL-* and LLM-* line below is "user-facing behavior X must exist by milestone close" not "phase Y ships exactly this design."

## v1 Requirements

### Endgame Percentile Annotations (PCTL)

Surfaces global "top X%" annotations on selected Endgame metrics, scoped to the SEED-019 Tier-1 / Tier-2 set. Always rendered as "top X%" (a user at p1 reads "top 99%", a user at p99 reads "top 1%") — NO "bottom X%" wording. Renders only when the user's sample size clears a metric-specific reliability gate; the raw value always stays — the chip is additive social context, not a replacement metric.

- [x] **PCTL-01**: A global empirical-CDF benchmark artifact exists for each in-scope Endgame metric — the **4 chipped ΔES metrics** per the SEED-019 empirical refinement (`reports/benchmarks-gap-metrics-percentile-candidacy.md`, 2026-05-22): Endgame Score Gap, Achievable Score Gap, Parity Score Gap (Section 2), Conversion Score Gap (Section 2). Recovery Score Gap and the 3 raw % gauges are intentionally excluded (Recovery is opponent-confounded with inverted rating coupling; raw gauges would be redundant chips on cards whose ΔES row is already chipped). The artifact is produced through the canonical `/benchmarks` CTE (lichess_username join, `bic.status='completed'`, sparse-cell `(2400, classical)` exclusion, equal-footing opponent filter, game-time ELO bucketing) and committed to `app/services/global_percentile_cdf.py` — separate from `endgame_zones.py` (which keeps its ZoneSpec / IQR-band shape). The module is Python-only with no TS mirror; backend interpolates user values against the CDF at request time and emits a scalar percentile in the API response (PCTL-02).
- [ ] **PCTL-02**: For each in-scope metric, the backend interpolates the user's value against the CDF and emits a nullable `{metric}_percentile` field (0–100) alongside existing value / CI / zone fields. The field is `null` when the user's sample size falls below the metric's reliability gate.
- [ ] **PCTL-03**: Each chipped row renders a compact percentile chip beside the metric value when `{metric}_percentile != null`. Phrasing always uses the "top X%" form (NO "bottom X%" wording): a user at p1 renders as "top 99%", a user at p99 renders as "top 1%", neutral fallback near the median (e.g. "top 50%"). Rounding is honest (no spurious decimals).
- [ ] **PCTL-04**: Chip popovers carry **metric-aware framing**: low-d metrics (Endgame Score Gap, Achievable Score Gap, Parity ΔES) frame the percentile as **skill-isolating** ("mostly independent of rating — reveals endgame ability separate from overall strength"); the high-d Conversion ΔES chip frames the percentile as **improvement-focus** ("tracks rating closely — if you're in the lower tiers here, this is one of the biggest single improvements available to your ELO"). Both flavors serve the "what should I focus on to improve?" goal for different segments of the user base.
- [ ] **PCTL-05**: Percentile annotations render with desktop and mobile parity across every affected card (per CLAUDE.md mobile-parity rule) and use theme-driven colors (no hard-coded colors).
- [ ] **PCTL-06**: A misleading percentile is worse than none. Every in-scope metric has an explicit minimum-N reliability gate; below the gate, no chip renders and no percentile is emitted to the LLM.
- [ ] **PCTL-07**: The percentile chip is a *trait* of the user, not a *view* of their data — it is computed from a canonical slice of the user's games (status='completed' + ±100 ELO opponent at game time + sparse-cell `(2400, classical)` exclusion + 36-month recency + standard variant, pooled across TCs with no per-TC cap) that mirrors the benchmark cohort CTE, and is independent of UI filter state. Toggling recency / opponent-strength / TC / platform / rated / opponent-type filters does not change the chip. The row's filter-applied metric value continues to display per the existing per-request compute; chip tooltip copy makes the dual-value framing explicit.
- [x] **PCTL-08**: Each user's canonical-slice value and percentile per in-scope metric are persisted in a `user_benchmark_percentiles` table keyed by `(user_id, metric)` with columns for `value`, `percentile`, `n_games`, `cdf_snapshot`, and `computed_at`. `cdf_snapshot` records which `GLOBAL_PERCENTILE_CDF` revision the percentile was looked up against, enabling re-lookup without recomputing the value when the benchmark snapshot refreshes.
- [x] **PCTL-09**: Canonical-slice values are computed in two stages aligned with the two-lane import pipeline: Stage A computes the eval-independent `score_gap` as a background task at import-job completion (does not extend import latency); Stage B computes the three eval-dependent metrics (`achievable_score_gap`, `section2_score_gap_conv`, `section2_score_gap_parity`) as a background task at Stockfish cold-drain completion. Chips light up incrementally — `score_gap` is available within seconds-to-minutes of import completion, the three eval-dependent chips when cold drain wraps.
- [ ] **PCTL-10**: A `scripts/backfill_user_percentiles.py` script exists to populate `user_benchmark_percentiles` for existing users on each environment in a single batch — required so the chip lights up for the entire user base on rollout, not just users who import after Phase 94.1 ships. The script takes `--target dev|prod` (mirroring `scripts/import_stress_monitor.py`'s convention — `dev` connects to local Docker on `localhost:5432`, `prod` connects via the `bin/prod_db_tunnel.sh` tunnel on `localhost:15432`), is idempotent under UPSERT semantics, supports `--user-id` / `--metric` narrowing for testing, and emits a per-metric summary (rows upserted / skipped per inclusion-floor reason).

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

| Requirement | Phase | Status |
|-------------|-------|--------|
| PCTL-01 | Phase 93 | Complete |
| PCTL-02 | Phase 94 | Pending |
| PCTL-03 | Phase 94 | Pending |
| PCTL-04 | Phase 94 | Pending |
| PCTL-05 | Phase 94 | Pending |
| PCTL-06 | Phase 94 | Pending |
| PCTL-07 | Phase 94.1 | Pending |
| PCTL-08 | Phase 94.1 | Complete |
| PCTL-09 | Phase 94.1 | Complete |
| PCTL-10 | Phase 94.1 | Pending |
| LLM-01 | Phase 95 | Pending |
| LLM-02 | Phase 95 | Pending |
| LLM-03 | Phase 95 | Pending |
| LLM-04 | Phase 95 | Pending |
| LLM-05 | Phase 95 | Pending |
| LLM-06 | Phase 95 | Pending |
| LLM-07 | Phase 95 | Pending |

**Coverage:** 17/17 v1 requirements mapped (PCTL-01..10 + LLM-01..07). No orphans.
