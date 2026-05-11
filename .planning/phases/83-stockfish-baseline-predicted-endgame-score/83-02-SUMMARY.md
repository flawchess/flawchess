---
phase: 83
plan: 02
subsystem: services/endgame_service + schemas + score_confidence
tags: [aggregator, wilson, expected-score, refactor, single-source-of-truth]
requires:
  - "Plan 83-01 (eval_utils): eval_cp_to_expected_score / eval_mate_to_expected_score / LICHESS_K"
provides:
  - "EndgamePerformanceResponse.entry_expected_score (float)"
  - "EndgamePerformanceResponse.entry_expected_score_n (int)"
  - "EndgamePerformanceResponse.entry_expected_score_p_value (float | None)"
  - "EndgamePerformanceResponse.entry_expected_score_ci_low (float | None)"
  - "EndgamePerformanceResponse.entry_expected_score_ci_high (float | None)"
  - "score_confidence.compute_score_confidence_from_mean(score, n)"
  - "score_confidence._wilson_score_test_vs_half(score, n) [private]"
  - "endgame_service.EVAL_CLIP_MAX_CP = 2000"
affects:
  - "Plan 83-03 (UI 2x2 restructure) can now read perf.entry_expected_score* off the API"
  - "Plan 83-04 (benchmark calibration) shares the same cohort definition (mate INCLUDED, |eval_cp| < 2000, sign-flipped)"
  - "Plan 83-05 (LLM prompt) can read perf.entry_expected_score_n and perf.entry_expected_score in _findings_endgame_start_vs_end"
tech-stack:
  added: []
  patterns:
    - "Single Wilson code path (math factored into private helper; both bucket and from-mean siblings delegate)"
    - "Sibling aggregator over existing bucket_rows cursor (no SQL change required)"
    - "Subclass-based test reuse (TestEntryExpectedScore inherits _bucket/_wdl_rows fixtures from TestEntryEvalAggregation)"
    - "Cohort inversion documented in test_entry_expected_score_mate_INCLUDED (D-06 — flips Phase 81 entry_eval rule)"
key-files:
  created: []
  modified:
    - "app/services/score_confidence.py"
    - "app/services/endgame_service.py"
    - "app/schemas/endgames.py"
    - "tests/services/test_score_confidence.py"
    - "tests/test_endgame_service.py"
decisions:
  - "Wilson math lives in a single private helper `_wilson_score_test_vs_half(score, n) -> (p_value, se_null)` — both compute_confidence_bucket and compute_score_confidence_from_mean delegate. Verified by grep: the literal Wilson math (`math.sqrt(SCORE_PIVOT * (1.0 - SCORE_PIVOT) / n)`) appears exactly once in score_confidence.py."
  - "Bucketing thresholds and the N>=10 gate are also factored into `_bucket_from_p_value(p_value, n) -> Literal['low','medium','high']` so both siblings share the same threshold ladder."
  - "compute_score_confidence_from_mean returns SE=0.0 (not the Wilson null SE) so callers that gate on SE==0 for degenerate rows behave consistently with compute_confidence_bucket. The third element is informational only."
  - "wilson_bounds(score, n) reused for entry_expected_score_ci_low/high — no new statistical machinery (memory feedback_wilson_chess_score.md)."
  - "EVAL_CLIP_MAX_CP=2000 lives next to EVAL_ADVANTAGE_THRESHOLD as a module-level constant (CLAUDE.md 'no magic numbers')."
metrics:
  duration: "~25 minutes"
  completed: 2026-05-11
  tasks_completed: 3
  files_changed: 5
  tests_added: 20  # 8 in test_score_confidence (1 regression + 7 in TestComputeScoreConfidenceFromMean) + 12 in TestEntryExpectedScore
---

# Phase 83 Plan 02: Backend plumbing for entry_expected_score Summary

Wired the per-game Stockfish-baseline expected score into the existing
`EndgamePerformanceResponse` plumbing without duplicating Wilson math.
Factor-then-add refactor of `score_confidence.py` extracts the existing
Wilson `(p_value, se_null)` computation into a private helper so the new
float-mean sibling (`compute_score_confidence_from_mean`) and the existing
(W, D, L, N) bucket function share one source of truth. The new aggregator
in `_get_endgame_performance_from_rows` loops the existing `bucket_rows`
cursor exactly once, producing all five new schema fields.

## Schema Surface (app/schemas/endgames.py)

Five new fields on `EndgamePerformanceResponse`, defaulted per Phase 81 D-11:

```python
entry_expected_score: float = 0.0
entry_expected_score_n: int = 0
entry_expected_score_p_value: float | None = None
entry_expected_score_ci_low: float | None = None
entry_expected_score_ci_high: float | None = None
```

Docstrings are descriptive (`"Two-sided p-value vs 50%"`), not prescriptive
on methodology, per memory `feedback_wilson_chess_score.md`. Verified by
`grep -c -i wilson` over the new block: 0.

## Wilson Refactor (app/services/score_confidence.py)

Public surface (preserved + new):

