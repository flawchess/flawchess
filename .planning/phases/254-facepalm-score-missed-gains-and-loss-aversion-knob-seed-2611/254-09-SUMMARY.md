---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 09
subsystem: operator-scripts
tags: [facepalm-score, calibration-report, spot-check, backfill-status, query-time-expression, test-seeding]
requires:
  - phase: 254-02
    provides: "facepalm_expr(lam) and tests/facepalm_seed.py (facepalm_fact_columns, SEED_FACEPALM_MARGIN)"
  - phase: 254-04
    provides: "MaterialType and material_type in scripts/blunder_check/metrics.py"
  - phase: 254-18
    provides: "Library readers on the expression; last R2 plan before the operator scripts"
provides:
  - "Calibration sample and cache (version 3) that store facts; BlunderRecord.facepalm_score computed with the Python twin at FACEPALM_DRILL_LAMBDA and the checkout's model"
  - "section_material_types and section_pool_by_cut: the D-13 tables for choosing FACEPALM_SCORE_MIN"
  - "Spot check printing best material, missed gain, best-move probability and pre-blunder spread"
  - "Backfill status counts (user_blunders_with_score, user_blunders_qualifying) on facepalm_expr(FACEPALM_DRILL_LAMBDA)"
affects: [254-10, 254-11]
tech-stack:
  added: []
  patterns:
    - "A report record holds facts and exposes the score as a cached property over the Python twin, so a candidate refit is evaluated by editing constants in the checkout"
    - "Status counts bind the same expression the drill selects with; a parity test pins them to the stored-column counts under the pre-refit constants"
key-files:
  created: []
  modified:
    - scripts/blunder_check/sample.py
    - scripts/blunder_check/render.py
    - scripts/blunder_check/spot_check.py
    - scripts/backfill_maia_flaws.py
    - tests/scripts/test_blunder_check_calibration.py
    - tests/scripts/test_backfill_maia_flaws.py
key-decisions:
  - "BlunderRecord.facepalm_score is a functools.cached_property: the report reads it in many passes (every threshold, every section), and the facts never change after construction"
  - "The cache stores facts only (no score key); a version 2 cache is refused with a message naming both versions and telling the operator to re-run without --from-cache"
  - "section_pool_by_cut splits the own pool per Elo bucket with a new own_windows_by_bucket (exact per-user count in that bucket times the bucket's rates at the cut) next to the existing all-users estimate, since 'per rating band' needs it"
  - "section_material_types prints all five MaterialType values (unknown included) pooled, then a per-bucket table that skips buckets with no blunders"
  - "scripts/copy_line_material.py keeps its read of GameFlaw.facepalm_score: it is plan 03's read-only parity check (stored versus expression), which plan 10 needs before R2 ships"
requirements-completed: [D-01, D-03, D-12, D-13]
coverage:
  - id: D1
    description: "A calibration BlunderRecord holds facts and scores them with the twin at FACEPALM_DRILL_LAMBDA; the report ignores a decoy stored score; unscored, no-spread, no-line and line-too-short are told apart from the facts; the loss helper flips sign"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/scripts/test_blunder_check_calibration.py#TestTracer::test_sample_to_records_to_report"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestBlunderRecordFacts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Cache version 3 round-trips every fact and stores no score; a version 2 cache is refused with a message naming the version"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestCacheRoundTrip"
        status: pass
    human_judgment: false
  - id: D3
    description: "The report shows pass shares per material type and Elo bucket, and the own and foreign drill pool at every cut of the grid, a higher cut never growing the foreign pool"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestSectionMaterialTypes"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestSectionPoolByCut"
        status: pass
    human_judgment: true
    rationale: "The owner reads these tables on the real sample to choose FACEPALM_SCORE_MIN; the tests pin structure and monotonicity, not that the tables are readable or sufficient for that decision"
  - id: D4
    description: "The spot check prints played and best depth-3 material, missed gain, best-move probability and pre-blunder spread, and marks an unknown best line instead of a zero gain"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestRenderSpotCheck::test_spot_check_prints_missed_inputs"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestRenderSpotCheck::test_spot_check_marks_an_unknown_best_line"
        status: pass
    human_judgment: false
  - id: D5
    description: "Backfill status counts use facepalm_expr(FACEPALM_DRILL_LAMBDA) and equal the stored-column counts under the pre-refit constants; reverting the qualifying count to the stored column fails the status test"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_spread_status_counts"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full backend suite, ty, ruff and the nesting-depth gate are clean on the new scripts"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "uv run pytest -n auto -x -q (6585 passed, 19 skipped)"
        status: pass
    human_judgment: false
