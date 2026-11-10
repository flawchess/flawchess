---
phase: 248-blunder-check-refutation-stats-and-calibration-seed-261108-d
plan: 05
subsystem: scripts/blunder-check-calibration
tags: [calibration, maia, arrow-oddness, spot-check, recommended-constants, SEED-261108-dk0]
status: complete
requires: ["248-02", "248-04"]
provides:
  - "scripts/blunder_check/oddness.py: seeded Good-move sample per Elo bucket, Maia scoring on exact replayed boards, per-bucket quartiles / rank-1 share / AUC"
  - "scripts/blunder_check/spot_check.py: hazard-model window draws, read-only PGN/refutation lookups, spot-check markdown"
  - "render.py sections 'Arrow oddness' (D-17) and 'Recommended constants' (D-18)"
  - "CLI flags --oddness-sample, --spot-check-per-bucket, --seed; spot-check-{date}.md; EXIT_MAIA_UNAVAILABLE = 3"
affects: [248-08]
requirements-completed: [D-17, D-18]
key-files:
  created:
    - scripts/blunder_check/oddness.py
    - scripts/blunder_check/spot_check.py
  modified:
    - scripts/blunder_check/render.py
    - scripts/blunder_check/sample.py
    - scripts/blunder_check_calibration.py
    - tests/scripts/test_blunder_check_calibration.py
decisions:
  - "GoodMoveOddness lives in sample.py (re-exported by oddness.py) so the cached Collection can hold it without an import cycle"
  - "The cache stores db_target, seed and the oddness records; --from-cache reopens that target read-only for the spot-check lookups only (so the plan's --from-cache command works without --db); a cache without a target skips the spot-check with a log line"
  - "Blunder side of the oddness table = usable blunders (findable at R/X' AND pre-move ES in band), the same population the windows use; Good moves are band-filtered at render time"
  - "pick_windows takes an rng and derives one child stream per Elo bucket, so one bucket's draws never shift another's"
metrics:
  completed: "2026-11-09"
commits: 2
plan_head_before: a66f5cf4a582bbbd6a2fbc508e8184de62c3e9e3
plan_head_after: 65475df49b23747c79deecff956e13b8bee7512c
actuals:
  tokens: 17700
  tasks: 2
  commits: 2
---

# Phase 248 Plan 05: Arrow oddness, spot-check and recommended constants Summary

**The calibration script now measures with the real Maia model whether blunders look odd at the user's rating, exports a reproducible hazard-model spot-check for humans, and states the chosen R, X' and eval band as a recommendation only.**

## What was built

