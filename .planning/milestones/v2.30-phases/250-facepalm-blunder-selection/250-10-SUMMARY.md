---
phase: 250-facepalm-blunder-selection
plan: 10
status: superseded
superseded_by: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
requirements-completed: []
---

# Phase 250 Plan 10: Superseded by Phase 254

**Plan 250-10 was not executed. Its refit and line pass are folded into Phase 254 (254-CONTEXT D-11).**

## What moved where

- **Refit on the repaired lines:** one refit in Phase 254, on the repaired lines, with the miss labels and the new
  inputs (best-line material, best-move probability, pre-blunder spread). Plans 254-11 (prod line pass, features,
  fit, owner sets `FACEPALM_SCORE_MIN`) and 254-12 (ship the constants).
- **Prod line pass after Phase 252's pv repair:** plan 254-11. It now writes both line arrays and both mate plies.
- **Score recompute and the mixed-score window (T-250-38):** no longer exist. From Phase 254 the score is computed
  at query time from stored facts (254 D-01), so there is no stored score to recompute and no window in which old
  and new scores coexist.

## Tasks

None run. No code, report or prod change was made under this plan.

## Phase 250 status

All 11 plans are closed: 250-01 to 250-09 and 250-11 executed, 250-10 superseded. 250-CONTEXT D-18 (the line-only
recompute pass and refit) is carried out by Phase 254.
