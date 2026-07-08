# Stack Research

**Domain:** Client-side MCTS practical-play chess engine (FlawChess Engine, SEED-082) — built on already-shipped `onnxruntime-web` (Maia-3) + `stockfish.wasm` (Stockfish 18 lite-single) in-browser Web Workers.
**Researched:** 2026-07-05
**Confidence:** HIGH (versions verified against npm registry directly; architecture recommendations verified against the two existing sibling hooks and the locked SEED-082 spec, which already made most of the load-bearing decisions)

**Scope note:** this is a *narrow, additive* stack question — the milestone reuses the entire existing v1.29/v1.32 substrate (Stockfish 18 lite-single WASM, Maia-3 ONNX, `useStockfishEngine`, `useMaiaEngine`, `useStockfishGradingEngine`). Nothing below touches those pins. The finding, in short: **add zero new npm dependencies.** The MCTS engine is glue code over primitives that already exist; every "library" question resolves to "hand-roll it, it's 50–150 lines" because either (a) no maintained library fits the non-standard requirement, or (b) the problem is too small at this workload's scale to justify a dependency.

## Recommended Stack

### Core Technologies (already pinned — no change)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `stockfish` (npm, vendors `stockfish-18-lite-single.{js,wasm}`) | 18.0.8 | Leaf-eval workhorse for the MCTS pool | Already vendored to `public/engine/`, non-bundler-processed classic Worker, ~7 MB single-thread NNUE. Confirmed still latest on npm (2026-06-15). No reason to bump for this milestone — do not conflate an engine-version bump with the MCTS feature. |
| `onnxruntime-web` | 1.27.0 | Maia-3 policy/WDL inference | Already pinned, confirmed still latest (2026-06-19). `maia-worker.js` already forces `ort.env.wasm.numThreads = 1` unconditionally (Phase 136 D-3) because there is no cross-origin isolation — this is *exactly* the config a concurrent Stockfish pool needs it to keep (see Q3 below). No version or config change required. |
| TypeScript / Vite / React | 6.0.3 / 8.0.14 / 19.2.6 | Existing frontend stack | Unaffected — the engine is pure hook + worker-message logic, no new build-time tooling. |

### Supporting Libraries — recommendation: add none

