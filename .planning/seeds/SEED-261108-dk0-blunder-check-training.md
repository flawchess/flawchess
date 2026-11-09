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
- **Eval band (owner, 2026-11-09):** skip completely won or lost positions, judged on the pre-move eval, for both herrings and blunder windows. Applies to every judged user move (otherwise a herring can drift into a won position where nearly any move is "Good", and users learn "I'm way up, so it's safe"). Band bounds are named constants on the user's expected score.
- **Face-palm test (UNDER REVISION, see "Face-palm test v2" under Proposed).** At the mover's rating at game time (converted via `pinned_elo_for_mover`, see below):
  - (a) Maia gives the played blunder less than X probability, **and**
  - (c) Maia's top move is safe (optionally holding at least Y% probability). Safety is known when the top move equals Stockfish's best move, or the second-best with a good enough eval; if the top move *is* the played move, the test fails. **Default: when the top move is neither best nor second-best, the blunder does not qualify** (no extra Stockfish search). Calibration measures how many blunders this drops.
  - Missed punishment: the punishing (Stockfish best) move gets at least X′ probability, or is Maia's top move.
- **One fixed X for all ratings.** Maia already conditions on rating, so a fixed X means "unlikely for a player of your rating". Low-rated players have more blunders, so supply is not expected to be the constraint.

### Interaction and scoring (owner, 2026-11-09)

