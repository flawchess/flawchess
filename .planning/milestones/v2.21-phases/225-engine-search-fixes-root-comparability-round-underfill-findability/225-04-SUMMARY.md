---
phase: 225-engine-search-fixes-root-comparability-round-underfill-findability
plan: 04
subsystem: engine
tags: [mcts, search, typescript, vitest, selectPath, round-dispatch]

requires:
  - phase: 225-engine-search-fixes-root-comparability-round-underfill-findability (plan 225-03)
    provides: accept-rule.md content assertions and A0 tooling baseline this plan's A2 arm is measured against
provides:
  - "Block-and-restart fix for selectPath's round underfill bug (SEED-170 item 2): a non-root node with zero selectable children no longer collapses the whole dispatch round"
  - "Permanent D-08 round-fill regression test (mctsSearch.roundFill.test.ts) proving full concurrency on peaked one- and two-candidate non-root policies"
  - "Concurrency=2 determinism test under two different provider resolution jitters on the peaked fixture"
  - "Single-chain fully-blocked termination test (T-225-07 DoS mitigation proof)"
  - "Arm A2 for the Phase 225 measurement gate: commit a9d5113ef"
affects: [225-05, 225-06, engine-search-fixes-225 measurement gate]

actuals:
  tokens: 5703
  tasks: 2
  commits: 3
  plan_head_before: 17716cb84338ecea525fe54e71af4bd2adfe7eee
  plan_head_after: a9d5113efed9270d02692c9b97e87508ecc414b2

tech-stack:
  added: []
  patterns:
    - "Round-scoped block flag (EngineNode.isBlocked + round-owned blockedThisRound list), separate from isPending, cleared after the fill loop — mirrors propagateClosure's closes-at-most-once termination argument"
    - "P/S run-length observable for round-size testing: policy() is the first await in dispatchExpansion, so consecutive policy() calls between onSnapshot events are exactly one round's dispatch size, with zero production instrumentation"

key-files:
  created:
    - frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts
  modified:
    - frontend/src/lib/engine/mctsSearch.ts

key-decisions:
  - "D-06/D-07 (CONTEXT.md, Claude's discretion on naming/placement): isBlocked is a distinct EngineNode field from isPending, filtered alongside isPending/isClosed in selectPath's candidate loop, and cleared in bulk (list + per-node reset) immediately after the round's fill loop, before Promise.all"
  - "D-09: fix-site comment names reports/continuous-dispatch/apply-order-design.md section 5 as the historical misread; that report itself is left unedited"
  - "Root policy stays flat (uniform) in the two round-fill regression cases so the peaked shape lives entirely in non-root nodes, isolating the bug to the mechanism it actually affects; a separate makeFullyPeakedPolicy helper peaks the root too, used only by the single-chain termination test"

requirements-completed: []

coverage:
  - id: D1
    description: "selectPath blocks a non-root dead-end node for the rest of the round and restarts from root instead of giving up the whole round; root dead end still returns null unchanged"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts#mctsSearch — D-08 round fill > every non-tail round dispatches exactly one-candidate (92%) expansions"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts#mctsSearch — D-08 round fill > every non-tail round dispatches exactly two-candidate (55%/37%) expansions"
        status: pass
    human_judgment: false
  - id: D2
    description: "isBlocked is a separate per-round flag from isPending, cleared after the fill loop each round; determinism per concurrency level is preserved"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts#mctsSearch — D-08 round fill > produces toEqual final snapshots and toEqual onSnapshot sequences at concurrency 2 under two different resolution jitters"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — ENGINE-07 determinism"
        status: pass
    human_judgment: false
  - id: D3
    description: "A fully blocked/single-chain tree terminates structurally at concurrency 4 (T-225-07 DoS mitigation) — no infinite restart loop"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts#mctsSearch — D-08 round fill > resolves with round size 1 every round on a fully single-chain tree"
        status: pass
    human_judgment: false
  - id: D4
    description: "The fix is mutation-proven: reverting selectPath's block-and-restart to the pre-fix unconditional return null makes the round-fill tests fail"
    verification:
      - kind: other
        ref: "Manual mutation check performed and reverted this plan (see Mutation Check section below) — not a standing automated gate"
        status: pass
    human_judgment: true
    rationale: "The mutation check is a one-time manual revert-and-confirm procedure per the project's mutation-test rule, not a repeatable automated test; recorded here as evidence rather than a re-runnable verification."

duration: 20min
completed: 2026-09-27
status: complete
---

# Phase 225 Plan 04: Round Underfill Fix in selectPath Summary

