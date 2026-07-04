---
created: 2026-04-30T00:00:00.000Z
title: Build /benchmarks skill v2 — Cohen's d collapse verdict per metric
area: skills / analytics
files:
  - .claude/skills/benchmarks/SKILL.md
  - reports/benchmarks-skill-v2-YYYY-MM-DD.md (output)
related_notes:
  - .planning/notes/benchmark-skill-v2-design.md
related_seeds: [SEED-006, SEED-009]
---

## Why

The current `/benchmarks` skill emits pooled rates and partial per-cell tables but does not systematically answer "can we use the same gauge bounds across cells, or do we need cell-specific bounds?" — the collapse decision is the central input to SEED-006 Phase 73 (rating-bucketed zone calibration) and to SEED-009's per-TC-threshold work. Skill v2 produces that verdict deterministically.

Methodology is fully specified in `.planning/notes/benchmark-skill-v2-design.md`. This todo is the build checklist.

## What

### Deliverables

1. Updated `.claude/skills/benchmarks/SKILL.md` that produces a v2 report distinct from v1 (separate output filename for side-by-side comparison during dev).
2. Report `reports/benchmarks-skill-v2-YYYY-MM-DD.md` covering every benchmarked metric with the standard 5-block per-metric structure.
3. Top-axis collapse summary table at end of report listing every metric × {TC verdict, ELO verdict}.

### Per-metric output structure (every metric section)

1. 20-cell grid: per-user p25/p50/p75 per (TC × ELO).
2. TC marginal table: 4 rows, columns n_users / mean / SD / p25 / p50 / p75.
3. ELO marginal table: 5 rows, same columns.
4. Heatmap of per-user p50 (visual sanity check for interaction effects).
5. Verdict block: `TC_d_max = X.XX → {collapse|review|keep}` and `ELO_d_max = Y.YY → {collapse|review|keep}`.

### Verdict computation

- Per-user values per (TC × ELO) cell, floor ≥10 users/cell.
- TC marginal: 4 levels, 6 pairwise Cohen's d, take max |d|.
- ELO marginal: 5 levels, 10 pairwise Cohen's d, take max |d|.
- Thresholds (hard-coded): `< 0.2` collapse / `0.2–0.5` review / `≥ 0.5` keep separate.
- Two axes evaluated independently. Single override flag for re-running with different thresholds.

### Metrics to cover

All metrics currently in the v1 report:
- Score-gap (endgame − non-endgame), per-user diff
- Conversion rate, per-user
- Parity rate, per-user
- Recovery rate, per-user
- Endgame Skill (composite), per-user
- Endgame ELO vs Actual ELO gap, per-user
- Clock pressure at endgame entry (% of base time), per-user
- Net timeout rate, per-user

### Custom-logic metrics (decide during build)

- **Time-pressure-vs-performance curves**: per-bucket metric, not single per-user value. Either run Cohen's d per time-remaining bucket and aggregate (max across buckets, or weighted-mean by sample density), or use a curve-similarity measure. Decide based on which produces the cleaner "should we display per-TC" verdict.
- **Per-endgame-class breakdowns**: 4×5×6 = 120 cells too sparse for cell-level Cohen's d at ~50 users/cell. Treat class as a separate axis: pool per (class), then ask "do per-class rates collapse across TC/ELO at the rate level?".

## Acceptance criteria

- Running the v2 skill on the populated benchmark DB produces the report described above.
- Every metric section contains the 5 standard blocks.
- Verdict table at end has one row per metric with two verdict columns.
- v1 skill output remains accessible (don't break the existing skill yet — add v2 as parallel mode or new skill name).
- Methodology in the report header references `.planning/notes/benchmark-skill-v2-design.md` for full rationale.
