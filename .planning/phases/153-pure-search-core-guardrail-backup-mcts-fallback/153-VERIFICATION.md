---
phase: 153-pure-search-core-guardrail-backup-mcts-fallback
verified: 2026-07-06T00:20:00Z
status: passed
score: 5/5 ROADMAP success criteria verified
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "Decide disposition of 153-REVIEW.md CR-01 (Critical, unresolved): the mctsSearch.ts module header (lines 21-31) and applyExpansion comment (lines 263-268) assert concurrency=1 and concurrency=2 produce bit-identical output/snapshot sequences as a general invariant. The reviewer produced a runnable counterexample proving this is false in general (c=1's second selection happens after applying the first expansion and can re-descend the same subtree; c=2's second selection happens before application and is forced into a different node). The shipped ENGINE-07 concurrency=2 test (mctsSearch.test.ts:356-387) only passes because it reuses the degenerate `makeFixedPolicy({})`/`makeFixedGrade({})` fixture (uniform policy, all-zero evals -> every node value pinned at exactly 0.5), which cannot distinguish the true divergence from the false invariant."
    expected: "One of: (a) accept as documented follow-up debt for Phase 154 and file a tracked issue, or (b) fix now — rewrite the header/comment to state the true, narrower invariant (deterministic per concurrency level; c=1 and c=2 trees may legitimately differ) and add a real concurrency=2-vs-itself repeated-run test with non-degenerate (non-0.5) grades, which is what CONTEXT.md D-03 actually locked ('the ranking is still deterministic with ordered providers') rather than cross-concurrency equality."
    why_human: "This is a scope/priority tradeoff (fix now vs. accept as Phase 154 follow-up), not a fact a grep/read can resolve — ROADMAP SC1 and CONTEXT D-03 are technically satisfied as narrowly worded (repeated runs at a FIXED concurrency are proven bit-identical), so this does not block the phase goal, but the false invariant is live in shipped code comments that Phase 154 will read."

  - test: "Decide disposition of 153-REVIEW.md WR-02 (unresolved): `backupRootMax([])` returns `Math.max(...[])` = `-Infinity` with no degenerate guard, unlike its sibling `backupExpectation` (which guards `totalPrior === 0` and returns 0.5, with a dedicated test). `backup.ts` is an exported public primitive of the frozen Phase 153 surface Phases 154-157 import directly."
    expected: "Either add the guard (`if (children.length === 0) return 0.5;`) plus a test, or explicitly accept the risk on the grounds that `mctsSearch.ts`/`fallbackExpectimax.ts` currently never call `backupRootMax`/`recomputeValue` with zero children (guarded by `children.size === 0` early return in both `recomputeValue` functions) and record why this is safe today."
    why_human: "A correctness judgment about how strictly to harden a public interface function that has no current unguarded call path but no test proving the guard as instructed by the plan's own `backupExpectation` precedent — a policy call, not a discoverable fact."

  - test: "Decide disposition of 153-REVIEW.md WR-01 (unresolved): when mctsSearch's tree is fully closed (all leaves terminal/depth-capped) before `maxNodes` is reached, the selection loop's `SELECTION_ATTEMPT_CAP = 1000` dead-end retries each bump `visits` along the walked path (mctsSearch.ts:373), inflating `RankedLine.visits` (documented in types.ts:57 as 'Total expansion visits attributed to this root candidate') by up to 3 orders of magnitude versus `nodesEvaluated`. Verified independently by reading the code path: the retry loop increments `node.visits` on every dead-end walk, uncapped by any structural closure check."
    expected: "Either land the structural `fullyClosed` propagation fix 153-REVIEW.md WR-01 proposes (with a `visits`-sum regression test), or explicitly accept for Phase 153 on the grounds that Phase 155's UI consumption of `visits` is not yet built and record the acceptance."
    why_human: "Affects the meaning of a frozen, documented `RankedLine` field Phase 155 will render — a scope/timing call on when to fix, not a fact this verifier can resolve alone."

  - test: "Review 153-REVIEW.md WR-03 through WR-08 as a batch (tie-break not UCI-order in `truncateAndRenormalize`; `budgetExhausted`/empty-candidate-set semantic drift between the two 'identical-contract' runners; ~150 duplicated lines including the correctness-critical `terminalValue` frame logic; unhandled illegal/malformed UCI from a provider throwing and rejecting the whole search; zero test coverage for the locked `extraRootMoves` (D-04) and `AbortSignal` contract surfaces) — all unresolved as of this verification (no commits after the review's 00:08 timestamp)."
    expected: "A decision on which of these to close before Phase 154 starts consuming the frozen contract (WR-07/WR-08 in particular touch surfaces Phase 154's real Stockfish/Maia workers will exercise for the first time) versus tracking as follow-up debt."
    why_human: "Prioritization across 6 warnings against the Phase 154 start date — a project-management call, not a fact this verifier can resolve."
