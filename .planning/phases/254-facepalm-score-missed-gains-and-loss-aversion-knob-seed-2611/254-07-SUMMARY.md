---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 07
subsystem: operator-runs
tags: [facepalm-score, maia, pre-blunder-inputs, prod-backfill, miss-labels]
requires:
  - phase: 254-06
    provides: "R1 on prod (pre-blunder columns, pre mode, miss sampler) and the prod-run worktree at 697ec5fbd"
provides:
  - "maia_best_prob and maia_pre_spread on prod for 99.2% / 99.9% of user-side blunders"
  - "50 owner miss labels (set 7) in reports/blunder-check/facepalm-labels.tsv, with a comment column"
  - "Answer to RESEARCH open question 7: the two dev example games are not on prod"
affects: [254-11]
tech-stack:
  added: []
  patterns:
    - "A stamp-checkpointed pass can be stopped with SIGTERM and relaunched with another shard count"
key-files:
  created:
    - reports/maia-flaws-backfill/prod-facepalm-pre-coverage.md
  modified:
    - reports/blunder-check/facepalm-labels.tsv
key-decisions:
  - "D-21 (owner): plan 11 does not wait for Phase 252; short lines keep NULL material, a gap-fill line pass follows the repair"
  - "D-22 (owner): one label file, reports/blunder-check/facepalm-labels.tsv (sets 1-7), replaces leg2-labels-2026-11-11.tsv and the planned miss-labels-<date>.tsv"
  - "D-23 (owner): label 1 means 'score should be above 70%' in all sets; FACEPALM_SCORE_MIN may be set lower on purpose"
  - "Leg 2 ran with 14 shards (owner request), above D-20's 8: the 252 repair was not connected to prod, connections peaked near 27 of 50"
requirements-completed: [D-08, D-14, D-15, D-16, D-20]
coverage:
  - id: D1
    description: "Dev tracer: sampler, labelled sheet, features and fit tooling chain end to end on dev"
    requirement: "D-14"
    verification:
      - kind: integration
        ref: "temp/blunder-check/dev-tracer-254-07.log (sample 8 rows set 7, features 8 rows, fit exit 2 on 8 rows as expected)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Prod pre pass complete: both legs exit 0, pre_pending_games=30, no write or score failure"
    requirement: "D-08"
    verification:
      - kind: integration
        ref: "reports/maia-flaws-backfill/prod-facepalm-pre-coverage.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "Owner labels: 50 set 7 rows, labels in {0, 0.5, 1}, no game shared with sets 1-6, parse_labels loads 230 rows"
    requirement: "D-16"
    verification:
      - kind: unit
        ref: "tests/scripts/test_facepalm_features.py::test_parse_labels_on_the_real_label_file"
        status: pass
    human_judgment: true
    rationale: "The labels are the owner's judgment"
duration: 13 h 13 min of pass run time
completed: 2026-11-15
status: complete
commits: 5
actuals:
  tasks: 3
  commits: 5
---

# Phase 254 Plan 07: Prod pre pass and owner miss labels Summary

**The pre-blunder Maia inputs are on prod for 2.3M user-side blunders (best-move probability 99.17%, pre-blunder spread 99.94%), and the owner's 50 miss labels are committed in the single label file.**

## Task 1: dev tracer (inline)

Sampler on dev: 23 candidates, 7 dropped as unstable_line, 8 rows written (set 7). Labelled copy, features TSV (8 rows, all from the DB, no NULL score input, no NULL best line). `fit_facepalm.py` exited 2 ("no candidate model could be fitted") on 8 rows, which is the expected outcome at that size. Log: `temp/blunder-check/dev-tracer-254-07.log` (gitignored).

## Task 2: blind sample and prod pre pass

- **Open question 7:** games 817357 (ply 24) and 820181 (ply 65) are not on prod; plan 11 passes no `--extra` for them.
- **Blind sample (prod):** candidates read 8,719; dropped unstable_line 2,932; stable 5,787 (loses 1,767, loses_and_misses 822, misses 1,382, neither 1,816); 50 rows written, no shortfall.
- **S1:** 10 client connections before launch. **Slice:** 50 games in 12 s, 98 blunders scored.
- **Full pass:** leg 1 with 8 shards 06:13 to 13:49 UTC (518,281 games), stopped with SIGTERM and relaunched as leg 2 with 14 shards 13:52 to 19:29 UTC (519,090 games). Both exit 0, zero write or score failures.
- **Status at 19:30Z:** `pre_stamped_games=1040211 pre_pending_games=30 user_blunders_total=2326282 user_blunders_with_best_prob=2306902 user_blunders_with_pre_spread=2324907`.
- Every launch ran from the prod-run worktree at `697ec5fbd`.
- Report and 23 shard JSONs: commit `7ad8708bb` on `main`.

## Task 3: owner labels

50 set 7 rows labelled (24 fair, 24 unfair, 2 undecided; all 10 loses-and-misses rows fair, 15 of 40 pure misses fair), 15 with a comment giving the expected score range. Commit `3ee902cad` on `main`.

## Task Commits (all on `main`)

1. `b78aa8643` docs(254): D-21
2. `bad64bbe6` chore(254): one facepalm label file (sets 1-7), drop superseded 2026-11-10 reports
3. `3ee902cad` docs(254-07): owner miss labels (set 7) with comments
4. `d66e085a1` docs(254): D-23
5. `7ad8708bb` docs(254-07): prod facepalm pre pass and coverage

## Deviations from Plan

- **Label file (D-22):** the labels live in `reports/blunder-check/facepalm-labels.tsv` with sets 1-6, not in a separate `miss-labels-<date>.tsv`; set 7 rows are numbered 191-240 and the file has a `comment` column. `DEFAULT_EXCLUDE_LABELS`, two docstrings and one test were updated for the new path.
- **Shard count:** 14 in leg 2 instead of 8 (owner request). Pace was 19 then 26 games per second, below the plan's estimate; total 13 h 13 min instead of about 9 h.
- **Order:** the blind sample was drawn hours before the pass (plan order kept), the pass started after R2 shipped, so all commits landed on `main`.
- **Task 1 ran inline** in the orchestrator.

## Issues Encountered

- 17,907 blunders have no stored best move, so `maia_best_prob` is NULL there (0.8%).
- Another session has uncommitted Phase 255 planning files in the main checkout; they were left untouched.

## Known Stubs

None.

## Threat Flags

None. T-254-19 mitigated: connections recorded before launch, the sampler ran before the pass, connections stayed at or below about 27 of 50, the 252 repair was not connected to prod.

## Next Phase Readiness

Plan 11 can start: R2 is live, the pre inputs and labels are in place. Per D-21 it runs without the Phase 252 precondition; its `--labels` argument is the single label file (D-22) and its cut tables must cover 50% to 70% (D-23).

## Self-Check: PASSED

`git log --oneline -1 -- reports/maia-flaws-backfill/prod-facepalm-pre-coverage.md` prints `7ad8708bb`; the label check printed 50 valid set 7 rows with no game overlap; `parse_labels` loads 230 rows; `git branch --show-current` prints `main`.
