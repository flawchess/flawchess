---
phase: 259-facepalm-first-principles-refit
plan: 02
subsystem: tooling
tags: [facepalm, features-tsv, review-report, quiet-point, offline]

requires:
  - phase: 259-01
    provides: "facepalm_material_inputs, material_inputs_from_facts, quiet_line_facts, quiet_best_line_facts, _quiet_walk_end"
provides:
  - "features TSV with ten appended columns: reply_uci, reply_prob, loss, missed, loss_shipped, missed_shipped, pre_fen, played_uci, played_line, best_line"
  - "--skip-missing flag on the features pull"
  - "scripts/blunder_check/quiet_rule_review.py: offline D-09 review report grouped by cause"
affects: [259-03, 259-07, 259-09, 259-11, fit]

actuals:
  tokens: 10800
  tasks: 2
  commits: 2
plan_head_before: baf88638a82b46805743a63cf725aec8eb1a0760
plan_head_after: 34f0aceb556f02f4260dda7d72bcbf6500080cad
commits: 2

tech-stack:
  added: []
  patterns:
    - "append-only TSV columns so the current fit loader (schema picked by column name) keeps working"
    - "review classifies with the app's own private walk helpers (imported with noqa PLC2701), never a copy"

key-files:
  created:
    - scripts/blunder_check/quiet_rule_review.py
    - tests/scripts/test_quiet_rule_review.py
  modified:
    - scripts/blunder_check/facepalm_features.py
    - tests/scripts/test_facepalm_features.py

key-decisions:
  - "FEATURE_COLUMNS is now (*FACTS_FEATURE_COLUMNS, *QUIET_FEATURE_COLUMNS); the facts tuple keeps the old content so load_features is untouched"
  - "The review's drift check rounds the recomputed value to the TSV's 6 significant digits before comparing against REVIEW_EPSILON (1e-6); the raw comparison would flag every cell above ~1 because of the write-time rounding"
  - "No reply_missing note when the rating is unknown or the policy is unavailable: those rows keep their own note (rating_unknown, no_policy)"

patterns-established:
  - "Offline review tools read a committed TSV and import no database or Maia code (acceptance grep)"

requirements-completed: [D-07, D-09, D-12, D-13]

coverage:
  - id: D1
    description: "Features TSV carries reply_uci / reply_prob from the same post-blunder policy call as reply_spread (D-07), with the reply_missing note"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py#test_reply_prob_is_the_policy_of_the_first_refutation_token"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py#test_reply_prob_comes_from_the_spread_call"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py#test_reply_missing_note_without_a_refutation_line"
        status: pass
    human_judgment: false
  - id: D2
    description: "Features TSV carries quiet loss/missed (facepalm_material_inputs), shipped loss/missed and the raw pre_fen/played_uci/played_line/best_line (D-12), appended so the current fit tool still loads it as schema facts"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py#test_quiet_and_shipped_material_columns_match_the_app"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py#test_quiet_and_shipped_columns_are_not_swapped_on_changed_positions"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py#test_current_fit_tool_loads_the_extended_table"
        status: pass
    human_judgment: false
  - id: D3
    description: "--skip-missing lists missing label rows and exits 0; without it the exit code stays 5"
    verification:
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py#test_cli_skip_missing_exits_0_and_lists_rows"
        status: pass
    human_judgment: false
  - id: D4
    description: "Offline review report: counts by cause x line x depth, moved rows, reply coverage, about 10 before/after examples with analysis links, always the D-13 row and fixtures 153/154/156/170, byte-identical across runs"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "tests/scripts/test_quiet_rule_review.py#test_d13_row_end_to_end"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_quiet_rule_review.py#test_changed_fixtures_are_classified"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_quiet_rule_review.py#test_report_is_deterministic"
        status: pass
    human_judgment: true
    rationale: "Whether the cause taxonomy and the example selection read well to the owner is a judgement; plan 03 puts the prod report in front of the owner"

duration: 35min
completed: 2026-11-21
status: complete
---

# Phase 259 Plan 02: Features pull and quiet-rule review Summary

**Features TSV extended with reply probability, quiet and shipped loss/missed and the raw lines, plus an offline review tool that classifies every value the quiet rule changes by cause.**

## Performance

