---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 04
subsystem: blunder-check-tooling
tags: [facepalm-score, refit, features-table, staged-model-selection, cross-validation, owner-fixtures]
requires:
  - phase: 254-01
    provides: "best_line_facts and the signed 9-slot LineFacts.material_array / opponent_mate_ply"
  - phase: 254-15
    provides: "FacepalmModel (D-06/D-07/D-08 shape fields), loss_feature / missed_feature, both score twins"
provides:
  - "facepalm_features.py facts schema: repeatable --labels, best line from game_positions.pv at the flaw ply, both 9-slot arrays, both mate plies, best_prob and pre_spread from ONE pre-blunder policy call"
  - "fit_facepalm.py: FeatureSchema (legacy | facts), CandidateSpec design matrices that are the twins' own terms, staged select_material_form / select_spread_form / select_pre_inputs, repeated-seed CV, D-13 and D-18 report sections, full-model --check-constants, --material-form / --spread-form"
  - "metrics.py: MaterialType, MIN_MISSED_GAIN, material_type (shared by the fit report, the later calibration report and the miss sampler)"
  - "tests/services/facepalm_owner_fixtures.py: OWNER_FIXTURE_FACTS (both owner misses with every score input, measured on dev)"
affects: [254-11, 254-12, 254-13]
tech-stack:
  added: []
  patterns:
    - "Fit candidates are real FacepalmModel instances; the design matrix uses loss_feature / missed_feature, and a parametrized test pins sigmoid(x @ coef) to facepalm_score for six model shapes"
    - "Stage decisions are made on seed-averaged CV AUC and fair share; a model only adds an input by beating the incumbent"
    - "Schema detected from the header: the committed legacy TSV keeps fitting and keeps reproducing the shipped constants"
key-files:
  created:
    - tests/services/facepalm_owner_fixtures.py
    - tests/services/test_facepalm_owner_fixtures.py
  modified:
    - scripts/blunder_check/facepalm_features.py
    - scripts/blunder_check/fit_facepalm.py
    - scripts/blunder_check/metrics.py
    - tests/scripts/test_facepalm_features.py
    - tests/scripts/test_fit_facepalm.py
    - tests/scripts/test_blunder_check_metrics.py
key-decisions:
  - "Stage choices use the mean over REPEAT_SEEDS=5 CV seeds (base seed FIT_SEED + 0..4) instead of one seed; the single-seed numbers are reported next to the mean and spread (Pitfall 10)"
  - "Fair-share ties: shares within FAIR_SHARE_TIE_TOLERANCE=0.01 count as equal so an input cannot enter on a coin-flip share difference; a remaining tie takes fewer free coefficients, first listed wins a full tie"
  - "The pre-refit baseline (split, no missed term) is fitted and shown in stage 1 as a reference row but is never a candidate: stage 1 decides how to carry the missed term"
  - "The facts-schema loss floor is fixed at 0 (D-05); --loss-floor is legacy only, --material-form / --spread-form are facts only, a flag of the other schema exits 2"
  - "best_uci = first token of pv at the flaw ply, else game_positions.best_move (Pitfall 7)"
requirements-completed: [D-06, D-07, D-08, D-10, D-13, D-16, D-18]
coverage:
  - id: D1
    description: "D-16: features script takes --labels more than once and writes both lines, both mate plies, best_prob and pre_spread from one pre-blunder policy call"
    requirement: "D-16"
    verification:
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py#test_features_reads_best_line_and_pre_inputs"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py#test_features_best_uci_falls_back_to_best_move"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py#test_features_multiple_label_files"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_facepalm_features.py#test_read_only_database_source_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-06 / D-07 / D-08: staged deterministic selection among combined vs split, three spread forms and the two optional Maia inputs; an input that earns nothing keeps a 0.0 coefficient"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_staged_selection_is_deterministic"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_an_informative_input_is_kept"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_tie_prefers_simpler_model"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_design_matrix_is_the_shipped_twin"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_forced_form_flags"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-13 / D-18: report with fair / unfair among passers per cut by material type and label set, repeated-seed CV, NULL best-line count, Constants block with every FACEPALM_* model constant"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_report_has_d13_sections"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_blunder_check_metrics.py#TestMaterialType"
        status: pass
    human_judgment: false
  - id: D4
    description: "--check-constants compares every FacepalmModel field including selectors, and still exits 0 on the legacy 2026-11-13 TSV against the pre-refit constants"
    requirement: "D-12"
    verification:
      - kind: other
        ref: "uv run python scripts/blunder_check/fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-13.tsv --out temp/blunder-check/fit-check-254-04.md --check-constants (exit 0)"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_check_constants_reports_every_field_that_moved"
        status: pass
    human_judgment: false
  - id: D5
    description: "Owner miss fixtures carry every score input (measured on dev) and pin the pre-refit defect (both score about 2%)"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "tests/services/test_facepalm_owner_fixtures.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "Whether the staged selection, tie tolerances and report layout suit the owner's real labels (needs the post-252 prod features run)"
    verification: []
    human_judgment: true
    rationale: "The selection rule is verified on synthetic data only; its behaviour on the real ~230 labels is the plan 11 owner decision"
