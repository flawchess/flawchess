# Architecture Research: FlawChess Engine Integration

**Domain:** Client-side MCTS chess search (expectimax-inside-MCTS, Maia-weighted backup) integrating into an existing React/Vite analysis board
**Researched:** 2026-07-05
**Confidence:** HIGH — grounded in direct reads of the shipped codebase (`useStockfishGradingEngine.ts`, `useMaiaEngine.ts`, `useStockfishEngine.ts`, `useAnalysisBoard.ts`, `Analysis.tsx`, `useGameOverlay.ts`, `moveQuality.ts`, `theme.ts`) plus the locked algorithm/architecture in `SEED-082` and the locked scope in `PROJECT.md`'s v2.0 milestone section. No external ecosystem research was needed — this is an integration design against a codebase already read in full for the relevant surfaces.

## Standard Architecture

### System Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│                         React (main thread)                                │
│  ┌────────────────┐   ┌─────────────────────┐   ┌───────────────────────┐ │
│  │ Analysis.tsx    │   │ useFlawChessEngine   │   │ FlawChessEngineLines  │ │
│  │ (arrow compose, │◄──┤ (NEW hook: lifecycle,│──►│ (NEW panel: ranked    │ │
│  │  toggles)       │   │  debounce, abort)    │   │  lines, modal path,   │ │
│  └────────────────┘   └──────────┬───────────┘   │  score pair)          │ │
│                                    │                └───────────────────────┘ │
│                                    ▼                                        │
│                        ┌───────────────────────┐                           │
│                        │ lib/engine/mctsSearch │  pure orchestrator loop   │
│                        │ (selection/expansion/ │  (async, main thread —    │
│                        │  backup, guardrail    │   no dedicated worker,    │
│                        │  interface)           │   see Concurrency below)  │
│                        └──────────┬────────────┘                           │
│              ┌─────────────────────┴─────────────────────┐                │
│              ▼                                             ▼                │
│  ┌────────────────────────┐                  ┌─────────────────────────┐   │
│  │ lib/engine/maiaQueue    │                  │ lib/engine/workerPool    │   │
│  │ (1 Maia worker,         │                  │ (2–4 Stockfish workers,  │   │
│  │  FIFO request queue)    │                  │  node-eval priority queue)│   │
│  └───────────┬─────────────┘                  └────────────┬────────────┘   │
└──────────────┼───────────────────────────────────────────────┼──────────────┘
               ▼                                                ▼
   ┌─────────────────────────┐                     ┌──────────────────────────┐
   │ Web Worker               │                     │ Web Worker × N (2–4)      │
   │ /maia/maia-worker.js      │                     │ /engine/stockfish-18-     │
   │ (onnxruntime-web, same    │                     │ lite-single.js (same      │
   │ binary as useMaiaEngine,  │                     │ vendored binary as        │
   │ SEPARATE instance)        │                     │ useStockfishGradingEngine,│
   │                           │                     │ N SEPARATE instances)     │
   └───────────────────────────┘                     └──────────────────────────┘
