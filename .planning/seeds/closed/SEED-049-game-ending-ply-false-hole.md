---
id: SEED-049
status: implemented
implemented: 2026-06-14
implemented_via: quick task 260614-tgs (see .planning/quick/260614-tgs-seed-049-exclude-the-game-ending-ply-fro/)
planted: 2026-06-14
planted_during: prod investigation of SEED-045 (Phase 119) eval-drain holes — diagnosing why the stamped-with-holes count kept drifting up after the bounded-retry fix shipped
trigger_when: next eval-pipeline / eval-drain / analysis-coverage phase, or immediately if the tier-3 drain churn on re-armed games becomes a concern. Promote via /gsd-plan-phase.
scope: small (1 phase — fix the hole counter in the drain + the resweep predicate; no migration, no lichess backfill)
---

# SEED-049: The game-ending ply is a false hole (correct the SEED-045 hole definition)

## Why This Matters

SEED-045 (Phase 119) shipped a bounded-retry drain on the premise that eval holes were
**transient Stockfish timeouts under pool contention** that a retry would fill. A prod
investigation on 2026-06-14 disproved that premise: **~99.9% of prod "holes" are a structural
artifact of the game-ending move, not timeouts.** The bounded retry is firing (and the cap path
is stamping games complete-with-holes) on positions it can never fill, while the genuinely
transient holes it was designed for number ~2 in all of prod.

## The Actual Cause

Under post-move storage (SEED-044), row `k` holds the eval of the position **after** move `k`.
For the move that **ends the game** (checkmate / stalemate / insufficient material), the position
after it is the game-over terminal. `_collect_full_ply_targets` deliberately skips game-over
terminals (`include_terminal and ... not board.is_game_over()`, eval_drain.py ~line 217) — you
cannot and should not evaluate a position with no legal moves. So the game-ending ply's
post-move eval is `(None, None)` **forever, by design**. The SEED-045 hole definition excludes
the terminal ply (`ply < MAX(ply)`) but NOT the move *into* the terminal (`ply = MAX(ply) - 1`),
which under post-move storage is exactly where the un-fillable NULL lands.

## Evidence (prod, 2026-06-14)

Across all post-Phase-119 retry-path games (`full_eval_attempts >= 1`, engine games):
- **23 holes, 23/23 at `ply = max_ply - 1`** (the game-ending move), **0 genuine mid-game holes**.
- 23/23 had `best_move` written by the engine → the search **completed, no timeout, no crash**.
- 22/23 `move_san` ended in `#` (the one without was a non-`#`-annotated game-over).

Across the broader analyzed population (holes where `best_move IS NOT NULL`, isolating analyzed
games from the 558k un-analyzed backlog): **1,381 holes / 1,380 games — 1,379 at `max_ply - 1`,
1,333 explicit checkmate, only 2 genuine mid-game holes.** Avg 5.9 pieces (trivial endgames the
engine mates in instantly).

Sample of capped games (all `full_eval_attempts = 2`, stamped, holed): every hole was the mating
move — `Qh8#` / `Qd4#` / `Qh7#` / `Rd8#` / `Qxf7#` … each at `ply = max_ply - 1`, `best_move` set.

## Chosen Fix: Option (a) — exclude the game-ending ply from the hole definition

A ply whose move ends the game (resulting position `is_game_over()`) is **not a hole** — its
NULL post-move eval is legitimate and expected, exactly like the terminal ply already excluded.

**Decided AGAINST option (b)** — storing a synthetic `eval_mate = 0` ("mate delivered") and/or
backfilling lichess games — for three reasons:
1. **`eval_mate = 0` is unrepresentable.** `eval_mate` is a *signed* white-perspective score
   (positive = white mates, negative = white gets mated; flaws_service.py:172 keys on
   `eval_mate > 0`). Zero has no sign, so it can't encode *who* was mated, and the existing
   `> 0` check would misread every `0` as "opponent has forced mate." Overloading ±1 collides
   with real mate-in-1.
2. **The position is genuinely unevaluable** — no legal moves; the result comes from the game
   outcome, not a position eval. The engine skip and lichess's omission are both correct.
