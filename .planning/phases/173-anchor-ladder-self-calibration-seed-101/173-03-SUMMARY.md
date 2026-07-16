---
phase: 173-anchor-ladder-self-calibration-seed-101
plan: 03
subsystem: tooling
tags: [python, stdlib, statistics, bradley-terry, elo, calibration, tdd]

# Dependency graph
requires: []
provides:
  - "scripts/calibration_anchor_fit.py — stdlib-only Zermelo/MM joint Bradley-Terry/Elo rating fit over an anchor-vs-anchor game graph"
  - "load_games/build_win_counts parsing the per-game TSV column contract shared with Plan 02's calibration-anchor-ladder.mjs"
  - "check_connectivity D-04 defensive fail-loud guard (BFS reachability + >=2 cross-family edges)"
  - "bootstrap_ci nonparametric per-anchor CIs and compute_residuals cross-family-flagged per-pair residuals (D-06)"
affects: [173-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Zermelo/MM fixed-point iteration for Bradley-Terry MLE (stdlib math/random only, no numpy/scipy)"
    - "TypedDict for internal structured data (ResidualRow) rather than dict[str, object], per ty compliance"
    - "Continuity-correction clamp (epsilon = 1/(2*games)) ported from scripts/lib/calibration-elo.mjs's SCORE_CLAMP_EPSILON_DIVISOR pattern"

key-files:
  created:
    - scripts/calibration_anchor_fit.py
    - tests/scripts/test_calibration_anchor_fit.py
  modified: []

key-decisions:
  - "fit_bradley_terry returns ratings already converted to the 400*log10(pi) scale (not raw strengths) so apply_scale_fix operates uniformly on ratings"
  - "apply_scale_fix assigns the pin anchor's value directly (not via addition) so the D-05 pin is exact regardless of floating-point rounding"
  - "bootstrap_ci resamples the full flat game list uniformly (not stratified per pair), matching RESEARCH.md Pattern 2's literal description"
  - "compute_residuals uses a TypedDict (ResidualRow) instead of dict[str, object] to satisfy ty's static analysis on tuple-unpacking the pair field"
  - "Test fixed during implementation: the pinned anchor's bootstrap CI collapses to a zero-width point by construction (apply_scale_fix pins it exactly in every resample) — documented as expected behavior, not a bug"

patterns-established:
  - "Pattern: stdlib-only statistical fit tooling in scripts/ mirrors backfill_eval.py's argparse/docstring runbook conventions even with no DB/engine dependency"

requirements-completed: [D-04, D-05, D-06, D-07]

coverage:
  - id: D1
    description: "Python script fits a joint Bradley-Terry/Elo rating for every anchor from a per-game TSV, with draws folded 0.5/0.5"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "tests/scripts/test_calibration_anchor_fit.py#test_fit_converges"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_calibration_anchor_fit.py#test_draws"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fitted scale is pinned so maia1500 == 1500 exactly (internal scale, NOT human ELO)"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "tests/scripts/test_calibration_anchor_fit.py#test_scale_fix"
        status: pass
    human_judgment: false
  - id: D3
    description: "Per-anchor bootstrap CIs and per-pair residuals (cross-family flagged) are produced"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "tests/scripts/test_calibration_anchor_fit.py#test_bootstrap"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_calibration_anchor_fit.py#test_residuals"
        status: pass
    human_judgment: false
  - id: D4
    description: "Disconnected or under-cross-linked game graph is rejected loudly before fitting (D-04 defensive re-check)"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "tests/scripts/test_calibration_anchor_fit.py#test_connectivity"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-15
status: complete
---

# Phase 173 Plan 03: Anchor Ladder Rating Fit Tooling Summary

**Stdlib-only Zermelo/MM Bradley-Terry rating fit (`scripts/calibration_anchor_fit.py`) with a maia1500=1500 scale pin, bootstrap CIs, cross-family residuals, and a fail-loud D-04 connectivity guard — TDD RED then GREEN, six passing unit tests, zero ruff/ty errors, no numpy/scipy.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-15T21:55:00+02:00 (approx)
- **Completed:** 2026-07-15T22:04:02+02:00
- **Tasks:** 2 (RED test suite, GREEN implementation)
- **Files modified:** 2

## Accomplishments
- `scripts/calibration_anchor_fit.py` implements the full D-05/D-06/D-07 rating-fit pipeline: TSV loading, draw-folded win-count construction, Zermelo/MM fixed-point MLE (symmetric `1.0` init per Pitfall 3 — never seeded from folklore `SF_SKILL_ELO`), exact scale pinning, nonparametric bootstrap CIs, and cross-family-flagged per-pair residuals.
- `check_connectivity` (D-04) runs as a fail-loud `RuntimeError` guard inside `main()` **before** any fit call — proven both via a disconnected-graph fixture and a connected-but-under-cross-linked (1 edge) fixture, both raising, and a 2-cross-link fixture that does not raise.
- Degenerate-pair continuity clamp (`epsilon = 1/(2*games)`) ported from `scripts/lib/calibration-elo.mjs`'s `SCORE_CLAMP_EPSILON_DIVISOR` pattern (Pitfall 2), applied inside `fit_bradley_terry` before the MM iteration.
- End-to-end smoke-tested via `main()` on a synthetic TSV: produces both `scripts/lib/calibration-internal-scale.mjs`-shaped JS output (`export const INTERNAL_RATING = {...}`) and a JSON sibling with CIs + residuals, both carrying the D-13 "internal scale — NOT human ELO" caveat header.
- Zero `numpy`/`scipy` imports (verified via `grep -Ec 'import (numpy|scipy)'` returning 0) — D-07 satisfied via pure stdlib (`math`, `random`, `argparse`, `json`).

## Task Commits

Each task was committed atomically (TDD RED/GREEN):

1. **Task 1: Write the fit test suite first (RED)** - `3cb27961` (test)
2. **Task 2: Implement the stdlib Zermelo/MM fit + guards + artifact emitters (GREEN)** - `c031b221` (feat)

_Note: Task 2's commit also includes a one-line test correction (see Decisions) discovered while implementing bootstrap_ci — not a separate commit since it was found and fixed within the same GREEN cycle before the test suite went green._

## Files Created/Modified
- `scripts/calibration_anchor_fit.py` - Public API (`load_games`, `build_win_counts`, `fit_bradley_terry`, `apply_scale_fix`, `check_connectivity`, `bootstrap_ci`, `compute_residuals`, `main`) plus a `ResidualRow` TypedDict and argparse CLI
- `tests/scripts/test_calibration_anchor_fit.py` - Six pure-function unit tests, one per behavior, each with a named tolerance constant and a hand-computed or independently-derived oracle

## Decisions Made
- `fit_bradley_terry` returns ratings already on the `400*log10(pi)` scale (not raw Bradley-Terry strengths), so `apply_scale_fix` operates uniformly on rating dicts throughout the pipeline (matches the plan's literal API description).
- `apply_scale_fix` assigns the pin anchor's rating directly to `value` (not `ratings[pin] + shift`) so the D-05 "exactly 1500.0" pin holds regardless of floating-point rounding in the shift computation.
- `bootstrap_ci` resamples the full flat game list uniformly with replacement (not stratified per pair) — matches RESEARCH.md Pattern 2's literal description ("resample games with replacement, refit").
- `compute_residuals` returns `list[ResidualRow]` (a `TypedDict`) instead of `list[dict[str, object]]` — `ty` could not statically verify tuple-unpacking `row["pair"]` on a plain `object`-valued dict; the TypedDict makes every field's type precise with zero suppression comments needed.
- Test correction found during GREEN: `test_bootstrap` originally asserted a non-zero, non-huge CI width for every anchor including the pin (`maia1500`). Since `apply_scale_fix` pins `maia1500` to exactly `1500.0` in every one of the 200 bootstrap resamples, its CI is *by construction* a zero-width point — not a bug in `bootstrap_ci`. Fixed the test to assert `width ≈ 0` for the pin anchor and the original sane-width bounds for the other two.

## Deviations from Plan

None - plan executed exactly as written. The one test-assertion correction above was a self-caught error in the RED-phase test's own expectation (not a deviation from the plan's specified behavior) — the plan's `<behavior>` bullet for bootstrap only requires "a finite (lo, hi) per anchor with lo <= point <= hi and a sane (non-zero, non-huge) width," and the pin anchor's zero-width CI is a direct, correct consequence of D-05's exact-pin requirement, not a violation of that bullet (the point IS the pin's CI collapsing to itself).

