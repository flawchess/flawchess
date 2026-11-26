---
phase: 262-facepalm-promotions-and-key-move-gate
plan: 01
subsystem: backend-services
tags: [chess, line-material, facepalm, promotion, static-exchange]

requires:
  - phase: 259-facepalm-quiet-point
    provides: quiet-point line walk and the single stored-pair writer (facepalm_material_inputs)
provides:
  - promotion-aware _victim_value (_promotion_gain) read by the first move, the quiet walk and the static exchange
  - pinned stored pair for the promotion cap examples, D-03 desperado case pinned
affects: [262-02, 262-03, 262-04, facepalm material inputs, line pass, features tool]

actuals:
  tokens: 9000
  tasks: 3
  commits: 3
plan_head_before: 57cafb6e4a6efd581ee2db528018eba62f6f5e1a
plan_head_after: f60348fba9a17499c42a5394f5cc114337686b29

tech-stack:
  added: []
  patterns:
    - "One victim rule: captured piece plus promotion gain lives in _victim_value; the static exchange reads it"

key-files:
  created: []
  modified:
    - app/services/line_material.py
    - tests/services/test_line_material.py
    - tests/services/line_material_fixtures.py
    - tests/services/test_facepalm_inputs.py

key-decisions:
  - "D-01: promotion credits promoted piece minus pawn (Q 8, R 4, B/N 2); capture-promotion adds the captured piece"
  - "D-02: no cap, floor or mate constant changed (verified by assertion)"
  - "D-03: capture of a freshly promoted piece on its promotion square counts; promotion is a gain so it clears the desperado quiet square"

patterns-established:
  - "Per-depth exact tests plus a recorded mutation check for each promotion rule"

requirements-completed: [D-01, D-02, D-03]

status: complete
---

# Phase 262 Plan 01: Promotions count as material Summary

One rule in `_victim_value` (captured piece plus promoted piece minus pawn) now feeds the first move, the quiet walk and the static exchange, so an opponent queening stores the capped loss 5.0 through the app's single writer.

## Accomplishments

- Task 1 (tracer): `_promotion_gain(move)` added; `_victim_value` returns captured value plus promotion gain (en passant branch first). FEN `6k1/8/8/8/8/8/2p5/1R4K1 w`, played `b1b3`, line `c2c1q ...` reads 8, 8, 8, 8, 8 and stores loss 5.0, missed 0.0 (was 0.0).
- Task 2: `_exchange_value` takes its gain from `_victim_value` (research correction a), with a bug-fix comment at the site. New tests `test_promotion_gain_per_piece`, `test_quiet_promotion_rules`, `test_see_prices_a_capture_promotion` (reads 10 at every depth, was 2) and `test_desperado_exclusion_counts_a_freshly_promoted_piece` (D-03, reads 1, was 0). Fixtures 35, 170, 177, 162 re-derived: 35 reads 0, 8, 8, 8, 8; 170 reads 0, 0, 0, 4, 4; 177 reads 5, 5, -3, -3, -3; 162 reads -8 at every depth with mate ply 1 unchanged. Module docstring counting rules rewritten (promotion is non-quiet, short line ending on a promotion is settled by the static exchange, desperado skip of an opponent capture-promotion is whole).
- Task 3: `test_promotion_cap_examples_store_the_decaying_mean` pins the stored pair: queen stays 1.1290322580645162, queen taken at once 0.0 (the CONTEXT 0.23 example is wrong under D-01, per-depth values are 0, 0, -1, -1, -1), promotion-only line 0.0 (a settled loss, no longer None), D-03 position 1.0; missed 0.0 in each.

## Mutation checks

- `_promotion_gain` forced to 0: `test_opponent_queen_promotion_next_move_stores_the_cap` fails.
- Old `_SEE_VALUES` gain lines restored in `_exchange_value`: `test_see_prices_a_capture_promotion` fails (the only failure in the file); before the fix it read 2, not 10.
- Pre-change code failed the four promotion fixtures and the D-03 case (observed before the fixture/test edits).

## Verification

- Full backend suite `uv run pytest -n auto -x`: 6982 passed, 8 skipped, 0 failed. No other test pinned material on a promotion line, so no extra re-derived expectations.
- `ruff check`, `ruff format --check`, `ty check app/ tests/ scripts/`, `check_function_size.py --fail-over-depth 4`: all clean.
- Cap/floor/mate constants assertion `(5, 5, 0, 0, 5, 5)` still passes (D-02); `blunder_check_rules.py` untouched.

## Deviations from Plan

None - plan executed as written. Fixture note for 170 and 177 were reworded to match the derived per-ply arithmetic (170: the opponent queens at ply 7 for +8, the blunderer takes the queen for -9, the rook recaptures for +5, net 4; 177: 5 is the opponent's 8 net of the bishop the blunder took).

## Known Stubs

None.

## Threat Flags

None. Tokens still go through `_parse_move` and the legality check before `_victim_value`; `move.promotion` is a python-chess piece type so `PIECE_VALUES` always has the key.

## Self-Check: PASSED

- app/services/line_material.py contains `def _promotion_gain` (FOUND)
- commits a3a95d624, e370d9fd8, f60348fba reachable from HEAD (FOUND)