---

# Phase 153: Pure Search Core (Guardrail + Backup + MCTS + Fallback) Verification Report

**Phase Goal:** A fully unit-tested, worker-free search core exists behind a stable `position + budget → ranked root lines` interface, with the two highest-risk pieces of the design — the custom Maia-weighted expectimax backup rule and the asymmetric self+opponent ELO routing — proven correct against fabricated providers before any WASM/ONNX integration exists.
**Verified:** 2026-07-06T00:20:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria — authoritative)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1/ENGINE-07 | Fixed FEN + fixed budget + fabricated providers → bit-identical ranked-root-lines across repeated runs, no Dirichlet noise, canonical tie-breaking | ✓ VERIFIED | `mctsSearch.test.ts` "ENGINE-07 determinism" describe block (lines 326-354): two repeated concurrency=1 runs assert `toEqual` on both the final `EngineSnapshot` and the FULL `onSnapshot` sequence (D-10's strengthened guarantee). Grepped `frontend/src/lib/engine/` for `Math.random`/`Date.now`/`performance.now`/`Dirichlet` — zero hits in logic (only in header comments documenting the absence). Independently re-ran `npx vitest run src/lib/engine` — 33/33 pass. **Caveat:** see human-verification item on CR-01 below — the ADDITIONAL concurrency=1-vs-concurrency=2 equality claim in this same test file is disproven in general by code review, though ROADMAP SC1 itself (repeated runs at a fixed budget) does not require cross-concurrency identity and is independently satisfied. |
| SC2/ENGINE-03 | Hand-computed fixture proves non-root backup = Maia-prior-weighted expectation, with negative assertions vs naive average and visit-count-weighted average | ✓ VERIFIED | `backup.test.ts` lines 22-45: three-child fixture (0.6/0.72 expanded, 0.3/0.55 and 0.1/0.4 unexpanded) → `backupExpectation ≈ 0.637` (`toBeCloseTo(0.637, 6)`), with explicit `expect(result).not.toBeCloseTo(0.5567, 2)` (naive average) and `expect(result).not.toBeCloseTo(0.72, 2)` (visit-weighted collapse). Read `backup.ts` directly: `BackupChild` has exactly `{prior, value}`, no `visits`/`n` field or term anywhere in the file. |
| SC3/ENGINE-04 | Node-level oracle test for both root colors — opponent ELO at opponent-to-move nodes, own ELO at own future nodes, keyed on side-to-move not depth parity | ✓ VERIFIED | `mctsSearch.test.ts` "ENGINE-04 ELO oracle" (lines 169-206): recorder-wrapped `policy()` asserts, for BOTH a white-root run and a black-root run, `side==='w' ⇒ elo===1500` and `side==='b' ⇒ elo===1800` across every recorded call. Read `mctsSearch.ts` `fenSide()`/`dispatchExpansion()`: elo is `budget.elo[leaf.side]` where `leaf.side` derives from `fen.split(' ')[1]` — no `depth % 2`/ply-parity expression found by grep. |
| SC4/ENGINE-02+05 | Expansion from fabricated Maia top-k (~90% cumulative mass, renormalized) graded by fabricated shallow-eval; depth-cutoff leaves convert via lichess sigmoid | ✓ VERIFIED | `select.ts` `truncateAndRenormalize` (POLICY_MASS_THRESHOLD=0.9) proven by `select.test.ts` (mass-cut + renormalize to ~1.0). `mctsSearch.test.ts` "ENGINE-02 truncation" (lines 210-228): dropped sub-90%-mass tail moves are asserted absent from every `grade()` call. "ENGINE-05 leaf conversion + depth cutoff" (lines 232-260): an unexpanded leaf's `practicalScore` asserted `toBe` (exact) `evalToExpectedScore(grade, rootMover)`, and a `maxPlies:1` fixture confirms descent stops at the depth ceiling. |
| SC5/ENGINE-06 | fallbackExpectimax.ts implements the identical SearchRunner interface reusing backup.ts and is exercised via swap-in test | ✓ VERIFIED | `fallbackExpectimax.test.ts` "SC5 guardrail swap-in" (lines 108-121): a single `let runner: SearchRunner` variable is assigned `mctsSearch` then reassigned `fallbackExpectimax`, both invoked with identical `(rootFen, budget, providers, onSnapshot, signal)` arguments, both returning a valid non-empty `rankedLines`. Read `fallbackExpectimax.ts`: imports and calls `backupExpectation`/`backupRootMax` from `./backup`, `leafExpectedScore` from `./leafScore`, `truncateAndRenormalize` from `./select` — no second copy of that math. |

**Score:** 5/5 ROADMAP success criteria verified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/engine/types.ts` | Frozen SearchRunner/EngineProviders/SearchBudget/RankedLine/EngineSnapshot contract | ✓ VERIFIED | Exists, exports match D-04/06/07/08/09 shapes exactly (`elo:{w,b}`, `extraRootMoves?`, UCI-typed `rootMove`/`modalPath`, `MoveGrade` re-exported not redeclared). `npx tsc -b` zero errors. |
| `frontend/src/lib/engine/guardrail.ts` | `SearchRunner` type only, no logic | ✓ VERIFIED | Exactly the 5-parameter function type, no logic. |
| `frontend/src/lib/engine/leafScore.ts` | Root-relative leaf-eval-to-expected-score wrapper | ✓ VERIFIED | Wraps `evalToExpectedScore` verbatim; `leafScore.test.ts` (5 tests) proves mirrored (not identical) output across root colors. |
| `frontend/src/lib/engine/backup.ts` | BackupChild + backupExpectation/backupRootMax | ✓ VERIFIED (with WR-02 caveat) | Present, substantive, wired into both runners. `backupRootMax([])` is unguarded (`-Infinity`) — see human-verification. |
| `frontend/src/lib/engine/select.ts` | truncateAndRenormalize, selectChild (PUCT), rootExplorationPriors | ✓ VERIFIED (with WR-03 caveat) | Present, substantive, wired. `truncateAndRenormalize`'s truncation sort has no UCI tie-break (only `selectChild`/`buildModalPath`/`buildRankedLines` do) — see human-verification. |
| `frontend/src/lib/engine/mctsSearch.ts` | SearchRunner orchestrator (select→terminal→expand→backup→snapshot) | ✓ VERIFIED (with WR-01/CR-01 caveats) | Present, substantive, wired, composes all Plan 01-03 primitives correctly for every tested scenario. Exhausted-tree visit-count corruption and the disproven cross-concurrency invariant are real but scoped defects — see human-verification. |
| `frontend/src/lib/engine/fallbackExpectimax.ts` | Depth-limited expectimax reusing shared primitives, identical SearchRunner | ✓ VERIFIED (with WR-04/05/06 caveats) | Present, substantive, wired, reuses `backup.ts`/`leafScore.ts`/`select.ts` verbatim. Diverges from `mctsSearch.ts` on `budgetExhausted` semantics and empty-candidate-set handling — see human-verification. |
| Test files (5, one per module) | Vitest suites proving each must-have | ✓ VERIFIED | `npx vitest run src/lib/engine` → 5 files, 33/33 tests pass (independently re-run). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `leafScore.ts` | `@/lib/liveFlaw` (`evalToExpectedScore`) | import + call, no reimplementation | ✓ WIRED | Confirmed by direct read; no new sigmoid constant. |
| `mctsSearch.ts` / `fallbackExpectimax.ts` | `backup.ts` (`backupExpectation`/`backupRootMax`) | import + call in `recomputeValue` | ✓ WIRED | Both runners call the same functions; no reimplemented combination logic. |
| `mctsSearch.ts` / `fallbackExpectimax.ts` | `select.ts` (`truncateAndRenormalize`) | import + call in expansion | ✓ WIRED | Confirmed in both files. |
| `mctsSearch.ts` | `select.ts` (`selectChild`, `rootExplorationPriors`) | import + call in `selectPath`/`dispatchExpansion` | ✓ WIRED | `fallbackExpectimax.ts` deliberately does NOT use these (uniform depth-first walk, no PUCT) — correct per its design (no PUCT/visit selection). |
| `types.ts` | `@/lib/moveQuality` (`MoveGrade`) | re-export, not redeclare | ✓ WIRED | Confirmed: `export type { MoveGrade }` after `import type { MoveGrade } from '@/lib/moveQuality'`. |
| SC5 swap-in test | `mctsSearch` + `fallbackExpectimax` | one `SearchRunner`-typed variable, identical call args | ✓ WIRED | Confirmed by direct read of `fallbackExpectimax.test.ts` lines 108-121 — genuinely exercised, not just claimed. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Zero type errors across the whole frontend | `cd frontend && npx tsc -b` | No output (clean) | ✓ PASS |
| Engine test suite green | `cd frontend && npx vitest run src/lib/engine` | 5 files / 33 tests pass | ✓ PASS |
| Full frontend suite green | `cd frontend && npm test -- --run` | 122 files / 1439 tests pass | ✓ PASS |
| Lint clean | `cd frontend && npm run lint` | 0 errors (3 pre-existing warnings in `coverage/` build artifacts, unrelated to this phase) | ✓ PASS |
| Knip clean (no dead-export flags on the new engine surface) | `cd frontend && npm run knip` | 0 issues | ✓ PASS |
| No debt markers in phase files | `grep -rnE "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER" frontend/src/lib/engine/` | No matches | ✓ PASS |
| No randomness/wall-clock in engine logic | `grep -rn "Math.random\|Date.now\|performance.now" frontend/src/lib/engine/` | Zero hits in logic (only in comments documenting the absence) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| ENGINE-01 | 153-04 | Ranked candidate root moves scored by practical score | ✓ SATISFIED | `mctsSearch.test.ts` ENGINE-01 describe block |
| ENGINE-02 | 153-03, 153-04 | Maia top-k truncated ~90%, graded by Stockfish shallow-eval | ✓ SATISFIED | `select.test.ts`, `mctsSearch.test.ts` ENGINE-02 describe block |
| ENGINE-03 | 153-02 | Prior-weighted expectation (non-root) / max (root) backup | ✓ SATISFIED | `backup.test.ts`, direct source read |
| ENGINE-04 | 153-04 | Asymmetric self+opponent ELO keyed on side-to-move | ✓ SATISFIED | `mctsSearch.test.ts` ENGINE-04 describe block |
| ENGINE-05 | 153-01, 153-04 | Depth-cutoff leaves via lichess sigmoid | ✓ SATISFIED | `leafScore.test.ts`, `mctsSearch.test.ts` ENGINE-05 describe block |
| ENGINE-06 | 153-01, 153-05 | Stable interface + drop-in fallback | ✓ SATISFIED | `guardrail.ts`, `fallbackExpectimax.test.ts` SC5 swap-in |
| ENGINE-07 | 153-04 | Deterministic output, no Dirichlet noise, canonical tie-break | ✓ SATISFIED (with WR-03/CR-01 caveats) | `mctsSearch.test.ts` ENGINE-07 describe block |

**Orphaned requirements check:** ROADMAP.md's requirements-traceability table lists exactly ENGINE-01..07 for Phase 153, all seven appear in at least one plan's `requirements:` frontmatter (153-01: ENGINE-05/06; 153-02: ENGINE-03; 153-03: ENGINE-02; 153-04: ENGINE-01/02/04/05/07; 153-05: ENGINE-06). No orphaned requirements.

### Anti-Patterns Found (carried forward from 153-REVIEW.md, unresolved — no commits after the review)

| File | Line(s) | Pattern | Severity | Impact |
|------|---------|---------|----------|--------|
| `mctsSearch.ts` | 21-31, 262-268 | CR-01: false general invariant claimed (c=1==c=2 bit-identical) — degenerate test fixture masks the disproof | Critical (per code review) | Misleading documentation for Phase 154; underlying ROADMAP SC1/D-03 scope is still met (see human-verification) |
| `backup.ts` | 54-56 | WR-02: `backupRootMax([])` unguarded, returns `-Infinity` | Warning | Unguarded public primitive on the frozen contract; no current unguarded call path but no guard/test either |
| `mctsSearch.ts` | 53, 360-390 | WR-01: exhausted-tree endgame inflates `RankedLine.visits` by up to 3 orders of magnitude | Warning | Violates the documented meaning of a frozen, Phase-155-consumed field |
| `select.ts` | 45 | WR-03: `truncateAndRenormalize` tie-break is Record-insertion-order, not UCI order | Warning | The one seam in the core not following the locked "canonical UCI tie-break" rule; doesn't affect same-provider repeated-run determinism |
| `mctsSearch.ts` / `fallbackExpectimax.ts` | various | WR-04/WR-05: empty-candidate-set and `budgetExhausted` semantics diverge between the two "identical-contract" runners | Warning | Contradicts `types.ts`'s own doc comment for `budgetExhausted`; the two runners already disagree with each other |
| `mctsSearch.ts` / `fallbackExpectimax.ts` | ~150 lines | WR-06: near-verbatim duplication including `terminalValue` (correctness-critical mate-frame sign logic) | Warning | Maintenance/drift risk — WR-04/05 show it has already happened |
| `mctsSearch.ts` / `fallbackExpectimax.ts` | various | WR-07: a single illegal/malformed UCI from a provider throws and rejects the whole search | Warning | Untested edge relevant to Phase 154's real worker boundary |
| test files | — | WR-08: zero test coverage for `extraRootMoves` (D-04) and `AbortSignal`, both locked `SearchRunner`/`SearchBudget` contract surfaces | Warning | The phase's own goal states "fully unit-tested" — these two locked surfaces have no coverage at all |

None of the above are debt-markers (`TBD`/`FIXME`/`XXX`) — they are code-review findings from `153-REVIEW.md`, independently re-confirmed by direct source reads during this verification. No commits exist after the review's timestamp, so all are still live.

### Human Verification Required

See frontmatter `human_verification` — four items covering CR-01 (Critical), WR-02, WR-01, and a batched WR-03–WR-08 disposition decision. None of these block the ROADMAP success criteria from being VERIFIED (all 5 are satisfied by real, substantive, passing tests), but they represent unresolved code-review findings on a "frozen" contract that Phases 154-157 build against unchanged, and warrant an explicit accept-or-fix decision before or during Phase 154.

### Gaps Summary

No ROADMAP success criterion FAILED and no artifact is missing or stub — the phase goal (a fully unit-tested, worker-free search core proving the backup rule and ELO routing against fabricated providers) is genuinely achieved: all 5 SCs are backed by real, substantive, passing tests that were independently re-run during this verification (33/33 engine tests, 1439/1439 full frontend suite, zero `tsc`/lint/knip issues).

The gap is between "goal achieved" and "zero known defects": `153-REVIEW.md` found 1 Critical + 8 Warning issues, all still unresolved (no commits landed after the review). The most consequential is CR-01 — a documented, code-reviewer-proven-false invariant ("concurrency=1 and concurrency=2 produce bit-identical output") baked into `mctsSearch.ts`'s own header and inline comments, which the shipped test cannot detect because its fixture is degenerate (uniform 0.5 everywhere). This does not fail ROADMAP SC1/CONTEXT.md D-03 as actually scoped (repeated-run determinism at one fixed concurrency, which IS proven), but the false claim is live in code Phase 154 will read and build assumptions on. WR-02 (unguarded `-Infinity` on a public primitive) and WR-01 (visit-count corruption on a documented, frozen field) are the next-most-consequential, both on interfaces Phases 154-157 consume directly. WR-03 through WR-08 round out a pattern of real-but-scoped debt in the delivered "frozen" contract.

Recommendation: resolve or explicitly accept each item in the human-verification list before Phase 154 begins consuming the frozen `EngineProviders`/`SearchBudget`/`SearchRunner` contract at scale, since several (WR-07, WR-08, WR-02) touch code paths Phase 154's real Stockfish/Maia workers will exercise for the first time.

---

_Verified: 2026-07-06T00:20:00Z_
_Verifier: Claude (gsd-verifier)_
