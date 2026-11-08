---
id: SEED-261108-dk0
status: dormant
planted: 2026-11-08
planted_during: v2.27, phase 246 (training-features research session)
trigger_when: after the Maia-stats-on-game_flaws phase (see Breadcrumbs) lands; that phase opens the next milestone, and blunder check follows it
scope: large (design not finished; likely 2+ phases after the Maia precompute phase)
---

# SEED-261108-dk0: Blunder-check training

## Why This Matters

Train's puzzles announce that something critical is happening. In a real game nothing does. Blunder check trains the habit of checking your own move before you play it, on stretches of the user's own games. The idea was inspired by Aimchess's spot-the-blunder drill. lichess users ask for unannounced drills that start before the critical moment with no hint ([forum](https://lichess.org/forum/general-chess-discussion/puzzle-dashboard-2)).

## Decisions (owner, 2026-11-08)

- **As close to a real game as possible.**
- **Checks only on the user's own moves.** The opponent's moves play through without a question.
- **Missed punishment counts.** Failing to punish an opponent blunder (e.g. a hanging piece) is a blunder to spot. Its share must be capped so missed-punishment sequences don't dominate.
- **Only face-palm blunders.** Moves the player should have seen easily *at their rating*. Selection uses Maia because this differs by Elo: an expert should spot an allowed or missed fork in 2, a beginner probably not.
- **Timer: about 15 s per own move.**

### Selection (owner, 2026-11-08, /gsd-explore session)

- **Window length varies: 3-5 user moves (5-9 plies)**, so the player can't tell when the sequence ends.
- **The puzzle ends at the first blunder**, whether caught or missed. Moves after it never matter, so a window does not need "only one blunder".
- **Constant per-move hazard, not a uniform blunder position.** Draw the length L (3-5) independently; at each user move the blunder is "due" with probability h, and the first firing is the blunder position. If none fires within L, the window is a red herring (all moves Good). The probability of a blunder at each question is then exactly h at every step, so surviving several safe moves tells the user nothing. With L uniform over 3-5, **h ≈ 0.265 gives about 30% herrings**. A uniform blunder position would leak: with 70% blunder windows of fixed length 4, the chance at the next question climbs 17.5% → 21% → 27% → 37%. `HAZARD` and the length range are named constants.
- **Selection procedure:** draw L and the blunder position, then pick a face-palm blunder with (position − 1) earlier user moves that are all Good. Herrings: pick a window of L user moves, all Good.
- **Quality bar "Good" for every user move before the blunder and every herring move.** "Good" = expected-score drop below `INACCURACY_DROP` (the flaw pipeline's threshold). A mistake never counts as "safe", so the answer key is unambiguous.
- **Face-palm test.** At the mover's rating at game time (converted via `pinned_elo_for_mover`, see below):
  - (a) Maia gives the played blunder less than X probability, **and**
  - (c) Maia's top move is safe (optionally holding at least Y% probability). Safety is known when the top move equals Stockfish's best move, or the second-best with a good enough eval; if the top move *is* the played move, the test fails. **Default: when the top move is neither best nor second-best, the blunder does not qualify** (no extra Stockfish search). Calibration measures how many blunders this drops.
  - Missed punishment: the punishing (Stockfish best) move gets at least X′ probability, or is Maia's top move.
- **One fixed X for all ratings.** Maia already conditions on rating, so a fixed X means "unlikely for a player of your rating". Low-rated players have more blunders, so supply is not expected to be the constraint.

## Proposed (discussed, not yet decided)

- **Ask before the move is played.** Show the user's move as pending (lifted piece or arrow), ask "blunder or safe?", then play it. Judging a move already on the board is hindsight, not a real-game check. Showing the game's real clocks would add realism.
- **Ask before the opponent's reply appears**, so a punishing reply doesn't reveal the answer.
- **Missed-punishment windows must include the opponent's blunder** that the user failed to punish.
- **Score per sequence** (catch the blunder or correctly call the line clean, with no false alarms), with per-move points on top. Always answering "safe" must not pay off.
- **Calibrate X (and X′, Y) from the precomputed Maia stats** once the backfill lands: in SQL, the share of blunders qualifying at several thresholds by Elo bucket, how often top-move safety can't be resolved, and supply per user under the hazard model.
- **Prefer older games, or games not yet seen in Train,** to limit the user remembering the game.

## Open Questions

- **Timer:** fixed 15 s or based on the user's own median think time (Train telemetry), and does slowness only lose a bonus or also cost points?
- **After a correct flag:** chain into "find the better move" (reuse Train grading)?
- **Placement:** inside the daily Train session or a separate mode with its own score, streak and leaderboard interplay?
- **Missed-punishment cap:** what share (a starting guess was 25-30%, as a named constant)?
- **Supply:** windows need per-ply evals, so only fully analyzed games qualify (`full_evals_completed_at`). Count supply on prod before planning (part of the calibration above).

## Implementation Notes

- **No Maia data is precomputed for flaws today (checked on prod, 2026-11-08).** The only stored Maia value is `game_best_moves.maia_prob`, written only for plies where the played move == Stockfish's best move and it beat the runner-up by at least `INACCURACY_DROP` (gem/great candidates, `eval_apply.py` `_build_best_move_candidates`). Of 4.58M blunders, only 6,268 (0.14%) overlap a `game_best_moves` row, almost certainly lichess-eval engine-divergence noise. The precompute is planned as its own phase: see SEED-261108-zkp.
- **Maia cost (measured on the 16-core dev box, 2026-11-08):** about 65-78 ms per position single-threaded; extra intra-op threads and batching barely help (4 threads + batch 32: 55 ms), so throughput scales with processes. Prod is about 150 ms per position per the `eval_apply.py` comment.
- **`score_move` already computes the full policy** (`mask_and_softmax` returns every legal move's probability) and discards all but one move. A full-policy helper is a few lines.
- **`game_flaws.fen` is `board_fen()` only** (no side to move, castling or en passant). Maia's softmax masks to legal moves, so exact positions need PGN replay.
- **Elo conversion:** `pinned_elo_for_mover` (`app/services/best_move_candidates.py`) mirrors the analysis-board Maia card's `deriveRawDefault` (lichess-blitz normalization, clamped to 600-2600). Reuse it.
- **Flaw data:** `game_flaws.is_miss` marks missed punishments, along with severity, phase, tempo and the tactic motif columns.
- **Herring precedent:** Train's red-herring pool (SEED-120, `herring_pool`) is the closest existing pattern for clean positions.

## Breadcrumbs

- `.planning/seeds/SEED-261108-zkp-maia-stats-on-game-flaws.md`: prerequisite phase, first of the next milestone
- `app/services/maia_engine.py`, `app/services/maia_encoding.py`, `app/services/best_move_candidates.py`
- `app/models/game_flaw.py`, `app/models/game_best_move.py`, `app/models/herring_pool.py`
- `app/services/train_pool.py`, `app/repositories/train_repository.py`
- `frontend/src/components/train/`
- `.planning/research/FEATURES.md` (2026-07-25 Train market research)
