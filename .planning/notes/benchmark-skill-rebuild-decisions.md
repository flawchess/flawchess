---
title: /benchmarks skill rebuild — decisions from methodology review
date: 2026-05-30
context: Triage of a 10-point conceptual/methodical review of the /benchmarks skill and its
  benchmarks-latest.md report, plus the locked decisions for rebuilding the skill as
  deterministic code + LLM narration.
---

# /benchmarks skill rebuild — decisions

/ benchmarks today is an LLM executing ~40 inline SQL blocks via the benchmark MCP and hand-computing
Cohen's d / IQRs / midpoint drifts into a hand-written markdown report. A methodology review raised 10
points; this note records the triage and the locked decisions for the rebuild.

## Triage of the 10 review points

| # | Point | Verdict | Rationale |
|---|-------|---------|-----------|
| 1 | Lichess-only cohort, raw-rating buckets, applied to chess.com users | **Not a problem (by design)** | chess.com ELO is converted to lichess ELO (or reported separately in ELO-timeline charts). Collapsed charts generalize across TC/ELO; non-collapsible metrics get TC-specific charts and/or TC+ELO-specific percentile badges. Assume chess.com ≈ lichess players modulo rating system (Glicko-1 vs Glicko-2). |
| 2 | Equal-footing bands applied to all-games UI values (estimand mismatch) | **Not a problem (by design)** | All metrics except percentile badges respond to current filter settings. Zone bands are a *stable frame of reference*, not exact IQR ranges for every filter combination. |
| 3 | Known TC mispaint shipped as "keep" | **Already being addressed** | Phase 97 shipped TC-specific Endgame Metrics cards. Phase 98 extends Endgame Type Breakdown bands to TC-mix. Phase 99 adds per-(metric,TC) percentile chips. |
| 4 | `max\|d\|` is biased/unstable as collapse statistic | **Worth improving (Phase 102)** | Bands respond to filters (see #2) so the stakes are lower, but a more stable statistic is wanted. Candidate: metric-vs-ELO correlation (Spearman/Pearson) + TC effect measure, with round-number-band miscoverage as a sanity check. |
| 5 | Same users populate multiple ELO buckets (non-independence) | **Not a big problem** | Only the 1000 most-recent games per user are used, so ELO-boundary crossings are limited. Previously quantified and accepted. |
| 6 | No conditional-opportunity denominator floor for conv/recov | **Worth looking into (Phase 102)** | May tighten noisy per-user rates (0/3-style) that widen band tails. Not expected to change the big picture. |
| 7 | IQR-as-neutral mechanically marks 50% atypical | **Debatable, maybe revisit** | Captured as an open design question; not scheduled. |
| 8 | Classical column thin / looser selection drives biggest TC contrasts | **Acknowledged** | We may have over-conceded (e.g. TC-specific cards) to accommodate less-frequent classical players. Retro observation feeding #3 scoping, not separate work. |
| 9 | LLM-narrated report is fragile for source-of-truth constants | **Accepted — drives the rebuild** | /benchmarks should be deterministic code + LLM narration. |
| 10 | Need a full rerun; drop cross-snapshot comparison | **Accepted (Phase 102)** | Rerun after methodology changes land. Drop the in-report cross-snapshot section; Claude can still diff against a prior report on demand if the user supplies it. |

## Locked decisions for the rebuild

1. **Faithful port first, methodology second.** Phase 101 ports the *existing* methodology (max|d|, IQR
   bands, current floors) into deterministic code, validated by diffing script output against the current
   `benchmarks-latest.md` within rounding. This keeps the regression oracle clean. Phase 102 then layers
   in #4 and #6 as isolated, attributable changes. (Without the split, port bugs and intended method
   changes are entangled and port bugs hide.)

2. **Code/LLM seam: code emits numbers, LLM applies verdicts + narrates.** The deterministic script
   computes all distributions / d-values / IQRs / correlations into a structured data artifact
   (JSON + MD tables). The LLM applies the collapse thresholds to call collapse/review/keep and writes the
   prose interpretation + recommendations. **Consequence:** the Phase-101 port diff validates the
   *numbers*, not the verdicts (verdicts are LLM-produced and may vary run-to-run even when numbers are
   identical). Acceptable because verdicts derive from numbers via a fixed threshold table; if verdict
   reproducibility is ever needed, this is the knob to reconsider (move threshold application into code).

3. **Methodology scope for Phase 102: #4 + #6 only.** #4 (better collapse statistic than max|d| — likely
   ELO-correlation + TC effect size, with band-miscoverage sanity check) and #6 (conditional-opportunity
   denominator floor for conversion/recovery). #7 (IQR-as-neutral) is recorded as an open question, not
   scheduled. #1/#2/#5 dismissed by design. #3/#8 covered by Phases 97–99.

4. **Phase 102 includes the full rerun (#10)** and drops the cross-snapshot section from the report
   template.

## Phasing

- **Phase 101** — Deterministic /benchmarks generator (faithful port + numeric regression gate against
  current report).
- **Phase 102** — Benchmark methodology improvements (#4 collapse statistic, #6 conditional floor) + full
  rerun, cross-snapshot section dropped.

Both under a new milestone (v1.23 Benchmark Generator Rebuild). Phase 100 was already taken (LLM
statistical-reasoning rework, v1.22).

## Related

- Report reviewed: `reports/benchmark/benchmarks-latest.md` (2026-05-27 snapshot)
- Skill: `.claude/skills/benchmarks/SKILL.md`
- Production percentile path already deterministic: `scripts/gen_global_percentile_cdf.py`,
  `app/services/global_percentile_cdf.py`, `app/services/canonical_slice_sql.py` (Phase 93/94) — the
  right direction; this rebuild brings the zone-calibration report in line.
- Memory: `feedback_benchmark_source_of_truth`, `feedback_no_dev_db_reset_in_plans`,
  `project_benchmark_outliers_unfiltered`.
