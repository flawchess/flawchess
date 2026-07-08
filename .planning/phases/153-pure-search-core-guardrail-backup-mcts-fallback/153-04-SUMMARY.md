---
phase: 153-pure-search-core-guardrail-backup-mcts-fallback
plan: 04
subsystem: engine
tags: [typescript, engine-core, mcts, search-orchestrator, vitest]

# Dependency graph
requires:
  - "frozen types.ts/guardrail.ts contract (153-01)"
  - "leafExpectedScore() root-relative leaf-eval-to-expected-score conversion (153-01)"
  - "backupExpectation()/backupRootMax() Maia-prior-weighted backup rule (153-02)"
  - "truncateAndRenormalize()/rootExplorationPriors()/selectChild() deterministic PUCT selection (153-03)"
provides:
  - "mctsSearch() — the primary SearchRunner orchestrator: select -> terminal check -> expand -> backup -> snapshot"
affects: [153-05-fallbackExpectimax, 154-real-providers, 155-react-hook]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Private in-memory EngineNode tree (fen/side/depth/prior/value/visits/isPending/isTerminal/isExpanded/children) is the orchestrator's only mutable state — no exported class, matches guardrail.ts's function-type contract"
    - "Terminal-ness (chess.js isGameOver) is determined ONCE at node creation time, immediately overriding the leaf-estimate value if game-over — a terminal node is permanently isExpanded=true with zero children, so it can never be re-selected for its own expansion"
    - "extraRootMoves union happens AFTER truncateAndRenormalize (not before), guaranteeing inclusion regardless of Maia mass — matches D-05's floor-boost rationale (an SF-injected candidate with ~0 Maia probability must still receive PUCT exploration weight)"
    - "Concurrent dispatch: Promise.all's input-order-preserving resolution IS the canonical-order buffer-then-apply mechanism (Pattern 5) — no separate sort/bookkeeping needed beyond building the dispatch array via synchronous, deterministic PUCT selection before any await"
    - "Visit-count increments happen at APPLY time, not at selection/dispatch time — the isPending flag alone prevents a same-round re-pick, so deferring the bump keeps intermediate onSnapshot visit counts identical regardless of concurrency"

key-files:
  created:
    - frontend/src/lib/engine/mctsSearch.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
  modified: []

key-decisions:
  - "extraRootMoves (D-04) unioned with the truncated Maia top-k set AFTER truncateAndRenormalize, not before — the plan's action text was ambiguous on ordering; D-05's own rationale (floor-boosting a candidate with ~0 Maia probability) only makes sense if that candidate would otherwise survive truncation via forced inclusion, which requires post-truncation union."
  - "Removed an eager 'virtual visit' bump at selection/dispatch time (visits+=1 immediately upon marking a leaf isPending) in favor of incrementing visits only at apply time. Discovered via the ENGINE-07 concurrency=2 determinism test failing on intermediate onSnapshot visit counts (0 vs 1) even though final results matched — isPending alone already prevents re-picking a node within a round, so the extra eager bump was unnecessary and broke snapshot-sequence bit-identity."
  - "Added a root-is-pending guard at the top of selectPath — without it, a concurrency>1 dispatch round could select the still-unexpanded pending root twice in the same round (the child-level pending filter never protects the walk's own starting node). Found and fixed while designing the Task 3 determinism fixtures, before any test asserted on it directly."
  - "SELECTION_ATTEMPT_CAP (1000) added as a safety valve bounding a single round's synchronous dead-end/pending-skip retries — without it, a subtree that is entirely terminal or depth-capped (or where every remaining child is already pending) would spin the selection loop forever without consuming node budget. Not explicitly required by the plan text but a necessary correctness/liveness guarantee; exercised directly by the maxPlies=1 depth-cutoff test."
  - "Test fixtures use a small chess.js-derived helper (uniformPolicyFromLegalMoves) to build fabricated policy distributions from ACTUAL legal moves at any reachable fen, rather than hand-enumerating UCI lists for every tree node — avoids illegal-move runtime errors deep in the search tree for tests that don't need precise truncation control (ELO oracle, depth-cutoff, determinism)."

patterns-established:
  - "Pattern: terminal-value fixed at child-creation time (not lazily at selection time) — collapses the terminal/depth-ceiling handling into one code path (both close a node to isExpanded=true with zero children, forever) and makes 'no policy() call for a terminal node' a structural guarantee rather than something enforced by careful call-site ordering."

requirements-completed: [ENGINE-01, ENGINE-02, ENGINE-04, ENGINE-05, ENGINE-07]

