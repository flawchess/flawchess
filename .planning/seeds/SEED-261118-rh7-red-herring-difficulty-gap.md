---
id: SEED-261118-rh7
status: dormant
planted: 2026-11-18
planted_during: phase 251 planning (tester feedback on blunder check and personalized puzzles)
trigger_when: more tester feedback that red herrings feel too easy, or when the herring pool / herring serve order is next touched
scope: small for the serve-time filter (one constant); medium if herrings are regenerated for "tempting bad move" positions
---

# SEED-261118-rh7: Red herrings are easier than own blunders

## Why This Matters

A blunder-check tester wrote (2026-11-18): "in the regular puzzles it's quite crazy the difference
between being confronted with my own dead angles and red herrings, I can basically tell in a few
seconds if something is a red herring because it just feels too easy most of the time".

If herrings are recognisable as herrings, the "critical / several fine moves" guess in personalized
puzzles stops testing judgment, and the herring slots become free points.

## Status (owner, 2026-11-18)

No change decided. The owner is not sure anything needs to change; this seed records the evidence so
the question can be revisited.

## Evidence (prod, 2026-11-18, all solved `drill_solves` since 2026-07-25)

About 17,800 solves from roughly 250 users. The fair comparison is a herring against an own blunder
whose correct guess is also "several", on first exposure (herrings never repeat). The correct guess
was derived as `guess` when `correct_guess`, else the other value. First exposure = first solve per
`(user_id, game_id, ply, source)`.

### All users

| Puzzle | n | Guess correct | Good move played | Median guess time | Guess under 10 s |
|---|---|---|---|---|---|
| Red herring | 3,837 | 85.4% | 81.3% | 27.2 s | 8.7% |
| Own blunder, "several", first time | 3,212 | 68.4% | 55.2% | 32.1 s | 9.5% |
| Own blunder, "critical", first time | 2,007 | 63.4% | 55.4% | 25.0 s | 13.9% |
| Own blunder, "several", repeat | 5,280 | 77.7% | 70.9% | 22.0 s | 19.8% |
| Own blunder, "critical", repeat | 3,461 | 71.3% | 76.1% | 15.9 s | 31.3% |

### User 2

| Puzzle | n | Guess correct | Good move played | Median guess time | Guess under 10 s |
|---|---|---|---|---|---|
| Red herring | 35 | 88.6% | 82.9% | 30.8 s | 0% |
| Own blunder, "several", first time | 38 | 76.3% | 50.0% | 31.4 s | 9.1% |
| Own blunder, "critical", first time | 24 | 50.0% | 41.7% | 42.3 s | 4.8% |

Reading:

- Herrings are easier: 17 points on the guess and 26 points on move quality, against comparable
  own blunders. User 2 shows the same direction (the guess gap is within noise at n=35, the move
  gap is not: 29 of 35 against 19 of 38).
- Herrings are not answered faster. "I can tell in a few seconds" is not visible in guess times
  (guess time includes choosing the move to play, so quick recognition is still possible).

### Number of fine moves explains much of it

A move is "fine" when it is less than `INACCURACY_DROP` (0.05 expected score) below the best move of
the stored MultiPV-5 ladder, the same rule `herring_stmt` uses.

Served herrings (2,413 solves that link to a pool row):

| Fine moves in top 5 | Share of served | Guess correct | Good move played | Median guess time |
|---|---|---|---|---|
| 3 | 29% | 73.5% | 67.9% | 30.4 s |
| 4 | 18% | 84.4% | 80.3% | 27.7 s |
| 5 | 53% | 88.2% | 83.9% | 27.3 s |

By phase: opening 89.8% guess correct (n=324), middlegame 91.0% (n=1,006), endgame 74.3% (n=1,083).

Pool composition (`herring_pool`, 4,999 rows, 3,550 pass the serve-time gates of `herring_stmt`):

| Fine moves in top 5 | Servable rows | Share | Opening | Middlegame | Endgame |
|---|---|---|---|---|---|
| 2 | 911 | 25.7% | 268 | 299 | 344 |
| 3 | 633 | 17.8% | 201 | 215 | 217 |
| 4 | 499 | 14.1% | 143 | 175 | 181 |
| 5 | 1,507 | 42.5% | 569 | 495 | 443 |

