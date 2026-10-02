---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 11
subsystem: engine
tags: [mcts, root-split, gradeRoot, stockfish-pool, arm-A21S, worker-pool]

requires:
  - phase: 226-10
    provides: "Arm A21S engine half (D-18): rootSplit.ts's partitionCandidates/mergeShardGrades/ROOT_SPLIT_MAX_SHARDS, EngineProviders.gradeRoot?, mctsSearch.ts's dispatchExpansion routing line"
provides:
  - "Arm A21S app half (D-18): WorkerPool.gradeRoot(fen, candidateUcis, signal?, gradingDepth?) — fans a root grade across countIdleReadySlots(state) shards (k = min(idle count, candidates, ROOT_SPLIT_MAX_SHARDS)); k<=1 delegates to the unchanged grade() path"
  - "L-2 fail-closed semantics: any shard that does not complete via bestmove (abort, watchdog fire, slot death, stopAll) — or the outer signal aborting the whole group — resolves the WHOLE gradeRoot call to an empty Map, never a partial merge; siblings are stopped via the group's own AbortController"
  - "L-3 cache isolation: shard requests carry readCache/writeCache: false (new optional QueuedGradeRequest flags); the group performs exactly ONE success-only merged gradeCache.write at (fen, gradingDepth) — grep-verified exactly 2 gradeCache.write call sites in workerPoolDispatch.ts"
  - "L-4/D-08: fan-out is sized from LIVE idle+ready+unassigned+alive slots at call time (0 whenever anything is already pending), not a static pool-size constant"
  - "Both app call sites wired: useFlawChessEngine.ts's providers and useBotGameEngineDispatch.ts's buildBotMoveDeps both pass gradeRoot: pool.gradeRoot alongside grade (D-18/Pitfall 1 — the shipped app now splits the root identically to the calibration harness)"
  - "D-17 not fired (CANDIDATE_CAP_ARM_ACTIVE = False, scripts/engine_throughput_226_verdict.py) — arm A21SC's non-root candidate cap was NOT implemented; Task 3's own <verify> confirms no '(arm A21SC)' commit exists"
affects: [226-12]

actuals:
  tokens: 10989
  tasks: 3
  commits: 2
  plan_head_before: 788ce0a66d76bb9e5e56adb3eb7b5de48ae872b1
  plan_head_after: f6c1f7a5452389d744d61e51f284a026d5cea5f4

tech-stack:
  added: []
  patterns:
    - "Shared request-submission body (submitGradeRequest) extracted from grade()'s pre-existing body, parameterized by { readCache?, writeCache? } options — grade() calls it with {} (byte-identical command stream/timing for every existing test), gradeRoot()'s per-shard requests call it with { readCache: false, writeCache: false }. Returns { promise, req } so the caller (gradeRoot's group) can inspect the per-request completed flag after settlement, not just the resolved grades."
    - "Per-shard completion tracking via a new QueuedGradeRequest.completed flag, set ONLY by handleLine's bestmove branch — every other settle path (abort, stopAll, terminate, watchdog fire) never touches it, so 'did this shard finish via a real bestmove' is distinguishable from 'did this shard's promise merely resolve' without a second resolve path."
    - "Group orchestration via a fresh AbortController per gradeRoot() call, linked to the caller's outer signal by exactly ONE manual addEventListener/removeEventListener pair (never AbortSignal.any, per plan prohibition) — the first shard to settle without completed=true marks the group failed and calls groupController.abort(), which stops every still-thinking sibling through ITS OWN existing abort-handling path (no duplicated stop logic)."

key-files:
  created: []
  modified:
    - frontend/src/lib/engine/workerPoolState.ts
    - frontend/src/lib/engine/workerPoolDispatch.ts
    - frontend/src/lib/engine/workerPool.ts
    - frontend/src/lib/engine/__tests__/workerPool.test.ts
    - frontend/src/hooks/useFlawChessEngine.ts
    - frontend/src/hooks/useBotGameEngineDispatch.ts

