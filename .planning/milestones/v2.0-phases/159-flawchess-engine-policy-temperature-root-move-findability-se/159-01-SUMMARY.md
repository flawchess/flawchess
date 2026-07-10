---
phase: 159-flawchess-engine-policy-temperature-root-move-findability-se
plan: 01
subsystem: ai
tags: [typescript, vitest, mcts, expectimax, flawchess-engine, ranking]

requires:
  - phase: 153
    provides: MCTS/expectimax search core (backup.ts, select.ts, treeCommon.ts, leafScore.ts) that this plan's ranking-layer change sits on top of, untouched
provides:
  - "findability.ts pure module: P_REF_ANCHORS, pRefForElo(elo), rankScore(pYou, pRef, value) — the D-01 saturating linear findability factor"
  - "buildRankedLines/buildSnapshot threaded with a rootElo parameter, sorting root candidates by findability-weighted rankScore instead of raw practicalScore"
  - "Both SearchRunner implementations (mctsSearch, fallbackExpectimax) pass budget.elo[root.side] through the single treeCommon.ts seam, so the fix covers both engines identically"
affects: [159-02, 159-03, 159-04]

tech-stack:
  added: []
  patterns:
    - "Sort-only local field (never assigned onto a public shape) computed once per call, not per child — mirrors select.ts's layered-transform discipline"

key-files:
  created:
    - frontend/src/lib/engine/findability.ts
    - frontend/src/lib/engine/__tests__/findability.test.ts
  modified:
    - frontend/src/lib/engine/treeCommon.ts
    - frontend/src/lib/engine/mctsSearch.ts
    - frontend/src/lib/engine/fallbackExpectimax.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
    - frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts

key-decisions:
  - "P_REF_ANCHORS starting hypothesis (600->0.12 ... 2600->0.005) taken verbatim from RESEARCH.md's worked example — flagged in the module header as a hypothesis to validate via live UAT (159-04), not a proven fact, since the real D-03 FENs were never recovered"
  - "buildRankedLines pairs each public RankedLine with its ephemeral sortRankScore via a parallel { line, sortRankScore } array rather than a spread-and-omit destructure, to avoid an eslint no-unused-vars error on the discarded key"
  - "D-03 regression fixture values (Nb5/Qxf2/Rxf2 priors and V, Qb8 prior and V) are illustrative approximations of the real observed grades (Best > Good > Mistake), not recovered real numbers — matches the plan's own acknowledgment that the real FENs are unavailable this session"

requirements-completed: [SEED-085]

