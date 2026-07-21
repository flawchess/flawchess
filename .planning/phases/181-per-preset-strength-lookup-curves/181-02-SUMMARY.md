---
phase: 181-per-preset-strength-lookup-curves
plan: 02
subsystem: tooling
tags: [codegen, confirmation-testing, isotonic-regression, bootstrap-ci, bot-strength]

# Dependency graph
requires:
  - phase: 181-per-preset-strength-lookup-curves
    plan: "01"
    provides: "scripts/gen_bot_strength_curves.py's isotonic_fit/approx_blitz_points/load_internal_scale/compute_artifact/PRESETS/BLITZ_OFFSET_C/GRID_STEP; reports/data/bot-strength-lookup.json's shipped per-preset range"
provides:
  - "scripts/gen_bot_strength_confirmation_cells.py — sibling generator: off-grid target selection, off-grid bot_elo interpolation, interpolated 95% CI (D-13 locked rule)"
  - "reports/data/bot-strength-confirmation-predictions.json — 7 off-grid confirmation cells (3 human, 2 light, 2 deep) with runbook commands"
  - ".planning/notes/2026-07-21-bot-strength-lookup-findings.md — human-readable findings note (offset model, beyond_ladder resolution, HUMAN-UAT placeholder)"
affects: [bot-builder, preset-cards, seed-098-personas]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sibling gen_*.py importing a prior phase's fit machinery (never re-implementing it) via the scripts.* package + sys.path bootstrap, mirroring scripts/gen_benchmarks.py's scripts.benchmarks import precedent"
    - "inverse-variance-pooled + spread-widened CI for values landing inside a merged PAVA plateau (new technique this phase introduces, extending calibration_anchor_fit.py's combine_preset_g_preset pooling idea)"

key-files:
  created:
    - scripts/gen_bot_strength_confirmation_cells.py
    - reports/data/bot-strength-confirmation-predictions.json
    - tests/scripts/test_gen_bot_strength_confirmation_cells.py
    - .planning/notes/2026-07-21-bot-strength-lookup-findings.md
  modified: []

key-decisions:
  - "D-12 narrow-range fallback: when a preset's shipped range spans fewer than 3 GRID_STEPs (Light ~100-wide, Deep ~200-wide — narrower than the literal floor+100/ceiling-100 formula can honor without landing ON the endpoints), select_confirmation_targets falls back to two targets 1/3 and 2/3 across the range instead of forcing GRID_STEP-alignment — documented as a deliberate deviation from the plan's literal formula, not a bug"
  - "D-13 CI rule implemented as inverse-variance-pooled center + a WIDENED half-width (standard combined SE plus the between-cell spread of the merged points' own rating_vs_maia values), so a genuinely divergent PAVA-merged plateau always yields a band at least as wide as either individual member cell's own CI — proven revert-provable by temporarily reverting to a plain two-bound average and confirming the test fails"
  - "compute_confirmation_predictions() reuses Plan 01's compute_artifact() for the shipped range (single source of truth for D-10's floor/ceiling rounding) rather than re-deriving it, while independently recomputing blocks/cells via isotonic_fit for the per-cell CI data compute_artifact's output doesn't expose"
  - "SEED-104 marked complete per the D-11 split-delivery precedent (mirrors Phase 180 D-01): the interactive phase's scope (gen pipeline + shipped artifact + prediction file + findings note) is fully delivered; only the overnight confirmation game-play run remains, explicitly designated operator-run HUMAN-UAT outside this session's scope"

patterns-established:
  - "Sibling gen_*.py scripts within one phase family import each other's public functions rather than duplicating fit logic — acceptance-gated by grepping the sibling file for the absence of a re-implemented function definition (e.g. no `def isotonic_fit(` in the confirmation-cell script)"

requirements-completed: [SEED-104]

