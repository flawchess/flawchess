---
id: SEED-108
status: dormant
planted: 2026-07-15
planted_during: v2.3 (post Phase 172 / SEED-106)
trigger_when: next analysis/insights milestone that can absorb a Maia-on-worker addition, or when gem-move game filtering becomes a wanted feature
scope: medium
supersedes: SEED-107 (client-side sweep fix — this backend approach makes the browser sweep unnecessary)
---

# SEED-108: Backend gem detection — Maia on remote workers, gems as a peer to flaws

## Why This Matters

The client-side background gem sweep (Phase 172 / SEED-106) is brittle — it is
starved by the always-on live analysis engines and disabled outright on
coarse-pointer devices, so gems only ever appear when the user dwells on a move
(see [[SEED-107]] for the root cause). It also computes ephemerally on one
device and never persists, so it can NEVER power a game-level "show me my
brilliant games" filter.

Moving gem detection into the backend full-game analysis pass fixes both: gems
become a first-class stored artifact, a **peer to blunder/mistake/tactic tags**,
surfaced through the same game-filter machinery that already exists for flaws.

## The Key Cost Insight

Two of the three ingredients already exist server-side, so this is far cheaper
than "we'd need Maia and workers" implies:

1. **Stockfish best-move + eval** is already computed and persisted per ply
   (`game_positions.best_move` / `eval_cp`; exposed as `EvalPoint.best_move`).
   Gem condition C2's "is best move" half is free.

2. **The runner-up eval (C2's margin) is already COMPUTED at nearly every ply**
   — `eval_drain.py:790` runs `evaluate_nodes_multipv2` on every engine target,
   returning `(cp, mate, best_move, pv, second_cp, second_mate, second_uci)`.
   Today the second-best data lands in `second_best_map` (`eval_drain.py:826`)
   but is consumed ONLY for flaw plies (`game_flaws` is mistakes+blunders only)
   and **discarded for every non-flaw ply**. Persisting it for candidate gem
   plies is pure plumbing — NO extra Stockfish `go`, no extra depth.

3. **Maia inference is the only genuinely new compute** — and it is tiny: only
   needed on plies where the played move == Stockfish best move AND the ply is
   past the opening book (a handful per game), at the player's pinned
   lichess-blitz-equivalent ELO (the existing `pinnedEloForMover` /
   `*_lichess_blitz ?? raw` rating-at-game-time rung — NOT the reactive slider).
   The real lift is adding onnxruntime + the Maia ONNX model to the remote
   worker image, not the per-game compute.

## Proposed Design

- **Store the Maia probability (a float), not a boolean.** Decouples the
  expensive inference from the cheap threshold decision — retuning the gem
  threshold becomes a constant change with ZERO re-analysis.
- **Store the runner-up margin (or `second_cp`) alongside it**, so BOTH gem
  conditions stay query-time tunable as constants:
  - C1 (human rarity): `maia_prob <= GEM_MAIA_MAX_PROB`
  - C2 (clearly best): `best_cp - second_cp >= MISTAKE_DROP`
- **New `game_gems` sibling table**, peer to `game_flaws`: one row per candidate
  ply — `(game_id FK, ply, maia_prob, best_cp, second_cp)` (final column set
  TBD). FK with `ondelete=CASCADE`, natural-key unique on `(game_id, ply)`.
  Sparse (only best-move-out-of-book plies), so a sibling table beats mostly-NULL
  columns on the high-cardinality `game_positions`.
- **Filter machinery**: reuse the existing flaw/tactic game-filter path so
  "games with gem moves" comes largely for free.

## Open Questions

- Which Maia model/rung on the backend, and does the nearest-rung result match
  the client's `perElo` curve closely enough that a game analyzed server-side
  and re-checked client-side agree? (Repro env: onnxruntime==1.20.1, Maia-3 has
  no history planes — see the engine self-execution memory.)
- Backfill: recompute for the existing game corpus, or go-forward only + lazy
  fill? (Mirror the tier-4 blob backfill lottery pattern rather than a
  deterministic sweep.)
- Does the current gem definition need the full `perElo` curve, or is the single
  pinned-rung probability sufficient to store? (User's call: pinned rung only.)
- Worker image size / cold-start impact of bundling the Maia ONNX model.

## Breadcrumbs

- `app/services/eval_drain.py:761-827` — the per-ply multipv=2 pass; `second_best_map` is where the runner-up margin already exists and is currently dropped for non-flaw plies.
- `app/services/eval_apply.py:1208-1316` — `_build_flaw_multipv2_blobs`; iterates flaws only (line 1246/1296) — the flaw-scoping that discards non-flaw second-best.
- `app/models/game_flaw.py` — the sibling-table + JSONB-blob pattern to mirror for `game_gems`.
- `app/models/game_position.py:159-172` — existing per-position eval columns (`eval_cp`, `best_move`, flaw-only `pv`); no second-best column today.
- `app/schemas/library.py:32-45` — `EvalPoint`; would gain gem data for the analysis board.
- `frontend/src/lib/gemMove.ts` — `classifyGem` C1/C2 definition to port server-side (thresholds `GEM_MAIA_MAX_PROB`, `MISTAKE_DROP`).
- `frontend/src/hooks/useMaiaEloDefault.ts` — the lichess-blitz-equivalent ELO pinning to reproduce server-side.
- `.planning/seeds/closed/SEED-106-background-gem-sweep-on-analysis.md` — the client sweep this replaces.
- `.planning/seeds/SEED-107-gem-sweep-starved-by-live-engines.md` — the tactical client-side fix this supersedes.

## Notes

If shipped, the client-side sweep (`useGemSweep.ts`) can be retired: the board
reads stored gem data instead of recomputing it, and SEED-107 becomes moot. The
live per-node dwell path could stay as a free-play (no stored analysis) fallback,
or be dropped too.
