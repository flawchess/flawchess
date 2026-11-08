---
id: SEED-261108-zkp
status: dormant
planted: 2026-11-08
planted_during: v2.27 (/gsd-explore session on blunder-check selection)
trigger_when: first phase of the next milestone, before blunder-check planning (SEED-261108-dk0 depends on it)
scope: medium-large (one phase: schema + go-forward scoring + local backfill)
---

# SEED-261108-zkp: Maia stats on game_flaws

## Why This Matters

No Maia data is stored for flaws today. The only stored Maia value is `game_best_moves.maia_prob`, written for gem/great candidates (played move == Stockfish best). Only 6,268 of the 4.58M prod blunders (0.14%) overlap it (checked 2026-11-08). Precomputed Maia stats per flaw enable:

1. **The blunder-check face-palm selection test** (SEED-261108-dk0): Maia at the mover's rating gives the played blunder less than X probability, and Maia's top move is safe; for missed punishments, Maia finds the punishing move.
2. **A face-palm filter on the Flaws tab**, showing only blunders the player really should have seen.
3. **Data for a future chess data story** (e.g. how often rating peers would have found the right move, by Elo and phase).

## When to Surface

**Trigger:** the owner plans to open a new milestone whose first phase is this precompute. Blunder check (SEED-261108-dk0) follows it.

## What

- **One Maia-3 inference per `game_flaws` row**: both players, mistakes and blunders. 7.60M rows on prod (2026-11-08): 3.02M mistakes (765k misses), 4.58M blunders (1.77M misses).
- **At the mover's rating at game time**, converted with `pinned_elo_for_mover` (`app/services/best_move_candidates.py`), which mirrors the analysis-board Maia card's `deriveRawDefault` (lichess-blitz normalization, clamped to 600-2600).
- **Values per flaw:** P(played move), P(Stockfish best move), Maia's top move (UCI) and its probability. One inference yields all of them: `score_move` already computes the full policy via `mask_and_softmax` and discards all but one move, so a full-policy helper is a few lines.
- **No stored `maia_elo` column (owner decision):** the Elo is derivable by joining `games`. Accepted cost: a later retune of the chess.com-to-lichess conversion means a re-run.
- **Per-game completion stamp**, mirroring `games.best_moves_completed_at` (and its `is_maia_available` guardrail).

## Storage (open)

Separate nullable columns vs one JSONB column, not decided:

- **Columns:** `maia_played_prob REAL`, `maia_best_prob REAL`, `maia_top_uci varchar(5)`, `maia_top_prob REAL`.
- **Recommendation:** typed columns for the scalars that filters and aggregates hit. A Flaws-tab filter like `maia_played_prob < X` runs across millions of rows, and 4-byte REALs avoid per-row JSONB parsing and overhead. Columns also avoid the asyncpg trap where Python `None` written to JSONB is `null::jsonb`, not SQL NULL. Add a deferred JSONB alongside only if a richer policy (e.g. top-k moves) is wanted for stories.

## Go-forward scoring

Score flaws in the eval-apply path alongside the best-move pass. About 7.5 flaws per analyzed game, so about 0.5-1 s of CPU per game (the best-move pass already runs 6-13 Maia calls per game). Only where the `maia-inference` group is installed, with the same stamp guardrail as `best_moves_completed_at`.

## Backfill

- **Run locally on the dev machine** against prod over the tunnel (`bin/prod_db_tunnel.sh`), not on the server, with 8-10 worker processes.
- **Order like the ES lottery's priority** (recently active users first, newer games first), but deterministic, checkpointed and resumable.
- **Measured 2026-11-08 on the 16-core dev box:** about 65-78 ms per position single-threaded. Intra-op threads and batching barely help (4 threads + batch 32: 55 ms), so scale by processes.
- **Estimate:** 7.6M × 70 ms ≈ 150 core-hours ≈ 16 h on 9 processes, plus about 5 h of writes over the tunnel (prod retag precedent: 4.76M rows in 3h17m), overlappable. About one day in total.

## Gotchas

- **Rebuild exact positions by replaying `games.pgn`**, not from `game_flaws.fen`. That column is `board_fen()` only (no side to move, castling or en passant), and Maia's softmax masks to legal moves via `chess.Board(fen)`, so guessed castling rights skew the probabilities.
- **Flaw reclassification is a 4-way diff/upsert** (`_classify_and_fill_oracle` in `eval_apply.py`). It must carry the Maia columns through, like the PV blobs, or a re-analysis silently clears them.
- **Top-move safety is only partly resolvable from stored data:** safe when the top move equals Stockfish's best move, or the second-best with a good enough eval; fails when it equals the played move. Otherwise unknown. Blunder check's default treats unknown as not qualifying (no extra Stockfish search); a stories use may want the share of unknowns.

## Breadcrumbs

- `app/services/maia_engine.py` (`score_move`, session setup), `app/services/maia_encoding.py` (`mask_and_softmax`, `encode_board`)
- `app/services/best_move_candidates.py` (`pinned_elo_for_mover`)
- `app/services/eval_apply.py` (`_build_best_move_candidates`, `_classify_and_fill_oracle`)
- `app/models/game_flaw.py`, `app/models/game_best_move.py`, `app/models/game.py` (`best_moves_completed_at`)
- `.planning/seeds/SEED-261108-dk0-blunder-check-training.md` (consumer)
