---
phase: 263-foreign-blunder-fillers
source: 263-REVIEW.md
recorded: 2026-11-23
---

# Phase 263: Code Review Disposition

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

| ID | Severity | Disposition | Source |
|---|---|---|---|
| WR-01 | warning | fixed | D-16 sharp guarantee lost when the sharp pick came from the nearest draw step. Fixed in 148d00b41 at the shortfall trim; test `test_first_ever_session_keeps_sharp_pick_from_nearest_step` fails with the fix disabled. |
| WR-02 | warning | fixed | Foreign reveal sent the stranger's `played_at` to the second. Fixed in 101afecb1: UTC midnight of the game date, wire type unchanged; test `test_reveal_foreign_played_at_is_date_only` fails with the truncation reverted. |
| WR-03 | warning | accepted | Score bubble for `own_puzzle_count === 0` tells an established user on an exhausted day that their games are not analyzed yet, against the D-13 start sentence. Owner accepted the wording as is on 2026-11-24 (263-UAT.md test 2). |
| WR-04 | warning | fixed | Stale "tactics puzzles don't count here" on the Accuracy board. Fixed in 903d6ccec; new copy for owner sign-off in 263-HUMAN-UAT.md item 12. |
| IN-01 | info | open | The owner-keyed source set is defined three times. |
| IN-02 | info | fixed | Dead argument of `_classify_legacy_filler_solve` removed in 4f37aab7c. |
| IN-03 | info | fixed | `ForeignCandidate` platform and bucket typed with `Platform` / `TimeControlBucket` in 247d5d729. |
| IN-04 | info | open | Names and comments left over from the filler era (`non_filler_*`). |
| IN-05 | info | open | No-repeat is per position, not per game (D-17 as written is honoured); the opponent's copy of the solver's own game can be drawn (blunder check has the same property). |
| IN-06 | info | open | The nav badge counts unservable legacy or deleted-foreign rows until Train is next opened. |
| IN-07 | info | fixed | The level-2600 isolation did not cover the nearest step. Fixed in 7cc821bbd: band-only fixture `real_foreign_band_draw` for the exact-count foreign tests; a leaked raw-1500 game made the old fixture fail (`assert 2 == 1`). |

Security audit follow-up: the T-263-18 test gap was closed in b9c05a272 (the test now fails when the `not foreign` gate is removed), and the comments that described the library endpoints as owner-scoped were corrected.
