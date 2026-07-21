---
phase: 181-per-preset-strength-lookup-curves
reviewed: 2026-07-21T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - .github/workflows/ci.yml
  - frontend/knip.json
  - frontend/src/generated/botStrengthCurves.ts
  - reports/data/bot-strength-confirmation-predictions.json
  - reports/data/bot-strength-lookup.json
  - scripts/gen_bot_strength_curves.py
  - scripts/gen_bot_strength_confirmation_cells.py
  - tests/scripts/test_gen_bot_strength_confirmation_cells.py
  - tests/scripts/test_gen_bot_strength_curves.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 181: Code Review Report

**Reviewed:** 2026-07-21
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed Phase 181's two generators (`gen_bot_strength_curves.py`, `gen_bot_strength_confirmation_cells.py`), their emitted artifacts (JSON + generated TS), the CI/knip wiring, and both test files. `ruff check`, `ty check`, and the full test suite for these files (18 tests) all pass, and both `--check` drift modes are currently clean. I traced the PAVA fit, offset math, lowest-wins inversion, and the D-13 interpolated-CI pooling by hand against the committed JSON and confirmed the numbers are internally consistent — no arithmetic bugs found in the shipped output.

The issues found are process/robustness gaps rather than active defects: one artifact (the confirmation-predictions JSON) is missing from the CI drift-check net that covers its two siblings, and two edge cases in the confirmation-cell math have no guard and would surface as a confusing crash rather than the module's otherwise-consistent fail-loud error style if a future re-fit narrows a preset's range. None of these reproduce against the currently committed `bot-curves-internal-scale.json`.

## Warnings

### WR-01: Confirmation-predictions JSON has no CI drift check

**File:** `.github/workflows/ci.yml:60-63` (compare `scripts/gen_bot_strength_confirmation_cells.py:287-307`, `reports/data/bot-strength-confirmation-predictions.json`)
**Issue:** `gen_bot_strength_curves.py` and its two artifacts (`frontend/src/generated/botStrengthCurves.ts`, `reports/data/bot-strength-lookup.json`) are drift-checked in CI ("Bot strength curves drift check" step). `gen_bot_strength_confirmation_cells.py` implements the identical `--check` contract (verified working locally: `uv run python scripts/gen_bot_strength_confirmation_cells.py --check` exits 0), but no CI step invokes it, and neither `test_gen_bot_strength_confirmation_cells.py::test_prediction_render_deterministic` nor any other test compares the committed `reports/data/bot-strength-confirmation-predictions.json` against a fresh render — that test only compares two in-memory recomputations against each other, never the file on disk. So if a future change touches `gen_bot_strength_confirmation_cells.py`, `gen_bot_strength_curves.py`'s shared fit functions, or the frozen input, the committed predictions file can silently go stale while CI stays green.

This isn't cosmetic: the file's entire purpose (per its own `pass_criterion` field) is to be the ground truth an operator diffs a real confirmation game-play run against (D-13/D-14). A stale `predicted_bot_elo`/`ci95_lo`/`ci95_hi` would make the operator run the wrong harness command or judge the run against the wrong confidence band, silently invalidating the calibration check the phase was built to support.
**Fix:**
```yaml
      - name: Bot strength confirmation predictions drift check
        run: |
          uv run python scripts/gen_bot_strength_confirmation_cells.py
          git diff --exit-code reports/data/bot-strength-confirmation-predictions.json
```
Add this immediately after the existing "Bot strength curves drift check" step (`.github/workflows/ci.yml:60-63`).

### WR-02: `select_confirmation_targets` narrow-range fallback has no guard for a zero-width range

**File:** `scripts/gen_bot_strength_confirmation_cells.py:104-123`
**Issue:** When `span < MIDPOINT_TARGET_MIN_GRID_STEPS * GRID_STEP`, the fallback computes `offset = max(1, round(span / 3))`, `first = floor + offset`, `second = ceiling - offset`, then bumps `second = first + 1` if `second <= first`. If `span == 0` (i.e. `floor == ceiling` — a legitimate output of Plan 01's `preset_range()` when a preset's fitted approx-blitz span contains exactly one `GRID_STEP`-aligned point), this produces `offset = 1`, `first = floor + 1`, `second = floor - 1`, which triggers the bump to `second = first + 1 = floor + 2`. Both `first` and `second` then land strictly *above* `ceiling` (`== floor`), violating the function's own documented invariant ("strictly inside the measured curve... none equal to floor or ceiling themselves" — 181-02-PLAN.md D-12, and this module's own docstring lines 19-28).

