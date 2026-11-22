---
phase: 259-facepalm-first-principles-refit
plan: 08
subsystem: tooling
tags: [facepalm, calibration, sampler, spot-check, miss-labels, quiet-rule]

requires:
  - phase: 259-07
    provides: "metrics.material_type_of(loss, missed); the fit tool no longer imports the score twin"
  - phase: 259-01
    provides: "quiet_line_facts, quiet_best_line_facts, material_inputs_from_facts"
provides:
  - "sample.BlunderRecord with material_loss, material_missed, maia_best_reply_prob; CACHE_VERSION 5"
  - "sample._facepalm_facts(record): the single place every twin input of the sampler is built"
  - "render material type and spot check read the stored scalars"
  - "miss_labels on the quiet facts; metrics.material_type deleted"
affects: [259-09, 259-11]

actuals:
  tokens: 12300
  tasks: 2
  commits: 2
commits: 2
plan_head_before: dcc4266b282a03a59090bbd930fb01cc02a7ec6e
plan_head_after: 60184f380a7fad27615811a5d1bc34f778b00ed3

tech-stack:
  added: []
  patterns:
    - "one function (_facepalm_facts) builds every score-twin input of the calibration sampler, so the plan 09 twin switch edits one body"
    - "calibration tests seed inputs through tests.facepalm_seed.facepalm_fact_columns plus explicit scalars (_seed_inputs), and compare the record score to facepalm_expr selected for the same row"

key-files:
  created: []
  modified:
    - scripts/blunder_check/sample.py
    - scripts/blunder_check/render.py
    - scripts/blunder_check/spot_check.py
    - scripts/blunder_check/miss_labels.py
    - scripts/blunder_check/metrics.py
    - tests/scripts/test_blunder_check_calibration.py
    - tests/scripts/test_miss_labels.py
    - tests/scripts/test_blunder_check_metrics.py

key-decisions:
  - "The twin input stays today's old-line arguments inside _facepalm_facts (plan 09 swaps the body); the three stored scalars ride on the record next to them and are used by render, the spot check and the cache"
  - "The 'reply probability next to the spread' is a new column 'median best-reply prob' in the fair-share proxy table (the only place the report prints the median reply spread)"
  - "The material-type section prose now says the types come from the stored decaying-mean inputs, not a 3-ply read"
  - "The spot check's score-inputs line no longer prints the reply spread or played material 3 (plan text lists score, played prob, loss, missed, reply prob, mate ply); the report still shows the spread"

requirements-completed: [D-05, D-07, D-15]

coverage:
  - id: D1
    description: "Sampler selects material_loss, material_missed, maia_best_reply_prob from game_flaws, carries them on BlunderRecord and in the cache; CACHE_VERSION 5 refuses v3 and v4 caches"
    requirement: "D-15"
    verification:
      - kind: integration
        ref: "tests/scripts/test_blunder_check_calibration.py#TestTracer::test_record_carries_the_stored_scalars_into_the_report"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestCacheRoundTrip::test_an_older_cache_is_refused"
        status: pass
    human_judgment: false
  - id: D2
    description: "All twin inputs of the sampler are built in _facepalm_facts; the record score equals facepalm_expr(FACEPALM_DRILL_LAMBDA) for the same row"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "tests/scripts/test_blunder_check_calibration.py#TestTracer::test_sample_to_records_to_report"
        status: pass
    human_judgment: false
  - id: D3
    description: "Spot check prints the stored loss, missed gain and reply probability and no longer recomputes a depth-3 missed gain"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "tests/scripts/test_blunder_check_calibration.py#TestRenderSpotCheck"
        status: pass
    human_judgment: false
  - id: D4
    description: "miss_labels reads the quiet facts and material_type_of; metrics.material_type is deleted"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "tests/scripts/test_miss_labels.py#test_candidate_arrays_follow_the_quiet_rule_on_a_labelled_fixture"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_blunder_check_metrics.py#TestMaterialTypeOf"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-21
status: complete
---

# Phase 259 Plan 08: Calibration chain on the stored scalar inputs Summary

**The calibration sampler, report, spot check and miss-label sampler now read the stored material_loss, material_missed and reply probability (cache version 5), every twin input of the sampler is built in `_facepalm_facts`, and the depth-3 `material_type` is gone.**

## Performance

- **Duration:** about 8 min
- **Started:** 2026-11-21T19:23:52Z
- **Completed:** 2026-11-21T19:32:10Z
- **Tasks:** 2/2
- **Files modified:** 8

## Accomplishments