duration: 11 min
completed: 2026-11-15
status: complete
plan_head_before: a5d560a47947a596944f7cabc6c692405f15491c
plan_head_after: 2850ed52be6ecc3c0f6a6849a5c8928436c56e59
commits: 4
actuals:
  tokens: 14100
  tasks: 3
  commits: 4
---

# Phase 254 Plan 09: Operator scripts on facts and the expression Summary

**The calibration sample, report and spot check now carry stored facts and score them with the Python twin at the drill lambda, the report gains the D-13 pass-share and drill-pool tables, and the backfill status counts read `facepalm_expr(FACEPALM_DRILL_LAMBDA)`.**

## Performance

- **Duration:** 11 min (00:32 to 00:43 UTC), including a 108 s full suite
- **Tasks:** 3 (a tracer, a TDD task, an auto task)
- **Files modified:** 6

## Accomplishments

- `BlunderRecord` replaces the stored loss and score fields with `played_3`, `best_3`, `best_mate_ply`, `maia_best_prob`, `maia_pre_spread` (keeping `line_mate_ply`, `has_line`) and exposes `facepalm_score` as a cached property over `facepalm_score(FacepalmFacts(...), lam=FACEPALM_DRILL_LAMBDA, model=FACEPALM_MODEL)`. `_load_flaws` selects the two material arrays and reads depth `LINE_DEPTH` with `material_at_depth`. `CACHE_VERSION` is 3 and `to_dict` carries no score; an older cache raises a `ValueError` naming both versions.
- `render.py`: the material-loss helper flips sign; `section_material_types` (pooled table, then Elo bucket by material type, pass share of the scored blunders at every cut of `pass_thresholds`) and `section_pool_by_cut` (own pool as p25 / median usable windows per user, all users and per Elo bucket; foreign pool as qualifying blunders per pinned-Elo level, one column per cut) are inserted after the facepalm section. The "How to read" text names the drill lambda and that scores come from the checkout's constants.
- `spot_check.py` prints a `Missed inputs` line (best material 3, missed gain via `missed_feature` with the model's settings, best-move probability, pre-blunder spread); an unknown best line prints `n/a`, not a zero gain.
- `backfill_maia_flaws._fetch_facepalm_value_counts` binds `facepalm_expr(FACEPALM_DRILL_LAMBDA)` once for the scored and qualifying predicates.
- Tests: the calibration factory seeds facts (`score=` goes through `facepalm_fact_columns`, explicit facts override); the DB fixture seeds facts plus a decoy stored score the report must ignore; the status test asserts parity with the stored-column counts before reseeding facts above the bar.
- Proof the status test bites: reverting the qualifying predicate to the stored column failed `test_spread_status_counts`, then restored.

## Task Commits

1. **Task 1 (tracer): facts-based sample, twin-scored report** - `79fc80d10` (feat)
2. **Task 2 (TDD RED): failing tests for the D-13 sections and spot-check inputs** - `b6d031d85` (test)
3. **Task 2 (TDD GREEN): material-type and pool-by-cut sections, spot-check inputs** - `569737759` (feat)
4. **Task 3: backfill status counts on the expression** - `2850ed52b` (feat)

Tracer gate: the tracer `<verify>` is automated-only; it was re-run end to end (70 tests in the calibration file) before the expansion task.

## TDD Gate Compliance

- **RED:** six target tests failed for the planned reason: `section_material_types` and `section_pool_by_cut` were stubs raising `NotImplementedError` (four tests), and the two spot-check tests failed on the missing `Missed inputs` text. The `gsd_run check tdd-red-evidence` classifier was not run (no TAP/JUnit record captured; the pytest output was inspected by hand). Semantic assessment: the targets executed and failed on the intended behaviour, not on import, collection or fixture faults; the stubs were committed with the RED tests so the module imports.
- **GREEN:** 76 passed in the calibration file.
- **REFACTOR:** none needed.

## Files Created/Modified

- `scripts/blunder_check/sample.py` - facts on `BlunderRecord`/`FlawRow`, `_flaw_row`, computed `facepalm_score`, cache version 3
- `scripts/blunder_check/render.py` - sign-flipped loss helper, `blunder_material_type`, `section_material_types`, `own_windows_by_bucket`, `section_pool_by_cut`, wiring and text
- `scripts/blunder_check/spot_check.py` - `_missed_gain`, `_missed_inputs_line`, played material replaces line loss
- `scripts/backfill_maia_flaws.py` - expression-based status counts
- `tests/scripts/test_blunder_check_calibration.py`, `tests/scripts/test_backfill_maia_flaws.py` - facts seeding, new section, cache and parity tests

## Decisions Made

See key-decisions. The cached property is safe because no code mutates facts after a record is built; a test that did would see a stale score.

## Deviations from Plan

**1. [Acceptance criterion not met as written] `grep -rn "GameFlaw\.facepalm_score" scripts` prints 1, not 0**
- **Found during:** Task 3
- **Issue:** the remaining hit is `scripts/copy_line_material.py:292`, plan 03's `--parity` mode, whose whole job is to compare the stored column with the expression (D-01 / D-12) so plan 10 can gate R2 on it. The plan's "baseline 3" predates that file (the live baseline was 4: sample, two in backfill, copy_line_material).
- **Fix:** none. Rewriting the parity read would defeat its purpose. Every other script reads facts or the expression; the sample and backfill hits are gone.
- **Files modified:** none

**Total deviations:** 1 (a criterion that conflicts with an intended read). **Impact:** none on behaviour; plan 10 keeps its parity check.

## Issues Encountered

- `app/services/blunder_check_candidates.py:203` still reads `flaw.facepalm_score` (the stored value on a loaded row). It is app code outside this plan's file list; flagged for the plan that owns the blunder-check selection readers, not touched here.
- No real calibration run was made (needs a sample against dev or prod); the report was rendered from synthetic collections only. Run it on the dev sample before the owner chooses `FACEPALM_SCORE_MIN`.
- No dev database state was changed; Alembic head stays `a7d2c9e1b254`. Calibration DB tests commit games and delete them in teardown.

## Known Stubs

None.

## Threat Flags

None. T-254-26 mitigated (`CACHE_VERSION` 3, other versions refused with a message naming both; tested); T-254-27 mitigated (`make_readonly_engine` untouched, no write statement added; the status counts are SELECT-only).

## Next Phase Readiness

No operator script reads the stored score except the parity check. Plan 10 runs the prod EXPLAIN and parity checks; plan 11 can judge a candidate refit by editing the `FACEPALM_*` constants and re-rendering the report from a version 3 cache.

## Self-Check: PASSED

Commits `79fc80d10`, `b6d031d85`, `569737759`, `2850ed52b` are on HEAD (`git rev-list --count` from the plan base: 4). Verified: `CACHE_VERSION: int = 3` and `FACEPALM_DRILL_LAMBDA` in `sample.py`; `grep -c "GameFlaw.facepalm_score" sample.py` prints 0; `def section_material_types(` and `def section_pool_by_cut(` in `render.py`; calibration tests 76 passed, backfill tests 39 passed; `uv run pytest -n auto -x -q` 6585 passed, 19 skipped; `ty check app/ tests/ scripts/`, `ruff check .`, `ruff format --check` and `check_function_size.py app/ --fail-over-depth 4` clean.