duration: ~55 min (start time not captured, estimate)
completed: 2026-11-14
status: complete
plan_head_before: ca5069fec0b2060e2b142286635f2b69fca8d612
plan_head_after: f3701ade79e4cb20b0eafc41346df35403377a96
commits: 3
actuals:
  tokens: 24000
  tasks: 3
  commits: 3
---

# Phase 254 Plan 04: Refit tooling Summary

The post-252 refit is now a run-and-decide step: the features table carries both lines and the two pre-blunder Maia inputs, the fit picks among every D-06 / D-07 / D-08 shape in three deterministic stages and writes the D-13 report, `--check-constants` covers every model field, and the two owner misses carry every score input in the repo.

## Performance

- **Duration:** about 55 min (start time not captured)
- **Completed:** 2026-11-14T22:05Z
- **Tasks:** 3 of 3
- **Files:** 6 modified, 2 created

## Accomplishments

- **Features (D-16).** `facepalm_features.py` writes the facts schema (`best_prob`, `pre_spread`, `played_mat_1..9`, `line_mate_ply`, `best_mat_1..9`, `best_mate_ply`, `best_uci`, `best_pv_plies`). The best line always comes from `game_positions.pv` at the flaw ply (the `--pv-cache` path still only covers the refutation line); `best_uci` is the first pv token, else `best_move`. `best_prob` and `pre_spread` come from ONE `policy_fn(pre_board.fen(), elo)` call (a test counts the calls: one pre, one post). `--labels` is repeatable and optional, at least one of `--labels` / `--extra` is required (exit 2 otherwise). Read-only engine and exit codes unchanged.
- **Fit, facts schema (D-06, D-07, D-08).** Candidates are `CandidateSpec` shapes whose design columns are `loss_feature` / `missed_feature` and the twins' term rules; `model_from_spec` builds a real `FacepalmModel`. Stage 1 compares combined vs split crossed with missed floor `(None, 0)` and cap `(LOSS_CAP, 9)` (the pre-refit baseline is shown as a reference row); stage 2 the three spread forms; stage 3 adds `best_prob` (unless stage 2 already uses it) then `pre_spread`, each only if it beats the incumbent. Loss floor fixed at 0 (D-05), missed mate value stays `MATE_LOSS`, no forcing flag (D-10). `--material-form` and `--spread-form` force a stage and the report says so; `--check-constants` compares against the forced fit.
- **Report (D-13, D-18).** Stage tables with base-seed CV AUC and fair share plus the mean and spread over 5 seeds, the chosen model in words, fair / unfair among passers at every cut by material type and by label set, usable rows per set and material type, the count of label rows with a NULL best line, the count with a best mate within `LINE_DEPTH`, the set 6 holdout (miss set 7 trains), extras, and a `## Constants` block setting all 13 `FACEPALM_*` model constants.
- **`--check-constants`.** `constants_mismatches` compares every `FacepalmModel` field: coefficients within tolerance, floors, cap, mate value and both `Literal` selectors exactly. On the legacy 2026-11-13 TSV the refit carries the pre-refit defaults, so it still exits 0 against today's constants and would report any shipped field that moved.
- **Shared classifier.** `metrics.material_type` / `MaterialType` / `MIN_MISSED_GAIN` (loses, misses, loses_and_misses, neither, unknown), consistent with `missed_feature` (an unsettled played line only misses through a best mate).
- **Owner fixtures.** `OWNER_FIXTURE_FACTS` for games 817357 ply 24 (played 0, best 3, missed 3) and 820181 ply 65 (played 5, best 10, missed 5), every input measured on dev; both score about 2% (0.0215, 0.0201) under the pre-refit model, pinned below 0.1 for plan 12 to flip.

## Task Commits

1. **Task 1 (tracer): features with both lines and pre-blunder inputs, fit reads the facts schema, legacy TSV reproduces** - `ac5a4e796` (feat)
2. **Task 2: staged model selection and the D-13 report sections** - `6cb2a711e` (feat)
3. **Task 3: owner miss fixtures with every score input** - `f3701ade7` (test)

