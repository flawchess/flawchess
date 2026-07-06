---
phase: 153-pure-search-core-guardrail-backup-mcts-fallback
reviewed: 2026-07-05T22:06:42Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - frontend/src/lib/engine/types.ts
  - frontend/src/lib/engine/guardrail.ts
  - frontend/src/lib/engine/leafScore.ts
  - frontend/src/lib/engine/backup.ts
  - frontend/src/lib/engine/select.ts
  - frontend/src/lib/engine/mctsSearch.ts
  - frontend/src/lib/engine/fallbackExpectimax.ts
  - frontend/src/lib/engine/__tests__/leafScore.test.ts
  - frontend/src/lib/engine/__tests__/backup.test.ts
  - frontend/src/lib/engine/__tests__/select.test.ts
  - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
  - frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts
findings:
  critical: 1
  warning: 8
  info: 3
  total: 12
status: issues_found
---

# Phase 153: Code Review Report

**Reviewed:** 2026-07-05T22:06:42Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the new pure TypeScript search core (`frontend/src/lib/engine/`) plus its five test files, cross-referencing the imported primitives (`evalToExpectedScore`/`sideToMoveFromFen` in `liveFlaw.ts`, `uciToSquares` in `sanToSquares.ts`, `MoveGrade` in `moveQuality.ts`) and the phase's locked decisions in 153-CONTEXT.md / 153-04-PLAN.md.

The core correctness machinery is sound: the root-relative value frame is threaded correctly (rootMover computed once, no per-ply negation), ELO routing is genuinely color-keyed off each node's own FEN side field, the backup rule is structurally prior-weighted (no visit term anywhere in `backup.ts`), truncation keeps the crossing move, terminal values are frame-correct, and `Promise.all` canonical-order application is real. All 33 tests pass.

However, the phase's headline ENGINE-07 claim — bit-identical output at concurrency=1 vs concurrency=2 — is **not a real invariant of this algorithm**. I disproved it with a runnable counterexample (details in CR-01): the shipped test passes only because its fixture pins every node value at exactly 0.5, making the test structurally unable to detect the divergence. Additionally, the two swappable `SearchRunner` implementations have already drifted from each other in three observable ways despite the module headers claiming divergence is impossible, the exhausted-tree endgame in `mctsSearch` demonstrably corrupts reported visit counts (verified: `nodesEvaluated: 1`, root-child visits sum ≈ 1000), and two locked contract surfaces (`extraRootMoves`, `AbortSignal`) have zero test coverage.

## Critical Issues

### CR-01: The concurrency=1 vs concurrency=2 "bit-identical" invariant is false; the test fixture is degenerate and cannot detect it

**File:** `frontend/src/lib/engine/mctsSearch.ts:22-31, 262-268` and `frontend/src/lib/engine/__tests__/mctsSearch.test.ts:356-387`

**Issue:** The module header, the `applyExpansion` comment ("required for ENGINE-07's concurrency=1 vs concurrency=2 snapshot-sequence equality"), and 153-04-PLAN.md's success criterion all claim c=1 and c=2 produce bit-identical output. This is provably false in general. The mechanism cannot deliver it: at c=1, the second selection of a round happens **after** applying the first expansion (it sees the backed-up value and can re-descend into the same subtree); at c=2, the second selection happens **before** application with the first leaf merely pending-excluded (it is forced to pick a different node). Deferring visit bumps to apply time equalizes visit *counts* in snapshots but cannot equalize *which nodes get selected*.

I verified this with a scratch test (root policy `{e2e4: 0.8, e2e3: 0.2}`, root grades `+200cp`/`+100cp`, uniform-neutral below; `maxNodes: 3, maxPlies: 3`): `expect(resultC2).not.toEqual(resultC1)` **passes** — c=1 expands `root → e2e4 → e2e4-child` while c=2 expands `root → {e2e4, e2e3}`, yielding different visits and modal paths.

The shipped ENGINE-07 test passes only because `makeFixedPolicy({})`/`makeFixedGrade({})` produce uniform policies and all-zero evals, so every node value is pinned at exactly 0.5 forever and selection is insensitive to the information difference. The test is structurally incapable of detecting the false claim it exists to prove.

Note that 153-CONTEXT.md's D-03 only requires the c=2 test to prove "the ranking is still deterministic with ordered providers" — determinism at c=2 *does* hold (selection is synchronous and application is dispatch-ordered). The bit-identical-to-c=1 escalation entered in 153-04-PLAN.md and is undeliverable. This matters downstream: Phase 154 runs concurrency 2-4 and will silently produce different rankings than any sequential reference; any debugging or verification workflow that assumes c-independence will chase phantom bugs.