```python
def wilson_bounds(p: float, n: int) -> tuple[float, float]: ...   # unchanged
def compute_confidence_bucket(w, d, losses, n) -> (level, p, se_emp): ...   # signature preserved
def compute_score_confidence_from_mean(score: float, n: int) -> (level, p, 0.0): ...   # NEW
```

Private helpers (new):

```python
def _wilson_score_test_vs_half(score: float, n: int) -> tuple[float, float]: ...  # (p_value, se_null)
def _bucket_from_p_value(p_value: float, n: int) -> Literal["low", "medium", "high"]: ...
```

Backward-compat regression pinned by `test_compute_confidence_bucket_golden_after_refactor`:
`compute_confidence_bucket(70, 10, 20, 100)` returns `("high", 5.733031e-7, sqrt(0.1625/100))`
both before and after the refactor.

## Aggregator (app/services/endgame_service.py)

Module-level constant added (sibling to `EVAL_ADVANTAGE_THRESHOLD = 100`):

```python
EVAL_CLIP_MAX_CP = 2000   # Phase 83 D-07 — drop rows where |eval_cp| >= 2000
```

New imports (under the existing `eval_confidence` / `score_confidence` block):

```python
from app.services.eval_utils import (
    eval_cp_to_expected_score, eval_mate_to_expected_score,
)
from app.services.score_confidence import (
    compute_confidence_bucket,
    compute_score_confidence_from_mean,   # NEW
    wilson_bounds,                          # NEW (existing export, newly used here)
)
```

Sibling loop placed immediately after the existing entry-eval / endgame-score
sig blocks and before the `EndgamePerformanceResponse(...)` constructor.
Each `row.<col>` access carries `# ty: ignore[unresolved-attribute]` (matches
the existing entry-eval loop convention).

Wire-format gating matches the entry_eval pattern:
- `entry_expected_score_p_value = p_ex_raw if ex_n >= 10 else None`
- CI bounds set when `ex_n >= 2`, else `None`

## Cohort Semantics

| Rule | entry_eval (Phase 81) | entry_expected_score (Phase 83) |
|---|---|---|
| Mate rows                 | Excluded                | INCLUDED (D-06: mate has a defined expected score)  |
| NULL eval rows            | Excluded                | Excluded                                            |
| `|eval_cp| >= 2000`       | Not clipped             | Dropped (D-07)                                      |
| Sign convention           | sign-flipped per color  | sign-flipped per color (via eval_utils helpers)     |
| Sig test                  | Wald-z mean vs 0 cp     | Wilson score vs 0.5 (compute_score_confidence_from_mean) |
| Sample-size p_value gate  | n >= 10                 | n >= 10                                             |
| CI bounds gate            | n >= 2                  | n >= 2                                              |

The mate-INCLUDED inversion is locked in by `test_entry_expected_score_mate_INCLUDED`,
which asserts `entry_expected_score_n > entry_eval_n` on a mixed cohort.

## Test Functions Added

**`tests/services/test_score_confidence.py`** (8 tests):

Regression:
- `test_compute_confidence_bucket_golden_after_refactor` — pins the
  pre-refactor output of `compute_confidence_bucket(70, 10, 20, 100)`

`TestComputeScoreConfidenceFromMean`:
- `test_n_zero_returns_low_one_zero`
- `test_n_below_gate_returns_low_with_real_p_value`
- `test_centered_mean_returns_low_p_one`
- `test_strong_evidence_returns_high`
- `test_medium_evidence_returns_medium`
- `test_matches_compute_confidence_bucket_for_equivalent_inputs`
- `test_white_black_symmetry`

**`tests/test_endgame_service.py`** (12 tests in `TestEntryExpectedScore`,
which subclasses `TestEntryEvalAggregation` to inherit `_bucket` / `_wdl_rows`):

- `test_entry_expected_score_empty_defaults`
- `test_entry_expected_score_centered_when_eval_zero`
- `test_entry_expected_score_n_nine_p_value_gated`
- `test_entry_expected_score_sign_flip_black`
- `test_entry_expected_score_mate_INCLUDED` (D-06 cohort inversion)
- `test_entry_expected_score_mate_against_user_is_zero`
- `test_entry_expected_score_eval_cp_clip` (D-07)
- `test_entry_expected_score_eval_cp_clip_boundary` (exact +/-2000 boundary)
- `test_entry_expected_score_null_eval_dropped`
- `test_entry_expected_score_ci_bounds_set_when_n_ge_two`
- `test_entry_expected_score_p_value_significant_when_strong`
- `test_entry_eval_unchanged_by_phase_83` (Phase 81 regression sanity)

## Verification

