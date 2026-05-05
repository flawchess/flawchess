---
phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns
plan: "01"
subsystem: backend-statistics-schema
tags: [backend, statistics, schema, eval_confidence, opening_wdl, wave1]
dependency_graph:
  requires: []
  provides:
    - app.services.eval_confidence.compute_eval_confidence_bucket
    - app.schemas.stats.OpeningWDL (Phase 80 fields)
  affects:
    - plans 02-06 (all consume these symbols)
tech_stack:
  added: []
  patterns:
    - stdlib math.erfc two-sided Wald z-test (mirrors score_confidence.py)
    - Pydantic BaseModel additive optional fields with Literal types
key_files:
  created:
    - app/services/eval_confidence.py
    - tests/services/test_eval_confidence.py
    - tests/test_stats_schemas.py
  modified:
    - app/schemas/stats.py
decisions:
  - "Two-sided p-value (erfc, no 0.5x factor) — both MG-entry positive and negative deviations meaningful"
  - "Used model_validate(dict) in schema tests instead of **kwargs to satisfy ty's invalid-argument-type rule on heterogeneous dicts"
metrics:
  duration: "~30 minutes"
  completed: "2026-05-03"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
---

# Phase 80 Plan 01: Eval Confidence Helper and Schema Extension Summary

Two-sided Wald-z p-value helper (`compute_eval_confidence_bucket`) and additive `OpeningWDL` schema fields (15 new optional fields covering MG-entry eval, clock-diff, and EG-entry eval).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create eval_confidence.py helper + unit tests | 456172d | app/services/eval_confidence.py, tests/services/test_eval_confidence.py |
| 2 | Extend OpeningWDL schema + schema-additivity tests | 386b5ec | app/schemas/stats.py, tests/test_stats_schemas.py |

## Public Symbols Created

### `app/services/eval_confidence.py`

```python
def compute_eval_confidence_bucket(
    eval_sum: float, eval_sumsq: float, n: int
) -> tuple[Literal["low", "medium", "high"], float, float, float]:
```

Returns `(confidence, p_value, mean, ci_half_width)`.

- Bessel-corrected sample variance: `(eval_sumsq - n * mean^2) / (n - 1)`
- Two-sided p-value: `math.erfc(abs(z) / math.sqrt(2.0))` (no `0.5*` factor)
- CI half-width: `OPENING_INSIGHTS_CI_Z_95 * se` (1.96 * SE)
- N-gate: `n < CONFIDENCE_MIN_N (10)` forces "low"
- Edge cases: `n <= 0` returns `("low", 1.0, 0.0, 0.0)`; `n == 1` returns `("low", 1.0, mean, 0.0)`
- Zero variance: `mean != 0` gives `p = 0.0` (high), `mean == 0` gives `p = 1.0` (low)
- No scipy import; stdlib `math` only

### `app/schemas/stats.py` — `OpeningWDL` new fields

MG-entry pillar (D-01, D-04, D-08):
- `avg_eval_pawns: float | None = None`
- `eval_ci_low_pawns: float | None = None`
- `eval_ci_high_pawns: float | None = None`
- `eval_n: int = 0`
- `eval_p_value: float | None = None`
- `eval_confidence: Literal["low", "medium", "high"] = "low"`

Clock-diff at MG entry (D-05):
- `avg_clock_diff_pct: float | None = None`
- `avg_clock_diff_seconds: float | None = None`
- `clock_diff_n: int = 0`

EG-entry pillar (D-09):
- `avg_eval_endgame_entry_pawns: float | None = None`
- `eval_endgame_ci_low_pawns: float | None = None`
- `eval_endgame_ci_high_pawns: float | None = None`
- `eval_endgame_n: int = 0`
- `eval_endgame_p_value: float | None = None`
- `eval_endgame_confidence: Literal["low", "medium", "high"] = "low"`

## Test Counts

| File | Tests |
|------|-------|
| tests/services/test_eval_confidence.py | 11 |
| tests/test_stats_schemas.py | 6 |
| **Total** | **17** |

All 17 tests pass. Full backend suite: 1220 passed, 6 skipped, 0 failures.

## Verification

- `uv run pytest tests/services/test_eval_confidence.py tests/test_stats_schemas.py -x -q`: 17 passed
- `uv run pytest -x -q`: 1220 passed, 6 skipped
- `uv run ty check app/ tests/`: All checks passed (zero errors)
- `uv run ruff check .`: All checks passed
- `grep -c "import scipy" app/services/eval_confidence.py`: 0 (stdlib only)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ty check failure on heterogeneous dict spread in schema tests**
- **Found during:** Task 2 (ty check step)
- **Issue:** Using `**{**_legacy_fields(), "eval_confidence": "bogus"}` with `OpeningWDL(...)` constructor caused ty `invalid-argument-type` errors because ty cannot narrow the inferred `dict[str, int | float | str]` value type to match the specific typed keyword arguments expected by the Pydantic model constructor.
- **Fix:** Switched all test calls from `OpeningWDL(**dict)` to `OpeningWDL.model_validate(dict)` with explicit `dict[str, object]` type annotation. Pydantic's `model_validate` accepts `Any` input, which ty handles correctly.
- **Files modified:** `tests/test_stats_schemas.py`
- **Commit:** 386b5ec

**2. [Rule 1 - Formatting] ruff wrapped long comment inline annotations to multi-line**
- **Found during:** Task 2 (ruff format step)
- **Issue:** Fields with long trailing inline comments (e.g. `avg_eval_endgame_entry_pawns: float | None = None  # signed, user-perspective; None when eval_endgame_n == 0`) were wrapped by ruff into a parenthesized two-line form. This caused some acceptance-criteria grep patterns to not match the exact single-line form.
- **Impact:** None — all tests pass, ty passes, ruff passes. The grep pattern `eval_endgame_n: int = 0` does not match the formatted two-line `eval_endgame_n: int = (\n    0  # ...\n)` form, but the field is correct. Plan acceptance criteria are illustrative grep checks; the actual test suite is the normative gate.
- **Fix:** No code change needed; ruff's formatting is correct. Documented here for traceability.

## Known Stubs

None. This plan creates pure-compute infrastructure (helper + schema fields). No data-fetching stubs.

## Threat Flags

None. This plan is pure-compute (no new network endpoints, no new auth paths, no new file access patterns). See plan frontmatter `<threat_model>` — T-80-01 and T-80-02 both have `accept` disposition with existing controls.

## Self-Check: PASSED
