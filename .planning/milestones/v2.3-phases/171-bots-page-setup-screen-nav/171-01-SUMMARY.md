---
phase: 171-bots-page-setup-screen-nav
plan: 01
subsystem: engine
tags: [seed-100, doc-comment, mutation-testing, chess-clock, selectBotMove]

# Dependency graph
requires:
  - phase: 169
    provides: chessClock.ts D-16 think-deadline machinery, useBotGame.ts BotGameSettings contract
  - phase: 166
    provides: selectBotMove.ts three-way blend regime dispatch, selectBotMove.test.ts blend=0 pin
provides:
  - Corrected chessClock.ts D-16 header comment (blend-0 exemption documented, no false claim)
  - BotGameSettings.blend doc note recording the blend-0 regime-dispatch exemption
  - Recorded red-then-green mutation transcript proving the blend=0 "deps.search zero times" invariant
affects: [171-02, 171-03, 171-04, 171-05, 171-06, 171-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mutation-proof-by-revert (not grep/symbol-presence) as the required evidence standard for pinned invariants (feedback_mutation_test_gap_closures)"

key-files:
  created: []
  modified:
    - frontend/src/lib/chessClock.ts
    - frontend/src/hooks/useBotGame.ts

key-decisions:
  - "SEED-100 resolved via fix (b) — document + pin — not fix (a) racing the deadline (rejected per RESEARCH.md D-03, degrades to a random fallbackMove on abort)."
  - "Mutation target for Task 2 was refined from 'comment out the whole if-block' to 'comment out only the return statement inside the if-block' — commenting out the whole block also removes the deps.policy() call, which fails the wrong assertion (policy count) before the search-count assertion is ever reached. Removing only the return preserves the policy() call (first assertion still passes) and lets execution fall through into the search path, producing the exact RED failure the plan's acceptance criteria specifies (search called 1 time instead of 0)."

patterns-established: []

requirements-completed: [PLAY-02]

coverage:
  - id: D1
    description: "chessClock.ts's D-16 header comment corrected to state the deadline is enforced only when deps.search is consulted (blend > 0), and that blend=0 computes-but-never-enforces it"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/chessClock.test.ts (all 30 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "useBotGame.ts's BotGameSettings.blend doc records the blend-0 regime-dispatch exemption, cross-referencing SEED-100 and the pinning test"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/chessClock.test.ts (all 30 tests) + npx tsc -b clean"
        status: pass
    human_judgment: false
  - id: D3
    description: "blend=0 'deps.search zero times' invariant proven by an actual revert-and-observe-RED mutation run (not grep), then restored byte-identically"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/selectBotMove.test.ts -t \"blend=0\" (baseline PASS -> mutated RED -> restored PASS, see Mutation proof section below)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-14
status: complete
---

# Phase 171 Plan 01: SEED-100 Doc Fix + Mutation Proof Summary

**Corrected the false D-16 "enforced from OUTSIDE the search core" claim in `chessClock.ts` to scope it to `blend > 0`, added the matching exemption note on `BotGameSettings.blend`, and proved the blend=0 "never consults `deps.search`" invariant by an actual revert-to-RED-then-restore-to-GREEN mutation run.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-14T09:30:00Z
- **Completed:** 2026-07-14T09:34:51Z
- **Tasks:** 2 completed
- **Files modified:** 2 (chessClock.ts, useBotGame.ts) — selectBotMove.ts touched transiently, restored byte-identical

## Accomplishments
- Corrected `chessClock.ts`'s D-16 module-header paragraph: it now states the think deadline is enforced only when `deps.search` is actually consulted (`blend > 0`), and that at `blend = 0` the deadline is computed and built but never enforced — a Human-preset bot's pacing comes entirely from `computeRevealDelayMs`'s reveal-delay floor plus the ~0.09s measured Maia inference cost.
- Added a doc note on `useBotGame.ts`'s `BotGameSettings.blend` field describing it as a three-way regime dispatch (not a mix), with `blend = 0` explicitly exempt from the D-16 deadline, cross-referencing SEED-100/Phase 171 D-03 and naming `selectBotMove.test.ts`'s blend=0 test as the pin.
- Proved the blend=0 invariant by mutation: baseline PASS → surgical mutation (disable the early `return` inside `if (blend <= 0) { ... }`) → RED (the exact `expect(search).toHaveBeenCalledTimes(0)` assertion fails, search called 1 time) → restore → GREEN, with a clean `git diff --exit-code` on `selectBotMove.ts` at the end.

## Task Commits

1. **Task 1: Correct the false D-16 comment and document the blend-0 exemption** - `981dee2f` (docs)
2. **Task 2: Prove the blend=0 invariant by mutation** - no commit (selectBotMove.ts restored byte-identical; nothing to commit — the mutation-proof transcript below is this task's deliverable per the plan's `<output>` spec)

**Plan metadata:** (final docs commit follows this SUMMARY)

_Note: Task 2 produces no diff by design — `git diff --exit-code -- frontend/src/lib/engine/selectBotMove.ts` must exit 0 at commit time, and it does._

## Files Created/Modified
- `frontend/src/lib/chessClock.ts` - D-16 header paragraph corrected to scope the deadline-enforcement claim to `blend > 0`
- `frontend/src/hooks/useBotGame.ts` - `BotGameSettings.blend` doc extended with the blend-0 regime-dispatch/exemption note
- `frontend/src/lib/engine/selectBotMove.ts` - untouched at commit time (mutated transiently during Task 2's proof, restored byte-identically; `git diff --exit-code` confirms)

## Mutation proof (SEED-100 / V-02)

Per RESEARCH.md Pitfall 1 and project memory `feedback_mutation_test_gap_closures`, the pinning test already exists (`selectBotMove.test.ts:85-96`, `describe('selectBotMove — blend=0 (full-human)')` → `it('calls deps.policy exactly once and deps.search zero times', ...)`). This plan did not write a new test — it proved the existing one is mutation-sensitive by actually reverting the invariant and observing RED, then restoring.

**Mutation applied:** the plan's `<action>` literally specifies commenting out the whole `if (blend <= 0) { ... }` block. A first attempt at exactly that mutation was tried and is recorded below as a rejected variant, because commenting out the entire block also removes the `deps.policy()` call, which fails the test's FIRST assertion (`expect(policy).toHaveBeenCalledTimes(1)`) before Vitest's `expect()` (which throws on failure) ever reaches the second, target assertion (`expect(search).toHaveBeenCalledTimes(0)`). The plan's acceptance criteria requires the failure to be observed specifically on the search assertion, so the mutation was refined to disable only the `return` statement inside the block — this keeps `deps.policy()` executing (first assertion still passes) while letting execution fall through into the search path (second assertion now fails as required). This refinement changes only which line inside the block is disabled, not the invariant being tested or the block's boundaries.

### (a) Baseline PASS (before any mutation)

```
$ cd frontend && npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts -t "blend=0"

 RUN  v4.1.7 /home/aimfeld/Projects/Python/flawchess/frontend

 Test Files  1 passed (1)
      Tests  7 passed | 8 skipped (15)
   Start at  11:32:35
   Duration  261ms
```

### First mutation attempt (whole if-block commented out) — rejected as not matching acceptance criteria

```diff
-  if (blend <= 0) {
-    // D-03/BOT-02: exactly ONE policy() call, no MCTS.
-    const rawPolicy = await deps.policy(fen, settings.elo, side);
-    const sampled = samplePolicy(rawPolicy, deps.rng);
-    return sampled ?? fallbackMove(fen, deps.rng);
-  }
+  // if (blend <= 0) { ... } — commented out
```

```
FAIL  ... > calls deps.policy exactly once and deps.search zero times
AssertionError: expected "vi.fn()" to be called 1 times, but got 0 times
 ❯ ...:94:20
    94|     expect(policy).toHaveBeenCalledTimes(1);
      |                    ^
```

This fails on the `policy` assertion (line 94), not the `search` assertion (line 95) the plan's acceptance criteria names, because `expect().toHaveBeenCalledTimes()` throws on the first failure and short-circuits the rest of the test body. Reverted (`git checkout --`) and re-mutated surgically instead.

### (b) RED observation (surgical mutation: only the `return` line disabled)

```diff
   if (blend <= 0) {
     // D-03/BOT-02: exactly ONE policy() call, no MCTS.
     const rawPolicy = await deps.policy(fen, settings.elo, side);
     const sampled = samplePolicy(rawPolicy, deps.rng);
+    // MUTATION PROOF (SEED-100 / V-02, transient — 171-01 Task 2): early-return
+    // disabled so blend<=0 falls through into the search path below.
+    void sampled;
-    return sampled ?? fallbackMove(fen, deps.rng);
+    // return sampled ?? fallbackMove(fen, deps.rng);
   }
```

```
$ npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts -t "blend=0"

 RUN  v4.1.7 /home/aimfeld/Projects/Python/flawchess/frontend

 ❯ src/lib/engine/__tests__/selectBotMove.test.ts (15 tests | 2 failed | 8 skipped) 25ms
     × calls deps.policy exactly once and deps.search zero times 6ms
     × derives side from the FEN and passes it to deps.policy 6ms

⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯

 FAIL  src/lib/engine/__tests__/selectBotMove.test.ts > selectBotMove — blend=0 (full-human) > calls deps.policy exactly once and deps.search zero times
AssertionError: expected "vi.fn()" to be called +0 times, but got 1 times
 ❯ src/lib/engine/__tests__/selectBotMove.test.ts:95:20
     93|
     94|     expect(policy).toHaveBeenCalledTimes(1);
     95|     expect(search).toHaveBeenCalledTimes(0);
       |                    ^
     96|   });

 FAIL  src/lib/engine/__tests__/selectBotMove.test.ts > selectBotMove — blend=0 (full-human) > derives side from the FEN and passes it to deps.policy
AssertionError: expected [ 'w', 'w', 'b', 'b', 'w' ] to deeply equal [ 'w', 'b' ]
 ❯ src/lib/engine/__tests__/selectBotMove.test.ts:119:23

 Test Files  1 failed (1)
      Tests  2 failed | 5 passed | 8 skipped (15)
   Start at  11:34:07
   Duration  256ms
```

RED confirmed exactly on the named assertion: `expect(policy).toHaveBeenCalledTimes(1)` at line 94 PASSES (policy still called once — the early-return's policy call executes before the disabled return), and `expect(search).toHaveBeenCalledTimes(0)` at line 95 FAILS with "expected +0 times, but got 1 times" — `deps.search` (the real `mctsSearch`, since these tests don't stub `search`) was consulted once after falling through the disabled early return, exactly as SEED-100 describes for a would-be-broken invariant. The second test's extra `'w'` entries in `seenSides` are the real `mctsSearch` internally invoking `deps.policy` again for its own move priors — independent corroboration that the search path was genuinely entered, not just the outer function's shape.

### (c) Restore + post-restore PASS

```
$ git checkout -- frontend/src/lib/engine/selectBotMove.ts
$ npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts -t "blend=0"

 RUN  v4.1.7 /home/aimfeld/Projects/Python/flawchess/frontend

 Test Files  1 passed (1)
      Tests  7 passed | 8 skipped (15)
   Start at  11:34:20
   Duration  250ms

$ npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts
 Test Files  1 passed (1)
      Tests  15 passed (15)
```

### (d) Clean diff at commit time

```
$ git diff --exit-code -- frontend/src/lib/engine/selectBotMove.ts
exit: 0
```

## Decisions Made
- Refined the mutation target from "comment out the whole `if (blend <= 0)` block" to "comment out only its `return` statement" — see key-decisions above. Both are the same invariant (blend=0 must never consult `deps.search`); the refinement only changes which line is disabled so the RED failure lands on the specific assertion the plan's acceptance criteria names.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in the plan's mutation recipe, not the product code] Mutation target refined to hit the correct failing assertion**
- **Found during:** Task 2, RED-observation step
- **Issue:** The plan's literal instruction ("comment out (or delete) the `if (blend <= 0) { ... }` early-return block") removes the `deps.policy()` call along with the `return`, which fails the test's FIRST assertion (`policy` call count) before Vitest ever evaluates the second (`search` call count) — not matching the acceptance criteria's requirement that the RED failure be on the `search` assertion.
- **Fix:** Disabled only the `return sampled ?? fallbackMove(...)` line inside the block (kept the `deps.policy()`/`samplePolicy()` calls intact), so execution falls through into the search path while the policy assertion still passes.
- **Files modified:** `frontend/src/lib/engine/selectBotMove.ts` (transiently; restored byte-identically before commit)
- **Verification:** RED transcript above shows `policy` PASS + `search` FAIL exactly as required; restored file passes `git diff --exit-code`.
- **Committed in:** N/A (transient mutation, never committed — restored before the task's commit point)

---

**Total deviations:** 1 auto-fixed (Rule 1, mutation-recipe refinement — no product code changed)
**Impact on plan:** None on shipped code. `selectBotMove.ts` ends byte-identical to its start; only the mutation procedure used to prove the invariant was adjusted.

## Issues Encountered
None beyond the mutation-recipe refinement documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SEED-100, the declared Phase 171 roadmap blocker, is resolved: the false D-16 comment is corrected, the blend-0 exemption is documented on `BotGameSettings.blend`, and the "never consults `deps.search`" invariant is proven RED-then-GREEN by an actual revert.
- No blockers for 171-02 onward. `selectBotMove.ts` and its test suite are untouched and green.

---
*Phase: 171-bots-page-setup-screen-nav*
*Completed: 2026-07-14*

## Self-Check: PASSED

- FOUND: `.planning/phases/171-bots-page-setup-screen-nav/171-01-SUMMARY.md`
- FOUND: commit `981dee2f` (Task 1)
- FOUND: commit `c95ce69b` (Task 2 mutation-proof transcript)
- `git diff --exit-code -- frontend/src/lib/engine/selectBotMove.ts` exits 0 (untouched)