- `oddness.py`: `select_good_moves` (every judged Good user move of rated non-guest games, no band filter at sampling, per bucket sample with one seeded `random.Random` over a (game_id, ply) order); `score_good_moves` (one read-only PGN SELECT per 100 games, session closed before inference, `replay_flaw_boards` for the exact board, `maia_engine.full_policy(board.fen(), pinned Elo)`, probability and rank from `compute_maia_flaw_stats`, raises when the policy is `None`, counts unreachable plies as skipped); `summarize_oddness` / `summarize_group` (quartiles, rank-1 share, `metrics.auc`).
- `spot_check.py`: `draw_window_shape` (L uniform over 3..5, first position whose 0.265 hazard fires, else herring), `pick_windows` (blunder window at position k only from a usable blunder that fits k at the chosen band, herring window from a disjoint run of L consecutive Good in-band moves, one game per bucket, bounded attempts), `fetch_window_details` (two read-only SELECTs, single-pass PGN replay to SAN, refutation = best_move else first pv token at ply+1, missed best at the answer ply, illegal stored UCI printed as `uci (illegal)`), `render_spot_check`.
- CLI: Maia lifecycle (`start_maia(intra_op_num_threads=1)`, exit 3 with a message when unavailable, `stop_maia()` in finally, skipped under `--from-cache` or `--oddness-sample 0`); spot-check file next to the report with the same overwrite protection.
- `render.py`: "Arrow oddness" (n, quartiles, rank-1 shares, AUC per bucket plus pooled row, how to read AUC) and "Recommended constants" (R, X', band, pass share per bucket and case, hazard-weighted fit, median supply, "recommendation only", spot-check file pointer).

## Tracer gate

Task 1 (`type=tracer`) was verified end to end before expansion: oddness tests green and the dev run with the real ONNX model wrote a report with a single `## Arrow oddness` heading (`HUMAN_VERIFY_MODE` end-of-phase with automated-only verify, so no checkpoint).

## Dev smoke (real Maia model, dev DB only; smoke evidence, not calibration evidence)

Plan commands, foreground:

| Run | Wall time |
| --- | --- |
| `--db dev --sample-permille 1000 --limit-games 300 --oddness-sample 20 --spot-check-per-bucket 5` (60 Good moves) | 13.6 s total (about 9 s of Maia) |
| `--from-cache ... --refutation-threshold 0.3 --spot-check-per-bucket 5` (with and without `--db`) | 2.0 s |
| extra wider run, all 9756 dev games, `--oddness-sample 300` (1800 Good moves), 6 spot-check windows per bucket | 4 m 44 s (16 s collection, 262 s Maia = about 0.146 s per Good move on the loaded box) |
| wider run re-rendered from cache | about 2 s |

Sizing input for plan 08: the default 1500 per bucket x 6 buckets = 9000 Good moves is about 22 minutes of single-threaded Maia at the loaded-box rate; fewer on an idle box. The aggregate scans, not the sample, dominate the prod DB cost (plan 04).

The plan's 300-game smoke only reaches low-id games without refutation pairs (oddness: 53 Good moves, 0 blunders). The wider dev run covers user 28's backfilled blunders (R = X' = 0.2, band [0.10, 0.90]):

| Elo bucket | n Good | n blunder | Good prob q1 / median / q3 | blunder prob q1 / median / q3 | Good rank 1 | blunder rank 1 | AUC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1200-1599 | 256 | 190 | 0.232 / 0.479 / 0.711 | 0.068 / 0.165 / 0.401 | 67.2% | 31.1% | 0.742 |
| 1600-1999 | 270 | 50 | 0.239 / 0.437 / 0.688 | 0.059 / 0.151 / 0.288 | 63.7% | 26.0% | 0.781 |
| all | 1524 | 240 | 0.205 / 0.432 / 0.711 | 0.067 / 0.162 / 0.374 | 64.0% | 30.0% | 0.726 |

Other buckets have Good moves but no scored blunders on dev (one user). Read as a smoke result: with one user's blunders, AUC around 0.74 to 0.78 says the arrow's oddness does leak, which is exactly the question plan 08 answers on prod. The 300-game smoke (R=0.2) showed `<800` 19 / `800-1199` 16 / `1200-1599` 18 Good moves, AUC n/a.

Recommended constants on the wider run: allowed pass 75.5% (n=204) and 78.4% (n=51) in 1200-1599 / 1600-1999, pure miss 52.1% / 50.0%, mixed 86.5% / 90.0%, hazard-weighted window fit 73.8% (n=240), median 4.0 usable blunder windows per user, 11 of 12 dev users under 50.

### Hand check (two windows against the stored game moves)

- `https://lichess.org/mH2a6Cz2` (mixed, blunder at position 2): report lead-in `49. Kg1 Kf5 50. Ra6`, judged `50... Qd1+` reply `51. Kh2`, blunder `51... Qf3`; the game PGN in dev has plies 96-101 = Kg1, Kf5, Ra6, Qd1+, Kh2, Qf3. The printed FEN has Ra6 and a pawn on f6, so the shown refutation `Rxf6+` is legal.
- `https://lichess.org/iWOmkB2E` (allowed, blunder at position 2): lead-in `12. Nc3 Ne7 13. a3`, judged `13... O-O` reply `14. Qd3`, blunder `14... Nxd4`, refutation `Qxd4` (rank 1, probability 0.754); the PGN has plies 22-28 = Nc3, Ne7, a3, O-O, Qd3, Nxd4, Qxd4.
- The FEN printed before each lead-in matches the side to move and move number of the first lead-in ply.

### Determinism

- Re-rendering the same cache with the same flags: `diff` of both the report and the spot-check is empty (checked on the 300-game and the wider cache; also with and without `--db`).

## Mutation proof

| Mutation | Failing test |
| --- | --- |
| spot_check: blunder pool ignores the position-fit check (`if True` instead of `blunder_fits`) | `TestPickWindows::test_blunder_windows_only_use_blunders_that_fit_their_position` |
| oddness: `auc(blunder_probs, good_probs)` (arguments swapped) | `TestOddnessSummary::test_known_auc_quartiles_and_rank_one_shares` and `TestArrowOddnessSection::test_section_filters_good_moves_by_band_and_prints_auc` |

Both reverted; suite back to green.

## Verification

- `uv run pytest tests/scripts/test_blunder_check_calibration.py tests/scripts/test_blunder_check_metrics.py`: 72 passed (41 + 31). `uv run pytest -n auto -x`: 5875 passed, 20 skipped.
- `ruff format` / `ruff check .` clean; `uv run ty check app/ tests/ scripts/`: All checks passed; `check_function_size.py app/ scripts/blunder_check scripts/blunder_check_calibration.py --fail-over-depth 4`: no breaches.
- Acceptance: `## Arrow oddness` and `## Recommended constants` once each in the dev report, "recommendation only" present, `replay_flaw_boards` in `oddness.py`, spot-check file with at least one window per bucket that has data.

## Deviations from Plan

1. **[Rule 3 - Blocking] `EXIT_EXISTS` moved from 3 to 4.** Plan 04's CLI used exit 3 for "refusing to overwrite"; this plan requires exit 3 for Maia unavailable (matching `scripts/backfill_maia_flaws.py`). No test or doc asserted the old value.
2. **`sample.py` also modified** (not in this plan's file list): `GoodMoveOddness`, `Collection.oddness`, `RunMeta.db_target/seed/oddness_sample/oddness_skipped`, and cache read/write for them. Needed so the oddness records ride the cache (a requirement of Task 1); old caches still load (`raw.get("oddness", [])`).
3. **"Recommended constants" section landed in the Task 1 commit**, not Task 2, because both sections share `render_report`; Task 2 added its test and the `spot_check_file` pointer wiring in the CLI.
4. **`score_good_moves` returns `ScoredGoodMoves(records, skipped)`** instead of a bare list, so skipped targets are counted in the report; `pick_windows` takes `SpotCheckParams` (report params + per-bucket count) and an `rng`, as the plan's rng signature implies.
5. **Oddness blunder side uses usable blunders** (qualifying and in band), where the plan text says qualifying; it is the population the windows actually contain. Stated in the section text.
6. The wider dev run (`--oddness-sample 300`, 4 m 44 s) was an extra run beyond the plan's two smoke commands, needed because the plan's 300-game sample contains no scored blunders. The harness moved it to the background after 180 s; it completed and its output is the evidence above.

## Known Stubs

None.

## Threat Flags

None new. T-248-11 mitigated and tested: the spot-check carries only the public platform link, user rating, pinned Elo, FEN and moves; a test asserts the test user id and email domain never appear. T-248-12 accepted: one single-threaded ORT session, sample size is a flag.

## Notes for plan 08

- Prod run: start the tunnel, pass `--db prod --cache ...`; `--overwrite` is required to re-run on the same day. The cache holds user ids and is gitignored; the report and spot-check hold none.
- The spot-check is the artifact to show GM Noel Studer; `--spot-check-per-bucket` default 20 per bucket.
- Dev blunder-side numbers above come from one user (28); do not quote them as calibration.

## Self-Check: PASSED

- Files exist: `scripts/blunder_check/oddness.py`, `scripts/blunder_check/spot_check.py`, dev outputs under `temp/blunder-check/` (gitignored).
- Commits `130d3834f` and `65475df49` are ancestors of HEAD on the phase branch.