**`selectPath` now blocks a dead-end non-root node for the rest of the dispatch round and restarts the walk from the root instead of giving up on the entire round — restoring full concurrency-4 dispatch on peaked positions that previously collapsed to 1-2 expansions per round.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-27T07:40:00Z (approx)
- **Completed:** 2026-09-27T07:54:56Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- Fixed SEED-170 item 2: a non-root node reached mid-walk with zero selectable children (every child pending or closed) used to make `selectPath` return `null`, collapsing the *entire* dispatch round to whatever had already been dispatched — even when sibling root subtrees still had selectable work. On a peaked non-root policy (one candidate ~92%, or two at ~55%/37%) this fired on nearly every round, dropping effective concurrency from 4 to 1-2 on both the bot (50 nodes/c4) and analysis (400 nodes/c4) budgets.
- Added `EngineNode.isBlocked` — a separate per-round flag from `isPending` (D-07) — plus a round-owned `blockedThisRound` list in the `mctsSearch` round loop, cleared right after the fill loop and before `Promise.all`.
- Turned the throwaway round-underfill probe into a permanent regression test (`mctsSearch.roundFill.test.ts`, D-08): real `mctsSearch`, fake providers, italian-opening FEN, 50 nodes / concurrency 4 / 8 plies, asserting every non-tail round dispatches exactly `concurrency` expansions on both peaked shapes.
- Added a concurrency=2 determinism test (two runs, two different provider-resolution jitters, `toEqual` final snapshot and `toEqual` onSnapshot sequence) proving the fix does not touch the existing per-concurrency-level determinism guarantee (ENGINE-07/D-03).
- Added a fully single-chain-tree termination test at concurrency 4 (T-225-07): the search resolves, every round dispatches exactly 1 expansion, and `nodesEvaluated` equals `maxPlies` — proving the restart mechanism cannot loop or hang on the maximally constrained tree shape.
- Commented the fix site per D-09: `reports/continuous-dispatch/apply-order-design.md` section 5 misread the old unconditional `null` return as the "saturated tree" case; it actually fired whenever one favored subtree's only children were pending, starving every other subtree's dispatch slot. That historical report is left unedited.
- Performed and recorded the required mutation check (see below): reverting the fix makes the new round-fill tests fail, confirming they exercise the actual behavior change.

## Task Commits

1. **Task 1 (RED): failing D-08 round-fill test on the unmodified engine** — `d428a0194` (test)
2. **Task 1 (GREEN): block-and-restart fix in selectPath + round loop** — `82b910bb2` (fix)
3. **Task 2: concurrency=2 determinism + single-chain termination tests, module-header update, mutation check** — `a9d5113ef` (test)

_Note: Task 1 followed the RED -> GREEN TDD cycle as required by `tdd="true"`; Task 2's mutation check was performed manually and reverted, leaving no separate mutation commit (the mutated state was never committed, per the project's mutation-test rule)._

**A2 (Phase 225 measurement gate arm, `reports/engine-search-fixes-225/accept-rule.md`):** `a9d5113efed9270d02692c9b97e87508ecc414b2` — the last commit with the `(225-04)` scope touching `frontend/src/lib/engine`.

## RED Evidence (pre-fix round sequences)

Captured via a one-off Node probe run against the unmodified engine (identical fixture and helpers to the committed test, run before any fix landed), confirming the round-fill test failed on the baseline and reproducing 225-RESEARCH.md's own probe numbers:

- **One-candidate (92%) peaked non-root policy:** `nodesEvaluated=50`, rounds `[1,4,4,4,4,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]` (38 rounds instead of the expected 14; only the first two rounds after the root reach full concurrency, then it collapses to 1 for the remaining 34).
- **Two-candidate (55%/37%) peaked non-root policy:** `nodesEvaluated=50`, rounds `[1,4,4,4,4,2,2,2,2,2,2,2,2,2,2,2,2,2,2,3,2]` (21 rounds instead of 14; collapses to 2 for most of the run, with one round of 3).

Both shapes failed the committed test's assertions on the unmodified engine (`rounds.slice(1, -1).every((size) => size === ROUND_FILL_CONCURRENCY)` was `false` in both cases) before the fix, and passed after.

## Mutation Check (D-08, project mutation-test rule)

**Reverted code:** `selectPath`'s block-and-restart branch was temporarily replaced with the pre-fix unconditional give-up:

```ts
// MUTATION-TEST (temporary): pre-fix unconditional give-up, ignoring blockedThisRound.
if (candidates.length === 0) return null;
```

(replacing the `if (node.isRoot) return null; ... node.isBlocked = true; blockedThisRound.push(node); path = [root]; node = root; continue;` block.)

**Result:** `npx vitest run src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` reported **2 failed, 2 passed** (4 total):

- FAILED: `mctsSearch — D-08 round fill > every non-tail round dispatches exactly one-candidate (92%) expansions...`
- FAILED: `mctsSearch — D-08 round fill > every non-tail round dispatches exactly two-candidate (55%/37%) expansions...`
- passed (unaffected by this mutation, as expected): the concurrency=2 determinism test and the single-chain termination test — neither exercises the block-and-restart branch, since the determinism test only needs internal consistency between two runs of the SAME code, and the single-chain fixture never produces a non-root dead end with sibling subtrees still pending (there are no siblings).