- `sample.py`: `_load_flaws` selects `GameFlaw.material_loss`, `material_missed`, `maia_best_reply_prob`; `FlawRow` and `BlunderRecord` carry them, `to_dict` / `from_dict` round-trip them, `CACHE_VERSION = 5` (v3 and v4 caches are refused). `_facepalm_facts(record)` builds the twin inputs (today's arguments, unchanged) and the cached `facepalm_score` calls it.
- `render.py`: `blunder_material_type` is `material_type_of(loss, 0.0 if missed is None else missed)`; the proxy table gains a "median best-reply prob" column next to the median reply spread; the material-type section prose describes the new source.
- `spot_check.py`: `_missed_gain`, `FACEPALM_MODEL` and `missed_feature` are gone; the missed-input line prints the stored missed gain, best-move probability and pre spread; the score-inputs line prints score, played prob, loss, missed, reply prob and mate ply.
- `miss_labels.py`: `quiet_line_facts` / `quiet_best_line_facts` for both lines, `material_type_of` on `material_inputs_from_facts`; docstring notes the quiet rule and that sets 7 and 8 (drawn under the old rule) are not redrawn.
- `metrics.py`: `material_type` deleted (with its `__all__` entry and the unused `LINE_DEPTH` import).
- Tests: calibration tests seed every score input through `facepalm_fact_columns` plus the three scalars in `_seed_inputs`; no `FacepalmFacts(` and no `_material` array literal remain in the file; the tracer test `test_record_carries_the_stored_scalars_into_the_report` pins DB row to record to rendered type to cache; the record score is asserted equal to `facepalm_expr(FACEPALM_DRILL_LAMBDA)` selected for the same row.
- Mutation checks (instead of trusting green): nulling `material_loss` in `_blunder_record` fails the tracer test; reverting miss_labels to the old `line_facts` fails `test_build_candidate_modes_and_arrays` and the new quiet-rule fixture test. Both reverted.

## Task Commits

1. **Task 1: tracer, stored scalars through the sampler record into the report** - `626fc9cb5` (feat)
2. **Task 2: spot check and miss labels on the stored inputs; depth-3 material type retired** - `60184f380` (refactor)

**Plan metadata:** the commit that carries this SUMMARY (docs: complete plan)

## Files Created/Modified

- `scripts/blunder_check/sample.py` - scalars on FlawRow/BlunderRecord, `_facepalm_facts`, CACHE_VERSION 5
- `scripts/blunder_check/render.py` - material type from the scalars, reply-prob column
- `scripts/blunder_check/spot_check.py` - stored inputs printed, model recomputation removed
- `scripts/blunder_check/miss_labels.py` - quiet facts and `material_type_of`
- `scripts/blunder_check/metrics.py` - `material_type` removed
- `tests/scripts/test_blunder_check_calibration.py`, `tests/scripts/test_miss_labels.py`, `tests/scripts/test_blunder_check_metrics.py` - re-pointed tests

## Decisions Made

See key-decisions. In short: `_facepalm_facts` keeps the old-line arguments for plan 09 to swap; the reply probability shows as a new proxy-table column; the spot check drops the reply-spread and played-material-3 fields from its score line.

## Deviations from Plan

None - plan executed exactly as written, with these small interpretations:

- The `_blunder` test factory (hand-built records for the section tests) gained `material_loss`, `material_missed` and `reply_prob` parameters, with defaults derived from the played depth-3 material, so the existing section tests stay readable; section tests that assert a material type now pass the scalars explicitly.
- `test_miss_labels.py`: the expected arrays in `test_build_candidate_modes_and_arrays` are hand-derived literals (verified against the code afterwards, they matched). The new fixture test uses label 153 from `LINE_FIXTURES` (`expected_quiet_loss` (0, 3, 3, 2, 2) vs the old (0, 3, 3, 2, 1)); labels 154, 156 and 170 are not kept by `build_candidate` in disagreement mode with an arbitrary best line, so they are covered by `tests/services/test_line_material.py` only.
- Quick task 261121-n50 had already deleted some script tests; none named by this plan were missing.

## Issues Encountered

None. The new proxy-table column shifted two test indices in `TestRecommendedConstants`; updated.

## Known Stubs

None.

## Threat Flags

None. T-259-18: both samplers still use `make_readonly_engine`, no write path added. T-259-19: CACHE_VERSION 5 refuses older caches (`test_an_older_cache_is_refused`, v3 and v4). T-259-SC: no package installed.

## Verification

- `uv run pytest -n auto tests/scripts/test_miss_labels.py tests/scripts/test_blunder_check_metrics.py tests/scripts/test_blunder_check_calibration.py -x`: 144 passed; whole `tests/scripts` (-n auto): 850 passed.
- `uv run ty check app/ tests/ scripts/`, `uv run ruff check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean.
- Acceptance greps: `def _facepalm_facts` 1; `GameFlaw.material_loss` in sample.py 1; `FacepalmFacts(` in the calibration test 0; `CACHE_VERSION` 5; `FACEPALM_MODEL|missed_feature` in spot_check.py 0; `material_type(` callers 0; `line_facts|best_line_facts` words in miss_labels.py 0.
- Tracer gate: interactive, end-of-phase mode, automated-only verify: re-run green, expanded.

## Next Phase Readiness

Plan 09 switches the twin by editing `sample._facepalm_facts` (the record already carries loss, missed and reply prob). The old line arrays are still on the record for the old twin until then; the D-15 prod calibration in plan 11 reads the new columns through this sampler.

## Self-Check: PASSED

- All eight modified files exist; commits `626fc9cb5` and `60184f380` are ancestors of HEAD; `git rev-list --count dcc4266b2..HEAD` = 2 at SUMMARY time.

---
*Phase: 259-facepalm-first-principles-refit*
*Completed: 2026-11-21*