Nothing downstream validates this before use: `compute_confirmation_predictions` feeds these targets straight into `interpolate_bot_elo`, which will raise a generic `ValueError: interpolate_bot_elo: target {target} outside fitted curve range` (`scripts/gen_bot_strength_confirmation_cells.py:144`) — a fail-loud crash, but one that doesn't name the actual root cause (a zero-width preset range), unlike the rest of the module's deliberately explicit fail-loud errors (e.g. `load_internal_scale`).

This does not reproduce against the currently committed `bot-curves-internal-scale.json` (human/light/deep spans are 500/100/200, never 0), so it's dormant today — but it's exactly the kind of edge case a future D-14 refit (fold confirmation games into the fit, re-run the generator) could hit if a preset's range narrows further.
**Fix:** Guard the zero-span case explicitly and fail with a clear message naming the preset/range rather than letting it fall through to a confusing crash three functions downstream:
```python
def select_confirmation_targets(preset_range: dict[str, int]) -> list[int]:
    floor = preset_range["floor"]
    ceiling = preset_range["ceiling"]
    span = ceiling - floor
    if span <= 0:
        raise ValueError(
            f"select_confirmation_targets: range {preset_range!r} has no interior "
            "targets (floor == ceiling) — cannot pick off-grid confirmation cells"
        )
    ...
```

### WR-03: `invert_lookup` / `preset_range` can crash with a bare `min()`/`max()` error instead of a fail-loud message

**File:** `scripts/gen_bot_strength_curves.py:148-172`
**Issue:** If the inward-rounded `floor` ends up greater than `ceiling` (possible whenever a preset's raw approx-blitz span `[approx[0][1], approx[-1][1]]` doesn't contain any multiple of `GRID_STEP`), `range(floor, ceiling + GRID_STEP, GRID_STEP)` in `invert_lookup` silently produces zero iterations, yielding an empty `lookup` dict. `preset_range()` then calls `min(lookup)` / `max(lookup)` on that empty dict, raising a bare `ValueError: min() iterable argument is empty` with no context about which preset or why. This is inconsistent with the fail-loud philosophy the rest of the module follows deliberately (`load_internal_scale` names the offending field; `compute_artifact` names the preset and expected/actual cell count for D-08). Like WR-02, this doesn't reproduce against the current committed data (all three presets have real gaps of 100-500 between rounded floor/ceiling) but is unguarded against future re-fits.
**Fix:** Add an explicit check in `invert_lookup` (or `preset_range`) that raises a named `ValueError` when `floor > ceiling`, e.g.:
```python
    if floor > ceiling:
        raise ValueError(
            f"invert_lookup: rounded floor {floor} exceeds ceiling {ceiling} — "
            "approx-blitz span is narrower than one GRID_STEP"
        )
```

## Info

### IN-01: `bot_elo` type is inconsistent within the shipped lookup JSON

**File:** `reports/data/bot-strength-lookup.json:6,10,29-32` (produced by `scripts/gen_bot_strength_curves.py:220,226`)
**Issue:** `components.<preset>.fit_points[].bot_elo` is emitted as a float (e.g. `700.0`, `1100.0` — `b.x_lo` is never cast to `int`), while `components.<preset>.extrapolated_bot_elos` and every key/value in `derived.<preset>.lookup` are plain ints (`int(c["bot_elo"])`, `int(bot_elo)`). Both represent the same underlying grid values, so a consumer parsing this artifact sees `bot_elo` typed as `number` in one place and effectively-integer `number` in another with different JSON literal shapes. Functionally harmless (both round-trip identically through `json`/JS `number`), but it's an avoidable inconsistency in a schema meant to be the "single source of truth for all future labeled bot strength claims."
**Fix:** Cast `b.x_lo` to `int` when building `fit_points` in `compute_artifact` (`scripts/gen_bot_strength_curves.py:220`), since all `bot_elo` values in the frozen input are already integers:
```python
"fit_points": [{"bot_elo": int(b.x_lo), "internal_rating": b.value} for b in blocks],
```

### IN-02: Local `import math` inside a test function instead of module-level

**File:** `tests/scripts/test_gen_bot_strength_curves.py:182`
**Issue:** `test_range_rounds_inward` does `import math` inside the function body, while the module under test (`scripts/gen_bot_strength_curves.py`) and the sibling test file both import `math` at module scope. Purely a style inconsistency (ruff doesn't flag it since there's no repo-wide isort/PLC0415 rule enabled), not a functional issue.
**Fix:** Move `import math` to the top of `tests/scripts/test_gen_bot_strength_curves.py` alongside the existing `import json` / `from pathlib import Path`.

---

_Reviewed: 2026-07-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
