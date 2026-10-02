---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 09
subsystem: engine
tags: [mcts, selectPath, root-guard, cherry-pick, mutation-test, arm-A2, arm-A21]

requires:
  - phase: 226-08
    provides: "design-inputs.md D-13 classification (cBFTV = side effect, pending ratification), frozen verdict-twin constants, accept-rule.md (arm A0)"
provides:
  - "Arm A2 (frontend/src/lib/engine/mctsSearch.ts block-and-restart selectPath + mctsSearch.roundFill.test.ts) — SEED-170 item 2 re-landed, no additional D-13 code fix"
  - "Arm A21 (botBudget.ts ROOT_GUARD_BOOST_ALLOWANCE=0.04 field, types.ts BotStopRule.rootGuardBoostAllowance, mctsSearch.ts boost-aware clear-winner guard, test coverage) — SEED-170 item 1 re-landed on top of A2"
affects: [226-10, 226-11, 226-12]

actuals:
  tokens: 11643
  tasks: 2
  commits: 2
  plan_head_before: 472d547807fac7ac2e08bc6741a8ce9638284df1
  plan_head_after: 29f543f2730621f8567923c83c113e62f4f13519

tech-stack:
  added: []
  patterns:
    - "Stacked-arm re-land via git cherry-pick --no-commit across multiple upstream commits, squashed into one arm commit whose subject carries the accept rule's fixed-string marker"
    - "Mutation check performed on the WORKING TREE only (edit -> run failing test -> restore -> run green -> confirm byte-identical to pre-mutation state via diff) — never committed"

key-files:
  created:
    - frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts
  modified:
    - frontend/src/lib/engine/mctsSearch.ts
    - frontend/src/lib/engine/types.ts
    - frontend/src/lib/engine/botBudget.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
    - frontend/src/hooks/useFlawChessEngine.test.tsx

key-decisions:
  - "D-13 (cBFTV) treated as already-resolved per 226-08-SUMMARY.md's pending-ratification override: arm A2 carries no additional code fix beyond the three cherry-picked Phase 225 commits, per accept-rule.md's own A2 definition and this plan's orchestrator notes"
  - "Both cherry-picks (A2: 3 commits; A21: 2 commits) applied with --no-commit and squashed into ONE commit per arm, matching the plan's explicit <action> instruction (a single arm commit carrying the fixed-string marker), not a fresh multi-commit TDD cycle"
  - "Did not add a literal ROOT_GUARD_BOOST_ALLOWANCE constant to botBudget.ts to satisfy Task 2's acceptance-criteria grep check — see Owner review required below"

requirements-completed: []

coverage:
  - id: D1
    description: "Arm A2 lands block-and-restart selectPath (isBlocked/blockedThisRound) plus the permanent round-fill test, mutation-checked"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts (4 tests, all pass)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts (32 tests, all pass, pre-A21)"
        status: pass
      - kind: other
        ref: "scripts/engine-search-trace.mjs --ids cBFTV --label a2 (real 50-node search, anomaly-free)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Arm A21 lands the boost-aware clear-winner guard on top of A2, mutation-checked, type-checks and lints"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts (32 tests) + mctsSearch.roundFill.test.ts (4) + useFlawChessEngine.test.tsx (4) = 40 tests, all pass"
        status: pass
      - kind: other
        ref: "npm run build (tsc -b + vite) and npm run lint (eslint)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both arm commits carry the accept rule's fixed-string markers and stay inside the allowed file lists"
    verification:
      - kind: other
        ref: "git log -F --grep='(arm A2)'/'(arm A21)' resolution + git diff --name-only allowed-file checks (both plan <verify> automated commands)"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-29
status: complete
---

# Phase 226 Plan 09: Underfill Fix & Root Guard Re-Land (Arms A2, A21) Summary

