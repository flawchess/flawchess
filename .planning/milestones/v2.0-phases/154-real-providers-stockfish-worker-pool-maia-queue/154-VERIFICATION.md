---
phase: 154-real-providers-stockfish-worker-pool-maia-queue
verified: 2026-07-06T18:10:00Z
status: passed
score: 8/8 must-haves verified (2 deferred, not counted against score)
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 6/9
  gaps_closed:
    - "stopAll() settles every in-flight (dispatched, slot.current) grade() promise with an empty Map, not just queued pending requests (POOL-04, D-03) — CR-01"
    - "terminate() settles every in-flight grade() promise with an empty Map before worker.terminate() kills the worker (POOL-04, D-03) — CR-02"
    - "Every policy() call is answered via a proper async FIFO queue — a pre-ready worker init error no longer permanently deadlocks the queue (POOL-03, D-04) — CR-03"
  gaps_remaining: []
  regressions: []
deferred:
  - truth: "The priority queue actually influences real-world grade() dispatch order in the integrated system (goal-backward derived from ROADMAP SC2's 'favoring nodes under the currently-highest-scoring root line')"
    addressed_in: "Phase 155"
    evidence: "154-03-PLAN.md <deferred_findings> WR-02: 'The frozen 2-arg EngineProviders.grade(fen, candidateUcis) contract has no channel for a caller to supply a priority/depth, and there is NO caller in Phase 154 ... Tracked forward as a Phase 155 requirement.' workerPool.ts header/docstring (lines 4-11, 118-123) now honestly states priority/depth are always 0 until Phase 155's MCTS orchestrator supplies real values, instead of claiming present-tense priority-ordered dispatch. This is an explicitly documented scope boundary (the ordering mechanism itself — enqueue/dequeueHighestPriority — is built and unit-tested, satisfying SC2's literal 'verified by a queue-ordering test' wording), not a silently dropped gap."
  - truth: "On a real iPhone and a real mid-tier Android device, a multi-position review session runs the pool without the tab reloading or crashing (SC4, POOL-04)"
    addressed_in: "Phase 155"
    evidence: "154-CONTEXT.md D-02/D-03 and 154-VALIDATION.md's Manual-Only Verifications explicitly and pre-approvedly defer this HUMAN-UAT: no React hook/UI exists to drive the pool until Phase 155 wires workerPool.ts + maiaQueue.ts into useFlawChessEngine.ts on /analysis. Carried forward unchanged from the initial verification pass."
---

# Phase 154: Real Providers (Stockfish Worker Pool + Maia Queue) — Verification Report

