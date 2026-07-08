---
phase: 153-pure-search-core-guardrail-backup-mcts-fallback
fixed_at: 2026-07-06T06:35:00Z
review_path: .planning/phases/153-pure-search-core-guardrail-backup-mcts-fallback/153-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 153: Code Review Fix Report

**Fixed at:** 2026-07-06T06:35:00Z
**Source review:** .planning/phases/153-pure-search-core-guardrail-backup-mcts-fallback/153-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (1 Critical + 8 Warning; fix_scope=critical_warning, IN-01/IN-03 not applied, IN-02 subsumed by WR-06)
- Fixed: 9
- Skipped: 0

**Verification:** after every fix and at the end: `npx vitest run src/lib/engine` (46 tests, up from 33), `npx tsc -b`, `npx eslint src/lib/engine`, `npx knip` — all clean.

## Fixed Issues

### CR-01: False c=1 vs c=2 "bit-identical" invariant; degenerate determinism fixture

**Files modified:** `frontend/src/lib/engine/mctsSearch.ts`, `frontend/src/lib/engine/__tests__/mctsSearch.test.ts`
**Commit:** 5665bb80
**Applied fix:** Per the review's recommended direction (no algorithm change): the ENGINE-07 c=2 test now asserts what D-03 actually locked — bit-identical output + snapshot sequences across two repeated c=2 runs under *different* non-monotonic provider jitters — instead of equality with the c=1 run. The module header gained a "Determinism scope" paragraph and the `applyExpansion` comment was rewritten to state the true invariant (deterministic per concurrency level; c=1 and c=2 trees may legitimately differ because pending-exclusion forces same-round breadth). Determinism fixtures were hardened with a non-uniform root policy plus a deterministic hash-derived non-neutral grade at every node, and a guard assertion verifies the fixture is not 0.5-degenerate.

### WR-01: Exhausted-tree endgame corrupts RankedLine.visits (~1000 phantom visits)

**Files modified:** `frontend/src/lib/engine/mctsSearch.ts`, `frontend/src/lib/engine/__tests__/mctsSearch.test.ts`
**Commit:** b9c1e3f3
**Applied fix:** Chose the review's structural option: nodes carry an `isClosed` flag (terminal at creation, depth-cap at first discovery, empty expansion, or all-children-closed via root-ward `propagateClosure`). `selectPath` filters closed subtrees (and a closed root), so each dead end is discovered — and visit-bumped — exactly once. `SELECTION_ATTEMPT_CAP` is removed entirely; loop termination is now structural, eliminating the "cap trips while expandable leaves remain → false budgetExhausted" failure mode. The depth-cutoff test gained the recommended visits regression assertion (`visits === 1` per depth-capped child).

### WR-02: `backupRootMax([])` returns -Infinity

**Files modified:** `frontend/src/lib/engine/backup.ts`, `frontend/src/lib/engine/__tests__/backup.test.ts`
**Commit:** 7f0fb56f
**Applied fix:** Added the review's suggested degenerate guard (returns 0.5, mirroring `backupExpectation`) with a comment explaining why the exported primitive must be safe standalone; added a test.

### WR-03: Truncation ties broken by Record insertion order

