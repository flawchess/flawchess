# Phase 168: Headless Calibration Harness (spike-gated) - Research

**Researched:** 2026-07-11
**Domain:** Headless Node engine-vs-engine self-play harness (Maia ONNX WASM + Stockfish WASM/UCI), reusing the app's own `selectBotMove`/`mctsSearch` search core
**Confidence:** HIGH (nearly everything is direct-from-codebase reuse; the two genuinely new/uncertain areas — Stockfish skill-level Elo mapping and grid throughput — are flagged LOW/MEDIUM and are exactly what CAL-03's spike exists to de-risk)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Area A — ONNX runtime & spike scope**
- D-01: Reuse the proven `onnxruntime-web` 1.27.0 WASM path (single-thread, `ort.env.wasm.numThreads = 1`) + vendored Stockfish 18.0.8 WASM-over-UCI, exactly as `scripts/gem-elo-calibration.mjs` already does headlessly in Node. Lock `onnxruntime-web@1.27.0` (already in `frontend/package.json`).
- D-02: This overrides CAL-03 / ROADMAP wording "lock the `onnxruntime-node` version". That text predates Phase 165 (v2.2, SEED-094), which already proved Maia ONNX runs headlessly in Node via `onnxruntime-web`. `onnxruntime-node` (native) is NOT adopted up front — it is the documented fallback only if the spike (D-03) shows WASM throughput makes the full grid infeasible. Read CAL-03 as "lock the ONNX runtime version"; the runtime is web/WASM.
- D-03: The spike measures throughput, not feasibility. Its go/no-go gate: play a small number of games (a handful) in the most expensive cell (`blend = 1`, full-Stockfish → `mctsSearch` + Stockfish grading every move), report moves/sec and projected full-grid wall-clock, and decide proceed vs fallback. Feasibility ("does Maia run headless in Node") is already answered — do not re-litigate it.

**Area B — Output & ELO estimate**
- D-04: Primary deliverable = the raw results matrix. One row per (bot-cell × anchor): games played, W/D/L, score (points/games), color split (as-White vs as-Black), plus run metadata (seed, per-move budget, git SHA, grid params). This is the honest, caveat-free artifact.
- D-05: Secondary/advisory = a derived per-cell ELO estimate, via standard anchor-logistic inversion: expected score `E = 1 / (1 + 10^((R_anchor − R_bot)/400))`, invert the observed score against each anchor's known rating and combine across anchors (weighted mean / least-squares) to a single point estimate. Carry the SEED-091 caveat: coarse, anchors are themselves approximate — an estimate, not a precise ELO. Anchor known ratings: raw-Maia argmax rung at ELO X → rating = X; Stockfish skill level → its published approximate Elo.
- D-06: Follow the gem-elo TSV conventions (`gem-elo-calibration.mjs`): main TSV + sibling `-summary.tsv`, timestamped filename, written to `reports/data/`, streamed durably (per-row append, so a mid-sweep crash keeps completed rows). User-results curve fitting stays deferred (SEED-091 #3).

**Area C — Grid & games-per-cell**
- D-07: Coarse grid, every axis CLI-configurable with cheap defaults.
  - Bot grid: ELO ∈ {1100, 1500, 1900} × blend ∈ {0, 0.5, 1.0} (full-human, mid, full-Stockfish — captures both ends + middle; `TAU_MAX` is refinable from the mid results per Phase 166 D-05).
  - Anchors: raw-Maia argmax rungs {1100, 1300, 1500, 1700, 1900} + low Stockfish skill levels {0, 3, 5} (kept low — the bot is human-strength, so high SF levels would just crush it and yield no signal).
  - ~20 color-balanced games per matchup to start (10 as White, 10 as Black), varied openings (D-09). A `--games-per-cell` knob; keep the first map cheap and expandable.
- D-08: Bot ELO rungs must be members of `MAIA_ELO_LADDER` (600–2600 step 100), same validation as the gem-elo harness's `validateRungs`.

**Area D — Game mechanics**
- D-09: Vary openings (MANDATORY). `blend = 1` is deterministic argmax (Phase 166 D-06) — from a single start position it replays the identical game, so every matchup MUST draw from a fixed, seeded set of diverse balanced opening start FENs, one per game, with colors alternated. Reproducible under `--seed`.
- D-10: Bound cost with three cutoffs — real terminal conditions (mate / stalemate / threefold / 50-move / insufficient material) + Stockfish-eval adjudication (|eval| ≥ ~600 cp sustained → adjudicate the result) + a hard ply cap (adjudicate by final eval / draw). Reuse the already-spawned vendored Stockfish for adjudication; all thresholds are named constants.
- D-11: Per-move search budget is a FIXED harness constant, constant across the whole grid, so measured differences reflect ELO/blend, not budget. Mirror the app's defaults (`FLAWCHESS_ENGINE_MAX_NODES` / `FLAWCHESS_ENGINE_MAX_PLIES` from `useFlawChessEngine.ts`). The harness has no clock — clock-derived budgets are Phase 169's concern, explicitly not here.

### Claude's Discretion
- User selected "You decide" on the discuss menu — all four areas above were decided by Claude and are open to the user's edit before planning.
- Left to the planner/researcher: exact opening-book source (curated FEN list vs sampling early positions from the lichess/kaggle FENs the gem-elo harness already uses) and its size; exact adjudication cp threshold and sustain-ply count; ply-cap value; the anchor→Stockfish-skill-level Elo mapping table; whether shared scaffolding (alias hook, Maia session loader, Stockfish UCI wrapper, PRNG, TSV writer) is refactored into `scripts/lib/` or duplicated; exact new file paths under `scripts/`; how the Node `policy`/`grade` providers wrap the Maia session + Stockfish (the interesting reuse work).

### Deferred Ideas (OUT OF SCOPE)
- User-results strength calibration (player rating vs result vs bot config curve fitting; relabel bots with measured ELO) — explicitly a later milestone per SEED-091 #3, needs post-launch data volume.
- `onnxruntime-node` native runtime — not adopted; only revisited if the D-03 spike shows the WASM path can't finish the grid in a reasonable wall-clock.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CAL-01 | A headless Node harness plays the bot against known-strength anchors (raw Maia argmax rungs 1100–1900 + Stockfish skill levels) across a coarse (ELO × play-style) grid and emits a strength map as TSV in `reports/data/`. | Architecture Patterns (game loop + grid sweep), Code Examples, Standard Stack — everything needed already exists in `scripts/gem-elo-calibration.mjs` + `frontend/src/lib/engine/*`; only the game loop, anchor choosers, and grid orchestration are new. |
| CAL-02 | The harness reuses the exact same provider-agnostic `selectBotMove` move-selection code the app uses (via the `@/` alias hook), so the measured strength reflects the code users actually play against. | `selectBotMove`/`mctsSearch` signatures below; `EngineProviders` contract; the parity-check pattern (`gem-parity.check.mjs`) mirrored as a new `calibration-parity.check.mjs`. |
| CAL-03 | A feasibility spike confirms Maia ONNX inference runs headlessly in Node at harness-viable throughput (locks the ONNX runtime version — D-02 corrects "onnxruntime-node" to "onnxruntime-web") before the full grid is built. | Validation Architecture (spike throughput report), Common Pitfalls (concurrency=1 single-Stockfish-process bottleneck is the likely throughput lever, not ONNX runtime choice). |

</phase_requirements>

## Summary

This phase is almost entirely composition over code that already exists and already runs headlessly in Node. Three things are proven prior art, verified by direct file read in this session:

1. **`scripts/gem-elo-calibration.mjs`** (Phase 165) already runs `onnxruntime-web@1.27.0` WASM (single-thread) + vendored Stockfish 18.0.8 WASM-over-UCI in Node, imports live frontend TS via the `@/` alias hook, and streams a durable per-row TSV to `reports/data/`. It supplies ~90% of the harness's plumbing verbatim: `createMaiaSession`, `StockfishUciEngine`/`spawnStockfish` (with the `.cjs`/`.wasm` basename-copy trick), `mulberry32`, `validateRungs`, the CLI-flag validation helpers, and the TSV/summary-writer conventions.
2. **`frontend/src/lib/engine/selectBotMove.ts`** (Phase 166) is the frozen, provider-agnostic move-selection function this harness must import unchanged: `selectBotMove(fen, settings, deps, signal?): Promise<string>`, where `settings = { elo, blend, budget }` and `deps = { policy, grade, rng, search? }` (the exact `EngineProviders` shape). `deps.search` defaults to the real `mctsSearch`, so the harness doesn't even need to inject it — just supply Node-side `policy`/`grade` + a seeded `mulberry32` rng, exactly the app's own reuse seam (Phase 166 D-08).
3. **`frontend/src/lib/engine/types.ts`**'s `EngineProviders` contract (`policy(fen, elo, side)`, `grade(fen, candidateUcis)`) is exactly what the Node providers must satisfy — and the pieces to build them (Maia forward pass, Stockfish MultiPV search) already exist in `gem-elo-calibration.mjs`, just wired to a different (SAN-keyed, all-legal-moves) shape that needs re-adapting to the UCI-keyed, candidate-restricted contract (see Pitfall 1 below — this is the one genuinely new piece of engineering).

**Primary recommendation:** Build one new harness file (`scripts/calibration-harness.mjs`) plus a small `scripts/lib/` library (Node `EngineProviders` adapter, anchor move-choosers, opening book, calibration parity check) refactored out of `gem-elo-calibration.mjs`'s reusable primitives — do not duplicate the Maia-session/Stockfish-UCI bring-up a second time. Run the D-03 spike as a tiny invocation of the SAME harness code (`--elo 1900 --blends 1 --anchors sf5 --games-per-cell 4`) with built-in throughput instrumentation (elapsed-time / total-moves-played), rather than a separate throwaway script — this means "spike" is a CLI-flag-driven code path, not a distinct artifact to gate later work on.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Move selection (`selectBotMove`, `mctsSearch`) | Shared library (frontend/src/lib, imported via `@/`) | — | Frozen, provider-agnostic; both the browser (Phase 169) and this Node harness import the identical function — CAL-02's whole point. |
| Maia policy inference | Node script (harness) | Shared library (`maiaEncoding.ts` encode/decode helpers) | Model + tensor math live in `maiaEncoding.ts`; the Node harness owns the ORT session lifecycle (load once, reuse) since there's no Worker/React tier in a CLI script. |
| Stockfish grading + adjudication | Node script (harness) | — | UCI process I/O is inherently a Node/OS-process concern; no browser Worker equivalent exists here. |
| Game loop, anchors, grid sweep, TSV emission | Node script (harness) | — | New code, owned entirely by this phase; no existing tier does bot-vs-anchor self-play. |
| CLI argument parsing/validation | Node script (harness) | — | Mirrors `gem-elo-calibration.mjs`'s `parseArgs`/`requireFlagValue` pattern; no framework, plain `process.argv` parsing. |
| Opening-book source data | Node script / static module (`scripts/lib/`) | — | A small, curated, versioned constant — not a database or generated artifact. |

## Standard Stack

### Core (all already installed — zero new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `onnxruntime-web` | 1.27.0 [VERIFIED: npm registry, matches `frontend/package.json`] | Maia-3 ONNX inference, WASM backend, single-thread | Already the locked runtime (D-01/D-02); confirmed headless-in-Node prior art in `gem-elo-calibration.mjs`. |
| `stockfish` (vendored `stockfish-18-lite-single.{js,wasm}`) | 18.0.8 [VERIFIED: npm registry, matches `frontend/package.json`, binary confirmed to expose `Skill Level`/`UCI_LimitStrength`/`UCI_Elo` UCI options] | Move grading (MultiPV), anchor Stockfish-skill moves, adjudication eval | Same binary as the app; UCI-over-stdio proven in Node (`project_headless_stockfish_wasm_verification` memory + this session's `gem-elo-calibration.mjs` read). |
| `chess.js` | 1.4.0 [VERIFIED: npm registry, matches `frontend/package.json`] | Legality, SAN↔UCI, terminal-state detection (`isGameOver`/`isCheckmate`/`isStalemate`/`isThreefoldRepetition`/`isInsufficientMaterial`) | Same library the frontend uses for the identical checks (`treeCommon.ts`'s `terminalValue` calls exactly these methods) — the harness's own game-over check should call them directly, not re-derive termination logic. |

**No new `npm install` is required for this phase.** Every runtime dependency is already present in `frontend/node_modules` and resolved from `scripts/*.mjs` via the existing `resolveFrontendModule()` recipe (`createRequire(frontend/package.json)` + dynamic `import()` — see `gem-elo-calibration.mjs` lines 375-379) or the `@/` alias hook.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Node built-ins (`node:child_process`, `node:readline`, `node:fs`, `node:module`) | Node 24.14.0 [VERIFIED: local `node --version`] | Process spawning, streaming I/O, TSV writing, the `@/` resolve hook | No new packages — the entire harness is Node-builtin + the two vendored engines. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `onnxruntime-web` WASM | `onnxruntime-node` (native N-API bindings) | Faster, but NOT adopted per D-01/D-02 — fallback only if the spike shows WASM throughput is inadequate. Would require a new dependency + platform-specific native build, which is exactly the extra risk the locked decision avoids until proven necessary. |
| Curated static opening-book FEN list | Sample early-game positions from the gem-elo harness's Kaggle CSV (`temp/brilliants_no_stalemates.csv`) | That CSV is "brilliant tactical moves" (mid/endgame positions with a computed brilliancy `score`, not opening theory) — wrong semantic source for "diverse balanced opening starts." A hand-curated list of ~20-30 known-balanced opening lines is simpler, license-clean (same "written from confirmed facts, not copied" discipline as `maiaEncoding.ts`), and trivially reviewable. See Open Question 1 below for the concrete recommendation. |
| Weighted-mean anchor-ELO combination | Full nonlinear least-squares fit across all anchors simultaneously | Least-squares is more statistically "correct" but requires iterative solving (the logistic curve is nonlinear in `R_bot`); a per-anchor closed-form inversion + weighted mean is simpler to implement correctly in a spike-gated harness and is honestly labeled "advisory" per D-05's own caveat. Recommend weighted mean now; least-squares is a natural follow-up refinement, not a blocker. |

**Installation:**
```bash
# No new packages. Verify existing versions match what's already locked:
cd frontend && npm view onnxruntime-web version && npm view chess.js version && npm view stockfish version
```

## Package Legitimacy Audit

**Not applicable — this phase installs zero new packages.** All three runtime dependencies (`onnxruntime-web@1.27.0`, `stockfish@18.0.8` vendored binary, `chess.js@1.4.0`) are already installed, already used in production frontend code, and already proven headless-in-Node by the Phase 165 `gem-elo-calibration.mjs` prior art. No `package-legitimacy check` run was needed since no new package names are being introduced.

## Architecture Patterns

### System Architecture Diagram

```
CLI invocation
  node --import ./scripts/lib/frontend-alias-hook.mjs scripts/calibration-harness.mjs [flags]
        │
        ▼
┌─────────────────────────── Setup (once per run) ───────────────────────────┐
│ 1. Parse + validate CLI flags (grid axes, games-per-cell, seed, out-dir)   │
│ 2. validateRungs(bot ELOs) against MAIA_ELO_LADDER (@/lib/maiaEncoding)    │
│ 3. Load Maia ORT session ONCE (createMaiaSession, reused across ALL games) │
│ 4. Spawn ONE Stockfish UCI process (spawnStockfish, reused across ALL     │
│    games/anchors/adjudication — see Pitfall 2 for the shared-process      │
│    option-reset discipline this requires)                                 │
│ 5. Open main TSV + summary TSV writers (durable per-row append, D-06)     │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────── Grid sweep: for each (elo × blend) bot-cell ───────────┐
│   for each anchor (5 raw-Maia rungs + 3 SF skill levels):                  │
│     for each game (games-per-cell, alternating color, cycling opening-book)│
│                                                                             │
│       ┌───────────────── One game's move loop ─────────────────┐          │
│       │  side to move == bot?                                  │          │
│       │    → selectBotMove(fen, settings, nodeDeps) [@/ import] │          │
│       │  side to move == anchor?                                │          │
│       │    → raw-Maia argmax: one policy() call, argmax(probs)  │          │
│       │    → OR Stockfish-skill: setoption Skill Level N; go    │          │
│       │  apply UCI move (chess.js) → check terminal conditions: │          │
│       │    chess.js isGameOver()/isCheckmate()/isStalemate()/   │          │
│       │    isThreefoldRepetition()/isInsufficientMaterial()     │          │
│       │    OR |Stockfish eval| >= ADJUDICATION_CP_THRESHOLD     │          │
│       │      sustained N plies OR ply >= PLY_CAP (D-10)         │          │
│       └──────────────────────────────────────────────────────────┘        │
│       → tally result (W/D/L, color) into the (bot-cell × anchor) row       │
│       → tsvWriter.writeRow(...) after EVERY completed game (durability)    │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────── Post-processing (per bot-cell, across anchors) ───────────┐
│  invert each anchor's observed score → per-anchor Elo estimate            │
│  (E = 1/(1+10^((R_anchor − R_bot)/400)) solved for R_bot)                 │
│  weighted-mean combine → one advisory Elo estimate per bot-cell (D-05)    │
│  write summary TSV (D-06)                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
scripts/
├── calibration-harness.mjs         # NEW — main orchestrator: CLI parsing, grid loop, game loop, TSV emission
├── gem-elo-calibration.mjs         # UNCHANGED (Phase 165) — sibling harness, do not touch
└── lib/
    ├── frontend-alias-hook.mjs     # UNCHANGED (Phase 165) — `@/` resolve hook, reused verbatim
    ├── gem-parity.check.mjs        # UNCHANGED (Phase 165) — sibling parity check, do not touch
    ├── calibration-parity.check.mjs  # NEW — mirrors gem-parity.check.mjs's pattern: imports
    │                                  #        selectBotMove/mctsSearch/maskAndSoftmax live and
    │                                  #        asserts wiring against hand-derived fixtures
    ├── node-engine-providers.mjs   # NEW — Maia session loader + Stockfish UCI wrapper, REFACTORED
    │                                  #        out of gem-elo-calibration.mjs's createMaiaSession/
    │                                  #        StockfishUciEngine/spawnStockfish (see Recommendation
    │                                  #        below on shared vs duplicated scaffolding)
    ├── calibration-anchors.mjs     # NEW — raw-Maia-argmax and Stockfish-skill-level move choosers
    └── calibration-openings.mjs    # NEW — curated static opening-book FEN list (Open Question 1)
```

**Recommendation on shared vs duplicated scaffolding (explicitly left to the planner by CONTEXT.md):** refactor `createMaiaSession`, `StockfishUciEngine`/`spawnStockfish`, and `resolveFrontendModule` OUT of `gem-elo-calibration.mjs` into `scripts/lib/node-engine-providers.mjs`, then have BOTH `gem-elo-calibration.mjs` and the new `calibration-harness.mjs` import from there. Reasons to refactor rather than duplicate:
- These functions are verbatim-identical bring-up code (session load, WASM engine spawn via the `.cjs`/`.wasm` basename-copy trick) — duplicating them is the exact "hand-rolled reimplementation" anti-pattern this codebase's CAL-02 discipline exists to prevent, just one directory up from the frontend/`@/` boundary instead of across it.
- `gem-elo-calibration.mjs`'s `gradePosition`/`maiaProbsForPosition` are NOT reusable as-is for this phase (different contract shape — see Pitfall 1) — only the process/session bring-up (`spawnStockfish`, `createMaiaSession`) is a clean, contract-neutral extraction.
- Low risk: `gem-elo-calibration.mjs` is a Phase 165-frozen sibling script this phase is told not to touch — extracting its bring-up helpers into a shared lib module and re-importing them back is a mechanical, behavior-preserving refactor (verify with the existing gem-elo smoke run before/after).

### Pattern 1: `selectBotMove` reuse — the harness supplies `deps`, nothing else

**What:** The harness's ENTIRE interaction with the bot's move selection is constructing one `BotMoveDeps` object and calling `selectBotMove(fen, settings, deps)`. No search/sampling/argmax logic is ever reimplemented.

**Signature to call exactly** (`frontend/src/lib/engine/selectBotMove.ts` lines 97-102):
```typescript
export async function selectBotMove(
  fen: string,
  settings: BotSettings,          // { elo, blend, budget: Omit<SearchBudget,'elo'|'policyTemperature'> }
  deps: BotMoveDeps,               // EngineProviders & { rng, search? }
  signal: AbortSignal = NEVER_ABORT_SIGNAL,
): Promise<string>
```

**Node call site (harness game loop, per bot move):**
```javascript
// Source: mirrors frontend/src/hooks/useFlawChessEngine.ts's budget construction
// (lines 220-233), imported live via the @/ alias hook — no reimplementation.
import { selectBotMove } from '@/lib/engine/selectBotMove';

const uci = await selectBotMove(
  fen,
  {
    elo: botElo,             // one of D-07's {1100, 1500, 1900}
    blend: botBlend,         // one of D-07's {0, 0.5, 1.0}
    budget: {
      maxNodes: FLAWCHESS_ENGINE_MAX_NODES,   // mirror 400 (useFlawChessEngine.ts line 39)
      maxPlies: FLAWCHESS_ENGINE_MAX_PLIES,   // mirror 8   (useFlawChessEngine.ts line 45)
      concurrency: 1,        // harness constant — see Pitfall 2 (single shared Stockfish process)
    },
  },
  { policy: nodePolicy, grade: nodeGrade, rng: mulberry32(gameSeed) },
);
```
`deps.search` is omitted — `selectBotMove` defaults it to the real `mctsSearch` import (Phase 166 D-08), so the harness gets the IDENTICAL search the app runs, with zero extra wiring.

### Pattern 2: Node `policy()` provider — a single batched Maia forward pass, no queue needed

**What:** Unlike the browser's `maiaQueue.ts` (which needs an async FIFO queue because multiple concurrent callers share one Worker), the harness only ever has ONE `policy()` call in flight at a time (because `SearchBudget.concurrency = 1` — see Pitfall 2), so the Node provider can be a direct, unqueued async function.

```javascript
// Adapts gem-elo-calibration.mjs's maiaProbsForPosition (single-ELO, single-batch
// variant) into the EngineProviders.policy(fen, elo, side) contract — UCI-keyed,
// not SAN-keyed (mctsSearch/selectBotMove require UCI throughout, per types.ts D-08).
import { sanToUci } from '@/lib/sanToSquares';
import { encodeBoard, maskAndSoftmax, eloToInput, NUM_SQUARES, PLANES_PER_SQUARE, POLICY_VOCAB_SIZE } from '@/lib/maiaEncoding';

async function nodePolicy(fen, elo, side) {
  void side; // implicit in fen's own 'w'/'b' field (D-08), same convention as maiaQueue.ts
  const tokens = encodeBoard(fen);
  const feeds = {
    tokens: new ort.Tensor('float32', tokens, [1, NUM_SQUARES, PLANES_PER_SQUARE]),
    elo_self: new ort.Tensor('float32', Float32Array.of(eloToInput(elo)), [1]),
    elo_oppo: new ort.Tensor('float32', Float32Array.of(eloToInput(elo)), [1]), // symmetric — BOT-03
  };
  const result = await session.run(feeds);
  const sanProbs = maskAndSoftmax(result.logits_move.data.slice(0, POLICY_VOCAB_SIZE), fen);
  const uciProbs = {};
  for (const [san, prob] of Object.entries(sanProbs)) {
    const uci = sanToUci(fen, san);
    if (uci !== null) uciProbs[uci] = prob;
  }
  return uciProbs;
}
```

### Pattern 3: Node `grade()` provider — NOT `gem-elo`'s `gradePosition` (Pitfall 1 — read before implementing)

**What:** `EngineProviders.grade(fen, candidateUcis)` must return a UCI-keyed `Map<string, MoveGrade>` where `MoveGrade = { evalCp, evalMate, depth, pv? }` for EXACTLY the candidate moves `mctsSearch` asks about (via `searchmoves`), NOT a full-legal-move MultiPV sweep. This is a genuinely different shape from `gem-elo-calibration.mjs`'s `gradePosition` (which grades ALL legal moves, keys by SAN, and omits `depth`). The correct pattern to mirror is `frontend/src/lib/engine/workerPool.ts`'s `sendGo`/`handleLine` (lines 210-219, 249-266):

```javascript
// Source: mirrors workerPool.ts's sendGo/handleLine pattern (UCI-keyed, searchmoves-restricted,
// depth-field-carrying), NOT gem-elo-calibration.mjs's gradePosition (SAN-keyed, all-legal-moves).
async function nodeGrade(fen, candidateUcis) {
  if (candidateUcis.length === 0) return new Map(); // mirror workerPool.ts WR-05
  const whitePovSign = fen.split(' ')[1] === 'b' ? -1 : 1;
  const grades = new Map();
  const off = stockfish.onLine((line) => {
    if (!line.startsWith('info ')) return;
    const parsed = parseInfoLine(line); // @/hooks/uciParser — imported, not reimplemented
    if (parsed === null || parsed.bound !== 'exact') return;
    const uci = parsed.pv[0];
    if (uci === undefined) return;
    grades.set(uci, {
      evalCp: parsed.scoreCp !== null ? parsed.scoreCp * whitePovSign : null,
      evalMate: parsed.scoreMate !== null ? parsed.scoreMate * whitePovSign : null,
      depth: parsed.depth,
    });
  });
  stockfish.send('setoption name Skill Level value 20');       // Pitfall 2: reset to full strength
  stockfish.send('setoption name UCI_LimitStrength value false');
  stockfish.send(`setoption name MultiPV value ${candidateUcis.length}`);
  stockfish.send(`position fen ${fen}`);
  stockfish.send(`go depth ${GRADING_TARGET_DEPTH} searchmoves ${candidateUcis.join(' ')} movetime ${GRADING_MOVETIME_SAFETY_CAP_MS}`);
  try {
    await stockfish.waitFor((line) => line.startsWith('bestmove'), GRADING_MOVETIME_SAFETY_CAP_MS + SLACK_MS);
  } finally {
    off();
  }
  return grades;
}
```
`GRADING_TARGET_DEPTH = 14` and `GRADING_MOVETIME_SAFETY_CAP_MS = 2500` are the app's own constants (`frontend/src/lib/engine/workerPool.ts` lines 36, 39) — mirror them as fixed harness constants per D-11.

### Pattern 4: Anchor move-choosers (raw-Maia argmax, Stockfish-skill)

```javascript
// Raw-Maia argmax anchor: ONE inference (shares the same session as nodePolicy),
// argmax instead of weighted sampling — deterministic per position.
async function maiaArgmaxMove(fen, rungElo) {
  const uciProbs = await nodePolicy(fen, rungElo, fenSide(fen));
  let bestUci = null, bestProb = -Infinity;
  for (const [uci, prob] of Object.entries(uciProbs).sort(([a], [b]) => (a < b ? -1 : 1))) {
    if (prob > bestProb) { bestProb = prob; bestUci = uci; }
  }
  return bestUci; // null only on a fully degenerate policy — fall back to a legal move (mirror fallbackMove)
}

// Stockfish-skill anchor: let Stockfish's OWN weakening logic pick — do not
// grade candidates ourselves. setoption + go, read bestmove directly.
async function stockfishSkillMove(fen, skillLevel) {
  stockfish.send(`setoption name Skill Level value ${skillLevel}`);
  stockfish.send('setoption name UCI_LimitStrength value false'); // Skill Level, not UCI_Elo (D-07 wording)
  stockfish.send(`position fen ${fen}`);
  stockfish.send(`go movetime ${ANCHOR_MOVETIME_MS}`);
  const line = await stockfish.waitFor((l) => l.startsWith('bestmove'), ANCHOR_MOVETIME_MS + SLACK_MS);
  return parseBestmove(line); // @/hooks/uciParser — already exported, imported not reimplemented
}
```

### Anti-Patterns to Avoid

- **Reimplementing `selectBotMove`'s regime dispatch (blend<=0 vs blend>=1 vs softmax) in the harness.** The whole point of CAL-02 is that the harness calls the real function. If the harness ever branches on `blend` itself to decide sampling vs argmax, that's a parity bug waiting to happen.
- **Using `gem-elo-calibration.mjs`'s `gradePosition` unchanged as `EngineProviders.grade`.** Wrong key (SAN not UCI), wrong scope (all legal moves, not `searchmoves`-restricted candidates), missing `depth` field. See Pattern 3 / Pitfall 1.
- **Letting Stockfish "Skill Level" state leak across roles.** A single shared Stockfish process serves three roles (bot's own `grade()`, Stockfish-skill anchor moves, adjudication eval) — every `go` must explicitly reset the options it needs first. See Pitfall 2.
- **Sourcing the opening book from the gem-elo Kaggle CSV.** That CSV is tactical brilliancy positions, not diverse balanced opening starts — wrong semantics (see Open Question 1).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Move selection at (ELO, blend) strength | A parallel "bot logic" for the harness | `selectBotMove` imported via `@/` | CAL-02's entire purpose; any reimplementation defeats the measurement's validity. |
| Maia board/policy encoding | A second tensor-encoding module | `@/lib/maiaEncoding` (`encodeBoard`, `maskAndSoftmax`, `eloToInput`, `MAIA_ELO_LADDER`) | Already confirmed against the real ONNX contract (`151-MAIA-CONTRACT.md`); a second hand-rolled encoder risks silently drifting from the confirmed vocab/plane order. |
| UCI `info` line parsing | A regex ad-hoc parser | `@/hooks/uciParser`'s `parseInfoLine`/`parseBestmove` | Already handles the `multipv`-is-a-rank-not-an-identity landmine and bound (`exact`/`lowerbound`/`upperbound`) filtering correctly. |
| Terminal-position detection (mate/stalemate/repetition/50-move/insufficient material) | A custom rules engine | `chess.js`'s `isGameOver()`/`isCheckmate()`/`isStalemate()`/`isThreefoldRepetition()`/`isInsufficientMaterial()` | Exactly what `frontend/src/lib/engine/treeCommon.ts`'s `terminalValue` already calls — same library, same semantics, zero drift risk. |
| Weighted/statistical combination of per-anchor Elo estimates | A bespoke variance/weighting formula | `@/lib/scoreConfidence`'s `wilsonBounds`/`computeScoreConfidence` (Wilson 95% CI over W/D/L), imported via the `@/` alias hook | The project already has an established, memory-flagged-as-canonical Wilson-based statistical utility (`feedback_wilson_chess_score`: "Trust the established Wilson stat method... don't editorialize methodology"). Use the CI width as an inverse-variance weight per anchor rather than inventing a new formula. |
| Seeded PRNG | A `Math.random()`-seeded shim or a new library | `mulberry32` — already implemented THREE times in this codebase (`gem-elo-calibration.mjs`, `frontend/src/lib/engine/botSampling.ts` exported, `selectBotMove`'s own test fixtures) | Import `mulberry32` from `@/lib/engine/botSampling` (it's already exported there per Phase 166 D-11) rather than adding yet a fourth copy. |

**Key insight:** this phase's entire value is in NOT writing new chess/ML logic — every piece of domain logic (move selection, encoding, parsing, rules, statistics) already exists and is imported. The only genuinely new code is orchestration: the game loop, the anchor move-choosers' Stockfish-option plumbing, the opening book, and the grid/TSV sweep.

## Common Pitfalls

### Pitfall 1: `gem-elo`'s `gradePosition` is the WRONG shape for `EngineProviders.grade`
**What goes wrong:** Copying `gem-elo-calibration.mjs`'s `gradePosition(engine, fen, chessCtor, multipvCap, movetimeMs)` verbatim and passing it as the harness's `grade()` provider. It returns a `Map<san, {evalCp, evalMate}>` for ALL legal moves (unrestricted `MultiPV`), but `EngineProviders.grade` must return a UCI-keyed `Map<uci, MoveGrade>` (with a `depth` field) for ONLY the candidate UCIs `mctsSearch` passes via `searchmoves`.
**Why it happens:** Both functions "grade positions with Stockfish MultiPV" and look superficially identical; the key/shape/candidate-scope differences are easy to miss on a skim.
**How to avoid:** Build `grade()` from `frontend/src/lib/engine/workerPool.ts`'s `sendGo`/`handleLine` pattern instead (see Pattern 3) — `searchmoves`-restricted, keyed by `parsed.pv[0]` (UCI), `depth` included.
**Warning signs:** `mctsSearch`'s expansion loop silently drops every child (grade lookup by UCI always misses because the map is SAN-keyed) — the search tree would build with `objectiveEvalCp: null` everywhere and `practicalScore` would degrade to whatever `leafExpectedScore`'s null-grade fallback does, silently corrupting every measurement without an obvious crash.

### Pitfall 2: One shared Stockfish process serves THREE roles — option state leaks across them
**What goes wrong:** The harness's single spawned Stockfish process is asked to (a) grade the bot's own MCTS candidates at full strength, (b) choose a move AS the Stockfish-skill anchor at a deliberately weakened `Skill Level`, and (c) evaluate the position for adjudication (D-10). If a prior anchor move's `setoption name Skill Level value 3` is never reset before the next `grade()` call, the bot's own search gets silently weakened too — corrupting the measurement without any error.
**Why it happens:** UCI engines are stateful (`setoption` persists until changed); `gem-elo-calibration.mjs`'s single-role usage never had to worry about this.
**How to avoid:** Every call site that sends `go` must explicitly set every option it depends on immediately before that `go` — never assume a "default" state. `grade()` (Pattern 3) resets `Skill Level` to 20 and `UCI_LimitStrength` to `false` on every call; the anchor mover (Pattern 4) sets its own `Skill Level` on every call. Since chess is strictly turn-based, there is never a concurrency collision (only ever one `go` in flight) — this is a sequencing bug risk, not a race condition.
**Warning signs:** Bot-cell ELO estimates that are anomalously low/noisy specifically in cells adjacent to a Stockfish-skill anchor matchup, or a spike/smoke run where the bot loses far more than the ELO gap would predict.

### Pitfall 3: `SearchBudget.concurrency > 1` needs N independent engines, but the harness has ONE
**What goes wrong:** The browser's real `EngineProviders.grade` is backed by a 2-4 worker `WorkerPool` (`workerPool.ts`), so `mctsSearch` can dispatch several `grade()` calls in the same round via `Promise.all` (bounded by `budget.concurrency`). The harness has exactly ONE spawned Stockfish process. Setting `concurrency > 1` would fire multiple `position`/`go` commands at the same engine before the first resolves, corrupting all of them.
**Why it happens:** `SearchBudget.concurrency` is a generic dial in the frozen contract; nothing structurally prevents setting it above 1 in a harness with only one engine.
**How to avoid:** Fix the harness's `SearchBudget.concurrency = 1` as a named constant (this is a harness-specific choice, distinct from D-11's `maxNodes`/`maxPlies` mirroring — flag it clearly as a deliberate divergence from the app's `computePoolSize()`, not an oversight). If the D-03 spike shows this is the actual throughput bottleneck (more likely than the ONNX runtime choice — Stockfish grading, not Maia inference, is probably the harness's hot path), the fallback lever is spawning a small pool of 2-4 Stockfish child processes (mirroring `workerPool.ts`'s slot-queue design with `node:child_process` instead of Web Workers), NOT switching to `onnxruntime-node`.
**Warning signs:** Garbled/`undefined` PV lines, `bestmove` responses appearing out of order relative to the `position`/`go` that triggered them.

### Pitfall 4: Anchor-inversion math blows up at score = 0 or score = 1
**What goes wrong:** With only ~20 games per (bot-cell × anchor) matchup, a lopsided result (e.g. the bot loses every single game to a strong anchor) yields `score = 0`, and `E = 1/(1+10^((R_anchor−R_bot)/400))` inverted for `R_bot` requires `log10(1/E - 1)`, which is `+Infinity`/`NaN` at `E ∈ {0, 1}`.
**Why it happens:** Small sample sizes at a coarse grid (D-07's explicit tradeoff) make extreme scores common, especially for anchors far from the bot-cell's true strength.
**How to avoid:** Clamp the observed score into `[epsilon, 1 - epsilon]` before inversion (e.g. a continuity correction `epsilon = 1 / (2 * games)`, matching standard practice for small-sample Elo/Bayeselo estimation), and document the clamp in the summary TSV's metadata so a clamped row is visibly flagged, not silently smoothed over.
**Warning signs:** `NaN`/`Infinity` values in the summary TSV's per-cell Elo estimate column.

### Pitfall 5: The `.cjs`/`.wasm` basename-copy trick must be re-verified in this harness's own spawn helper
**What goes wrong:** `spawnStockfish()`'s `.wasm` binary lookup is `path.join(__dirname, basename(__filename, ext) + '.wasm')` inside the Emscripten glue — same directory, SAME basename minus extension. If the harness's own spawn helper (even if refactored into `scripts/lib/node-engine-providers.mjs`) changes the temp-file naming scheme, this silently breaks.
**Why it happens:** This is Emscripten-generated glue code, not a documented contract — the exact lookup logic is opaque unless read directly (already done in `gem-elo-calibration.mjs`'s Task 165-02, referenced in memory `project_headless_stockfish_wasm_verification`).
**How to avoid:** When refactoring `spawnStockfish` into a shared lib module, keep the exact `runId`/copy-then-rename logic unchanged; verify with a smoke run (`setoption`/`isready`/`uciok` round-trip) immediately after the refactor, before writing any harness-specific logic on top.
**Warning signs:** Stockfish process spawns but never responds to `uci` (silently hangs on `waitFor('uciok', ...)`, eventually timing out at `STOCKFISH_INIT_TIMEOUT_MS`).

## Code Examples

See Architecture Patterns 1-4 above for the four load-bearing new code shapes (`selectBotMove` call site, `nodePolicy`, `nodeGrade`, anchor movers). All cite exact source file/line locations already verified against the real files in this session.

### Weighted-mean anchor-Elo combination (D-05)

```javascript
// Per-anchor inversion: solve E = 1/(1+10^((R_anchor-R_bot)/400)) for R_bot.
// Clamp score to avoid +/-Infinity at the extremes (Pitfall 4).
const SCORE_CLAMP_EPSILON_DIVISOR = 2; // epsilon = 1 / (SCORE_CLAMP_EPSILON_DIVISOR * games)

function invertAnchorElo(observedScore, anchorRating, games) {
  const epsilon = 1 / (SCORE_CLAMP_EPSILON_DIVISOR * games);
  const clamped = Math.min(1 - epsilon, Math.max(epsilon, observedScore));
  return anchorRating - 400 * Math.log10(1 / clamped - 1);
}

// Combine across anchors, weighting by inverse Wilson-CI-width (imported via @/ alias —
// Don't Hand-Roll table) rather than a bespoke formula.
import { wilsonBounds } from '@/lib/scoreConfidence';

function combineAnchorEstimates(perAnchor /* [{ score, games, anchorRating }] */) {
  let weightedSum = 0;
  let totalWeight = 0;
  for (const { score, games, anchorRating } of perAnchor) {
    const estimate = invertAnchorElo(score, anchorRating, games);
    const [ciLow, ciHigh] = wilsonBounds(score, games);
    const ciWidth = Math.max(ciHigh - ciLow, MIN_CI_WIDTH); // guard divide-by-zero at a perfect 0/N or N/N CI
    const weight = 1 / (ciWidth * ciWidth);
    weightedSum += estimate * weight;
    totalWeight += weight;
  }
  return totalWeight > 0 ? weightedSum / totalWeight : null;
}
```

## State of the Art

Not applicable in the usual sense — this is a novel internal tool, not an area with an evolving external best practice. The one relevant "state of the art" fact: engine-vs-engine strength testing (CCRL, CEGT, and Stockfish's own `fishtest`) conventionally uses a FIXED, DIVERSE opening book (not random starts, not a single position) specifically to avoid both (a) identical repeated games against a deterministic opponent and (b) bias toward one opening family — this is the same rationale D-09 already locked in for this harness, confirming the design choice against established engine-testing practice [ASSUMED — general chess-engine-testing community knowledge, not sourced from a specific citation this session].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Stockfish "Skill Level" 0/3/5 map approximately to Elo ~1320-1350 / ~1700-1750 / ~2050-2200 respectively | Open Question 2 | If the real mapping differs by more than the ±100-150 Elo the milestone already treats as inherent noise (SEED-091), the anchor-known-rating inputs to D-05's inversion are wrong, but this only affects the ADVISORY Elo estimate (D-05), never the primary raw W/D/L matrix (D-04) — low blast radius. |
| A2 | A ~20-30 entry curated static opening-book FEN list, cycled deterministically by seed, satisfies D-09's "diverse balanced" requirement | Open Question 1 | If the list is too narrow (e.g. all e4 lines) it could bias the measured strength toward one opening family; mitigated by explicitly including both e4/d4/c4/Nf3 first moves and a range of resulting pawn structures (see the concrete list in Open Question 1). |
| A3 | `SearchBudget.concurrency = 1` is the correct harness constant (vs. building a multi-process Stockfish pool up front) | Pitfall 3 | If wrong, the spike's throughput number understates achievable speed and could trigger an unnecessary `onnxruntime-node`/multi-process escalation; low risk since the spike itself is designed to catch and report this, and a multi-process pool is a bounded, well-precedented fallback (mirrors `workerPool.ts`'s already-proven design, just over child processes instead of Workers). |
| A4 | Weighted-mean (inverse-Wilson-CI-width) anchor combination is an adequate substitute for full least-squares, per D-05's "weighted mean / least-squares" either-or wording | ELO-estimate inversion math (Code Examples) | If wrong, the derived per-cell Elo estimate is somewhat less statistically efficient than a joint fit, but D-05 explicitly frames this whole number as "advisory... an estimate, not a precise ELO" — the caveat already covers this. |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **Exact opening-book source and size (explicitly left to research/planner by CONTEXT.md).**
   - What we know: D-09 requires a fixed, seeded, diverse, color-balanced set of opening start FENs; `blend=1` is deterministic so opening variety is the ONLY source of game-to-game variation at the top of the grid. The gem-elo harness's Kaggle CSV (`temp/brilliants_no_stalemates.csv`) is the only existing FEN corpus in the repo, but it's sourced from tactical "brilliant move" positions (mid/endgame, with a computed brilliancy `score` field), not opening theory — wrong semantics for "diverse balanced opening starts."
   - What's unclear: whether the planner wants a larger (e.g. 50-100) auto-generated pool (e.g. via a short random-legal-move walk from the start position, filtered to near-equal Stockfish eval) vs. a small, human-curated, named list.
   - Recommendation: a small, hand-curated static list (~20-30 entries) of well-known, standard, balanced opening lines after 3-6 half-moves, covering both `1.e4` and `1.d4`/`1.c4`/`1.Nf3` first-move families and a spread of resulting structures (open/semi-open/closed) — e.g. Italian, Ruy Lopez, Scotch, Sicilian (two branches), French, Caro-Kann, Scandinavian, QGD, QGA, Slav, KID, Nimzo-Indian, Grünfeld, English, Reti, Dutch, Pirc, Modern, Vienna. Store as a plain `scripts/lib/calibration-openings.mjs` array (name/ECO tag + FEN), written from well-known public chess theory (same "confirmed facts, not copied source" discipline as `maiaEncoding.ts`'s header, since these are standard opening move sequences, not a licensed database). Assign games round-robin (`openings[gameIndex % openings.length]`) with color alternating every game — this simultaneously satisfies "one per game" and "colors alternated" (D-09) without needing a shuffle.

2. **Anchor → Stockfish-skill-level Elo mapping table (explicitly left to research/planner by CONTEXT.md).**
   - What we know: the vendored `stockfish-18-lite-single.js` binary confirms `Skill Level`, `UCI_LimitStrength`, and `UCI_Elo` UCI options are all present [VERIFIED: grep of the vendored binary's CLI-completer option list this session]. Official Stockfish documentation states Skill Level 0 corresponds to approximately 1347 Elo and Skill Level 19 to approximately 3212 Elo, per a graph in the official FAQ, with the developers' own disclaimer that the mapping is coarse and calibrated at a specific time control (120s+1s, anchored to CCRL 40/4) [CITED: official-stockfish.github.io/docs/stockfish-wiki/Stockfish-FAQ.html]. Community-reported specific-level tables vary by Stockfish version and testing methodology; one frequently-cited table gives Skill 0 ≈ 1320 Elo, Skill 3 ≈ 1742 Elo, Skill 5 ≈ 2204 Elo [ASSUMED — WebSearch, not an authoritative source, and NOT re-verified against Stockfish 18 specifically].
   - What's unclear: no authoritative, version-specific (Stockfish 18) numeric table for exactly levels {0, 3, 5} was found this session.
   - Recommendation: use round approximate anchor ratings — **Skill 0 ≈ 1320, Skill 3 ≈ 1750, Skill 5 ≈ 2200** — clearly documented as coarse/approximate in the TSV run-metadata and in the summary output, consistent with SEED-091's own already-accepted ±100-150 Elo conversion-error caveat (D-05). Do not present these as precise; this is exactly the kind of claim CONTEXT.md flags as needing confirmation before being treated as locked — surface it to the user at plan/discuss time if precision matters more than the milestone's own stated tolerance suggests.

3. **Exact adjudication cp threshold, sustain-ply count, and ply cap (explicitly left to research/planner by CONTEXT.md).**
   - What we know: D-10 specifies "|eval| ≥ ~600 cp sustained" plus a hard ply cap, reusing the already-spawned Stockfish for the adjudication eval (a plain `go movetime N` at the current position, not a MultiPV grade — just the top-line score).
   - What's unclear: no existing precedent for adjudication thresholds elsewhere in this codebase (this is the first engine-vs-engine self-play harness in the repo).
   - Recommendation: `ADJUDICATION_CP_THRESHOLD = 600`, `ADJUDICATION_SUSTAIN_PLIES = 4` (eval must stay past the threshold, same side favored, for 4 consecutive plies before adjudicating — avoids adjudicating a transient tactical spike that gets refuted), `PLY_CAP = 120` (60 full moves — generous for decisive games at this budget, still bounds worst-case runtime; adjudicate as a draw if the cap is hit without a sustained-eval trigger). These are named constants the planner/executor should treat as tunable, not load-bearing — flag as `[ASSUMED]`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Entire harness (type-stripping `@/` alias hook requires Node's native TS support) | ✓ | v24.14.0 [VERIFIED: local `node --version`] | — |
| `frontend/node_modules` (onnxruntime-web, chess.js) | Resolved via `resolveFrontendModule`/`@/` hook, not a root `node_modules` | ✓ | matches `frontend/package.json` [VERIFIED] | — |
| Vendored Stockfish WASM binary (`frontend/public/engine/stockfish-18-lite-single.{js,wasm}`) | Grading, anchors, adjudication | ✓ | 18.0.8 [VERIFIED] | — |
| Vendored Maia ONNX model (`frontend/public/maia/maia3_simplified.onnx`) | Bot policy + raw-Maia argmax anchor | ✓ [assumed present — same path `gem-elo-calibration.mjs` already reads successfully] | — | — |
| Disk space under `reports/data/` | TSV output | ✓ (existing dir, already used by gem-elo/benchmark outputs) | — | — |
| Multi-core CPU (for a future multi-process Stockfish pool, if the spike mandates it) | Pitfall 3's fallback lever only, not the initial build | ✓ | 16 cores [VERIFIED: local `nproc`] | Not needed unless the spike shows `concurrency=1` throughput is inadequate. |

**Missing dependencies with no fallback:** none identified.

**Missing dependencies with fallback:** none — every dependency this phase needs is already present.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None — this class of harness is verified by direct `node` execution + `node:assert`-based parity scripts, exactly like the existing `scripts/lib/gem-parity.check.mjs` (no vitest/jest wrapper; `scripts/` is outside the frontend's vitest project and has no root `package.json`/test runner). |
| Config file | none — see Wave 0 gap below |
| Quick run command | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-parity.check.mjs` |
| Full suite command | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/calibration-harness.mjs --games-per-cell 2 --elo 1500 --blends 0,1` (a full-grid-shaped but tiny smoke run — same code path as production, small enough to run in CI/pre-commit time) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAL-02 | `selectBotMove`/`mctsSearch`/`maskAndSoftmax` are imported unchanged, never reimplemented | parity assertion | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-parity.check.mjs` | ❌ Wave 0 — new file, mirrors `gem-parity.check.mjs` |
| CAL-03 | Spike reports moves/sec + projected full-grid wall-clock for the `blend=1` cell | manual/instrumented run | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/calibration-harness.mjs --elo 1900 --blends 1 --anchors sf5 --games-per-cell 4` (built-in timing instrumentation, printed to stdout) | ❌ Wave 0 — the harness itself, run in "spike mode" via small flags |
| CAL-01 | Grid sweep produces a well-formed main + summary TSV in `reports/data/` | smoke run + manual TSV inspection | `node --import ... scripts/calibration-harness.mjs --games-per-cell 2` then inspect column headers/row counts | ❌ Wave 0 — the harness itself |
| D-09 (seeded reproducibility) | Same `--seed` produces the identical opening assignment and move sequence for `blend=1` games | property/determinism assertion | A small `node:assert`-based check: run the harness twice with the same `--seed`, diff the resulting TSVs' `fen`/`san` move-sequence columns for byte-identity | ❌ Wave 0 — new assertion, can be folded into `calibration-parity.check.mjs` or a sibling `calibration-determinism.check.mjs` |
| D-05 (ELO-inversion math) | `invertAnchorElo`/`combineAnchorEstimates` produce a finite, correctly-signed estimate for known synthetic inputs (e.g. `score=0.5` at `R_anchor=1500` → `R_bot≈1500`; a clamped extreme score never yields `NaN`/`Infinity`) | unit-style assertion (canned inputs, no engines/network) | A `node:assert` script over hand-computed expected values (mirrors `gem-parity.check.mjs`'s fixture style) — pure math, no ONNX/Stockfish needed | ❌ Wave 0 — new, pure-function, fast to write |

### Sampling Rate
- **Per task commit:** `calibration-parity.check.mjs` (parity) + the pure-math ELO-inversion assertion — both run in well under a second, no engines spawned.
- **Per wave merge:** the small smoke-run full-suite command above (spawns real Maia + Stockfish, plays a handful of games — budget ~1-2 minutes based on `gem-elo-calibration.mjs`'s per-position grading time).
- **Phase gate:** the actual D-03 spike run (the throughput-measuring invocation) IS the phase's Nyquist gate for CAL-03 — its printed moves/sec + projected wall-clock is the human-readable go/no-go artifact, not a pass/fail automated assertion (this is a measurement, not a correctness check).

### Wave 0 Gaps
- [ ] `scripts/lib/calibration-parity.check.mjs` — new parity check (CAL-02), mirrors `gem-parity.check.mjs`
- [ ] A pure-math assertion script (or folded into the parity check) for `invertAnchorElo`/`combineAnchorEstimates` (D-05)
- [ ] A determinism assertion (same `--seed` → byte-identical `blend=1` game) — can fold into the parity check or stand alone
- [ ] Framework install: none — no new test framework needed, `node:assert` + direct `node` execution is the established pattern for this `scripts/` directory

## Security Domain

This phase has no user-facing or network-exposed surface — it is an offline, developer-invoked CLI tool with no auth, no persisted user data, and no HTTP endpoints. Most ASVS categories do not apply.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — no auth surface |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A — local dev tool, filesystem-permission-gated only |
| V5 Input Validation | yes | CLI flag parsing must validate every flag value (mirrors `gem-elo-calibration.mjs`'s `requireFlagValue`/`parsePositiveIntFlag`/`validateRungs` pattern — a missing/malformed flag must throw, never silently coerce to `NaN`/`undefined` and produce an empty or garbage TSV). |
| V6 Cryptography | no | N/A — no secrets, no crypto operations |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Silent no-op from an unvalidated CLI flag (e.g. `--n` at end of argv) producing an empty/garbage TSV that looks like a successful run | Tampering (of the resulting artifact's trustworthiness, not a security exploit) | `requireFlagValue`/`parsePositiveIntFlag` pattern already established in `gem-elo-calibration.mjs` — every flag consuming a value validates it before use, exactly as WR-02 in that file documents. |
| A crashed mid-sweep run discarding hours of completed grading work | Denial of availability (of the research artifact, not a system) | Durable per-row TSV streaming (D-06/WR-01) — write the header immediately, append each completed row, never buffer-then-write-at-end. |

## Sources

### Primary (HIGH confidence — direct file reads this session)
- `scripts/gem-elo-calibration.mjs` — full read; source of `createMaiaSession`, `spawnStockfish`/`StockfishUciEngine`, `mulberry32`, `resolveFrontendModule`, TSV/summary conventions, CLI validation pattern.
- `scripts/lib/frontend-alias-hook.mjs` — full read; the `@/` resolve hook mechanism.
- `scripts/lib/gem-parity.check.mjs` — full read; the parity-check pattern to mirror.
- `frontend/src/lib/engine/selectBotMove.ts`, `types.ts`, `mctsSearch.ts`, `botSampling.ts`, `guardrail.ts`, `maiaQueue.ts`, `workerPool.ts`, `treeCommon.ts` (partial) — full/partial reads; the exact contracts and reference implementations this harness's Node providers must satisfy.
- `frontend/src/lib/maiaEncoding.ts` — full read; `encodeBoard`/`maskAndSoftmax`/`eloToInput`/`MAIA_ELO_LADDER` and the confirmed ONNX contract.
- `frontend/src/hooks/useFlawChessEngine.ts` — full read; `FLAWCHESS_ENGINE_MAX_NODES=400`/`FLAWCHESS_ENGINE_MAX_PLIES=8` (D-11 mirror targets).
- `frontend/src/lib/scoreConfidence.ts` — full read; `wilsonBounds`/`computeScoreConfidence` for anchor-weight combination.
- `frontend/package.json` — full read; confirmed `onnxruntime-web@1.27.0`, `chess.js@1.4.0`, `stockfish@18.0.8`, no `onnxruntime-node`.
- `npm view onnxruntime-web version` / `npm view chess.js version` / `npm view stockfish version` — confirmed registry versions match locked package.json values exactly.
- `frontend/public/engine/stockfish-18-lite-single.js` — grepped; confirmed `Skill Level`, `UCI_LimitStrength`, `UCI_Elo` UCI options are all present in the vendored binary's own CLI completer list.
- `.planning/phases/166-bot-move-selection-core-selectbotmove/166-CONTEXT.md` and `166-PATTERNS.md` — full reads; Phase 166's locked decisions and pattern map this phase depends on.

### Secondary (MEDIUM confidence — official docs via WebFetch)
- [Stockfish FAQ — Skill Level and UCI_Elo](https://official-stockfish.github.io/docs/stockfish-wiki/Stockfish-FAQ.html) — Skill Level 0 ≈ 1347 Elo, Skill Level 19 ≈ 3212 Elo, calibrated at 120s+1s anchored to CCRL 40/4; explicit developer disclaimer that the mapping is approximate.

### Tertiary (LOW confidence — WebSearch only, flagged for validation)
- Community-reported Stockfish skill-level-to-Elo tables (picochess groups post, various forum threads) giving Skill 0 ≈ 1320, Skill 3 ≈ 1742, Skill 5 ≈ 2204 — not verified against Stockfish 18 specifically, methodology/time-control varies by source. See Open Question 2 / Assumption A1.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, all versions verified against both `package.json` and the npm registry directly.
- Architecture: HIGH — every contract (`selectBotMove`, `EngineProviders`, `SearchBudget`, `RankedLine`) was read directly from source this session; the game-loop/grid orchestration is new but composes only already-understood pieces.
- Pitfalls: HIGH for Pitfalls 1/2/3/5 (derived directly from reading the actual contract mismatches and stateful-engine semantics in source); MEDIUM for Pitfall 4 (standard small-sample-Elo-estimation practice, not codebase-specific).
- Stockfish skill-level Elo mapping (Open Question 2): LOW — no authoritative Stockfish-18-specific table found; flagged for user confirmation.
- Opening-book source (Open Question 1): MEDIUM — the recommendation is a defensible, license-clean design choice, but the exact list is Claude's own construction from general chess knowledge, not sourced from an external authoritative opening database.

**Research date:** 2026-07-11
**Valid until:** 30 days (stable — no fast-moving dependency in this phase; the vendored Stockfish/Maia binaries and `selectBotMove` contract are all frozen prior-phase artifacts)