```

No server round-trip anywhere in this diagram — every box above the dashed worker boundary runs in the browser tab. No SharedArrayBuffer: each Stockfish worker is single-threaded and independent (embarrassingly-parallel leaf grading, not one deep multi-threaded search).

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `lib/engine/guardrail.ts` | The stable contract: `position + budget → ranked root moves with lines`, incremental emission | TypeScript interfaces only, no logic — both search backends implement it |
| `lib/engine/backup.ts` | The one genuinely novel piece: Maia-prior-weighted expectation backup (opponent/your-ELO asymmetric), root = max | Pure function, zero I/O, deterministic, exhaustively unit-tested with fabricated priors |
| `lib/engine/mctsSearch.ts` | MCTS orchestrator: selection → expansion → backup → anytime snapshot emission | Pure-ish async generator/callback loop over injected `EngineProviders`, no direct Worker references |
| `lib/engine/fallbackExpectimax.ts` | Depth-limited expectimax, same guardrail interface — the 1-day recovery path if MCTS tuning stalls | Pure function tree, reuses `backup.ts` for its own value combination so the "custom backup rule" isn't reimplemented twice |
| `lib/engine/leafScore.ts` | Eval→expected-score at the depth cutoff | Thin re-export of the ALREADY-SHIPPED `evalToExpectedScore` (`lib/liveFlaw.ts`) — no new sigmoid |
| `lib/engine/maiaQueue.ts` | Serializes Maia policy requests to one dedicated worker instance | FIFO async queue wrapping a fresh `Worker('/maia/maia-worker.js')` — same script as `useMaiaEngine`, separate instance (SC3-style isolation, same precedent as `useStockfishGradingEngine` vs `useStockfishEngine`) |
| `lib/engine/workerPool.ts` | Generalizes the Phase 151.1 single-worker grading pattern to N workers with a node-evaluation priority queue | N fresh `Worker('/engine/stockfish-18-lite-single.js')` instances, each doing the SAME `searchmoves`-restricted MultiPV protocol as `useStockfishGradingEngine`, dispatched round-robin from a priority queue |
| `hooks/useFlawChessEngine.ts` | React lifecycle: worker pool creation/teardown, position debounce, abort-on-navigate, throttled snapshot → state | Mirrors `useStockfishEngine`/`useMaiaEngine`'s `enabled`/tab-hide-pause/stale-guard conventions |
| `components/analysis/FlawChessEngineLines.tsx` | Renders ranked root lines + modal path + objective-vs-practical score pair | Structural sibling of `EngineLines.tsx` (clickable move chips via `playUciLine`, miniboard hover) |
| `Analysis.tsx` (modified) | Wires the hook, composes the new arrow layer into the existing precedence chain, owns toggle state | Extends the existing `boardArrows`/`useMemo` chain — no new composition pattern needed |

## Recommended Project Structure

```
frontend/src/
├── lib/
│   ├── engine/                      # NEW subsystem — pure/testable, zero React, zero Worker refs at the core
│   │   ├── types.ts                 # SearchBudget, EngineProviders, RankedLine, EngineSnapshot, MoveGrade (reuse)
│   │   ├── guardrail.ts             # SearchRunner type — the interface both backends implement
│   │   ├── backup.ts                # the Maia-weighted expectimax backup rule (pure, most-tested file)
│   │   ├── select.ts                # MCTS selection policy, deterministic tie-break, no Dirichlet noise
│   │   ├── mctsSearch.ts            # MCTS orchestrator implementing SearchRunner
│   │   ├── fallbackExpectimax.ts    # depth-limited expectimax implementing SearchRunner (guardrail fallback)
│   │   ├── leafScore.ts             # wraps lib/liveFlaw.ts's evalToExpectedScore — no new formula
│   │   ├── maiaQueue.ts             # dedicated Maia worker + FIFO request queue (policy provider)
│   │   ├── workerPool.ts            # N-worker Stockfish grading pool + priority queue (grade provider)
│   │   └── __tests__/
│   │       ├── backup.test.ts       # pure fixture-based tests, no workers
│   │       ├── mctsSearch.test.ts   # fake-provider tests (in-memory stub policy/grade fns), fully deterministic
│   │       └── fallbackExpectimax.test.ts
│   ├── liveFlaw.ts                  # EXISTING — evalToExpectedScore reused by leafScore.ts, not duplicated
│   ├── moveQuality.ts               # EXISTING — selectCandidatesByMass / classifyMoveQuality patterns reused
│   ├── maiaEncoding.ts              # EXISTING — maskAndSoftmax / MAIA_ELO_LADDER reused by maiaQueue.ts
│   └── theme.ts                     # MODIFIED — + FLAWCHESS_ENGINE_ARROW / FLAWCHESS_ENGINE_ARROW_SECOND
├── hooks/
│   ├── useFlawChessEngine.ts        # NEW — React integration layer over lib/engine
│   ├── useStockfishGradingEngine.ts # EXISTING — Phase 151.1 primitive; workerPool.ts generalizes its protocol
│   ├── useMaiaEngine.ts             # EXISTING — untouched; maiaQueue.ts is a SEPARATE worker instance
│   └── useAnalysisBoard.ts          # EXISTING — untouched; playUciLine already supports engine-line clicks
├── components/analysis/
│   ├── FlawChessEngineLines.tsx     # NEW — mirrors EngineLines.tsx structurally
│   ├── EngineLines.tsx              # EXISTING — pattern reference, untouched
│   └── MaiaHumanPanel.tsx           # EXISTING — untouched (no Maia arrow layer in this milestone)
└── pages/Analysis.tsx               # MODIFIED — wire useFlawChessEngine, extend arrow composition + toggles
```

### Structure Rationale

- **`lib/engine/` as a nested subsystem, not a flat `lib/*.ts` file:** every other `lib/` module is a single flat file; this is deliberately the one nested exception because the guardrail mandate (interface-swappable MCTS ↔ expectimax) needs several small, independently-unit-testable files. Nesting keeps the flat `lib/` namespace legible while keeping the subsystem's internal boundaries visible in the filesystem.
- **The pure core (`guardrail.ts`/`backup.ts`/`select.ts`/`mctsSearch.ts`/`fallbackExpectimax.ts`) never imports a `Worker` directly.** It only depends on the `EngineProviders` interface (two async functions: `policy` and `grade`). This is what makes `mctsSearch.test.ts` possible without spinning up real WASM/ONNX workers — tests inject fake providers with fabricated, deterministic (fen → probability/eval) tables. This is the single most important structural decision: it's what makes the "1-day fallback" claim in SEED-082 credible, and what makes the custom backup rule verifiable in isolation before any worker plumbing exists.
- **`workerPool.ts` and `maiaQueue.ts` are the ONLY files that touch `Worker`/`postMessage`.** They are thin adapters implementing `EngineProviders`, built by generalizing the ALREADY-SHIPPED `useStockfishGradingEngine.ts` protocol (searchmoves-restricted MultiPV, pv[0]-keyed results, stop-before-go serialization) rather than inventing a new UCI dance.
- **`useFlawChessEngine.ts` lives in `hooks/`, not `lib/engine/`** — it's the one file allowed to use React (`useState`/`useEffect`/`useRef`), following the project's existing convention that hooks own Worker lifecycle + component-facing state, while `lib/` holds pure logic.
- **No new top-level directory sibling to `lib`/`hooks`/`components`.** The temptation to create `frontend/src/flawchess-engine/` was rejected — it would fragment the codebase's two-tier convention (pure logic in `lib/`, stateful glue in `hooks/`, presentation in `components/`) for no benefit; nesting under `lib/engine/` preserves it.

## Architectural Patterns

### Pattern 1: Guardrail interface — position+budget→ranked lines, two interchangeable backends

**What:** A single `SearchRunner` type that both `mctsSearch.ts` and `fallbackExpectimax.ts` implement identically. `useFlawChessEngine.ts` imports exactly ONE of them (a single line, or a config flag), never both at once and never conditionally per-call — the fallback is a build-time/config-time swap, not a runtime branch inside the hook.

**When to use:** Any time the "risky, novel" part of a system (here: MCTS budget tuning, node-count-per-second reality on WASM) might not converge in the available time. Isolate the risky part behind a narrow interface with an accepted-but-boring fallback implementation, built EARLY (Phase A below), not as an afterthought.

**Trade-offs:** Slight upfront cost (defining the interface before either backend is battle-tested) in exchange for a real, exercised escape hatch. Because `fallbackExpectimax.ts` reuses `backup.ts` for its own value combination, the interface doesn't duplicate the one truly novel piece of logic — only the tree-shape/traversal differs between the two backends.

**Example:**
```typescript
// lib/engine/types.ts
export interface MoveGrade { evalCp: number | null; evalMate: number | null; depth: number } // reused from moveQuality.ts

export interface EngineProviders {
  /** Maia move-probability distribution for `side` at `elo`, full legal-move mass. */
  policy(fen: string, elo: number, side: 'w' | 'b'): Promise<Record<string, number>>;
  /** Stockfish shallow-eval grades for the given candidate SANs at `fen`. */
  grade(fen: string, candidateSans: string[]): Promise<Map<string, MoveGrade>>;
}

