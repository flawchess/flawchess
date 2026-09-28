---
phase: 225-engine-search-fixes-root-comparability-round-underfill-findability
plan: 05
subsystem: engine
tags: [mcts, search, typescript, vitest, stopRule, botBudget]

requires:
  - phase: 225-engine-search-fixes-root-comparability-round-underfill-findability (plan 225-04)
    provides: A2 arm (round-underfill fix) this plan's A21 arm is measured against
provides:
  - "Boost-aware visit guard on the bot's clear-winner early stop (SEED-170 item 1, D-01/D-02 amended): the clear-winner branch of stopRuleSatisfied now fires only when every root child within marginThreshold + rootGuardBoostAllowance of the top has been visited or closed"
  - "Required BotStopRule.rootGuardBoostAllowance field, set in FLAWCHESS_BOT_STOP_RULE to the measured D-02 allowance (0.04)"
  - "Rewritten clear-winner stop-rule test proving the guard delays the stop for an in-window unvisited child and never blocks on an out-of-window one"
  - "Closed-top guard test proving a terminal (mate-in-1) root child counts as settled at zero visits (RESEARCH Pitfall 1)"
  - "Explicit D-03 flatness-residual assertion and well-formedness check for the new allowance field"
  - "Arm A21 for the Phase 225 measurement gate: commit 27beff12fb22d009b1f30c2b5552ba9cba4aad0e"
affects: [225-06, 225-07, 225-08, engine-search-fixes-225 measurement gate]

actuals:
  tokens: 5992
  tasks: 2
  commits: 2
  plan_head_before: 1eb15cf9ba900a6df1e179507cc22fa53304dec6
  plan_head_after: 27beff12fb22d009b1f30c2b5552ba9cba4aad0e

tech-stack:
  added: []
  patterns:
    - "Guard computed inside rootChildValueExtremes's existing single collection pass (settled per entry, hasUnsettledInWindow on the result) — never a second pass with different semantics"
    - "Allowance lives on the BotStopRule object itself (required field), not a free-floating constant, so any literal omitting it is a tsc -b error — the same structural-desync-impossible argument botBudget.ts's header already makes for the shared constant"

key-files:
  created: []
  modified:
    - frontend/src/lib/engine/types.ts
    - frontend/src/lib/engine/botBudget.ts
    - frontend/src/lib/engine/mctsSearch.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
    - frontend/src/hooks/useFlawChessEngine.test.tsx

key-decisions:
  - "Test-local GUARD_TEST_ALLOWANCE = 0.1 (wider than the production 0.04) keeps the guard-window arithmetic in the fixtures easy to verify by hand; the production value (0.04, measured D-02) lives only in botBudget.ts"
  - "The rewritten clear-winner fixture grades every reply at a root child's own position with that child's own evalCp, so a root child's first expansion leaves its own .value unchanged — isolating the guard's visit-based settlement logic from any actual value drift the real opponent-error boost would cause"
  - "nodesEvaluated=3 for the rewritten clear-winner test was hand-derived from select.ts's PUCT formula (root re-selects e2e4 for its own first expansion at node 2, then e2e3 wins the PUCT comparison at node 3) and confirmed by running the test — recorded as a derivation comment, per the plan's explicit allowance to pin an observed value"

requirements-completed: []

coverage:
  - id: D1
    description: "BotStopRule.rootGuardBoostAllowance is a required field; FLAWCHESS_BOT_STOP_RULE sets it to the measured D-02 allowance (0.04)"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/useFlawChessEngine.test.tsx#useFlawChessEngine — bot-play budget profile (D-07/D-09) > FLAWCHESS_BOT_STOP_RULE is well-formed: minNodes within the bot budget, positive stabilityWindow"
        status: pass
      - kind: other
        ref: "npm run build (tsc -b) — a BotStopRule literal missing the field is a compile error; full frontend build green"
        status: pass
    human_judgment: false
  - id: D2
    description: "stopRuleSatisfied's clear-winner branch is gated on hasUnsettledInWindow (settled = visits >= 1 || isClosed); the flatness branch and deadlineSearch.ts stay unguarded"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — Phase 168.5 D-05/D-06 (guarded Phase 225 D-01/D-02) bot-play stop rule > clear-winner guard: an in-window unvisited runner-up (e2e3) delays the stop until settled, while an out-of-window unvisited child (e1d2) never blocks it"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — Phase 168.5 D-05/D-06 (guarded Phase 225 D-01/D-02) bot-play stop rule > closed-top guard: a terminal (mate-in-1) top root child counts as settled at zero visits, so the search still early-stops at node 1"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — Phase 168.5 D-05/D-06 (guarded Phase 225 D-01/D-02) bot-play stop rule > near-tie-flatness: closely-bunched root moves stop the search even with no clear winner"
        status: pass
    human_judgment: false
  - id: D3
    description: "The guard fix is mutation-proven: reverting either the isClosed clause in settled or the guard conjunct in the clear-winner disjunct makes the corresponding new/rewritten test fail"
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

