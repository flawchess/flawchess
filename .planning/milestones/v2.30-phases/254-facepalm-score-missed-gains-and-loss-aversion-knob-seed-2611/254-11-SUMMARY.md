---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 11
subsystem: operator-runs
tags: [facepalm-score, refit, prod-line-pass, calibration, owner-decision]
requires:
  - phase: 254-07
    provides: "Pre-blunder inputs on prod, 50 miss labels (set 7) in the single label file"
  - phase: 254-10
    provides: "R2 live: readers on the query-time expression"
provides:
  - "Both line arrays and both mate plies on prod recomputed from the stored lines (cutoff 2026-11-15T19:34:08+00:00)"
  - "Refit on 199 usable labels: reports/blunder-check/facepalm-fit-2026-11-15.md and its features TSV"
  - "Prod calibration and spot check under the candidate constants (2026-11-15)"
  - "Owner decision: FACEPALM_SCORE_MIN = 0.50, fitted forms confirmed"
affects: [254-12, 254-13, 254-14]
tech-stack:
  added: []
  patterns: []
key-files:
  created:
    - reports/maia-flaws-backfill/prod-facepalm-line-pass-254.md
    - reports/blunder-check/facepalm-features-2026-11-15.tsv
    - reports/blunder-check/facepalm-fit-2026-11-15.md
    - reports/blunder-check/blunder-check-calibration-2026-11-15.md
    - reports/blunder-check/spot-check-2026-11-15.md
  modified: []
key-decisions:
  - "D-21 (owner): the Phase 252 precondition was waived; the pass and the fit ran on the lines as stored, a gap-fill line pass follows the repair"
  - "Owner, 2026-11-15: FACEPALM_SCORE_MIN = 0.50 (below the labels' 70% meaning on purpose, D-23), forms confirmed: split material, missed floor none, cap 5, spread best_prob_for_misses, best_prob in, pre_spread out"
  - "The refit cycle branch lives in a separate worktree (.claude/worktrees/phase-254-refit), not the main checkout, because another session works there on Phase 255"
requirements-completed: [D-06, D-07, D-08, D-09, D-11, D-13, D-16]
duration: 2 h 15 min
completed: 2026-11-15
status: complete
commits: 2
actuals:
  tasks: 3
  commits: 2
---

# Phase 254 Plan 11: Prod line pass, refit and the owner's cut Summary

**The line facts on prod are recomputed (83.9% of user-side blunders scoreable), the score is refitted on 199 labels (CV AUC 0.874), and the owner chose FACEPALM_SCORE_MIN = 0.50 with the fitted forms. The missed gain's size earned almost no weight (coefficient 0.0891); the best-move probability carries the misses.**

## Task 1: dev rehearsal (inline)

- `--check-constants` on `facepalm-features-2026-11-13.tsv`: "constants match", exit 0.
- Dev line pass, cutoff `2026-11-15T19:33:21+00:00`, user 28: `games_selected=2880 ... scores_set=4557 scores_null=839`, exit 0; second run `games_selected=0`; status `line_done_since_cutoff=2880 line_pending_games=0 user_blunders_total=5396 user_blunders_with_score=4557 user_blunders_qualifying=1228`.
- Dev features for 817357:24 and 820181:65: both rows carry `best_mat_3` (3 and 10) and `best_prob` (0.206584 and 0.209111).

## Task 2: prod line pass

Precondition waived (D-21); `252-06-SUMMARY.md` does not exist. Prod-run worktree re-pointed to `origin/production` at `130978073` (contains R2 via `9c22730c6`; the ancestor check on the squash SHA does not apply under squash releases). Connections before launch: 12 of 50. Cutoff `2026-11-15T19:34:08+00:00`. Slice 50 games in about 1 s. Full pass with 4 shards, 19:35:43 to 20:46:00 UTC, exit 0:

```
total: games_selected=1039785 games_scored=1039785 games_stamped=1039780 games_already_stamped=2 games_fingerprint_changed=3 games_missing=0 games_write_failed=0 games_score_failed=0 flaws_scored=0 flaws_null=0 spreads_scored=0 spreads_null=0 scores_set=1950592 scores_null=375215 pre_scored=0 pre_null=0 reason_invalid_root=17 reason_ply_beyond_mainline=11
```

Status after: `line_done_since_cutoff=1040264 line_pending_games=3 user_blunders_total=2326913 user_blunders_with_score=1951340 user_blunders_qualifying=627406` (pre-refit constants, cut 0.70).