**Files modified:** `frontend/src/lib/engine/select.ts`, `frontend/src/lib/engine/__tests__/select.test.ts`
**Commit:** 34b44ac0
**Applied fix:** Applied the suggested sort fallback (`b[1] - a[1] || (a[0] < b[0] ? -1 : 1)`) so equal probabilities tie-break by ascending UCI. Added a boundary-straddling-tie test proving both insertion orders keep the same survivor (fixture uses 0.75+0.2 rather than the review's implied 0.7+0.2, which is < 0.9 in doubles).

### WR-04: mcts calls `grade(fen, [])` and burns budget on empty candidate sets

**Files modified:** `frontend/src/lib/engine/mctsSearch.ts`, `frontend/src/lib/engine/__tests__/mctsSearch.test.ts`
**Commit:** 886c0f54
**Applied fix:** `dispatchExpansion` skips `grade()` when the candidate set is empty; `applyExpansion` closes the leaf as a dead end (no children, no visit bumps); the orchestrator skips `nodesEvaluated`/`onSnapshot` for it — matching `fallbackExpectimax`'s existing guard and D-09. Test asserts grade() is never called with `[]` and `nodesEvaluated === 0`.

### WR-05: `budgetExhausted` semantics contradict types.ts and each other

**Files modified:** `frontend/src/lib/engine/mctsSearch.ts`, `frontend/src/lib/engine/fallbackExpectimax.ts`, `frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts`
**Commit:** 94bdb8e4
**Applied fix:** Enforced the types.ts semantic in both runners: `budgetExhausted = true` iff `maxNodes` or `maxPlies` cut an expandable (non-terminal) node. Fallback now sets it when the depth check closes an unexpanded node; mcts sets it in the dead-end depth-cap branch and no longer reports a fully searched (e.g. terminal-root) tree as exhaustion. Added the recommended shared contract test running BOTH runners over the same terminal-root and maxPlies-bound fixtures (identical completion states, including zero-snapshot terminal roots).

### WR-06: ~150 duplicated lines across the two runners, including `terminalValue`

**Files modified:** `frontend/src/lib/engine/treeCommon.ts` (new), `frontend/src/lib/engine/mctsSearch.ts`, `frontend/src/lib/engine/fallbackExpectimax.ts`
**Commit:** a3d19956
**Applied fix:** Created `treeCommon.ts` exporting `NEUTRAL_EXPECTED_SCORE`, `fenSide`, `terminalValue`, `applyUciMoveFen`, and — parameterized over a recursive `SearchTreeNode<N>` shape — `recomputeValue` and `buildSnapshot` (`buildModalPath`/`buildRankedLines` are module-private, consumed via `buildSnapshot`, keeping knip clean). `EngineNode extends SearchTreeNode<EngineNode>` adds only pending/closure/root-floor fields; `FallbackNode` is the bare shared shape. This subsumes IN-02 as the review anticipated: `terminalValue` now reads `chess.turn()` instead of re-parsing the FEN, and the draw literal is the named `DRAW_EXPECTED_SCORE`.

### WR-07: One illegal/malformed provider UCI rejects the entire search

**Files modified:** `frontend/src/lib/engine/treeCommon.ts`, `frontend/src/lib/engine/mctsSearch.ts`, `frontend/src/lib/engine/fallbackExpectimax.ts`, `frontend/src/lib/engine/__tests__/mctsSearch.test.ts`, `frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts`
**Commit:** 4101a10d
**Applied fix:** `applyUciMoveFen` now returns `string | null` (null when chess.js rejects the move) with a trust-boundary comment; both runners `continue` past null candidates — a deterministic drop with priors renormalized downstream by `backupExpectation`, never a crash. If ALL candidates are illegal, WR-01's closure logic already closes the node cleanly. Tests in both suites feed an illegal move (`e7e5` from a white-to-move FEN) plus a malformed UCI (`zz`) and assert the search resolves with only legal moves ranked.

### WR-08: Zero coverage for `extraRootMoves` (D-04) and `AbortSignal`

**Files modified:** `frontend/src/lib/engine/__tests__/mctsSearch.test.ts`, `frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts`
**Commit:** c73af326
**Applied fix:** Both suites gained (a) a D-04 test injecting `e1f1` (in the fixture's dropped tail) via `extraRootMoves`, asserting it is passed to `grade()`, carries its own grade-derived `practicalScore` (not the 0.5 omitted-grade fallback), appears in `rankedLines`, and does NOT revive its dropped-tail siblings; and (b) an abort test that aborts inside the 2nd `onSnapshot`, asserting prompt stop, resolution (not rejection), exactly 2 snapshots (none after abort), and `budgetExhausted: false`. One deviation from the review's wording: the D-05 floor-boosted *exploration prior* is not externally observable through the frozen `SearchRunner` surface, so it is proven indirectly (the injected move is graded and ranked) rather than asserted directly.

## Skipped Issues

None.

## Notes

- IN-01 and IN-03 (Info tier) were intentionally not applied per fix_scope=critical_warning. IN-02 was folded into WR-06 as the review itself recommended ("Folds into the WR-06 extraction naturally").
- 153-04-PLAN.md's ENGINE-07 success criterion still words the invariant as c=1 vs c=2 equality; the code and tests now document the corrected invariant (deterministic per concurrency level, per D-03). The planning doc was left untouched (out of the review's cited fix scope) — worth a one-line amendment if the phase docs are revisited.
- Engine suite grew from 33 to 46 tests; `tsc -b`, `eslint`, and `knip` are all clean on the changed surface.

---

_Fixed: 2026-07-06T06:35:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
