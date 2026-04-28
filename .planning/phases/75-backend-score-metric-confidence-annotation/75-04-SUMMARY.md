---
phase: 75
plan: 04
subsystem: planning
tags:
  - planning
  - requirements
  - documentation
requires: []
provides:
  - "Amended INSIGHT-SCORE-04 (trinomial Wald + half-width buckets) and INSIGHT-SCORE-06 (confidence + p_value) in REQUIREMENTS.md"
affects:
  - .planning/REQUIREMENTS.md
tech-stack:
  added: []
  patterns:
    - "Doc-and-code sync: requirements prose mirrors implementation decisions D-05/D-09 from 75-CONTEXT.md"
key-files:
  created:
    - .planning/phases/75-backend-score-metric-confidence-annotation/75-04-SUMMARY.md
  modified:
    - .planning/REQUIREMENTS.md
key-decisions:
  - "Adopt trinomial Wald CI in REQUIREMENTS prose (D-05) — variance (W + 0.25·D)/N − score² is the actual variance of the chess result distribution; binomial Wilson over-states uncertainty when draws are common"
  - "Half-width buckets ≤ 0.10 → high, ≤ 0.20 → medium, else low (strict ≤ boundaries)"
  - "API contract gains both confidence and p_value (D-09); p_value computed via the same Z-statistic that drives the half-width — no extra math"
  - "loss_rate and win_rate are dropped cleanly in Phase 75 because the only consumer is the v1.14 frontend (Phase 76) in this same milestone"
metrics:
  duration_minutes: 3
  tasks_completed: 1
  files_modified: 1
  completed: 2026-04-28
---

# Phase 75 Plan 04: REQUIREMENTS amendment for trinomial Wald + p_value Summary

Applied the two REQUIREMENTS.md amendments locked in 75-CONTEXT.md (D-05 amends INSIGHT-SCORE-04; D-09 amends INSIGHT-SCORE-06) so the v1.14 milestone source-of-truth document reflects what Phase 75 actually ships: trinomial Wald CI (not Wilson) with half-width buckets, and an API contract that includes both `confidence` and `p_value`.

## Objective

Keep the milestone REQUIREMENTS document in sync with Phase 75 implementation. The default-direction Wilson approach in INSIGHT-SCORE-04 over-states uncertainty when draws are common, so Phase 75 pivots to the trinomial Wald formula (the standard for chess match statistics: BayesElo, Ordo). D-09 also extends the API contract to include `p_value` alongside `confidence`. Both amendments need to land at Phase 75 commit time so doc and code stay aligned.

Pure documentation update. One file modified. No code, no tests.

## Tasks

### Task 1: Amend INSIGHT-SCORE-04, INSIGHT-SCORE-06, and footer

Three surgical edits to `.planning/REQUIREMENTS.md`. Diff confirms only lines 19, 21, and 68 (the two amended bullets and the footer) changed; INSIGHT-SCORE-01/-02/-03/-05/-07, INSIGHT-UI-01..07, the milestone-goal paragraph, the Future / Out-of-Scope sections, and the traceability table are all untouched.

**Commit:** `d153a2f` — docs(75-04): amend INSIGHT-SCORE-04 (trinomial Wald) and -06 (add p_value)

#### Edit 1 — INSIGHT-SCORE-04

**Before:**

> - [ ] **INSIGHT-SCORE-04**: Compute Wilson 95% confidence interval on score per (entry_position, candidate_move) pair. Bucket each surviving finding to `confidence: "low" | "medium" | "high"` based on Wilson half-width (or equivalent p-value bucket). Exact bucket boundaries resolved during Phase 75 `/gsd-discuss-phase`; default direction: `high` = LB clears the effect-size threshold; `medium` = LB clears 0.50 but not the threshold; `low` = LB doesn't clear 0.50 but observed score does.

**After:**

