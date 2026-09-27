---
quick_id: 260927-8xn
status: complete
commits: [9064ab922, d323a5379, e55b26a93, 853ab2dd5]
---

# Quick 260927-8xn Summary

All seven behavior-neutral findings from the 2026-09-27 FlawChess engine review shipped. No SEED-170 surface touched (verified via `git diff --quiet a7a30c659` against select.ts/findability.ts/policyTemperature.ts/fallbackExpectimax.ts/deadlineSearch.ts — clean).

## Per-item outcome

- **8XN-1** (chart fulfilment-handler throw settles pending policy entries): `useMaiaEngine.ts`'s `issue()` fulfilment handler now wraps `mergeMaiaResult` + `cacheResult` in try/catch. On throw: `Sentry.captureException(err, { tags: { source: 'maia-chart' } })`, then `failPolicyPending(req.fen, elo, reason)` for every elo in the request, then clears `inFlightRef`/`isAnalyzing` (no pump, matching the rejection branch). New test: a malformed rung (`policy: null`) throws inside `softmaxPolicyByContext`, the pending waiter rejects, `getPendingPolicy` returns undefined, Sentry captured once, `isAnalyzing` returns to false.
- **8XN-2** (policy() AbortSignal drops undispatched requests): `EngineProviders.policy` and `MaiaQueue.policy` both gained an optional 4th `signal?: AbortSignal` param, following `grade`'s own precedent (structurally assignable — confirmed by the existing 3-arg fakes throughout `mctsSearch.test.ts` compiling unchanged). `maiaQueue.requestPolicy` registers a `{ once: true }` abort listener that splices an UNDISPATCHED request out of `pending` and resolves it `{}`; an already-dispatched request is untouched (in-flight ONNX can't be interrupted). The chart-owned `getPendingPolicy` join path is deliberately NOT signal-aware. `mctsSearch.ts`'s `dispatchExpansion` forwards its own signal as the 4th arg to `policy()`.
- **8XN-3** (one chess.js instance per expansion): new `treeCommon.ts` export `expandChildPositions(parentFen, ucis, rootMover)` builds ONE `new Chess(parentFen)` and reuses it (move/fen/terminal/undo) for every candidate UCI, replacing `mctsSearch.ts`'s per-candidate `applyUciMoveFen` calls in `applyExpansion`. Bit-identical to the old path (chess.js `undo` restores every FEN field and decrements the position count). Proven by a new parity test suite across en passant, promotion, castling, mate-in-1, stalemate, and fifty-move-draw fixtures — all independently verified against chess.js before writing.
- **8XN-4** (Maia policy cache keyed on first four FEN fields): `maiaPolicyCache.ts`'s private `cacheKey` now normalizes to `board side castling ep|elo` instead of the full FEN. Maia's own encoding reads only fields 1-2 and legal-move generation ignores the halfmove/fullmove counters, so a chart-vs-engine or transposition counter mismatch no longer misses the cache or pending registry. The Stockfish grade cache in `workerPool.ts` is unchanged (its halfmove clock matters for fifty-move handling) — confirmed via `grep -c "function cacheKey(fen: string, gradingDepth: number)"` returning 1.
- **8XN-5** (worker transfers result buffers): `maia-worker.js`'s analyze-message handler now posts the `result` message with a transfer list of every rung's `policy.buffer`/`wdl.buffer`. Ownership check (per plan): confirmed each buffer comes from `analyze()`'s own `.slice()` calls — fresh, owned, non-shared, never a view into ORT/wasm memory (which is disposed in `analyze()`'s own `finally`, before postMessage runs) — and confirmed the init-time webgpu warmup `analyze()` call never posts a result. **Not skipped** — shipped as specified.
- **8XN-6** (honest grade-cache merge comment): `workerPool.ts`'s `write()`/`read()` comments corrected — a same-UCI-same-depth re-grade is NOT guaranteed to be "the same computation" (CACHE-04's own subset/full-set measurement proves it can differ), and a `read()` hit can be a union of grades written under different candidate sets across separate PUCT rounds, not one coherent search. Comment-only: `git diff` against `a7a30c659` on this file contains only `+`/`-` lines that are blank or start with `//`/`*`/`/*`.
- **8XN-7** (empty non-abort grade closes a dead end): `mctsSearch.ts`'s `dispatchExpansion` now closes the leaf as a dead end (empty candidateMap, no children, no visit bump, no `nodesEvaluated` increment) when `grade()` resolves an empty Map for a non-empty candidate set, is not an abort, and the leaf is not the root. Partial maps are untouched (still fall back to `NEUTRAL_EXPECTED_SCORE` per-candidate).