**Cherry-picked the three Phase 225 round-underfill commits (arm A2) and the two root-comparability-guard commits (arm A21) verbatim onto Phase 226, each mutation-proven, with no conflicts and no additional D-13 code fix.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-09-29T00:36:00Z (approx, session start)
- **Completed:** 2026-09-29T01:21:00Z
- **Tasks:** 2
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- **Arm A2** (`fix(226-09): re-land round underfill fix (arm A2)`, commit `756d2a4a1`): cherry-picked
  `d428a0194`/`82b910bb2`/`a9d5113ef` with `git cherry-pick --no-commit`, zero conflicts. Diff limited
  to exactly `mctsSearch.ts` + `mctsSearch.roundFill.test.ts` (verified against A0 via
  `git diff --name-only`). D-13 carries no additional fix per the 226-08-classified "side effect"
  ruling. Mutation check: reverted the fixed empty-candidate branch to the pre-fix unconditional
  `return null`, confirmed both round-fill tests fail, restored, confirmed 35/35 green. Ran the real
  trace harness on `cBFTV` (50 nodes, concurrency 4): `TRACE id=cBFTV label=a2 rounds=14
  round_sizes=1,4,4,4,4,4,4,4,4,4,4,4,4,1 pick=e2g4`, zero `TRACE-ANOMALY` lines.
- **Arm A21** (`feat(226-09): re-land root comparability guard (arm A21)`, commit `29f543f27`):
  cherry-picked `4a13b2f3a`/`27beff12f` with `git cherry-pick --no-commit`; git auto-merged the
  `mctsSearch.test.ts` hunks cleanly (no manual conflict resolution needed). Diff limited to exactly
  the five allowed files vs A2. Two mutation checks performed and reverted: (a) dropping the
  `|| child.isClosed` settled clause made the closed-top guard test fail (`expected 20 to be 1`);
  (b) dropping the `&& !hasUnsettledInWindow` conjunct made the clear-winner guard test fail
  (`expected 1 to be 3`, reverting to the pre-225 bug). Both restored, 40/40 targeted tests green.
  `npm run build` (tsc -b + vite) and `npm run lint` both clean after the `types.ts` change.

## Task Commits

Each task was committed atomically:

1. **Task 1: Re-land arm A2 and prove it end to end on cBFTV** - `756d2a4a1` (fix)
2. **Task 2: Re-land arm A21 (root comparability guard) with its mutation checks** - `29f543f27` (feat)

**Plan metadata:** (this commit, to follow)

## Files Created/Modified

- `frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` - permanent round-fill regression test (one-candidate 92%, two-candidate 55%/37%, concurrency=2 determinism, fully-blocked termination)
- `frontend/src/lib/engine/mctsSearch.ts` - `isBlocked`/`blockedThisRound` block-and-restart `selectPath` (A2); boost-aware `hasUnsettledInWindow` guard on the clear-winner stop, `settled = visits >= 1 || isClosed` (A21)
- `frontend/src/lib/engine/types.ts` - `BotStopRule.rootGuardBoostAllowance: number` (required field)
- `frontend/src/lib/engine/botBudget.ts` - `FLAWCHESS_BOT_STOP_RULE.rootGuardBoostAllowance = 0.04`
- `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` - closed-top guard test, clear-winner guard test, flatness residual assertion
- `frontend/src/hooks/useFlawChessEngine.test.tsx` - well-formedness assertion (`rootGuardBoostAllowance` finite and >= 0)

## Decisions Made

- Both arms squashed each multi-commit Phase 225 cherry-pick sequence into a single arm commit, per
  this plan's explicit `<action>` text ("Commit with subject `fix(226-09): ...(arm A2)`" / "Commit with
  subject `feat(226-09): ...(arm A21)`" — singular), not a fresh RED-GREEN-REFACTOR TDD sequence. This
  is a re-land of already-tested code, not new development; `workflow.tdd_mode` is unset in
  `.planning/config.json`, so the TDD gate-enforcement mechanics (separate `test(...)`/`feat(...)`
  commits) do not apply here regardless.
- D-13 treated as resolved without additional code per 226-08-SUMMARY.md's classification (cBFTV =
  side effect) and this plan's orchestrator notes explicitly confirming arm A2 = exactly the three
  Phase 225 cherry-picks.

## Deviations from Plan

None - plan executed exactly as written for both tasks' `<action>` and `<verify>` blocks. One
acceptance-criterion mismatch was found and is NOT treated as a deviation requiring a code fix — see
"Owner review required" below, since fixing it would mean adding code not present in the unchanged
Phase 225 re-land the plan explicitly calls for.

## Issues Encountered

None.

## Owner review required

Per the orchestrator's autonomy instructions, the one genuine judgment call in this plan:

1. **Task 2's acceptance criterion `grep -n "ROOT_GUARD_BOOST_ALLOWANCE" frontend/src/lib/engine/botBudget.ts` does not match the actual (correctly re-landed) code, and I did not add code to force it to match.**
   The real Phase 225 commit `4a13b2f3a` implements the allowance as a lowercase field
   `rootGuardBoostAllowance: 0.04` inside the `FLAWCHESS_BOT_STOP_RULE` object literal in
   `botBudget.ts` — there is no standalone `ROOT_GUARD_BOOST_ALLOWANCE` constant, and there never was.
   This exact discrepancy was already found and explicitly marked "expected" in
   `.planning/phases/225-.../225-REVIEW.md` ("`ROOT_GUARD_BOOST_ALLOWANCE` appear**s** nowhere under
   `frontend/src`... only as historical-context prose"). The design docs (225-CONTEXT.md D-02,
   226-CONTEXT.md, this plan's own frontmatter and Task 2 body) all describe it as "a named constant,"
   but the shipped implementation never matched that description, and Phase 225's own review accepted
   the field-based implementation as-is.
   I re-landed the commits verbatim (per this plan's own instruction: "guard design unchanged from
   Phase 225 D-01/D-02" and "Do NOT touch any file outside the accept rule's allowed lists") rather
   than adding a new, redundant `ROOT_GUARD_BOOST_ALLOWANCE` constant purely to satisfy a literal grep
   check that was never true of the actual code. Adding one now would be an unplanned code change
   (CLAUDE.md: "Do not add unplanned features, refactors, or improvements outside the current phase
   scope... flag it rather than implementing it"), and would diverge arm A21's engine content from
   arm A21 as defined by `accept-rule.md` (which itself only asserts the VALUE `0.04`, never the
   symbol name — see `accept-rule.md` §1's A21 row and §2's constants table, neither of which lists
   `ROOT_GUARD_BOOST_ALLOWANCE` as a code-level identifier to be grepped).
   **The value 0.04 IS present and verified** (`grep -n "rootGuardBoostAllowance" frontend/src/lib/engine/botBudget.ts` -> `rootGuardBoostAllowance: 0.04,`), and both mutation checks confirm the guard is functionally live. Only the literal SCREAMING_SNAKE_CASE symbol name from the plan's acceptance criterion is absent, matching Phase 225's actual, already-reviewed shipped code.
   **If the owner wants the literal constant to exist**, that is a small, separate, deliberate code
   change (extract `ROOT_GUARD_BOOST_ALLOWANCE = 0.04` as an exported constant and reference it from
   the object literal) that should be scoped as its own task rather than smuggled into this re-land.

## Next Phase Readiness

- Arms A2 and A21 are both live on this branch, mutation-proven, content-boundary-verified against
  `accept-rule.md` §1.
- Plan 226-10/226-11 can proceed to define arm A21S (root grade split) on top of A21, per
  `accept-rule.md`'s stacked-arm chain.
- No gate measurement (throughput, calibration, move quality) was run in this plan — out of scope per
  the plan's own task list (measurement happens in later plans per `accept-rule.md` §3).

## Self-Check: PASSED

- `frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` confirmed present on disk with `[ -f ]`.
- Commits `756d2a4a1` and `29f543f27` confirmed in `git log --oneline --all`.
- `git log -F --grep='(arm A2)' --format=%s -1` -> `fix(226-09): re-land round underfill fix (arm A2)`.
- `git log -F --grep='(arm A21)' --format=%s -1` -> `feat(226-09): re-land root comparability guard (arm A21)`.
- Allowed-file diff checks re-verified: A0->A2 diff = exactly `mctsSearch.ts` +
  `mctsSearch.roundFill.test.ts`; A2->A21 diff = exactly `mctsSearch.ts`, `types.ts`, `botBudget.ts`,
  `mctsSearch.test.ts`, `useFlawChessEngine.test.tsx`.
- Both mutation checks (arm A2's `return null` revert; arm A21's `isClosed` and
  `hasUnsettledInWindow` reverts) re-confirmed to fail their target tests and restore to green,
  with the restored file byte-identical (`diff` exit 0) to the pre-mutation state.
- `npx vitest run` on all touched test files: 40/40 passed at HEAD. `npm run build` and `npm run lint`
  clean at HEAD.

---
*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Completed: 2026-09-29*