# Phase 225 Plan 05: Root Comparability Guard on the Bot's Clear-Winner Stop Summary

**The bot's clear-winner early stop now withholds until every root child within `marginThreshold + rootGuardBoostAllowance` (measured 0.04) of the top has been visited or closed — fixing SEED-170 item 1's comparison of a boosted, already-visited top child against an unboosted, never-visited runner-up.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-27T07:57:00Z (approx)
- **Completed:** 2026-09-27T08:12:25Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Fixed SEED-170 item 1 (root comparability before the early stop, bot play only): `stopRuleSatisfied`'s clear-winner branch previously compared root children's `.value`s the instant the margin was met, even when every child — including the top itself — was still unvisited. A root child's first expansion can raise its value by roughly the opponent's expected error (the "boost"), so an unvisited runner-up within reach of the top could still overtake it before the stop fired.
- Added the required `BotStopRule.rootGuardBoostAllowance` field (`types.ts`) and set `FLAWCHESS_BOT_STOP_RULE.rootGuardBoostAllowance = 0.04` (`botBudget.ts`) — the D-02 measured pooled-p90 allowance from `reports/engine-search-fixes-225/d02-allowance.md` (guard window `W = marginThreshold 0.05 + 0.04 = 0.09` in production).
- Extended `rootChildValueExtremes` in its existing single collection pass: each entry now carries `settled: child.visits >= 1 || child.isClosed` (never `isTerminal` alone — a closed root child, e.g. a mate-in-1 top move, is filtered out of selection and can never be visited, so a visits-only test would stall the stop forever). The function's result gains `hasUnsettledInWindow`, computed once the top is known.
- `stopRuleSatisfied` now computes `guardWindow = rule.marginThreshold + rule.rootGuardBoostAllowance` and gates ONLY the clear-winner disjunct on `!hasUnsettledInWindow`; the stability-state update stays unconditional, and the near-tie-flatness disjunct is completely untouched (D-03), as is `deadlineSearch.ts`'s wall-clock cut (D-04).
- Rewrote the pre-225 "clear-winner ... stops at node 1" test as an intended behavior change (RESEARCH Pitfall 2, not a loosened assertion): the new fixture grades every reply at a root child's own position with that child's own `evalCp` (isolating the guard's visit-based settlement from any actual value drift), asserts the exact stop node (`nodesEvaluated` 3, hand-derived from `select.ts`'s PUCT formula and confirmed by running the test), that `e2e4`/`e2e3` end up visited while the out-of-window `e1d2` stays at 0, and a stream property that every pre-stop snapshot with the margin already met still has an in-window unvisited line (the guard, not the margin, delayed the stop).
- Added a new "closed-top guard" test (RESEARCH Pitfall 1): a mate-in-1 `MATE_IN_1_FEN` root with the mating move as top candidate stops at `nodesEvaluated` 1 even though that top child is never visited — it counts as settled via `isClosed`.
- Extended the existing near-tie-flatness test with an explicit D-03 residual assertion: every root child is still at 0 visits when the flatness branch stops the search, documenting (not fixing) that this branch is deliberately left unguarded.
- Added a well-formedness assertion in `useFlawChessEngine.test.tsx` that `FLAWCHESS_BOT_STOP_RULE.rootGuardBoostAllowance` is finite and `>= 0`.
- Performed and recorded both required mutation checks (see below): reverting either half of the fix makes its corresponding test fail; both reverted before any commit.
- Confirmed `deadlineSearch.ts` untouched, and that the `(225-04) -> (225-05)` engine diff is limited to exactly the five files this plan declared in `files_modified` (content assertion, `accept-rule.md` §1).

## Task Commits

1. **Task 1 (guard implementation + rewritten clear-winner test, TDD RED->GREEN)** — `4a13b2f3a` (feat)
2. **Task 2 (closed-top test, flatness residual, well-formedness, mutation checks)** — `27beff12f` (test)