coverage:
  - id: D1
    description: "mctsSearch returns a ranked RankedLine[] scored by practicalScore, sorted descending, from a fixed FEN + budget + fabricated providers"
    requirement: "ENGINE-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — ENGINE-01 ranked output"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every policy() call's elo is keyed on the NODE's own side-to-move field (fen.split(' ')[1]), never depth/ply parity — proven for both a white-root and a black-root run"
    requirement: "ENGINE-04"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — ENGINE-04 ELO oracle"
        status: pass
    human_judgment: false
  - id: D3
    description: "The ~90%-mass-truncated dropped tail is never passed to grade(); extraRootMoves union happens only at the root"
    requirement: "ENGINE-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — ENGINE-02 truncation"
        status: pass
    human_judgment: false
  - id: D4
    description: "An unexpanded leaf's practicalScore matches evalToExpectedScore(grade, rootMover) exactly; descent stops at budget.maxPlies (every modal path is exactly one ply for a maxPlies=1 fixture)"
    requirement: "ENGINE-05"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — ENGINE-05 leaf conversion + depth cutoff"
        status: pass
    human_judgment: false
  - id: D5
    description: "Terminal positions (Pitfall 6): mate-in-1 yields practicalScore ~1.0 for the mating root move; a 2-ply forced-mate fixture yields ~0.0 when the root player is mated one ply deeper; zero policy() calls recorded for either terminal node's own fen"
    requirement: null
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — terminal positions"
        status: pass
    human_judgment: false
  - id: D6
    description: "Bit-identical final EngineSnapshot AND full onSnapshot emission sequence across two repeated concurrency=1 runs, and across concurrency=1 vs concurrency=2 with deliberately jittered promise-resolution order"
    requirement: "ENGINE-07"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — ENGINE-07 determinism"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-07-05
status: complete
---

# Phase 153 Plan 04: MCTS Search Orchestrator Summary

**`mctsSearch.ts` — the select→terminal→expand→backup→snapshot orchestrator composing Plans 01-03's primitives into the frozen `SearchRunner` contract, with a private in-memory node tree, chess.js-driven terminal detection, and a concurrency-safe buffer-then-apply-in-canonical-order dispatch loop proven bit-identical at concurrency 1 and 2 via a 9-test suite (ranked output, both-color ELO oracle, truncation, leaf-sigmoid match, depth cutoff, mate-in-1 and forced-mate-in-2 terminal fixtures, and full snapshot-sequence determinism).**

## Performance

- **Duration:** 35 min
- **Tasks:** 3
- **Files modified:** 2 (both new)

## Accomplishments

- `frontend/src/lib/engine/mctsSearch.ts` implements `SearchRunner`: a private `EngineNode` tree, `selectPath()` (deterministic PUCT descent with pending-aware child filtering), terminal detection at node-creation time (chess.js `isGameOver()`, fixed root-relative value, never separately expanded), `dispatchExpansion()`/`applyExpansion()` (policy → truncate/renormalize → root-only `extraRootMoves` union → one batched `grade()` call → backup propagation root-ward), and ranked-line/modal-path construction with canonical UCI tie-breaks throughout.
- `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` (9 tests, all pass) proves: non-empty descending-sorted ranked output (ENGINE-01); per-node-color ELO keying for both a white-root and a black-root run (ENGINE-04); the dropped truncation tail is never graded (ENGINE-02); an unexpanded leaf's `practicalScore` exactly equals `evalToExpectedScore(grade, rootMover)` and descent never passes `budget.maxPlies` (ENGINE-05); a mate-in-1 fixture yields `practicalScore ≈ 1.0` and a 2-ply forced-mate fixture yields `≈ 0.0` for the root player being mated one ply deeper, with zero `policy()` calls ever recorded for either terminal node's fen; and bit-identical final snapshots + full `onSnapshot` sequences across two repeated runs and across concurrency=1 vs. jittered-resolution concurrency=2 (ENGINE-07).
- All fabricated test providers derive their candidate-move distributions from chess.js's own legal-move enumeration at each reachable fen (never hand-enumerated UCI lists), eliminating illegal-move risk in deeper tree nodes for the ELO-oracle, depth-cutoff, and determinism fixtures.
- `npx tsc -b` reports zero errors project-wide; `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts` is green (9/9); `npm run lint` and `npm run knip` are clean; the full frontend suite (`npm test -- --run`) passes 1435/1435.

## Task Commits

Each task was committed atomically:

1. **Task 1: mctsSearch.ts — select→terminal→expand→backup→snapshot loop (ENGINE-01/02/04/05/07)** - `c9f24509` (feat)
2. **Task 2: mctsSearch.test.ts — ranked output, ELO oracle, truncation+leaf, terminal (ENGINE-01/02/04/05)** - `a918ed69` (test)
3. **Task 3: mctsSearch.test.ts — determinism suite, concurrency 1 and 2 (ENGINE-07)** - `79482af8` (test, includes the selectPath root-pending-guard + deferred-visit-increment fix)

## Files Created/Modified

- `frontend/src/lib/engine/mctsSearch.ts` - `mctsSearch: SearchRunner` orchestrator: private `EngineNode` tree, `selectPath`/`createRoot`/`createChildNode`/`terminalValue`/`applyExpansion`/`dispatchExpansion`/`buildModalPath`/`buildRankedLines`/`buildSnapshot` helpers
- `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` - 9 tests across ranked-output, ELO-oracle, truncation, leaf-conversion+depth-cutoff, terminal-position, and ENGINE-07-determinism describe blocks

