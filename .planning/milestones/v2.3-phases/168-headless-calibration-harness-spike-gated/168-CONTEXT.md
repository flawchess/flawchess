# Phase 168: Headless Calibration Harness (spike-gated) - Context

**Gathered:** 2026-07-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a **headless Node harness** that plays the FlawChess bot — the exact
provider-agnostic `selectBotMove` from Phase 166, imported unchanged via the
`@/` alias — against known-strength anchors across a **coarse (ELO × play-style)
grid**, and emits a strength-map TSV to `reports/data/`. First task is a
**feasibility/throughput spike** that gates building the full grid.

This phase owns ONLY the harness: Node-side engine providers, a bot-vs-anchor
game loop, the anchor move-choosers, the grid sweep, and TSV emission. It does
NOT modify `selectBotMove`/`mctsSearch`/the engine primitives (reuses them
verbatim — CAL-02), does NOT touch the play UI/clocks (Phase 169), and does NOT
do user-results curve fitting (deferred out of milestone per SEED-091 #3).

</domain>

<decisions>
## Implementation Decisions

### Area A — ONNX runtime & spike scope
- **D-01: Reuse the proven `onnxruntime-web` 1.27.0 WASM path** (single-thread,
  `ort.env.wasm.numThreads = 1`) + vendored **Stockfish 18.0.8** WASM-over-UCI,
  exactly as `scripts/gem-elo-calibration.mjs` already does headlessly in Node.
  **Lock `onnxruntime-web@1.27.0`** (already in `frontend/package.json`).
- **D-02: The CAL-03 / ROADMAP "lock `onnxruntime-node` version" wording is overridden — the runtime is web/WASM.**
  That text predates Phase 165 (v2.2, SEED-094), which already proved
  Maia ONNX runs headlessly in Node via `onnxruntime-web`. `onnxruntime-node`
  (native) is NOT adopted up front — it is the documented **fallback only** if
  the spike (D-03) shows WASM throughput makes the full grid infeasible. Read
  CAL-03 as "lock the ONNX runtime version"; the runtime is web/WASM.
- **D-03: The spike measures throughput, not feasibility.** Its go/no-go gate:
  play a small number of games (a handful) in the **most expensive cell**
  (`blend = 1`, full-Stockfish → `mctsSearch` + Stockfish grading every move),
  report **moves/sec** and **projected full-grid wall-clock**, and decide
  proceed vs fallback. Feasibility ("does Maia run headless in Node") is already
  answered — do not re-litigate it.

### Area B — Output & ELO estimate
- **D-04: Primary deliverable = the raw results matrix.** One row per
  `(bot-cell × anchor)`: games played, W/D/L, score (points/games), color split
  (as-White vs as-Black), plus run metadata (seed, per-move budget, git SHA,
  grid params). This is the honest, caveat-free artifact.
- **D-05: Secondary/advisory = a derived per-cell ELO estimate**, via standard
  anchor-logistic inversion: expected score `E = 1 / (1 + 10^((R_anchor −
  R_bot)/400))`, invert the observed score against each anchor's known rating
  and combine across anchors (weighted mean / least-squares) to a single point
  estimate. Carry the **SEED-091 caveat**: coarse, anchors are themselves
  approximate — an estimate, not a precise ELO. Anchor known ratings: raw-Maia
  argmax rung at ELO X → rating = X; Stockfish skill level → its published
  approximate Elo.
- **D-06: Follow the gem-elo TSV conventions** (`gem-elo-calibration.mjs`):
  main TSV + sibling `-summary.tsv`, timestamped filename, written to
  `reports/data/`, streamed durably (per-row append, so a mid-sweep crash keeps
  completed rows). User-results curve fitting stays **deferred** (SEED-091 #3).

### Area C — Grid & games-per-cell
- **D-07: Coarse grid, every axis CLI-configurable with cheap defaults.**
  - Bot grid: **ELO ∈ {1100, 1500, 1900}** × **blend ∈ {0, 0.5, 1.0}** (full-
    human, mid, full-Stockfish — captures both ends + middle; `TAU_MAX` is
    refinable from the mid results per Phase 166 D-05).
  - Anchors: **raw-Maia argmax rungs {1100, 1300, 1500, 1700, 1900}** + **low
    Stockfish skill levels {0, 3, 5}** (kept low — the bot is human-strength, so
    high SF levels would just crush it and yield no signal).
  - **~20 color-balanced games per matchup** to start (10 as White, 10 as
    Black), varied openings (D-09). A `--games-per-cell` knob; keep the first
    map cheap and expandable.
- **D-08: Bot ELO rungs must be members of `MAIA_ELO_LADDER`** (600–2600 step
  100), same validation as the gem-elo harness's `validateRungs`.

### Area D — Game mechanics
- **D-09: Vary openings (MANDATORY).** `blend = 1` is deterministic argmax
  (Phase 166 D-06) — from a single start position it replays the identical game,
  so every matchup MUST draw from a **fixed, seeded set of diverse balanced
  opening start FENs**, one per game, with **colors alternated**. Reproducible
  under `--seed`.
- **D-10: Bound cost with three cutoffs** — real terminal conditions (mate /
  stalemate / threefold / 50-move / insufficient material) **+** Stockfish-eval
  **adjudication** (|eval| ≥ ~600 cp sustained → adjudicate the result) **+** a
  hard **ply cap** (adjudicate by final eval / draw). Reuse the already-spawned
  vendored Stockfish for adjudication; all thresholds are named constants.
- **D-11: Per-move search budget is a FIXED harness constant, constant across the whole grid.**
  So measured differences reflect ELO/blend, not budget. Mirror
  the app's defaults (`FLAWCHESS_ENGINE_MAX_NODES` / `FLAWCHESS_ENGINE_MAX_PLIES`
  from `useFlawChessEngine.ts`). The harness has **no clock** — clock-derived
  budgets are Phase 169's concern, explicitly not here.

### Claude's Discretion
- User selected **"You decide"** on the discuss menu — all four areas above were
  decided by Claude and are open to the user's edit before planning.
- Left to the planner/researcher: exact opening-book source (curated FEN list vs
  sampling early positions from the lichess/kaggle FENs the gem-elo harness
  already uses) and its size; exact adjudication cp threshold and sustain-ply
  count; ply-cap value; the anchor→Stockfish-skill-level Elo mapping table;
  whether shared scaffolding (alias hook, Maia session loader, Stockfish UCI
  wrapper, PRNG, TSV writer) is refactored into `scripts/lib/` or duplicated;
  exact new file paths under `scripts/`; how the Node `policy`/`grade` providers
  wrap the Maia session + Stockfish (the interesting reuse work).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase / milestone scope
- `.planning/ROADMAP.md` §"Phase 168" — goal + the 3 success criteria (SC1 spike,
  SC2 exact-`selectBotMove` reuse, SC3 grid→TSV).
- `.planning/REQUIREMENTS.md` — CAL-01 (grid vs anchors → TSV), CAL-02 (exact
  `selectBotMove` reuse via `@/`), CAL-03 (spike, ONNX version lock — see D-02
  for the runtime correction).
- `.planning/seeds/SEED-091-flawchess-bot-play-milestone.md` §"Calibration"
  (decision #3) — anchor harness in-milestone, self-play-only ELO unreliable,
  user-results fitting deferred; the ±100–150 conversion-error caveat.

### The primary reusable prior-art harness (READ FIRST)
- `scripts/gem-elo-calibration.mjs` — the Phase 165 headless harness that ALREADY
  runs Maia (`onnxruntime-web` WASM) + Stockfish (WASM/UCI) in Node via the `@/`
  hook and streams TSV to `reports/data/`. Source of nearly all scaffolding this
  phase reuses: `createMaiaSession`, `spawnStockfish`/`StockfishUciEngine`,
  `mulberry32`, streaming TSV writer, CLI arg validation, WR-01 durability.
- `scripts/lib/frontend-alias-hook.mjs` — the `@/` alias resolve hook; run the
  harness with `node --import ./scripts/lib/frontend-alias-hook.mjs …`.
- `scripts/lib/gem-parity.check.mjs` — the no-reimplementation-drift parity
  pattern (import live frontend fns, never re-derive) — mirror for CAL-02.

### Engine code reused UNCHANGED (CAL-02)
- `frontend/src/lib/engine/selectBotMove.ts` — the function the harness imports
  and runs verbatim (`selectBotMove(fen, settings, deps, signal?)`).
- `frontend/src/lib/engine/types.ts` — `EngineProviders` (`policy(fen,elo,side)`,
  `grade(fen,candidateUcis)`), `SearchBudget`, `RankedLine`. The Node providers
  the harness builds must satisfy these exactly.
- `frontend/src/lib/engine/mctsSearch.ts` — the search `selectBotMove` runs for
  `blend > 0` (default `deps.search`).
- `frontend/src/lib/engine/maiaQueue.ts` — reference `EngineProviders.policy`
  impl (uses `maskAndSoftmax`); the harness builds a Node equivalent off the
  shared Maia session.
- `frontend/src/lib/maiaEncoding.ts` — `encodeBoard`, `maskAndSoftmax`,
  `eloToInput`, `MAIA_ELO_LADDER`, vocab/plane constants (the gem-elo harness
  already imports these for headless inference).
- `frontend/src/hooks/useFlawChessEngine.ts` — reference wiring of providers +
  `SearchBudget` (`FLAWCHESS_ENGINE_MAX_NODES`/`_MAX_PLIES`) into `mctsSearch`;
  D-11 mirrors these budget defaults.

### Phase 166 decisions the harness depends on
- `.planning/phases/166-bot-move-selection-core-selectbotmove/166-CONTEXT.md` —
  D-07/D-08 (`deps` reuse seam, `search` injectable), D-10/D-11 (injected seeded
  `mulberry32` rng), D-06 (`blend=1` deterministic argmax → the D-09 opening-
  variety requirement).

### Memory / prior-art notes
- `project_headless_stockfish_wasm_verification` — vendored Stockfish WASM runs
  as a UCI CLI in Node (copy to `.cjs`, rename `.wasm` to match basename);
  `searchmoves`/MultiPV verified; illegal searchmoves silently dropped.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/gem-elo-calibration.mjs` is ~90% of the harness plumbing already:
  Maia WASM session + batched forward pass, `StockfishUciEngine` UCI wrapper
  with `stopAndSync` recovery, `mulberry32` PRNG, streaming durable TSV writer,
  strict CLI flag validation. New work is the **game loop + anchors + providers**,
  not the engine bring-up.
- Vendored Stockfish 18.0.8 supports `setoption name Skill Level value N`
  (confirmed present in `stockfish-18-lite-single.js`) → Stockfish-skill anchors
  need no new engine, just a skill-level option on the same spawned process.
- `EngineProviders.grade(fen, candidateUcis)` can be built from the gem-elo
  harness's `gradePosition` (MultiPV grade of legal moves), filtered to the
  requested candidate UCIs, white-POV cp.

### Established Patterns
- **No-reimplementation discipline (CAL-02 = gem-elo's D-03):** import every
  gem/eval/selection fn from live frontend source via `@/`; the harness re-derives
  nothing. A parity check guards drift.
- Engine core speaks **UCI everywhere**; side-to-move is the FEN `'w'/'b'`
  literal. Providers and the game loop follow the same convention.
- Durable per-row TSV streaming (WR-01): open file + header up front, append each
  completed row, so a killed multi-hour sweep keeps its work.

### Integration Points
- The `deps` boundary from Phase 166 is the reuse seam: the harness supplies
  Node `policy` (Maia WASM session) + `grade` (Stockfish UCI) providers + a
  seeded `mulberry32` rng, and uses the default `mctsSearch` — identical wiring
  to the app, so measured strength = what users play against.
- Anchors are just alternative move-choosers sharing the same loaded Maia session
  / spawned Stockfish: raw-Maia argmax = one inference + argmax of `maskAndSoftmax`
  policy; Stockfish-skill = `go` under a `Skill Level` option.

</code_context>

<specifics>
## Specific Ideas

- The strength map is the "engine test bench" Adrian wanted (SEED-091 #3): its
  point is to measure the *unknown real strength* of the (ELO × play-style)
  engine, since the ELO slider only conditions Maia's candidates and the blend
  slider's strength impact is unmeasured.
- Keep the first grid deliberately cheap and coarse; correctness and the
  reuse/parity discipline matter more than grid resolution. Finer grids and more
  games are a re-run with different CLI flags, not a code change.

</specifics>

<deferred>
## Deferred Ideas

- **User-results strength calibration** (player rating vs result vs bot config
  curve fitting; relabel bots with measured ELO) — explicitly a later milestone
  per SEED-091 #3, needs post-launch data volume.
- **`onnxruntime-node` native runtime** — not adopted; only revisited if the D-03
  spike shows the WASM path can't finish the grid in a reasonable wall-clock.

None outside phase scope surfaced during discussion.

</deferred>

---

*Phase: 168-headless-calibration-harness-spike-gated*
*Context gathered: 2026-07-11*