- **Duration:** about 35 min
- **Completed:** 2026-11-21T16:23Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `facepalm_features.py` appends `QUIET_FEATURE_COLUMNS` (ten columns) after `note`; `_spread_for` returns `(spread, reply_prob, note)` from the one post-blunder policy call; `build_feature_row` fills `quiet` (via `facepalm_material_inputs`), `shipped` (via `material_inputs_from_facts` on the old-rule facts), and the raw inputs. `--skip-missing` lists missing rows (`missing: 4, 9`) and exits 0.
- `quiet_rule_review.py` (`classify_change`, `review_rows`, `render_review`, `main`): rebuilds each row's board from `pre_fen`, compares shipped vs quiet at every odd depth of both lines, classifies each change with the app's `_quiet_walk_end`, and writes a deterministic markdown report. Exit 2 when the TSV has no `pre_fen`.
- D-13 row pinned end to end: best line depth-1 material `9 -> 0` with cause `longer_exchange_settled`, missed `2.581 -> 0.000`.

## Dev run (Task 1 acceptance record)

The dev database has the D-13 row. Real Maia on dev:

```
uv run --group maia-inference python scripts/blunder_check/facepalm_features.py --db dev --extra 2883555:47 --out temp/blunder-check/features-dev-259-02.tsv
  rows 1; pv_source: db 1; cache mismatches 0; rows with a NULL score input 0; rows with a NULL best line 0
uv run python scripts/blunder_check/quiet_rule_review.py --features temp/blunder-check/features-dev-259-02.tsv --out temp/blunder-check/quiet-review-dev-259-02.md
```

Report: 1 row, 1 changed value (best line, depth 1, `longer_exchange_settled`), drift 0, reply_prob 0.200, loss 2.935 -> 2.935, missed 2.581 -> 0.000. Both files are gitignored (`temp/`).

## Task Commits

1. **Task 1: Tracer, D-13 row from features row through the TSV into the review** - `8d8dc6641` (feat)
2. **Task 2: Columns and classification pinned by tests** - `34f0aceb5` (test)

Tracer gate: `<verify>` is automated only and human_verify_mode is end-of-phase, so the tracer was re-run (passed, 1 test) and expansion continued.

## Files Created/Modified

- `scripts/blunder_check/facepalm_features.py` - appended columns, reply probability, quiet/shipped inputs, `--skip-missing`
- `scripts/blunder_check/quiet_rule_review.py` - D-09 offline review (new)
- `tests/scripts/test_facepalm_features.py` - column, reply, skip-missing and fit-loader tests
- `tests/scripts/test_quiet_rule_review.py` - tracer, cause, determinism, drift and no-DB tests (new)

## Decisions Made

See key-decisions above. The drift comparison is the only place the plan's literal text (`REVIEW_EPSILON = 1e-6`) needed interpretation: cells carry 6 significant digits, so the recomputed value is rounded the same way first. `FEATURE_CELL_DIGITS` mirrors `facepalm_features.FLOAT_SIGNIFICANT_DIGITS` (a test pins them equal) because importing the features module would pull database and Maia code into the offline tool.

## Deviations from Plan

None - plan executed exactly as written. (Verification note: mutating the quiet/shipped column order and the `--skip-missing` gate each made a test fail; the first mutation was only caught after adding `test_quiet_and_shipped_columns_are_not_swapped_on_changed_positions`, because the seed line has loss equal under both rules.)

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. The review imports no database or Maia code (acceptance grep 0, plus `test_review_imports_no_database_or_maia_code`); the features builder keeps `test_builder_has_no_write_path`; the report carries game ids, plies and links only.

## Verification

- `uv run pytest tests/scripts/test_facepalm_features.py tests/scripts/test_quiet_rule_review.py` : 42 passed
- `uv run pytest -n auto tests/scripts/test_fit_facepalm.py` : 70 passed (appended columns do not break the current fit loader)
- `uv run ty check app/ tests/ scripts/`, `ruff check`, `ruff format --check`, `check_function_size.py app/ --fail-over-depth 4`: all clean

## Next Phase Readiness

Plan 03 can run the read-only prod pull with `--skip-missing` (orchestrator, prod access), then the offline review on the resulting TSV. The new TSV is the shared input for the fit plans (07, 09, 11).

## Self-Check: PASSED

- FOUND: scripts/blunder_check/quiet_rule_review.py, tests/scripts/test_quiet_rule_review.py
- FOUND commits: 8d8dc6641, 34f0aceb5 (ancestors of HEAD)

---
*Phase: 259-facepalm-first-principles-refit*
*Completed: 2026-11-21*