## Decisions Made

- `extraRootMoves` (D-04) unioned with the truncated Maia top-k AFTER `truncateAndRenormalize`, not before — required for D-05's floor-boost rationale (a Stockfish-injected candidate with near-zero Maia probability must survive the mass cut via forced inclusion, then get floor-boosted for PUCT exploration only).
- Removed an eager "virtual visit" bump at selection/dispatch time in favor of incrementing visits only at apply time — discovered via the ENGINE-07 concurrency=2 test initially failing on intermediate `onSnapshot` visit-count divergence (0 vs 1) despite matching final results. The `isPending` flag alone already prevents a same-round re-pick; the extra eager bump was unnecessary and broke snapshot-SEQUENCE bit-identity (as opposed to just final-result identity).
- Added a root-is-pending guard at the top of `selectPath` — the child-level pending filter never protects the walk's own starting node, so without this a concurrency>1 round could select the still-unexpanded pending root twice in the same round before it's ever applied.
- Added `SELECTION_ATTEMPT_CAP = 1000` as a liveness safety valve bounding a round's synchronous dead-end/pending-skip retries — prevents an all-terminal/all-depth-capped/all-pending subtree from spinning the selection loop forever without consuming node budget. Directly exercised by the maxPlies=1 depth-cutoff test (budget exhausts after root's single expansion).
- Test fixtures build fabricated policy distributions from chess.js's own legal-move enumeration (`uniformPolicyFromLegalMoves`) rather than hand-enumerated UCI lists, for every test that doesn't need precise truncation control — avoids illegal-move errors at deeper, unconfigured tree nodes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] selectPath missing root-pending guard**
- **Found during:** Task 3 (writing the ENGINE-07 concurrency=2 determinism fixture)
- **Issue:** `selectPath` filtered pending CHILDREN when descending, but never checked whether the walk's own starting node (the root) was itself pending. A concurrency>1 dispatch round, before root's first expansion, could select the pending root a second time in the same round.
- **Fix:** Added `if (root.isPending) return null;` at the top of `selectPath`.
- **Files modified:** `frontend/src/lib/engine/mctsSearch.ts`
- **Verification:** ENGINE-07 concurrency=2 test passes; full engine suite green.
- **Committed in:** `79482af8` (Task 3 commit)

**2. [Rule 1 - Bug] Eager virtual-visit bump broke snapshot-sequence determinism**
- **Found during:** Task 3 (the concurrency=2 vs concurrency=1 test initially failed with a visits-field diff on two ranked-lines entries mid-sequence)
- **Issue:** Visits were incremented immediately when a leaf was marked `isPending` for dispatch (before its async provider calls resolved). In a multi-select round (concurrency=2), this made a not-yet-applied sibling's visit count visible one snapshot earlier than the equivalent sequential (concurrency=1) run would show it, since concurrency=1 only ever selects and bumps one node at a time, always after applying the previous one.
- **Fix:** Moved the path visit-count increment from selection/dispatch time into `applyExpansion` (apply time). The `isPending` flag alone already prevents a same-round re-pick of the same node, so no correctness was lost.
- **Files modified:** `frontend/src/lib/engine/mctsSearch.ts`
- **Verification:** `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts` — 9/9 pass, including both determinism tests asserting `toEqual` on full snapshot sequences.
- **Committed in:** `79482af8` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs found while implementing the plan's own ENGINE-07 acceptance criteria, not scope additions)
**Impact on plan:** Both fixes are internal correctness details of the concurrency/determinism mechanism the plan itself specifies (Pattern 5); no interface, requirement, or acceptance-criterion changes. No scope creep.

## Issues Encountered

None beyond the two auto-fixed issues above, both caught by the test suite itself (not manual review) before any commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `mctsSearch` is ready for `fallbackExpectimax.ts` (153-05) to be compared against via the SC5 swap-in test (same `SearchRunner` type, same `EngineProviders`/`SearchBudget`/`EngineSnapshot` shapes) — no changes needed to this plan's exports.
- The `EngineNode`/`selectPath`/`applyExpansion`/terminal-detection internals are private to this file (not exported) — 153-05 must implement its own tree/traversal internals, reusing only `backup.ts`, `select.ts`'s `truncateAndRenormalize`, and `leafScore.ts` per the plan's Open Question 2 resolution, not this file's private helpers.
- No blockers. `mctsSearch` has zero dependencies beyond the Plan 01-03 primitives, `chess.js`, and `@/lib/liveFlaw`/`@/lib/sanToSquares` (both already-shipped, already-tested project utilities) — nothing in 153-05/154/155 is blocked waiting on this file's own dependencies resolving.

---
*Phase: 153-pure-search-core-guardrail-backup-mcts-fallback*
*Completed: 2026-07-05*

## Self-Check: PASSED
