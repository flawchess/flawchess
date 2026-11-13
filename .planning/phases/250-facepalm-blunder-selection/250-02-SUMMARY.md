---
phase: 250-facepalm-blunder-selection
plan: 02
subsystem: tooling
tags: [logistic-regression, irls, numpy, cross-validation, blunder-check, maia, features-tsv]

requires:
  - phase: 250-facepalm-blunder-selection
    provides: "plan 01: line_facts, loss_feature, facepalm_score, D-04 constants, public reply_spread"
  - phase: 248-maia-refutation
    provides: "game_positions.pv refutation line and the pinned-Elo Maia scoring pattern"
provides:
  - "scripts/blunder_check/facepalm_features.py: label rows to features TSV builder (read-only DB, optional pv cache, extra rows, FEATURE_COLUMNS)"
  - "scripts/blunder_check/fit_facepalm.py: numpy IRLS logistic fit, seeded 10-fold CV, Form A / Form B / loss-clip comparison, precision-among-passers table, constants block"
  - "reports/blunder-check/facepalm-features-2026-11-13.tsv: committed provisional feature table, 181 rows (180 labels + Window 14)"
affects: [250-03, 250-04, 250-05, facepalm fit, FACEPALM_SCORE_MIN, D-18 refit after Phase 252]

actuals:
  tokens: 22400
  tasks: 3
  commits: 3
plan_head_before: cabd7929325fe63bd49552c15f5403bef1a3db79
plan_head_after: 519bd7102a4a74dafa421ee422b9c02df11a76e6

tech-stack:
  added: []
  patterns:
    - "Fit reproduces from a committed TSV alone (seeded folds via FIT_SEED, no cache, no DB, no Maia)"
    - "Feature rows built with the app's own functions (replay_flaw_boards, pinned_elo_for_mover, full_policy -> reply_spread, line_facts) through a read-only engine"

key-files:
  created:
    - scripts/blunder_check/facepalm_features.py
    - scripts/blunder_check/fit_facepalm.py
    - tests/scripts/test_facepalm_features.py
    - tests/scripts/test_fit_facepalm.py
    - reports/blunder-check/facepalm-features-2026-11-13.tsv
  modified: []

key-decisions:
  - "FitForm covers both Form A and Form B (widened from Form A only in Task 1 to include Form B in Task 2), so the two forms are compared by the same code path"
  - "The severity_not_a_blunder note is added in resolve_feature_row, not build_feature_row, because it depends on the resolved DB row"

patterns-established:
  - "Features TSV header equals FEATURE_COLUMNS; pv_source column records cache / cache_none / db per row for provenance"

requirements-completed: [D-01, D-02, D-03]

coverage:
  - id: C1
    description: "Features builder and IRLS fit run end to end on synthetic inputs (tracer), and the synthetic fit recovers known coefficients"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py (synthetic coefficient recovery, worst error 0.064 vs tolerance 0.07)"
        status: pass
    human_judgment: false
  - id: C2
    description: "Form A vs Form B vs loss clip comparison, precision among passers at 0.5 to 0.9, sets 1-5 train / set 6 test split, byte-identical report"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "uv run pytest tests/scripts/test_facepalm_features.py tests/scripts/test_fit_facepalm.py (31 passed)"
        status: pass
    human_judgment: false
  - id: C3
    description: "Builder is read-only against prod (make_readonly_engine; no add/commit/insert/update in the script)"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py"
        status: pass
    human_judgment: false
  - id: C4
    description: "Provisional features TSV committed with 181 data rows, header equal to FEATURE_COLUMNS, 0 cache mismatches; smoke fit exits 0"
    requirement: "D-01"
    verification:
      - kind: other
        ref: "reports/blunder-check/facepalm-features-2026-11-13.tsv: 182 lines (header + 181 rows); orchestrator run exit 0; fit_facepalm.py --features <tsv> --out temp/blunder-check/fit-smoke.md exit 0"
        status: pass
    human_judgment: false

duration: not recorded
completed: 2026-11-13
status: complete
---

# Phase 250 Plan 02: Facepalm Fit Tooling and Provisional Label Features Summary

**A numpy IRLS logistic fit with seeded CV and Form A / Form B / clip comparison, a read-only features builder, and the committed 181-row provisional label feature table it reproduces from**

## Accomplishments

