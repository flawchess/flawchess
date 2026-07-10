# Phase 154: Real Providers (Stockfish Worker Pool + Maia Queue) - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the fabricated `EngineProviders` (fabricated in the Phase 153 tests) with real
browser-side implementations behind the frozen `{policy, grade}` interface:

- **`workerPool.ts`** — a pool of 2–4 single-threaded Stockfish.wasm workers that grade
  candidate moves/leaves in parallel, fronted by a priority queue that schedules grading
  work toward nodes under the currently-highest-scoring root line (POOL-01, POOL-02). No
  SharedArrayBuffer, no site-wide COOP/COEP headers.
- **`maiaQueue.ts`** — a dedicated Maia policy worker (separate instance from the existing
  `useMaiaEngine`) that supplies per-node UCI-keyed move-probability distributions keyed by
  an explicit per-side ELO parameter, reusing the v1.32 client-side ONNX inference glue
  (POOL-03).
- Adaptive pool sizing so the browser tab stays within mobile Safari's memory ceiling, and
  a guarantee that the pool never runs concurrently with the standalone `useStockfishEngine`
  eval bar on the same position (POOL-04).

Requirements: POOL-01..04. **No React hook, no UI in this phase** — that's Phases 155–157.
The `SearchRunner`/`EngineProviders`/`SearchBudget`/`RankedLine`/`EngineSnapshot` shapes are
frozen from Phase 153 and are NOT re-opened here.

</domain>

<decisions>
## Implementation Decisions

### Adaptive pool sizing (POOL-01, POOL-04)
- **D-01 Cap + mobile floor:** Desktop pool size = `clamp(navigator.hardwareConcurrency − 2, 2, 4)`;
  mobile = 2 workers. "Mobile" is detected by `hardwareConcurrency ≤ 4` **OR**
  `matchMedia('(pointer: coarse)')` — deliberately NOT UA sniffing (brittle) and NOT
  `navigator.deviceMemory` (unavailable/coarse on Safari). Pool size and both detection
  thresholds are named tunable constants, revisited after the real-device UAT (SC4).

### Worker warm-up / lifecycle (POOL-01, POOL-04)
- **D-02 Lazy spawn on first request:** The 2–4 SF workers and the Maia ONNX worker are
  created on the first engine search (via an `enabled`-style gate, mirroring the existing
  `useStockfishGradingEngine`/`useMaiaEngine` worker lifecycle), and terminated on
  idle/unmount. Keeps idle memory low — the binding concern on mobile Safari — at the cost
  of a slightly slower first result (WASM + ONNX load). No eager page-load spawn.

### Eval-bar mutual exclusion (POOL-04)
- **D-03 Engine wins; the "engine busy" gate is wired in Phase 155:** When the FlawChess
  Engine pool runs a position, the standalone `useStockfishEngine` eval bar pauses on that
  same position (the engine already computes an objective root eval, so the bar is redundant
  during the run). **Phase 154's obligation:** make the pool cleanly startable / stoppable /
  abortable (per-worker stop-before-go, drop-in-flight on navigation) so a caller can gate
  it. The actual shared "engine active" signal that pauses the eval bar lives in the Phase
  155 hook — **flag to the researcher.** 154 exposes the abort/lifecycle surface; it does not
  itself reach into the eval-bar hook.

### Maia inference granularity (POOL-03)
- **D-04 Only needed ELOs, own cache:** Per node, `maiaQueue` requests only the distinct
  ELOs the search needs — the per-side pair `{w, b}` from `budget.elo`, deduped (often 2,
  sometimes 1) — NOT the full 600–2600 ladder. The worker already takes an `eloInputs`
  array, so pass `[eloW, eloB]` (deduped); minimal worker change. Cache is keyed by
  `(fen, elo)` and is **fully separate** from the standalone Maia chart's cache (the roadmap
  already locks a separate worker instance). No shared-cache coupling with `useMaiaEngine`.

### Claude's Discretion
- **SAN↔UCI at the Maia boundary:** `maskAndSoftmax` currently emits SAN-keyed probabilities,
  but `policy()` must return UCI-keyed (D-08 from Phase 153). Convert at the `maiaQueue`
  boundary (or add a UCI-emitting variant) — implementation detail, researcher/planner's call.
- **Priority queue internals (POOL-02):** the exact scheduling data structure and how
  "nodes under the currently-highest-scoring root line" is expressed as a priority key —
  researcher territory. Requirement: verified by a queue-ordering test (not FIFO/arrival).
- **grade() → worker mapping:** one `grade(fen, ucis)` call maps to one worker's
  `searchmoves`-restricted MultiPV search; pool parallelism comes from multiple concurrent
  `grade()` calls (the `budget.concurrency` in-flight expansions from D-03/Phase 153).
  Exact dispatch/queueing across the pool is Claude's discretion.
- Per-worker abort/navigation handling reuses the established stop-before-go / stopPending
  dance from `useStockfishGradingEngine`; grade-depth / movetime-cap constants carry over.
- Worker init/error handling, Sentry forwarding for the Maia worker (classic Worker, no
  Sentry init — forward via message, per `useMaiaEngine`), and cache cap sizes.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked contract + scope (read first)