- **Separate training mode on the Train page**, with its own leaderboard on the leaderboard page: a **Points** and a **Score %** board, each with its own medals.
- **Shared Train schedule** (owner, 2026-11-09): blunder check and personalized puzzle training share the schedule and reminders. The number of puzzles per session is configured **separately per mode**, and **0 is allowed**, so a user can train only one mode.
- **Session streak:** a completed session of either mode counts toward the streak.
- **3-ply lead-in replay** (owner, 2026-11-09, replaces the earlier cold start): the window opens by replaying the 3 plies before the first judged move (opponent, user, opponent) at a fixed pace, then stops on the user's first judged move with its arrow. The ply count is a named constant (`LEAD_IN_PLIES = 3`). Near the start of a game, replay whatever plies exist. The lead-in is the same length for every window, so it leaks nothing about where the blunder sits. In a missed-punishment window whose first judged move is the miss, the opponent's blunder is the last lead-in ply.
- **Ask before the move is played:** the user's move is an arrow, and the piece stays on its source square. Prompt: "Safe / Blunder".
- **Ask before the opponent's reply appears**, so a punishing reply doesn't give the answer away.
- **Correct "safe":** award 1 point with a small animation and sound (reuse Train's point badges and sounds). Then play the user's move and the opponent's reply, and show the arrow for the user's next move with the prompt again.
- **Correct "blunder":** a larger bonus (starting value 3 points, a named constant). Then chain into "find the better move" for extra points (starting value 2, as in personalized puzzle training).
- **Solution screen:** reuse the personalized-puzzle solution screen. On a missed blunder, show the Best and Game cards and let the user investigate the lines and positions as in personalized puzzle training, with the same game info and Analyze button.
- **Missed-punishment windows use the same "Blunder" label** (owner, 2026-11-09). Failing to punish is a blunder, so no separate copy.
- **The lead-in is not quality-checked** (owner, 2026-11-09): it is what it is. Only the judged user moves carry the Good bar.
- **False alarm (flagging a safe move): the sequence ends.**
- **A missed blunder forfeits the window's safe points** (owner, 2026-11-09). Show them being discarded with a small animation and the 0-points feedback sound, so more feels at stake. This drops the "always safe" strategy from about 1.9 to about 1.2 points per window (herrings only), against about 5.4 for a perfect player. Watch for frustration in telemetry (abandon rate after a forfeit) and soften if needed.
- **Spaced repetition: only missed-blunder windows are reviewed**, 4 days later as in personalized puzzle training. Red herrings are never repeated.
- **Reviews are not labelled.** The player must not be able to tell a review from a new window. A review re-draws L and the blunder's position within the window from the hazard model, so it starts at a different move and feels less familiar.
- **Missed punishments: included, capped at about 30% per session** (owner, 2026-11-09, revised; replaces "no cap for now"). The calibration probe showed misses would be about 58% of qualifying blunders at every rating, not a beginner thing. The cap is a named constant (`MAX_MISS_SHARE`); reviews count toward it. **Not final:** the owner will discuss including or excluding misses with GM Noel Studer before the final call. On prod, 39% of blunders are misses (1.78M of 4.59M).
- **Clean window (herring) completed:** each safe answer already earned its point with animation and sound. There is no separate herring payoff.
- **Timer: a fixed 15 s per own move.** On timeout at a safe move, that move's point is lost **and all safe points accumulated in the window are discarded** (same animation and sound as the missed-blunder forfeit), so ignoring the timer doesn't pay. The window continues, and the user can still earn the blunder points by catching the blunder. A timeout on the blunder move counts as a missed blunder.
- **Cold start and thin supply: blunders from similarly rated FlawChess users** (owner, 2026-11-09). A user with no imported games or no analyzed flaws gets windows from other users' games, matched on the mover's rating at game time. This replaces the need for a lichess-puzzle-style warm-up and covers guests. (Owner idea for later, separate scope: replace the lichess warm-up puzzles in personalized puzzle training the same way.)
- **Missed-punishment windows include the opponent's blunder** that the user failed to punish.
- **"Second-best is safe" rule (resolved):** reuse `train_pool._vetted_move`, i.e. `best_es - second_es < INACCURACY_DROP`, computed from `missed_pv_lines[0]` (`b`/`bm` against `s`/`sm`). Phase 247 stores which move is second-best; its eval comes from the PV blob at selection time.
- **Score % = points scored / points possible** (owner, 2026-11-09; chosen over balanced accuracy). The second board is named **Score %**, not Accuracy, so users don't read it as the share of right answers. Possible points per window are the window's full maximum: 1 per safe move, plus `BLUNDER_POINTS` (3) and `BETTER_MOVE_POINTS` (2) if it holds a blunder. Forfeits, timeouts and false alarms all lower the score naturally, and the board measures quality while the Points board measures volume. Requires a minimum number of windows to rank. Rules:
  - **A false alarm in a blunder window still counts the unreached blunder's points as possible**, even though the blunder returns to the pool as unseen. Otherwise an early false alarm would cost only 1 point and a trigger-happy player would be barely punished.
  - It mixes two skills (spotting and finding the better move). That is intended: it matches what the Points board rewards.

  Under the hazard model (computed 2026-11-09, h=0.265, L uniform 3-5; better-move success rate in brackets), raw answer accuracy compresses the range so much that skill barely shows, while Score % spreads it:

  | Player (hit rate, false-alarm rate, better move) | Raw answer accuracy | Balanced | Score % |
  |---|---|---|---|
  | Always "safe" (0, 0, 0) | 73.5% | 50% | 21% |
  | Weak (0.5, 0.10, 0.4) | 79.4% | 70% | 44% |
  | Good (0.8, 0.10, 0.6) | 87.3% | 85% | 64% |
  | Strong (0.9, 0.05, 0.8) | 93.7% | 92.5% | 81% |

- **Other users' games:** no ownership gate needed (owner, 2026-11-09). Game deep links are public, as on chess.com and lichess. Copy must still not say "your move" for a stranger's game (precedent: the cross-user herring pool).
- **Session composition:** count reviews toward the ~70/30 blunder-to-herring mix (owner agreed, 2026-11-09).
- **False alarm inside a blunder window:** return the unreached blunder to the pool as unseen; herring false alarms are dropped (owner agreed, 2026-11-09).

## Proposed (discussed, not yet decided)

- **Face-palm test v2** (2026-11-09 review, owner agrees with the direction, details to elaborate). Problem with test (a): capping the played move's Maia probability means every blunder arrow is a move that looks unusual for the rating, while the Good moves before it look natural. Users could score by flagging odd-looking arrows instead of checking, and the drill would skip the *typical* blunders of a level, which the owner wants trained. Proposal: judge whether the punishment is easy to spot, not whether the move is unlikely to be played.
  - **Concrete:** the refutation leads to a tactic or material swing within a short depth that scales with rating, so purely positional blunders never reach beginners. Data: `allowed_tactic_motif` / `allowed_tactic_depth` / `allowed_tactic_confidence` and `allowed_pv_lines` (the opponent's punishing line from flaw_ply+1). Reuse the app's confidence gate for shown tactic tags; fall back to the PV's material swing (or mate) for untagged blunders. Depth caps per rating bucket are named constants.
  - **Findable:** Maia, set to the *user's* rating but playing the opponent's side in the position after the blunder, gives the punishing reply at least R probability or ranks it top ("would a player of your level see this reply if they checked?"). Needs one new Maia call per candidate: every Phase 247 column describes the position before the flaw. Misses already have this as X′ on `maia_best_prob`.
  - Drop the played-probability cap (a), or loosen it a lot. Revisit (c) too: "if Maia's top move is the played move, the blunder fails" excludes exactly the typical blunders of a level.
  - **Prod data (2026-11-09, user blunders, 2% / 0.5% samples):** `allowed_tactic_motif` is set on only 22% of non-miss blunders (`missed_tactic_motif` on 16% of misses), so tactic tags cannot gate. `game_positions.pv` (refutation line, ~9 plies on average) exists for about 93% of user blunders, so concreteness = material swing (or mate) along the refutation PV within the depth cap, computed by replaying the PV; motif tags are a label only. Check which `game_positions` row holds the refutation PV (two eval ply conventions) before relying on it.
  - **Miss classification for blunder check (owner agreed, 2026-11-09).** `game_flaws.is_miss` only means the opponent's previous move was a mistake or blunder (`flaws_service._is_miss`); it says nothing about the user's move. Split with expected scores from the user's point of view: `ES_ref` = before the opponent's error (after the user's previous move), `ES_played` = after the user's blunder.
    - **Allowed (non-miss):** `is_miss` false. Findable = Maia (user's rating, opponent's side, post-blunder position) finds the punishing reply. Concreteness line = refutation PV.
    - **Pure miss:** `is_miss` true and `ES_played ≥ ES_ref − INACCURACY_DROP` (gave back the gift, no worse than before). Findable = X′ on `maia_best_prob`/`maia_best_rank`. Concreteness line = best-move PV at the flaw ply.
    - **Mixed:** `is_miss` true and `ES_played < ES_ref − INACCURACY_DROP` (missed the gift and also hung something). Passes if either test passes, on either line.
    - The `MAX_MISS_SHARE` cap counts **pure misses only**; mixed cases behave like ordinary blunders. The mixed share of `is_miss` blunders is unmeasured (needs ES from per-ply evals with the right ply convention): first calibration step.
  - **Precompute, not runtime (owner decided, 2026-11-09):** add a refutation column pair (prob, rank) to the Phase 247 scorer for user-side allowed and mixed blunders (non-miss alone is about 61% of user blunders, roughly 1.4M rows; mixed adds some more; a few hours with the existing backfill tooling). Runtime is feasible (prod API has `maia-inference`, about 10-15 Maia calls per session) but calibrating R by Elo bucket and counting supply need the values in bulk anyway, and SQL-only selection stays simple.
  - **Phase 247 is still used:** `maia_best_prob/rank` is the miss test (X′); `maia_played_prob/rank` becomes a "typical blunder at your level" signal (prefer, don't cap); `maia_effective_moves` measures complexity; the Flaws-tab filter and stories are unaffected.
  - Calibration: shares passing concrete / findable / both by Elo bucket; Maia probability of judged Good moves against blunders (a big gap means the arrow's oddness gives the answer away); plus a hand spot-check of about 20 windows per bucket (owner, possibly Noel), since automated metrics have missed load-bearing selection defects before.

- **Calibrate X (and X′, Y) from the precomputed Maia stats** as the first phase (a first probe is below, see "Calibration probe"): in SQL, the share of blunders qualifying at several thresholds by Elo bucket, how often top-move safety can't be resolved, and supply per user under the hazard model.
- **Prefer older games, or games not yet seen in Train,** to limit the user remembering the game.

## Open Questions

- **Overlap with personalized puzzles (leaning cooldown, 2026-11-09):** the split by difficulty was considered and rejected by the owner. It would make personalized puzzles harder, and puzzle-only users would never meet their face-palm blind spots. Direction: a **cross-mode cooldown** keyed on the flaw (served in either mode → ineligible in the other for `CROSS_MODE_COOLDOWN_DAYS`), including spaced-repetition reviews, so one missed blunder is not due in both modes in the same week.
- **Re-drawn review windows need enough clean user moves:** a blunder at position k needs k−1 Good user moves before it. If a re-draw can't fit, fall back to the original window.

## Calibration probe (prod, 2026-11-09)

A 2% `TABLESAMPLE` of the user's own blunders (`severity = 2`, ply parity matches `user_color`) with Maia stats. The Phase 247 backfill had scored 5.70M of 7.62M flaws (75%) at the time. Rating = raw mover rating at game time (not yet `pinned_elo_for_mover`). Shares are of all user blunders in the bucket.

| Rating | n | Miss share | Non-miss: top = best | Non-miss: top = best or 2nd | + played < 0.05 (top = best) | + played < 0.10 (top = best or 2nd) | Miss: best is top | Miss: top or best ≥ 0.2 |
|---|---|---|---|---|---|---|---|---|
| <800 | 6,995 | 0.44 | 0.19 | 0.27 | 0.08 | 0.17 | 0.20 | 0.24 |
| 800-1199 | 7,745 | 0.39 | 0.22 | 0.33 | 0.09 | 0.18 | 0.19 | 0.24 |
| 1200-1599 | 7,522 | 0.38 | 0.23 | 0.33 | 0.10 | 0.18 | 0.18 | 0.23 |
| 1600-1999 | 6,992 | 0.35 | 0.24 | 0.35 | 0.10 | 0.19 | 0.17 | 0.23 |
| 2000-2399 | 3,763 | 0.37 | 0.25 | 0.35 | 0.12 | 0.20 | 0.20 | 0.25 |
| 2400+ | 1,201 | 0.36 | 0.26 | 0.37 | 0.12 | 0.19 | 0.15 | 0.24 |

Findings:

- **The top-move-safety rule is the main filter.** Maia's top move is Stockfish's best on only 19-26% of non-miss blunders, and best-or-second on 27-37%. A played-probability cap of X = 0.10 then keeps about half of those.
- **The qualifying share is flat across Elo**: about 0.17-0.20 non-miss plus 0.23-0.25 miss, so **about 40% of user blunders qualify** at X = 0.10 and X′ = top-or-0.2. That is an upper bound: the second-best safety check (PV blob) and the Good bar for inaccuracies (not in `game_flaws`) were not applied.
- **Misses are not a beginner thing.** Their share of all blunders goes from 44% (<800) to 35-37% (1600+), and among *qualifying* blunders misses are the majority (about 58%) at every rating. Without a cap most windows would be missed-punishment windows, which led to the ~30% session cap (see Decisions).
- **Lead-in fit (qualifying blunders, M/B only):** with at least 2 clean prior user moves, 85% of non-miss and 78% of miss blunders; with 4 (fits any position up to 5), 64% / 56%. Of misses, 36% follow a user move that was itself a mistake or blunder (mutual-blunder chains), so they can only serve at position 1. Selection must draw the position from the hazard model and then pick from blunders that fit it, or position 1 will be over-represented.
- **Supply per user (non-guest, analyzed games, 601 users):** user blunders per user, 10/25/50/75/90th percentiles: 96 / 503 / 1,951 / 4,103 / 8,892. At about 40% qualifying, the median user has about 800 qualifying blunders. **69 users (11%) have fewer than 50**; the fallback to similarly rated users' blunders covers them.

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
