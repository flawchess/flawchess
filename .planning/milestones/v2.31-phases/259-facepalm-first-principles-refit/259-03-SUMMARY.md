---
phase: 259-facepalm-first-principles-refit
plan: 03
subsystem: tooling
tags: [facepalm, quiet-point, owner-checkpoint, prod-read, review-report]

requires:
  - phase: 259-02
    provides: "extended features pull (--skip-missing, quiet and shipped columns, reply_prob) and the offline quiet_rule_review.py"
provides:
  - "reports/blunder-check/facepalm-features-2026-11-21.tsv: the D-09 prod pull, first table in the extended schema (291 rows)"
  - "reports/blunder-check/quiet-rule-review-2026-11-21.md: cause breakdown of every value the quiet rule changes"
  - "Owner decision D-09: confirm-retire (rule confirmed, old fit runs' reproducibility retired)"
affects: [259-04, 259-07, 259-09, 259-11]

actuals:
  tasks: 3
  commits: 1
commits: 1

key-files:
  created:
    - reports/blunder-check/facepalm-features-2026-11-21.tsv
    - reports/blunder-check/quiet-rule-review-2026-11-21.md
  modified: []

key-decisions:
  - "D-09 owner decision, 2026-11-21: \"confirm-retire\" (Rule confirmed; retire the old fit runs' reproducibility). Plans 04 onward build the recompute; plan 07 Task 3 builds no frozen legacy copy."
  - "Open question 5: operator runs stay strictly one at a time (plan default kept). The Task 2 pull ran beside the Phase 252 feeder as a one-off exception the owner approved."
---

# Phase 259 Plan 03: D-09 Owner Checkpoint Summary

**The owner confirmed the quiet-point rule on today's prod lines (option "confirm-retire"): 322 changed depth values, all from the two exchange causes, zero drift, and the D-13 row fixed.**

## Performance

- **Executed by:** the orchestrator inline (the plan's dispatch override gives Tasks 2 and 3 to the orchestrator; Task 1 is two dev commands)
- **Completed:** 2026-11-21
- **Tasks:** 3/3
- **Commits:** 1 (`af05ad613`)

## Task 1: dev rehearsal (nothing committed)

- Features pull on dev with `--labels`, both `--extra` rows and `--skip-missing`: exit 0.
  Summary line: `rows 3; pv_source: db 3; cache mismatches 0; rows with a NULL score input 0; rows with a NULL best line 0`.
  Missing: nearly all label rows (dev holds only a handful of the label games), listed by number in the run output.
- Review on the dev table: 3 rows, 2 rows with a changed value, 3 changed values (played 1, best 2), all `longer_exchange_settled`, drift 0.
- Outputs in gitignored `temp/blunder-check/features-dev-259-03.tsv` and `temp/blunder-check/quiet-review-dev-259-03.md`.

## Task 2: prod pull (read-only) and review

- Operator check: the Phase 252 feeder (`scripts/repair_short_lines.py feed --db prod`) was running (6.5 h). The plan says wait; the owner chose to run the read-only pull alongside it (one connection, a few minutes).
- Pull summary line: `rows 291; pv_source: db 280, db_none 11; cache mismatches 0; rows with a NULL score input 11; rows with a NULL best line 5`.
- Missing rows: `10` (one label game gone, as RESEARCH expected).
- Review totals: 194 of 291 rows have a changed value; changed values played line 143, best line 179; drift 0.
- Causes: `longer_exchange_settled` 279, `exchange_settled_at_end` 43, `later_capture_pulled_earlier` 0, `other` 0.
- Rows whose loss or missed moved: 162 of 291.
- Reply probability known for 280 of 291; quartiles 0.179 / 0.529 / 0.741.
- D-13 row (game 2883555 ply 47): `loss` 2.93548, `missed` 0, `loss_shipped` 2.93548, `missed_shipped` 2.58065, `reply_prob` 0.199631.
- Labels 153, 154, 156 and 170 are present in the report's examples.
- Both files committed on `gsd/phase-259-facepalm-first-principles-refit` as `af05ad613` (`docs(259-03): D-09 quiet rule review on prod lines`); branch unchanged before and after.

Orchestrator's own cut of the TSV by label (not part of the report): label 0 (n 129) mean change in missed -0.31 and in loss +0.07; label 1 (n 139) mean change in missed -0.21 and in loss +0.18. Loss rises by more than 0.5 on 19 label-1 rows and 8 label-0 rows.

## Task 3: owner decision (D-09 and open question 6)

- **Chosen option, verbatim:** "confirm-retire" (Rule confirmed; retire the old fit runs' reproducibility).
- **Date:** 2026-11-21.
- **Consequence:** the D-02 quiet rule stands as built in plans 01 and 02. The 2026-11-13/15/16 fit runs are no longer reproducible by command after the switch; the committed reports and TSVs stay as history. No `scripts/blunder_check/legacy/` copy.
- **Open question 5:** operator runs strictly one at a time (default kept).

## Task Commits

1. **Task 2: prod TSV and review** - `af05ad613` (docs)

## Deviations from Plan

- Task 2 step 1 (no other operator process) was not met: the Phase 252 feeder was running. The owner approved running the read-only pull beside it instead of waiting. A label row whose short line the feeder repaired mid-pull is read in whichever state it was in; the review's drift count is 0.
- Task 1 ran inline in the orchestrator rather than in an executor (two commands, nothing to commit).

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. T-259-05: one read-only connection, run beside one feeder with owner approval. T-259-06: the decision is recorded above before plan 04 starts.

## Verification

- `grep -c "longer_exchange_settled\|exchange_settled_at_end\|later_capture_pulled_earlier" reports/blunder-check/quiet-rule-review-*.md` prints 18.
- `git log --name-only -1 -- reports/blunder-check/` lists both new files on the phase branch.

## Next Phase Readiness

Plan 04's precondition holds: this SUMMARY records option "confirm-retire".

## Self-Check: PASSED
