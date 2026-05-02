---
phase: 75
plan: 03
subsystem: backend/openings-insights
tags:
  - openings
  - insights
  - service
  - repository
  - tdd
requirements:
  - INSIGHT-SCORE-01
  - INSIGHT-SCORE-02
  - INSIGHT-SCORE-03
  - INSIGHT-SCORE-04
  - INSIGHT-SCORE-05
  - INSIGHT-SCORE-06
dependency_graph:
  requires:
    - .planning/phases/75-backend-score-metric-confidence-annotation/75-01-SUMMARY.md
    - .planning/phases/75-backend-score-metric-confidence-annotation/75-02-SUMMARY.md
    - app/services/opening_insights_constants.py (Plan 01 score-based constants)
    - app/schemas/opening_insights.py (Plan 02 confidence + p_value contract)
  provides:
    - app/services/opening_insights_service.py::_compute_confidence
    - score-based _classify_row and SQL HAVING gate
    - end-to-end confidence + p_value population on OpeningInsightFinding
  affects:
    - tests/services/test_opening_insights_service.py
    - tests/repositories/test_opening_insights_repository.py
tech_stack:
  added: []
  patterns:
    - trinomial Wald 95% CI half-width bucketing as a pure-Python helper
    - direct score-vs-threshold comparison (numerically stable on IEEE-754 boundaries)
    - SQL HAVING gate using CTE-internal score expression
key_files:
  created:
    - .planning/phases/75-backend-score-metric-confidence-annotation/75-03-SUMMARY.md
  modified:
    - app/services/opening_insights_service.py
    - app/repositories/openings_repository.py
    - tests/services/test_opening_insights_service.py
    - tests/repositories/test_opening_insights_repository.py
decisions:
  - "D-11 — score-based _classify_row, strict <=/>= boundaries, symmetric"
  - "D-05/D-06 — trinomial Wald variance, half-width buckets in pure stdlib"
  - "D-07 — confidence/p_value computed post-aggregation in Python (not SQL)"
  - "D-08 — SQL HAVING uses score gate (n>=10 AND (score<=0.45 OR score>=0.55))"
  - "D-09 — drop loss_rate / win_rate cleanly; populate confidence + p_value"
  - "Rule 1 fix — switched _classify_row from delta-based to direct score-vs-threshold comparison; 0.45-0.50 != -0.05 in IEEE-754 but 0.50-0.05 == 0.45 exactly, preserving strict-boundary semantics"
metrics:
  duration_seconds: ~1500
  completed_at: "2026-04-28T11:30:00Z"
  tasks: 4
  files_modified: 4
  commits: 4
---

# Phase 75 Plan 03: Service + repository score-metric pipeline summary

**One-liner:** Wire the Phase 75 score metric and trinomial Wald confidence end-to-end across the service classifier, repository HAVING gate, and finding construction, so `POST /api/insights/openings` returns score-based classification with `confidence` + `p_value` annotations and `loss_rate`/`win_rate` are gone from the contract.

## Outcome

Plan 03 turns the Plan 01 constants and Plan 02 schema into actual end-to-end behavior. Four production / test files modified, one transient broken-import state from Wave 1 resolved, full pytest + ty + ruff green.

### Service module (`app/services/opening_insights_service.py`)

- **Imports:** dropped the `OPENING_INSIGHTS_LIGHT_THRESHOLD` import (no longer exists). Added `import math` and a five-line aliased import of the new score / confidence constants (`SCORE_PIVOT`, `MINOR_EFFECT`, `MAJOR_EFFECT`, `CONFIDENCE_HIGH_MAX_HALF_WIDTH`, `CONFIDENCE_MEDIUM_MAX_HALF_WIDTH`).
- **Removed dead constant:** `DARK_THRESHOLD = 0.60` (Phase 70 hard-coded percent gate). The Phase 70 banner block was rewritten to reference the Phase 75 constants and the CI consistency test.
- **`_classify_row` rewrite (D-11):** operates on `score = (W + 0.5·D) / N`, compares directly against precomputed `SCORE_PIVOT ± MINOR_EFFECT` / `± MAJOR_EFFECT` thresholds. Strict `<=` / `>=` boundaries (D-03), symmetric on both sides.
- **`_compute_confidence` helper added (D-05/D-06):** trinomial Wald variance `(W + 0.25·D)/N − score²`, clamped at zero; SE = sqrt(var/N); half-width = 1.96·SE; bucket per `CONFIDENCE_HIGH_MAX_HALF_WIDTH` (0.10) and `CONFIDENCE_MEDIUM_MAX_HALF_WIDTH` (0.20). p_value via `math.erfc(|z|/sqrt(2))`. Pure stdlib only (no scipy). SE=0 guard returns `("high", 1.0)` for all-draws and `("high", 0.0)` for all-wins/all-losses.
- **`compute_insights` wiring (D-09):** the `OpeningInsightFinding` constructor now passes `score`, `confidence`, `p_value` and no longer passes `loss_rate` / `win_rate`. Field order in the constructor preserved; everything else (attribution, dedupe, ranking, caps) is metric-agnostic and unchanged.

