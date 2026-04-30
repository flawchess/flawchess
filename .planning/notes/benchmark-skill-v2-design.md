---
title: Benchmark skill v2 — collapse verdict methodology
date: 2026-04-30
context: Captured during `/gsd-explore` after the 2026-04-29 benchmark report. The current `/benchmarks` skill emits pooled rates and partial per-cell tables but does not systematically answer "can we use the same gauge bounds across cells, or do we need cell-specific bounds?". Skill v2 produces that verdict.
related_files:
  - .claude/skills/benchmarks/SKILL.md
  - reports/benchmarks-2026-04-29.md
related_seeds: [SEED-006, SEED-009]
---

# Benchmark skill v2 — collapse verdict methodology

## Goal

For every benchmarked metric, the v2 report must answer: **does the per-user distribution collapse across TC? across ELO? both? neither?** The answer drives whether gauge bounds can stay global (`theme.ts` constants), need TC-bucketed variants, ELO-bucketed variants, or full per-(TC × ELO) bucketing.

## Methodology — Cohen's d on marginals

For each metric:

1. Compute per-user values per (TC × ELO) cell. Floor: ≥10 users/cell.
2. Form **TC marginal** (4 levels: bullet/blitz/rapid/classical, pooling across ELO at user-weighted level).
3. Form **ELO marginal** (5 levels: 500-bucketed, pooling across TC).
4. Compute pairwise Cohen's d on user-level distributions:
   - TC axis: 4 marginals → 6 pairs → take **max |d|** as the headline.
   - ELO axis: 5 marginals → 10 pairs → take **max |d|** as the headline.
5. Verdict per axis (hard-coded thresholds):
   - `max |d| < 0.2` → **collapse** (negligible difference)
   - `0.2 ≤ max |d| < 0.5` → **review** (small but noticeable)
   - `max |d| ≥ 0.5` → **keep separate** (meaningful difference)
6. The two axes are evaluated independently. A metric can land at "collapse on TC, keep ELO" or vice versa.

### Why marginals (not all 20-cell pairs)

Full pairwise on 20 cells would over-reject collapse on outlier cells. Marginal-pair Cohen's d directly answers "does this dimension matter?" — which is the actual question.

### Why Cohen's d (not gauge-range relative or absolute pp)

Gauge ranges are arbitrary in some cases. Absolute pp doesn't translate across metrics with different units (rates 0–1 vs score-gap ± vs clock pressure %). Cohen's d is standardized in within-group SD units and gauge-range-independent.

### Threshold rationale

0.2 / 0.5 follow Cohen's published conventions. Hard-coded into the skill, single override flag if a future analysis wants to be stricter/looser.

## Per-metric output shape

Every metric section in the v2 report contains the same five blocks:

1. **20-cell grid** — per-user p25/p50/p75 per (TC × ELO).
2. **TC marginal table** — 4 rows (bullet/blitz/rapid/classical), columns: n_users, mean, SD, p25, p50, p75.
3. **ELO marginal table** — 5 rows (500-wide buckets), same columns.
4. **Heatmap of per-user p50** — visual sanity check for interaction effects (e.g., bullet-low-ELO behaving unlike both marginals would predict).
5. **Verdict block** — `TC_d_max = X.XX → {collapse|review|keep}`, `ELO_d_max = Y.YY → {collapse|review|keep}`.

The report ends with a **top-axis collapse summary table** listing every metric with its two verdicts in one place. This is the artifact that drives the v1.x calibration phase decisions.

## Caveats

### Time-pressure-vs-performance curves (Section 5)

The metric is per-bucket, not a single per-user value. Either:
- Run Cohen's d per time-remaining bucket (10 buckets) and aggregate (max across buckets, or weighted-mean by sample density).
- Use a curve-similarity measure (e.g., max pointwise difference normalized by curve std).

Decide during skill v2 build. The current report's Section 5 already shows the bucket-0 spread (13pp pooled-bullet vs pooled-classical) is large enough to keep separate; the question is whether mid-buckets collapse.

### Per-endgame-class breakdowns (Section 6)

Adds a third dimension (4 TC × 5 ELO × 6 classes = 120 cells). At ~50 users/cell baseline this thins to ~8 users/cell — too sparse for cell-level Cohen's d. Treat **endgame class as a separate axis**: pool across users, then ask "do per-class rates collapse across TC/ELO at the rate-of-rates level?" — i.e., is the queen→pawn ordering stable, and how much do absolute rates shift across cells?

## Decisions captured for skill v2

- Score-gap re-centering **rejected** — sub-3pp asymmetry not worth losing the round ±0.10 bounds. Skill should not propose re-centering for differences below ~5pp.
- Verdict thresholds 0.2 / 0.5 **hard-coded**.
- Cell floor: ≥10 users/cell for inclusion in marginals (matches existing skill convention).
- Output destination: `reports/benchmarks-skill-v2-YYYY-MM-DD.md` (separate from v1 output for side-by-side comparison during v2 dev).