## Issues Encountered
None beyond the test-assertion fix documented above. `ruff format` reformatted both files on first run (line-wrapping for readability) — accepted as-is, no logic change.

## User Setup Required
None - no external service configuration required. This is a local, developer-invoked CLI tool with no network/DB/auth surface.

## Next Phase Readiness
- `scripts/calibration_anchor_fit.py` is ready to consume the real per-game TSV once Plan 02's `calibration-anchor-ladder.mjs` harness run produces one — the TSV column contract (`pass\tanchor_white\tanchor_black\tresult\treason\tplies\tgame_index\topening\tseed\tgit_sha`) is locked and shared verbatim between the two plans.
- Plan 04 (D-11/D-12 execution + artifact finalization) can call this script's `main()` directly with `--input`/`--out-js`/`--out-json` against the real anchor-ladder run's output TSV.
- No blockers. This plan intentionally does NOT run the real multi-hour anchor-vs-anchor game harness (that is Plan 04's job, per the plan's own scope note) — only the fit tooling and its unit-level proof are delivered here.

---
*Phase: 173-anchor-ladder-self-calibration-seed-101*
*Completed: 2026-07-15*

## Self-Check: PASSED

- FOUND: scripts/calibration_anchor_fit.py
- FOUND: tests/scripts/test_calibration_anchor_fit.py
- FOUND: 3cb27961 (test commit)
- FOUND: c031b221 (feat commit)