> - [ ] **INSIGHT-SCORE-04**: Compute a **trinomial Wald 95% confidence interval** on score per (entry_position, candidate_move) pair. The formula uses per-game variance `(W + 0.25·D)/N − score²` (the actual variance under the trinomial result distribution X ∈ {0, 0.5, 1}) rather than the binomial Wilson approximation, which over-states uncertainty when draws are common. Standard formula for chess match statistics (BayesElo, Ordo). Bucket each surviving finding to `confidence: "low" | "medium" | "high"` based on the half-width: `≤ 0.10 → high`, `≤ 0.20 → medium`, else `low`. Strict `≤` boundaries. Pure Python `math` only — no scipy dependency. Bucket boundaries live in `opening_insights_constants.py` so they can be retuned against real data without touching service code.

#### Edit 2 — INSIGHT-SCORE-06

**Before:**

> - [ ] **INSIGHT-SCORE-06**: Extend the `OpeningInsightFinding` API contract with a `confidence: "low" | "medium" | "high"` field. The existing `severity: "major" | "minor"` field stays, so the frontend can render both severity (effect size) and confidence (annotation) per finding without overloading either.

**After:**

> - [ ] **INSIGHT-SCORE-06**: Extend the `OpeningInsightFinding` API contract with two new fields: `confidence: "low" | "medium" | "high"` (the half-width bucket from INSIGHT-SCORE-04) and `p_value: float` (two-sided test of observed score vs the 0.50 pivot, computed via the same Z-statistic that drives the half-width). The existing `severity: "major" | "minor"` field stays, so the frontend can render severity (effect size), confidence (precision), and a tooltip-grade p_value per finding without overloading any one cue. Phase 75 also drops `loss_rate` and `win_rate` cleanly — only consumer is the v1.14 frontend (Phase 76) in this same milestone.

#### Edit 3 — Footer

**Before:**

> *Last updated: 2026-04-28 — milestone v1.14 opened. 14/14 requirements mapped (INSIGHT-SCORE-01..07 → Phase 75; INSIGHT-UI-01..07 → Phase 76).*

**After:**

> *Last updated: 2026-04-28 — milestone v1.14 opened. 14/14 requirements mapped (INSIGHT-SCORE-01..07 → Phase 75; INSIGHT-UI-01..07 → Phase 76). Phase 75 amendments: INSIGHT-SCORE-04 pivots from Wilson to trinomial Wald with half-width-based buckets (D-05); INSIGHT-SCORE-06 extends API contract to include `p_value` alongside `confidence` (D-09).*

## Verification

All seven automated checks specified in the plan pass:

- `trinomial Wald 95% confidence interval` present
- `≤ 0.10 → high` present
- `≤ 0.20 → medium` present
- `p_value: float` present
- `two-sided test of observed score` present
- `Phase 75 amendments` present in footer
- `Wilson 95% confidence interval` no longer appears anywhere in the file

`git diff --stat` confirms scope: `1 file changed, 3 insertions(+), 3 deletions(-)`. The traceability table at the bottom is unchanged (INSIGHT-SCORE-04 → 75, INSIGHT-SCORE-06 → 75).

## Cross-references

- **D-05** (75-CONTEXT.md): Amends INSIGHT-SCORE-04 from Wilson to trinomial Wald with half-width buckets. Implementation lives in `app/services/opening_insights_service.py::_compute_confidence` (Plan 03). Bucket constants live in `app/services/opening_insights_constants.py`.
- **D-09** (75-CONTEXT.md): Adds `p_value: float` to the `OpeningInsightFinding` API contract. Implementation lives in `app/schemas/opening_insights.py::OpeningInsightFinding` (Plan 02).
- **Phase 76** picks up the amended INSIGHT-SCORE-06 contract: the frontend will surface `severity`, `confidence`, and `p_value` (the latter as a tooltip-grade cue) on Opening Insights cards and Move Explorer rows.

## Deviations from Plan

None. Plan executed exactly as written. Three surgical edits, all verbatim from the plan's `<action>` block, all seven verification greps pass, diff scope confirmed at three lines.

## Self-Check: PASSED

- FOUND: `.planning/REQUIREMENTS.md` (modified)
- FOUND: `.planning/phases/75-backend-score-metric-confidence-annotation/75-04-SUMMARY.md` (created)
- FOUND commit: `d153a2f` (verified via `git log --oneline`)