**A21 (Phase 225 measurement gate arm, `reports/engine-search-fixes-225/accept-rule.md`):** `27beff12fb22d009b1f30c2b5552ba9cba4aad0e` — the last commit with the `(225-05)` scope touching `frontend/src`.

_Note: Task 1 carried `tdd="true"`. The rewritten clear-winner test was written first against the guard-free (A2) engine and observed failing there (`nodesEvaluated` stuck at 1, the pre-fix bug — see "RED Evidence" below), then the guard implementation was added in the same commit to reach GREEN, per the plan's explicit TDD-inside-a-single-task instruction (write test before the engine change, confirm it fails on the unguarded engine, then implement)._

## RED Evidence (pre-guard engine, Task 1)

Before implementing the guard, the rewritten clear-winner test was run against the then-unmodified (A2) `stopRuleSatisfied` (guard code absent, `rootGuardBoostAllowance` field not yet on `BotStopRule`). It failed exactly as the RESEARCH C-1 analysis predicted: `nodesEvaluated` was `1` (the pre-225 behavior — the margin between `e2e4` and `e2e3` already exceeds `marginThreshold` at the root's own first expansion, before any child is visited), not the expected `3`. This confirmed the fixture reproduces SEED-170 item 1 on the pre-fix engine. The guard (rootChildValueExtremes/stopRuleSatisfied changes) was then added and the test went green with `nodesEvaluated` observed at `3`.

## Mutation Check (RESEARCH Pitfall 1/2, project mutation-test rule)

Both mutations were applied to a working copy, run, and reverted — restored file confirmed byte-identical via `diff` before any commit; the mutated state was never staged.

**(a) Dropped the `|| child.isClosed` clause from `settled`:**
```ts
// MUTATION-TEST (temporary): settled without isClosed.
settled: child.visits >= 1 /* MUTATION-TEST: temporarily dropped isClosed */,
```
Result: `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts -t "closed-top guard"` — **1 failed**. `expected 20 to be 1` — the mate-in-1 top child, never visited and no longer counted as settled by the mutated test, blocked the clear-winner stop for the entire 20-node budget (RESEARCH Pitfall 1 reproduced exactly).

**(b) Dropped the `&& !hasUnsettledInWindow` guard conjunct from the clear-winner disjunct:**
```ts
// MUTATION-TEST (temporary): clear-winner disjunct without the guard.
(extremes.topValue - extremes.runnerUpValue >= rule.marginThreshold /* MUTATION-TEST: dropped guard conjunct */) ||
```
Result: `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts -t "clear-winner guard"` — **1 failed**. `expected 1 to be 3` — the search reverted to stopping at `nodesEvaluated` 1, byte-for-byte the pre-225 bug the rewritten test exists to catch.

Both mutations were reverted (confirmed identical to the pre-mutation file via `diff`) and the full suite reconfirmed green: `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/hooks/useFlawChessEngine.test.tsx` — 36/36 passed.

## Files Created/Modified

- `frontend/src/lib/engine/types.ts` — required `BotStopRule.rootGuardBoostAllowance: number` field with a Phase 225 D-01/D-02 doc comment.
- `frontend/src/lib/engine/botBudget.ts` — `FLAWCHESS_BOT_STOP_RULE.rootGuardBoostAllowance = 0.04` with a method comment; module-header Phase 225 paragraph on the guard and the deliberately-unguarded flatness/deadline branches (D-03/D-04).
- `frontend/src/lib/engine/mctsSearch.ts` — `rootChildValueExtremes(root, guardWindow)` now takes the guard window and returns `hasUnsettledInWindow`; `stopRuleSatisfied` computes the window and gates only the clear-winner disjunct on it; both docblocks rewritten to explain the settled/window semantics.
- `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` — new `GUARD_TEST_ALLOWANCE` constant and `buildChildOwnGradeFixture` helper; rewrote the clear-winner test; added the closed-top guard test; extended the flatness test with a D-03 residual assertion; added `rootGuardBoostAllowance` to all four `BotStopRule` test literals.
- `frontend/src/hooks/useFlawChessEngine.test.tsx` — added a finite/`>= 0` well-formedness assertion for `rootGuardBoostAllowance`.

## Decisions Made

- `GUARD_TEST_ALLOWANCE = 0.1` (test-local, wider than production's 0.04) keeps the fixtures' guard-window arithmetic easy to verify by hand; documented in-code as deliberately distinct from the measured production value.
- `nodesEvaluated = 3` for the rewritten clear-winner test was derived analytically from `select.ts`'s PUCT formula (root re-selects `e2e4` for its own first expansion at node 2 since its Q-term still dominates at N=1; `e2e3` then wins the PUCT comparison at node 3 as `e2e4`'s exploration term shrinks with visits) and confirmed by running the test — recorded as a derivation comment per the plan's explicit instruction to pin an observed value if hand-derivation is needed.
- The "closed-top guard" test's ordinary candidate (`e1e2`, 0cp) intentionally sits far outside the guard window (gap ~0.5 vs window 0.15) so the test isolates the `isClosed`-as-settled property without also depending on in-window blocking behavior (already covered by the clear-winner test).

## Deviations from Plan

None — plan executed exactly as written. One informational note: the plan's literal acceptance-criteria command `awk '/^function rootChildValueExtremes/,/^}/' frontend/src/lib/engine/mctsSearch.ts | grep -c "isClosed"` returns `0`, not `>= 1`, because the function's multi-line return-type annotation contains a line (`} | null {`) that itself matches `/^}/` and terminates the awk range early, before the function body (where `isClosed` actually appears) is reached. This is a limitation of the literal grep/awk pattern against this function's multi-line signature, not a gap in the implementation — manually extracting the full function body (`sed -n '238,272p'`) confirms `isClosed` appears exactly once, inside the single collection pass, as required.