## 8XN-7 root exemption confirmation

Per the orchestrator's amendment, the ROOT is exempt from the dead-end close: an empty grade() Map at the root leaves `rankedLines` populated with the root's Maia candidates at `NEUTRAL_EXPECTED_SCORE` (today's unchanged behavior), rather than emptying the ranked list and forcing `selectBotMove` into `fallbackMove` (a uniformly random legal move). Covered by `mctsSearch — 8XN-7 empty non-abort grade() closes a dead end > root exemption` — asserts `rankedLines.length > 0` and every line's `practicalScore === 0.5` when `grade()` always returns an empty Map, including at the root.

## 8XN-7 revert-proof runs

Per plan: temporarily deleted the `dispatchExpansion` guard (`if (grades.size === 0 && !signal.aborted && !leaf.isRoot) { ... }`), ran the 8XN-7 describe block, restored the guard, ran it again.

- **Guard removed:** `mctsSearch — 8XN-7 empty non-abort grade() closes a dead end > non-root: ...` **FAILED** — `expected 0.4981608297404997 to be close to 0.676211637485054` (the leaf's practicalScore was corrupted toward the fabricated NEUTRAL-derived value instead of its own real grade). The `root exemption` case still **PASSED** (2 passed / 27 skipped in that run, since `-t 8XN-7` scoped the run and only the non-root case failed).
- **Guard restored:** all 3 tests in the describe block **PASSED** (`3 passed | 27 skipped`).

## Verification

- Task 1 suite (treeCommon, mctsSearch, fallbackExpectimax, deadlineSearch, selectBotMove): 110 passed.
- Task 2 suite (useMaiaEngine, maiaPolicyCache, maiaQueue, maiaWorkerScript, maiaWorkerHost, useGemSweep): 182 passed.
- Task 3 suite (maiaQueue, mctsSearch, useFlawChessEngine, useBotGame): 168 passed.
- Full frontend gate from repo root: `npm --prefix frontend run lint` (clean), `npm --prefix frontend run build` (tsc -b + vite build, clean — pre-existing CSS/chunk-size warnings unrelated to this change), `npm --prefix frontend run test` (275 files, 4408 passed), `npm --prefix frontend run knip` (clean, only a pre-existing config hint).
- `fenVariant()` helpers in `maiaPolicyCache.test.ts` and `maiaQueue.test.ts` rewritten to vary the BOARD field (kings-only, non-adjacent king-pair enumeration) instead of only the fullmove counter, since 8XN-4 collapsed counter-only variants to the same cache key; LRU/capacity tests at `MAIA_POLICY_CACHE_MAX + 1` entries still pass under the new helper.

## Deviations from Plan

None functionally — plan executed as written, including the orchestrator's root-exemption amendment to 8XN-7.

Commit granularity: the plan offered "one commit per item" or a coarser grouping as alternatives ("one fix commit that names both" / "one commit per item is also fine"). Task 2's three items (8XN-1, 8XN-4, 8XN-5) landed in a single combined `fix(...)` commit rather than the suggested `fix` + `perf` split, since all three touch the same Maia subsystem and were developed together; this is a commit-message-granularity choice, not a scope or correctness deviation.

## Known Stubs

None.

## Self-Check: PASSED

All files listed in `files_modified` found on disk; all four commits (9064ab922, d323a5379, e55b26a93, 853ab2dd5) found in git history.
