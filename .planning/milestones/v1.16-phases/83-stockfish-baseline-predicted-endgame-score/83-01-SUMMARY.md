---
phase: 83
plan: 01
subsystem: services/eval_utils
tags: [pure-math, conversion, sigmoid, mate, expected-score]
requires: []
provides:
  - "eval_utils.LICHESS_K (module constant)"
  - "eval_utils.eval_cp_to_expected_score(eval_cp, user_color) -> float"
  - "eval_utils.eval_mate_to_expected_score(eval_mate, user_color) -> float"
affects: []
tech-stack:
  added: []
  patterns:
    - "Pure-function service module (mirrors app/services/eval_confidence.py shape)"
    - "Class-grouped pytest tests (TestSigmoid / TestMate)"
    - "Literal['white','black'] color parameter (CLAUDE.md type-safety)"
key-files:
  created:
    - "app/services/eval_utils.py"
    - "tests/services/test_eval_utils.py"
  modified: []
decisions:
  - "Mate is NOT routed through the sigmoid (D-02): mate-in-N maps to exactly 0.0 or 1.0 regardless of N."
  - "Sign convention mirrors endgame_service._classify_endgame_bucket: sign=+1 for white user, -1 for black user."
  - "LICHESS_K kept as a single module-level constant (no in-function literal) so Plan 4's SQL CTE can reference the same canonical value."
metrics:
  duration: "~10 minutes"
  completed: 2026-05-11
  tasks_completed: 2
  files_changed: 2
  tests_added: 17
---

# Phase 83 Plan 01: eval_utils Summary

Pure-math conversion utility translating Stockfish eval (signed centipawns or mate-in-N) to a user-perspective expected score in [0, 1], using the Lichess winning-chances sigmoid for cp and a direct 0/1 mapping for mate. Ships with 17 unit tests covering centering, sign convention, white/black symmetry, saturation, monotonicity, and mate-for/against for both colors (Pitfall 1).

## Module Signature

```python
# app/services/eval_utils.py
LICHESS_K: float = 0.00368208  # Lichess winning-chances coefficient

def eval_cp_to_expected_score(
    eval_cp: int,
    user_color: Literal["white", "black"],
) -> float: ...

def eval_mate_to_expected_score(
    eval_mate: int,
    user_color: Literal["white", "black"],
) -> float: ...
```

`eval_cp_to_expected_score` returns `1 / (1 + exp(-K * sign * eval_cp))` where `sign = +1 if user_color == "white" else -1`. Centered at 0.5 for cp == 0, saturates near 1.0 / 0.0 at ±1500 cp.

`eval_mate_to_expected_score` returns `1.0` iff the side that has the forced mate matches `user_color`, else `0.0`. Distance to mate is ignored (D-02).

## Test Coverage (17 tests, all passing)

`TestSigmoid` (10 tests):
- `test_lichess_k_constant_value` — LICHESS_K == 0.00368208 exactly
- `test_zero_cp_returns_half` — f(0, _) == 0.5 for either color
- `test_positive_cp_white_user` — f(+100, "white") ~ 0.591
- `test_positive_cp_black_user` — f(+100, "black") ~ 0.409
- `test_white_black_symmetry` — f(+x, "white") + f(+x, "black") == 1.0 for x in {-1500, -300, -1, 0, 1, 50, 300, 1500}
- `test_saturation_high` — f(+1500, "white") > 0.99 AND f(+1500, "black") < 0.01
- `test_saturation_low` — f(-1500, "white") < 0.01 AND f(-1500, "black") > 0.99
- `test_monotonic_in_cp_for_white_user` — strictly increasing
- `test_monotonic_in_cp_for_black_user` — strictly decreasing
- `test_range_in_unit_interval` — output ∈ [0, 1] even at ±100_000 cp

`TestMate` (7 tests, both colors covered per Pitfall 1):
- `test_white_mating_white_user` — eval_mate=+5, "white" -> 1.0
- `test_white_mating_black_user` — eval_mate=+5, "black" -> 0.0
- `test_black_mating_white_user` — eval_mate=-5, "white" -> 0.0
- `test_black_mating_black_user` — eval_mate=-5, "black" -> 1.0 (Pitfall 1 coverage)
- `test_short_mate_for_each_color` — mate-in-1 for both colors
- `test_long_mate_for_each_color` — mate-in-30 for both colors (distance ignored)
- `test_mate_output_is_exactly_zero_or_one` — exact float 0.0 / 1.0, not sigmoid-rounded

## Verification

- `uv run pytest tests/services/test_eval_utils.py` — 17 passed
- `uv run ty check app/services/eval_utils.py tests/services/test_eval_utils.py` — All checks passed
- `uv run ruff check app/services/eval_utils.py tests/services/test_eval_utils.py` — All checks passed
- `uv run ruff format --check` — already formatted

## Deviations from Plan

**1. Typed Literal tuples in tests instead of `# type: ignore` pragmas (Rule 1 - cleaner alternative)**

- **Found during:** Task 2 GREEN verification
- **Issue:** Initial test draft used `# type: ignore[arg-type]` to silence `ty` complaints when iterating over plain-string color tuples (matches a common pytest idiom).
- **Plan acceptance criterion explicitly required:** "No `# type: ignore` / `# ty: ignore` pragmas needed — pure-function tests".
- **Fix:** Declared the iteration containers with explicit `Literal["white", "black"]` types (`colors: tuple[Literal["white", "black"], ...]` and `cases: list[tuple[int, Literal["white", "black"], float]]`). Added `from typing import Literal` to the test module.
- **Files modified:** `tests/services/test_eval_utils.py`
- **Commit:** included in `7885bcae` (GREEN phase)

No other deviations. PATTERNS.md guidance was followed exactly: module shape mirrors `eval_confidence.py`, tests are class-grouped (`TestSigmoid` / `TestMate`), and the sign-flip pattern matches `_classify_endgame_bucket`.

## Known Stubs

None. The module is complete and ready for Plan 2's aggregator and Plan 4's benchmark CTE to import.

## TDD Gate Compliance

- RED commit: `785d1906` — `test(83-01): add failing unit tests for eval_utils` (ImportError confirmed before implementation)
- GREEN commit: `7885bcae` — `feat(83-01): implement eval_utils for Stockfish baseline expected score` (17/17 pass)
- REFACTOR: not needed; implementation was minimal and clean on first pass.

## Self-Check: PASSED

- `app/services/eval_utils.py` — FOUND
- `tests/services/test_eval_utils.py` — FOUND
- Commit `785d1906` — FOUND (RED)
- Commit `7885bcae` — FOUND (GREEN)
- All verification commands clean
