---
phase: quick-260428-v9i
plan: 01
subsystem: opening-insights
tags: [opening-insights, ranking, statistics, wilson-interval]
provides:
  - "_wilson_bounds(p, n) helper in opening_insights_service"
  - "Wilson 95% CI ranking in _rank_section (direction-aware)"
  - "OPENING_INSIGHTS_CI_Z_95 constant (renamed from OPENING_INSIGHTS_WALD_Z_95)"
requires:
  - "OpeningInsightFinding.score and .n_games (already produced upstream)"
affects:
  - "Within-section ordering of opening insights weaknesses and strengths"
tech-stack:
  added: []
  patterns:
    - "Wilson score interval (replaces Wald CI for ranking)"
key-files:
  created: []
  modified:
    - app/services/opening_insights_service.py
    - app/services/opening_insights_constants.py
    - tests/services/test_opening_insights_service.py
    - CHANGELOG.md
decisions:
  - "Wilson 95% score interval over Wald: well-defined at boundary scores (0/11 -> upper ~0.259, not 0.000); tighter for small n; no SE=0 degeneracy"
  - "Preserve the (finding, se) tuple shape upstream — SE still feeds the UI confidence badge via compute_confidence_bucket; only _rank_section ignores SE"
  - "Use _ to mark the unused se in the sort_key closure (ruff-friendly, ty-clean)"
  - "Tests drive uncertainty via parametrized n_games (not synthetic SE) since Wilson reads n_games directly; SE inputs to _rank_section are now arbitrary"
metrics:
  duration: ~15min
  completed: 2026-04-28
---

# Quick Task 260428-v9i: Switch Opening Insights Ranking from Wald to Wilson 95% CI Summary

Replaced the Wald 95% CI bound (`score +/- 1.96 * SE`) with the Wilson 95% score interval bound for within-section ranking of opening insights — fixes Wald's SE=0 degeneracy at boundary scores (0/11 had upper bound 0.000 under Wald, claiming 100% certainty; Wilson gives ~0.259) and demotes small-N extreme findings in favor of large-N moderate ones.

## What Changed

- **`app/services/opening_insights_service.py`**:
  - Added `_wilson_bounds(p, n) -> (lower, upper)` helper above `_rank_section`. Imports `math` (new stdlib import). Defensive `n <= 0 -> (0.0, 1.0)` branch (caller guarantees `n >= MIN_GAMES_PER_CANDIDATE = 10`). Result clamped to `[0, 1]`.
  - Rewrote `_rank_section` to call `_wilson_bounds(finding.score, finding.n_games)` instead of `score +/- 1.96 * SE`. Direction logic unchanged: weakness asc by upper, strength desc by lower (negated for default ascending sort). The `_se` from the input tuple is intentionally ignored.
  - Rewrote the `_rank_section` docstring and updated two comment blocks in `compute_insights` (sections accumulator + per-section transposition) from "Wald 95% CI bound" to "Wilson 95% CI bound" with the 260428-v9i task ID.
  - Import alias updated: `OPENING_INSIGHTS_WALD_Z_95 as WALD_Z_95` -> `OPENING_INSIGHTS_CI_Z_95 as CI_Z_95`.
- **`app/services/opening_insights_constants.py`**:
  - Renamed `OPENING_INSIGHTS_WALD_Z_95` -> `OPENING_INSIGHTS_CI_Z_95` (value unchanged at 1.96).
  - Replaced docstring to describe Wilson interval usage and explicitly note that the trinomial Wald p-value in `score_confidence.py` is a separate procedure.