**Phase Goal:** The Phase 153 search core runs against real Stockfish.wasm and Maia workers — a 2–4-instance grading pool prioritized toward the current-best root line, and a dedicated Maia policy worker — sized adaptively so the browser tab stays within mobile Safari's memory ceiling.
**Verified:** 2026-07-06T18:10:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (154-03, 154-04)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `workerPool.ts` runs 2-4 single-threaded Stockfish.wasm workers in parallel grading candidate moves, no SharedArrayBuffer/COOP-COEP (POOL-01) | ✓ VERIFIED | `createWorkerPool`/`createSlot`/`ensureSpawned` in workerPool.ts:195-352; classic `new Worker(ENGINE_PATH)`, no SAB/postMessage-transfer usage anywhere (rechecked, this verification); 46/46 tests pass (workerPool.test.ts + maiaQueue.test.ts combined run) |
| 2 | Every MultiPV consumption path keys results by `pv[0]`, never the `multipv` rank (SC5) | ✓ VERIFIED | `grep -n "\.multipv" frontend/src/lib/engine/workerPool.ts` returns nothing (rerun, this verification); `handleLine` reads `parsed.pv[0]` (workerPool.ts:253); rank-swap regression test passes |
| 3 | `enqueue`/`dequeueHighestPriority` dequeue in priority order (priority desc, depth asc, UCI-string tie-break), not FIFO, verified by a queue-ordering test (POOL-02, SC2 literal wording) | ✓ VERIFIED | workerPool.ts:126-155; priority-ordering, depth-tie, UCI-tie unit tests pass in isolation |
| 4 | `maiaQueue.ts` supplies UCI-keyed move-probability distributions per node/per-side-ELO from a dedicated, separate Maia worker instance, with deduped narrow-ELO batching (never the full ladder) and entry-count parity with `maskAndSoftmax`'s SAN-keyed output (POOL-03, D-04) | ✓ VERIFIED | maiaQueue.ts:84-264; `grep -n "MAIA_ELO_LADDER" maiaQueue.ts` returns nothing (rerun); dedup/batching + entry-count-parity (promotion/castling/en-passant fixtures) tests pass |
| 5 | Every `policy()` call is answered via a proper async FIFO queue — no request ever silently dropped or left hanging, including on a pre-ready worker init error (POOL-03, D-04) | ✓ VERIFIED (was FAILED — CR-03 closed) | `handleMessage`'s `error` branch (maiaQueue.ts:194-219) now calls `settleAllAndDropWorker()` when `!isReady`, draining `pending` (not just `currentBatch`) and nulling `worker` so the next `policy()` re-spawns. Regression test `'drains pending and drops the dead worker on a PRE-READY error ... (CR-03)'` (maiaQueue.test.ts:274) passes; independently rerun in this verification (`npm test -- --run maiaQueue.test.ts`, 18/18 green) |
| 6 | Pool size adapts to device: mobile (`hardwareConcurrency<=4` OR coarse pointer) = 2, desktop = `clamp(cores-2,2,4)`, no UA-sniffing/`deviceMemory` (POOL-04/D-01) | ✓ VERIFIED | workerPool.ts:172-179; `grep -nE "deviceMemory\|userAgent"` returns nothing (rechecked); all computePoolSize branch tests pass |
| 7 | Workers (both pools) are spawned lazily on first call, never eagerly at page load (POOL-04/D-02) | ✓ VERIFIED | workerPool.ts `ensureSpawned()`/`spawned` flag (335-352); maiaQueue.ts `ensureSpawned()`/`worker` null-check (223-251); lazy-spawn tests pass for both |
| 8 | The pool exposes a clean, reliably-settling abort/lifecycle surface: `AbortSignal` per `grade()` call plus `stopAll()`/`terminate()` (POOL-04, D-03) | ✓ VERIFIED (was FAILED — CR-01/CR-02 closed) | `stopAll()` (workerPool.ts:421-441) and `terminate()` (443-460) now call `slot.current?.resolve(new Map())` + null it for every affected slot BEFORE/while draining `pending`. Test `'stopAll() sends stop to every thinking slot and clears the pending queue'` now awaits the previously-discarded in-flight promise (`await expect(second).resolves.toEqual(new Map())`, workerPool.test.ts:356) and a dedicated `'CR-02: terminate() resolves an in-flight (dispatched) grade() promise instead of hanging it'` test (359-370) — both pass. `void second;` no longer present (`grep -n "void second"` clean). Additionally WR-01 (pre-aborted signal, workerPool.ts:366) and WR-05 (empty `candidateUcis`, workerPool.ts:362) fail-fast guards added and tested. |
| 9 | Priority queue mechanism actually influences real-world `grade()` dispatch order in the integrated system (goal-backward derived beyond SC2's literal wording) | DEFERRED | See `deferred` frontmatter — the frozen 2-arg `EngineProviders.grade` contract (Phase 153) has no priority channel and no real caller exists until Phase 155's MCTS orchestrator; explicitly documented in 154-03-PLAN.md `<deferred_findings>` and corrected (no longer overclaimed) in workerPool.ts's header/docstring |
| 10 | Real-device (iPhone + mid-tier Android) multi-position review session runs the pool without tab reload/crash (SC4, POOL-04) | DEFERRED | See `deferred` frontmatter — no UI exists in this phase to drive the pool; pre-approved deferral to Phase 155, tracked in 154-VALIDATION.md |

**Score:** 8/8 countable truths verified (2 explicitly-documented deferrals to Phase 155, not counted against score — both were pre-approved scope boundaries, not silently dropped gaps)

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Real dispatch order actually uses live priorities (vs. `priority:0` today) | Phase 155 | 154-03-PLAN.md `<deferred_findings>` WR-02: no caller/channel exists until Phase 155's MCTS orchestrator; docstring corrected to state this honestly rather than claim present-tense priority-ordered dispatch |
| 2 | Real-device mobile-memory-ceiling UAT (SC4) | Phase 155 | 154-CONTEXT.md D-02/D-03 + 154-VALIDATION.md Manual-Only Verifications: sign-off approved, no UI exists until Phase 155 wires the pool into `/analysis` |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/engine/workerPool.ts` | `createWorkerPool()` factory implementing `EngineProviders.grade()` | ✓ VERIFIED (463 lines, real logic, all 3 gap-closure fixes present) | Structurally assignable to `EngineProviders['grade']`, verified via `tsc -b` (0 errors, this verification) and a type-level test |
| `frontend/src/lib/engine/__tests__/workerPool.test.ts` | mock-Worker vitest suite, strengthened per gap closure | ✓ VERIFIED | `void second;` removed; CR-01/CR-02/WR-01/WR-03/WR-04/WR-05 tests all present and passing |
| `frontend/src/lib/engine/maiaQueue.ts` | `createMaiaQueue()` factory implementing `EngineProviders.policy()` | ✓ VERIFIED (281 lines, real logic, CR-03/WR-03 fixes present) | Structurally assignable to `EngineProviders['policy']`, verified via `tsc -b` and a type-level test |
| `frontend/src/lib/engine/__tests__/maiaQueue.test.ts` | mock-Worker vitest suite, strengthened per gap closure | ✓ VERIFIED | Pre-ready-error (CR-03) and async-onerror (WR-03) regression tests present and passing |

**Wiring note:** Neither artifact is imported by any non-test file yet (`grep -rn "workerPool\|maiaQueue" frontend/src --include="*.ts*" | grep -v __tests__` returns nothing outside the modules' own headers) — this is BY DESIGN per both PLANs ("No React, no UI, no wiring into any hook — that is Phase 155") and confirmed clean by `npx knip` (no dead-export warnings, rerun in this verification). Not a gap.

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `workerPool.ts` `grade` | `EngineProviders.grade` (types.ts) | Structural assignment | ✓ VERIFIED | `const providerGrade: EngineProviders['grade'] = pool.grade` compiles (`tsc -b` 0 errors, rechecked) |
| `workerPool.ts` `handleLine` | `parseInfoLine` (uciParser.ts) | Import + call | ✓ VERIFIED | `import { parseInfoLine } from '@/hooks/uciParser'` (line 26), used at line 251 |
| `maiaQueue.ts` `policy` | `EngineProviders.policy` (types.ts) | Structural assignment | ✓ VERIFIED | `const providerPolicy: EngineProviders['policy'] = queue.policy` compiles |
| `maiaQueue.ts` | `maskAndSoftmax` (maiaEncoding.ts) + `sanToUci` (sanToSquares.ts) | Import + call | ✓ VERIFIED | Both imported (lines 33-34) and used at the SAN→UCI boundary (lines 144, 151) |
| `workerPool.ts` `stopAll`/`terminate` | in-flight `slot.current` request | Settle-before-null | ✓ VERIFIED (NEW — closes CR-01/CR-02) | `slot.current?.resolve(new Map())` then `slot.current = null` in both functions (workerPool.ts:431-432, 451-452), confirmed by passing regression tests |
| `maiaQueue.ts` `handleMessage` (error, pre-ready) | `pending` array + `worker` reference | Drain-and-drop | ✓ VERIFIED (NEW — closes CR-03) | `settleAllAndDropWorker()` (maiaQueue.ts:170-181) called from the `!isReady` branch (203-210), confirmed by passing regression test |

### Behavioral Spot-Checks

| Behavior | Command / Setup | Result | Status |
|----------|------------------|--------|--------|
| `stopAll()` resolves an in-flight (dispatched) `grade()` promise | `npm test -- --run workerPool.test.ts` — `'stopAll() sends stop to every thinking slot and clears the pending queue'` | `await expect(second).resolves.toEqual(new Map())` passes | ✓ PASS (CR-01 closed) |
| `terminate()` resolves an in-flight `grade()` promise | `npm test -- --run workerPool.test.ts` — `'CR-02: terminate() resolves an in-flight (dispatched) grade() promise instead of hanging it'` | Passes | ✓ PASS (CR-02 closed) |
| `maiaQueue` pre-ready init error resolves the pending `policy()` promise and self-heals | `npm test -- --run maiaQueue.test.ts` — `'drains pending and drops the dead worker on a PRE-READY error ... (CR-03)'` | Passes; `createdWorkers` grows to 2 on the next `policy()` call | ✓ PASS (CR-03 closed) |
| Pre-aborted signal / empty candidateUcis fail fast (WR-01/WR-05) | `npm test -- --run workerPool.test.ts` | Both tests pass, zero Worker constructions | ✓ PASS |
| Async `worker.onerror` + sync construction-throw are Sentry-visible (WR-03/WR-04, both files) | `npm test -- --run workerPool.test.ts maiaQueue.test.ts` | All onerror/Sentry-tag assertions pass (`stockfish-worker-pool`, `maia-queue-worker` tags) | ✓ PASS |
| Targeted test suite (both files) | `cd frontend && npm test -- --run src/lib/engine/__tests__/workerPool.test.ts src/lib/engine/__tests__/maiaQueue.test.ts` | 2 files, 46/46 tests passed | ✓ PASS |
| Full frontend suite (regression check) | `cd frontend && npm test -- --run` | 124 files, 1498/1498 tests passed | ✓ PASS (matches 154-04-SUMMARY.md's claimed count exactly) |
| Type check | `cd frontend && npx tsc -b` | 0 errors | ✓ PASS |
| Lint | `cd frontend && npx eslint src/lib/engine/workerPool.ts src/lib/engine/maiaQueue.ts src/lib/engine/__tests__/workerPool.test.ts src/lib/engine/__tests__/maiaQueue.test.ts` | 0 errors/warnings | ✓ PASS |
| Dead-export / unused-dependency check | `cd frontend && npx knip` | Clean, no output | ✓ PASS |
| Commit existence (154-03: eea4ec83, e8636e48, d12b884c; 154-04: 44203a20, 7cec5839) | `git cat-file -e <hash>` x5 | All 5 commits exist and match the claimed task/file scope in `git log` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|--------------|--------|----------|
| POOL-01 | 154-01, 154-03 | Stockfish grading pool, 2-4 workers, parallel, no SAB/COOP-COEP | ✓ SATISFIED | Truths #1, #2 VERIFIED; WR-03/WR-04 observability closed by 154-03 |
| POOL-02 | 154-01, 154-03 | Priority queue schedules grading work toward currently-best root lines, verified by a queue-ordering test | ✓ SATISFIED (per SC2 literal wording) | Truth #3 (isolated queue logic + ordering test) VERIFIED; the extra goal-backward-derived truth (real dispatch actually using live priorities) is explicitly deferred to Phase 155 with corrected, honest docstrings (154-03 Task 3) — not silently dropped |
| POOL-03 | 154-02, 154-04 | Maia move-probability distributions per node/per-side-ELO from dedicated worker | ✓ SATISFIED | Truth #4 (dedup/entry-parity) and Truth #5 (no-drop FIFO, CR-03 closed) both VERIFIED |
| POOL-04 | 154-01, 154-02, 154-03 | Adaptive pool sizing + lazy spawn/terminate + clean abort/lifecycle surface | ✓ SATISFIED (code-complete; SC4 real-device UAT deferred) | Truths #6, #7, #8 VERIFIED (CR-01/CR-02 closed by 154-03); SC4 real-device UAT (Truth #10) is a pre-approved deferral to Phase 155, unchanged from initial verification |

No orphaned requirements — REQUIREMENTS.md maps only POOL-01..04 to Phase 154, and all four plans declare this exact set (154-01: POOL-01/02/04; 154-02: POOL-03/04; 154-03: POOL-01/02/04; 154-04: POOL-03).

### Anti-Patterns Found

No blocking anti-patterns found in this re-verification pass. The 3 critical findings (CR-01, CR-02, CR-03) from 154-REVIEW.md and the prior VERIFICATION.md are now closed with passing regression tests (verified above). Status of the previously-listed warnings:

| Finding | Prior Severity | Status Now |
|---------|----------------|------------|
| WR-01 (pre-aborted signal ignored) | Warning | ✓ FIXED (workerPool.ts:366, tested) |
| WR-02 (priority hardcoded to 0, no caller channel) | Warning | Documented deferral — docstring corrected to state this honestly (workerPool.ts:1-11, 118-123); tracked forward as a Phase 155 requirement per 154-03-PLAN.md `<deferred_findings>` |
| WR-03 (no `worker.onerror` handler, both files) | Warning | ✓ FIXED (workerPool.ts:321-330, maiaQueue.ts:235-240, both tested with Sentry-tag assertions) |
| WR-04 (empty construction catch, workerPool.ts) | Warning | ✓ FIXED (workerPool.ts:343-350, now calls `Sentry.captureException`, tested) |
| WR-05 (empty candidateUcis unrestricted search) | Warning | ✓ FIXED (workerPool.ts:362, tested) |
| IN-01 (cacheGrades overwrites vs merges) | Info | DEFERRED (154-03-PLAN.md — never returns wrong data, throughput-only, out of scope for a hang-defect closure pass) |
| IN-02 (cached containers shared by reference) | Info | DEFERRED (both plans — latent only, sole consumer is read-only) |
| IN-03 (computePoolSize undefined-cores fallback) | Info | DEFERRED (154-03-PLAN.md — coincidentally correct today, not a live bug) |
| IN-04 (`void second;` masking CR-01) | Info | ✓ FIXED (removed, replaced with an awaited assertion; `grep -n "void second"` confirmed clean) |
| IN-05 (maiaQueue caches `{}` on missing ELO) | Info | DEFERRED (154-04-PLAN.md — cannot fire today, defensive-only) |

No `TBD`/`FIXME`/`XXX` debt markers found in any of the four phase files (`grep -nE "TBD|FIXME|XXX"` clean, rechecked). No empty `catch {}` blocks remain in either source file (rechecked). No `console.log`-only implementations or placeholder/stub text found.

### Human Verification Required

None required for this verification pass. All previously-open code-level defects (CR-01, CR-02, CR-03) have deterministic, independently-rerun regression tests confirming the fix. SC4's real-device UAT and the WR-02 real-priority-wiring item are genuine deferrals to Phase 155 (no UI/caller exists yet to test them against), pre-approved and explicitly tracked — not open items for this phase.

### Gaps Summary

All three gaps from the initial verification pass (2026-07-06T14:59:15Z) are closed:

1. **CR-01/CR-02 (stopAll()/terminate() promise hangs, workerPool.ts)** — closed by 154-03 Task 1. Both functions now call `slot.current?.resolve(new Map())` and null it for every affected slot before/while draining `pending`. The test that previously masked this (`void second;`) now asserts the in-flight promise resolves. Independently rerun in this verification — passes.
2. **CR-03 (pre-ready worker-init-error deadlock, maiaQueue.ts)** — closed by 154-04 Task 1. `handleMessage`'s error branch now drains `pending` (not just `currentBatch`) and nulls `worker` when `!isReady`, via the new `settleAllAndDropWorker()` helper, so a subsequent `policy()` call re-spawns a fresh worker instead of queuing behind a dead one. Independently rerun — passes.
3. Additional hardening delivered alongside the gap closure: WR-01 (pre-aborted signal), WR-05 (empty candidateUcis), WR-03/WR-04 (async `onerror` + sync construction-throw Sentry visibility, both files) — all implemented and tested, closing the broader "silent promise hang" failure class the reviewer flagged.

The one remaining open item (WR-02, real priority-value wiring into `grade()`) is not a phase-154 defect: the frozen 2-arg `EngineProviders.grade()` contract from Phase 153 has no channel for a caller-supplied priority, and no real caller exists until Phase 155's MCTS orchestrator is wired in. This was explicitly documented as a deferral (not silently dropped) in 154-03-PLAN.md's `<deferred_findings>`, and the module's docstring was corrected to stop overclaiming present-tense priority-ordered dispatch. The isolated ordering mechanism itself (`enqueue`/`dequeueHighestPriority`) satisfies ROADMAP SC2's literal wording ("verified by a queue-ordering test").

Full regression check: 124 test files / 1498 tests pass across the whole frontend suite (rerun in this verification, matches 154-04-SUMMARY.md's claim exactly); `tsc -b`, `eslint`, and `knip` are all clean. All 5 gap-closure commits (eea4ec83, e8636e48, d12b884c, 44203a20, 7cec5839) exist in git history and match their claimed scope.

**Recommendation:** Phase 154 goal is achieved. Proceed to Phase 155, which owns wiring both providers into `useFlawChessEngine`/`mctsSearch` (the first real caller) and is the natural point to supply real per-root-line priorities into `grade()` (WR-02) and run the SC4 real-device UAT.

---

_Verified: 2026-07-06T18:10:00Z_
_Verifier: Claude (gsd-verifier)_