export interface SearchBudget {
  maxNodes: number;      // fixed node budget — deterministic under test
  yourElo: number;
  opponentElo: number;
  maxPlies: number;      // leaf depth cutoff, 6–10 per SEED-082
}

export interface RankedLine {
  rootMoveSan: string;
  practicalScore: number;         // this engine's objective, expected points
  objectiveEvalCp: number | null; // Stockfish eval of the root move, for the score-pair display
  modalPath: string[];            // SAN sequence: your move, then opponent's most likely reply, recursively
  visits: number;
}

export interface EngineSnapshot {
  rankedLines: RankedLine[];
  nodesEvaluated: number;
  budgetExhausted: boolean;
}

// lib/engine/guardrail.ts
export type SearchRunner = (
  rootFen: string,
  budget: SearchBudget,
  providers: EngineProviders,
  onSnapshot: (snapshot: EngineSnapshot) => void,
  signal: AbortSignal,
) => Promise<EngineSnapshot>;
```

### Pattern 2: Custom backup rule as a pure, fixture-tested function

**What:** `backup.ts` exports one function taking an array of `{ childValue, priorProbability }` pairs plus a `mover: 'root' | 'opponent' | 'self'` flag, returning a single scalar. Root = `Math.max(...childValues)`. Opponent/self = `Σ priorProbability_renormalized · childValue` over the Maia top-k truncated-at-90%-mass set (truncation/renormalization also lives here, not scattered into the search loop).

**When to use:** This is the ONE piece of domain logic in the whole system that is genuinely new (per SEED-082's prior-art survey) — it deserves to be the most isolated, most heavily fixture-tested file in the codebase, verifiable with hand-computed expected values before a single worker exists.

**Trade-offs:** None significant — pure functions are strictly easier to test and reuse (both backends need it) than embedding the weighting inline in the MCTS traversal.

### Pattern 3: Separate worker instances per subsystem (SC3 isolation), not shared caches

**What:** The new engine gets its OWN Maia worker (`maiaQueue.ts`) and its OWN pool of Stockfish workers (`workerPool.ts`) — completely independent of the existing `useMaiaEngine`/`useStockfishGradingEngine` instances that drive the Moves-by-Rating chart. No shared cache, no cross-subsystem message passing.

**When to use:** Whenever two features need the same underlying WASM/ONNX binary but have different call patterns (the Move-quality-bar wants ELO-ladder-wide single-shot inference; the search core wants many small per-node lookups against a specific ELO pair) and correctness depends on not disturbing the other's state machine. This is the EXACT precedent `useStockfishGradingEngine.ts`'s own header comment establishes relative to `useStockfishEngine.ts` ("never imports, mutates, or reads useStockfishEngine's state").

**Trade-offs:** More memory (Stockfish workers each load their own NNUE net; Maia workers each load their own ONNX session) — this is the reason the SEED explicitly caps the pool at 2–4, not "as many as cores." Per-node-request routing is also simpler this way: no need to arbitrate priority between the chart's inference and the search's inference on one shared worker.

### Pattern 4: Node-evaluation priority queue biased toward the current best root line

**What:** `workerPool.ts` holds a queue of pending `{ fen, candidateSans, priority }` grading requests. `mctsSearch.ts` assigns each pending leaf/child-expansion request a priority derived from the CURRENT backed-up value of the root ancestor it belongs to (nodes under the currently-highest-`practicalScore` root child are dequeued first; ties broken by shallower depth-from-root, then deterministic SAN order). The queue re-sorts (or is a binary heap) on every new request insertion, not on a timer — insertion volume is bounded by the number of idle workers, so this is cheap.

**When to use:** Any time the total work exceeds the available parallel workers (2–4 Stockfish instances vs. potentially dozens of pending node evaluations mid-search) and SOME lines matter more than others for the anytime/live-refining requirement — the currently-best line should sharpen fastest, not evaluate in arbitrary/FIFO order.

**Trade-offs:** A touch more bookkeeping than plain FIFO, but this is precisely what SEED-082 calls out as needed ("the worker pool needs a node-evaluation priority queue favoring the currently-best root lines") — skipping it would make the anytime top-n lines refine in an arbitrary order, undermining the live-refinement UX.

### Pattern 5: Main-thread orchestrator, not a dedicated orchestrator Worker

**What:** `mctsSearch.ts`'s tree-traversal loop (selection → expansion → backup → snapshot) runs directly on the main thread, invoked from a `useEffect` inside `useFlawChessEngine.ts` — NOT wrapped in its own dedicated Web Worker.

**When to use / rationale:** The orchestrator's own per-node CPU cost is tree bookkeeping (a handful of object-graph operations) — negligible next to a Stockfish shallow-eval (tens to low-hundreds of ms) or a Maia inference. All genuinely expensive work is ALREADY off the main thread inside `workerPool.ts`/`maiaQueue.ts`'s Worker instances. Adding a third worker tier (an orchestrator worker managing the other two worker tiers) would require either (a) proxying every `policy`/`grade` call through an extra `postMessage` hop with no compute benefit, or (b) structured-cloning the growing MCTS tree across a boundary on every snapshot — pure overhead. This keeps the system at the "boring configuration" SEED-082 explicitly asks for.

**Trade-offs:** The main thread does incur the orchestrator's JS execution time and the throttled `setState` calls for anytime snapshots. Mitigate by (a) batching state commits — emit `onSnapshot` at a fixed cadence (e.g. every 100–150ms, mirroring the existing `RAPID_STEP_DEBOUNCE_MS` convention already used by every other engine hook in this codebase) rather than on every single node backup, and (b) keeping the tree data structure itself outside React state (a `useRef`-held mutable tree, exactly like `useAnalysisBoard.ts`'s `stateRef` pattern), with only the DERIVED `EngineSnapshot` (ranked lines, a small array) going through `setState`.

## Data Flow

### Request Flow (one search, from position change to painted arrows)

```
FEN change (Analysis.tsx / useAnalysisBoard.position)
    ↓
