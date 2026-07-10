---
phase: 159-flawchess-engine-policy-temperature-root-move-findability-se
plan: 03
subsystem: ai
tags: [typescript, vitest, mcts, expectimax, flawchess-engine, softmax-temperature]

requires:
  - phase: 159-01
    provides: "findability.ts (P_REF_ANCHORS, pRefForElo, rankScore) and buildRankedLines/buildSnapshot's rootElo-threaded ranking, which this plan's temperature-adjusted child.prior feeds into for free (D-06 composition)"
provides:
  - "policyTemperature.ts pure module: DEFAULT_POLICY_TEMPERATURE=1, applyPolicyTemperature(policy, T) (p^(1/T) renormalized), ROOT_CANDIDATE_HARD_CAP=15"
  - "treeCommon.ts sideMatchesMover(side, mover) — the dedicated Side<->MoverColor comparison — and applyRootCandidateHardCap(candidateMap), both shared by the two SearchRunner implementations"
  - "SearchBudget.policyTemperature?: number threaded through both mctsSearch.ts's dispatchExpansion (gained a new rootMover parameter) and fallbackExpectimax.ts's expandNode (rootMover already in scope), applied ONLY on the root-mover's own side, BEFORE truncateAndRenormalize, short-circuited at the default temperature"
affects: [159-04]

tech-stack:
  added: []
  patterns:
    - "Layered pure transforms (select.ts convention): temperature reshapes the policy BEFORE truncateAndRenormalize; the root-candidate hard cap is applied AFTER truncation+extraRootMoves, at the root branch only — three sequential, never-conflated steps"
    - "Shared cross-runner helpers live in treeCommon.ts (sideMatchesMover, applyRootCandidateHardCap) so mctsSearch.ts and fallbackExpectimax.ts can never independently re-implement (and silently diverge on) the same logic"

key-files:
  created:
    - frontend/src/lib/engine/policyTemperature.ts
    - frontend/src/lib/engine/__tests__/policyTemperature.test.ts
    - frontend/src/lib/engine/__tests__/treeCommon.test.ts
  modified:
    - frontend/src/lib/engine/treeCommon.ts
    - frontend/src/lib/engine/types.ts
    - frontend/src/lib/engine/mctsSearch.ts
    - frontend/src/lib/engine/fallbackExpectimax.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
    - frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts

key-decisions:
  - "ROOT_CANDIDATE_HARD_CAP set to 15 (D-07/Pitfall 6 discretion) — generous at T~1 (real Maia policies are peaked, typically far below this), bounded enough at T=2.0 to protect the fixed FLAWCHESS_ENGINE_MAX_NODES=400 visit budget from diluting across dozens of near-uniform root candidates"
  - "applyRootCandidateHardCap and sideMatchesMover placed in treeCommon.ts (the existing shared-primitives file for both SearchRunner implementations) rather than inlined per-runner, so Pitfall 3 (the two runners silently diverging) is structurally impossible rather than merely avoided by copy-paste discipline"
  - "Test discriminator for the D-05 opponent-untouched case: a same-shape 0.85/0.05/0.05/0.05 distribution at both the root and a real depth-1 opponent FEN, where raw (T=1) truncation keeps exactly 2 candidates and T=2 flattening would keep all 4 — proven via the exact candidateUcis recorded at grade() time, not via output inference"

requirements-completed: []

coverage:
  - id: D1
    description: "policyTemperature.ts exports DEFAULT_POLICY_TEMPERATURE=1 (strict), applyPolicyTemperature (p^(1/T) renormalized with a zero-mass guard), and ROOT_CANDIDATE_HARD_CAP; does NOT import moveQuality.ts"
    requirement: SEED-085
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/policyTemperature.test.ts (10 tests: direction, T=1 identity, renormalization, empty/zero-mass guard, hard-cap sanity)"
        status: pass
      - kind: other
        ref: "grep confirms the three exports and the absence of a moveQuality.ts import"
        status: pass
    human_judgment: false
  - id: D2
    description: "sideMatchesMover(side, mover) added to treeCommon.ts alongside fenSide, covering all four Side x MoverColor truth-table combinations"
    requirement: SEED-085
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/treeCommon.test.ts (4 tests: w/white, b/black, b/white, w/black)"
        status: pass
    human_judgment: false
  - id: D3
    description: "SearchBudget gains optional policyTemperature; both runners apply applyPolicyTemperature ONLY on the root-mover's own side, before truncateAndRenormalize, short-circuited at DEFAULT_POLICY_TEMPERATURE; a root-only hard cap guards extreme flattening; temperature composes with the D-01 findability ranking via child.prior with zero extra glue"
    requirement: SEED-085
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts > 'Phase 159 policy temperature' (4 tests: no-op regression, opponent-untouched via exact candidateUcis, D-06 composition reversing the T=1/T=2 winner, root-cap regression)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts > 'Phase 159 policy temperature' (mirrored 4-test suite, proving runner parity per Pitfall 3)"
        status: pass
      - kind: other
        ref: "cd frontend && npx tsc -b (zero errors) && npm run lint (zero errors) && npm run knip (no new dead exports)"
        status: pass
    human_judgment: false

duration: 16min
completed: 2026-07-07
status: complete
---

# Phase 159 Plan 03: Policy temperature core (Thread A) Summary

**New `policyTemperature.ts` implements the standard `p^(1/T)` softmax-temperature reshape (T=1 no-op, T>1 flattens, T<1 sharpens), applied only on the root-mover's own side before the existing 0.9-mass truncation in both `mctsSearch.ts` and `fallbackExpectimax.ts`, with a named `ROOT_CANDIDATE_HARD_CAP=15` guarding the fixed visit budget against pathological flattening — the temperature-adjusted `child.prior` composes with Plan 01's findability ranking automatically, with zero third combiner function.**