## Issues Encountered

None. The guard implementation, rewritten fixture, and closed-top test all landed cleanly against the RESEARCH document's predictions (C-1's PUCT derivation, Pitfall 1's isClosed requirement, Pitfall 2's rewrite-not-loosen guidance); `eslint`, `tsc -b`, the full vitest suite (4419 tests, +1 over 225-04's 4418), and `knip` all passed on the first attempt after the fix.

## Verification Run Log (Task 2 full gate)

- `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/hooks/useFlawChessEngine.test.tsx` — 36 passed.
- `npm run lint` — clean (0 errors, 0 warnings), including `max-depth`.
- `npm run build` (`tsc -b` + vite) — succeeded, no type errors (confirms every `BotStopRule` literal in the codebase now carries the required field).
- `npm test -- --run` — 276 test files, 4419 tests, all passed.
- `npm run knip` — clean (one pre-existing config hint about `.css`, unrelated, same as 225-04).
- `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-dispatch-stop-rule.mjs --self-test` — `ALL CHECKS PASSED`, exit 0.
- `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs --self-test` — `ALL CHECKS PASSED`, exit 0.

## Content Assertion (accept-rule.md §1, arm A21)

`git diff --name-only <A2 SHA> HEAD -- frontend/src scripts bin` (A2 = `a9d5113efed9270d02692c9b97e87508ecc414b2`, the last `(225-04)` commit touching `frontend/src/lib/engine`) returns exactly:
```
frontend/src/hooks/useFlawChessEngine.test.tsx
frontend/src/lib/engine/__tests__/mctsSearch.test.ts
frontend/src/lib/engine/botBudget.ts
frontend/src/lib/engine/mctsSearch.ts
frontend/src/lib/engine/types.ts
```
matching the accept rule's "A2 to A21 engine diff is limited to `mctsSearch.ts`, `types.ts`, `botBudget.ts`, `__tests__/mctsSearch.test.ts`, and `frontend/src/hooks/useFlawChessEngine.test.tsx`" requirement exactly. `deadlineSearch.ts` is confirmed untouched (empty diff since `merge-base main HEAD`).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Arm A21 (`27beff12fb22d009b1f30c2b5552ba9cba4aad0e`) is ready for the Phase 225 measurement gate's stop-rule arm (A2 vs A21, S1/S2 criteria) and the move-quality/calibration arms that run against it.
- No blockers. The guard is structurally scoped to `stopRuleSatisfied`'s clear-winner branch only — the flatness branch, `deadlineSearch.ts`, and item 3 (findability, Plan 225-06) remain fully independent of this change.
- Plan 225-06 (item 3, findability fallback) can proceed against this commit as `A21`'s base.

---
*Phase: 225-engine-search-fixes-root-comparability-round-underfill-findability*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: frontend/src/lib/engine/types.ts
- FOUND: frontend/src/lib/engine/botBudget.ts
- FOUND: frontend/src/lib/engine/mctsSearch.ts
- FOUND: frontend/src/lib/engine/__tests__/mctsSearch.test.ts
- FOUND: frontend/src/hooks/useFlawChessEngine.test.tsx
- FOUND commit: 4a13b2f3a (feat)
- FOUND commit: 27beff12f (test, A21)
