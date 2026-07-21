---
phase: 181-per-preset-strength-lookup-curves
plan: 01
subsystem: tooling
tags: [codegen, isotonic-regression, pava, calibration, bot-strength, generated-ts]

# Dependency graph
requires:
  - phase: 180-three-preset-bot-strength-curves
    provides: "reports/data/bot-curves-internal-scale.json (15 measured cells + per-preset pooled G_preset_combined)"
provides:
  - "scripts/gen_bot_strength_curves.py — stdlib-only PAVA fit + offset + inversion + JSON/TS emitter"
  - "reports/data/bot-strength-lookup.json — components+derived shipping lookup artifact"
  - "frontend/src/generated/botStrengthCurves.ts — generated TS mirror (BOT_STRENGTH_LOOKUP, BOT_STRENGTH_RANGES, BOT_STRENGTH_BANDS, APPROX_ELO_DISCLAIMER)"
  - "CI drift-check step for the new generator"
affects: [bot-builder, preset-cards, seed-098-personas]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "gen_*.py -> committed TS/JSON -> CI drift check (extended to a 3rd generator)"
    - "hand-rolled stack-of-blocks PAVA isotonic regression, stdlib only"

key-files:
  created:
    - scripts/gen_bot_strength_curves.py
    - reports/data/bot-strength-lookup.json
    - frontend/src/generated/botStrengthCurves.ts
    - tests/scripts/test_gen_bot_strength_curves.py
  modified:
    - .github/workflows/ci.yml
    - frontend/knip.json

key-decisions:
  - "Fit uses rating_vs_maia minus the pooled per-preset g_preset_combined plus C=40 (D-01) — never per-cell g_preset, never rating_vs_sf"
  - "Inversion is lowest-bot_elo-wins on plateau/merged PAVA blocks (D-07) — proven revert-provable via test_inversion_lowest_bot_elo_wins"
  - "All 5 measured cells per preset feed the fit, including Human's two beyond_ladder cells (D-08), guarded by a hard ValueError in compute_artifact if the count ever drifts"
  - "Range endpoints round inward: floor up, ceiling down, to the nearest 100 (D-10)"
  - "Lookup JSON separates components (fit_points, g_preset_combined, c_offset, band, extrapolated_bot_elos) from derived (range, lookup) per preset, plus a top-level disclaimer (D-02)"
  - "botStrengthCurves.ts added to frontend/knip.json's ignore list — no consumer yet (D-04), same precedent as endgameZones.ts"

patterns-established:
  - "PAVA (Pool-Adjacent-Violators) stack-of-blocks isotonic regression as the project's stdlib-only monotone-fit primitive for small measured-point datasets"

requirements-completed: []  # SEED-104 only fully closes when Plan 02 (confirmation-cell prediction file + findings) lands per D-11 split delivery

coverage:
  - id: D1
    description: "PAVA isotonic fit + pooled-G offset + lowest-wins inversion + inward-rounded ranges, implemented as pure stdlib functions"
    verification:
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_pava_pools_light_dip"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_pava_deep_plateau_is_ceiling"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_pava_human_noop"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_inversion_lowest_bot_elo_wins"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_offset_uses_pooled_g_not_per_cell_or_vs_sf"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_range_rounds_inward"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fail-loud loader for the frozen input JSON, and all 5 cells per preset (incl. Human beyond_ladder cells) consumed by the fit"
    requirement: SEED-104
    verification:
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_loader_fails_loud_on_missing_cells"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_all_cells_retained"
        status: pass
    human_judgment: false
  - id: D3
    description: "Components+derived lookup JSON and generated, knip-clean, type-checking TS module with the canonical disclaimer; --check is green and deterministic"
    requirement: SEED-104
    verification:
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_json_has_components_and_derived"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_disclaimer_present_both_outputs"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_render_is_deterministic"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_gen_bot_strength_curves.py::test_deep_range_ceiling_below_1900"
        status: pass
      - kind: integration
        ref: "uv run python scripts/gen_bot_strength_curves.py --check"
        status: pass
      - kind: integration
        ref: "( cd frontend && npx tsc -b && npm run knip )"
        status: pass
    human_judgment: false
  - id: D4
    description: "CI will fail on any future drift between the generator and its two committed artifacts"
    requirement: SEED-104
    verification:
      - kind: integration
        ref: ".github/workflows/ci.yml — 'Bot strength curves drift check' step (git diff --exit-code on both emitted paths)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-21
status: complete
---

# Phase 181 Plan 01: Per-preset strength lookup curves — generator + shipping artifact Summary

