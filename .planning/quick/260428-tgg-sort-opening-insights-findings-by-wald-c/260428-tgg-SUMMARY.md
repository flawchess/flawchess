---
phase: quick-260428-tgg
plan: 01
subsystem: opening-insights
tags: [ranking, wald-ci, statistics, opening-insights]
requires:
  - app/services/opening_insights_constants.py::OPENING_INSIGHTS_WALD_Z_95
  - app/services/score_confidence.py::compute_confidence_bucket
provides:
  - direction-aware Wald 95% CI bound tiebreak in opening_insights_service._rank_section
  - SE component on the public return of compute_confidence_bucket
affects:
  - opening insights finding ranking within confidence buckets
  - openings_service.get_next_moves (call-site update only, ranking unchanged)
tech-stack:
  added: []
  patterns:
    - "Direction-aware sort with sign-flip trick (negate lower bound) to keep tuple keys homogeneously ascending under default sorted()"
    - "Internal payload widening (finding -> finding + se) through dedupe stages without leaking SE into the public schema"
key-files:
  created:
    - .planning/quick/260428-tgg-sort-opening-insights-findings-by-wald-c/deferred-items.md
  modified:
    - app/services/opening_insights_constants.py
    - app/services/score_confidence.py
    - app/services/opening_insights_service.py
    - app/services/openings_service.py
    - tests/services/test_score_confidence.py
    - tests/services/test_opening_insights_service.py
    - tests/test_openings_service.py
decisions:
  - "Within a confidence bucket, rank by direction-aware Wald 95% CI bound (clamped to [0, 1]) rather than raw |score - 0.50|. Same SE that drives the bucket gate now drives the within-bucket order."
  - "Thread SE through dedupe stages as `(finding, se)` tuples rather than adding an `se` field to OpeningInsightFinding — keeps the public API schema unchanged."
  - "Negate the lower bound in the strength sort key so the tuple `(confidence_rank, wald_bound)` is homogeneously ascending. Avoids a second branching parameter in sorted()."
  - "WALD_Z_95 (= 1.96) lives next to the other Wald constants in opening_insights_constants.py — same z value implicitly drives the p < 0.05 'high' bucket, so collocation keeps Wald-framework parameters in one place."
metrics:
  duration: ~25 min
  completed: 2026-04-28
---

# Quick Task 260428-tgg: Sort opening insights findings by Wald 95% CI bound (direction-aware) within confidence buckets Summary

Replaces the raw effect-size tiebreak (|score - 0.50|) inside each confidence
bucket with a direction-aware Wald 95% CI bound, so wide-CI small-N rows can
no longer leapfrog tight-CI large-N rows within the same bucket.

## What changed

1. **`compute_confidence_bucket` returns a 3-tuple**
   `(confidence, p_value, standard_error)`. SE was already computed internally
   for the bucket's Wald test; exposing it lets the ranking layer build the
   95% CI without re-deriving the variance formula.

2. **`OPENING_INSIGHTS_WALD_Z_95 = 1.96`** added to `opening_insights_constants.py`
   alongside the existing Wald confidence constants. The same z value implicitly
   drives the p < 0.05 "high" bucket gate — collocation prevents drift.

3. **`_rank_section` is direction-aware.** New signature:
   `_rank_section(findings_with_se: list[tuple[OpeningInsightFinding, float]], direction: Literal["weakness", "strength"])`.
   Within a confidence bucket:
   - **weakness:** sort by `min(max(score + 1.96*SE, 0.0), 1.0)` ascending — the
     finding whose score is most-confidently-below-0.5 sorts first.
   - **strength:** sort by negated `min(max(score - 1.96*SE, 0.0), 1.0)` (i.e.
     lower bound descending) — the finding whose score is most-confidently-above-0.5
     sorts first.

4. **SE flows through internally** without leaking into the public schema.
   `_dedupe_within_section` returns `(finding, se)` (consumes ply_count for
   D-24 dedupe, propagates SE for ranking). `_dedupe_continuations` widens its
   payload from `finding` to `(finding, se)`; the dedupe logic itself is
   unchanged. `OpeningInsightFinding` (API schema) is untouched.

5. **Both callers updated.** `opening_insights_service.compute_insights`
   captures `se` and threads it through. `openings_service.get_next_moves`
   uses `_se` (intentionally unused) — Move Explorer rows sort by frequency
   or win rate, not by Wald bound.

## Why

A "high" confidence bucket can contain rows with wildly different SE — one
based on n=10 and one based on n=400. Both pass the p<0.05 gate, but the n=10
row's confidence interval is wide. Sorting by raw |score - 0.50| promotes the
wide-interval row above the tight-interval row, the opposite of what users
want. The Wald bound mixes effect AND uncertainty within the same Wald-test
framework that already drives the bucket gate.

Concrete demonstration (the regression test
`test_ranking_small_n_high_effect_does_not_outrank_large_n_moderate_effect_within_bucket`):

| Finding | n   | score | SE   | Wald upper bound | \|score - 0.5\| |
| ------- | --- | ----- | ---- | ---------------- | --------------- |
| A       | 10  | 0.20  | 0.13 | 0.455            | 0.30            |
| B       | 400 | 0.30  | 0.02 | 0.339            | 0.20            |

- Old rule (|delta| desc): A first (|delta|=0.30 > 0.20).
- New rule (Wald upper asc): B first (0.339 < 0.455). The tighter, large-N
  row that's "really probably bad" beats the small-N row whose CI still
  reaches almost to 0.5.

## Tests

- **`tests/services/test_score_confidence.py`** — 16 tests, all 3-tuple
  unpacks. Added 4 SE-component tests: closed-form match, all-draws / all-wins /
  all-losses degenerate (SE=0), mixed-outcome SE>0.
- **`tests/services/test_opening_insights_service.py`** — replaced the two
  effect-size ranking tests with five new tests covering bucket ordering,
  weakness-side Wald upper-bound tiebreak, strength-side lower-bound tiebreak,
  small-N-vs-large-N regression, and `[0, 1]` clamp safety on both directions.
- **End-to-end smoke** (`test_compute_insights_populates_confidence_and_p_value`)
  unchanged — confirms public schema is intact.

## Verification

- `uv run ruff check .` — clean.
- `uv run ty check app/ tests/` — clean (zero errors).
- `uv run pytest` — 1166 tests pass.
- `uv run ruff format --check .` reports 92 pre-existing-drift files; none of
  the 92 are touched by this task. See `deferred-items.md` for the breakdown.

## Public API surface

Unchanged. `OpeningInsightFinding` and `NextMoveEntry` schemas have no new
fields. Frontend has no changes. The only change visible outside
`opening_insights_service.py` is the internal helper `compute_confidence_bucket`
returning a 3-tuple instead of a 2-tuple — the third element (`se`) is
unused at every other call site (`_se` placeholder).

## Deviations from Plan

None — plan executed exactly as written. Three commits:

| Task | Description                                                            | Commit  |
| ---- | ---------------------------------------------------------------------- | ------- |
| 1    | Extend compute_confidence_bucket to return SE, add WALD_Z_95 constant  | 67302f3 |
| 2    | Direction-aware Wald CI bound tiebreak in _rank_section                | 6537ddc |
| —    | Rename `bound` -> `wald_bound` in sort_key (cosmetic, must_haves grep) | 45c5a20 |

Task 3 (full-suite verification) had no file changes — no commit.

## Self-Check: PASSED

All seven modified files exist on disk; all three commits are present in
`git log`. `uv run ruff check .`, `uv run ty check app/ tests/`, and
`uv run pytest` (1166 tests) all green.
