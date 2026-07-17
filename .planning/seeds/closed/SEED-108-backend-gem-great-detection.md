---
id: SEED-108
status: closed
planted: 2026-07-15
updated: 2026-07-17 (implemented and shipped as milestone v2.4, Phases 174-176)
planted_during: v2.3 (post Phase 172 / SEED-106)
trigger_when: next analysis/insights milestone that can absorb backend Maia inference, or when gem/great game filtering becomes a wanted feature
scope: medium-large (full milestone: inference + storage, board integration, game filter, backfill)
supersedes: SEED-107 (client-side sweep fix — this backend approach makes the browser sweep unnecessary)
---

# SEED-108: Backend gem & great move detection — Maia at eval-apply, best-move rows as a peer to flaws

> **2026-07-16 rewrite.** The original seed proposed running Maia on the remote
> workers (old filename: `...-maia-on-workers.md`). A /gsd-explore session
> locked a different design: **inference runs on the backend at eval-apply
> time**, and the feature grows a second tier, **"Great" moves**. All decisions
> below are locked unless marked open.

## Why This Matters

The client-side background gem sweep (Phase 172 / SEED-106) is brittle — it is
starved by the always-on live analysis engines and disabled outright on
coarse-pointer devices, so gems only ever appear when the user dwells on a move
(see [[SEED-107]] for the root cause). It also computes ephemerally on one
device and never persists, so it can NEVER power a game-level "show me my
brilliant games" filter.

Moving detection into the backend full-game analysis pass fixes both: gems and
greats become first-class stored artifacts, **peers to blunder/mistake/tactic
tags**, surfaced through the same game-filter machinery that already exists for
flaws.

## Locked Decisions (2026-07-16 exploration)

### D-1: Two tiers, pure query-time thresholds — no hand-coded rules

- **Gem**: played == Stockfish best, out of book, `best_es - second_es >=
  MISTAKE_DROP` (C2), and `maia_prob <= GEM_MAIA_MAX_PROB` (0.20).
- **Great** (new): same C2 margin check, `maia_prob` in **(0.20, 0.50]**.
- Explicitly **rejected**: chess.com-style exclusion rules (trivial recaptures,
  forced sequences). Maia probability already encodes trivialness — an obvious
  recapture scores 80–95% and falls out of the band with zero rule code. The
  0.50 ceiling is a starting constant; calibrate against real per-game
  frequency once the pipeline exists (same playbook as Phase 172's 0.1 → 0.2
  retune).

### D-2: Candidate set — out-of-book best-move plies passing the inaccuracy floor

> **AMENDED 2026-07-16 at v2.4 milestone kickoff.** The original decision
> ("store ALL out-of-book best-move plies, no gate") was revised in discussion:
> candidate rows are now gated at analysis time by **`INACCURACY_DROP` (0.05)**
> — a row is stored (and Maia run) only when
> `best_es - second_es >= INACCURACY_DROP`, i.e. the runner-up move would have
> been at least an inaccuracy. Rationale: the near-zero-margin bulk of
> best-move plies (positions with several roughly equal moves) can never
> become gems/greats under any plausible retune, so storing them buys nothing;
> the realistic Gem/Great margin retune band (0.05–0.10+) stays fully
> query-time. Accepted trade-offs: loosening below 0.05 needs corpus
> re-analysis (unlikely direction), and the gate couples row storage to the
> shared flaw-threshold registry (a future `INACCURACY_DROP` retune leaves the
> corpus mixed-vintage below the new value). Gating at the full C2
> `MISTAKE_DROP` (0.10) remains rejected — it would bake the classification
> margin itself into the corpus.

Every out-of-book ply where the played move == Stockfish best AND the margin
passes the inaccuracy floor gets a stored row (`maia_prob` + second-best
eval). Both C1 band edges and the C2 margin (within [0.05, ∞)) stay retunable
forever with zero re-analysis.

### D-3: Inference host — backend at eval-apply, NOT the workers

Research findings that drove this (verified 2026-07-16):

- There are **no per-rung model files**. The frontend vendors a single Maia-3
  model (`frontend/public/maia/maia3_simplified.onnx`, ~44 MB, AGPL-3.0) that
  takes `elo_self`/`elo_oppo` as **float inputs**. "Which rung" is just which
  ELO value to pass — the pinned lichess-blitz-equivalent rating. Client's
  validated band is 1100–2000.
- Workers (`scripts/remote_eval_worker.py`, `Dockerfile.worker`) share the
  backend's `uv.lock` dependency tree, are NOT deployed by `bin/deploy.sh`,
  and are updated manually by operators — a worker protocol change has a
  fleet-coordination cost.
- Maia inference is tiny: 10–20 positions/game, milliseconds each after a
  one-time ~1–2 s InferenceSession load of the 44 MB model.

So: the backend loads the ONNX session once and scores candidate plies during
eval-apply, right where `second_best_map` already lands. Workers stay pure
Stockfish; no protocol change, no fleet coordination. Fallback if backend
RAM/CPU pressure materializes: move to workers later (protocol untouched until
proven necessary).

- New Python deps: `onnxruntime` (~19 MB wheel) + `numpy` (~16 MB), roughly
  110–140 MB installed incl. model. **Isolate behind a uv extra/dependency
  group** so the worker image stays lean.
- The board→tensor encoding (12 planes × 64 squares, policy vocab 4352,
  `frontend/src/lib/maiaEncoding.ts`, mirrored in
  `frontend/public/maia/maia-worker.js`) needs a Python port **with a parity
  check against client outputs**.

