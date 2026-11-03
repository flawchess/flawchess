---
quick_id: 261103-aad
mode: quick
executed: inline (orchestrator, no subagents)
---

# Herring opening ply floor and winnability band

Follow-up to 261103-9xl. Prod facts (2026-11-03):

- Opening-bucket rows sit at ply 12–26, median 13; 1,619 of 1,668 at ply ≤ 16 (moves 6–8, book).
  HERRING_MIN_PLY=12's stated intent ("not an opening-theory pick") is not met for the opening bucket.
- A 0.2% TABLESAMPLE of prod `game_positions` (|eval_cp| ≤ 200) still has ~3,300 opening-phase
  positions at ply ≥ 20, so a ply-20 floor leaves a large enough frame to refill the bucket.
- No winnability check exists anywhere: 310 rows have mover best-move ES > 0.80 (decided wins,
  mostly endgame 163 / middlegame 125), 1 row < 0.20.

## Task 1: constants + serve-time gates (`app/services/train_pool.py`)

- `HERRING_MIN_OPENING_PLY = 20` (move 10+): opening-phase rows below it are not served.
- `HERRING_MAX_BEST_ES = 1 - WINNABILITY_FLOOR_ES` (0.80): symmetric decided-win cap.
- `herring_stmt` WHERE: `WINNABILITY_FLOOR_ES <= best_es <= HERRING_MAX_BEST_ES` and
  `phase != opening OR ply >= HERRING_MIN_OPENING_PLY`. Query-time, so takes effect on the existing
  pool with zero re-analysis (the established loose-generation / tight-query split).
- Docstring: winnability is now enforced at serve time (and generation).

## Task 2: generator (`scripts/gen_red_herring_pool.py`)

- Opening-bucket candidate frame uses `ply >= HERRING_MIN_OPENING_PLY`; others keep `HERRING_MIN_PLY`.
- Reject (new outcome kind `winnability`, own tally line) when best-move ES is outside
  `[WINNABILITY_FLOOR_ES, HERRING_MAX_BEST_ES]`, so a top-up does not spend slots on unservable rows.
  Not applied in `--measure` mode (that mode histograms the whole searched population).

## Task 3: tests

- `tests/services/test_train_pool.py`: winnability band (inside served, above cap / below floor
  excluded), opening ply floor (opening ply 19 excluded, ply 20 served, middlegame ply 12 served).
  Fixtures that seed opening-phase rows must use ply ≥ HERRING_MIN_OPENING_PLY.
- `tests/scripts/test_gen_red_herring_pool.py`: opening frame skips ply < floor; winnability reject.

## Not in this task (needs owner go-ahead)

Prod refill of the opening bucket: `gen_red_herring_pool.py --db prod --phase opening
--n-positions 1667 --reset` (local Stockfish over the tunnel, destructive for opening rows,
drill_solves link is SET NULL). Until it runs, the deployed serve gate leaves almost no
opening herrings and the round-robin serves middlegame/endgame only.