Coverage of 2,326,929 user-side blunders: played line reaches depth 3 for 83.9% (mate within 3 for 3.2%, unknown 16.1%); best line reaches depth 3 for 78.7% (mate within 3 for 1.2%, unknown 21.3%, missed term 0 per D-18). Report commit `ffd675bf3`. The prod-run worktree was removed afterwards.

## Task 3: refit and decision

- Features from prod, one `--labels` file (D-22) plus `--extra 2099808:23`: 231 rows; `pv_source: db 219, db_none 12`; 26 rows with a NULL score input, 32 with a NULL best line.
- Fit: 199 usable rows (117 fair, 82 unfair); excluded 9 undecided, 1 extra, 22 with a line too short. 45 of 230 label rows have a NULL best line.
- Chosen model (report `## Constants`): intercept -0.7583, played -0.4146, spread -0.2585, loss 1.0129, missed 0.0891, best_prob 1.0405, pre_spread 0. Forms: split, missed floor none, cap 5, missed mate 5, spread `best_prob_for_misses`.
- CV AUC 0.874 (5 seeds: mean 0.874, spread 0.004); in sample 0.896; the old shape on the same rows 0.852. Set 6 as holdout: AUC 0.901.
- Fair / unfair among passers (out of fold), all rows: 98 / 21 at 0.50, 89 / 14 at 0.60, 81 / 9 at 0.70, 69 / 7 at 0.80. Pure misses: 12 / 6, 6 / 3, 2 / 1, 1 / 1.
- Prod calibration (25 permille, 58,616 user blunders) with the candidate constants: pass share at 0.50 / 0.60 / 0.70 / 0.80 is 88.5 / 80.8 / 72.3 / 61.7% for loses, 26.6 / 16.5 / 7.4 / 1.1% for misses, 91.5 / 86.1 / 78.1 / 67.6% for loses_and_misses, 8.6 / 3.7 / 0.8 / 0.0% for neither. Qualifying of scored at 0.50: 47.7%. Own pool, median usable windows per user: 507.5 at 0.50, 367.5 at 0.70. Foreign pool at 0.50: 16,600 to 206,720 qualifying blunders per level.
- **Window 14 (2099808:23): not scored** (its stored line is too short: `line_loss_3 None`), so it cannot qualify at any cut; "below the cut" can only be checked after the 252 repair.
- **Owner fixtures: 817357:24 and 820181:65 score 0.15 each** under the candidate model (0.02 before), below the chosen cut. Plan 12's must-have "owner fixtures score at or above FACEPALM_SCORE_MIN" cannot hold with this fit; the owner confirmed the forms with these numbers shown.
- The 15 commented set 7 rows: 6 meet the owner's expected range in sample (rows 216, 223, 224, 228, 233, 240); most others moved toward it.
- Reports commit `61d6fe4f6`.

## Decision (owner, 2026-11-15)

`FACEPALM_SCORE_MIN=0.50, forms confirmed`. Lambda stays 1.0 for both consumers.

## Deviations from Plan

- Phase 252 precondition waived (D-21); no repair status quoted.
- One label file (D-22) instead of two `--labels` arguments.
- Refit branch in a separate worktree, not the main checkout (shared-checkout race with the Phase 255 session).
- Tasks 1 to 3 ran inline in the orchestrator.
- The calibration took 29 minutes, not 15 (CPU shared with a Phase 252 benchmark repair).
- Plan criterion "the chosen cut is above Window 14's candidate score" is not checkable: Window 14 is unscored.

## Issues Encountered

- Missed-gain size barely separates the owner's labels among pure misses (fair share about 30% at every size except mates); see the fit report. A better input for misses is a candidate for a later phase.

## Known Stubs

None.

## Threat Flags

T-254-32 (refit on lines Phase 252 still changes) is accepted by the owner (D-21), not mitigated. T-254-31 and T-254-33 mitigated as planned (4 shards, read-only features and calibration).

## Next Phase Readiness

Plan 12 pastes the `## Constants` block of `reports/blunder-check/facepalm-fit-2026-11-15.md` and sets FACEPALM_SCORE_MIN = 0.50. Its owner-fixture and Window 14 tests must record the facts above (fixtures at 0.15 below the cut; Window 14 unscored) instead of the planned assertions.

## Self-Check: PASSED

`git log --oneline -2` on the refit branch shows `61d6fe4f6` and `ffd675bf3`; the four reports and the features TSV are tracked; `git status --porcelain` was clean before this SUMMARY.