- **`tests/services/test_opening_insights_service.py`**:
  - Parametrized `n_games` on `_make_weakness_finding` and `_make_strength_finding` factories (default 400 preserved). Wins/losses re-derived from `score * n_games` so each fixture is internally consistent.
  - Renamed four `_rank_section` tests:
    - `test_ranking_ignores_confidence_bucket_uses_wald_bound_only` -> `..._uses_ci_bound_only`
    - `test_ranking_wald_upper_bound_tiebreak_within_same_confidence_for_weaknesses` -> `test_ranking_ci_upper_bound_tiebreak_...`
    - `test_ranking_clamps_bound_to_unit_interval` -> `test_ranking_bound_handles_boundary_scores`
    - (`test_ranking_small_n_high_effect_does_not_outrank_large_n_moderate_effect_within_bucket` and `test_ranking_strength_uses_lower_bound` kept their names; bodies updated.)
  - Recomputed expected orderings against Wilson math (precomputed via `python -c` using the formula in the plan's interfaces block, not regenerated from observed test output). All four ranking tests fail under the old Wald implementation and pass under Wilson — verified by running RED before GREEN.
  - SE inputs to `_rank_section` set to `0.0` where useful — under old Wald with SE=0 the bound collapses to score-only, giving the opposite ordering for three of the four tests, so the tests genuinely discriminate Wilson from Wald.
- **`CHANGELOG.md`**: added an `### Changed` bullet under `## [Unreleased]` describing the switch and the constant rename.
- **`frontend/src/lib/arrowColor.ts`**: not modified (already score-only, no CI math). Verified.
- **`app/services/score_confidence.py`**: not modified (trinomial Wald p-value is a separate procedure, out of scope).

## Numerical Spot Check

```
>>> _wilson_bounds(0.0, 11)
(2.78e-17, 0.2588)   # vs Wald: 0.0 (degenerate)
>>> _wilson_bounds(0.20, 10)
(0.0567, 0.5098)     # small-N: bound is wide, demotes the row
>>> _wilson_bounds(0.30, 400)
(0.2572, 0.3466)     # large-N: bound is tight, promotes the row
```

## TDD Gate Compliance

- **RED commit:** `2385530 test(quick-260428-v9i): rebaseline _rank_section tests for Wilson 95% bounds`. Verified to fail against the old Wald implementation before the GREEN commit.
- **GREEN commit:** `0715fda feat(quick-260428-v9i): switch opening-insights ranking from Wald to Wilson 95% CI`. Implementation + constant rename + CHANGELOG bullet. All gates green.
- **REFACTOR:** none needed.

## Quality Gates

| Gate | Result |
| ---- | ------ |
| `uv run ruff check app/ tests/` | clean |
| `uv run ruff format --check` (in-scope files) | clean |
| `uv run ty check app/ tests/` | zero errors |
| `uv run pytest tests/services/test_opening_insights_service.py tests/services/test_opening_insights_arrow_consistency.py` | 32 passed |
| `uv run pytest` (full suite) | 1166 passed |
| Frontend gates | not applicable (`frontend/src/lib/arrowColor.ts` not modified) |
| `grep -rn "WALD_Z_95\|OPENING_INSIGHTS_WALD_Z_95" app/ tests/ --include="*.py"` | zero results |
| `git diff app/services/score_confidence.py` | empty |

## Deviations from Plan

None — plan executed as written, with two minor adjustments documented in the plan itself:

1. The plan's `<behavior>` block first proposed `f1=0.40, n=4000` / `f2=0.30, n=100` for the weakness CI-upper tiebreak, then noted (correctly) that this would still order f2 first under Wilson and revised to `f1=0.40, n=10000` / `f2=0.30, n=50`. Used the revised fixture and verified Wilson upper bounds (f1≈0.4096, f2≈0.4375) numerically.
2. The plan's `<behavior>` listed approximate Wilson bounds (e.g. f2 upper "~0.4189"); recomputed precisely (f2 upper = 0.4375). The orderings the plan specified are still correct under the precise values.

During the initial RED phase, the new tests happened to pass against the old Wald implementation because the synthetic SE values I had carried over from the old fixtures were coincidentally consistent with the n_games values I had chosen. To make the RED phase meaningfully fail (and thus genuinely prove that GREEN is the Wilson switch, not a no-op), I changed the SE inputs to `0.0` in the four ranking tests — which collapses the old Wald formula to a pure score sort, giving the opposite ordering for three of the four tests. This is faithful to the plan's instruction that "SE values can stay arbitrary (they are ignored)" under Wilson.

## Self-Check: PASSED

- `app/services/opening_insights_service.py` — modified, contains `_wilson_bounds` and Wilson-based `_rank_section`. Verified.
- `app/services/opening_insights_constants.py` — modified, contains `OPENING_INSIGHTS_CI_Z_95` (no `OPENING_INSIGHTS_WALD_Z_95`). Verified.
- `tests/services/test_opening_insights_service.py` — modified, four tests renamed and rebaselined. Verified.
- `CHANGELOG.md` — modified, new bullet under `## [Unreleased]` -> `### Changed`. Verified.
- Commit `2385530` (RED) — present in `git log`. Verified.
- Commit `0715fda` (GREEN) — present in `git log`. Verified.
- `score_confidence.py` byte-identical to pre-task state. Verified.
- `frontend/src/lib/arrowColor.ts` byte-identical to pre-task state. Verified.
