---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
review: 254-REVIEW.md
updated: 2026-11-16
findings: 6
fixed: 0
open: 6
---

# Phase 254 Review Disposition

| ID | Severity | Finding | Disposition | Evidence |
|----|----------|---------|-------------|----------|
| WR-01 | warning | A NULL `maia_best_prob` adds 0 to the best-move term, which reads as the easiest possible best move | open | Prod 2026-11-16: 14,826 of 2,178,931 rows with scoring inputs (0.68%) have a NULL best prob, 14,592 of them also lack a best line. A fix changes the live model, so it goes to the follow-up refit (SEED-261115-agg) |
| WR-02 | warning | Drop and R1 migrations take ACCESS EXCLUSIVE on `game_flaws` with no `lock_timeout` | open | Both migrations already ran on prod without a stall (R1 2026-11-15, drop 2026-11-16T05:56Z); nothing left to protect |
| WR-03 | warning | The fit drops rows with a NULL `reply_spread` although gated spread forms never read it on no-loss rows | open | Affects the fit script only; goes to the follow-up refit (SEED-261115-agg) |
| IN-01 | info | Stale comments in `game.py`, `facepalm_features.py`, `backfill_maia_flaws.py`; feature builder should call `pre_blunder_spread` | open | |
| IN-02 | info | The two shape CHECK constraints stay NOT VALID | open | |
| IN-03 | info | `_loss_at_depth` settles on an opponent mate for the played line too, a rare exception to the Phase 250 reproduction | open | |

No critical finding. The reviewer compared the SQL and Python twins on 55,800 random cases (36 model shapes,
lambda 0 / 0.5 / 1, NULLs in every input) with zero mismatches.
