---
phase: 262-facepalm-promotions-and-key-move-gate
plan: 06
subsystem: facepalm-score
tags: [facepalm, refit-checkpoint, owner-decision, prod-read-only, D-01, D-04, D-05]
requires:
  - phase: 262-03
    provides: "reports/blunder-check/facepalm-fit-2026-11-23.md (the refit and its Constants block)"
  - phase: 262-05
    provides: "refit_shift.py and caught_rate.py --rescore"
provides:
  - "Owner decision on the refit: confirm-keep-cuts"
  - "Prod checkpoint reports under reports/blunder-check/ dated 2026-11-23"
affects: [262-07]
key-files:
  created:
    - reports/blunder-check/refit-shift-2026-11-23.md
    - reports/blunder-check/blunder-check-calibration-2026-11-23.md
    - reports/blunder-check/spot-check-2026-11-23.md
    - reports/blunder-check/caught-rate-rescore-262-2026-11-23.md
    - reports/blunder-check/facepalm-explain-262.md
  modified:
    - reports/blunder-check/facepalm-fit-2026-11-23.md
key-decisions:
  - "Owner, 2026-11-23, verbatim: \"My label for row 177 was wrong. On a second look, the blunder is obvious and deserves a very high facepalm score. Capturing with Nxd5 is a check, which makes all the difference. I believe the changes are conceptually sound. confirm-keep-cuts\""
  - "FACEPALM_SCORE_MIN 0.70, FACEPALM_STATS_MIN 0.70 and HARD_TO_CATCH_SCORE_BELOW 0.5 stay as they are; no frontend cutoff change in plan 07"
  - "The constants to paste in plan 07 are the Constants block of facepalm-fit-2026-11-23.md, as printed"
requirements-completed: [D-01, D-04, D-05]
completed: 2026-11-23
status: complete
actuals:
  tasks: 3
---

# Phase 262 Plan 06: Prod facts and owner decision Summary

The owner confirmed the refitted model (promotions as material, key-move gate on the type rule) and kept all three cuts.

## Decision (Task 3)

- **Option:** `confirm-keep-cuts` (owner's words are quoted in the frontmatter).
- **Cuts:** FACEPALM_SCORE_MIN 0.70, FACEPALM_STATS_MIN 0.70, HARD_TO_CATCH_SCORE_BELOW 0.5, all unchanged.
- **Fit report:** reports/blunder-check/facepalm-fit-2026-11-23.md. Constants: intercept -1.7891, played -0.6193, loss 0.8879, missed 0.3993, best_prob 1.1635, reply_prob 0.8057.
- **AUC range check:** |AUC(chosen) - AUC(shipped_baseline)| = 0.019 against 0.02, inside the range at the edge; shown as a range check, not a selector.
- **D-05 old-gate line:** CV AUC 0.902 and 99 fair / 12 unfair at 0.70 out of fold, against 0.889 and 94 / 11 for the chosen gate.
- **D-04 unscored rows:** 161 prod rows lose the score they have today (stored pair; CONTEXT expected about 1,600). Accepted.
- **EXPLAIN:** both reader statements of user 95 are index-only on ix_game_flaws_facepalm_inputs under the new gate.

## Task 1: dev chain (orchestrator, inline)

Run from the main checkout with the candidate constants in the working tree only, then restored.

| Step | Command | Exit |
|---|---|---|
| 2 | blunder_check_calibration.py --db dev --sample-permille 1000 --limit-games 200 | 0 |
| 3 | refit_shift.py --db dev --mod 1 | 0 |
| 4 | caught_rate.py --db dev --rescore | 0 |
| 5 | temp/facepalm-262/gen_explain_sql.py --db dev --user-id 28 | 0 (second run) |

Both statements on dev read game_flaws through `Index Only Scan using ix_game_flaws_facepalm_inputs`. On dev the gate alone moves passers at 0.70 from 6,781 to 6,480; gate plus refitted coefficients gives 5,929 (58 enter, 910 leave). Dev shows no promotion effect because the plan 04 rehearsal already applied the rule there.

## Task 2: prod reads (orchestrator)

All read-only, one connection at a time. Calibration log ended with EXIT=0; refit_shift, both caught_rate runs and the EXPLAIN exited 0. The figures are in the "Prod facts at the 262 checkpoint" section appended to the fit report. Reports committed as 4ee05e228. `git diff --quiet -- app/services/blunder_check_rules.py` exits 0.

Headline prod numbers (10% game sample, 472,589 blunders): passers at 0.70 go from 154,205 to 140,082 (-9.2%), 3,835 enter and 17,958 leave; own blunders at 0.70 go from 77,680 to 70,491; 12,737 sampled rows change inputs with the promotion rule (about 127,000 on all prod).

## Deviations from Plan

- **Precondition not met, owner decided.** `repair_short_lines.py feed --db prod` (another session, running since 2026-11-21) was active. The owner chose to run the read-only reads alongside it. Stored lines were moving during the reads, so the prod counts are a snapshot.
- **Task 1 ran inline.** The orchestrator ran the dev chain itself instead of dispatching an executor, since tasks 2 and 3 are orchestrator work on the same working tree.
- **EXPLAIN helper bug fixed.** The first dev run of gen_explain_sql.py failed: literal-bind compilation doubles a percent sign. Fixed in the helper (gitignored) and re-run.
- **Calibration launch.** Run as a harness background task writing temp/facepalm-262/calibration-prod.log instead of setsid nohup; same log and EXIT marker.
- **EXPLAIN report is a summary.** facepalm-explain-262.md records statement shapes, timings and scan nodes, not the full plan text, which carries one account's game id list.
- **Not re-scored:** window 14 and the two owner fixtures under the candidate; the research preview (0.162, 0.130, 0.218, all below 0.70) was shown to the owner as such.

## Notes for plan 07

- Paste the Constants block of facepalm-fit-2026-11-23.md as printed; the three cuts and the frontend FACEPALM_HIGH_CUTOFF do not change.
- **Label 177 (follow-up, not applied).** The owner says the "unfair" label of row 177 was wrong. The label file is unchanged, because correcting it changes the fit and the confirmed constants are the ones fitted on the labels as they are. Correct it at the next refit.
- The prod promotion pass must not run alongside another operator job; the line-repair feed was still running at the checkpoint.

## Self-Check: PASSED
