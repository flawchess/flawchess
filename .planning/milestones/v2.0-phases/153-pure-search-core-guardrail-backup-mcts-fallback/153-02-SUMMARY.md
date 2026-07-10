---
phase: 153-pure-search-core-guardrail-backup-mcts-fallback
plan: 02
subsystem: engine
tags: [typescript, engine-core, mcts, expectimax, vitest]

# Dependency graph
requires:
  - "frozen types.ts/guardrail.ts contract (153-01)"
provides:
  - "backupExpectation()/backupRootMax() — the Maia-prior-weighted expectation (non-root) + max (root) backup rule"
  - "BackupChild interface with prior structurally independent of value/visits"
affects: [153-03-select, 153-04-mctsSearch, 153-05-fallbackExpectimax]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "backup.ts follows moveQuality.ts's 'small interface directly above the pure function that consumes it' convention, zero I/O, zero try/catch"
    - "BackupChild.prior is always populated from a fresh policy() call, never re-derived from value/visits — closes Pitfall 1 structurally, not just by convention"

key-files:
  created:
    - frontend/src/lib/engine/backup.ts
    - frontend/src/lib/engine/__tests__/backup.test.ts
  modified: []

key-decisions:
  - "backupExpectation degenerate guard also covers the empty-array case (totalPrior===0 reduces to 0 for []), returning 0.5 rather than NaN — not explicitly required by the plan's acceptance criteria but a natural consequence of the same guard, tested explicitly."

patterns-established:
  - "Pattern: BackupChild interface makes visit-count leakage code-review-visible — no visits/n field or term appears anywhere in backup.ts, verified by direct file read during Task 1."

requirements-completed: [ENGINE-03]

coverage:
  - id: SC2
    description: "Non-root backup is the Maia-prior-weighted expectation over the FULL truncated top-k set (mixing expanded+unexpanded children), provably distinct from a naive average and from a visit-count-weighted average"
    requirement: "ENGINE-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/backup.test.ts (6 tests, all pass)"
        status: pass
    human_judgment: false
  - id: D1-root-branch
    description: "Root backup is a plain max over candidate values, distinct from backupExpectation over the same children"
    requirement: "ENGINE-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/backup.test.ts ('differs from backupExpectation over the same children' test)"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-07-05
status: complete
---

# Phase 153 Plan 02: Backup Rule — Expectation + Root-Max Summary

**`backup.ts` — the single genuinely novel file in the v2.0 milestone: a Maia-prior-weighted expectation over the full truncated top-k set for non-root nodes, and a plain max for the root, proven against a hand-computed 0.637 fixture and two negative-assertion baselines that make the "silently degenerates into textbook MCTS" bug structurally testable.**

## Performance

- **Duration:** 8 min
- **Tasks:** 2
- **Files modified:** 2 (both new)

## Accomplishments

- `frontend/src/lib/engine/backup.ts` exports `BackupChild` (fields `prior`, `value` only — no `visits`/`n` term anywhere in the file), `backupExpectation()` (prior-weighted mean over the full set, renormalizing when priors don't sum to 1, returning `0.5` as a degenerate guard when `totalPrior === 0`), and `backupRootMax()` (plain `Math.max` over child values — the tree's single max node, D-01).
- `frontend/src/lib/engine/__tests__/backup.test.ts` encodes the SC2 primary fixture from 153-RESEARCH.md exactly: three children (one expanded, prior 0.6/value 0.72; two unexpanded, prior 0.3/value 0.55 and prior 0.1/value 0.40) yielding `backupExpectation ≈ 0.637`, plus both negative assertions (≠ naive average 0.5567, ≠ visit-weighted collapse 0.72), a renormalization case, a `totalPrior === 0` degenerate-guard case, and a root-vs-non-root case proving `backupRootMax` (0.66) differs from `backupExpectation` over the identical children.
- Both `npx tsc -b` (zero errors) and `npx vitest run src/lib/engine/__tests__/backup.test.ts` (6/6 pass) verify clean per the plan's `<verify>` block.

## Task Commits

Each task was committed atomically:

1. **Task 1: backup.ts — expectation + root-max pure functions (ENGINE-03, D-01/D-02)** - `98e30df4` (feat)
2. **Task 2: backup.test.ts — SC2 worked fixture + negative assertions (ENGINE-03)** - `8243dda4` (test)

_Note: Task 1 is `tdd="true"` per PLAN.md, but per the plan's own `<behavior>`/`<action>` split the test file is Task 2's separate deliverable (not a RED-then-GREEN pair inside Task 1) — both tasks were executed and verified independently per their own `<verify>` blocks, matching the plan's structure exactly._

## Files Created/Modified

- `frontend/src/lib/engine/backup.ts` - `BackupChild` interface + `backupExpectation()`/`backupRootMax()` pure functions
- `frontend/src/lib/engine/__tests__/backup.test.ts` - SC2 worked fixture, negative assertions, renormalization/degenerate-guard cases, root-vs-non-root branch proof

## Decisions Made

- Added an explicit empty-array test case (`backupExpectation([])` returns `0.5`) alongside the plan-specified `totalPrior === 0` case — both reduce to the same guard path (`totalPrior` sums to `0` either way), and testing both makes the guard's coverage complete without adding a second code path.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' acceptance criteria are met verbatim: `BackupChild` has exactly the two specified fields, no `visits`/`n` term appears anywhere in `backup.ts` (confirmed by direct read during Task 1), `backupExpectation` renormalizes and guards `totalPrior === 0` with `0.5`, `backupRootMax` uses `Math.max`, and the test file's primary fixture mixes one expanded + two unexpanded children in a single case per D-02's explicit requirement.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `backupExpectation`/`backupRootMax` are ready for `mctsSearch.ts` (153-04) and `fallbackExpectimax.ts` (153-05) to import directly — the literal reuse mechanism SC5 requires (both runners call the SAME `backup.ts`, never reimplementing their own combination logic).
- The `BackupChild` interface is the contract `select.ts` (153-03) and `mctsSearch.ts` (153-04) must populate at each expansion: `prior` from a fresh `policy()` call's truncated/renormalized output, `value` from either a child's own `backupExpectation`/`backupRootMax` result or `leafExpectedScore()` (153-01, already shipped).
- No blockers. `backup.ts` has zero dependencies beyond plain arrays/`Math` — nothing in 153-03/04/05 can be blocked waiting on this file's own dependencies resolving.

---
*Phase: 153-pure-search-core-guardrail-backup-mcts-fallback*
*Completed: 2026-07-05*

## Self-Check: PASSED