## Performance

- **Duration:** ~16 min
- **Completed:** 2026-07-07
- **Tasks:** 2
- **Files modified:** 9 (3 new, 6 edited)

## Accomplishments
- Created `frontend/src/lib/engine/policyTemperature.ts` exporting `DEFAULT_POLICY_TEMPERATURE=1`, `applyPolicyTemperature(policy, temperature)` (p^(1/T) renormalized with a zero-mass guard), and `ROOT_CANDIDATE_HARD_CAP=15` — deliberately not coupled to `moveQuality.ts`'s independent `CANDIDATE_HARD_CAP`.
- Added `sideMatchesMover(side, mover)` to `treeCommon.ts` — the single tested Side<->MoverColor comparison reused at both orchestrators' call sites, closing the Pitfall 2 risk of a hand-rolled comparison drifting between the two files.
- Added `applyRootCandidateHardCap(candidateMap)` to `treeCommon.ts` — root-only, applied AFTER temperature + truncation + the `extraRootMoves` union, never inside `truncateAndRenormalize` itself, shared by both runners.
- Threaded `SearchBudget.policyTemperature?: number` through `types.ts`, and wired the identical temperature-reshape step into `mctsSearch.ts`'s `dispatchExpansion` (which gained a new `rootMover` parameter) and `fallbackExpectimax.ts`'s `expandNode` (which already had `rootMover` in scope) — both edits landed in the same commit per Pitfall 3.
- Regression-tested: the no-op short-circuit at the default temperature (bit-identical `rankedLines`/`nodesEvaluated`/`budgetExhausted`), the opponent-side-untouched invariant (D-05, proven via the EXACT `candidateUcis` recorded at `grade()` time — 2 candidates for the untouched opponent vs. 4 for the temperature-flattened root-mover side on the identical distribution shape), the D-06 composition claim (temperature flips the low-ELO findability winner from `e2e3` at T=1 to `e2e4` at T=2, purely because `child.prior` — what T changed — is what `rankScore` reads), and the D-07 root-candidate hard cap (an extreme-flatness fixture over the 20-legal-move starting position never exceeds 15 root children).

## Task Commits

Each task was committed atomically:

1. **Task 1: policyTemperature.ts + sideMatchesMover helper + tests** - `82c710f5` (feat)
2. **Task 2: Thread temperature through SearchBudget + both runners** - `f9e958eb` (feat)

**Plan metadata:** (this commit, docs)

## Files Created/Modified
- `frontend/src/lib/engine/policyTemperature.ts` - New pure module: DEFAULT_POLICY_TEMPERATURE, applyPolicyTemperature, ROOT_CANDIDATE_HARD_CAP
- `frontend/src/lib/engine/__tests__/policyTemperature.test.ts` - Unit tests: direction, T=1 identity, renormalization, empty/zero-mass guard
- `frontend/src/lib/engine/__tests__/treeCommon.test.ts` - New file: sideMatchesMover 4-case truth table
- `frontend/src/lib/engine/treeCommon.ts` - Added sideMatchesMover and applyRootCandidateHardCap alongside fenSide
- `frontend/src/lib/engine/types.ts` - SearchBudget gained optional policyTemperature field
- `frontend/src/lib/engine/mctsSearch.ts` - dispatchExpansion gained rootMover param; temperature reshape + root-cap wired in
- `frontend/src/lib/engine/fallbackExpectimax.ts` - expandNode mirrors the identical temperature reshape + root-cap treatment
- `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` - New "Phase 159 policy temperature" describe block (4 tests)
- `frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts` - Mirrored "Phase 159 policy temperature" describe block (4 tests) + a shared makeFixedGrade calls-tracking extension

## Decisions Made
- `ROOT_CANDIDATE_HARD_CAP = 15` (Claude's discretion per D-07) — generous at T~1, bounded at T=2.0 against the 400-node budget; documented in the module header, not empirically tuned against real Maia distributions this session (same caveat class as Plan 01's `P_REF_ANCHORS`).
- Shared helpers (`sideMatchesMover`, `applyRootCandidateHardCap`) live in `treeCommon.ts` rather than being duplicated inline in each runner, structurally preventing Pitfall 3 divergence.
- The opponent-untouched test proves the invariant via the literal `candidateUcis` array recorded at the `grade()` call boundary (not via output inference), since `dispatchExpansion`/`expandNode` are private functions with no other externally observable seam for the post-provider-call transform.

## Deviations from Plan

None - plan executed exactly as written. The plan's suggested "inline slice" phrasing for the root-candidate hard cap was implemented as a small shared function in `treeCommon.ts` instead of literally duplicating a slice at each of the two call sites — this is the same "single shared implementation, never re-implemented per runner" discipline the plan's own Pitfall 3 discussion (and `treeCommon.ts`'s existing module header) already mandates for every other cross-runner primitive, not a deviation from intent.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The pure temperature transform, `SearchBudget.policyTemperature`, and both runners' wiring are ready for Plan 04 to consume via a UI slider (`TemperatureSelector.tsx`) and thread through `useFlawChessEngine.ts` — no further search-core changes needed.
- `ROOT_CANDIDATE_HARD_CAP`'s value (15) and `P_REF_ANCHORS` (Plan 01) both remain open items for the Plan 04 UAT checkpoint per Pitfall 4/6 — validated by unit test, not yet empirically confirmed against live Maia distributions at extreme temperature settings.

---
*Phase: 159-flawchess-engine-policy-temperature-root-move-findability-se*
*Completed: 2026-07-07*

## Self-Check: PASSED

All 9 created/modified source files plus this SUMMARY.md verified present on disk; both task commits (`82c710f5`, `f9e958eb`) verified present in git log.