coverage:
  - id: D1
    description: "findability.ts exports P_REF_ANCHORS, pRefForElo(elo), and rankScore(pYou, pRef, value); pRefForElo is monotonically non-increasing across 600-2600 and clamps outside it; rankScore saturates to exactly value at pYou>=pRef and guards pRef<=0"
    requirement: SEED-085
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/findability.test.ts (10 tests: pRefForElo shape/clamp/interpolation, rankScore saturation/scaling/guard/upper-bound)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The three D-03 regression cases pass as unit assertions: Nb5 (5%@600) does not top the ranking, Qxf2 (9%@600) beats both Nb5 and Rxf2 (57%@600, Mistake), Qb8 (~5%@1000 tail move) does not beat an in-chart candidate"
    requirement: SEED-085
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/findability.test.ts > 'D-03 regression cases' (2 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "buildRankedLines/buildSnapshot gain a rootElo parameter; both mctsSearch.ts and fallbackExpectimax.ts pass budget.elo[root.side] at every call site; practicalScore stays byte-identical to child.value; the canonical-UCI tie-break is preserved; both runners produce the identical findability-reordered sequence on the same fixture"
    requirement: SEED-085
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts > 'Phase 159 D-01 findability ranking'"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts > 'Phase 159 D-01 findability ranking' (incl. cross-runner identical-order assertion)"
        status: pass
      - kind: other
        ref: "cd frontend && npx tsc -b (zero errors) && npm run lint (zero errors) && npm run knip (no new dead exports)"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-07
status: complete
---

# Phase 159 Plan 01: Root-move findability ranking (Thread B) Summary

**New `findability.ts` pure module folds the root player's own Maia move-probability back into `buildRankedLines`'s sort via a saturating `min(1, P_you/P_ref)*V(X)` factor, so a ~5%-findable tail move can no longer top the FlawChess Engine's recommendation — threaded through both `mctsSearch` and `fallbackExpectimax` via one shared `rootElo` parameter, with `practicalScore` staying byte-identical.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-07-07
- **Tasks:** 2
- **Files modified:** 7 (2 new, 5 edited)

## Accomplishments
- Created `frontend/src/lib/engine/findability.ts` exporting `P_REF_ANCHORS`, `pRefForElo(elo)`, and `rankScore(pYou, pRef, value)` — the D-01 saturating linear findability factor, with beta fixed at 1 so the modal/highest-prior move can never be boosted above its own V.
- Wired `rootElo` through `buildRankedLines`/`buildSnapshot` in `treeCommon.ts`: `pRef` computed once per call, `rankScore` used as a sort-only local, canonical-UCI tie-break preserved, `practicalScore` unchanged.
- Both `mctsSearch.ts` and `fallbackExpectimax.ts` now pass `budget.elo[root.side]` at every `buildSnapshot` call site, so the findability fix covers both `SearchRunner` implementations through the single shared seam — no independent re-implementation.
- Regression-tested the three D-03 acceptance cases as pure `rankScore` assertions, plus a synthetic low-prior/high-V vs. high-prior/lower-V fixture proving the actual reorder happens end-to-end in both orchestrators, with an explicit cross-runner identical-order assertion.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create findability.ts pure module + tests** - `afb9e425` (feat)
2. **Task 2: Wire findability into buildRankedLines/buildSnapshot and both runners** - `2df45601` (feat)

**Plan metadata:** (this commit, docs)

## Files Created/Modified
- `frontend/src/lib/engine/findability.ts` - New pure module: P_REF_ANCHORS curve, pRefForElo interpolation, rankScore saturating factor
- `frontend/src/lib/engine/__tests__/findability.test.ts` - Unit tests for the above, including the three D-03 regression cases
- `frontend/src/lib/engine/treeCommon.ts` - buildRankedLines/buildSnapshot gain rootElo; rankScore sort-only local; stale prior doc comment updated
- `frontend/src/lib/engine/mctsSearch.ts` - Both buildSnapshot call sites pass budget.elo[root.side]
- `frontend/src/lib/engine/fallbackExpectimax.ts` - Both buildSnapshot call sites pass budget.elo[root.side]
- `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` - New Phase 159 D-01 findability-ranking test
- `frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts` - New Phase 159 D-01 findability-ranking test + cross-runner identical-order assertion

## Decisions Made
- Kept `P_REF_ANCHORS` exactly as RESEARCH.md's worked hypothesis (600->0.12 down to 2600->0.005), documented in the module header as an assumption pending live UAT validation (D-02 is fully Claude's discretion; only the qualitative shape and the three D-03 cases are locked).
- Used a parallel `{ line, sortRankScore }` array instead of a spread-and-omit destructure in `buildRankedLines`, to keep `eslint`'s `no-unused-vars` clean without a throwaway-prefixed binding — no behavior change, same output shape.
- D-03 fixture P/V values are illustrative constructions consistent with the Best/Good/Mistake grade ordering (real FENs unavailable this session, per RESEARCH.md Open Question 1) — the live end-to-end check is deferred to 159-04's UAT checkpoint as the plan specifies.

## Deviations from Plan

None - plan executed exactly as written. The `buildRankedLines` implementation detail (parallel array instead of spread-and-omit) is a mechanical lint-compliance choice within the plan's own "sort-only local, never assigned onto RankedLine" requirement, not a deviation from its intent.

## Issues Encountered
- Initial `buildRankedLines` implementation (matching RESEARCH.md's literal example verbatim, `lines.map(({ sortRankScore: _sortRankScore, ...line }) => line)`) failed `npm run lint` with `no-unused-vars` on the destructured discard — fixed inline by restructuring to a parallel-array pairing (Rule 1, auto-fixed, folded into Task 2's commit since it landed before the task commit).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `findability.ts` and the `rootElo`-threaded ranking are ready for Plan 02 (Thread A, policy temperature) to compose against: temperature reshapes `child.prior` before truncation, and `rankScore` already reads whatever prior lands on the root child post-truncation — no further wiring needed for the two threads to compose.
- `P_REF_ANCHORS` calibration remains an open item for the phase-close UAT checkpoint (159-04) per Pitfall 4 — the anchors are a validated-by-unit-test hypothesis, not empirically confirmed against the real 600/1000-ELO positions.

---
*Phase: 159-flawchess-engine-policy-temperature-root-move-findability-se*
*Completed: 2026-07-07*

## Self-Check: PASSED

All 5 created/modified files verified present on disk; both task commits (`afb9e425`, `2df45601`) verified present in git log.