useFlawChessEngine: debounce (mirrors existing RAPID_STEP_DEBOUNCE_MS pattern)
    → AbortController.abort() on the previous in-flight search (mirrors stopPendingRef stale-guard)
    ↓
mctsSearch.run(rootFen, budget, providers, onSnapshot, signal)
    ↓ (repeated until budget.maxNodes reached or signal.aborted)
  select.ts → pick a node to expand (deterministic tie-break, no Dirichlet noise)
    ↓
  providers.policy(fen, elo, side)  ──► maiaQueue (1 dedicated Maia worker, FIFO)
    ↓ (top-k truncated at ~90% cumulative mass, renormalized)
  providers.grade(fen, candidateSans)  ──► workerPool (2–4 Stockfish workers, priority queue)
    ↓ (shallow eval, depth ~12–16, per SEED-082 — same protocol as Phase 151.1's grading worker)
  leafScore.ts (only at maxPlies depth) → expected score via the lichess sigmoid (lib/liveFlaw.ts, reused)
    ↓
  backup.ts → propagate value up: opponent/self nodes = Maia-prior-weighted expectation; root = max
    ↓
  onSnapshot(EngineSnapshot) — throttled to ~10Hz — ranked root lines + modal paths + node count
    ↓
useFlawChessEngine state (rankedLines, isSearching, nodesEvaluated)
    ↓
Analysis.tsx: flawChessEngineArrows useMemo (top-2 rankedLines → BoardArrow[])
    +
FlawChessEngineLines.tsx (full ranked-line list + modal path + objective-vs-practical score pair)
    ↓
ChessBoard renders arrows; board arrow-precedence chain composes with existing layers
```

### Key Data Flows

1. **Asymmetric ELO plumbing:** every `policy()` call carries an explicit `elo` + `side` pair — `budget.yourElo` at your future-move nodes, `budget.opponentElo` at opponent nodes — so the asymmetric self+opponent rating (SEED-082's one likely-unclaimed novelty hook) is structural, not bolted on. `useFlawChessEngine.ts` needs a NEW small ELO-pair resolution step distinct from the existing `useMaiaEloDefault.ts` (which resolves a single "you are here" ELO for the Move-quality chart, keyed by whoever is currently to move). The engine instead needs BOTH ratings simultaneously and independent of whose turn it is: `yourElo` = the user's rating (game mode: `gameData` rating for `gameData.user_color`; free analysis: `profile.current_rating` else the existing `FREE_PLAY_DEFAULT_ELO` fallback) and `opponentElo` = the opponent's rating (game mode: the other color's `gameData` rating; free analysis: no known opponent — default symmetric to `yourElo`, or expose a second ELO control). Flag this second control as a UI open question for the roadmap (Phase D/E below), not a solved decision here.
2. **Root candidate set = union of Maia top-k and Stockfish multi-PV top-m** (per SEED-082's locked algorithm): at the ROOT specifically (not deeper nodes), `mctsSearch.ts` should also fold in `useStockfishEngine`'s existing MultiPV=2 primary-engine lines as extra root candidates even when Maia's distribution didn't surface them — this is what lets the engine ALSO show a line Maia would never suggest but that's objectively strong, ranked by the SAME practical-score metric. This reuses `useStockfishEngine`'s already-running analysis (no extra engine call) rather than re-deriving it inside the pool.
3. **Objective-vs-practical score pair:** `RankedLine.objectiveEvalCp` is the plain Stockfish eval of the root move (already available from the SAME `providers.grade()` call used for ranking — no second grading pass), converted to "objectively +X.X" via the SAME `evalToExpectedScore`/pawn-formatting utilities already used elsewhere (`formatFlawEval.ts`), displayed alongside `practicalScore` ("practically +Y.Y for you"). Both numbers come from data the search ALREADY computed; no new backend call is needed to produce the pair.
4. **Modal path construction:** at snapshot time, walk down each ranked root child always choosing the highest-current-prior (highest Maia probability) continuation among ALREADY-EXPANDED children — not a fresh search — so `modalPath` is a read of the existing tree, computed in the snapshot-assembly step of `mctsSearch.ts`, not a separate traversal mechanism.

## Concurrency / Scheduling

- **Node-evaluation priority queue** lives inside `workerPool.ts` (Pattern 4 above) because Stockfish grading is the actual bottleneck resource (2–4 single-threaded workers vs. potentially dozens of pending requests mid-search); `maiaQueue.ts` stays simple FIFO since a Maia inference (single ONNX forward pass) is comparatively fast and each request is for a DIFFERENT position (no meaningful reordering benefit).
- **Keeping both pools busy without blocking the UI thread:** all heavy compute already lives in Worker instances (WASM Stockfish, ONNX Maia) — the main thread's job is dispatch + bookkeeping only. The risk to the UI thread isn't computation, it's RE-RENDER volume: with 2–4 workers each completing a grading call every ~50–300ms, naive `setState` on every completion could fire dozens of re-renders/second. Mitigate exactly like Pattern 5: batch `onSnapshot` emission to a fixed cadence (~100–150ms), keep the live tree in a `useRef` (not React state), and only push the small derived `EngineSnapshot` through `setState`.
- **Where the search loop runs:** main-thread orchestrator (Pattern 5), invoked from `useFlawChessEngine.ts`'s `useEffect`. Rejected: a dedicated orchestrator Worker (extra message-passing hop for no compute benefit, given the heavy work is already isolated in `workerPool.ts`/`maiaQueue.ts`).
- **Cancellation:** a single `AbortController` per position, mirroring the existing `stopPendingRef`/stale-guard convention used by every other engine hook in this codebase (`useStockfishEngine.ts`, `useStockfishGradingEngine.ts`). On FEN change: abort the current search, tell in-flight Stockfish workers to `stop` (same UCI `stop` message, same "wait for the stale `bestmove` before sending the next `go`" serialization already implemented in `useStockfishGradingEngine.ts` — `workerPool.ts` should literally reuse that per-worker state machine, just multiplied across N workers), and start a fresh search once the debounce settles.
- **Tab-hide pause:** same `visibilitychange` pattern as every existing engine hook — pause all Stockfish workers (`stop`) and skip issuing new `policy()`/`grade()` calls while `document.visibilityState === 'hidden'`; resume (re-run the current position's search from scratch, budget resets — the tree isn't worth persisting across a pause) on return.

## Anti-Patterns

### Anti-Pattern 1: Feeding search results back to sharpen the Maia prior

**What people do:** Once a search has run and found that some continuation is strong, re-query Maia "as if" the position were more likely (e.g., re-weighting based on search-discovered value) to get a "smarter" opponent model.

**Why it's wrong:** This is the confirmed 3-0 pitfall from SEED-082's prior-art survey — the KDD 2020 Maia paper and the 2026 Maia-2+MCTS paper both found MCTS-wrapped-around-Maia degrades Maia's own move-prediction accuracy by 5–10pp. The nuance that likely saves this design is using Maia's STATIC policy as fixed expectimax weights and never re-searching to alter its distribution — but that nuance only holds if the implementation genuinely never feeds anything back. `providers.policy()` must be a pure function of `(fen, elo, side)` with no dependency on anything the search has computed so far.

**Instead:** Treat every `policy()` call as a fresh, independent, position-only query (which the existing `maskAndSoftmax`/`useMaiaEngine` machinery already does) — never pass search state (visit counts, backed-up values, partial trees) into the Maia worker's request.

### Anti-Pattern 2: An app-level Zobrist/transposition cache for the search core

**What people do:** Given FlawChess's whole architecture is built around Zobrist-hash position matching, it's tempting to reuse that infrastructure to cache `grade()`/`policy()` results across nodes that transpose to the same position.

**Why it's wrong:** Explicitly rejected in SEED-082 — "positions diverge too fast to pay off" for a shallow (6–10 ply), MCTS-adaptive-depth tree, and `stockfish.wasm`'s own internal transposition table already gives partial reuse for free within a single worker's lifetime. Building an app-level cache adds real complexity (cache-key derivation, invalidation across searches, memory growth) for a workload that mostly doesn't repeat positions.

**Instead:** No cross-node cache in `lib/engine/`. The ONLY caching that should exist is the ephemeral, board-session-scoped, per-worker caches that ALREADY exist inside `useStockfishGradingEngine`'s pattern (FIFO, capped, keyed by exact FEN) — and even that is per-worker-instance, not shared across the pool.

### Anti-Pattern 3: Deep, uniform-depth expectimax as the primary search

**What people do:** Given a "budget," walk every candidate line to a fixed depth uniformly (classic minimax/expectimax tree expansion), trusting more depth = more accuracy.

**Why it's wrong:** Explicitly rejected by SEED-082's own node-budget arithmetic — a WASM Stockfish eval at useful depth costs ~50–300ms, so a seconds-scale budget yields only a few hundred node evaluations; uniform-depth expectimax wastes most of that budget on lines that die at ply 2. This is WHY MCTS is the primary backend (adaptive allocation: main line 10+ plies deep, junk abandoned immediately) and why the depth-limited expectimax is explicitly labeled a FALLBACK, not a co-equal alternative.

**Instead:** MCTS-driven adaptive allocation is the primary path; `fallbackExpectimax.ts` exists ONLY as a "MCTS tuning became a time sink" recovery valve behind the identical guardrail interface, understood to be strictly worse at this node budget.

### Anti-Pattern 4: Sharing a Maia/Stockfish worker instance between the search core and the existing Move-quality chart

**What people do:** To save memory/init time, route the new engine's `policy()`/`grade()` calls through the EXISTING `useMaiaEngine`/`useStockfishGradingEngine` worker instances already running on the page.

**Why it's wrong:** Both existing hooks have call patterns and internal state machines tuned for THEIR consumer (one-shot ELO-ladder-wide inference for the chart; single position's candidate set for grading) with FIFO/debounce/cache semantics that assume a single logical caller. The MCTS core issues many small, rapid, per-node requests against SPECIFIC (not ladder-wide) ELO values — routing through the chart's hook would either starve the chart's own responsiveness or require rebuilding both hooks' internals to arbitrate two callers, undermining the "never imports, mutates, or reads [the other]'s state" isolation principle the codebase already established for exactly this class of problem (`useStockfishGradingEngine.ts`'s own header comment).

**Instead:** Dedicated worker instances (Pattern 3) — the memory/init cost is bounded and explicit (this is exactly why SEED-082 caps the Stockfish pool at 2–4).

## Board / UI Integration

### Toggle-able arrow layers (per PROJECT.md's locked v2.0 scope — 3 layers, not SEED-082's original 4)

`PROJECT.md`'s Current Milestone section is the authoritative, more recent scope statement and supersedes SEED-082's earlier 4-layer draft on one point: **no dedicated Maia arrow layer ships this milestone** (Maia moves stay reachable via the existing Moves-by-Rating chart / hover prose). The three layers that DO ship:

| Layer | Status | Where it comes from | Default (game review) | Default (free analysis) |
|-------|--------|----------------------|------------------------|---------------------------|
| Played move | EXISTING (`useGameOverlay.ts`) | precomputed `eval_series[ply].best_move` + severity square marker | ON | N/A (no "played move" concept outside game review) |
| **FlawChess Engine top-2** | **NEW (this milestone's headline)** | `useFlawChessEngine`'s `rankedLines[0..1]` | ON | ON |
| Stockfish top-2 | EXISTING (`useStockfishEngine`/`useGameOverlay`) | `engine.pvLines[0..1]` | OFF ("show your work") | as currently shipped |

### Wiring changes to `Analysis.tsx`

1. Instantiate `useFlawChessEngine({ fen: position, enabled, yourElo, opponentElo, budget })` alongside the EXISTING `useStockfishEngine`/`useMaiaEngine` calls — same `position`/`enabled` props already threaded through both modes, so free analysis AND game review get it for free without mode-specific plumbing.
2. Add a new `flawChessEngineArrows` `useMemo`, structurally identical to the existing `qualityHoverArrows`/`pvSidelineArrows` memos (replay top-2 `rankedLines[i].rootMoveSan` at `position` via `chess.move(san)` → `{from, to}`, color from two NEW `theme.ts` constants).
3. Insert it into the EXISTING arrow-precedence chain (`baseArrows`/`boardArrows` composition at the bottom of `Analysis.tsx`) at the same tier as `gameOverlay.boardArrows` — i.e., it participates in the SAME "quality-hover overlay wins, else PV-sideline, else the game/engine overlay" precedence the codebase already has, rather than introducing a second independent composition mechanism.
4. Two new `theme.ts` constants are needed: `FLAWCHESS_ENGINE_ARROW` (best) / `FLAWCHESS_ENGINE_ARROW_SECOND` (second-best) — must be visually distinct from `STOCKFISH_ACCENT` (blue), `MAIA_ACCENT` (violet), `BEST_MOVE_ARROW`/`SECOND_BEST_ARROW` (already blue-family per `EngineLines.tsx`), and the `TAC_MISSED`/`TAC_ALLOWED` tactic-line colors. Given this is the milestone's headline feature, it should read as the MOST prominent arrow layer on the board — a warm, high-saturation hue currently unused (the existing palette has claimed blue=Stockfish, violet=Maia, red/orange/yellow=severity, teal/crimson=tactic missed/allowed) is the open slot; final hue pick is a `/gsd-ui-phase` decision, not this research's call.
5. Toggle state: two new `useState<boolean>` flags (`showFlawChessEngine`, `showStockfish`) at the `Analysis.tsx` top level, defaulted per the table above and NOT persisted (no `localStorage`, no URL param) — consistent with v1.29 D-4's "analysis state lives in the URL" scope, which covers POSITION state, not view-toggle state; toggles are ephemeral session UI, matching how the existing engine on/off switch already behaves.
6. `FlawChessEngineLines.tsx` is a NEW panel, structurally mirroring `EngineLines.tsx` (up to N ranked lines, each a row with a colored score badge + clickable move chips via the SAME `playUciLine`-based click handler already wired for `EngineLines`/tactic chips), PLUS: the objective-vs-practical score-pair badge per line, and a lightweight "searching… N nodes" progress indicator so the anytime/live-refining behavior is visible (mirrors the existing `EngineLinesSkeleton` fixed-height-placeholder pattern while the FIRST snapshot hasn't arrived yet).
7. Game-review-specific delta: alongside the three-layer arrows, surface the "what you played vs. what was practically best for you" comparison — look up the ACTUALLY-PLAYED move's `practicalScore` if it appears among the root's expanded children (it will, since Maia's top-k almost always includes moves anywhere near what a human at that level actually played), else issue one supplementary `providers.grade()` call for it. This reuses `RankedLine`'s existing shape; no new data type needed.

## Suggested Build Order (dependency-ordered phases)

Starts from the ALREADY-SHIPPED Phase 151.1 primitive and defers all "Ambitious" (SEED-082 §MVP phasing) scope.

**Phase A — Guardrail interface + pure search core (no workers, no React).**
Define `types.ts`/`guardrail.ts`. Implement `backup.ts` FIRST, in isolation, with hand-computed fixture tests (this is the one genuinely novel piece — de-risk it before anything else touches it). Implement `mctsSearch.ts` against FAKE `EngineProviders` (in-memory stub tables, no async workers) — this proves selection/expansion/backup/anytime-snapshot end-to-end, entirely deterministic, runnable in the existing Vitest setup with zero new test infrastructure. Implement `fallbackExpectimax.ts` alongside (reusing `backup.ts`) WHILE the interface is fresh — locks in the guardrail's recoverability from day one instead of retrofitting it under time pressure later. **Depends on:** nothing outside this repo's existing test tooling. **Delivers:** a fully-tested, worker-free search core — the riskiest logic proven correct before any WASM/ONNX integration exists.

**Phase B — Real providers: worker pool + Maia queue.**
Generalize `useStockfishGradingEngine.ts`'s single-worker UCI protocol into `workerPool.ts` (N workers, priority queue) — mechanical extraction of ALREADY-SHIPPED, already-battle-tested logic, the lowest-risk new-worker-code phase. Build `maiaQueue.ts` as a dedicated Maia worker instance (separate from `useMaiaEngine`'s). Swap Phase A's fake providers for these real ones in `mctsSearch.ts`; hand-verify against 1–2 known positions (e.g., a documented Polecat/vala-bot-style swindle position) for sanity, not full correctness (that's UAT territory). **Depends on:** Phase A's `EngineProviders` interface being stable. **Delivers:** a real, running (if not yet UI-visible) search over real engines.

**Phase C — React hook + anytime UI (free analysis only, no arrows yet).**
Build `useFlawChessEngine.ts` (lifecycle, debounce, abort-on-navigate, throttled snapshot emission — mirrors existing hook conventions verbatim). Build `FlawChessEngineLines.tsx` (ranked lines + modal path + score pair, no board arrows). Ship in free analysis only — simpler surface, defers the game-review overlay precedence interactions to Phase E. **Depends on:** Phase B's real providers. **Delivers:** the FIRST user-visible surface — the data pipeline becomes observable/UAT-able before touching board rendering.

**Phase D — Board arrows + toggles (free analysis).**
New `theme.ts` constants, `flawChessEngineArrows` `useMemo`, insertion into the existing arrow-precedence chain, toggle UI (checkbox row, defaults per the table above). **Depends on:** Phase C's hook already producing `rankedLines`. **Delivers:** the milestone's headline visual — FlawChess Engine top-2 arrows on the board.

**Phase E — Game-review overlay integration.**
Wire the SAME hook into game mode (position/enabled plumbing already threads through both modes structurally — the delta is purely the "what you played vs. what was practically best" comparison lookup, and confirming the Played-move / FlawChess-Engine-top-2 / Stockfish-top-2 three-layer precedence + defaults from the table above). **Depends on:** Phase D's arrow rendering already working in free analysis. **Delivers:** the full locked v2.0 scope (both surfaces).

**Explicitly out of this build order (SEED-082 "deferred by design," confirmed in PROJECT.md):** trap-finder / branch-point UI, per-ELO leaf sigmoids fit from the benchmark DB, time-pressure conditioning (clock→temperature / clock→ELO-offset), SAB multithreading. Do not schedule phases for these; they are explicitly post-MVP.

## Open Questions Flagged for Roadmap / Discuss-Phase

- **Opponent-ELO input in free analysis:** game mode has both colors' ratings from `gameData`; free analysis has no known opponent. Symmetric default (`opponentElo = yourElo`) is the simplest MVP choice but silently drops the asymmetric-ELO novelty hook in the one mode where a user might most want to explore it (e.g., "how would I do against a 2200"). A second ELO control (mirroring `useMaiaEloDefault`'s existing selector pattern) is the more complete answer — flag as a Phase C/D scoping decision, not resolved here.
- **Node budget sizing across devices:** SEED-082's "a few hundred node evaluations" arithmetic assumes a baseline device; `useFlawChessEngine.ts` should expose `budget.maxNodes` as a tunable constant (not hard-coded inline) so it can be revisited once real wall-clock/device data comes in from UAT — treat it like the existing `MOVETIME_MS`/`GRADING_TARGET_DEPTH` tunables in `useStockfishEngine.ts`/`useStockfishGradingEngine.ts`.
- **Arrow hue selection for the new layer** is a `/gsd-ui-phase` decision (not resolved in this architecture research) — flagged only that the current palette (blue/violet/red-orange-yellow/teal-crimson) has one clearly open, high-saturation slot.

## Sources

- `frontend/src/hooks/useStockfishGradingEngine.ts` (Phase 151.1 primitive — worker-pool generalization target)
- `frontend/src/hooks/useMaiaEngine.ts`, `useStockfishEngine.ts`, `useAnalysisBoard.ts`, `useMaiaEloDefault.ts`, `useGameOverlay.ts` (existing hook/state conventions this design mirrors)
- `frontend/src/pages/Analysis.tsx`, `frontend/src/components/analysis/EngineLines.tsx` (arrow-composition and ranked-line panel patterns reused)
- `frontend/src/lib/moveQuality.ts`, `liveFlaw.ts`, `maiaEncoding.ts`, `theme.ts` (reused primitives: sigmoid, mass-truncation, ELO ladder, color constants)
- `.planning/seeds/SEED-082-human-playable-line-engine.md` (locked algorithm, architecture, prior-art survey, pitfalls)
- `.planning/PROJECT.md` — "Current Milestone: v2.0 FlawChess Engine" section (authoritative locked scope, supersedes SEED-082's 4-arrow-layer draft on the Maia-layer point)

---
*Architecture research for: FlawChess Engine (v2.0 milestone) integration into the existing `/analysis` board*
*Researched: 2026-07-05*