- Two-move herrings have never been served: the serve order prefers three or more
  (`HERRING_PREFERRED_QUALIFYING_MOVES`) and no user has exhausted those. Their difficulty is
  unmeasured.
- Five-move rows already exclude positions whose fifth move is within 0.02 of the best
  (`HERRING_DEGENERATE_MIN_GAP_ES`), so their fifth move is 0.02 to 0.05 behind. Only the top 5 are
  searched and stored, so many of these positions likely have more than five fine moves.

### Served share

Configured `HERRING_SHARE = 0.25`. Of solved puzzles: own blunders 75.1% (13,960), herrings 20.6%
(3,837), sharp fillers 4.3% (802). These are solved, not composed, puzzles.

## Why herrings are easier (interpretation)

- Selection on outcome: an own blunder is a position where a human went wrong, so it contains a
  tempting bad move. A herring is a sampled position with several fine moves and no such trap.
- More than half of the served herrings have all five top moves fine.

## Options

1. **Exclude herrings with five fine moves** (owner's idea, 2026-11-18). One constant in the
   `herring_stmt` filter, no re-analysis (the ladder is stored raw). Leaves 2,043 servable rows,
   1,132 of them in the preferred 3 to 4 group, phases still balanced. At two herrings per session
   that is over 500 sessions per user before two-move herrings appear. Expected herring results
   with only 3 and 4 served: about 78% guess correct and 73% good moves (from 85% and 81%). This
   narrows the gap to own blunders (68% and 55%) but does not close it.
2. **Also prefer three over four** in the serve order (73.5% against 84.4% guess correct).
3. **Select herrings for a tempting bad move** (a move Maia finds plausible that loses). Needs new
   generation work.
4. **Leave it.** Herrings partly exist as a breather and a calibration of "not everything is
   critical"; an easier herring may be acceptable.

## Open questions

- How many fine moves do own-blunder "several" positions have? Not stored as a ladder, so not
  compared yet.
- How hard are two-move herrings? No data until they are served.
- Does the composed (not solved) mix reach 25% herrings?

## Related: blunder check herrings (separate mechanism, already decided)

Blunder check does not use `herring_pool`; its herrings are runs of Good user moves
(`app/services/blunder_check_candidates.py::_herring_runs`). The same tester said the herrings
there were "4-5 streaks of good moves and I already could have pre-moved them".

Findings on prod (5 sessions, 30 sequences, 67 answers, users 2 and 28, so indicative only):

- Herring moves need a pre-move expected score in 0.10 to 0.90 (about ±600 cp); blunders must come
  from within ±300 cp (`BLUNDER_MAX_PRE_EVAL_CP`). Served herring moves: median absolute eval
  255 cp, 15 of 36 beyond ±300 cp. Safe moves before a blunder: median 30 cp, 0 of 15 beyond.
- False-alarm rate was the same on herring moves (5 of 36) and on safe moves before a blunder
  (2 of 15). Blunders: 3 of 16 caught, 7 missed, 6 timed out at 10 s.
- Sequence length is a mild tell: the chance that the current move is the blunder is about 25% at
  moves 1 to 3, 20% at move 4 and 16% at move 5 (calculated from the shape-drawing rules).

Owner decision (2026-11-18): tighten the blunder-check herring band to ±300 cp, then measure
herring against blunder-sequence difficulty offline by extending the Phase 248 calibration report
(`scripts/blunder_check/oddness.py`). Wait for the owner's heads-up after Phase 252 concludes.

## Breadcrumbs

- `app/services/train_pool.py`: `herring_stmt`, `HERRING_SHARE`, `HERRING_PREFERRED_QUALIFYING_MOVES`,
  `HERRING_DEGENERATE_MIN_GAP_ES`
- `app/models/herring_pool.py`, `app/models/drill_solve.py` (`telemetry.guess_ms`, `move_ms`)
- `scripts/gen_red_herring_pool.py`
- `closed/SEED-261108-dk0-blunder-check-training.md` (arrow oddness, levers for herrings)