Tracer gate: the tracer `<verify>` is automated-only, so it was re-run end to end (49 tests, legacy `--check-constants` exit 0) before expansion.

## Verification

- `uv run pytest tests/scripts/test_facepalm_features.py tests/scripts/test_fit_facepalm.py tests/scripts/test_blunder_check_metrics.py tests/services/test_facepalm_owner_fixtures.py tests/services/test_facepalm_score.py -n auto` : 202 passed
- legacy `--check-constants` on `facepalm-features-2026-11-13.tsv`: exit 0
- `uv run ty check app/ tests/ scripts/`, `ruff check`, `ruff format --check`, `check_function_size.py app/ --fail-over-depth 4`: clean
- Acceptance `-k "staged or simpler or d13"`: 3 passed
- Mutation check: replacing the stage-3b candidate with the incumbent makes `test_an_informative_input_is_kept[pre_spread]` fail; restored.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Selection noise] Decisions on seed-averaged numbers and a fair-share tie tolerance**
- **Found during:** Task 2
- **Issue:** The plan's rule decides on single-seed CV AUC and fair share while Pitfall 10 warns that ~190 usable rows make 10-fold CV noisy; an input could enter on a coin-flip fair-share difference.
- **Fix:** every candidate is cross-validated over `REPEAT_SEEDS = 5` seeds and the AUC / fair share used by the rule are the seed means (single-seed values are still reported next to mean and spread). Fair shares within `FAIR_SHARE_TIE_TOLERANCE = 0.01` are a tie. The rule order is unchanged (AUC beyond `AUC_TIE_TOLERANCE`, then fair share, then fewer free coefficients), and both comparisons use `<=` so a zero tolerance cannot empty the contender set.
- **Files modified:** scripts/blunder_check/fit_facepalm.py
- **Verification:** `test_choose_candidate_rules`, `test_tie_prefers_simpler_model`
- **Committed in:** `6cb2a711e`

**2. [Rule 1 - Report text] Legacy report wording**
- **Found during:** Task 1
- **Issue:** adding the miss set "7" to `TRAIN_SETS` made the legacy report print "sets 1-5" as "sets 1-7".
- **Fix:** a `TRAIN_SETS_TEXT` constant ("1-5 and 7"); the extra-rows sentence now says "the model below" in both schemas. Legacy numbers are unchanged (the diff to the committed 2026-11-13 report is those two wording lines only).
- **Committed in:** `ac5a4e796`, `6cb2a711e`

### Process note

Task 2 is marked `tdd="true"` but the implementation and its tests were written in one pass, so there is no RED commit. A mutation check (above) proved the key behaviour test fails without the behaviour.

**Total deviations:** 2 auto-fixed (1 Rule 2, 1 Rule 1), 1 process note. **Impact:** no scope change; both fixes make the selection and the legacy report more faithful.

## Issues Encountered

- The per-plan commit ledger under the git dir was not used (worktree tooling), so `plan_head_before` is the dispatch base SHA and `commits: 3` was measured with `git rev-list --count` against it.
- The sandbox rejected multi-line `python3 -` heredocs against the worktree; large edits were applied with scripts kept in the scratchpad.
- **Prod step not run (no prod access).** The features run on prod with the miss labels (`--labels reports/blunder-check/leg2-labels-2026-11-11.tsv --labels <miss set 7 labels>`) and the committed refit report are left for the orchestrator after Phase 252 (plan 11). The tooling was exercised against dev (the two owner rows), synthetic facts tables and the committed legacy TSV; no prod output was faked.

## Known Stubs

None.

## Threat Flags

None. T-254-11 holds: `make_readonly_engine` is still the only engine of the features script (`test_builder_has_no_write_path` passes). T-254-12: `--check-constants` now covers every model field. T-254-13: fixtures carry game ids, plies and numbers only.

## Next Phase Readiness

Plan 11 can run: features on prod (both label files, `--db prod`), `fit_facepalm.py --features <tsv> --out <report>`, read the stage tables and D-13 sections, paste the `## Constants` block. Plan 12 flips `test_pre_refit_model_scores_both_misses_below_the_ceiling` to "at or above FACEPALM_SCORE_MIN" and reuses `OWNER_FIXTURE_FACTS`. Note for plan 11: on the legacy TSV `--check-constants` will report the moved Phase 254 fields by design once the refit constants ship.

## Self-Check: PASSED

Created files exist (`tests/services/facepalm_owner_fixtures.py`, `tests/services/test_facepalm_owner_fixtures.py`), commits `ac5a4e796`, `6cb2a711e`, `f3701ade7` are on HEAD, tests / ty / ruff / size gate pass.
