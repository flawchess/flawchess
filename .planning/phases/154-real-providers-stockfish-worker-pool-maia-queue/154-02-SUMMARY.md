---
phase: 154-real-providers-stockfish-worker-pool-maia-queue
plan: 02
subsystem: engine
tags: [maia, onnx, web-worker, async-queue, vitest]

# Dependency graph
requires:
  - phase: 153-pure-search-core-guardrail-backup-mcts-fallback
    provides: "Frozen EngineProviders/Side contract this plan implements for policy()"
  - phase: 151-maia-in-the-browser-all-position-surfaces
    provides: "maskAndSoftmax/MAIA_ELO_LADDER (maiaEncoding.ts), the {type:'analyze', fen, eloInputs} maia-worker.js protocol, and sanToUci (sanToSquares.ts) — all reused verbatim"
provides:
  - "maiaQueue.ts: createMaiaQueue() factory implementing EngineProviders.policy() with a dedicated Maia worker, deduped narrow-ELO batching, (fen,elo)-keyed cache, and a no-drop async FIFO queue"
  - "Lazy spawn, terminate() lifecycle, and Sentry-forwarded worker errors under a distinct 'maia-queue-worker' tag"
affects: [155-react-hook-anytime-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Non-React fork of an already-shipped single-worker hook (useMaiaEngine) into a plain-module async queue, reusing the SAME wire protocol"
    - "Proper async FIFO queue (never drop-and-reissue) for a consumer where every request needs an answer, contrasted with useMaiaEngine's UI-driven single-in-flight-drop discipline"
    - "Same-FEN request batching collapsed into one worker analyze call via a deduped Set of ELOs — D-04's 'narrow ELOs only' contract"

key-files:
  created:
    - frontend/src/lib/engine/maiaQueue.ts
    - frontend/src/lib/engine/__tests__/maiaQueue.test.ts
  modified: []

key-decisions:
  - "The requestPolicy pipeline (dedup/cache/FIFO/SAN-UCI boundary) was committed as Task 1 without terminate()/Sentry/graceful-degradation, then Task 2 layered worker lifecycle + error forwarding on top — a real, independently testable split rather than one combined commit, since Task 1's own action already specifies ENGINE_PATH/worker send-and-receive as in-scope."
  - "Batching: multiple pending policy() calls sharing the SAME fen are collapsed into ONE analyze message with the deduped distinct ELOs across the whole matching batch (not just literal duplicate-ELO pairs) — an internal dispatch optimization within D-04's contract, not a change to policy()'s per-call semantics."
  - "On any error path (worker error message, or Worker() construction throwing), affected policy() promises resolve to `{}` (empty Record) rather than rejecting — matches EngineProviders.policy's Promise<Record<string,number>> return type and workerPool.ts's established resolve-empty-on-failure precedent from Plan 01, so mctsSearch.ts never has to catch a rejected policy() promise."
  - "The MAIA_ELO_LADDER identifier is not referenced anywhere in maiaQueue.ts, including comments — the SC-style grep audit (`grep -n \"MAIA_ELO_LADDER\" maiaQueue.ts` returning nothing) checks literal text, so even a contrastive code comment mentioning the identifier was reworded to describe it without repeating the name."

patterns-established:
  - "Pattern: forking an already-proven single-instance Worker hook (useMaiaEngine) into a non-React async queue by keeping the wire protocol identical and replacing only the request-shape/queueing discipline"

requirements-completed: [POOL-03, POOL-04]

coverage:
  - id: D1
    description: "policy(fen, elo, side) resolves to a UCI-keyed Record for the requested elo, with the SAME entry count as maskAndSoftmax's SAN-keyed output (no silent sanToUci-null drops)"
    requirement: POOL-03
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#has the same entry count as maskAndSoftmax for a promotion/castling/en-passant position"
        status: pass
    human_judgment: false
  - id: D2
    description: "Two requests for the same fen collapse into ONE analyze call with the deduped distinct-ELO array, never the full ladder"
    requirement: POOL-03
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#requests only the distinct ELOs needed, collapsing two same-ELO requests into one analyze call"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#batches two DIFFERENT ELOs for the same FEN into one analyze call, deduped"
        status: pass
      - kind: smoke
        ref: "grep -n \"MAIA_ELO_LADDER\" frontend/src/lib/engine/maiaQueue.ts (no output)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every policy() call is answered via a proper async FIFO queue (one inference at a time); a repeat (fen,elo) resolves from a separate cache with no second analyze call; the cache evicts FIFO at MAIA_CACHE_MAX"
    requirement: POOL-03
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#resolves every issued policy() promise, never dropping one under concurrent load"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#resolves a repeated (fen, elo) request from cache with no second analyze call"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#does not cache-hit across different ELOs for the same FEN (separate fen|elo keys)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#caps the cache at MAIA_CACHE_MAX entries (FIFO eviction)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The worker is spawned lazily on the first policy() call, never eagerly; terminate() tears it down and a later policy() re-spawns"
    requirement: POOL-04
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#does not construct a Worker until the first policy() call"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#terminate() posts {type:terminate} and calls worker.terminate(); a later policy() re-spawns"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#terminate() resolves any still-pending or in-flight promise rather than hanging it"
        status: pass
    human_judgment: false
  - id: D5
    description: "Worker errors and construction failures forward to Sentry under the distinct 'maia-queue-worker' tag and settle affected promises rather than hanging them (graceful degradation, Pitfall 1)"
    requirement: POOL-04
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#forwards a worker error message to Sentry with the distinct maia-queue-worker tag and settles the in-flight promise"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts#forwards a Worker construction failure to Sentry and resolves pending requests instead of hanging"
        status: pass
      - kind: smoke
        ref: "grep -n \"maia-queue-worker\" frontend/src/lib/engine/maiaQueue.ts"
        status: pass
    human_judgment: false
  - id: D6
    description: "SC4 real-device mobile-memory-ceiling UAT (no tab reload/crash across a multi-position review session, pool + Maia queue combined) and actual eval-bar mutual-exclusion wiring"
    verification: []
    human_judgment: true
    rationale: "No React hook/UI exists to drive maiaQueue.ts (or workerPool.ts) until Phase 155 wires both into /analysis — this is a HUMAN-UAT gate deferred by design, tracked in 154-VALIDATION.md Manual-Only Verifications, consistent with 154-01-SUMMARY.md's own deferral note"

# Metrics
duration: 25min
completed: 2026-07-06
status: complete
---

# Phase 154 Plan 02: Maia Policy Queue Summary

**`maiaQueue.ts` — a dedicated, lazily-spawned Maia policy Web Worker implementing `EngineProviders.policy()` with deduped narrow-ELO batching, a separate `(fen, elo)` cache, and a no-drop async FIFO queue**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-06T16:22:36Z (approx.)
- **Completed:** 2026-07-06T16:47:00Z (approx.)
- **Tasks:** 2
- **Files modified:** 2 (both new)

## Accomplishments

- `createMaiaQueue()`: a plain-module fork of `useMaiaEngine`'s `{type:'analyze', fen, eloInputs}` protocol implementing `EngineProviders.policy(fen, elo, side)` — structurally assignable to the frozen Phase 153 contract, verified by a type-level test
- D-04 dedup/batching: multiple pending requests sharing the same FEN collapse into ONE `analyze` call carrying only the distinct ELOs needed (a deduped `Set`), never the full 21-rung ladder — confirmed by both a same-ELO dedup test and a different-ELO batching test, plus a clean `grep -n "MAIA_ELO_LADDER"` audit
- SAN→UCI boundary conversion via the existing `sanToUci` helper, verified to produce the SAME entry count as `maskAndSoftmax`'s SAN-keyed output across promotion, castling, and en-passant fixture positions — closing Pitfall 4's flagged (and previously untested-at-full-scale) risk
- A proper async FIFO queue — unlike `useMaiaEngine`'s UI-driven single-in-flight-drop discipline, every `policy()` call issued gets an answer; proven with a three-concurrent-request no-drop test (Open Question 2, resolved)
- A separate `(fen, elo)`-keyed cache (distinct from `useMaiaEngine`'s per-FEN cache), FIFO-capped at `MAIA_CACHE_MAX`, verified for cache-hit-skips-analyze, no-cross-elo-cache-hit, and cap-eviction behavior
- Worker lifecycle: lazy spawn on the first `policy()` call (D-02, zero Worker instances before that), `terminate()` posting `{type:'terminate'}` + `worker.terminate()` + full state reset so a later `policy()` re-spawns
- `{type:'error'}` worker messages and `Worker()` construction failures both forward to `Sentry.captureException` under the distinct `'maia-queue-worker'` tag (vs. the chart's `'maia-worker'` tag) and settle every affected promise with `{}` rather than hanging (Pitfall 1 graceful-degradation floor)

## Task Commits

Each task was committed atomically:

1. **Task 1: requestPolicy pipeline — dedup + async FIFO queue + cache + SAN→UCI boundary** - `37e72159` (feat)
2. **Task 2: Worker lifecycle, Sentry forwarding, graceful degradation** - `fd8aed32` (feat)

_Note: Task 1 was committed as a real, independently green subset (dedup/cache/FIFO/SAN→UCI, with a minimal worker send/receive already required by Task 1's own action) — not a rewritten-then-discarded scaffold. Task 2 layered lazy-spawn semantics, `terminate()`, Sentry forwarding, and the construction-failure graceful-degradation path on top, matching the plan's own task boundary._

## Files Created/Modified

- `frontend/src/lib/engine/maiaQueue.ts` (237 lines) - `createMaiaQueue` factory, `MaiaQueue` type, `ENGINE_PATH`/`MAIA_CACHE_MAX` constants, the (fen,elo) cache + async FIFO queue + worker lifecycle
- `frontend/src/lib/engine/__tests__/maiaQueue.test.ts` (280 lines) - mock-Worker vitest suite: dedup/batching, entry-count parity (promotion/castling/en-passant), cache-hit/cross-elo/FIFO-cap, no-drop concurrent FIFO, lazy-spawn, terminate + re-spawn, Sentry error forwarding (module-mocked, both worker-error and construction-failure paths), type-level `EngineProviders.policy` assignability

## Decisions Made

- Batching goes beyond the literal "two same-ELO requests" example: ANY set of pending requests sharing the same FEN — regardless of how many distinct ELOs they carry — is dispatched as one `analyze` call with the deduped ELO list. This stays within D-04's "narrow ELOs, not the full ladder" contract while also covering the RESEARCH.md "batching caveat" (both `elo.w` and `elo.b` pending at once for the same node).
- Failure paths (worker error, construction throw) resolve affected `policy()` promises to `{}` rather than rejecting, mirroring `workerPool.ts`'s established resolve-empty-on-abort/failure precedent from Plan 01 — keeps `mctsSearch.ts`'s future integration free of a `try/catch` around every `policy()` await.
- A code comment referencing the full-ladder constant by name was rewritten to describe it without the literal identifier, since the phase's own SC5-style acceptance grep (`grep -n "MAIA_ELO_LADDER" maiaQueue.ts` expecting no output) checks literal text, not semantic intent.

## Deviations from Plan

None — plan executed exactly as written. All two tasks' `<behavior>`/`<action>`/`<acceptance_criteria>` were implemented and verified as specified; no bugs, missing critical functionality, or blocking issues were encountered.

## Requirements Completed

- **POOL-03** — fully closed by this plan (Maia move-probability distributions per node, per-side ELO, dedicated worker reusing v1.32 inference).
- **POOL-04** — code-complete as of this plan (Plan 01's adaptive Stockfish-pool sizing/lazy-spawn/abort surface + this plan's isolated Maia lazy-spawn/terminate lifecycle). The requirement's SC4 real-device mobile-memory-ceiling UAT and the actual eval-bar mutual-exclusion signal remain deferred to Phase 155 (the first phase with a UI to drive either) — this is a pre-existing, explicitly-scoped deferral from CONTEXT.md D-03, not new scope creep from this plan. Tracked in `154-VALIDATION.md`.

## Issues Encountered

None beyond the expected FEN-validity fixture correction during test authoring: the initial no-drop-FIFO and cache-cap tests used placeholder strings (`'FEN_A'`, `'FEN_0'`, etc.) that are not parseable FENs — `maskAndSoftmax`'s `new Chess(fen)` call throws on a malformed FEN. Replaced with a `fenVariant(n)` helper generating distinct-but-valid starting-position FENs (varying only the fullmove counter) before running the tests. No production code was affected.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`maiaQueue.ts` is a complete, unit-tested implementation of `EngineProviders.policy()`, structurally assignable to the frozen Phase 153 contract, ready for Phase 155 to import alongside `workerPool.ts` (Plan 01) into a React hook (`useFlawChessEngine.ts`). Both providers now exist for `mctsSearch.ts` to consume for real. SC4's real-device mobile-memory-ceiling UAT and the eval-bar mutual-exclusion wiring (D-03) are the two items Phase 155 must still close, both already flagged and tracked (154-VALIDATION.md; CONTEXT.md D-03).

---
*Phase: 154-real-providers-stockfish-worker-pool-maia-queue*
*Completed: 2026-07-06*

## Self-Check: PASSED

- FOUND: frontend/src/lib/engine/maiaQueue.ts
- FOUND: frontend/src/lib/engine/__tests__/maiaQueue.test.ts
- FOUND: commit 37e72159
- FOUND: commit fd8aed32
