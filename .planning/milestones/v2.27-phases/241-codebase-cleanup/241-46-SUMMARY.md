---
phase: 241-codebase-cleanup
plan: 46
subsystem: frontend-tests
tags: [cleanup, comments, vitest, test-titles, engine]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff"
  - phase: 241-03
    provides: "cleanup.py codemod"
  - phase: 241-04
    provides: "TypeScript support in cleanup.py (comments and describe/it/test titles)"
provides:
  - "34 frontend engine test files under frontend/src/lib/engine/__tests__/ free of planning tags in comments and test titles"
affects: [241-60, 241-67, 241-70]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: 1cee4f3aafad21ee45340b5560864b51abf3bf69
plan_head_after: 86a75dc3d973797225dd17d6d6af4e1dd35297ef

key-files:
  created: []
  modified:
    - frontend/src/lib/engine/__tests__/backup.test.ts
    - frontend/src/lib/engine/__tests__/botSampling.test.ts
    - frontend/src/lib/engine/__tests__/botStyle.test.ts
    - frontend/src/lib/engine/__tests__/botStyleBundles.test.ts
    - frontend/src/lib/engine/__tests__/deadlineSearch.test.ts
    - frontend/src/lib/engine/__tests__/engineAssetCache.test.ts
    - frontend/src/lib/engine/__tests__/engineAssetProgress.test.ts
    - frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts
    - frontend/src/lib/engine/__tests__/findability.test.ts
    - frontend/src/lib/engine/__tests__/gradingLadder.test.ts
    - frontend/src/lib/engine/__tests__/iosWebKit.test.ts
    - frontend/src/lib/engine/__tests__/leafScore.test.ts
    - frontend/src/lib/engine/__tests__/liveEngineWorkers.test.ts
    - frontend/src/lib/engine/__tests__/maiaPageKillSentinel.test.ts
    - frontend/src/lib/engine/__tests__/maiaPolicyCache.test.ts
    - frontend/src/lib/engine/__tests__/maiaQueue.test.ts
    - frontend/src/lib/engine/__tests__/maiaWorkerHost.test.ts
    - frontend/src/lib/engine/__tests__/maiaWorkerScript.test.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
    - frontend/src/lib/engine/__tests__/openingBook.test.ts
    - frontend/src/lib/engine/__tests__/ortRuntimeMemoryCap.test.ts
    - frontend/src/lib/engine/__tests__/ortRuntimeSource.test.ts
    - frontend/src/lib/engine/__tests__/policyTemperature.test.ts
    - frontend/src/lib/engine/__tests__/rootSplit.test.ts
    - frontend/src/lib/engine/__tests__/searchTestProviders.ts
    - frontend/src/lib/engine/__tests__/select.test.ts
    - frontend/src/lib/engine/__tests__/selectBotMove.test.ts
    - frontend/src/lib/engine/__tests__/stockfishWorkerSource.test.ts
    - frontend/src/lib/engine/__tests__/styleOpeningLines.test.ts
    - frontend/src/lib/engine/__tests__/treeCommon.test.ts
    - frontend/src/lib/engine/__tests__/wasmSimd.test.ts
    - frontend/src/lib/engine/__tests__/workerPool.test.ts

key-decisions:
  - "Test titles quoting identifiers keep the current name (ENGINE_PATH in maiaQueue.test.ts stays); only the tag was dropped"
  - "Sentry issue short ids (FLAWCHESS-9G, FLAWCHESS-9V, FLAWCHESS-BM) are not planning tags and were left in comments and titles"
  - "Comments that cited a deleted planning artifact as their only content (SUMMARY/PLAN/RESEARCH file names, 'recorded in NNN-SUMMARY.md') were reworded to state the behavior or rule, or the clause was dropped"
  - "searchTestProviders.ts (the only non-test file in scope) got comment edits only"

patterns-established:
  - "Per-line substitution helper (temp/241-46/mk.py) that composes several substring replacements on one line and emits one apply-edits batch; each substitution asserts its old text is present, so a stale line number fails loudly instead of editing the wrong line"

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

duration: 35min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 46: Frontend Engine Tests Comment and Title Cleanup Summary

**Planning tags (phase/plan/decision/review ids, SEED pointers, quick-task ids, RESEARCH/SUMMARY references) are gone from the comments and describe/it/test titles of the 34 tagged engine test files; the token diff against the phase base is empty apart from normalized titles and the vitest count is unchanged.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2
- **Files modified:** 34 (33 `*.test.ts` plus `searchTestProviders.ts`); `workerErrorContext.test.ts` was already clean and stays untouched
- **Scan:** 556 matches before (192 test titles, 364 comments), 0 after

## Accomplishments

- Task 1 (search, bot-style and selection tests, 19 files): codemod rewrote 68 lines mechanically, then 278 hand edits through `apply-edits` batches (plus three direct edits for multi-line headers: `backup.test.ts`, `fallbackExpectimax.test.ts`, `rootSplit.test.ts`).
- Task 2 (worker, asset, Maia and platform tests, 16 files incl. the clean `workerErrorContext.test.ts`): codemod rewrote 33 lines, then 242 hand edits.
- A broader leftover grep (letter-number ids such as `D-`, `L-`, `T-`, `G-`, `WR-`, `CR-`, `IN-`, `SC`, `BOT-`, `INJECT-`, `LADDER-`, `JANK-`, `Phase N`, `Pitfall`, `RESEARCH`, `SUMMARY`, `Task N`, `Plan N`, `quick NNNNNN-xxx`, `Hotfix`, `8XN`, `G-213-19b`-style ids) found a further ~15 tag shapes the scan regex does not see (single-digit ids, `Task 1/2/3`, `Plan 03`, `quick 260905-rhc`, `G-213-19b`, `8XN-7`, `L-2`); all were fixed and the grep is now empty apart from code-string false positives (`...-v1` cache-name literals, `workbox-precache-v2-x`) and the word "wave" in a worker-pool comment.
- Comments that were history narration ("SC4 reversed", "the pre-Phase-225 formula") now say what the code does today ("pre-fallback formula").

## Task Commits

1. **Task 1: search, bot-style and selection tests** - `f67566c1b` (`chore(comments): frontend engine search tests`)
2. **Task 2: worker, asset, Maia and platform tests** - `86a75dc3d` (`chore(comments): frontend engine worker and asset tests`)

`commits: 2` is measured with `git rev-list --count 1cee4f3aa..HEAD` before this SUMMARY commit.

## Gates (final tree)