- `facepalm_features.py` builds one feature row per owner label using the app's own functions (`replay_flaw_boards` for the exact pre-board, `pinned_elo_for_mover` on the pre-board mover, Maia `full_policy` on the post-blunder board fed to `reply_spread`, `line_facts` on the stored line) plus the stored `maia_played_prob`. It reads through a read-only engine; the stored line can come from the `temp/blunder-check` cache (lines as stored at label time) or the database, with an extra-rows hook used for Window 14.
- `fit_facepalm.py` fits the score by IRLS logistic regression with an intercept on the decided owner labels (0 / 1), runs seeded 10-fold CV, compares Form A (`ln(played_prob + PLAYED_PROB_OFFSET)`, reply spread, `loss_feature`) against Form B (raw played probability, reply spread, binary line-loss/mate), and compares the unclipped loss against a lower clip at 0. It reports fair / unfair counts among passers at 0.5, 0.6, 0.7, 0.8, 0.9 from out-of-fold predictions plus the sets 1-5 train / set 6 test split, and emits a constants block. It runs from a committed TSV alone.
- The orchestrator pulled the label features from prod and committed `reports/blunder-check/facepalm-features-2026-11-13.tsv` (checkpoint:human-action, Task 3).

## Task Commits

1. **Task 1: Tracer, label rows to features TSV to fitted constants block (synthetic inputs)** - `3cd202f13` (feat)
2. **Task 2: Real sources for the builder and the Form A / Form B / clip comparison** - `19e393908` (feat)
3. **Task 3: Provisional label features pulled from prod and committed** - `519bd7102` (docs)

**Plan metadata:** committed separately (docs: complete plan)

## Run Facts (Task 3, orchestrator pull)

- Exit 0. Summary line: `rows 181; pv_source: cache 168, cache_none 12, db 1; cache mismatches 0; rows with a NULL score input 37`.
- Window 14 (game 2099808 ply 23) came out `pv_source = db` with `pv_plies = 1`: `line_loss_1 = -1`, deeper depths NULL.
- Smoke fit (`fit_facepalm.py --features <tsv> --out temp/blunder-check/fit-smoke.md`) exited 0: 181 rows, 140 usable (88 fair, 52 unfair); excluded 7 undecided, 1 extra row, and 33 rows with a NULL loss feature (line too short to tell).

## Decisions Made

- `FitForm` was widened from Form A only (Task 1) to include Form B (Task 2) so both forms share one fit path.
- The `severity_not_a_blunder` note is added in `resolve_feature_row`, not `build_feature_row`.

## Deviations from Plan

None beyond the two design placements above, which stay inside the plan's file set and scope. Plan executed as written.

## Issues Encountered

None blocking. Flag for plan 04 and D-18: 33 of 181 rows (about 18%) are excluded from the fit because the stored line is too short to determine the loss feature at `LINE_DEPTH`. The provisional fit therefore rests on 140 rows; the refit after the Phase 252 line repair (D-18) should recover most of these. 37 rows carry some NULL score input, of which 33 are the short-line loss case.

## Verification

- `uv run pytest tests/scripts/test_facepalm_features.py tests/scripts/test_fit_facepalm.py -x`: 31 passed.
- `uv run ty check app/ tests/ scripts/`: all checks passed.
- Features TSV: 182 lines (header + 181 rows), header is the `FEATURE_COLUMNS` set (n, set, game_id, ply, label, pinned_elo, played_prob, reply_spread, line_loss_1/3/5/7/9, line_mate_ply, pv_source, pv_plies, note); 0 cache mismatches.

## Known Stubs

None. No TODO/FIXME/placeholder markers in the new scripts.

## Threat Flags

None. T-250-04 mitigated (read-only engine, no write calls in the builder), T-250-05 mitigated (TSV holds only game ids, plies, label numbers and numeric features), T-250-07 mitigated (seeded folds, committed TSV, byte-identical report test).

## Next Phase Readiness

- Plan 04 can run `fit_facepalm.py` against the committed TSV to produce the real report and the default `FacepalmModel` constants.
- Plan 04 and D-18 should treat the 33 short-line exclusions as a known coverage gap of the provisional features.

## Self-Check: PASSED

The TSV and the four script/test files exist, and commits `3cd202f13`, `19e393908`, `519bd7102` are ancestors of HEAD.

---
*Phase: 250-facepalm-blunder-selection*
*Completed: 2026-11-13*
