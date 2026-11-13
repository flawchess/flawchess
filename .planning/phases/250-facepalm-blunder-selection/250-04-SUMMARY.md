---
phase: 250-facepalm-blunder-selection
plan: 04
subsystem: scoring
tags: [logistic-regression, facepalm-score, maia, constants, blunder-check, fit-report]

requires:
  - phase: 250-facepalm-blunder-selection
    provides: "plan 01 facepalm_score twins, plan 02 fit_facepalm.py and the committed features TSV"
provides:
  - "FACEPALM_INTERCEPT / PLAYED_COEF / SPREAD_COEF / LOSS_COEF / LOSS_FLOOR in the selection constants block of app/services/blunder_check_rules.py"
  - "facepalm_score.FACEPALM_MODEL, the default model of facepalm_score and facepalm_score_sql"
  - "fit_facepalm.py --check-constants (CHECK_CONSTANTS_TOLERANCE 1e-4, EXIT_CONSTANTS_MISMATCH 6)"
  - "reports/blunder-check/facepalm-fit-2026-11-13.md, the committed provisional fit report"
affects: [250-05, 250-06, 250-07, FACEPALM_SCORE_MIN, D-18 refit after Phase 252]

actuals:
  tokens: 14000
  tasks: 2
  commits: 1
plan_head_before: 08135a98b6d0b577aeda01b45a70ac748bcec885
plan_head_after: 012cfec275fe03b130ba1888bf8e366ef7179209

tech-stack:
  added: []
  patterns:
    - "Shipped constants are the machine output of the fit; --check-constants proves it by refitting the committed TSV"

key-files:
  created:
    - reports/blunder-check/facepalm-fit-2026-11-13.md
  modified:
    - app/services/blunder_check_rules.py
    - app/services/facepalm_score.py
    - scripts/blunder_check/fit_facepalm.py
    - tests/scripts/test_fit_facepalm.py
    - tests/services/test_facepalm_score.py

key-decisions:
  - "Owner chose ship-as-fitted: Form A, loss floor 0, FACEPALM_SCORE_MIN 0.7, no constant change"
  - "Window 14 (game 2099808 ply 23) is unscored (NULL score, 1-ply stored line) and asserted as None, accepted by the owner for now; the real check waits for the D-18 refit on repaired lines"
  - "Loss floor 0 chosen over unclipped on a tie (CV AUC 0.880 vs 0.878)"

patterns-established:
  - "WINDOW_14_* test constants copied from the committed features TSV; score asserted None rather than xfail"

requirements-completed: [D-01, D-03, D-04]

coverage:
  - id: C1
    description: "Shipped coefficients are the output of the fit on the committed TSV (reproducible)"
    requirement: "D-01"
    verification:
      - kind: other
        ref: "fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-13.tsv --check-constants: 'constants match', exit 0"
        status: pass
    human_judgment: false
  - id: C2
    description: "FACEPALM_MODEL is the default of facepalm_score and facepalm_score_sql; SQL parity on the plan-01 grid; Window 14 test"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "uv run pytest tests/services/test_facepalm_score.py tests/scripts/test_fit_facepalm.py -x (37 passed; -k window_14: 2 passed)"
        status: pass
    human_judgment: false
  - id: C3
    description: "Form A vs Form B, clip choice, out-of-fold fair/unfair among passers, set-6 holdout written to the report"
    requirement: "D-03"
    verification:
      - kind: other
        ref: "reports/blunder-check/facepalm-fit-2026-11-13.md sections Form A, Form B, Clip choice, Sets 1-5 vs set 6, Constants"
        status: pass
    human_judgment: false
  - id: C4
    description: "Owner confirmed form, clip and threshold before the hook and backfill are built"
    requirement: "D-01"
    verification:
      - kind: other
        ref: "Task 2 checkpoint:decision, owner reply 'ship-as-fitted, unscored Window 14 is fine for now'"
        status: pass
    human_judgment: true

duration: not recorded
completed: 2026-11-13
status: complete
---

# Phase 250 Plan 04: Fitted Facepalm Constants and Owner Confirmation Summary

**The facepalm score now ships as five fitted named constants (Form A, loss floor 0, threshold 0.7), wired as the default model of both the Python and SQL scorers and provably the refit of the committed label features**

## Accomplishments