key-decisions:
  - "gradeRoot's guard prologue (empty candidates, already-aborted signal, full-set cache-read hit, ensureSpawned, no-slots/noLiveSlotRemains) is copied verbatim ahead of the k-computation, then k<=1 delegates to the existing grade() function rather than a bespoke single-shard path — per the plan's own <action> text. This means a k<=1 call performs the cache-read guard TWICE (once in gradeRoot's own prologue, once inside grade()'s call to submitGradeRequest), double-counting a cache MISS in that narrow fallback case. No test in this plan's behavior list exercises cache-stats counting on that specific path, and the plan's action text explicitly prescribes this structure, so it was implemented literally rather than optimized away."
  - "countIdleReadySlots(state) lives in workerPoolDispatch.ts (not workerPoolState.ts) per the plan's own file-content spec, even though it is a pure predicate over PoolState similar in shape to noLiveSlotRemains — kept local (not exported) since gradeRoot is its only caller."
  - "The group's per-shard settlement tracking runs via each submission's own .promise.then(...) callback (a microtask), not a synchronous hook into fireWatchdog/handleLine — confirmed correct via the mutation-checked 'L-2: 3 shards completing with real grades before a 4th is aborted' test, which specifically exercises a scenario where naive theorizing about synchronous propagation would have missed a bug (an earlier draft of this test used only empty-accumulator shards, which passed even with the L-2 gate disabled, since merging all-empty results is indistinguishable from resolving empty directly)."

requirements-completed: []

coverage:
  - id: D1
    description: "WorkerPool.gradeRoot fans a root grade across every idle/ready slot at call time (k = min(idle, candidates, ROOT_SPLIT_MAX_SHARDS)); k<=1 takes the unchanged grade() path"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts 'createWorkerPool: gradeRoot() root split (Phase 226 L-2/L-3/L-4)' (2 tests: real mctsSearch root over a real pool posts one go per idle slot in round-robin shards covering all 10 candidates; resolves with all grades and caches one merged entry, later grade() calls are cache hits with no extra go line)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts 'createWorkerPool: gradeRoot() root split — failure paths and edge cases (Phase 226 L-2/L-3/L-4)' (12 tests covering k<=1 fast paths, mobile sizing k=2, busy-slot k=3, non-empty-pending degrade)"
        status: pass
    human_judgment: false
  - id: D2
    description: "L-2: any non-completed shard (abort/watchdog/death/stopAll) — or an outer-signal abort — resolves the WHOLE gradeRoot call empty, stopping every sibling; never a partial merge, even when other shards already had real grades"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts: 'an outer abort mid-flight...', 'L-2: 3 shards completing with real grades before a 4th is aborted...', 'one shard slot watchdog-firing fails the whole group empty and stops the siblings'"
        status: pass
      - kind: other
        ref: "Mutation check (a): disabled the groupFailed/signal.aborted gate in workerPoolDispatch.ts's finish() — the partial-success-then-abort test failed (leaked 3 real grades, size 3 instead of 0); reverted, git diff confirmed empty"
        status: pass
    human_judgment: false
  - id: D3
    description: "L-3: shard requests neither read nor write the shared GradeCache; the group performs exactly ONE success-only merged write at (fen, gradingDepth) — grep -c confirms exactly 2 gradeCache.write call sites in workerPoolDispatch.ts (bestmove branch + group success path)"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts: cache-miss-after-abort assertion, and the post-failure cache-miss assertion in the partial-success test"
        status: pass
      - kind: other
        ref: "grep -c 'state.gradeCache.write(' frontend/src/lib/engine/workerPoolDispatch.ts == 2 (Task 1 acceptance criterion, re-confirmed at HEAD)"
        status: pass
      - kind: other
        ref: "Mutation check (b): forced shard writeCache: true — the post-failure cache-miss check failed (registered a hit instead of a miss); reverted, git diff confirmed empty"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-08: fan-out size is computed from LIVE idle+ready+unassigned+alive slots at call time, never a static pool-size constant — a busy slot leaves k reduced, and a non-empty pending queue forces k to 0"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts: 'one slot busy with another request leaves k = 3...', 'a non-empty pending queue makes gradeRoot take the plain grade() path...', 'a mobile-sized pool (MOBILE_POOL_SIZE 2 slots) fans the root out to exactly 2 shards'"
        status: pass
      - kind: other
        ref: "Mutation check (c): countIdleReadySlots counting every slot regardless of state — the busy-slot test timed out/hung and the k<=1 command-stream test failed; reverted, git diff confirmed empty"
        status: pass
    human_judgment: false
  - id: D5
    description: "Both app call sites (analysis board's useFlawChessEngine.ts, bot's useBotGameEngineDispatch.ts) pass gradeRoot: pool.gradeRoot alongside grade, so the shipped app splits the root identically to the calibration harness (RESEARCH Pitfall 1, D-18)"
    verification:
      - kind: other
        ref: "grep -q 'gradeRoot: pool.gradeRoot' on both frontend/src/hooks/useFlawChessEngine.ts and frontend/src/hooks/useBotGameEngineDispatch.ts — both found"
        status: pass
      - kind: e2e
        ref: "npm test -- --run (full frontend suite, 4471 tests) — no existing test asserting an exact providers/BotMoveDeps shape broke"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-17 gate: arm A21SC (non-root candidate cap) exists if and only if CANDIDATE_CAP_ARM_ACTIVE — measured False, so no code was added and no '(arm A21SC)' commit exists"
    verification:
      - kind: other
        ref: "python3 -c '...CANDIDATE_CAP_ARM_ACTIVE...' exits 1 (inactive); git log -F --grep='(arm A21SC)' --format=%H -1 returns empty — Task 3's own <verify> branch condition, both re-run at HEAD"
        status: pass
    human_judgment: false
  - id: D7
    description: "The A21 -> A21S content boundary (accept-rule.md section 1) holds: every file touched by this plan's commits is on the allowed list"
    verification:
      - kind: other
        ref: "git diff --name-only 29f543f27...(A21) HEAD -- frontend/src lists exactly: hooks/useBotGameEngineDispatch.ts, hooks/useFlawChessEngine.ts, __tests__/mctsSearch.test.ts, __tests__/rootSplit.test.ts, __tests__/workerPool.test.ts, mctsSearch.ts, rootSplit.ts, types.ts, workerPool.ts, workerPoolDispatch.ts, workerPoolState.ts — all on accept-rule.md's A21->A21S allowed list, nothing else"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-29