### D-4: Storage — neutral-named sibling table, floats not booleans

- Store **`maia_prob` (float) and the runner-up eval/margin**, never a
  gem/great boolean — classification is a query-time constants decision.
- New sibling table, peer to `game_flaws` — name it neutrally
  (**`game_best_moves`** or similar, NOT `game_gems`, since rows are
  candidates and the tier is decided at query time): `(game_id FK
  ondelete=CASCADE, ply, maia_prob, best_cp, second_cp)` (final column set at
  phase planning). Natural-key unique on `(game_id, ply)`. Sparse, so a
  sibling table beats mostly-NULL columns on high-cardinality
  `game_positions`.
- Maia ELO: the player's pinned lichess-blitz-equivalent rating at game time
  (the existing `pinnedEloForMover` / `*_lichess_blitz ?? raw` rung — NOT the
  reactive slider). Pinned rung only; no per-ELO curve stored.

### D-5: Milestone scope — all four chunks

1. **Backend inference + storage** — onnxruntime + Maia-3 in the backend,
   encoding port, new table, persist during eval-apply. Everything else
   depends on this.
2. **Board reads stored data** — `EvalPoint` gains gem/great data; retire
   `useGemSweep.ts` or demote it to a free-play (no stored analysis) fallback.
   The seed's old client/server parity question mostly dissolves: the board
   reads stored rows, so there is nothing to disagree with.
3. **Game filter UI** — "games with gems/greats" via the existing
   flaw/tactic game-filter machinery.
4. **Backfill** — existing corpus via the tier-4 lottery pattern
   (opportunistic global+random), not a deterministic sweep.

## The Key Cost Insight (unchanged)

Two of the three ingredients already exist server-side:

1. **Stockfish best-move + eval** is already computed and persisted per ply
   (`game_positions.best_move` / `eval_cp`; exposed as `EvalPoint.best_move`).
2. **The runner-up eval is already COMPUTED at nearly every ply** —
   `eval_drain.py:790` runs `evaluate_nodes_multipv2` on every engine target;
   `second_best_map` (`eval_drain.py:826`) is consumed only for flaw plies and
   discarded for every non-flaw ply. Persisting it for candidate rows is pure
   plumbing — no extra Stockfish `go`.
3. **Maia inference is the only genuinely new compute** — and it is tiny (see
   D-3).

## Open Questions (for phase planning, not blockers)

- Python encoding-port parity: how close must Python maia_prob match the
  client's (onnxruntime-web vs onnxruntime CPU, WebGPU nondeterminism)? Define
  a tolerance and a fixture-based parity test. (Repro env note:
  onnxruntime==1.20.1 was used in prior research; Maia-3 has no history
  planes — see the engine self-execution memory.)
- ELO clamping for pinned ratings outside Maia-3's validated 1100–2000 band.
- Calibrate the 0.50 Great ceiling (and re-check 0.20) against real per-game
  gem/great frequencies once the pipeline runs — greats should feel rare
  enough to mean something.
- Backfill lottery details: reuse the tier-4 blob lottery mechanism directly,
  or a parallel lottery keyed on missing best-move rows?
- Where exactly the ONNX session lives in the backend process (per-worker
  singleton? shared? lazy-load on first candidate?) given the 4 GB backend
  container and 6 Stockfish subprocesses.

## Breadcrumbs

- `app/services/eval_drain.py:761-827` — the per-ply multipv=2 pass; `second_best_map` is where the runner-up margin already exists and is currently dropped for non-flaw plies.
- `app/services/eval_apply.py:1208-1316` — `_build_flaw_multipv2_blobs`; iterates flaws only (line 1246/1296) — the flaw-scoping that discards non-flaw second-best. Eval-apply is also where backend Maia inference slots in (D-3).
- `app/models/game_flaw.py` — the sibling-table + JSONB-blob pattern to mirror for the new table.
- `app/models/game_position.py:159-172` — existing per-position eval columns (`eval_cp`, `best_move`, flaw-only `pv`); no second-best column today.
- `app/schemas/library.py:32-45` — `EvalPoint`; would gain gem/great data for the analysis board.
- `frontend/src/lib/gemMove.ts` — `classifyGem` C1/C2 definition to port server-side (thresholds `GEM_MAIA_MAX_PROB` = 0.2, `MISTAKE_DROP`).
- `frontend/src/lib/maiaEncoding.ts` + `frontend/public/maia/maia-worker.js` — the 12-plane encoding + inference glue to port to Python (with parity test).
- `frontend/public/maia/maia3_simplified.onnx` (~44 MB) + `frontend/public/maia/README.md` (SHA-256, provenance) — the model the backend will load.
- `frontend/src/hooks/useMaiaEloDefault.ts` — the lichess-blitz-equivalent ELO pinning to reproduce server-side.
- `.planning/seeds/closed/SEED-106-background-gem-sweep-on-analysis.md` — the client sweep this replaces.
- `.planning/seeds/SEED-107-gem-sweep-starved-by-live-engines.md` — the tactical client-side fix this supersedes.

## Notes

If shipped, the client-side sweep (`useGemSweep.ts`) can be retired: the board
reads stored gem/great data instead of recomputing it, and SEED-107 becomes
moot. The live per-node dwell path could stay as a free-play (no stored
analysis) fallback, or be dropped too.