| Library | Version | Purpose | Verdict |
|---------|---------|---------|---------|
| MCTS library (`mcts`, `mcts-js`, `monte-carlo-tree-search`, `ts-mcts`, `fast-mcts`) | n/a | Generic MCTS search | **Do not add.** Checked npm registry directly: only `mcts` (0.0.8, last published 2017, unmaintained) exists under an MCTS-ish name; `mcts-js`, `monte-carlo-tree-search`, `ts-mcts`, `fast-mcts` don't exist as packages. More importantly, none would fit even if maintained — the *algorithm itself* is non-standard (SEED-082's backup rule diverges from every textbook UCT/PUCT library's selection+backup contract, see "Alternatives Considered"). |
| Priority queue / binary heap (`tinyqueue`, `heap-js`) | 3.0.0 / 2.7.1 | Node-evaluation scheduler favoring best root lines | **Do not add at MVP1 scale.** SEED-082's own node-budget arithmetic says a seconds-scale budget yields "only a few hundred node evaluations" — at N≈hundreds, a linear max-scan over a plain array (`pendingNodes.reduce(maxByPriority)`) costs microseconds per pick and is trivially correct; a binary heap is premature optimization here. `tinyqueue` (4.9 KB unpacked, 0 deps, MIT, Mapbox-maintained) is the one worth reaching for *if and only if* the budget later scales to thousands of pending nodes — note it here as a name to reach for, not a dependency to add now. |
| Worker-RPC helper (`comlink`, `workerpool`, `threads.js`) | 4.4.2 / 10.0.3 / 1.7.0 | Structuring postMessage traffic to a worker pool | **Do not add.** The existing codebase's own convention (all three engine hooks: `useStockfishEngine`, `useStockfishGradingEngine`, `useMaiaEngine`) is raw `worker.postMessage`/`onmessage` with a hand-rolled state machine — no RPC wrapper anywhere, even for Maia's structured `{type, fen, eloInputs}` protocol. Comlink's overhead (proxying, promise-per-call) doesn't fit a **streaming, cancelable, stateful UCI session** anyway — you'd fight the wrapper to get `stop`/`bestmove` semantics back out. Follow the established pattern instead (see Q1). |
| Immutable tree / state-management (`immer`, zustand-flavored tree libs) | — | MCTS tree node storage | **Do not add.** The tree is ephemeral, per-analysis-session, discarded on FEN navigation (mirrors `useStockfishGradingEngine`'s per-FEN `Map` cache lifecycle). A plain mutable `Map<nodeId, MctsNode>` or parent-pointer tree of plain objects is sufficient and matches every existing hook's use of raw `useRef<Map<...>>` for ephemeral session caches. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Existing `useStockfishGradingEngine` | Per-node primitive (Maia top-k graded by Stockfish, `searchmoves`-restricted MultiPV) | This IS the MCTS node-expansion primitive per SEED-082 — do not rebuild it, extend it into a pool (see Q1). Its `pv[0]`-keyed grade cache and ELO-independent grading cache pattern should be reused for pool workers as well. |
| Existing `useMaiaEngine` | Policy prior + WDL at a node | Already returns a full per-ELO curve + WDL from one inference; the MCTS expansion step reads `moveProbabilities` (top-k truncated at ~90% cumulative mass per SEED-082) as the prior — no new Maia call shape needed. |
| `vitest` | Unit-testing the MCTS core (backup rule, selection, priority scheduler) in isolation | The custom backup rule is exactly the kind of pure-function logic (`backup(node, childValues, priors) -> value`) that should get dense unit tests with fixed node budgets for determinism (SEED-082: "fixed node budgets in tests → reproducible"), decoupled from the Worker/async plumbing. |

## Installation

```bash
# No new frontend dependencies for this milestone.
# (Optional, only if node budgets later scale past ~1-2k pending evaluations:)
# npm install tinyqueue
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|---------------------------|
| Hand-rolled MCTS core (custom selection + custom backup) | A maintained MCTS/UCT library (if one existed) | Only if the algorithm were textbook UCT/PUCT (uniform backup, single value estimate per node, standard `argmax(Q + c·U)` selection). SEED-082's backup rule is explicitly non-standard: non-root nodes back up a **Maia-prior-weighted expectation** over expanded children (not a mean-of-visits, not a max), with the *weighting distribution itself switching sides* (opponent-ELO Maia prior at opponent nodes, your-ELO Maia prior at your nodes) while **root stays plain max**. No published MCTS library supports asymmetric per-ply-parity backup semantics or a two-model (policy-from-Maia, value-from-Stockfish) node evaluator; retrofitting one would cost more than writing the ~150-line core fresh. |
| Extend `useStockfishGradingEngine`'s worker into an N-worker pool | A single shared Stockfish worker doing sequential MultiPV grading | Sequential grading is what Phase 151.1 already does for the root — fine there because it's one search. MCTS needs many *independent* leaf evaluations across the tree per iteration; sequential grading would serialize the whole search behind one WASM instance's queue. Only fall back to single-worker if pool-memory pressure (see Q1/Q3) forces pool size to 1 on constrained devices — treat that as a degraded mode, not the default. |
| Plain array + linear-scan priority pick | `tinyqueue`/`heap-js` | Switch once profiling shows the pending-node set regularly exceeds ~1–2k entries (unlikely at "seconds-scale, few hundred nodes" per SEED-082) or once time-pressure/ambitious-phase features raise node budgets by an order of magnitude. |
| Raw `postMessage`/`onmessage` worker protocol per pool member | Comlink/workerpool | Only if a *future* refactor extracts a shared low-level "StockfishWorkerClient" class to de-duplicate the now-triplicated worker-lifecycle/state-machine code across `useStockfishEngine`, `useStockfishGradingEngine`, and the new pool members — that's a legitimate internal refactor (flagged below), but it's still hand-rolled, not a wrapper-library adoption. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| SharedArrayBuffer / Stockfish multi-threaded WASM build | Requires COOP/COEP cross-origin isolation; COOP `same-origin` severs `window.opener`, which breaks the existing Google-OAuth popup flow (a hard, already-documented constraint, D-3/SEED-082). Deployment-level decision explicitly out of scope for this milestone. | The already-decided **pool of 2–4 single-threaded Stockfish workers**, each independently grading a different leaf — embarrassingly parallel, matches the "many shallow evals" workload (unlike lichess's one-deep-search workload), and needs zero cross-origin headers. |
| `onnxruntime-web` `numThreads > 1` for Maia | Same SAB/cross-origin-isolation requirement as above; also a documented ORT issue (microsoft/onnxruntime #26858) where multi-threaded sessions can hang indefinitely with external-data-file models. `maia-worker.js` already hard-codes `numThreads = 1` for this exact reason (Phase 136 D-3) — do not touch it while adding the Stockfish pool. | Leave Maia's WASM backend single-threaded (or WebGPU, which is a separate GPU execution path with no relation to the Stockfish CPU-side worker pool — the two coexist without contention). |
| A generic/off-the-shelf MCTS npm package | None exist in a maintained state (`mcts` is 2017-era, unmaintained) and none could express the asymmetric Maia-weighted backup rule without being gutted and rewritten anyway. | Hand-rolled core behind the SEED-082-mandated small interface: `search(position, budget) -> rankedRootLines`, with incremental/anytime emission — this is also the documented guardrail so a depth-limited expectimax fallback is swappable in a day if MCTS tuning stalls. |
| App-level Zobrist/transposition cache across MCTS nodes | Already explicitly rejected in SEED-082 ("No app-level Zobrist/transposition caching — positions diverge too fast to pay off"). Stockfish's own internal TT already gives partial reuse for free within a single grading search. | Rely on Stockfish's internal hash table (small per-instance `Hash` UCI option, see Q1) plus the existing per-FEN `pv[0]`-keyed grade `Map` cache pattern already used by `useStockfishGradingEngine` — that cache is ELO-independent and reusable as-is for pool workers. |
| A wrapper/RPC library for worker communication (Comlink et al.) | Doesn't fit a streaming, cancelable, stateful UCI session (`stop`/`bestmove` interleaving, stale-result discarding) — every existing hook in this codebase solved that with a hand-rolled state machine (`idle`/`thinking`/`stopping` + `stopPendingRef`), and a wrapper library would fight that pattern rather than help it. | Copy the `idle`/`thinking`/`stopping` state-machine pattern per pool worker (see Q1). |
| Bumping Stockfish/onnxruntime-web versions "while we're in there" | Both are already at the latest published npm version (verified 2026-07-05); a version bump is an unrelated, separately-testable change with its own regression surface (NNUE net compatibility, UCI option changes). | Leave both pinned; track version bumps as their own quick task if/when upstream ships something relevant (e.g. a smaller NNUE net). |
| Fitting per-ELO leaf sigmoids, time-pressure modeling, or a trap-finder UI as part of this stack | All three are explicitly deferred in SEED-082 ("Deferred by design"). Pulling them in now inflates the MVP1 surface the seed deliberately kept small. | Ship MVP1 (single position, modal-path display, lichess global eval→win% sigmoid, live-refining top-n + arrows) first; each deferred item is its own later phase with its own research if needed. |

## Stack Patterns by Variant

**Q1 — Stockfish.wasm worker pool pattern (no maintained multi-instance library exists; hand-roll):**

- There is no maintained "Stockfish worker pool" package — `stockfish` (npm) ships the single-instance engine only; nothing on npm wraps it in a pool. Build a thin `StockfishGradingPool` that is structurally `N` copies of `useStockfishGradingEngine`'s worker (same `ENGINE_PATH`, same classic-Worker/non-module load, same `idle`/`thinking`/`stopping` state machine, same `stopPendingRef` stale-result guard, same tab-hide pause) rather than inventing a new worker protocol.
- **Pool size: 2–4, per SEED-082.** Each worker is a fully independent WASM instance with its own copy of the ~7 MB NNUE net loaded into its own linear memory — pool memory scales roughly linearly with pool size (not shared). Cap `Hash` (UCI option) low per instance (e.g. 8–16 MB) since MultiPV/searchmoves-restricted shallow grading doesn't benefit from a large hash table, and a 4-worker pool at default Hash settings would otherwise multiply memory pressure for no search-quality gain.
- **Mobile ceiling matters.** This is a mobile-first PWA (CLAUDE.md). iOS Safari's per-tab WebKit memory ceiling is the binding constraint, not desktop RAM. Default the pool size conservatively (start at 2, not 4) and consider `navigator.hardwareConcurrency` as a rough proxy to size up on desktop-class hardware — Chrome-only `navigator.deviceMemory` is not available on Safari, so don't gate on it as the sole signal.
- **Node-evaluation priority queue**: not a separate library-worthy structure at SEED-082's stated node-budget scale (hundreds of evaluations per search). A plain array of pending `{node, priority}` entries with a linear max-scan on each worker-free event is correct and fast enough; priority is simply "current backed-up value of the root child this node descends from" (ties broken by shallower depth or earlier insertion, kept deterministic per the "no Dirichlet noise, deterministic tie-breaking" requirement).
- **Reuse, don't rebuild, the grade cache.** `useStockfishGradingEngine`'s existing `pv[0]`-keyed, ELO-independent, FIFO-capped `Map<fen, Map<san, MoveGrade>>` cache is exactly the leaf-eval cache the pool needs — extend its shape to a pool-shared cache (position-only key, no per-worker fragmentation) rather than one cache per worker instance.

**Q2 — MCTS in TypeScript/browser (hand-roll, no library):**

- No maintained TS/JS MCTS library exists that would fit (see "Alternatives Considered"). Build the core as a small, pure, synchronously-testable module: `selectAndExpand(tree) -> leafNode`, `evaluateLeaf(leafNode) -> Promise<value>` (dispatches to the Stockfish pool + Maia hook), `backup(path, value, priors) -> void` (the custom asymmetric rule), `emitRankedLines(tree) -> RankedLine[]` (anytime read, callable after every completed iteration or on a UI-driven cadence).
- **Anytime/incremental emission is native to MCTS**, not something to add: after any number of completed iterations, `emitRankedLines` just reads current visit counts / backed-up values off root children — no special "partial result" plumbing needed beyond calling it on a timer or on each iteration boundary and pushing into React state (mirrors the existing `commitDisplayedGradeMap`/`commitPvSnapshot` "commit a snapshot on every info-line-equivalent event" pattern already used by both Stockfish hooks).
- **Guardrail per SEED-082**: keep the tree/search behind `search(position, budget) -> rankedRootLines` so a depth-limited expectimax is a same-interface fallback if MCTS tuning stalls — this argues for the core living in one small, dependency-free module (e.g. `frontend/src/lib/flawchessEngine/`) independent of the React hook that drives it, exactly like `maiaEncoding.ts` is decoupled from `useMaiaEngine`.
- **Determinism for tests**: no Dirichlet noise, fixed node budgets, deterministic tie-breaking (explicit SEED-082 requirement) — this also means the core module needs zero `Math.random()` calls, which in turn means no MCTS library's default UCB1/PUCT exploration-noise behavior can be reused as-is even if one existed.

**Q3 — onnxruntime-web concurrency with the Stockfish pool:**

- No version or config change needed. `maia-worker.js` already forces `ort.env.wasm.numThreads = 1` unconditionally (comment: "NEVER > 1 — no cross-origin isolation," Phase 136 D-3) and this constraint is orthogonal to the Stockfish pool — Maia's WASM execution stays single-threaded regardless of how many Stockfish workers run.
- If Maia falls back to its WebGPU path (`ort.env.wasm.numThreads` set before session creation on the WASM fallback only — WebGPU sessions don't spawn wasm worker threads at all), it executes on the GPU, a resource pool entirely separate from the CPU-bound Stockfish workers — no contention to manage.
- **Real contention is CPU core count, not ORT config.** 2–4 Stockfish workers + 1 Maia WASM/WebGPU worker running concurrently on a low-core mobile device will compete for CPU time regardless of ORT flags; this is a scheduling/UX concern (how snappy does Maia's chart stay while the pool churns) not a library/version concern — no action needed at the stack-selection level, but worth flagging for the phase-planning stage as a real-device profiling item.
- `onnxruntime-web` known threading hang (microsoft/onnxruntime #26858, `numThreads > 1` + external data files) doesn't apply here — Maia's config never sets `numThreads > 1`, and the model isn't loaded via external data files.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-------------------|-------|
| `stockfish@18.0.8` (lite-single build) | `onnxruntime-web@1.27.0` | No interaction — two independent classic Workers, no shared runtime, no bundler-level conflict (both are non-module scripts served from `public/`, untouched by Vite). |
| Pool of N `stockfish-18-lite-single.js` Workers | Same-origin, no COOP/COEP | Verified compatible with the existing OAuth-popup constraint precisely because it avoids SharedArrayBuffer — this was the whole point of the "no SAB" architecture decision in SEED-082 and it holds unchanged for N≥2 independent instances (each instance is single-threaded internally; multiplying instances doesn't reintroduce a SAB requirement). |
| MCTS core module | React 19 hooks | Keep the core framework-agnostic (plain functions/classes) so it can be unit-tested with `vitest` without mounting hooks — the driving hook (`useFlawChessEngine` or similar) is a thin adapter, mirroring how `maiaEncoding.ts` (framework-agnostic) is separated from `useMaiaEngine` (the hook adapter). |

## Sources

- npm registry (direct queries, 2026-07-05): `onnxruntime-web` (latest 1.27.0, published 2026-06-19), `stockfish` (latest 18.0.8, published 2026-06-15), `chess.js` (latest 1.4.0), `mcts` (latest 0.0.8, published 2017 — unmaintained), `mcts-js`/`monte-carlo-tree-search`/`ts-mcts`/`fast-mcts` (none exist), `tinyqueue` (3.0.0), `heap-js` (2.7.1), `comlink` (4.4.2), `workerpool` (10.0.3), `threads` (1.7.0) — HIGH confidence (primary registry data).
- Codebase read (2026-07-05): `frontend/src/hooks/useStockfishEngine.ts`, `useStockfishGradingEngine.ts`, `useMaiaEngine.ts`, `frontend/public/maia/maia-worker.js` (confirmed `numThreads = 1` forced, Phase 136 D-3), `frontend/public/engine/` + `frontend/public/maia/` vendored asset listing — HIGH confidence (ground truth).
- `.planning/seeds/SEED-082-human-playable-line-engine.md` — locked design spec (algorithm, architecture, deferred scope) — HIGH confidence (project decision record, treated as authoritative, not re-litigated).
- WebSearch (2026-07-05): stockfish.wasm worker/threading limits (lichess-org/stockfish.wasm, nmrugg/stockfish.js, DeepWiki Stockfish thread-management docs) — MEDIUM confidence (community sources, cross-checked against the codebase's own already-working single-thread-per-worker pattern).
- WebSearch (2026-07-05): onnxruntime-web `env.wasm` flags (`numThreads`, `wasmPaths`, `simd`, proxy worker) and known multi-thread hang issue (microsoft/onnxruntime#26858, #25666) — MEDIUM-HIGH confidence (official onnxruntime.ai docs + GitHub issue tracker), cross-checked directly against `maia-worker.js`'s actual config.
- WebSearch (2026-07-05): Maia-2 skill-aware-attention architecture (CSSLab/maia2, NeurIPS 2024 paper) — MEDIUM confidence, background only; not actionable for this milestone (model already vendored is Maia-3/"Chessformer", out of scope to re-litigate the model choice here).

---

## Superseded prior research (v1.30 Forcing-Line Tactic Gate — kept for reference, not this milestone)

The section below is retained from the previous stack research pass (2026-06-29, MultiPV=2 + JSONB storage for the backend tactic gate). It is unrelated to the v2.0 FlawChess Engine milestone above and should not be treated as current guidance for this milestone — kept only so the historical backend research isn't lost.

**Domain:** Chess tactic analysis — MultiPV=2 engine pass + JSONB persistence (v1.30 Forcing-Line Gate)
**Researched:** 2026-06-29

Verdict: no new PyPI dependency required. `python-chess` 1.11.x ships a typed `multipv` overload on `UciProtocol.analyse()` returning `List[InfoDict]` (best-first, `info_list[0]` = best line, guard `len(info_list) > 1` for the second line). SQLAlchemy `dialects.postgresql.JSONB` (already used in `llm_log.py`) plus asyncpg's automatic JSONB codec cover storage with no `MutableDict`, no manual codec registration, and no TOAST configuration (blobs ~600 bytes, well under the ~2KB TOAST threshold). `EnginePool` needed a new `_analyse_multipv2()` sibling method (parallel to `_analyse_with_pv()`) since `multipv=2` changes the return type. No UCI `Hash`/`Threads` changes, no GIN index, no sidecar table at launch.

Full detail (exact API signatures, `EnginePool` code, Alembic migration, sources) lives in git history for `.planning/research/STACK.md` prior to 2026-07-05 if needed again.
