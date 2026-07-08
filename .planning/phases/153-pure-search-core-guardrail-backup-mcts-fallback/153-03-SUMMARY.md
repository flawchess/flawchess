---
phase: 153-pure-search-core-guardrail-backup-mcts-fallback
plan: 03
subsystem: engine
tags: [typescript, engine-core, puct, mcts, vitest]

# Dependency graph
requires:
  - "frozen types.ts/guardrail.ts contract (153-01)"
  - "backupExpectation()/backupRootMax() (153-02, consumed conceptually — select.ts feeds their prior/value inputs, not imported directly)"
provides:
  - "truncateAndRenormalize() — Maia top-k mass-truncation + renormalization (ENGINE-02, D-11)"
  - "selectChild() — deterministic PUCT selection with root/non-root formula split + canonical UCI tie-break (D-01)"
  - "rootExplorationPriors() — root-only floor-boosted exploration prior (D-05)"
affects: [153-04-mctsSearch, 153-05-fallbackExpectimax]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "select.ts mirrors moveQuality.ts's selectCandidatesByMass mass-cut loop shape exactly, with an independent constant (POLICY_MASS_THRESHOLD=0.9 vs 0.95) and no hard cap (D-11)"
    - "truncateAndRenormalize (all nodes) and rootExplorationPriors (root-only) are two distinct exported functions layered in sequence, never conflated — the floor never reaches backup.ts's inputs (D-05)"
    - "selectChild takes an isRoot boolean and branches the exploration weight source (rootExplorationPrior vs plain prior) and whether the Q term is added at all (D-01)"

key-files:
  created:
    - frontend/src/lib/engine/select.ts
    - frontend/src/lib/engine/__tests__/select.test.ts
  modified: []

key-decisions:
  - "selectChild() throws on an empty children array (Rule 2 — precondition validation) rather than returning a sentinel/undefined, since there is no sensible default UCI to return; matches the plan's implicit assumption that a node being selected from always has children."
  - "Test fixture for the D-01 root/non-root split uses ONE shared children array (splitFixtureChildren) where plain prior favors one child and rootExplorationPrior ties both — proving root and non-root selection disagree on the SAME object, not just on differently-constructed fixtures."

patterns-established:
  - "Pattern: canonical tie-break implemented as an inline comparison inside the same reduce-style loop (score > best OR score === best AND uci < bestUci) rather than a separate sort+pick pass — avoids allocating an intermediate sorted array per selection call (called once per expansion in the eventual hot loop)."

requirements-completed: [ENGINE-02]

coverage:
  - id: truncation
    description: "truncateAndRenormalize cuts at ~90% cumulative mass, drops the tail, and renormalizes the kept set to sum to ~1.0; an already-concentrated policy keeps just one move at 1.0"
    requirement: "ENGINE-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/select.test.ts (describe('truncateAndRenormalize'), 3 tests)"
        status: pass
    human_judgment: false
  - id: puct-split
    description: "Root selection includes the Q term (Q difference decides the winner when exploration terms tie); non-root selection drops Q entirely, flipping the winner on the SAME children fixture"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/select.test.ts (describe('selectChild'), 2 tests using splitFixtureChildren)"
        status: pass
    human_judgment: false
  - id: tie-break
    description: "Canonical ascending UCI-string tie-break wins on equal scores, independent of iteration order"
    requirement: "ENGINE-07 (determinism, referenced by this plan's threat model)"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/select.test.ts ('breaks ties by canonical ascending UCI-string order')"
        status: pass
    human_judgment: false
  - id: floor-scope
    description: "rootExplorationPriors floor-boosts a near-zero-Maia candidate after renormalization; truncateAndRenormalize on the identical input does NOT floor-boost (it drops the candidate below the mass cut instead) — proving the floor is a separate, root-only transform"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/select.test.ts (describe('rootExplorationPriors'), 2 tests)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-05
status: complete
---

# Phase 153 Plan 03: Candidate Selection — Truncation + Deterministic PUCT Summary

**`select.ts` — Maia top-k mass-truncation/renormalization (independent 90% constant, no hard cap), deterministic root/non-root PUCT selection with canonical UCI tie-break, and a root-only floor-boosted exploration prior that never touches backup values — all as three distinct, independently unit-tested pure functions.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2
- **Files modified:** 2 (both new)

## Accomplishments