3. **Consistency points to (a).** Lichess `%eval` games — the project's reference standard —
   leave the mating ply **empty** (verified: ~516/538 mate-ending lichess games in a 3k sample
   have NULL there; terminal ply NULL 3000/3000). Every downstream consumer (flaw classifier,
   endgame analytics, WDL) already handles an empty game-ending ply because it must for lichess
   games. Filling only engine games would make them *inconsistent* with lichess; backfilling
   lichess would invent data to "fix" a non-problem and risk the `eval_mate > 0` misread.

The empty game-ending ply **is** the consistent convention. (a) just codifies it for engine
games.

## Implementation

- **Primary — live drain (`_apply_full_eval_results`, eval_drain.py ~line 406-453).** Do not
  count a ply as a hole (`failed_ply_count`) when its post-move position is the game-over
  terminal. The drain already computes this at `_collect_full_ply_targets` (the
  `not board.is_game_over()` branch that skips the terminal donor) — thread that knowledge into
  the counter so the game-ending ply is a known-empty, not a failure. Effect: these games stamp
  complete on **attempt 1** (Path A) — no retries, no cap-path Sentry event, no churn.
- **Secondary — resweep predicate (`resweep_holed_games`, eval_drain.py ~line 1619-1639) and
  `scripts/resweep_holed_games.py`.** Exclude the game-ending move ply. `move_san LIKE '%#%'`
  covers 1,333/1,379 (checkmate); stalemate / insufficient-material endings (rare, non-`#`)
  need a board-replay or game-result check to be exact. The 2 genuine mid-game holes are at
  `ply < max_ply - 1`, so excluding only the terminal-move ply is precise and safe. Consider
  whether the SQL proxy is good enough or the resweep should replay the final position.
- **No migration, no lichess backfill, no `eval_mate` writes.**
- **Tests:** a game ending in checkmate stamps complete on attempt 1 with `failed_ply_count == 0`;
  a game with a genuine mid-game NULL still retries; resweep does not flag mate-ending games.

## Consequences / Cleanup

- **SEED-045's retry becomes precise, not wasted.** After (a) it fires only on the ~2 genuinely
  transient holes instead of 1,379 false ones — the mechanism finally does its intended job.
  SEED-045's bounded-retry + cap (D-116-07) stays; this only corrects *what counts as a hole*.
- **The 1,262-game re-arm self-heals.** On 2026-06-14 the investigation re-armed 1,262
  pre-Phase-119 stamped-with-holes games via `resweep_holed_games --db prod` (markers cleared,
  `full_eval_attempts = 0`). Their only holes are this terminal-move artifact. Once (a) ships,
  the next drain pick stamps each clean on attempt 1 (Path A) — no 3× churn. Given the 558k
  backlog and tier-3's recency lottery, they likely won't be re-picked before the fix lands. If
  the fix is delayed, current code will churn them 3× and re-cap (bounded, self-limiting waste).
- **Uncommitted on `main`:** the `--db {dev,benchmark,prod}` flag added to
  `scripts/resweep_holed_games.py` + the optional `session_maker` param on
  `resweep_holed_games` (eval_drain.py) during the investigation. Hold or fold into this phase,
  since the resweep predicate changes here anyway.

## Breadcrumbs

- `app/services/eval_drain.py::_apply_full_eval_results` (~line 406-453) — `failed_ply_count`
- `app/services/eval_drain.py::_collect_full_ply_targets` (~line 211-226) — the
  `not board.is_game_over()` terminal-donor skip that already knows the answer
- `app/services/eval_drain.py::resweep_holed_games` (~line 1619-1639) — the resweep predicate
- `app/services/eval_drain.py` Path A/B/C decision tree (~line 1437-1496) — where stamp-complete
  is decided from `failed_ply_count`
- `scripts/resweep_holed_games.py` — the backfill tool + new `--db` flag
- `app/services/flaws_service.py:172` — the `eval_mate > 0` sign check that rules out `eval_mate = 0`
- SEED-044 (post-move storage, the +1 shift), SEED-045 (bounded retry — corrected here),
  SEED-046 (tier-3 recency lottery)