**Fix:**
1. Change the ENGINE-07 c=2 test to assert what D-03 actually locked: two repeated c=2 runs with (differently) jittered providers produce identical output + snapshot sequences — not equality with the c=1 run.
2. Rewrite the mctsSearch.ts:22-31 header and the applyExpansion:262-268 comment to state the true invariant: output is deterministic *per concurrency level*; c=1 and c=2 trees may legitimately differ because pending-exclusion forces same-round breadth.
3. Regardless of choice, add non-neutral grades to the determinism fixtures so future regressions are detectable (the current all-0.5 fixture also weakens the repeated-run test).

## Warnings

### WR-01: Exhausted-tree endgame corrupts RankedLine.visits (verified ~1000 phantom visits) and can silently mislabel an early stop as budget exhaustion

**File:** `frontend/src/lib/engine/mctsSearch.ts:53, 360-390`

**Issue:** When the tree is fully closed (all leaves terminal or depth-capped) but `maxNodes` is not yet reached, the selection loop spins up to `SELECTION_ATTEMPT_CAP = 1000` dead-end walks, each bumping `visits` along its path (line 373), before concluding `toExpand.length === 0`. Verified with a scratch run (`maxPlies: 1, maxNodes: 3` on the K+P fixture): the final snapshot reports `nodesEvaluated: 1` while root-child visits sum to ~1000. Consequences:
- `RankedLine.visits` (documented in types.ts:57 as "Total expansion visits attributed to this root candidate") is inflated by up to 3 orders of magnitude and no longer reflects search effort. `modalPath` (most-visited-child selection) is also computed over these phantom visits.
- The final returned snapshot differs from the last `onSnapshot` emission (same `nodesEvaluated`, different visits), violating the reasonable expectation that the return value equals the last tick.
- If the cap ever trips while expandable leaves *remain* (deep tree where PUCT needs >1000 bumps to redirect away from a high-Q dead end — the constant's own comment admits this is only "generous enough" for "realistic fixture trees"), the search stops early and reports `budgetExhausted: true`, which is a lie.
The existing `maxPlies: 1` test (mctsSearch.test.ts:250) asserts `nodesEvaluated` and `modalPath` but never `visits`, so this is invisible to the suite.

**Fix:** Detect closure structurally instead of by retry: propagate a `fullyClosed` flag upward when a node is closed and all children are closed (or return a "dead-end vs. expandable" discriminant from `selectPath` and stop the round after the first full-tree dead-end pass at an unchanged frontier). At minimum, stop bumping visits on repeat discoveries of an already-closed leaf within the exhaustion-probe loop, and add a `visits`-sum assertion to the depth-cutoff test.

### WR-02: `backupRootMax([])` returns `-Infinity`

**File:** `frontend/src/lib/engine/backup.ts:54-56`

**Issue:** `Math.max(...[])` is `-Infinity`. Its sibling `backupExpectation` has an explicit degenerate guard (returns 0.5, with a dedicated test), but `backupRootMax` has none — an empty children array silently yields `-Infinity`, which would flow into `practicalScore` (documented as 0-1). Current orchestrators happen to guard via `recomputeValue`'s `children.size === 0` early return, but `backup.ts` is an exported public primitive of the locked Phase 153 surface that Phases 154-157 build against directly.

**Fix:**
```typescript
export function backupRootMax(children: readonly BackupChild[]): number {
  if (children.length === 0) return 0.5; // degenerate guard, mirrors backupExpectation
  return Math.max(...children.map((c) => c.value));
}
```

### WR-03: `truncateAndRenormalize` breaks probability ties by Record key insertion order, not UCI order

**File:** `frontend/src/lib/engine/select.ts:45`

**Issue:** `Object.entries(policy).sort((a, b) => b[1] - a[1])` leaves equal-probability moves in the provider's key insertion order. When two equal-probability moves straddle the 0.9 mass boundary, *which one survives truncation* depends on the order the provider happened to build its Record — not on the phase's locked "deterministic … UCI-string tie-breaks" rule. Repeated runs of the same provider stay deterministic, but a real Maia provider (Phase 154) that assembles its output Record in a different order (e.g., after a WASM update) changes the search tree with no code change in `lib/engine/`. Every other tie in the core (`selectChild`, `buildModalPath`, `buildRankedLines`) is UCI-broken; this is the one seam that is not.

**Fix:**
```typescript
const sorted = Object.entries(policy).sort(
  (a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1),
);
```

### WR-04: Runner drift #1 — empty candidate set: fallback closes for free, mcts burns budget and calls `grade(fen, [])`

**File:** `frontend/src/lib/engine/mctsSearch.ts:324-343, 399-405` vs `frontend/src/lib/engine/fallbackExpectimax.ts:261-266`

**Issue:** `fallbackExpectimax.expandNode` explicitly guards a degenerate empty candidate set (closes the node as a dead end **before** calling `grade()` and **without** incrementing `nodesEvaluated`). `mctsSearch.dispatchExpansion` has no such guard: an empty `truncateAndRenormalize` result still calls `providers.grade(fen, [])`, and `applyExpansion` still counts the node against `maxNodes` (`nodesEvaluated += 1` at line 402). The two implementations of the same frozen `SearchRunner` contract disagree on D-09 semantics ("one node = one expansion event") for the identical input. A real `grade()` provider receiving an empty `candidateUcis` array is also an untested edge in Phase 154's worker protocol.

**Fix:** In `dispatchExpansion` (or before dispatch in the selection loop), mirror the fallback's guard: if `candidateMap.size === 0`, close the leaf (`isExpanded = true`, `isPending = false`) without calling `grade()` and without consuming node budget.

### WR-05: Runner drift #2 — `budgetExhausted` semantics contradict types.ts and each other

**File:** `frontend/src/lib/engine/fallbackExpectimax.ts:241-249, 269-270` vs `frontend/src/lib/engine/mctsSearch.ts:387-390`; contract at `frontend/src/lib/engine/types.ts:66-67`

**Issue:** `types.ts` documents `budgetExhausted` as "True once `SearchBudget.maxNodes`/`maxPlies` stopped the search (not an abort)". The two runners disagree with the doc and with each other:
- **fallback:** when `maxPlies` (not `maxNodes`) is what stops the walk — which is the *normal* termination mode for a full-width expectimax — `budgetExhausted` stays `false` (it is only ever set on the `maxNodes` path, lines 246-248/270). Per the doc it should be `true`.
- **mcts:** a terminal root (nothing to search at all) yields `budgetExhausted: true` via the empty-`toExpand` branch (line 388), though no budget dimension stopped anything.
- **fallback bonus:** a terminal root produces *zero* `onSnapshot` emissions and `budgetExhausted: false`; mcts's terminal root emits none either but reports `true` — so Phase 155's hook sees contradictory completion states from the two "identical-contract" runners on the same input.

**Fix:** Pick one semantic and enforce it in both runners: set `budgetExhausted = true` whenever the walk was cut by `maxPlies` or `maxNodes` (fallback: set it when any node is closed by the depth check while unexpanded; mcts: don't set it when the root itself is terminal). Add a shared contract test running both runners over the same terminal-root and maxPlies-bound fixtures.

### WR-06: ~150 lines duplicated verbatim across the two runners — including correctness-critical `terminalValue` — and drift has already happened

**File:** `frontend/src/lib/engine/mctsSearch.ts:44-172, 225-233, 272-314` and `frontend/src/lib/engine/fallbackExpectimax.ts:48-160, 162-214`

**Issue:** `NEUTRAL_EXPECTED_SCORE`, `fenSide`, `terminalValue`, `applyUciMoveFen`, `createRoot`, `createChildNode`, `recomputeValue`, `buildModalPath`, `buildRankedLines`, and `buildSnapshot` are copy-pasted near-verbatim between the two files. The fallback's header sells its reuse of shared primitives as the mechanism by which "`practicalScore` semantics cannot silently diverge (D-06)" — but `terminalValue` (the root-relative mate/draw frame, exactly the class of subtle sign logic this phase's own docs call the highest-risk detail) and the entire `RankedLine` construction are *not* shared; they are parallel copies. WR-04 and WR-05 show divergence between the twins has already occurred in this very phase. A future fix to, say, mate handling in one file will not propagate to the other.

**Fix:** Extract the pure, strategy-agnostic helpers into a shared internal module (e.g. `frontend/src/lib/engine/treeCommon.ts`): `terminalValue`, `applyUciMoveFen`, `fenSide`, `NEUTRAL_EXPECTED_SCORE`, and (parameterized over a minimal node shape) `recomputeValue`/`buildModalPath`/`buildRankedLines`/`buildSnapshot`. The two orchestrators keep only their genuinely distinct search strategies, which is the actual ENGINE-06 independence story.

### WR-07: A single illegal/malformed UCI from a provider or `extraRootMoves` rejects the entire search with no containment

**File:** `frontend/src/lib/engine/mctsSearch.ts:103-112, 332-337` and `frontend/src/lib/engine/fallbackExpectimax.ts:95-104, 253-258`

**Issue:** `applyUciMoveFen` feeds provider-supplied UCI strings straight into chess.js's `.move()`, which **throws** on an illegal move or malformed string (`uciToSquares` returns null below 4 chars, and the `uci.slice()` fallback then passes garbage squares). Candidate UCIs come from `policy()` output and `budget.extraRootMoves` — in Phase 154 these are real Maia and Stockfish outputs crossing a worker boundary, exactly where a stale-FEN race or protocol hiccup produces a move that is legal in a *different* position. One bad UCI throws from inside `applyExpansion`/`expandNode`, rejecting the whole `SearchRunner` promise after budget was partially consumed and (in mcts) leaving sibling `isPending` markers set. There is no validation, no per-candidate containment, and no test for this path. The tests explicitly guarantee legality ("built from ACTUAL chess.js legal moves"), so the suite can never hit it.

**Fix:** Validate at the trust boundary: in `applyExpansion`/`expandNode`, skip (or drop with a preserved-mass renormalization) any candidate whose `chess.move()` throws, e.g. wrap the single move application and `continue` on failure — a deterministic drop, not a crash. Alternatively validate `extraRootMoves` and policy keys against `new Chess(fen).moves()` once per expansion.

### WR-08: Zero test coverage for two locked contract surfaces: `extraRootMoves` (D-04) and `AbortSignal`

**File:** `frontend/src/lib/engine/__tests__/mctsSearch.test.ts`, `frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts`

**Issue:** Verified by grep across both suites:
- `extraRootMoves` — the D-04 root-union path (implemented twice: mctsSearch.ts:332-337, fallbackExpectimax.ts:253-258, plus the D-05 floor whose entire rationale is these injected moves) is never exercised by any test. No test proves an extra root move survives truncation, receives the exploration floor, gets graded, or appears in `rankedLines`.
- `signal` — every test uses a never-aborted `freshSignal()`. Abort semantics (stop expanding, return partial snapshot, `budgetExhausted` stays false, no further `onSnapshot` after abort) are completely unverified for both runners, despite `signal` being a parameter of the frozen `SearchRunner` type this phase locks for Phases 154-157.

**Fix:** Add (a) a D-04 test injecting a zero-Maia-probability `extraRootMoves` UCI and asserting it appears in `rankedLines` with a floor-boosted exploration prior and is passed to `grade()`; (b) an abort test that aborts after the Nth `onSnapshot` and asserts the search stops promptly, resolves (not rejects), and reports `budgetExhausted: false`.

## Info

### IN-01: `EngineProviders` has no `AbortSignal` parameter — in-flight provider work is uncancellable through the core

**File:** `frontend/src/lib/engine/types.ts:26-31`

**Issue:** The runner receives a `signal`, but the frozen provider surface (`policy(fen, elo, side)`, `grade(fen, candidateUcis)`) cannot observe it. An abort only takes effect after all in-flight provider promises resolve; Phase 154's real Stockfish/Maia worker calls cannot be cancelled mid-flight via this contract. Since the types are locked for the rest of the milestone, this is the last cheap moment to add an optional `signal?: AbortSignal` trailing parameter.

**Fix:** Consider `policy(fen, elo, side, signal?)` / `grade(fen, candidateUcis, signal?)` before Phase 154 freezes worker plumbing; otherwise document that abort latency is bounded by the slowest in-flight provider call.

### IN-02: `terminalValue` re-parses the FEN it already has a `Chess` instance for; bare `0.5` draw literal

**File:** `frontend/src/lib/engine/mctsSearch.ts:92-100` and `frontend/src/lib/engine/fallbackExpectimax.ts:84-92`

**Issue:** The function constructs `new Chess(fen)` then calls `sideToMoveFromFen(fen)` (a second parse with a different color vocabulary) where `chess.turn()` already returns `'w' | 'b'`. The draw return is a bare `0.5` in both copies while a named `NEUTRAL_EXPECTED_SCORE` constant exists in both files (CLAUDE.md: no magic numbers) — a distinct `DRAW_EXPECTED_SCORE` (or reuse) would make the semantics explicit.

**Fix:** `const checkmatedSide = chess.turn() === 'w' ? 'white' : 'black';` (or compare `Side` directly) and name the draw constant. Folds into the WR-06 extraction naturally.

### IN-03: `selectChild` exits via an `as string` assertion; `selectPath` maps `uci: c.uci ?? ''`

**File:** `frontend/src/lib/engine/select.ts:133` and `frontend/src/lib/engine/mctsSearch.ts:211`

**Issue:** Minor type-safety style: `return bestUci as string` (a cast, commented, but restructurable — e.g. initialize `bestUci` from a guarded `children[0]`), and the `?? ''` fallback for child UCIs papers over an impossible state where an empty string would win every ascending tie-break. Neither is reachable today; both mask rather than encode the invariant.

**Fix:** Initialize the loop with the first child (`const first = children[0]; if (!first) throw ...`) so `bestUci` is `string` throughout; children of any node always have non-null `uci`, so consider typing child UCIs as `string` at the node level (only the root's `uci` is null, and the root is never a child).

---

_Reviewed: 2026-07-05T22:06:42Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