- `frontend/src/lib/engine/select.ts` exports `POLICY_MASS_THRESHOLD` (0.9, D-11, deliberately separate from `moveQuality.ts`'s 0.95), `C_PUCT` (1.4), `ROOT_PRIOR_FLOOR` (0.1), `truncateAndRenormalize()` (mass-cut + renormalize, mirroring `selectCandidatesByMass`'s loop shape with no hard cap), `rootExplorationPriors()` (root-only floor-boost + renormalization, D-05), and `selectChild()` (deterministic PUCT with the root/non-root formula split and canonical UCI tie-break, D-01).
- `frontend/src/lib/engine/__tests__/select.test.ts` (9 tests, all pass) proves: mass-cut truncation + renormalization on a 4-move policy; single-move-already-concentrated collapse; root PUCT selection where the Q term decides the winner; the SAME children fixture producing the OPPOSITE winner at a non-root node (Q dropped, plain prior decides) — the direct proof of the D-01 split; canonical UCI tie-break; empty-input guard; and the D-05 floor-scope isolation (floor boosts a near-zero candidate in `rootExplorationPriors`, while `truncateAndRenormalize` on the identical input drops that same candidate below the mass cut instead of boosting it).
- `npx tsc -b` reports zero errors for `select.ts`; `npx vitest run` is green (9/9).

## Task Commits

Each task was committed atomically:

1. **Task 1: select.ts — truncation, PUCT split, root floor-boost (ENGINE-02, D-01/D-05/D-11)** - `54493106` (feat)
2. **Task 2: select.test.ts — truncation, PUCT formula, tie-break, floor scope (ENGINE-02, D-01/D-05)** - `c1908839` (test)

## Files Created/Modified

- `frontend/src/lib/engine/select.ts` - `POLICY_MASS_THRESHOLD`, `C_PUCT`, `ROOT_PRIOR_FLOOR` constants; `truncateAndRenormalize()`, `rootExplorationPriors()`, `selectChild()` pure functions; `SelectionChild` interface
- `frontend/src/lib/engine/__tests__/select.test.ts` - 9 tests across `truncateAndRenormalize`, `selectChild`, and `rootExplorationPriors` describe blocks

## Decisions Made

- `selectChild()` throws on an empty `children` array rather than returning a sentinel — there is no sensible default UCI move, and a node being selected from is expected to always have at least one legal-move child by construction of the caller (`mctsSearch.ts`, Plan 04). Verified with an explicit `toThrow()` test.
- The D-01 root/non-root split test fixture (`splitFixtureChildren`) uses ONE shared array where `rootExplorationPrior` ties both children (isolating Q as the sole root-decision variable) while plain `prior` differs (isolating it as the sole non-root-decision variable) — a tighter proof than two differently-constructed fixtures would give, since it demonstrates the SAME object selects differently depending only on the `isRoot` flag and which field the formula reads.
- Initial fixture draft for the root-Q test had `C_PUCT * exploration_weight * sqrt(N)` swamp the Q difference (caught immediately by a runtime test failure — `scoreB` not `> scoreA`); corrected by equalizing the exploration term between children (same `rootExplorationPrior`, same `visits`) so Q alone decides, per the fixture design already documented above. Same-task correction, not a deviation from the plan's `<action>`/`<acceptance_criteria>`.

## Deviations from Plan

None — plan executed exactly as written. All 5 acceptance-criteria bullets for Task 1 and all 5 for Task 2 are met: `select.ts` exports the exact named set (`POLICY_MASS_THRESHOLD`, `truncateAndRenormalize`, `C_PUCT`, `ROOT_PRIOR_FLOOR`, `rootExplorationPriors`, and the selection function `selectChild`); `truncateAndRenormalize` does not import `CUMULATIVE_MASS_THRESHOLD`/`CANDIDATE_HARD_CAP` from `moveQuality.ts` (confirmed by grep — no import from `../moveQuality` anywhere in `select.ts`); the selection function drops the Q term for non-root and includes it only when `isRoot` is true; `rootExplorationPriors` and `truncateAndRenormalize` are two distinct exported functions; `npx tsc -b` is clean.

## Issues Encountered

None beyond the same-task fixture-value correction noted above (caught by the test itself, not by manual review).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `selectChild()`, `truncateAndRenormalize()`, and `rootExplorationPriors()` are ready for `mctsSearch.ts` (153-04) to import directly for its expansion/selection loop: at each node, call `truncateAndRenormalize(await providers.policy(...))` to get the child priors, `rootExplorationPriors(...)` additionally at the root for the exploration term, and `selectChild(children, node.visits, isRoot)` to pick the next child to descend into.
- The `SelectionChild` interface (`uci`, `prior`, `visits`, optional `q`/`rootExplorationPrior`) is the exact shape `mctsSearch.ts` must populate per node from its own tree-node bookkeeping — `q` comes from `backup.ts`'s `backupExpectation`/`backupRootMax` results (153-02), `rootExplorationPrior` from this plan's `rootExplorationPriors()`.
- No blockers. `select.ts` has zero dependencies beyond plain arrays/`Map`/`Math` — nothing in 153-04/05 is blocked waiting on this file's own dependencies resolving.

---
*Phase: 153-pure-search-core-guardrail-backup-mcts-fallback*
*Completed: 2026-07-05*

## Self-Check: PASSED