status: complete
---

# Phase 226 Plan 11: WorkerPool.gradeRoot Root Split, App Wiring, D-17 Gate (Arm A21S) Summary

**`WorkerPool.gradeRoot` fans one root grade call across every currently idle/ready slot (round-robin shards via Plan 226-10's `rootSplit.ts` helpers), fails the whole group empty on any shard trouble (mutation-proven), writes the shared cache exactly once on success, and is now wired into both the analysis board's and the bot's providers — completing arm A21S's app half. Arm A21SC's candidate cap was correctly skipped (D-17 did not fire).**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-29T03:50:00Z (approx, session start)
- **Completed:** 2026-09-29T04:45:00Z
- **Tasks:** 3 (2 executed, 1 correctly skipped per its own gate)
- **Files modified:** 6

## Accomplishments

- **Task 1** (`feat(226-11): WorkerPool.gradeRoot root split (arm A21S)`, commit `849a9bea2`):
  - Added optional `readCache?`/`writeCache?`/`completed?` flags to `QueuedGradeRequest`
    (`workerPoolState.ts`).
  - Refactored `grade()`'s entire body in `workerPoolDispatch.ts` into a shared
    `submitGradeRequest(state, ops, fen, candidateUcis, signal, gradingDepth, options)` helper —
    `grade()` now calls it with `{}` (byte-identical command stream and resolution timing for
    every pre-existing test — no added microtask), returning `{ promise, req }` so a caller can
    inspect the underlying request's `completed` flag after settlement.
  - Added `countIdleReadySlots(state)`: 0 whenever `state.pending.length > 0`, else the count of
    slots that are `idle`, `isReady`, unassigned (`current === null`), and not `dead`.
  - Added `export function gradeRoot(state, ops, fen, candidateUcis, signal?, gradingDepth?)`:
    copies `grade()`'s guard prologue verbatim (empty candidates, already-aborted signal,
    full-set cache-read hit, `ensureSpawned`, no-slots/`noLiveSlotRemains`), computes
    `k = min(countIdleReadySlots(state), candidateUcis.length, ROOT_SPLIT_MAX_SHARDS)`, and
    either delegates to `grade()` (`k <= 1`) or partitions via `partitionCandidates` (Plan
    226-10), links a fresh `AbortController` to the outer signal with exactly one manual
    `addEventListener`/`removeEventListener` pair (never `AbortSignal.any`), submits one shard
    request per partition with `{ readCache: false, writeCache: false }`, and resolves the whole
    group only once every shard has settled — empty if any shard lacked `completed: true` or the
    outer signal aborted, else `mergeShardGrades` plus exactly one
    `state.gradeCache.write(fen, gradingDepth, merged)`.
  - Updated `handleLine`'s `bestmove` branch (`workerPoolDispatch.ts`) to set
    `req.completed = true` unconditionally and gate the cache write on `req.writeCache !== false`;
    updated the "ONLY caller" comment to name the group's success-only write as the second (and
    now only other) write site.
  - Added `WorkerPool.gradeRoot` to the public interface and facade in `workerPool.ts`.
  - Added a `createWorkerPool: gradeRoot() root split (Phase 226 L-2/L-3/L-4)` describe block to
    `workerPool.test.ts` with the two Task-1-specified behavior tests, both driving a REAL
    `mctsSearch` over a REAL `createWorkerPool()`.
  - `grep -c "state.gradeCache.write(" frontend/src/lib/engine/workerPoolDispatch.ts` == 2
    (acceptance criterion).
  - Ran the tracer feedback gate per `HUMAN_VERIFY_MODE=end-of-phase` (default) with only
    `<automated>` verify present: re-ran `cd frontend && npx vitest run
    src/lib/engine/__tests__/workerPool.test.ts` (111/111 passed) before expanding to Task 2 —
    no checkpoint synthesized, per the executor's row-3 precedence rule.