| Check | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-46.txt` | exit 0 (35 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-46.txt` | exit 0 (35 selected, 34 changed, no residue; no title collisions) |
| vitest Task 1 files (explicit 18-file list) | 346 tests before, 346 after |
| vitest `src/lib/engine` | 35 files, 790 tests before, 790 after, all pass |
| `npm --prefix frontend run lint` | clean before and after |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed (same as baseline) |
| source-scan Python half, run serially (no `-n 4`) | 95 passed + 5 passed |
| grep `^\s*(#\|//\|\*)\s*[:;,]\s` over the engine tests (codemod punctuation-start bug) | no matches |

Environmental note: sibling executors share the dev Postgres, so the Python half of `source_scan_tests.sh` was run serially with the same test files; this is not a plan failure. The Python half reads `app/` source only and `app/` was not touched.

## Rewritten test titles (D-14)

207 describe/it/test titles changed (more than the 192 the scan flagged: the extra ones carried tags in shapes the scan regex misses, such as `L-2`, `T-213-01`, `G-213-19b`, `quick 260731-s0z FIX-4`). No title collides with a sibling title (`cleanup.py diff` checks this). Titles that quote a renamed identifier keep the current name (`ENGINE_PATH`).

| File | Old | New |
|---|---|---|
| backup | `computes the Maia-prior-weighted expectation over a mixed expanded/unexpanded set (SC2 fixture)` | `computes the Maia-prior-weighted expectation over a mixed expanded/unexpanded set` |
| botSampling | `samples ~50/50 over 10000 draws from a two-move 50/50 policy (RESEARCH A1)` | `samples ~50/50 over 10000 draws from a two-move 50/50 policy` |
| botSampling | `returns null for an empty policy (degenerate, D-13) — never throws` | `returns null for an empty policy (degenerate) — never throws` |
| botSampling | `returns null for an all-zero-weight policy (degenerate, D-13) — never throws` | `returns null for an all-zero-weight policy (degenerate) — never throws` |
| botSampling | `returns null for an all-NaN policy (degenerate, D-13) — never silently picks a move` | `returns null for an all-NaN policy (degenerate) — never silently picks a move` |
| botSampling | `returns null for an Infinity-total policy (degenerate, D-13)` | `returns null for an Infinity-total policy (degenerate)` |
| botSampling | `converges to the highest-practicalScore move at very small tau even when array order disagrees (Pitfall 1)` | `converges to the highest-practicalScore move at very small tau even when array order disagrees` |
| botSampling | `returns the argmax at tau = 0 (the softmax limit), never the worst move (WR-03)` | `returns the argmax at tau = 0 (the softmax limit), never the worst move` |
| botSampling | `returns the argmax at negative tau instead of inverting the softmax (WR-03)` | `returns the argmax at negative tau instead of inverting the softmax` |
| botSampling | `scans for the true max practicalScore, ignoring array order (Pitfall 1/D-06)` | `scans for the true max practicalScore, ignoring array order` |
| botSampling | `never latches a NaN practicalScore as best (WR-02)` | `never latches a NaN practicalScore as best` |
| botSampling | `returns null when every practicalScore is non-finite (degenerate, D-13)` | `returns null when every practicalScore is non-finite (degenerate)` |
| botStyle | `is a plain data object with no function-typed field (BOT-03 Tampering guard)` | `is a plain data object with no function-typed field` |
| botStyle | `preserves modalPath/modalStats as accessor properties after shaping and never invokes the underlying builder (Phase 194 JANK-03 landmine fix)` | `preserves modalPath/modalStats as accessor properties after shaping and never invokes the underlying builder` |
| botStyle | `needs the JOINED prefix, not the bare SAN (Pitfall 2): the same san only boosts under the matching history` | `needs the JOINED prefix, not the bare SAN: the same san only boosts under the matching history` |
| botStyle | `behaves identically to maiaPolicyWeighting for an empty style-prefix set (STYLE-01 empty edge)` | `behaves identically to maiaPolicyWeighting for an empty style-prefix set` |
| botStyleBundles | `%s bundle carries a bookBoost in the D-06 ~20-50 range` | `%s bundle carries a bookBoost in the ~20-50 range` |
| botStyleBundles | `Grinder has positive contempt (avoids draws) and Wall has negative contempt (welcomes them slightly early) — D-09` | `Grinder has positive contempt (avoids draws) and Wall has negative contempt (welcomes them slightly early)` |
| botStyleBundles | `Attacker's check and capture multipliers are greater than 1 (D-06 identity)` | `Attacker's check and capture multipliers are greater than 1` |
| botStyleBundles | `Grinder's exchange multiplier is greater than 1 (D-06 identity: trade-happy)` | `Grinder's exchange multiplier is greater than 1 (trade-happy)` |
| botStyleBundles | `Wall's exchange multiplier is greater than 1 and pawn-storm multiplier is less than 1 (D-06 identity: simplifying, never storms)` | `Wall's exchange multiplier is greater than 1 and pawn-storm multiplier is less than 1 (simplifying, never storms)` |
| botStyleBundles | `Grinder never resigns early: threshold is far below the other 3 styles' resign floor (D-08)` | `Grinder never resigns early: threshold is far below the other 3 styles' resign floor` |
| deadlineSearch | `cuts the search at the deadline and resolves with the best-so-far snapshot, not a throw (D-16)` | `cuts the search at the deadline and resolves with the best-so-far snapshot, not a throw` |
| deadlineSearch | `Phase 194 ABORT-02: a deadline cut aborts only the INNER controller — the caller's OUTER signal stays unaborted (D-17)` | `a deadline cut aborts only the INNER controller — the caller's OUTER signal stays unaborted` |
| deadlineSearch | `does not cut below the D-18 node floor even though the deadline already elapsed` | `does not cut below the node floor even though the deadline already elapsed` |
| deadlineSearch | `propagates an outer cancel immediately, never delayed by the node floor (D-17)` | `propagates an outer cancel immediately, never delayed by the node floor` |
| deadlineSearch | `continuous mode (Phase 227 D-09/D-13): a deadline that cuts mid-search returns the last snapshot before the cut and applies nothing after it` | `continuous mode: a deadline that cuts mid-search returns the last snapshot before the cut and applies nothing after it` |
| engineAssetCache | `getEngineAsset — truncation guard (CR-01)` | `getEngineAsset — truncation guard` |
| engineAssetProgress | `markEngineAssetsUnsupported — Sentry capture at the store choke point (SEED-158, 2026-09-07)` | `markEngineAssetsUnsupported — Sentry capture at the store choke point` |
| engineAssetProgress | `requiredEngineAssets — G-213-19b referential stability` | `requiredEngineAssets — referential stability` |
| engineAssetProgress | `returns all three assets, unconditionally (Phase 213-09 adds ort-runtime — G-213-35)` | `returns all three assets, unconditionally (including ort-runtime)` |
| engineAssetProgress | `reportEngineAssetProgress — coercion (T-213-01)` | `reportEngineAssetProgress — coercion` |
| engineAssetProgress | `useEngineAssets — byte-weighted aggregate (D-11)` | `useEngineAssets — byte-weighted aggregate` |
| engineAssetProgress | `useEngineAssets — three-asset denominator (Phase 213-09 adds ort-runtime)` | `useEngineAssets — three-asset denominator (includes ort-runtime)` |
| engineAssetProgress | `markEngineAssetPending / markEngineAssetReady — CR-02: allDone must not fire on a still-downloading concurrently-spawned asset` | `markEngineAssetPending / markEngineAssetReady: allDone must not fire on a still-downloading concurrently-spawned asset` |
| engineAssetProgress | `store-level property only, not reachable under G-213-19b: an asset that was never registered does not hold allDone back` | `store-level property only, not reachable through the unconditional engine gate: an asset that was never registered does not hold allDone back` |
| engineAssetProgress | `engineGateRequired — G-213-19b unconditional bundle (no per-persona subset)` | `engineGateRequired: unconditional bundle (no per-persona subset)` |
| engineAssetProgress | `stays true when only TWO of the three assets have been seen — a partially-cached device is still gated (Phase 213-09)` | `stays true when only TWO of the three assets have been seen — a partially-cached device is still gated` |
| engineAssetProgress | `markEngineAssetFailed — Plan 04 owns this UI; Task 1 owns the transport` | `markEngineAssetFailed — failure transport` |
| engineAssetProgress | `markEngineAssetsRetrying — D-15 manual retry seam` | `markEngineAssetsRetrying — manual retry seam` |
| engineAssetProgress | `WR-01: resets the failed (not-done) asset's loaded byte count to 0, so a fresh worker is not clamped up to the old high-water mark` | `resets the failed (not-done) asset's loaded byte count to 0, so a fresh worker is not clamped up to the old high-water mark` |
| engineAssetProgress | `WR-01: a fresh worker's first near-zero progress report is not clamped up to the failed attempt's old high-water mark` | `a fresh worker's first near-zero progress report is not clamped up to the failed attempt's old high-water mark` |
| engineAssetProgress | `resetEngineAssetForRefetch — WR-02: mid-session self-heal must not report a stale ready signal` | `resetEngineAssetForRefetch: mid-session self-heal must not report a stale ready signal` |
| engineAssetProgress | `reportEngineAssetProgress — coalesced notifications (G-213-35)` | `reportEngineAssetProgress — coalesced notifications` |
| engineAssetProgress | `markEngineAssetPending notifies even when nothing else has changed (CR-02)` | `markEngineAssetPending notifies even when nothing else has changed` |
| fallbackExpectimax | `fallbackExpectimax — SC5 guardrail swap-in` | `fallbackExpectimax — guardrail swap-in` |
| fallbackExpectimax | `fallbackExpectimax — D-04 extraRootMoves` | `fallbackExpectimax — extraRootMoves` |
| fallbackExpectimax | `INJECT-02 observable-ranking proof: a post-fix injected move with a real prior ranks ABOVE a known weaker organic candidate whose rankScore it beats` | `observable-ranking proof: a post-fix injected move with a real prior ranks ABOVE a known weaker organic candidate whose rankScore it beats` |
| fallbackExpectimax | `fallbackExpectimax — Phase 159 D-01 findability ranking (Phase 225 D-10a/D-10e: blend toward V_fallback)` | `fallbackExpectimax — findability ranking (blend toward V_fallback)` |
| fallbackExpectimax | `fallbackExpectimax — Phase 159 policy temperature` | `fallbackExpectimax — policy temperature` |
| fallbackExpectimax | `omitting policyTemperature behaves identically to the default (no-op short-circuit, Pitfall 1)` | `omitting policyTemperature behaves identically to the default (no-op short-circuit)` |
| fallbackExpectimax | `reshapes ONLY the root-mover's own side — the opponent's candidateUcis passed to grade() are the untouched raw truncation (D-05)` | `reshapes ONLY the root-mover's own side — the opponent's candidateUcis passed to grade() are the untouched raw truncation` |
| fallbackExpectimax | `composes with D-01 findability: reverses the T=1 winner at T=2 via a three-candidate fixture (Phase 225 D-10a/D-10e)` | `composes with findability: reverses the T=1 winner at T=2 via a three-candidate fixture` |
| fallbackExpectimax | `an extreme-flatness fixture never produces more than ROOT_CANDIDATE_HARD_CAP root children (D-07/Pitfall 6)` | `an extreme-flatness fixture never produces more than ROOT_CANDIDATE_HARD_CAP root children` |
| fallbackExpectimax | `extreme-flatness INJECT-01 regression: an out-of-mass-cut injected UCI survives BOTH the mass cut and the hard cap` | `extreme-flatness regression: an out-of-mass-cut injected UCI survives BOTH the mass cut and the hard cap` |
| fallbackExpectimax | `Phase 194 ABORT-01: every providers.grade() call receives the search's own AbortSignal, by reference, on every expansion` | `every providers.grade() call receives the search's own AbortSignal, by reference, on every expansion` |
| findability | `stays within [min(value, fallback), value] for every combination in the grid (D-10a invariant)` | `stays within [min(value, fallback), value] for every combination in the grid (invariant)` |
| findability | `reduces to (pYou/pRef) * value when fallback is 0 — the pre-Phase-225 formula (D-10b)` | `reduces to (pYou/pRef) * value when fallback is 0 — the pre-fallback formula` |
| findability | `D-10c: clamps a low-prior move already below V_fallback to its own value — never promoted` | `clamps a low-prior move already below V_fallback to its own value — never promoted` |
| findability | `returns 0 (not backupExpectation's own 0.5 default) when every prior is 0 — D-10b amended` | `returns 0 (not backupExpectation's own 0.5 default) when every prior is 0` |
| findability | `D-03 regression cases (restated for D-10a — V_fallback pinned by the stated rule BEFORE running)` | `regression cases (V_fallback pinned by the stated rule BEFORE running)` |
| findability | `@1000 restated (D-10e): the in-chart candidate (30% prior, V 0.58, saturated) still beats Qb8 (5% prior, V 0.60)` | `@1000 restated: the in-chart candidate (30% prior, V 0.58, saturated) still beats Qb8 (5% prior, V 0.60)` |
| gradingLadder | `index 0 returns GRADING_ROOT_DEPTH (D-02 pinned root rung)` | `index 0 returns GRADING_ROOT_DEPTH (pinned root rung)` |
| gradingLadder | `the shipped ladder table (LADDER-02)` | `the shipped ladder table` |
| gradingLadder | `pins the root rung at 14 (D-02 — root was never a variable in the A/B)` | `pins the root rung at 14 (the root was never a variable in the A/B)` |
| maiaPolicyCache | `LRU (CACHE-01/02): filling to exactly MAIA_POLICY_CACHE_MAX evicts nothing; reading an entry then forcing one eviction spares it and evicts a never-read entry — fails under FIFO` | `LRU: filling to exactly MAIA_POLICY_CACHE_MAX evicts nothing; reading an entry then forcing one eviction spares it and evicts a never-read entry — fails under FIFO` |
| maiaPolicyCache | `LRU (CACHE-02): a WRITE to an already-present key counts as a use — re-setting an entry spares it from the next eviction (fails when setCachedPolicy omits the delete-then-reinsert touch)` | `LRU: a WRITE to an already-present key counts as a use — re-setting an entry spares it from the next eviction (fails when setCachedPolicy omits the delete-then-reinsert touch)` |
| maiaQueue | `ENGINE_PATH now lives on maiaWorkerHost (D-04 reversal) and carries a ?v=<digits> version suffix` | `ENGINE_PATH now lives on maiaWorkerHost and carries a ?v=<digits> version suffix` |
| maiaQueue | `caps the shared policy cache at MAIA_POLICY_CACHE_MAX entries (LRU eviction, Phase 194 CACHE-01/02)` | `caps the shared policy cache at MAIA_POLICY_CACHE_MAX entries (LRU eviction)` |
| maiaQueue | `createMaiaQueue: handleResult throw containment (code-review WR-03)` | `createMaiaQueue: handleResult throw containment` |
| maiaWorkerHost | `SEED-195: a pre-ready OOM capture tags the spawn path (auto-wasm vs webgpu-failed-wasm)` | `a pre-ready OOM capture tags the spawn path (auto-wasm vs webgpu-failed-wasm)` |
| maiaWorkerHost | `WR-01 (Phase 219 review): a threaded-init timeout retries ONCE pinned to single-thread, preserving the queue` | `a threaded-init timeout retries ONCE pinned to single-thread, preserving the queue` |
| maiaWorkerHost | `WR-01 (Phase 219 review): a SECOND threaded-init timeout (already single-threaded) is terminal — no infinite retry loop` | `a SECOND threaded-init timeout (already single-threaded) is terminal — no infinite retry loop` |
| maiaWorkerHost | `WR-03 (Phase 219 review): lastReportedNumThreads resets on respawn — a pre-ready failure of the REPLACEMENT worker never reports the dead worker's thread count` | `lastReportedNumThreads resets on respawn — a pre-ready failure of the REPLACEMENT worker never reports the dead worker's thread count` |
| maiaWorkerHost | `WR-02: a mid-inference webgpu respawn resets maia-model to not-done in the store, even though it was already marked ready` | `a mid-inference webgpu respawn resets maia-model to not-done in the store, even though it was already marked ready` |
| maiaWorkerHost | `WR-01 still applies on iOS: a threaded wasm init timeout retries ONCE pinned to single-thread, on the wasm-only runtime` | `the threaded-init retry still applies on iOS: a threaded wasm init timeout retries ONCE pinned to single-thread, on the wasm-only runtime` |
| maiaWorkerHost | `T-213-09-03: concurrent ensureSpawned() calls during the in-flight runtime fetch issue exactly ONE fetch and construct exactly ONE Worker` | `concurrent ensureSpawned() calls during the in-flight runtime fetch issue exactly ONE fetch and construct exactly ONE Worker` |
| maiaWorkerHost | `T-213-09-03: an analyze() issued while the runtime fetch is still in flight is QUEUED and resolves once the worker becomes ready — never dropped` | `an analyze() issued while the runtime fetch is still in flight is QUEUED and resolves once the worker becomes ready — never dropped` |
| maiaWorkerHost | `T-213-09-02: a null runtime buffer (degraded fetch) still spawns the worker — init carries no runtimeBuffer field` | `a null runtime buffer (degraded fetch) still spawns the worker — init carries no runtimeBuffer field` |
| maiaWorkerHost | `D-13: a device without WASM SIMD issues ZERO runtime-fetch calls — the SIMD gate precedes the fetch, not the other way around` | `a device without WASM SIMD issues ZERO runtime-fetch calls — the SIMD gate precedes the fetch, not the other way around` |
| maiaWorkerHost | `CR-02: registers 'ort-runtime' pending in the SAME synchronous call as 'maia-model' — neither is reachable without the other` | `registers 'ort-runtime' pending in the SAME synchronous call as 'maia-model' — neither is reachable without the other` |
| maiaWorkerHost | `G-213-36 THE ACTUAL REGRESSION: teardown + respawn (the /analysis -> /bots navigation) delivers a valid, non-detached init message to the SECOND worker` | `THE ACTUAL REGRESSION: teardown + respawn (the /analysis -> /bots navigation) delivers a valid, non-detached init message to the SECOND worker` |
| maiaWorkerHost | `G-213-37: the init message carries assetCacheName on the normal ('auto') spawn branch` | `the init message carries assetCacheName on the normal ('auto') spawn branch` |
| maiaWorkerHost | `G-213-37: the init message carries assetCacheName on the wasm-pinned respawn branch too` | `the init message carries assetCacheName on the wasm-pinned respawn branch too` |
| maiaWorkerHost | `G-213-37: a second spawn after resetModuleState() teardown still delivers an init message the worker RECEIVES — asserted on the received message, not the absence of a throw` | `a second spawn after resetModuleState() teardown still delivers an init message the worker RECEIVES — asserted on the received message, not the absence of a throw` |
| maiaWorkerScript | `maiaWorkerScript — chooseWasmThreadCount() (Phase 219, D-08)` | `maiaWorkerScript — chooseWasmThreadCount()` |
| maiaWorkerScript | `maiaWorkerScript — WR-01 (Phase 219 review): bounded threaded init + forceSingleThread` | `maiaWorkerScript — bounded threaded init + forceSingleThread` |
| maiaWorkerScript | `an unrecognised backend value falls safe to wasm (D-13 fail-safe-toward-wasm philosophy)` | `an unrecognised backend value falls safe to wasm (fail-safe-toward-wasm philosophy)` |
| maiaWorkerScript | `maiaWorkerScript — asset cache (Phase 213-12, D-20, closing G-213-37)` | `maiaWorkerScript — asset cache` |
| maiaWorkerScript | `a model stream ending short of its declared content-length is retried and NEVER written to the cache (CR-01)` | `a model stream ending short of its declared content-length is retried and NEVER written to the cache` |
| maiaWorkerScript | `a model response with no usable content-length resolves but is NOT cached — the next spawn fetches again (CR-01)` | `a model response with no usable content-length resolves but is NOT cached — the next spawn fetches again` |
| maiaWorkerScript | `maiaWorkerScript — asset versioning (quick 260905-rhc)` | `maiaWorkerScript — asset versioning` |
| mctsSearch.continuous | `mctsSearch continuous — c=1 identity with round mode (D-11, design 2.4)` | `mctsSearch continuous — c=1 identity with round mode` |
| mctsSearch.continuous | `mctsSearch — dispatchMode omitted is round mode (D-11)` | `mctsSearch — dispatchMode omitted is round mode` |
| mctsSearch.continuous | `mctsSearch continuous — arrival order (D-08, SEED-171 item 5)` | `mctsSearch continuous — arrival order` |
| mctsSearch.continuous | `mctsSearch continuous — no result is applied after abort or early stop (D-09, L-2)` | `mctsSearch continuous — no result is applied after abort or early stop` |
| mctsSearch.continuous | `mctsSearch continuous — node budget (D-10, claim (b))` | `mctsSearch continuous — node budget` |
| mctsSearch.continuous | `mctsSearch continuous — pending exclusion (D-08)` | `mctsSearch continuous — pending exclusion` |
| mctsSearch.continuous | `mctsSearch continuous — fill (D-08, SEED-170 item 2)` | `mctsSearch continuous — fill` |
| mctsSearch.continuous | `mctsSearch continuous — listener hygiene (Pitfall 7)` | `mctsSearch continuous — listener hygiene` |
| mctsSearch.roundFill | `mctsSearch — D-08 round fill` | `mctsSearch — round fill` |
| mctsSearch.roundFill | `produces toEqual final snapshots and toEqual onSnapshot sequences at concurrency 2 under two different resolution jitters (D-06 determinism scope)` | `produces toEqual final snapshots and toEqual onSnapshot sequences at concurrency 2 under two different resolution jitters (determinism scope)` |
| mctsSearch.roundFill | `resolves with round size 1 every round on a fully single-chain tree (T-225-07 fully-blocked-round termination)` | `resolves with round size 1 every round on a fully single-chain tree (fully-blocked-round termination)` |
| mctsSearch | `mctsSearch — ENGINE-01 ranked output` | `mctsSearch — ranked output` |
| mctsSearch | `mctsSearch — ENGINE-04 ELO oracle` | `mctsSearch — ELO oracle` |
| mctsSearch | `mctsSearch — ENGINE-02 truncation` | `mctsSearch — truncation` |
| mctsSearch | `mctsSearch — ENGINE-05 leaf conversion + depth cutoff` | `mctsSearch — leaf conversion + depth cutoff` |
| mctsSearch | `modalStats carries each ply's RAW Maia prob (not the renormalized prior) + white-POV eval (Phase 160)` | `modalStats carries each ply's RAW Maia prob (not the renormalized prior) + white-POV eval` |
| mctsSearch | `mctsSearch — D-04 extraRootMoves` | `mctsSearch — extraRootMoves` |
| mctsSearch | `INJECT-02 observable-ranking proof: a post-fix injected move with a real prior ranks ABOVE a known weaker organic candidate whose rankScore it beats` | `observable-ranking proof: a post-fix injected move with a real prior ranks ABOVE a known weaker organic candidate whose rankScore it beats` |
| mctsSearch | `mctsSearch — Phase 159 D-01 findability ranking (Phase 225 D-10a/D-10e: blend toward V_fallback)` | `mctsSearch — findability ranking (blend toward V_fallback)` |
| mctsSearch | `mctsSearch — Phase 159 policy temperature` | `mctsSearch — policy temperature` |
| mctsSearch | `omitting policyTemperature behaves identically to the default (no-op short-circuit, Pitfall 1)` | `omitting policyTemperature behaves identically to the default (no-op short-circuit)` |
| mctsSearch | `reshapes ONLY the root-mover's own side — the opponent's candidateUcis passed to grade() are the untouched raw truncation (D-05)` | `reshapes ONLY the root-mover's own side — the opponent's candidateUcis passed to grade() are the untouched raw truncation` |
| mctsSearch | `composes with D-01 findability: reverses the T=1 winner at T=2 via a three-candidate fixture (Phase 225 D-10a/D-10e)` | `composes with findability: reverses the T=1 winner at T=2 via a three-candidate fixture` |
| mctsSearch | `an extreme-flatness fixture never produces more than ROOT_CANDIDATE_HARD_CAP root children (D-07/Pitfall 6)` | `an extreme-flatness fixture never produces more than ROOT_CANDIDATE_HARD_CAP root children` |
| mctsSearch | `extreme-flatness INJECT-01 regression: an out-of-mass-cut injected UCI survives BOTH the mass cut and the hard cap` | `extreme-flatness regression: an out-of-mass-cut injected UCI survives BOTH the mass cut and the hard cap` |
| mctsSearch | `Phase 194 ABORT-01: every providers.grade() call receives the search's own AbortSignal, by reference, on every expansion` | `every providers.grade() call receives the search's own AbortSignal, by reference, on every expansion` |
| mctsSearch | `LADDER-02: every providers.grade() call receives a resolved grading-depth 4th argument, never undefined` | `every providers.grade() call receives a resolved grading-depth 4th argument, never undefined` |
| mctsSearch | `mctsSearch — Phase 168.5 D-05/D-06 (guarded Phase 225 D-01/D-02) bot-play stop rule` | `mctsSearch — bot-play stop rule (guarded)` |
| mctsSearch | `mctsSearch — ENGINE-07 determinism` | `mctsSearch — determinism` |
| mctsSearch | `mctsSearch — gradeRoot routing (Phase 226 D-18)` | `mctsSearch — gradeRoot routing` |
| openingBook | `returns null when the single book candidate is below BOOK_POLICY_FLOOR on the RAW policy (Pitfall 3 guard)` | `returns null when the single book candidate is below BOOK_POLICY_FLOOR on the RAW policy` |
| openingBook | `styled weighting (Phase 182, STYLE-01) — floor check still runs before weighting` | `styled weighting — floor check still runs before weighting` |
| ortRuntimeSource | `probes the adapter ORT itself will use — requestAdapter({ powerPreference: "high-performance" }) (SEED-158)` | `probes the adapter ORT itself will use — requestAdapter({ powerPreference: "high-performance" })` |
| ortRuntimeSource | `ensureOrtRuntime — CR-02 synchronous pending registration` | `ensureOrtRuntime — synchronous pending registration` |
| ortRuntimeSource | `ensureOrtRuntime — failure degradation (T-213-09-02)` | `ensureOrtRuntime — failure degradation` |
| ortRuntimeSource | `ensureOrtRuntime — G-213-36 retain-and-copy (second call after the first buffer is detached)` | `ensureOrtRuntime — retain-and-copy (second call after the first buffer is detached)` |
| ortRuntimeSource | `ensureOrtRuntime — cache provenance (Phase 213-12, D-20)` | `ensureOrtRuntime — cache provenance` |
| policyTemperature | `is exactly 1 (strict equality — Pitfall 7)` | `is exactly 1 (strict equality)` |
| rootSplit | `a candidate missing from every shard is absent from the result — never fabricated (L-2)` | `a candidate missing from every shard is absent from the result — never fabricated` |
| select | `breaks equal-probability ties by ascending UCI order, not Record insertion order (WR-03)` | `breaks equal-probability ties by ascending UCI order, not Record insertion order` |
| select | `does NOT floor-boost when truncateAndRenormalize runs on the same input (D-05 floor scope isolated)` | `does NOT floor-boost when truncateAndRenormalize runs on the same input (floor scope isolated)` |
| selectBotMove | `falls back to a legal move when the policy is empty/degenerate (BOT-04)` | `falls back to a legal move when the policy is empty/degenerate` |
| selectBotMove | `falls back to a legal move when rankedLines is empty (BOT-04)` | `falls back to a legal move when rankedLines is empty` |
| selectBotMove | `selectBotMove — symmetric ELO (BOT-03)` | `selectBotMove — symmetric ELO` |
| selectBotMove | `rejects policyTemperature on BotSettings.budget at the type level (D-02/WR-04)` | `rejects policyTemperature on BotSettings.budget at the type level` |
| selectBotMove | `selectBotMove — style undefined regression (D-03 baseline invariant)` | `selectBotMove — style undefined regression (baseline invariant)` |
| selectBotMove | `selectBotMove — styled blend<=0 (STYLE-03 prior reweighting)` | `selectBotMove — styled blend<=0 (prior reweighting)` |
| selectBotMove | `selectBotMove — styled search branch (STYLE-04 score shaping)` | `selectBotMove — styled search branch (score shaping)` |
| selectBotMove | `selectBotMove — D-10d: order-invariant under any rankedLines permutation (item 3 proof)` | `selectBotMove — order-invariant under any rankedLines permutation` |
| stockfishWorkerSource | `ensureStockfishWorkerUrl — CR-02 synchronous pending registration` | `ensureStockfishWorkerUrl — synchronous pending registration` |
| stockfishWorkerSource | `ensureStockfishWorkerUrl — failure degradation (T-213-07)` | `ensureStockfishWorkerUrl — failure degradation` |
| stockfishWorkerSource | `a null shared URL appends STOCKFISH_ENGINE_WASM_PATH as an encoded location hash (D-05)` | `a null shared URL appends STOCKFISH_ENGINE_WASM_PATH as an encoded location hash` |
| styleOpeningLines | `curated prefixes are genuine ECO-corpus members (D-05)` | `curated prefixes are genuine ECO-corpus members` |
| treeCommon | `applyRootCandidateHardCap — INJECT-01 exemption` | `applyRootCandidateHardCap — injected-move exemption` |
| treeCommon | `two calls with the same inputs produce the same key order (deterministic tie-break, ENGINE-07)` | `two calls with the same inputs produce the same key order (deterministic tie-break)` |
| treeCommon | `buildRankedLines childScoreSpread (Phase 182 D-10)` | `buildRankedLines childScoreSpread` |
| treeCommon | `buildRankedLines lazy modalPath/modalStats (Phase 194 JANK-03)` | `buildRankedLines lazy modalPath/modalStats` |
| treeCommon | `onSnapshot fire count is unaffected by lazy modalPath/modalStats (Phase 194 D-10)` | `onSnapshot fire count is unaffected by lazy modalPath/modalStats` |
| treeCommon | `cloneRankedLineWith (Phase 194 JANK-03 / code-review WR-04)` | `cloneRankedLineWith` |
| workerPool | `createWorkerPool + mctsSearch: a tree node is graded at its ladder rung (LADDER-02 end-to-end)` | `createWorkerPool + mctsSearch: a tree node is graded at its ladder rung (end-to-end)` |
| workerPool | `createWorkerPool: gradeRoot() root split (Phase 226 L-2/L-3/L-4)` | `createWorkerPool: gradeRoot() root split` |
| workerPool | `createWorkerPool: gradeRoot() root split — failure paths and edge cases (Phase 226 L-2/L-3/L-4)` | `createWorkerPool: gradeRoot() root split — failure paths and edge cases` |
| workerPool | `L-2: 3 shards completing with real grades before a 4th is aborted still resolves the WHOLE group empty — never a partial merge` | `3 shards completing with real grades before a 4th is aborted still resolves the WHOLE group empty — never a partial merge` |
| workerPool | `L-2: 3 shards completing before the 4th watchdog-fires (no outer abort) still resolves the whole group empty` | `3 shards completing before the 4th watchdog-fires (no outer abort) still resolves the whole group empty` |
| workerPool | `createWorkerPool: gradingDepth parameter plumbing (LADDER-02/04)` | `createWorkerPool: gradingDepth parameter plumbing` |
| workerPool | `an omitted gradingDepth (3-arg call, no signal) defaults to GRADING_ROOT_DEPTH (D-02)` | `an omitted gradingDepth (3-arg call, no signal) defaults to GRADING_ROOT_DEPTH` |
| workerPool | `no emitted go line ever carries a wall-clock (movetime) token, across multiple grading depths (LADDER-04)` | `no emitted go line ever carries a wall-clock (movetime) token, across multiple grading depths` |
| workerPool | `createWorkerPool: watchdog (D-06)` | `createWorkerPool: watchdog` |
| workerPool | `quick 260731-s0z FIX-4: an abort of an in-flight request re-arms a stop-bestmove watchdog — one static Sentry capture after STOP_BESTMOVE_WATCHDOG_TIMEOUT_MS if the worker never answers `stop`, and the dead slot is never re-dispatched to` | `an abort of an in-flight request re-arms a stop-bestmove watchdog — one static Sentry capture after STOP_BESTMOVE_WATCHDOG_TIMEOUT_MS if the worker never answers `stop`, and the dead slot is never re-dispatched to` |
| workerPool | `quick 260731-s0z FIX-4: a healthy stop answered by a bestmove before STOP_BESTMOVE_WATCHDOG_TIMEOUT_MS disarms the re-armed watchdog — no Sentry capture` | `a healthy stop answered by a bestmove before STOP_BESTMOVE_WATCHDOG_TIMEOUT_MS disarms the re-armed watchdog — no Sentry capture` |
| workerPool | `quick 260731-s0z FIX-4: stopAll() re-arms a stop-bestmove watchdog per thinking slot — one static Sentry capture per never-answering slot after STOP_BESTMOVE_WATCHDOG_TIMEOUT_MS` | `stopAll() re-arms a stop-bestmove watchdog per thinking slot — one static Sentry capture per never-answering slot after STOP_BESTMOVE_WATCHDOG_TIMEOUT_MS` |
| workerPool | `195-06 WR-01: worker.onerror clears the in-flight watchdog — no second, misleading Sentry capture after the deadline` | `worker.onerror clears the in-flight watchdog — no second, misleading Sentry capture after the deadline` |
| workerPool | `createWorkerPool: grade() on a fully dead pool (quick 260731-s0z FIX-3)` | `createWorkerPool: grade() on a fully dead pool` |
| workerPool | `FIX-3 + FIX-4 composed: aborting one shared signal across every slot kills the whole pool via the stop-bestmove watchdog, and a subsequent signal-less grade() still resolves empty` | `composed: aborting one shared signal across every slot kills the whole pool via the stop-bestmove watchdog, and a subsequent signal-less grade() still resolves empty` |
| workerPool | `createWorkerPool: grade cache (Phase 194 CACHE-01..04, INJECT-05)` | `createWorkerPool: grade cache` |
| workerPool | `a fresh cache reports { hits: 0, misses: 0 } (INJECT-05)` | `a fresh cache reports { hits: 0, misses: 0 }` |
| workerPool | `a grade() for a novel (fen, depth) increments misses by 1 and leaves hits at 0 (INJECT-05)` | `a grade() for a novel (fen, depth) increments misses by 1 and leaves hits at 0` |
| workerPool | `a repeat grade() for the same (fen, depth) with an already-cached candidate subset increments hits by 1 and leaves misses unchanged (INJECT-05)` | `a repeat grade() for the same (fen, depth) with an already-cached candidate subset increments hits by 1 and leaves misses unchanged` |
| workerPool | `a repeat grade() for the same fen at a DIFFERENT depth increments misses (LADDER-03, INJECT-05)` | `a repeat grade() for the same fen at a DIFFERENT depth increments misses` |
| workerPool | `a repeat grade() for the same (fen, depth) requesting a UCI the cached entry lacks increments misses (CACHE-04, INJECT-05)` | `a repeat grade() for the same (fen, depth) requesting a UCI the cached entry lacks increments misses` |
| workerPool | `resetCacheStats() returns both counters to 0 without evicting any cached entry — a subsequent repeat request still reports a hit (INJECT-05)` | `resetCacheStats() returns both counters to 0 without evicting any cached entry — a subsequent repeat request still reports a hit` |
| workerPool | `the empty-candidateUcis and already-aborted early returns happen before the cache is consulted and increment neither counter (INJECT-05)` | `the empty-candidateUcis and already-aborted early returns happen before the cache is consulted and increment neither counter` |
| workerPool | `LRU (CACHE-01/02): filling to exactly GRADE_CACHE_MAX evicts nothing; touching an entry then forcing one eviction spares it and evicts a never-read entry — fails under FIFO` | `LRU: filling to exactly GRADE_CACHE_MAX evicts nothing; touching an entry then forcing one eviction spares it and evicts a never-read entry — fails under FIFO` |
| workerPool | `LRU (CACHE-02): a re-grade WRITE to an already-cached FEN counts as a use — it spares that FEN from the next eviction (fails when cacheGrades omits the delete-then-reinsert touch)` | `LRU: a re-grade WRITE to an already-cached FEN counts as a use — it spares that FEN from the next eviction (fails when cacheGrades omits the delete-then-reinsert touch)` |
| workerPool | `merges a new candidate set into the existing per-FEN entry rather than replacing it (CACHE-03)` | `merges a new candidate set into the existing per-FEN entry rather than replacing it` |
| workerPool | `re-grading a UCI already in the cache overwrites its value — the newly-graded value wins on key collision (CACHE-03 ordering)` | `re-grading a UCI already in the cache overwrites its value — the newly-graded value wins on key collision` |
| workerPool | `merging an empty incoming grades map (a search yielding no info lines) leaves the existing entry unchanged (CACHE-03 empty)` | `merging an empty incoming grades map (a search yielding no info lines) leaves the existing entry unchanged` |
| workerPool | `two concurrent grade() calls for the same FEN resolving in either order leave the union of both candidate sets cached (CACHE-03 concurrency)` | `two concurrent grade() calls for the same FEN resolving in either order leave the union of both candidate sets cached` |
| workerPool | `a superset cache entry serves any subset request as a hit, returning only the requested keys (CACHE-04 adjacency)` | `a superset cache entry serves any subset request as a hit, returning only the requested keys` |
| workerPool | `a request with one un-cached UCI is a miss that re-grades the FULL requested set, not only the missing UCI (CACHE-04 ordering)` | `a request with one un-cached UCI is a miss that re-grades the FULL requested set, not only the missing UCI` |
| workerPool | `a depth-14 cached grade never satisfies a depth-10 request for the same FEN, regardless of visit order — depth-14-first (LADDER-03)` | `a depth-14 cached grade never satisfies a depth-10 request for the same FEN, regardless of visit order — depth-14-first` |
| workerPool | `a depth-10 cached grade never satisfies a depth-14 request for the same FEN, regardless of visit order — depth-10-first (LADDER-03)` | `a depth-10 cached grade never satisfies a depth-14 request for the same FEN, regardless of visit order — depth-10-first` |
| workerPool | `two different FENs at the same grading depth remain independent cache entries (unchanged by the rekey, LADDER-03)` | `two different FENs at the same grading depth remain independent cache entries (unchanged by the rekey)` |
| workerPool | `the all-or-nothing gate still applies inside one (fen, depth) entry — a UCI absent from that entry is a miss even though other UCIs of the same entry are present (CACHE-04, composite key)` | `the all-or-nothing gate still applies inside one (fen, depth) entry — a UCI absent from that entry is a miss even though other UCIs of the same entry are present (composite key)` |
| workerPool | `a grade aborted before bestmove writes nothing to the cache — a subsequent identical (fen, depth) request issues a fresh go (LADDER-03)` | `a grade aborted before bestmove writes nothing to the cache — a subsequent identical (fen, depth) request issues a fresh go` |
| workerPool | `LRU regression (Task 2, read-side): the read-hit cache.delete(key)/cache.set(key, cached) touch in grade() survives the composite-key rekey — deleting it makes this test fail` | `LRU regression (read-side): the read-hit cache.delete(key)/cache.set(key, cached) touch in grade() survives the composite-key rekey — deleting it makes this test fail` |
| workerPool | `LRU regression (Task 2, write-side): cacheGrades' cache.delete(key) touch survives the composite-key rekey — deleting it makes this test fail` | `LRU regression (write-side): cacheGrades' cache.delete(key) touch survives the composite-key rekey — deleting it makes this test fail` |
| workerPool | `D-02: no Worker is constructed until the first grade() call (lazy spawn)` | `no Worker is constructed until the first grade() call (lazy spawn)` |
| workerPool | `grade(fen, []) spawns nothing — WR-05 no-op (this is why warm() exists)` | `grade(fen, []) spawns nothing — no-op (this is why warm() exists)` |
| workerPool | `CR-02: terminate() resolves an in-flight (dispatched) grade() promise instead of hanging it` | `terminate() resolves an in-flight (dispatched) grade() promise instead of hanging it` |
| workerPool | `Phase 194 ABORT-02: an AbortSignal aborting an IN-FLIGHT (dispatched) request posts stop to its owning slot and resolves it empty` | `an AbortSignal aborting an IN-FLIGHT (dispatched) request posts stop to its owning slot and resolves it empty` |
| workerPool | `Phase 194 ABORT-02: aborting a signal after its own request already settled is a no-op — no throw, no dangling entry` | `aborting a signal after its own request already settled is a no-op — no throw, no dangling entry` |
| workerPool | `code-review WR-02: a request that settles NORMALLY detaches its abort listener, so one signal reused across many grades does not accumulate listeners` | `a request that settles NORMALLY detaches its abort listener, so one signal reused across many grades does not accumulate listeners` |
| workerPool | `Phase 194 ABORT-02: a single abort settles every one of several concurrently-issued grade() promises sharing one signal` | `a single abort settles every one of several concurrently-issued grade() promises sharing one signal` |
| workerPool | `WR-01: a pre-aborted signal resolves grade() empty immediately with zero Worker constructions` | `a pre-aborted signal resolves grade() empty immediately with zero Worker constructions` |
| workerPool | `WR-05: an empty candidateUcis array resolves grade() empty without dispatching a go message` | `an empty candidateUcis array resolves grade() empty without dispatching a go message` |
| workerPool | `grade is structurally assignable to EngineProviders.grade (D-08 two-arg call form)` | `grade is structurally assignable to EngineProviders.grade (two-arg call form)` |
| workerPool | `WR-04: worker.onerror settles the in-flight request and is Sentry-captured with the stockfish-worker-pool tag` | `worker.onerror settles the in-flight request and is Sentry-captured with the stockfish-worker-pool tag` |
| workerPool | `WR-04: once every slot has failed via onerror, a still-pending (never-dispatched) request drains instead of hanging` | `once every slot has failed via onerror, a still-pending (never-dispatched) request drains instead of hanging` |
| workerPool | `createWorkerPool: whenReady() (Phase 213 D-01)` | `createWorkerPool: whenReady()` |
| workerPool | `createWorkerPool: markPoolFailed (CR-01, 213-REVIEW.md)` | `createWorkerPool: markPoolFailed` |
| workerPool | `createWorkerPool: progressPort wiring (Phase 213 D-01, T-213-01/T-213-07)` | `createWorkerPool: progressPort wiring` |
| workerPool | `a progressPort message with a missing/zero total still produces a finite percent via the store fallback (T-213-01)` | `a progressPort message with a missing/zero total still produces a finite percent via the store fallback` |
| workerPool | `a MessageChannel-less environment skips the wiring without breaking engine spawn (T-213-07)` | `a MessageChannel-less environment skips the wiring without breaking engine spawn` |
| workerPool | `createWorkerPool: shared Stockfish wasm source (Phase 213-08, G-213-35)` | `createWorkerPool: shared Stockfish wasm source` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- **Issue:** `.venv` and `frontend/node_modules` were missing in the new worktree.
- **Fix:** `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only, no new packages). Baseline lint, vitest and `scan` ran on the untouched tree first.
- **Files modified:** none tracked

### Plan-text adaptations

**2. Task 2 owns 16 scope files, Task 1 owns 19.** The plan's two file lists name 19 and 15 files; the 16th scope file (`workerErrorContext.test.ts`) was listed only in `files_modified`. It had no matches and was not modified.

**3. Codemod "unrecognized shape" lines were all hand edited.** Roughly 70 percent of tagged lines in these files were keyword-led headings, multi-line comments with ids split across a wrap, or test titles (the codemod skips titles by design).

**4. [Rule 2 - stale content] Wording fixes next to removed tags.** `rootSplit.test.ts` said edge cases and mutation checks "land in Plan 226-10 Task 2"; they are covered in the same file, so the header now says "covered below". `findability.test.ts` and `fallbackExpectimax.test.ts` headers reference sibling describe titles ("findability ranking") that were renamed in the same plan; the references were updated to match. No assertion, mock factory, fixture or `vi.mock` path was touched.

**Total deviations:** 1 blocking environment prep, 3 plan notes. Impact: none on scope or behavior.

## Issues Encountered

- The worktree sandbox rejects compound shell lines, `xargs` with npm/git, and `awk` with pipes; helper scripts (`temp/241-46/*.py`) and one-command-per-call were used instead.
- The codemod left a few short first lines after removing a leading tag (for example "// rankScore blends toward" followed by a line starting with "V_fallback"). They read correctly and were not re-wrapped, to keep the diff reviewable.

## Known Stubs

None.

## Threat Flags

None. Comments and titles only; T-241-64 (assertion tampering) is mitigated by `cleanup.py diff` exiting 0 (non-title tokens identical to the phase base) and the unchanged vitest counts.

## Self-Check: PASSED

Files verified present: all 34 modified test files, this SUMMARY. Commits `f67566c1b` and `86a75dc3d` are ancestors of HEAD.