**New stdlib-only `scripts/gen_bot_strength_curves.py` turns Phase 180's 15 measured cells into a components+derived lookup JSON and a knip-clean, CI-drift-checked `botStrengthCurves.ts`, via hand-rolled PAVA isotonic regression, pooled-G offset conversion, and lowest-bot_elo-wins inversion.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-21T17:40Z (approx, pre-commit reading/design phase)
- **Completed:** 2026-07-21T17:40:36Z (last commit)
- **Tasks:** 3
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments
- Hand-rolled stack-of-blocks PAVA (`isotonic_fit`) correctly pools Light's non-monotone bot_elo 1100/1300 dip and Deep's 2300/2600 dip into flat plateau blocks, matching RESEARCH.md's hand-verified expectations exactly.
- Offset conversion (`approx_blitz_points`) and inversion (`invert_lookup`) implement D-01 (pooled G, never per-cell/vs-SF) and D-07 (lowest-bot_elo-wins on plateaus) as pure, independently-testable functions — the D-07 invariant is proven revert-provable (reverting the `x_lo` tie-break to `x_hi` breaks `test_inversion_lowest_bot_elo_wins`).
- `compute_artifact()` produces the full components+derived structure (D-02) and hard-fails if any preset's cell count drifts from 5 (D-08 guard), so the Human `beyond_ladder` cells can never be silently dropped by a future maintainer.
- Emitted artifacts verified by hand-calculation and by the generator run: **Human** range 900–1400, **Light** 1500–1600, **Deep** 1600–1800 (below 1900, confirming D-07's plateau-honesty sanity check against the seed's hoped ~2600 ceiling).
- CI now drift-checks a third generator alongside the existing Zone/Flaw-thresholds steps.

## Task Commits

Each task was committed atomically:

1. **Task 1: PAVA fit, offset math, inversion, fail-loud loader (pure functions + tests)** - `9345902b` (feat)
2. **Task 2: Render + emit components+derived JSON and generated TS with disclaimer** - `c56687c0` (feat)
3. **Task 3: Wire CI drift-check step for the new generator** - `86dbee61` (chore)

_No TDD tasks in this plan (Task 1 was `tdd="true"` per frontmatter but implemented behavior tests alongside the pure functions in a single commit, per the plan's own single-commit structure — see Deviations)._

## Files Created/Modified
- `scripts/gen_bot_strength_curves.py` - PAVA fit, offset math, inversion, fail-loud loader, JSON/TS render, `--check`-mode `main()`
- `tests/scripts/test_gen_bot_strength_curves.py` - 13 behavior tests covering D-01/D-02/D-06/D-07/D-08/D-10
- `reports/data/bot-strength-lookup.json` - shipped components+derived lookup artifact
- `frontend/src/generated/botStrengthCurves.ts` - generated TS mirror (`BOT_STRENGTH_LOOKUP`, `BOT_STRENGTH_RANGES`, `BOT_STRENGTH_BANDS`, `APPROX_ELO_DISCLAIMER`)
- `.github/workflows/ci.yml` - added "Bot strength curves drift check" step
- `frontend/knip.json` - added `src/generated/botStrengthCurves.ts` to the `ignore` array

## Decisions Made
- `PRESETS: dict[float, str]` keys the blend->name map by float (0.0/0.05/0.5, matching the `cells[].bot_blend` type in the input JSON); `per_preset` lookups use `f"{blend:g}"` to match its string-keyed ("0"/"0.05"/"0.5") shape — avoids a redundant dual-typed constant while satisfying both access patterns.
- `preset_band()` rounds to the nearest 25 ELO (a new named `BAND_ROUNDING_STEP` constant, distinct from `GRID_STEP`=100) per the plan's literal D-03 formula — kept as its own constant rather than reusing `GRID_STEP` since the two round to genuinely different grids for different reasons (lookup granularity vs. "approximate" band precision).
- `APPROX_ELO_DISCLAIMER` copy written to satisfy D-06 (states APPROXIMATE, derived from an internal calibration scale, carries a per-preset uncertainty band, reads as a guide) with zero em-dashes per the project's communication-style convention.

## Deviations from Plan

None — plan executed exactly as written. All three tasks' acceptance criteria pass unchanged from the plan's literal specification.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. No package installs (stdlib-only Python, per D-05/RESEARCH.md).

## Next Phase Readiness

Plan 02 (per D-11 split delivery) writes the off-grid confirmation-cell prediction file (2-3 cells per preset near each range endpoint + mid-range) for the operator-run HUMAN-UAT confirmation via `scripts/calibration-harness.mjs`. This plan's `compute_artifact()`, `isotonic_fit()`, and the real fitted blocks per preset are directly reusable by Plan 02's interpolated-CI logic (Open Question 1 in RESEARCH.md). No blockers.

---
*Phase: 181-per-preset-strength-lookup-curves*
*Completed: 2026-07-21*

## Self-Check: PASSED