- Ran `fit_facepalm.py` on the committed 181-row features TSV and committed `reports/blunder-check/facepalm-fit-2026-11-13.md` (Data, Form A, Form B, Clip choice, Sets 1-5 vs set 6, Extra rows, Constants).
- Pasted the printed constants unedited into the selection constants block of `blunder_check_rules.py`; `FACEPALM_MODEL` in `facepalm_score.py` is built from them and is the default `model` of `facepalm_score` and `facepalm_score_sql`.
- Added `--check-constants` (tolerance 1e-4, exit 6 on mismatch) with match and mismatch tests; on the committed TSV it reports "constants match" and exits 0.
- Added `WINDOW_14_*` constants, a Window 14 test and a SQL-vs-Python parity test on the shipped model.
- Owner decision at the Task 2 checkpoint: `ship-as-fitted`.

## Fit Facts

- Rows used: 140 of 181 (88 fair, 52 unfair). Excluded: 7 undecided, 1 extra row (Window 14), 33 with a NULL loss feature (stored line too short to tell).
- Form A CV AUC 0.880 vs Form B 0.863. Loss floor 0 vs unclipped: 0.880 vs 0.878, chosen on a tie.
- At FACEPALM_SCORE_MIN 0.7, out-of-fold, Form A: 72 passers, 64 fair, 8 unfair (precision 0.889).
- Set-6 holdout AUC 0.911; 32 passers at 0.7: 30 fair, 2 unfair.
- Shipped constants: FACEPALM_INTERCEPT -1.4193, FACEPALM_PLAYED_COEF -0.6629, FACEPALM_SPREAD_COEF -0.3304, FACEPALM_LOSS_COEF 1.1570, FACEPALM_LOSS_FLOOR 0.

## Task Commits

1. **Task 1: Tracer, committed features to fit report to shipped constants to Window 14** - `012cfec27` (feat)
2. **Task 2: Owner confirms form, clip and threshold** - no commit (decision only: ship-as-fitted)

**Plan metadata:** committed separately (docs: complete plan)

## Decisions Made

- Ship Form A with loss floor 0 and FACEPALM_SCORE_MIN 0.7 as fitted; no constant or code change after the checkpoint.
- Window 14's score is `None`, not a value below 0.7: its stored line is 1 ply, so `line_loss_3` is NULL and the score is unscored. The owner accepts this for now; the real evaluation is deferred to the D-18 refit on repaired lines. The test asserts `None` (not an xfail).

## Deviations from Plan

### Plan deviation recorded for the decision

**1. [Plan expectation not met] Window 14 is unscored rather than below threshold**
- **Found during:** Task 1
- **Issue:** The plan expected Window 14 to score below FACEPALM_SCORE_MIN; with a 1-ply stored line the score is NULL, so a below-threshold score cannot be shown.
- **Fix:** No tuning. The test asserts the score is `None`; raised as the first item of the Task 2 decision and accepted by the owner ("unscored Window 14 is fine for now").
- **Files modified:** tests/services/test_facepalm_score.py
- **Commit:** 012cfec27

Task 1 additions beyond the plan's literal wording stay inside the planned file set: the `--check-constants` flag, the `FACEPALM_MODEL` default used by both twins and the Window 14 constants.

## Issues Encountered

Flag for later plans (05-07) and D-18: a blunder whose stored line is shorter than `LINE_DEPTH` plies (and not settled by a mate or the recapture credit) has a NULL `facepalm_score` and is never selectable until the D-18 refit on repaired lines. That is about 18% of the label rows (33 of 181).

## Verification

- `uv run pytest tests/services/test_facepalm_score.py tests/scripts/test_fit_facepalm.py -x`: 37 passed (`-k window_14`: 2 passed).
- `fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-13.tsv --out temp/blunder-check/fit-check.md --check-constants`: "constants match", exit 0.
- `uv run ty check app/ tests/ scripts/`: all checks passed.
- Acceptance greps: 5 `FACEPALM_*` constant lines in `blunder_check_rules.py`, 4 `FACEPALM_MODEL` occurrences in `facepalm_score.py`, report contains the Form B, Clip choice and Constants sections.

## Known Stubs

None.

## Threat Flags

None. T-250-11 mitigated by `--check-constants`; T-250-12 mitigated (report holds game ids, numbers and counts only).

## Next Phase Readiness

- Plans 05-07 can build the hook and backfill on `FACEPALM_MODEL` and `FACEPALM_SCORE_MIN = 0.7`.
- Short-line blunders are unselectable until D-18; keep that in mind when sizing the backfill and reading the beta drill pool.

## Self-Check: PASSED

Commit `012cfec27` is an ancestor of HEAD; the report, the two service files, the fit script and both test files exist; plan commit count measured as 1 from the ledger base.

---
*Phase: 250-facepalm-blunder-selection*
*Completed: 2026-11-13*
