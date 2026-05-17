> **SUPERSEDED by Phase 87.6** (2026-05-17): The K=450 additive formula documented here is replaced by FIDE Performance Rating computed independently for endgame and non-endgame game subsets. The "lifts up / holds back" interpretation is preserved; Non-Endgame ELO is now a first-class data point. See `.planning/milestones/v1.17-phases/87.6-endgame-elo-via-performance-rating/` for the current design.

---
title: Endgame ELO rebuild — additive mapping from Endgame Score Gap (eg − non_eg)
date: 2026-05-17
context: Captured during `/gsd-explore` reviewing Phase 87.4 (Conversion ELO). UAT surfaced two issues — (1) gaps to actual ELO of up to 500 with strong players *always* above actual ELO, and (2) high volatility of the per-window series. Root cause traced via §3.1.6 vs §3.2.2 of `reports/benchmarks-latest.md` to the input metric, not the affine recenter or calibration knob. Switching from Conv ΔES (conv-bucket-only, eval-baselined) to Endgame Score Gap (eg − non_eg, self-baselined) eliminates the structural strong-player bias and reduces volatility by enlarging the sample. The "Endgame ELO holds back or lifts up actual ELO" interpretation — which Phase 87.4 traded away — is restored by construction.
supersedes:
  - .planning/notes/endgame-skill-dropped-conversion-elo.md
related_files:
  - app/services/endgame_service.py
  - app/services/endgame_zones.py
  - app/services/insights_service.py
  - app/services/insights_llm.py
  - app/schemas/endgames.py
  - app/repositories/endgame_repository.py
  - frontend/src/components/charts/ConversionEloTimelineSection.tsx
  - frontend/src/pages/Endgames.tsx
  - reports/benchmarks-latest.md
related_phases: [57, 87.3, 87.4, 87.5]
---

# Endgame ELO rebuild on Endgame Score Gap

## The bias finding

Two facts from `reports/benchmarks-latest.md` decide the redesign:

| Source                  | Metric                                | ELO marginal p50 sweep            | Cohen's d  | Verdict      |
| ----------------------- | ------------------------------------- | --------------------------------- | ---------- | ------------ |
| §3.2.2 (Phase 87.4 in)  | Conv ΔES (conv-bucket only)           | −14.0pp → −0.3pp across 800→2400  | **1.62**   | **keep**     |
| §3.1.6 (Phase 87.5 in)  | Endgame Score Gap (eg − non_eg)       | −3.6pp → +0.1pp across 800→2400   | **0.17**   | **collapse** |

The Conv ΔES sigmoid bias is real and large — strong players systematically outperform the Lichess population-average sigmoid baseline because the sigmoid does not condition on rating. Phase 87.4's affine recenter inherited that bias by construction:

```
s = clamp(0.5 + ALPHA · (conv_ΔES − PIVOT), 0.05, 0.95)
PIVOT = −0.0474  # benchmark global p50
```

A 2400 player's typical Conv ΔES is around +0.001, not −0.047. Plugged into the recenter that lands at s ≈ 0.60, then through the Phase 57 multiplicative formula it produces `endgame_elo ≫ actual_elo` regardless of how the user is actually playing relative to their peers. UAT saw 500-ELO gaps; the math predicts them.

The Endgame Score Gap metric `eg_score_gap = achievable_eg − achievable_non_eg` is a **within-player difference** measured against the same eval baseline in both phases. The sigmoid bias appears in both terms and cancels in the subtraction — which is why the ELO sweep collapses to d = 0.17. The metric is essentially flat across rating.

## The redesign

**Input metric:** windowed mean of `eg_score_gap` over a trailing 100-game window per (platform, time_control) combo. This is the same series that already drives the existing "Endgame Score Gap over Time" timeline on the Endgames page — Endgame ELO becomes a derived view of that series, not a parallel computation.

**ELO mapping — additive, no PIVOT, no affine, no Phase 57 multiplicative formula:**

```
endgame_elo = actual_elo + K · eg_score_gap
```