The failures reproduce the same round-collapse shape recorded in the RED Evidence section above (the mutation restores byte-for-byte the pre-fix logic). The fix was then restored (verified via `diff` against the pre-mutation file — zero difference) and reconfirmed green: `npx vitest run src/lib/engine/__tests__/mctsSearch.roundFill.test.ts src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/fallbackExpectimax.test.ts` — 55/55 passed. The mutated state was never staged or committed.

## Files Created/Modified

- `frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` (new) — permanent D-08 round-fill regression suite: one-candidate/two-candidate round-fill invariant, concurrency=2 determinism under jitter, single-chain fully-blocked termination.
- `frontend/src/lib/engine/mctsSearch.ts` — `EngineNode.isBlocked` field + doc comment; `selectPath` block-and-restart logic + updated docblock; round loop's `blockedThisRound` declaration, threading, and post-fill-loop clear; fill-loop termination comment; module header pending-marker paragraph update.

## Decisions Made

- Named the block flag `isBlocked` and the round-owned list `blockedThisRound`, matching 225-RESEARCH.md's Pattern 1 naming exactly (Claude's discretion per CONTEXT.md D-07).
- Cleared block flags immediately after the fill loop (before `Promise.all`) rather than after — behaviorally identical since only `selectPath` reads the flag and it runs only inside the fill loop, and this placement also covers the nothing-dispatched break with no extra code.
- Kept the round-fill regression fixture's root policy flat (uniform) to isolate the peaked shape to non-root nodes, matching the exact fixture 225-RESEARCH.md's probe already verified; added a separate `makeFullyPeakedPolicy` helper (peaks the root too) solely for the single-chain termination test, since that case needs genuine single-branch structure starting at the root.

## Deviations from Plan

None — plan executed exactly as written. The Task 2 module-header update, mutation check, and full gate run all matched the plan's `<action>` and `<verify>` blocks; no Rule 1-4 deviations were needed.

## Issues Encountered

None. The fix landed cleanly against the documented pattern (225-RESEARCH.md Pattern 1) with no unexpected nesting-depth or type issues; `eslint`, `tsc -b`, the full vitest suite (4418 tests), and `knip` all passed on the first attempt after the fix.

## Verification Run Log (Task 2 full gate)

- `npx vitest run src/lib/engine/__tests__/mctsSearch.roundFill.test.ts src/lib/engine/__tests__/mctsSearch.test.ts -t "D-08|ENGINE-07"` — 6 passed, 29 skipped (the `-t` filter scopes to matching test names only).
- `npm run lint` — clean (0 errors, 0 warnings), including `max-depth`.
- `npm run build` (`tsc -b` + vite) — succeeded, no type errors.
- `npm test -- --run` — 276 test files, 4418 tests, all passed.
- `npm run knip` — clean (one pre-existing config hint about `.css`, unrelated).
- `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-dispatch-stop-rule.mjs --self-test` — `ALL CHECKS PASSED`, exit 0 (proves the Node harness can still type-strip the modified engine file).

## Content Assertion (accept-rule.md §1, arm A2)

`git diff --name-only <A0 SHA> HEAD -- frontend/src scripts bin` returns exactly:
```
frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts
frontend/src/lib/engine/mctsSearch.ts
```
matching the accept rule's "A0 to A2 engine diff is limited to `mctsSearch.ts` and `__tests__/mctsSearch.roundFill.test.ts`" requirement exactly. All three `(225-04)` commits (`d428a0194`, `82b910bb2`, `a9d5113ef`) touch only these two files.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Arm A2 (`a9d5113efed9270d02692c9b97e87508ecc414b2`) is ready for the Phase 225 measurement gate's throughput (T-50/T-400), move-quality (MQ-2), and stop-rule (A2 report-only) runs against A0.
- Plan 225-05 (item 1, root comparability guard) can now branch from this commit as its own base for building arm A21.
- No blockers. The round-fill fix is structurally scoped to `mctsSearch.ts` selection logic only — `stopRuleSatisfied`, `rootChildValueExtremes`, and `findability.ts` are untouched, so items 1 and 3 remain fully independent of this change.

---
*Phase: 225-engine-search-fixes-root-comparability-round-underfill-findability*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts
- FOUND: frontend/src/lib/engine/mctsSearch.ts
- FOUND: .planning/phases/225-engine-search-fixes-root-comparability-round-underfill-findability/225-04-SUMMARY.md
- FOUND commit: d428a0194 (test)
- FOUND commit: 82b910bb2 (fix)
- FOUND commit: a9d5113ef (test, A2)