- `uv run pytest tests/services/test_score_confidence.py tests/test_endgame_service.py` — **256 passed**
- `uv run pytest tests/services/test_eval_utils.py tests/services/test_eval_confidence.py tests/test_endgame_repository.py tests/test_endgames_router.py tests/services/test_insights_service.py` — **122 passed** (no regressions in adjacent suites)
- `uv run ty check app/ tests/` — All checks passed (zero errors)
- `uv run ruff check app/ tests/` — All checks passed
- `grep -c "math.sqrt(SCORE_PIVOT \* (1.0 - SCORE_PIVOT) / n)" app/services/score_confidence.py` — **1** (Wilson math single-sourced)
- `grep -c "EVAL_CLIP_MAX_CP" app/services/endgame_service.py` — **3** (defined once, used in loop, plus the docblock reference)
- `grep -c "eval_cp_to_expected_score\|eval_mate_to_expected_score" app/services/endgame_service.py` — **4** (2 imports + 2 call sites)
- `grep -E "^\s+entry_expected_score(_n|_p_value|_ci_low|_ci_high)?:" app/schemas/endgames.py | wc -l` — **5**
- Schema smoke instantiation `EndgamePerformanceResponse(endgame_wdl=..., non_endgame_wdl=..., endgame_win_rate=0.0)` populates all 5 new fields at their defaults.

## Deviations from Plan

**1. Plan's smoke verification snippet was incomplete (no functional deviation)**

- **Found during:** Task 2 verify step
- **Issue:** The plan's verify command instantiates `EndgamePerformanceResponse()` with no args, but the existing schema has three required fields (`endgame_wdl`, `non_endgame_wdl`, `endgame_win_rate`) that pre-date this plan. The snippet would have failed even before adding the new fields.
- **Fix:** Ran the spirit of the verify (existing call sites that build the response without the new fields still work) by passing in the three required pre-existing fields and asserting the new five fields default correctly. No code change needed.
- **Files modified:** None (verification-only adjustment).
- **Commit:** N/A.

**2. Added a `_bucket_from_p_value` shared bucketer (Rule 2 — consistency)**

- **Found during:** Task 1 GREEN implementation
- **Issue:** The plan asked to single-source the Wilson math, but the bucketing/gating ladder (`if n < CONFIDENCE_MIN_N -> "low"; if p < HIGH -> "high"; ...`) was also duplicated between the two siblings in the planner's example code. Two parallel ladders would drift over time.
- **Fix:** Extracted `_bucket_from_p_value(p_value, n) -> Literal["low","medium","high"]` so both siblings share the same threshold ladder, mirroring the Wilson-math factor-out.
- **Files modified:** `app/services/score_confidence.py`
- **Commit:** `35b0088a` (GREEN of Task 1)

**3. Imported `wilson_bounds` for the CI computation (Rule 3 — fulfilment)**

- **Found during:** Task 3 GREEN
- **Issue:** The plan said "Compute Wilson CIs via the existing CI utility on the (score, n) signature; gate to None when ex_n < 2. (Inspect the existing endgame_score_ci_low derivation path nearby to identify the correct CI util — reuse it; do not introduce new statistical machinery)." The endgame_score code path does NOT expose a Wilson CI on the endgame_score itself today (it has only `endgame_score_p_value`, no CI). The actual canonical `wilson_bounds(p, n)` lives in `score_confidence.py` and is already used elsewhere; this is the right CI util for a (score, n) signature.
- **Fix:** Imported `wilson_bounds` from `score_confidence` (existing export) and called it directly. No new machinery introduced.
- **Files modified:** `app/services/endgame_service.py`
- **Commit:** `b135d6fe` (GREEN of Task 3)

No architectural changes were needed (no Rule 4 escalations).

## TDD Gate Compliance

| Task | RED                                                                  | GREEN                                                                  | REFACTOR        |
|------|----------------------------------------------------------------------|------------------------------------------------------------------------|-----------------|
| 1    | `75b26cdb` — failing tests for `compute_score_confidence_from_mean` | `35b0088a` — Wilson math factored + sibling helper                     | not needed      |
| 2    | (schema-only task — gated by Task 3's behavior tests)                | `d2e72741` — 5 new fields with safe-empty defaults                     | not needed      |
| 3    | `0b6ad011` — failing aggregator tests (11/12 fail)                  | `b135d6fe` — sibling aggregator + 5 new fields wired in constructor    | not needed      |

Task 2 ships fields whose behavior is tested by Task 3 — the schema-only task
has no independent "failing test then passing test" cycle, only a smoke
instantiation gate, so the RED commit is folded into Task 3's test commit.

## Known Stubs

None. The schema fields are wired end-to-end from `bucket_rows` through the
aggregator to the API response. Plans 83-03 (UI), 83-04 (benchmark
calibration), and 83-05 (LLM prompt) consume the same five fields as
documented in their PLAN.md frontmatter.

## Self-Check: PASSED

- `app/services/score_confidence.py` — FOUND (modified)
- `app/services/endgame_service.py` — FOUND (modified)
- `app/schemas/endgames.py` — FOUND (modified)
- `tests/services/test_score_confidence.py` — FOUND (modified)
- `tests/test_endgame_service.py` — FOUND (modified)
- Commit `75b26cdb` — FOUND (RED Task 1)
- Commit `35b0088a` — FOUND (GREEN Task 1)
- Commit `d2e72741` — FOUND (Task 2 schema fields)
- Commit `0b6ad011` — FOUND (RED Task 3)
- Commit `b135d6fe` — FOUND (GREEN Task 3)
- All verification commands clean (pytest 256/256, ty zero, ruff zero, grep counts as expected)