- At `eg_score_gap = 0`, `endgame_elo == actual_elo`. Neutral is literal zero, not a benchmark-derived constant.
- Proposed `K ≈ 450`. Calibrated from §3.1.6: p95 of `eg_score_gap ≈ +0.22` → +100 ELO at p95; p75 ≈ +0.073 → +33 ELO. p05 ≈ −0.23 → −100 ELO. To be sanity-checked against real prod timelines before locking — see `.planning/todos/pending/calibrate-endgame-elo-k.md`.
- Sign convention restores the original Phase 57 storytelling: positive `eg_score_gap` → endgame is *lifting* the rating; negative → endgame is *holding back*. The LLM section narrative reads cleanly again.

**Window inheritance:** sample-quality bands, sparse-window sentinel handling, and per-combo series scaffolding are reused from the existing Endgame Score Gap timeline. No new sample-quality logic.

## Rejected alternatives

| Alternative                                          | Why rejected                                                                                                                                                                                |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A — Smooth peer-conditional PIVOT** (Conv ΔES)    | Still uses sigmoid-biased Conv ΔES. Y-axis "ELO" silently means "where your rating would land if your endgame matched peers'" — quietly redefines the ELO scale. Bucket boundary fixed but the calibration headache remains. |
| **B — Self-baseline at row level** (Conv ΔES − user's own non-endgame Conv ΔES per row) | Equivalent to Endgame Score Gap in spirit but reinvents the aggregation. Self-baselines also get noisy at low sample counts. Score Gap already computes this at the right granularity. |
| **Drop the ELO axis, ship Score Gap only**          | Considered. Rejected because actual ELO + Endgame ELO are load-bearing for the LLM-narrated section ("your endgame is lifting your rating by 35 ELO" is the story users understand). Keep ELO units, just feed the right metric. |
| **Keep the affine recenter, retune `PIVOT`/`ALPHA`** | Treats the symptom, not the cause. Any single PIVOT against an ELO-d=1.62 metric is wrong at most rating buckets. |

## UI placement

The renamed **"Endgame ELO Timeline"** moves *out* of the "Endgame Metrics and ELO" section and *into* "Endgame Overall Performance," positioned **directly below** the existing "Endgame Score Gap over Time" chart in `frontend/src/pages/Endgames.tsx`. Rationale: the two charts now share an input series and tell the same story in different units; co-locating them lets the user read score gap and ELO impact on the same scroll position. The "Endgame Metrics and ELO" section retains the Conv / Parity / Recov gauges only — naming may need a follow-up rename (likely "Endgame Metrics" with the ELO bit excised).

## LLM payload impact

- `MetricId` Literal: `conversion_elo_gap` → `endgame_elo_gap`.
- `SubsectionId` Literal: `conversion_elo_timeline` → `endgame_elo_timeline`.
- Subsection moves from `metrics_elo` to `overall` in the section-by-section grouping. Insights narrative ownership transfers with it.
- Prose updates: the Plan 03 surface from Phase 87.4 (left intact: `[summary endgame_elo | …]` literal, `### Subsection:` header, glossary) is rewritten to reference Endgame Score Gap as the input, restore "lifts / holds back actual rating" as the headline metaphor, drop "conversion" from the wording. `_PROMPT_VERSION` bumps.

## Calibration constants to drop

The Phase 87.4 constants are deleted, not retuned:

- `PIVOT = -0.0474`
- `ALPHA = 2.025`
- `CALIBRATION_VERSION = "conv_delta_v1_260516"`
- `_affine_recenter_conv_delta(...)` helper
- `_windowed_conv_delta_es(...)` bucket-row aggregator
- `_conversion_elo_from_skill(...)` (renamed from `_endgame_elo_from_skill` — name reverts, formula is new and simpler)

Replaced by:

- `K = <calibrated value>` — single constant.
- `_endgame_elo_from_score_gap(actual_elo, eg_score_gap, K) -> int` — additive mapping with rounding/clamping rules to match the existing endgame_elo timeline contract (positive int, sensible floor/ceiling).
- Inherit the windowed `eg_score_gap` from the existing Endgame Score Gap timeline producer rather than a new aggregator.

## Out of scope

- Conv / Recov gauge centering. The §3.2.2 benchmark explicitly says these bands *should* be off-center (sigmoid bias on conversions near the score ceiling, recoveries near the floor). Re-centering them would lie about what's typical. Discussed and deferred.
- Per-(platform, TC) `K` tuning. Endgame Score Gap is ELO-collapse and only TC-review (max d = 0.34) — a single global `K` is justified for v1. Per-TC `K` flagged as a future option only if UAT reveals systematic per-TC drift.