- `frontend/src/lib/engine/types.ts` — the FROZEN `EngineProviders` / `SearchBudget` /
  `RankedLine` / `EngineSnapshot` contract this phase implements for real. `policy()` returns
  UCI-keyed probs; `grade()` returns `Map<uci, MoveGrade>` white-POV cp keyed by `pv[0]`.
- `.planning/phases/153-pure-search-core-guardrail-backup-mcts-fallback/153-CONTEXT.md` —
  D-01..D-11 (especially D-03 parallel-ready loop / `concurrency`, D-04 `extraRootMoves`,
  D-07 color-keyed ELO, D-08 UCI-everywhere). These are locked upstream — do not re-open.
- `.planning/REQUIREMENTS.md` — POOL-01..04 (this phase) + Out of Scope table (no SAB, no
  site-wide COOP/COEP, no "best move" unqualified framing).
- `.planning/ROADMAP.md` — Phase 154 goal + 5 success criteria (SC5 = the multipv-as-identity
  grep audit: every new MultiPV path keys by `pv[0]`, never the `multipv` rank).

### Reusable implementation precedents
- `frontend/src/hooks/useStockfishGradingEngine.ts` (Phase 151.1) — the single-worker
  batched `searchmoves`-restricted MultiPV grading primitive the pool generalizes:
  **pv[0]-keyed results**, legal-only `searchmoves`, white-POV normalization, stop-before-go /
  `stopPendingRef` serialization, tab-hide pause, FIFO per-FEN cache. `MoveGrade` shape stays
  compatible.
- `frontend/src/hooks/useMaiaEngine.ts` — the single-worker ONNX Maia precedent `maiaQueue`
  forks from: `{type:'analyze', fen, eloInputs}` protocol, worker returns RAW policy/WDL
  logits, `maskAndSoftmax`/`softmaxWdl` applied host-side, single-inference-in-flight
  discipline, Sentry error forwarding.
- `frontend/src/lib/maiaEncoding.ts` — `maskAndSoftmax` (SAN-keyed; convert to UCI at the
  boundary), `MAIA_ELO_LADDER`, `softmaxWdl`, `expectedScore`.
- `public/maia/maia-worker.js` + `public/engine/stockfish-18-lite-single.{js,wasm}` — the
  vendored worker/binary assets the pool + queue instantiate.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useStockfishGradingEngine.ts`: the exact per-node grade() behavior (batched MultiPV,
  pv[0] keying, white-POV sign, stop-before-go, cache) — the pool is N of these coordinated
  by a priority queue, not a rewrite of the grading logic.
- `useMaiaEngine.ts`: worker lifecycle + `{type:'analyze', fen, eloInputs}` protocol —
  `maiaQueue` is a non-React fork of this (no per-ELO-ladder full sweep; request only needed ELOs).
- `SearchBudget.concurrency` + `SearchBudget.elo:{w,b}` (Phase 153, already in `types.ts`):
  the pool serves up to `concurrency` concurrent `grade()` calls; the Maia queue reads the
  per-side ELO pair.

### Established Patterns
- Separate-worker-instance isolation: `useStockfishGradingEngine` is already a second SF
  instance fully independent of the eval bar's `useStockfishEngine`; `maiaQueue` is likewise
  a separate Maia instance from `useMaiaEngine`. This phase extends that pattern to a pool.
- Classic (non-module) `new Worker(path)` for both SF and Maia (Maia uses `importScripts`
  for onnxruntime-web). No module workers.
- `noUncheckedIndexedAccess` + Knip in CI — every new export must be imported (tests count);
  pool/queue array indexing must be narrowed.

### Integration Points
- `workerPool.ts` and `maiaQueue.ts` land in `frontend/src/lib/engine/` (the existing nested
  subsystem). They implement the `EngineProviders` methods; nothing wires them into React
  until Phase 155.
- SC5 grep audit target: any new Stockfish MultiPV consumption path in these files must key
  by `pv[0]` — reuse the shared parser (`uciParser`/`parseInfoLine`), never `parsed.multipv`.

</code_context>

<specifics>
## Specific Ideas

- Pool parallelism model in one line: **the pool is throughput for concurrent `grade()`
  calls, not multi-threading inside one grade** — one grade = one worker's MultiPV search;
  the `budget.concurrency` in-flight expansions from Phase 153 D-03 are what fan out across
  the 2–4 workers.
- Mobile-first sizing intent: on a real iPhone / mid-tier Android, correctness = "tab does
  not reload or crash during a multi-position review session" (POOL-04 SC4). Sizing (D-01)
  and lazy spawn (D-02) both exist to serve that ceiling, not raw speed.
- Eval-bar contention resolved in favor of the engine (D-03): during an engine run the
  objective eval is already available from the root grade, so pausing the redundant standalone
  bar is a feature, not a regression.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (SharedArrayBuffer multithreading, per-ELO
calibrated sigmoids, time-pressure conditioning, and Maia-2 dual-skill adoption remain
formally deferred in REQUIREMENTS.md → Future Requirements. The React hook, anytime UI,
board arrows, and game-review overlay are Phases 155–157.)

</deferred>

---

*Phase: 154-Real Providers (Stockfish Worker Pool + Maia Queue)*
*Context gathered: 2026-07-06*
