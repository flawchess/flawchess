---
title: Tactic tagging — compute architecture & coverage (decision record)
date: 2026-06-17
context: /gsd-explore session on SEED-039 (tactic family / cause-of-error flaw tags)
status: pre-milestone decision record
---

# Tactic tagging — architecture decision record

Captured during a `/gsd-explore` session (2026-06-17) ahead of scoping a tactic-tagging
milestone. The point of this note: **SEED-039 was written 2026-06-07, before the v1.27
"Remote Eval Worker Fan-Out" milestone, and several of its core premises are now stale.**
Anyone planning this milestone should read this before re-deriving the compute path from
the seed's (outdated) assumptions.

## What changed since the seed was written

The seed assumes "there is no `pv`/`bestmove` column anywhere; the new Stockfish work is
capturing a PV per flaw." That is **false as of v1.27**. The remote eval worker
(`scripts/remote_eval_worker.py`, `pool.evaluate_nodes_with_pv`) now computes and submits:

- **`game_positions.best_move`** — stored for **every** ply. (Future consumer: miniboard
  "best move" replay on the game card. Not wired up yet.)
- **`game_positions.pv`** — stored **only at flaw-relevant plies**, keyed at
  **`flaw_ply + 1`** (SEED-044 post-move shift). That ply holds the **refutation line**
  (best reply to the flawed move) — exactly the line cook-style detectors run on.

Neither column is consumed yet. So tactic tagging is largely *consuming data we already
pay to produce*, not a new engine pass.

## Verified against prod (game 975197, user 44, black)

`game_flaws` plies vs `game_positions.pv` plies:

| flaw ply | color (parity) | pv stored at |
|---|---|---|
| 7  | black (user)     | 8  |
| 9  | black (user)     | 10 |
| 14 | white (opponent) | 15 |
| 15 | black (user)     | 16 |
| 22 | white (opponent) | 23 |

Three load-bearing facts fall out:

1. **`game_flaws` already materializes BOTH colors.** Even plies (14, 22) are the
   opponent's flaws, already stored under the importing user's `user_id`. So SEED-039's
   "opponent-flaw materialization (drop the player-only filter)" is **already done**.
   `is_opponent` is derivable as `ply parity vs games.user_color` — a convenience column,
   not a re-classification effort. (Consistent with the standing memory note
   "game_flaws covers both players".)
2. **`pv` is keyed at `flaw_ply + 1`** — clean 1:1 post-move shift. The detector reads
   `game_positions.pv` at that ply; no reconstruction, no synthetic board search.
3. **PV is captured for both colors' flaws** (plies 15 and 23 are opponent refutations).
   So the seed's worry that opponent tags would need a separate both-color PV pass
   **does not apply** — the data is already there.

## Compute path (settled)

- **Detector = pure CPU, no engine.** Reads stored `pv` at `flaw_ply + 1`, builds the
  `(board, line, pov)` the cook heuristics expect, names the motif. Runs identically inside
  `classify_game_flaws` (eval drain) and `backfill_flaws.py` (recompute). No Stockfish, no
  OOM exposure. The "extend backfill_flaws.py vs leverage workers" framing was a false
  dichotomy: `backfill_flaws.py` runs the **detector** (CPU); the workers already produced
  the **PV** (engine).
- **No new worker code, no bespoke PV-gap job type.**

## Coverage (prod, 2026-06-17)

| games | count | tactic-taggable? |
|---|---|---|
| self-eval'd (`full_evals_completed_at` set) | 130,996 | **yes, today** — pv present |
| lichess-eval only (`lichess_evals_at` set, no full eval) | 13,588 | not yet — flaws exist but `pv` is NULL |
| no eval | 478,993 | irrelevant — no flaws until eval'd |
| total | 623,577 | |

The lichess gap (~9% of eval'd games) needs **no special tooling**: full-eval'ing those
games through the **existing tier-3 idle fleet** yields `best_move` (miniboard) *and* `pv`
(tactic) in one pass. `tactic_motif` simply stays NULL until `full_evals_completed_at` is
set. The milestone ships tags for ~131k games on day one; lichess coverage fills in via
infra that already exists.

## Locked decisions (this session)

- **Storage: single `tactic_motif`** (nullable SmallInteger enum), at most one per flaw.
  NOT a bitmask, NOT a join table. Matches the existing one-tag-per-family rule; clean
  `GROUP BY tactic_motif`.
- **Tiebreak: fixed priority order**, NOT "largest ES swing" (which can't discriminate
  within a single refutation line — see Q-010). The order defines card semantics.
- **Milestone scope: full you-vs-opponent (A+B)** — detector + `tactic_motif` + `is_opponent`
  (derived) + Wilson you-vs-opponent comparison stats + frontend surface. This is *smaller*
  than the seed implies because opponent materialization and both-color PV capture are
  already done. Real remaining work: the **detector** (reimplement cook heuristics +
  validate, Q-011), the schema column + priority order, the comparison stats, the frontend.

## Open questions (see .planning/research/questions.md)

- **Q-010** — the motif priority order (card semantics).
- **Q-011** — cook-heuristic reimplementation validation set + accuracy bar (no AGPL copying).

## Key code references

- `scripts/remote_eval_worker.py` — `_eval_positions` / `pool.evaluate_nodes_with_pv`:
  produces `best_move` + `pv`.
- `app/services/flaws_service.py` — `classify_game_flaws`, `_run_all_moves_pass`
  (both colors), `_recompute_fen_map`: detector integration point.
- `scripts/backfill_flaws.py` — runs the same `classify_game_flaws`; the detector recompute path.
- `app/models/game_flaw.py` — add `tactic_motif` (+ `is_opponent` if stored rather than derived).
- `app/models/game_position.py` — `best_move`, `pv` columns (the data source).
