---
quick_id: 261103-aad
status: complete
commit: 20b2a15a4
---

# Summary: herring opening ply floor and winnability band

## Done

- `app/services/train_pool.py`: new `HERRING_MIN_OPENING_PLY = 20`, `HERRING_OPENING_PHASE = 0`,
  `HERRING_MAX_BEST_ES = 1 - WINNABILITY_FLOOR_ES` (0.80). `herring_stmt` now serves only rows with
  best-move ES in [0.20, 0.80] and, for the opening phase, ply ≥ 20. Docstring updated.
- `scripts/gen_red_herring_pool.py`: opening-bucket frame uses the ply-20 floor; new
  `winnability` outcome/tally rejects searched candidates outside the band (not in `--measure`).
- Tests: serve-time band + opening floor (`tests/services/test_train_pool.py`), generator band
  reject + opening frame floor (`tests/scripts/test_gen_red_herring_pool.py`). The loose-band
  boundary test's best-move markers moved from ES 1.0 to 0.6 (1.0 is now a winnability reject).
  Mutation check: disabling each of the four gates individually fails its test.
- 689 Train/herring/drill/generator tests pass; ruff, ty, nesting gate clean.

## Prod impact (read-only check, 2026-11-03)

Servable rows before → after the serve gates: opening 1,175 → 13, middlegame 1,181 → 1,094,
endgame 1,171 → 1,071.

## Pending (owner go-ahead)

Regenerate the opening bucket on prod, ideally BEFORE deploying this commit so opening herrings
never go missing (the currently deployed serve code serves new rows fine):

    bin/prod_db_tunnel.sh
    uv run python scripts/gen_red_herring_pool.py --db prod --phase opening --n-positions 1667 --reset

Destructive for opening rows only: `drill_solves.herring_pool_id` is SET NULL, and an in-progress
session whose herring row is deleted silently drops that puzzle (`train_repository` reconstruction
skips a missing pool row), so run it off-peak. Local Stockfish, ~1M nodes per candidate. The ~311
rows outside the winnability band stay stored but unservable; a `--reset` of middlegame/endgame is
optional.
