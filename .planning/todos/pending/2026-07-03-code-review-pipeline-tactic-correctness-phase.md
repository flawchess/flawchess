---
created: 2026-07-03T00:00:00.000Z
title: Phase candidate — pipeline & tactic correctness fixes (code-review 2026-07-02)
area: pipeline / tactics / stats
priority: high
source: reports/code-review-fable-2026-07-02.md
promote_at: next /gsd-new-milestone (becomes a phase — needs plan + verify + tests)
files:
  - app/services/tactic_detector.py
  - app/services/flaws_service.py
  - app/services/eval_drain.py
  - app/routers/eval_remote.py
  - app/services/endgame_service.py
  - app/services/chesscom_client.py
  - app/services/lichess_client.py
---

## Why a phase, not a quick task

Each item touches a silent-data-loss or production-only-correctness path and needs tests +
a verify loop. "It looked like a one-liner" is exactly how the circuit-breaker and fen_map
bugs shipped. Full triage: `.planning/notes/2026-07-03-code-review-fable-triage.md`.

## Items

1. **#4 tactic production defects (live wrong output today)**
   - `has_forced_mate` is a no-op (`tactic_detector.py:2462-2490`): flag gates the mate
     branch but every mate detector re-checks `boards[-1].is_checkmate()` and bails. With
     `PV_CAP_PLIES = 12`, mates-in-7+ have truncated PVs → **deep mates never tag as mate**
     in prod. Fix: fall back to generic `mate` when the flag is set but the truncated PV
     doesn't end in checkmate (skip geometry-dependent subtypes). Add flag coverage (zero
     today).
   - `fen_map` stores `board_fen()` only (`flaws_service.py:443-451`) → ep/castling flaw
     moves fail `parse_san` (no tag), and a PV starting with an ep capture is pushed as a
     quiet pawn move without removing the captured pawn → corrupt board for the whole line.
     Fix: store `board.fen()` in the detector-internal `fen_map` (keep `board_fen()` for
     Zobrist comparisons per the CLAUDE.md rule).

2. **#2 entry-ply drain all-fail circuit breaker**
   `eval_drain.py:2304-2308` stamps every picked game `evals_completed_at = now()`
   regardless of eval success; `engine.evaluate()` returns `(None, None)` on a dead pool.
   Mirror the full-ply WR-05 breaker (`eval_drain.py:2556-2570`): if all results in a
   non-empty batch are `(None, None)`, release the lease instead of marking complete, emit
   ONE aggregated Sentry event, sleep. Fix the `EnginePool` docstring
   (`engine.py:380-382`) in the same pass. (Related closed work: SEED-076.)

3. **5.1 quintile significance test anti-conservative**
   `endgame_service.py:2326-2328`: shared games sit on both sides of
   `compute_score_difference_test` (which assumes independent cohorts), dropping the
   anti-correlated covariance term → false "significant" verdicts. Track shared-game count
   m per (tc, quintile) and add `+2m·cov/(n_u·n_o)` (or use a paired test for the overlap).
   Fix the wrong independence docstring at `:2140-2143`. Point estimates unaffected.

4. **2.7 one malformed platform game aborts the whole import**
   `normalize_chesscom_game`/`normalize_lichess_game` called unguarded per game
   (`chesscom_client.py:325-330`, `lichess_client.py:184-188`); a single `KeyError` fails
   the entire job. Add per-game try/except + skip + one aggregated Sentry capture (the
   CLAUDE.md per-game rule, currently honored for PGN parse but not normalization).

5. **(cheap add) #6 entry-submit batch scoping — minimum guard**
   `eval_remote.py:746-813` stamps the FULL set leased under a worker id. At minimum add
   `entry_eval_lease_expiry > now()` to the guard; ideally return claimed `game_ids` from
   `/entry-lease` and stamp only the echoed/intersected set. (Operator-error-triggered:
   shipped worker uses random ids, so low real-world likelihood — hence "minimum guard".)

## Verification

Per item: unit test the tactic mate-fallback + an ep/castling flaw fixture (build board via
conftest `build_detector_board`, not `chess.Board(fen)` — see memory
`project_tactic_detector_flaw_move_context`); a dead-pool drain test asserting the lease is
released and NOT stamped; a shared-cohort significance test asserting SE widens; a
malformed-game import test asserting skip + job completes.