coverage:
  - id: D1
    description: "Deterministic off-grid target picker (D-12): 2-3 targets per preset strictly inside the shipped range, none equal to floor/ceiling"
    requirement: SEED-104
    verification:
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_confirmation_cells.py::test_targets_off_grid_and_inside_range"
        status: pass
    human_judgment: false
  - id: D2
    description: "Off-grid bot_elo interpolation: every predicted_bot_elo in the shipped prediction JSON is NOT one of the preset's 5 measured grid bot_elo values (D-11/D-12)"
    requirement: SEED-104
    verification:
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_confirmation_cells.py::test_predicted_bot_elo_not_on_measured_grid"
        status: pass
    human_judgment: false
  - id: D3
    description: "Interpolated 95% CI (D-13): a bot_elo landing inside a merged PAVA plateau returns the inverse-variance-pooled, spread-widened bound, provably different from and at least as wide as a plain two-bound average"
    requirement: SEED-104
    verification:
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_confirmation_cells.py::test_plateau_ci_is_inverse_variance_pooled_not_lerp"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every emitted row is self-documenting: target_blitz_elo, predicted_bot_elo, predicted_internal, ci95_lo/hi, harness_cmd, fit_cmd; payload has a top-level pass_criterion"
    requirement: SEED-104
    verification:
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_confirmation_cells.py::test_row_has_runbook_commands"
        status: pass
    human_judgment: false
  - id: D5
    description: "Prediction JSON render is deterministic and drift-checked (--check exits 0)"
    requirement: SEED-104
    verification:
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_confirmation_cells.py::test_prediction_render_deterministic"
        status: pass
      - kind: integration
        ref: "uv run python scripts/gen_bot_strength_confirmation_cells.py --check"
        status: pass
    human_judgment: false
  - id: D6
    description: "Findings note documents the offset model, measured-curve realities, resolves the beyond_ladder mechanism (internal-scale anchor floor sf0, not Maia-3's 1100-2000 policy band), and has a HUMAN-UAT confirmation-run placeholder"
    requirement: SEED-104
    verification:
      - kind: other
        ref: "grep -q beyond_ladder / -qi sf0 / -qi HUMAN-UAT .planning/notes/2026-07-21-bot-strength-lookup-findings.md"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-21
status: complete
---

# Phase 181 Plan 02: Confirmation-cell predictions + findings note Summary

**Off-grid confirmation-cell predictor reusing Plan 01's PAVA fit to predict bot_elo/internal-rating/95%-CI at 7 never-before-measured points, plus the human-readable findings note resolving the `beyond_ladder` mystery and closing the phase per split-delivery.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-21T19:44Z (approx, post-plan-01 context read)
- **Completed:** 2026-07-21T19:56:50Z (last commit)
- **Tasks:** 2
- **Files modified:** 4 (all created)

