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
- **Symmetric Elo:** feed the mover's Elo as both `elo_self` and `elo_oppo`, as the server `score_move` and the browser Maia card (`frontend/public/maia/maia-worker.js` `analyze`) both do. Parity with the Maia card beats the small accuracy gain from the real opponent rating.
- **One inference yields every value below:** `score_move` already computes the full policy via `mask_and_softmax` and discards all but one move, so a full-policy helper is a few lines.
- **No stored `maia_elo` column (owner decision):** the Elo is derivable by joining `games`. Accepted cost: a later retune of the chess.com-to-lichess conversion means a re-run.
- **Per-game completion stamp**, mirroring `games.best_moves_completed_at` (and its `is_maia_available` guardrail).

## Stored values

All nullable (NULL = not scored yet). "Best" and "second" are Stockfish's best and second-best moves at the flaw ply: `game_positions.best_move` and `missed_pv_lines[0].su` (`missed_pv_lines` covers 7,600,177 of 7,605,748 prod flaws, 2026-11-08). Rank = 1 + the number of legal moves with strictly higher Maia probability, so 1 means Maia's top choice.

| Column | Type | Use |
|---|---|---|
| `maia_played_prob` | REAL | Face-palm test (a): peers rarely play this |
| `maia_played_rank` | SMALLINT | "Natural mistakes" (rank 1 = Maia's own top choice) for stories; rank 1 fails the face-palm test outright |
| `maia_best_prob` | REAL | Missed-punishment test; "peers find the right move" stat |
| `maia_best_rank` | SMALLINT | Top-move safety: rank 1 means Maia's top move is Stockfish's best |
| `maia_second_prob` | REAL | With `maia_best_prob`, a lower bound on Maia's mass on safe moves (when the second-best move is Good) |
| `maia_second_rank` | SMALLINT | Top-move safety via the second-best move; NULL when there is no second legal move |
| `maia_top_prob` | REAL | The optional "top move holds at least Y%" test |
| `maia_entropy` | REAL | How spread out peers' choices are: position difficulty, for selection tuning and stories |

Ranks replace a stored `maia_top_uci` string: `maia_best_rank = 1` or `maia_second_rank = 1` answers "is the top move safe" without string comparisons. About 26-32 bytes per row, roughly 230 MB over 7.6M rows.

**Not stored, on purpose:**
- **Maia's value head (WDL):** the owner distrusts Maia WDL (SEED-128 rejected).
- **The full policy or top-k moves as JSONB:** about 30 legal moves × (UCI + probability) is 300-400 bytes per row, about 2.5-3 GB in total, for little beyond what the ranks give.
- **An Elo curve (P(best) across the 600-2600 ladder):** about 11× the inference cost (about a week on 9 cores) because batching doesn't help. Run it on a sample for a story instead.
- **Maia on non-flaw moves:** blunder check's "Good" moves don't need it. A story about how often peers find the best move overall would; out of scope here.

## Storage: typed columns (recommended over JSONB)

- **Filters and aggregates hit these values directly.** A Flaws-tab filter like `maia_played_prob < X` and story aggregates run across millions of rows. Typed REAL/SMALLINT columns avoid per-row JSONB parsing and the per-row key overhead.
- **Matches the high-cardinality table convention** for `game_flaws` (SMALLINT/REAL discipline), and `game_best_moves.maia_prob` is already a REAL.
- **Avoids the asyncpg trap** where Python `None` written to JSONB becomes `null::jsonb`, not SQL NULL, so `IS NULL` predicates and partial indexes miss it.
- **JSONB's flexibility edge is small:** adding a nullable column without a default is a metadata-only change in Postgres. Adding a value later still means re-running the backfill, with either storage.

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
- **Top-move safety is only partly resolvable from stored data:** safe when `maia_best_rank = 1`, or `maia_second_rank = 1` with a good enough second-best eval; fails when `maia_played_rank = 1`. Otherwise unknown. Blunder check's default treats unknown as not qualifying (no extra Stockfish search); a stories use may want the share of unknowns.

## Breadcrumbs

- `app/services/maia_engine.py` (`score_move`, session setup), `app/services/maia_encoding.py` (`mask_and_softmax`, `encode_board`)
- `app/services/best_move_candidates.py` (`pinned_elo_for_mover`)
- `app/services/eval_apply.py` (`_build_best_move_candidates`, `_classify_and_fill_oracle`)
- `app/models/game_flaw.py`, `app/models/game_best_move.py`, `app/models/game.py` (`best_moves_completed_at`)
- `.planning/seeds/SEED-261108-dk0-blunder-check-training.md` (consumer)