### Repository module (`app/repositories/openings_repository.py`)

- **Imports updated:** dropped `OPENING_INSIGHTS_LIGHT_THRESHOLD`; added `OPENING_INSIGHTS_SCORE_PIVOT`, `OPENING_INSIGHTS_MINOR_EFFECT`, and `OPENING_INSIGHTS_MAJOR_EFFECT` (the last suppressed with `# noqa: F401` — kept for docstring traceability and as a future hook if the SQL gate ever moves to major-only).
- **HAVING clause (D-08):** rewrote `query_opening_transitions` HAVING to a score-based effect-size gate. Three new locals (`score_expr`, `weakness_threshold`, `strength_threshold`) are computed before the `select(...)` chain so the `.having(...)` block can reference them cleanly. Final gate:
  ```python
  having(
      and_(
          n_games >= OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE,  # 10
          or_(
              score_expr <= weakness_threshold,  # 0.45
              score_expr >= strength_threshold,  # 0.55
          ),
      )
  )
  ```
  The `n_games >= 10` floor is automatic — Plan 01 already dropped the constant from 20 to 10, so the SQL picks up the new value without a change here.
- **Docstring update:** the HAVING-summary sentence in `query_opening_transitions` now says `n>=10 candidates whose chess score (W + 0.5·D)/N is at most 0.45 (weaknesses) or at least 0.55 (strengths). Phase 75 D-08; replaces the Phase 70 win_rate/loss_rate gate.`

### Service tests (`tests/services/test_opening_insights_service.py`)

- **Classifier boundary tests rewritten** (D-03 / D-11): five new tests at exact score boundaries — neutral (0.46, 0.54), minor weakness (0.45 exactly), major weakness (0.40 exactly), minor strength (0.55 exactly), major strength (0.60 exactly). The old loss_rate/win_rate boundary tests (0.55, 0.551, 0.60, 0.599) are deleted.
- **MIN_GAMES floor tests rewritten** (D-04): assert `MIN_GAMES_PER_CANDIDATE == 10`, plus a test that the classifier itself does not gate on n (the SQL HAVING owns that floor).
- **Seven new `_compute_confidence` boundary tests** (D-05 / D-06):
  - `test_compute_confidence_high_at_large_n` — n=400, half-width≈0.039 → "high"
  - `test_compute_confidence_medium_at_moderate_n` — n=30, half-width≈0.143 → "medium"
  - `test_compute_confidence_low_at_n10_extreme_score` — n=10, half-width≈0.248 → "low"
  - `test_compute_confidence_just_inside_medium_boundary` — n=25, half-width≈0.157 → "medium"
  - `test_compute_confidence_p_value_at_score_050_is_one` — score=0.50 → p_value≈1.0
  - `test_compute_confidence_se_zero_all_draws` — variance=0 → ("high", 1.0)
  - `test_compute_confidence_se_zero_all_wins` — variance=0, score≠0.5 → ("high", 0.0)

  No "exact 0.10 / 0.20" half-width tests: 0.10/1.96 and 0.20/1.96 are irrational, so no integer-row half-width can land exactly on either boundary. Every constructible synthetic row sits strictly inside a bucket — those are what we test.
- **Ranking test rebuilt** with score-based row data (2 minor weaknesses at score=0.42 + 1 major at score=0.30) so the "major-first then n_games-desc within tier" assertions hold under the new gate.
- **End-to-end smoke test added:** `test_compute_insights_populates_confidence_and_p_value` verifies that `compute_insights` returns a finding with `score`, `confidence ∈ {low, medium, high}`, and `p_value ∈ [0, 1]`.

### Repository tests (`tests/repositories/test_opening_insights_repository.py`)

- **Renamed `test_min_games_per_candidate_floor_at_20` → `…_at_10`** — fixtures now seed 10 vs 9 games (boundary at the new MIN_GAMES_PER_CANDIDATE=10) with score=0.0 (all-loss) framing.
- **Renamed `test_having_strict_gt_055_drops_neutrals` → `test_having_score_boundaries_drops_neutrals`** — three scenarios at n=20 covering score=0.50 (neutral, dropped), score=0.55 (strength boundary, surfaces), score=0.45 (weakness boundary, surfaces).
- **Other tests unchanged** — CTE structure, ply boundaries, has_standard_start, recency, opponent filters, color filter are all metric-agnostic. Their pre-existing fixtures (e.g. `loss_rate=0.6` from white = score=0.40) remain valid weakness rows under the new gate.