## Accomplishments
- `select_confirmation_targets` picks 2-3 deterministic off-grid targets per preset (D-12); handled a real edge case the plan's literal formula didn't anticipate — Light's and Deep's shipped ranges (100-wide and 200-wide) are narrower than 3 GRID_STEPs, so the literal `floor+100`/`ceiling-100` formula would collide with the actual endpoints. Fell back to a 1/3-2/3 interior split for those two presets, documented as a deliberate deviation.
- `interpolate_bot_elo` produces genuinely off-grid predictions for all 7 rows — none of the 7 predicted `bot_elo` values (1083, 1588, 1741, 1781, 1820, 1298, 1442) matches any of the 15 measured grid points, satisfying D-11/D-12's core test of the shipped inversion.
- Implemented and hand-verified the locked D-13 interpolated-CI rule: inverse-variance-pooled center + a band widened by the between-cell spread, so a merged PAVA plateau's CI is always at least as wide as either individual member cell's own CI. Proved revert-provable by temporarily swapping the rule to a plain two-bound average and confirming `test_plateau_ci_is_inverse_variance_pooled_not_lerp` fails, then restoring the real implementation.
- Every emitted row carries the exact `harness_cmd`/`fit_cmd` runbook (from RESEARCH.md's Code Examples invocation pattern), so the operator confirmation run needs no additional lookup.
- Findings note documents the shipped offset model with real numbers (C=40, pooled G 40.95/186.24/247.18), the Light non-monotone dip and Deep plateau-below-hoped-ceiling realities, resolves `beyond_ladder` as the internal-scale anchor floor (`sf0≈1069.33`) rather than Maia-3's 1100-2000 policy-input band, and ends with the HUMAN-UAT confirmation-run placeholder table + D-13/D-14 pass/refit protocol.

## Task Commits

Each task was committed atomically:

1. **Task 1: Confirmation-cell prediction generator + prediction JSON + tests** - `774a74c9` (feat)
2. **Task 2: Findings note (measured-curve realities + beyond_ladder mechanism + confirmation placeholder)** - `290d4300` (docs)

_Task 1 was marked `tdd="true"` in the plan; implementation and tests were written and verified together in one commit (behavior tests exercise the real pure functions directly), same single-commit structure Plan 01 used for its own `tdd="true"` task._

## Files Created/Modified
- `scripts/gen_bot_strength_confirmation_cells.py` - sibling generator: target selection, off-grid inversion, interpolated internal rating, interpolated 95% CI, JSON emission, `--check`-mode `main()`
- `reports/data/bot-strength-confirmation-predictions.json` - 7 confirmation-cell rows (3 human, 2 light, 2 deep) + top-level `pass_criterion`
- `tests/scripts/test_gen_bot_strength_confirmation_cells.py` - 5 behavior tests covering D-11/D-12/D-13
- `.planning/notes/2026-07-21-bot-strength-lookup-findings.md` - human-readable findings note

## Decisions Made
- Narrow-range target fallback (Light/Deep) uses a 1/3-2/3 interior split rather than forcing GRID_STEP alignment when the shipped range is narrower than 3 GRID_STEPs — the literal D-12 formula (`floor+100`, `ceiling-100`) is mathematically impossible to satisfy without landing on the actual floor/ceiling for a 100-wide range (Light). Documented in the generator's module docstring as a deliberate, deterministic fallback, not a bug.
- D-13's "widen by the pooled standard error" instruction was implemented as: pooled center via standard inverse-variance weighting, half-width = between-cell point-estimate spread + `Z * pooled_se`. This guarantees the pooled band is never narrower than either individual merged cell's own CI (the RESEARCH.md Pitfall-3 requirement), which a naive standard inverse-variance-only combination would violate (that formula alone narrows below both individual CIs, since it treats the two divergent cells as noisy estimates of one shared truth — exactly wrong for cells PAVA merged BECAUSE they disagreed).
- `compute_confirmation_predictions` calls Plan 01's `compute_artifact()` to get the shipped `range` (reusing D-10's rounding logic as the single source of truth) rather than re-deriving floor/ceiling itself, while separately re-running `isotonic_fit` over the grouped cells to get per-cell CI data that `compute_artifact`'s returned structure doesn't expose.
- SEED-104 marked complete in this plan per the D-11 split-delivery precedent (Phase 180 D-01): the interactive-session scope (generator + prediction file + findings note) is fully delivered here; the overnight confirmation game-play run is explicit operator-run HUMAN-UAT, tracked in the findings note's placeholder section rather than blocking this requirement.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] D-12's literal target formula is unsatisfiable for Light's real (narrower-than-hoped) range**
- **Found during:** Task 1, implementing `select_confirmation_targets`
- **Issue:** The plan's literal D-12 formula (`floor + GRID_STEP`, midpoint, `ceiling − GRID_STEP`, falling back to "the two endpoints" when the range spans fewer than 3 grid steps) breaks down for Light's real shipped range (`floor=1500, ceiling=1600`, only 1 GRID_STEP wide): `floor+100` equals `ceiling` exactly, and `ceiling-100` equals `floor` exactly — both violate the plan's own stated invariant that targets must be strictly inside the range and never equal to floor/ceiling. Deep's range (`1600-1800`, 2 GRID_STEPs) has the milder issue that `floor+100` and `ceiling-100` both equal 1700 — the same point, insufficient for 2 distinct targets.
- **Fix:** Implemented a fallback for ranges spanning fewer than `MIDPOINT_TARGET_MIN_GRID_STEPS` (3) GRID_STEPs: two targets placed 1/3 and 2/3 of the way across the range, strictly interior and distinct by construction, not necessarily GRID_STEP-aligned. Documented the rationale and exact formula in the module docstring.
- **Files modified:** scripts/gen_bot_strength_confirmation_cells.py
- **Verification:** `test_targets_off_grid_and_inside_range` covers both the wide (Human-shaped) and narrow (Light-shaped) cases; the real prediction JSON confirms Light/Deep both get exactly 2 valid, distinct, interior targets.
- **Committed in:** 774a74c9 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix — the plan's literal target-selection formula was mathematically unsatisfiable against the real, narrower-than-hoped Light/Deep ranges landed by Plan 01)
**Impact on plan:** Necessary correctness fix to make D-12's own stated invariant ("none equal to floor or ceiling themselves") actually hold against the real data. No scope creep — the fix stays entirely within `select_confirmation_targets`'s contract.

## Issues Encountered

None beyond the documented deviation above.

## User Setup Required

None - no external service configuration required. No package installs (stdlib-only Python, matching Plan 01's convention).

## Next Phase Readiness

Phase 181 is complete at the interactive-session scope per D-11's split delivery. **Remaining work is operator-run HUMAN-UAT, not a blocker for this phase's requirement closure:** run each of the 7 rows' `harness_cmd` + `fit_cmd` from `reports/data/bot-strength-confirmation-predictions.json` (or the findings note's mirrored table), compare each measured `rating_vs_maia` against its recorded `[ci95_lo, ci95_hi]`, and update `.planning/notes/2026-07-21-bot-strength-lookup-findings.md`'s "Confirmation run" section with the pass/fail result. On any failure, fold the games into `bot-curves-internal-scale.json` and re-run `scripts/gen_bot_strength_curves.py` per D-14 (no hand-tuning).

Downstream consumers (custom bot builder preset toggle/slider, preset cards, SEED-098 personas) can now import `frontend/src/generated/botStrengthCurves.ts`'s `BOT_STRENGTH_LOOKUP`/`BOT_STRENGTH_RANGES`/`BOT_STRENGTH_BANDS`/`APPROX_ELO_DISCLAIMER` — no blockers from this plan.

---
*Phase: 181-per-preset-strength-lookup-curves*
*Completed: 2026-07-21*

## Self-Check: PASSED