- **Task 2** (`feat(226-11): wire gradeRoot into analysis and bot providers (arm A21S)`, commit
  `f6c1f7a54`):
  - `useFlawChessEngine.ts`'s `providers` object and `useBotGameEngineDispatch.ts`'s
    `buildBotMoveDeps` both now pass `gradeRoot: pool.gradeRoot` alongside `grade`.
  - Added a second describe block, `createWorkerPool: gradeRoot() root split — failure paths and
    edge cases (Phase 226 L-2/L-3/L-4)` (12 tests; named to include "root split" so the plan's own
    `-t "root split"` filter picks up both blocks), covering every behavior bullet: outer abort
    mid-flight + cache-miss-after; watchdog fire stopping siblings; a busy slot leaving `k = 3`
    untouched; a non-empty pending queue degrading to plain `grade()`; mobile sizing (`k = 2`);
    `k <= 1` fast paths (one idle slot, one candidate); a zero-info-line shard counting as
    completed not failed (and NOT polluting the cache with a partial merge); the outer signal's
    add-once/remove-on-settle listener discipline; and an additional test proving the L-2 gate is
    load-bearing against a genuinely non-trivial partial-merge scenario (3 real shard results
    present before a 4th shard's abort).
  - Ran the full frontend gate: `npx vitest run ... -t "root split"` (12/12), `npm test -- --run`
    (4471/4471), `npm run lint` (clean), `npm run build` (`tsc -b` + vite, clean), `npm run knip`
    (clean — no dead exports from the new `WorkerPool.gradeRoot`/hook wiring).
  - Confirmed both hook call sites via `grep -q "gradeRoot: pool.gradeRoot"` on both files.
- **Task 3** (no commit — D-17 gate correctly inactive):
  - `python3 -c "...engine_throughput_226_verdict...CANDIDATE_CAP_ARM_ACTIVE..."` confirmed
    `False`.
  - Per the plan's own `<action>` ("if CANDIDATE_CAP_ARM_ACTIVE is False, make no change and
    record the skip"), no files under `policyTemperature.ts`/`treeCommon.ts`/`mctsSearch.ts`/
    `fallbackExpectimax.ts`/`treeCommon.test.ts` were touched.
  - Ran the task's own `<verify>` literally: the `if python3 ...; then ...; else test -z
    "$(git log -F --grep='(arm A21SC)' --format=%H -1)"; fi` branch took the `else` arm and found
    no matching commit — verify passes.

## Task Commits

Each executed task was committed atomically:

1. **Task 1: End-to-end app root split — mctsSearch over a real createWorkerPool fans the root
   across idle slots** - `849a9bea2` (feat)
2. **Task 2: Failure-path tests with mutation checks, hook wiring, and the frontend gate** -
   `f6c1f7a54` (feat)
3. **Task 3: Conditional arm A21SC — non-root candidate cap** - not committed (D-17 not fired,
   arm A21SC absent — this is the correct, plan-specified outcome, not a deferral)

**Plan metadata:** (this commit, to follow)

_Note: Task 2 carried `tdd="true"`, but per this plan's own `<action>` text (mirroring 226-10
Plan 2's precedent) the sequence was test-then-mutation-prove against Task 1's already-landed
production code, not a RED-then-GREEN pair — a single `feat(...)` commit, since the hook wiring
(the primary production-code change in this task) landed alongside the tests in one commit._

## Files Created/Modified

- `frontend/src/lib/engine/workerPoolState.ts` - `QueuedGradeRequest` gains optional
  `readCache?`/`writeCache?`/`completed?` flags
- `frontend/src/lib/engine/workerPoolDispatch.ts` - `submitGradeRequest` (shared body behind
  `grade`/`gradeRoot`'s shards), `countIdleReadySlots`, `export function gradeRoot`, updated
  `handleLine` bestmove branch
- `frontend/src/lib/engine/workerPool.ts` - `WorkerPool.gradeRoot` interface member and facade
  wrapper forwarding to `dispatchGradeRoot`
- `frontend/src/lib/engine/__tests__/workerPool.test.ts` - two new describe blocks (14 new tests
  total) covering the happy path and every failure/edge-case behavior bullet
- `frontend/src/hooks/useFlawChessEngine.ts` - `providers` now includes `gradeRoot: pool.gradeRoot`
- `frontend/src/hooks/useBotGameEngineDispatch.ts` - `buildBotMoveDeps` now includes
  `gradeRoot: pool.gradeRoot`

## Decisions Made

- Followed the plan's own literal instruction for `gradeRoot`'s `k <= 1` fallback: re-run the
  guard prologue (including a redundant second cache-read check inside the delegated `grade()`
  call) rather than optimizing it away — the double-miss-counting side effect on that narrow path
  is undocumented by any test in this plan's behavior list and was accepted as specified rather
  than silently "fixed" outside plan scope.
- Kept `countIdleReadySlots` local to `workerPoolDispatch.ts` (not exported, not moved to
  `workerPoolState.ts`) per the plan's own file-content spec, even though it is a pure
  `PoolState`-only predicate similar in shape to `noLiveSlotRemains`.
- Named the new failure-paths describe block to literally contain the substring "root split" (not
  just "gradeRoot") so the plan's own `<verify>` `-t "root split"` filter picks up both Task 1's
  and Task 2's describe blocks in one run — verified by running the filtered command directly.
- Strengthened the plan's own behavior-bullet coverage with one additional test beyond the 8 named
  bullets — a genuine partial-success-before-failure scenario (3 shards complete with real,
  non-empty grades before a 4th is aborted) — after discovering during mutation-check (a) that the
  originally-planned "outer abort mid-flight" and "watchdog fire" tests are BLIND to a disabled
  L-2 gate whenever every shard's accumulator happens to be empty at failure time (an all-empty
  merge is indistinguishable from resolving `new Map()` directly). This is disclosed here because
  it means the mutation check initially reported a false "pass" against the wrong test before the
  gap was found and closed with the added test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test-authoring bug: iterating the shared `createdWorkers` array after a
watchdog fire silently included freshly-spawned REPLACEMENT workers**
- **Found during:** Task 2 (writing the "one shard slot watchdog-firing" test)
- **Issue:** `replaceDeadSlot` pushes a new `MockWorker` onto the same module-level
  `createdWorkers` array a dead slot's watchdog respawns into. The test's `for (const w of
  createdWorkers) expect(w.messages).toContain('stop')` loop, run AFTER the watchdog fire, iterated
  over 8 workers instead of the original 4 — failing on a fresh replacement that had only ever
  received its own init `'uci'` message.
- **Fix:** Captured `const originalWorkers = [...createdWorkers]` immediately after warming the
  pool, before dispatching `gradeRoot`, and asserted against that fixed snapshot instead of the
  live (growable) array.
- **Files modified:** frontend/src/lib/engine/__tests__/workerPool.test.ts
- **Verification:** Test passes; re-confirmed the fix does not mask a real defect by checking
  `originalWorkers.length === 4` explicitly via the prior `warmAllSlots` assertion.
- **Committed in:** `f6c1f7a54` (Task 2 commit)

**2. [Rule 1 - Bug] Test-authoring bug: a worker slot reused for a second, unrelated dispatch made
a bare `startsWith('go ')` filter over-count**
- **Found during:** Task 2 (writing the "non-empty pending queue" test)
- **Issue:** After freeing 4 busy slots in sequence, the freed slot that took over the ROOT
  request was the SAME worker object that had earlier served the original busy request (a
  different FEN) — so `rootWorker.messages.filter(m => m.startsWith('go '))` returned 2 lines (the
  old busy one plus the new root one), not 1.
- **Fix:** Filtered for the EXACT expected root `go` line string (`buildGradeGoCommand(...)`)
  instead of any line starting with `'go '`.
- **Files modified:** frontend/src/lib/engine/__tests__/workerPool.test.ts
- **Verification:** Test passes; the exact-string filter is strictly MORE precise than the
  original (proves no split occurred, not just "at least one go line exists").
- **Committed in:** `f6c1f7a54` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — test-authoring bugs discovered and fixed while
writing this plan's own new tests, not defects in the production code). **Impact on plan:** None
outside test-file scope; both fixes tightened test precision rather than loosening assertions.

## Issues Encountered

None beyond the two test-authoring bugs documented above as deviations. All three of Task 2's
required mutation checks succeeded on the first attempt at exposing their target defect (after the
test-precision fixes above), and each restore was confirmed `git diff`-empty against the Task 1
commit before proceeding.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Arm A21S is now COMPLETE on both halves: the engine routing (Plan 226-10) and the app's
  `WorkerPool.gradeRoot` implementation plus both hook call sites (this plan). The shipped app and
  the calibration harness now split the root identically (RESEARCH Pitfall 1 discharged).
- Arm A21SC does not exist for this phase (D-17 measured inactive, `CANDIDATE_CAP_ARM_ACTIVE =
  False`) — Plan 226-12 and later should NOT expect a `(arm A21SC)` commit anywhere in this
  phase's history.
- No throughput/calibration gate measurement was run in this plan — out of scope per the plan's
  own task list (per accept-rule.md section 3, measurement happens once arm A21S is complete on
  both sides, which it now is).
- `frontend/src/lib/engine/workerPoolDispatch.ts`'s `submitGradeRequest` extraction is a
  behavior-preserving refactor for every EXISTING `grade()` caller (confirmed via the full
  4471-test frontend suite passing unchanged) — future plans touching `grade()`'s guard prologue
  should update BOTH call sites (`grade()`'s `{}` options and `gradeRoot()`'s shard options) or
  risk the two diverging silently.

## Owner review required

None. This plan carried no genuine judgment call requiring owner sign-off — the one open question
(D-17 fired or not) was resolved unambiguously by re-running the frozen
`CANDIDATE_CAP_ARM_ACTIVE` constant, and the plan's own `<action>` text prescribed the exact
response (skip Task 3, record the skip) for the measured value.

## Self-Check: PASSED

- `frontend/src/lib/engine/workerPoolState.ts`, `workerPoolDispatch.ts`, `workerPool.ts`,
  `__tests__/workerPool.test.ts`, `../../hooks/useFlawChessEngine.ts`,
  `../../hooks/useBotGameEngineDispatch.ts` all confirmed present and modified via `git diff
  --stat` against `788ce0a66d76bb9e5e56adb3eb7b5de48ae872b1`.
- Commits `849a9bea2` and `f6c1f7a54` confirmed via `git log --oneline --all`.
- Both commit subjects confirmed to contain the literal `(arm A21S)` marker via `git log -F
  --grep='(arm A21S)'`.
- Re-ran ALL of this plan's `<verify>` commands at HEAD: Task 1's vitest run (111/111 at the time,
  120+ after Task 2's additions — all passing), Task 2's full gate (`-t "root split"` 12/12,
  full suite 4471/4471, lint clean, build clean, knip clean, both hook grep checks found), and
  Task 3's conditional branch (correctly took the "inactive" arm, found no `A21SC` commit).
- `grep -c "state.gradeCache.write(" frontend/src/lib/engine/workerPoolDispatch.ts` == 2,
  re-confirmed at HEAD.
- `git diff --name-only <A21 SHA> HEAD -- frontend/src` re-confirmed at HEAD: exactly the 11 files
  on accept-rule.md's A21->A21S allowed list, nothing else.
- All three Task 2 mutation checks re-confirmed: each reverted mutation leaves
  `workerPoolDispatch.ts` `git diff`-empty against the Task 1 commit (849a9bea2).

---
*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Completed: 2026-09-29*