## Verification

All checks pass on the full repo, not just touched modules:

- `uv run pytest tests/services/test_opening_insights_service.py tests/repositories/test_opening_insights_repository.py tests/services/test_opening_insights_arrow_consistency.py` — **52/52 passed**
- `uv run pytest tests/routers/test_insights_openings.py` — **6/6 passed**
- `uv run pytest -q` (full suite) — **1140/1140 passed**
- `uv run ty check app/ tests/` — **All checks passed**
- `uv run ruff check .` — **All checks passed**
- `uv run ruff format --check` on the four touched files — clean (project-wide pre-existing format drift in unrelated files is not Plan 03 scope).

## Tasks executed

| # | Task | Commit |
| - | ---- | ------ |
| 1 | Rewrite `_classify_row`, add `_compute_confidence`, remove `DARK_THRESHOLD`, wire confidence/p_value into `compute_insights` | `26ca382` |
| 2 | Rewrite `query_opening_transitions` HAVING for score-based effect-size gate | `779be4a` |
| 3 | Update service tests (boundary tests, MIN_GAMES, confidence boundary tests, ranking, smoke test) | `191f947` |
| 4 | Update repository tests (10/9 floor, score-boundary HAVING test, docstring) | `3540715` |

## Deviations from Plan

### Rule 1 — Bug fix in `_classify_row` boundary semantics

**Found during:** Task 3 verification (`test_classify_row_minor_weakness_at_score_045_exact` failed with `assert None is not None`).

**Issue:** The plan's `_classify_row` body computed `delta = score - SCORE_PIVOT` and compared `delta <= -MINOR_EFFECT`. With the boundary row n=20, w=5, d=8, l=7, the computed score is exactly 0.45 (representable as a float since 9/20 == 0.45), but `0.45 - 0.50 == -0.04999999999999999` in IEEE-754, which fails the strict `<=` test. The same artifact affects the score=0.40 and score=0.60 boundaries. The plan's `must_haves.truths` explicitly require `score=0.45 → minor weakness` and `score=0.40 → major weakness` to classify on the boundary, so this is a correctness bug in the canonical formulation.

**Fix:** Switched `_classify_row` to compare `score` directly against precomputed thresholds (`SCORE_PIVOT - MINOR_EFFECT`, etc.) rather than computing a delta. `0.50 - 0.05 == 0.45` exactly in IEEE-754, so `score <= 0.45` evaluates correctly on boundary rows. The classifier docstring documents the rationale. No test data needed adjustment.

**Files modified:** `app/services/opening_insights_service.py`

**Commit:** `191f947` (folded into the Task 3 test+service joint commit because the fix and the new boundary tests ship together).

This adjustment preserves CONTEXT.md D-03 / D-11 semantics ("strict <= / >= boundaries"). Rule 1 (bug fix during execution) applies — classifier intent is unambiguous, the fix is purely numerical, and no architectural change is involved.

## Threat Flags

None new. Plan 03's threat register (T-75-03 information disclosure on p_value, T-75-04 DoS on Wald math, T-75-05 SQL HAVING tampering) all dispositioned `accept` — no new trust boundary, no new auth surface, no user-controlled data flowing into the SQL gate.

## Self-Check: PASSED

Files exist on disk:

- `app/services/opening_insights_service.py` — FOUND (modified)
- `app/repositories/openings_repository.py` — FOUND (modified)
- `tests/services/test_opening_insights_service.py` — FOUND (modified)
- `tests/repositories/test_opening_insights_repository.py` — FOUND (modified)
- `.planning/phases/75-backend-score-metric-confidence-annotation/75-03-SUMMARY.md` — FOUND (created)

Commits exist on branch:

- `26ca382` — `feat(75-03): rewrite opening_insights_service for score classifier and Wald confidence` — FOUND
- `779be4a` — `feat(75-03): rewrite query_opening_transitions HAVING for score gate` — FOUND
- `191f947` — `test(75-03): rewrite service tests for score classifier and confidence helper` — FOUND
- `3540715` — `test(75-03): rewrite repository HAVING tests for score-based gate` — FOUND

## Next Steps

Phase 75 backend work is now complete on this worktree. Wave 2 has consumed Plan 01's constants foundation, Plan 02's contract changes, and Plan 04's REQUIREMENTS amendments. After this worktree merges, the milestone moves to Phase 76 (frontend consumption of `confidence` and `p_value`) which will refactor `getArrowColor()` to use the score-based exports already shipped in Plan 01.
