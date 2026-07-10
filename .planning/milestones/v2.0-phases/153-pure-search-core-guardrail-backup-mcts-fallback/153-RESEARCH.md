# Phase 153: Pure Search Core (Guardrail + Backup + MCTS + Fallback) - Research

**Researched:** 2026-07-05
**Domain:** Deterministic client-side MCTS/expectimax chess search core (pure TypeScript, no workers, no React)
**Confidence:** HIGH — grounded in direct reads of the target codebase files, the locked CONTEXT.md decisions, and the prior milestone-level ARCHITECTURE/SUMMARY/PITFALLS research. The one genuinely new finding below (root-relative score frame) is derived directly from the locked SEED-082 formulas + D-06, not external research, and is HIGH confidence by construction (it falls out of the math, not a guess).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Selection policy (select.ts)**
- **D-01 Deterministic PUCT, chance-node-aware.** The tree has exactly one max node: the root. Selection at the ROOT uses Q-based UCB: `argmax Q(c) + c_puct · P_root(c) · √N(root)/(1+n(c))`. At ALL non-root nodes (all expectation/chance nodes under the locked backup rule) the Q term is dropped: `argmax P̂(c) · √N(node)/(1+n(c))` — refine what dominates the expectation. Ties broken by canonical UCI-string order. `c_puct` is a named tunable constant. No Dirichlet noise anywhere.
- **D-02 Backup expectation ranges over the FULL truncated top-k set** with best-estimate child values: a child with its own subtree contributes its backed-up expectation; a subtree-less child contributes `sigmoid(shallowEval)` from the batched grade() done at its parent's expansion. No probability mass is ever dropped. **This clarifies ROADMAP.md Phase 153 SC2's "expectation over expanded children" wording — do not implement a renormalized expanded-subtrees-only expectation.** The hand-computed SC2 fixture must mix expanded and unexpanded children in one case.
- **D-03 Parallel-ready core loop now.** The orchestrator issues up to `budget.concurrency` expansions concurrently; selection marks in-flight nodes (pending/virtual-visit state) so it never re-picks them. The ENGINE-07 bit-identical determinism suite runs at `concurrency=1`; add one `concurrency=2` fake-provider test proving the ranking is still deterministic with ordered providers. Rationale: Phase 154's 2–4-worker pool needs multiple grade() calls in flight; restructuring the loop mid-154 would violate the spirit of ENGINE-06.

**Root candidate union (SearchRunner interface)**
- **D-04 `extraRootMoves?: string[]` parameter on the SearchRunner signature.** Root children = Maia top-k ∪ extraRootMoves, all graded in the same batched grade() call; deeper nodes remain Maia-top-k-only. `EngineProviders` stays exactly `{policy, grade}`. Phase 155's hook will feed the already-running `useStockfishEngine` MultiPV `pv[0]` moves; Phase 153 tests pass literal arrays. The interface is final from day one (ENGINE-06).
- **D-05 Floor-boosted root exploration prior.** `P_root(c) = max(P_maia(c), ROOT_PRIOR_FLOOR)` renormalized over the root candidate set (floor a named constant, ~0.10), used ONLY in the root PUCT exploration term — otherwise an SF-injected candidate with ~0 Maia probability would never receive subtree visits and its practical score would stay a single shallow eval. backup.ts expectations use true renormalized Maia priors everywhere (the floor never touches values), and ranking is by V (root = max), so scores are never distorted — only visit allocation.

**Score semantics + interface shape (types.ts)**
- **D-06 `practicalScore` is expected score 0–1** from the root side-to-move's perspective — the native space of `evalToExpectedScore` and of all backup math; SEED-082's stated unit ("expected points, comparable to WDL"). The core never converts to pawn units. How Phase 155 renders "objectively +3.0, practically +0.9 for you" (percentage, pawn-equivalent via inverse sigmoid, delta) is a free presentation decision over the raw `{practicalScore, objectiveEvalCp}` pair.
- **D-07 Color-keyed ELOs: `budget.elo = { w: number, b: number }`.** The core selects the ELO for every policy() call purely from the node's side-to-move color — the ENGINE-04 keying rule becomes structural, leaving no place for the depth-parity inversion pitfall. The yourElo/opponentElo → color mapping is resolved once, in the Phase 155 hook, where `user_color` is known. The ENGINE-04 oracle test asserts per-call `(fen side-to-move → elo)` pairs for both root colors.
- **D-08 UCI notation throughout the core.** `policy()` returns UCI-keyed probabilities (what `maskAndSoftmax` already emits), `grade()` takes/returns UCI moves (what the pv[0]-keyed worker protocol already speaks), `RankedLine.rootMove`/`modalPath` carry UCI. Canonical tie-break key = UCI string. SAN conversion happens only at display time (Phase 155), same as `EngineLines` today. (Supersedes the SAN field names sketched in `.planning/research/ARCHITECTURE.md`'s example interfaces.) **CORRECTION (verified against source, see Code Context below): `maskAndSoftmax` today emits SAN-keyed probabilities, not UCI — D-08's premise is inaccurate about the CURRENT state of that function. D-08's UCI-throughout DECISION for the new core stands (it is still the right choice, matching `grade()`'s pv[0]/UCI convention), but Phase 154's real `policy()` provider will need a SAN→UCI re-keying step over `maskAndSoftmax`'s output — flag this for the Phase 154 researcher, it is out of scope for Phase 153's fabricated providers.**

**Budget + snapshot contract**
- **D-09 One "node" = one expansion event** — one policy() call plus one batched grade() call over that node's truncated top-k. `nodesEvaluated += 1` per expansion; `budgetExhausted` at `nodesEvaluated ≥ maxNodes`. Keeps SEED-082's "few hundred node evaluations" arithmetic meaningful and maps 1:1 to wall-clock cost drivers.
- **D-10 Core emits `onSnapshot` after EVERY completed backup; throttling is the caller's job.** No wall-clock (`Date.now()`) anywhere in `lib/engine/`. The Phase 155 hook applies the ~10Hz/`RAPID_STEP_DEBOUNCE_MS`-style batching. The ENGINE-07 test can therefore assert the FULL snapshot emission sequence is bit-identical across runs, not just the final output.
- **D-11 Separate engine mass-truncation constant** — a new named constant in `lib/engine` (e.g. `POLICY_MASS_THRESHOLD = 0.90`, per ENGINE-02's ~90%), independent of `moveQuality.ts`'s `CUMULATIVE_MASS_THRESHOLD = 0.95`. Search branching factor and chart display set are different concerns and must tune independently.

### Claude's Discretion
- `c_puct`, `ROOT_PRIOR_FLOOR`, `POLICY_MASS_THRESHOLD`, and the `maxPlies` default (within the locked 6–10 band) — exact values as named tunable constants, revisited post-UAT.
- Virtual-visit/pending-marker mechanics, tree data structures, and how the async completion loop is structured.
- Terminal-position handling (mate/stalemate before the depth cutoff), mate-score representation in `MoveGrade`, and fixture design details — flagged by the research as Phase 153 researcher territory (see "Terminal Positions" and "Fixture Designs" below).
- `fallbackExpectimax.ts` internals, as long as it reuses `backup.ts` and implements the identical `SearchRunner` (locked by ENGINE-06/SC5).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (Trap-finder UI, per-ELO sigmoids, time-pressure conditioning, SAB multithreading, and Maia-2 adoption are already formally deferred in REQUIREMENTS.md → Future Requirements.) Two reviewed todos (Tailwind score-axis label, bitboard partial-position storage) are unrelated, not folded in.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENGINE-01 | Ranked candidate root moves by expected practical score | `types.ts`'s `RankedLine.practicalScore` (D-06) + `guardrail.ts`'s `SearchRunner` contract (Pattern 1) implement this end to end; the determinism fixture (ENGINE-07) doubles as the acceptance test for "returns a ranked list" |
| ENGINE-02 | Maia top-k (~90% mass, renormalized) graded by Stockfish shallow-eval per node | `select.ts`/`mctsSearch.ts` expansion step + `POLICY_MASS_THRESHOLD` (D-11); mirrors `moveQuality.ts`'s `selectCandidatesByMass` truncation *pattern* (not its constant) — see "Truncation Algorithm" below for the exact mass-cut recipe to reuse |
| ENGINE-03 | Maia-prior-weighted expectation backup (non-root), max (root) | `backup.ts` — see "Backup Rule: Worked Fixture" below for the exact hand-computed numbers to encode as the SC2 test, plus the two negative-assertion baselines |
| ENGINE-04 | Asymmetric self/opponent ELO keyed by actual side-to-move | `budget.elo: {w,b}` (D-07) + the ELO-oracle test design in "ELO Oracle Fixture" below, covering both root colors |
| ENGINE-05 | Leaf eval → expected score via lichess sigmoid | `leafScore.ts` wraps the ALREADY-SHIPPED `evalToExpectedScore()` in `frontend/src/lib/liveFlaw.ts` (verified: `LICHESS_K = 0.00368208` already exists in `frontend/src/generated/flawThresholds.ts`, generated from the backend) — see "Root-Relative Score Frame" below for the ONE non-obvious wiring detail (which `mover` argument to pass) |
| ENGINE-06 | Stable `position + budget → ranked root lines` interface; fallback drop-in | `guardrail.ts`'s `SearchRunner` type (Pattern 1) + `fallbackExpectimax.ts` reusing `backup.ts` (Pattern 2); SC5's swap-in test is the acceptance check |
| ENGINE-07 | Deterministic, reproducible output under fixed budget | Canonical UCI tie-break (D-01) + buffered-apply-in-canonical-order backup (not raw arrival order, per Pitfall 5) + `onSnapshot`-sequence assertion (D-10) — see "Determinism Mechanics" below |
</phase_requirements>

## Summary

Phase 153 builds the one part of the v2.0 FlawChess Engine that is genuinely novel and genuinely risky: a deterministic, worker-free TypeScript search core combining Maia-prior-weighted expectation (non-root) with a plain max (root) inside an MCTS budget-allocation loop, plus a depth-limited expectimax fallback behind the identical interface. Everything downstream (Phase 154's real Stockfish/Maia workers, Phase 155's React hook, Phases 156–157's UI) depends on this phase locking a correct, fully unit-tested contract first. No new npm dependency is needed — `chess.js@1.4.0` is already installed and is the only external package the core touches, for legal-move generation and child-FEN derivation.

The most consequential fact this research surfaces, not previously spelled out in CONTEXT.md or the prior milestone research, is that **every value flowing through `backup.ts` must be expressed in a single fixed reference frame — the ROOT's side-to-move color — for the entire depth of the tree, never flipped per ply** (unlike a textbook negamax convention that negates at every ply). This falls directly out of SEED-082's own formulas (`V = Σ P(m)·V(child)`, no negation term) and D-06 ("practicalScore is expected score from the root side-to-move's perspective"). It means `leafScore.ts` must convert every leaf's Stockfish eval using the ROOT's color as the `mover` argument to `evalToExpectedScore()`, a constant carried through the whole search, NOT the leaf node's own side-to-move (which flips every ply). Getting this wrong produces a search that still "runs" and still ranks moves, but silently corrupts every value below ply 1 — exactly the kind of "looks done but isn't" bug this phase's SC1/SC2/SC3 fixture tests exist to catch, and it deserves its own explicit test, not just incidental coverage from the ELO-oracle or backup tests.

A second load-bearing, easily-missed correction: CONTEXT.md's D-08 asserts `maskAndSoftmax` (the existing Maia policy-masking utility in `frontend/src/lib/maiaEncoding.ts`) "already emits" UCI-keyed probabilities. Direct inspection shows it emits **SAN-keyed** probabilities (`probabilities[move.san] = ...`). D-08's decision to use UCI throughout the NEW core is still correct and should not change — it matches `grade()`'s existing pv[0]/UCI convention from `useStockfishGradingEngine.ts` — but Phase 153's fabricated test providers must not encode the false assumption that a real UCI-keyed policy already exists; that re-keying step is Phase 154's job, flagged here so it isn't silently "discovered" as a surprise later.

**Primary recommendation:** Build `backup.ts` and `select.ts` first, as pure functions with zero tree/orchestration awareness, verified against the hand-computed fixtures below before writing `mctsSearch.ts`'s traversal loop. This is the single highest-leverage sequencing choice available to the planner — it isolates the two hardest-to-debug failure modes (backup degeneration, ELO/frame confusion) into files that can be 100% unit-tested in isolation, exactly mirroring the "de-risk the novel piece first" build order already established in `.planning/research/ARCHITECTURE.md`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Search orchestration (selection/expansion/backup loop) | Browser / Client (pure lib) | — | FlawChess is a client-side SPA with no SSR tier; `lib/engine/` is deliberately worker-free and React-free pure TypeScript, executed on the main thread in later phases (per ARCHITECTURE.md Pattern 5) |
| Backup value computation | Browser / Client (pure lib) | — | Isolated pure function (`backup.ts`), zero I/O, the one piece of domain logic this milestone claims as novel |
| Candidate truncation/renormalization (Maia top-k) | Browser / Client (pure lib) | — | Pure math over a `Record<string, number>` input; no fetch, no DOM |
| Fabricated `EngineProviders` (test doubles) | Browser / Client (test-only) | — | In-memory stub tables (`Map`/object literals), no Worker, no network — exactly what makes this phase testable without WASM/ONNX |
| Real Stockfish/Maia providers | Browser / Client (Worker) | — | Explicitly OUT of scope for Phase 153 (Phase 154); noted only so the planner doesn't accidentally pull worker code in early |

## Standard Stack

### Core
No new libraries. The phase is 100% hand-rolled pure TypeScript over one already-installed dependency.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chess.js | 1.4.0 (already installed; `npm view chess.js version` confirms 1.4.0 is also latest on the registry) [VERIFIED: npm registry] | Legal move generation, child-FEN derivation, terminal-position detection (checkmate/stalemate/draw) inside the pure core | Already the project's sole chess-logic dependency (used by `maiaEncoding.ts`, `sanToSquares.ts`, `useStockfishGradingEngine.ts`); no reason to introduce a second chess library for one new subsystem |
| vitest | ^4.1.7 (existing) [VERIFIED: package.json] | Test runner for `lib/engine/__tests__/` | Already the project's only frontend test runner; zero new test infrastructure needed (CONTEXT.md code_context) |

### Supporting
None. No priority-queue library, no MCTS library, no worker-RPC wrapper — all explicitly rejected by prior milestone research (`.planning/research/SUMMARY.md`: "a plain array with linear max-scan suffices" at this node-budget scale).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled MCTS core | A generic MCTS npm package | None exist that support the non-standard chance-node/max-node hybrid backup rule this design requires (verified in prior milestone SUMMARY.md research) — a generic library would need to be bypassed for the one thing that matters, so it adds a dependency with no leverage |
| Plain array scan for node selection | `tinyqueue` or similar priority-queue package | Named only as a FUTURE option past ~1-2k pending nodes (Phase 154+ concern); at Phase 153's fabricated-provider node counts (a handful to a few hundred), a linear scan over children is simpler and equally fast |

**Installation:** None — no `npm install` needed for this phase.

**Version verification:** `chess.js` confirmed installed at `^1.4.0` in `frontend/package.json` and `npm view chess.js version` returns `1.4.0` (registry-current) [VERIFIED: npm registry]. `vitest` confirmed at `^4.1.7` in `frontend/package.json` [VERIFIED: package.json].

## Package Legitimacy Audit

No external packages are installed by this phase. `chess.js` is an EXISTING dependency (already vetted in prior phases — long-established package, `jhlywa/chess.js`, millions of weekly downloads, used throughout the codebase since before this milestone). No legitimacy check is required for a zero-new-dependency phase.

**Packages removed due to [SLOP] verdict:** none (no packages evaluated — none installed).
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
FEN + SearchBudget + EngineProviders (fabricated in tests)
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│ mctsSearch.ts (SearchRunner impl #1 — MCTS orchestrator)   │
│                                                             │
│   loop until nodesEvaluated >= budget.maxNodes:            │
│     1. select.ts: walk root→leaf via PUCT                  │
│        (root: Q+prior*explore; non-root: prior*explore     │
│         only — D-01), skipping in-flight/pending nodes     │
│     2. terminal check (chess.js isGameOver at this node)   │
│        → terminal leaf value, no expansion, back to step 4 │
│     3. expand: providers.policy(fen, elo[side], side)      │
│        → truncate/renormalize top-k (POLICY_MASS_THRESHOLD)│
│        → providers.grade(fen, ucis) batched over that set  │
│        → each child gets a leaf estimate via leafScore.ts  │
│          (root-color-relative, see below) until its OWN     │
│          subtree is expanded later                          │
│     4. backup.ts: propagate value root-ward                │
│        non-root = Σ prior_renorm · childValue (D-02, over  │
│          the FULL truncated set, expanded+unexpanded mixed) │
│        root = max(childValue)                              │
│     5. onSnapshot(EngineSnapshot) — every backup (D-10)     │
└───────────────────────┬─────────────────────────────────────┘
                         │ same EngineProviders/SearchBudget
                         ▼
┌───────────────────────────────────────────────────────────┐
│ fallbackExpectimax.ts (SearchRunner impl #2 — depth-limited)│
│   walks the full tree to budget.maxPlies uniformly,         │
│   calls the SAME backup.ts for its own value combination,   │
│   emits the SAME EngineSnapshot shape                       │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
EngineSnapshot { rankedLines: RankedLine[], nodesEvaluated, budgetExhausted }
        (consumed by Phase 155's hook — out of scope here)
```

A reader can trace one search from FEN-in to ranked-lines-out by following the loop: select picks a node → terminal-check short-circuits mate/stalemate leaves → expand queries the two fabricated providers → leafScore converts unexpanded children's shallow evals → backup propagates the mixed expanded/unexpanded set root-ward → snapshot emits. The fallback runner is a structurally separate `SearchRunner` implementation that reuses only `backup.ts`, entered exactly once per test to prove interface-swappability (SC5), never invoked from inside `mctsSearch.ts`.

### Recommended Project Structure
```
frontend/src/lib/engine/
├── types.ts                 # SearchBudget, EngineProviders, RankedLine, EngineSnapshot, MoveGrade (or reuse from moveQuality.ts — see note)
├── guardrail.ts             # SearchRunner type only — no logic
├── backup.ts                # the Maia-weighted expectimax backup rule (pure, most-tested file)
├── select.ts                # PUCT selection, canonical tie-break, virtual-visit/pending marking
├── leafScore.ts             # thin wrapper over lib/liveFlaw.ts's evalToExpectedScore — root-color-relative (see below)
├── mctsSearch.ts            # MCTS orchestrator implementing SearchRunner
├── fallbackExpectimax.ts    # depth-limited expectimax implementing SearchRunner, reuses backup.ts
└── __tests__/
    ├── backup.test.ts           # SC2 — hand-computed fixture, negative assertions
    ├── select.test.ts           # root-vs-non-root PUCT formula, canonical tie-break
    ├── leafScore.test.ts        # root-color-relative wiring, mate handling
    ├── mctsSearch.test.ts       # SC1/SC3/SC4/ENGINE-07 — fake-provider end-to-end, determinism
    └── fallbackExpectimax.test.ts  # SC5 — same-interface swap-in test
```

### Structure Rationale
Matches `.planning/research/ARCHITECTURE.md`'s recommended layout exactly, with two adjustments confirmed by this research: (1) no `maiaQueue.ts`/`workerPool.ts` in this phase (Phase 154 scope, correctly excluded per CONTEXT.md's phase boundary), and (2) `types.ts` needs an explicit decision on whether the core defines its own `MoveGrade` or imports `moveQuality.ts`'s existing `{evalCp, evalMate, depth}` shape (see "MoveGrade Reuse" below — recommend reuse).

### Pattern 1: Guardrail interface — position+budget→ranked lines, two interchangeable backends
**What:** A single `SearchRunner` type both `mctsSearch.ts` and `fallbackExpectimax.ts` implement identically:
```typescript
// lib/engine/guardrail.ts
export type SearchRunner = (
  rootFen: string,
  budget: SearchBudget,
  providers: EngineProviders,
  onSnapshot: (snapshot: EngineSnapshot) => void,
  signal: AbortSignal,
) => Promise<EngineSnapshot>;
```
**When to use:** The MCTS orchestrator and the fallback are never both invoked from the same call site conditionally — `useFlawChessEngine.ts` (Phase 155) imports exactly one. This phase's job is to prove BOTH satisfy the type and produce comparable output shape (SC5), not to wire the config switch.
**Example — `EngineProviders`/`SearchBudget`/`RankedLine` per the LOCKED decisions (D-04/D-06/D-07/D-08):**
```typescript
// lib/engine/types.ts
export type Side = 'w' | 'b';

/** Reused from moveQuality.ts's existing shape — see "MoveGrade Reuse" below. */
export interface MoveGrade { evalCp: number | null; evalMate: number | null; depth: number }

export interface EngineProviders {
  /** UCI-keyed Maia move-probability distribution at `elo`, full legal-move mass. */
  policy(fen: string, elo: number, side: Side): Promise<Record<string, number>>;
  /** UCI-keyed Stockfish shallow-eval grades for the candidate UCI moves, white-POV cp (matches existing MoveGrade convention). */
  grade(fen: string, candidateUcis: string[]): Promise<Map<string, MoveGrade>>;
}

export interface SearchBudget {
  maxNodes: number;               // D-09: one node = one expansion event
  elo: { w: number; b: number };  // D-07: color-keyed, not self/opponent-keyed
  maxPlies: number;                // 6-10, locked band (SEED-082)
  concurrency: number;             // D-03: >=1; ENGINE-07 suite runs at 1
  extraRootMoves?: string[];       // D-04: union with Maia top-k at root only
}

export interface RankedLine {
  rootMove: string;         // UCI (D-08)
  practicalScore: number;   // D-06: root-side-to-move expected score, 0-1
  objectiveEvalCp: number | null;
  modalPath: string[];      // UCI sequence
  visits: number;
}

export interface EngineSnapshot {
  rankedLines: RankedLine[];
  nodesEvaluated: number;
  budgetExhausted: boolean;
}
```

### Pattern 2: The backup rule as an isolated pure function — no visit-count leakage possible
**What:** `backup.ts` exports a function whose signature makes the Pitfall-3 bug (silently reverting to visit-count-weighted MCTS) structurally impossible: it takes prior probabilities as an explicit, separate array parameter that is NEVER derived from visit counts or child values.
```typescript
// lib/engine/backup.ts
export interface BackupChild {
  /** Renormalized Maia prior for this child at THIS node (D-02) — frozen at
   *  expansion time, never re-derived from visits or values. */
  prior: number;
  /** Either the child's own backed-up expectation (if expanded) or the
   *  parent-time sigmoid(shallowEval) leaf estimate (if not) — D-02. */
  value: number;
}

/** Non-root nodes: Maia-prior-weighted expectation over the FULL truncated set. */
export function backupExpectation(children: readonly BackupChild[]): number {
  const totalPrior = children.reduce((sum, c) => sum + c.prior, 0);
  if (totalPrior === 0) return 0.5; // degenerate guard, should not occur post-renormalization
  return children.reduce((sum, c) => sum + (c.prior / totalPrior) * c.value, 0);
}

/** Root only: max over candidate values (D-01's "exactly one max node"). */
export function backupRootMax(children: readonly BackupChild[]): number {
  return Math.max(...children.map((c) => c.value));
}
```
**When to use:** `backupExpectation` for every node except the root; `backupRootMax` for the root only, called from `mctsSearch.ts`'s (and `fallbackExpectimax.ts`'s) top-level backup step. `fallbackExpectimax.ts` imports both functions directly — this is the literal mechanism by which SC5's "reuses the same backup.ts" is satisfied.
**Trade-offs:** None significant. The interface makes it a code-review-visible fact that `prior` and `value` are supplied independently, closing the exact hole Pitfall 3 describes.

### Pattern 3: Root-relative score frame — no per-ply sign flip (NEW finding, not in prior research docs)
**What:** SEED-082's formula `V(node) = Σ P_maia(m) · V(child)` has NO negation term at any depth — unlike textbook negamax, values are never flipped to "the mover's perspective" per ply. Every value flowing through `backup.ts`, from leaf to root, must already be expressed in the SAME fixed reference frame: **the root position's side-to-move color**, constant for the entire search. This is what makes D-06's "`practicalScore` is expected score from the root side-to-move's perspective" true not just at the root but at every intermediate node feeding into it.

**Concretely:** `leafScore.ts` must NOT call `evalToExpectedScore(evalCp, evalMate, leafNodeMover)` (which would use the LEAF's own side-to-move, flipping sign every ply, exactly like a negamax value). It must call `evalToExpectedScore(evalCp, evalMate, rootMover)`, where `rootMover` is derived ONCE from the root FEN (`sideToMoveFromFen(rootFen)`, already exported by `liveFlaw.ts`) and threaded as a constant through the entire search — never recomputed per node.

```typescript
// lib/engine/leafScore.ts
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import type { MoveGrade } from './types';

/** Converts a leaf's white-POV Stockfish eval into root-relative expected score.
 *  `rootMover` MUST be the ROOT position's side to move, constant for the whole
 *  search — NOT the leaf node's own side to move (Pattern 3: no per-ply sign flip). */
export function leafExpectedScore(grade: MoveGrade, rootMover: MoverColor): number {
  return evalToExpectedScore(grade.evalCp, grade.evalMate, rootMover);
}
```
**When to use:** Every call site that converts a Stockfish `MoveGrade` into a value fed to `backup.ts`, at any depth. This is easy to get subtly wrong because the surrounding codebase's OWN existing convention (`useStockfishGradingEngine.ts`, `moveQuality.ts`) always passes the CURRENT mover (correct for THEIR use case — classifying a single ply's move quality — but wrong for this multi-ply expectimax accumulator). A naive port of that pattern into `lib/engine/` reintroduces a silent, MCTS-adjacent version of the classic side-to-move parity bug (structurally the same failure class as Pitfall 4, but affecting VALUES instead of ELO selection — test it separately).
**Trade-offs:** None — it's a one-parameter difference from the existing pattern, but the exact opposite parameter would compile and run without error, producing a plausible-looking but wrong search. This deserves its own fixture test (see "Root-Relative Frame Fixture" below), independent of the ELO-oracle test, because a reviewer checking "did we use the right ELO at each node" will not automatically also check "did we use the right MOVER for the sigmoid" — they are two different parameters threaded through two different functions (`policy()`'s `side` vs. `leafExpectedScore()`'s `rootMover`).

### Pattern 4: Truncation/renormalization as one shared utility (ENGINE-02, D-11)
**What:** A single function, called both at the root (for the `extraRootMoves`-unioned set) and at every deeper node (Maia-top-k only), implementing the ~90% cumulative-mass cut + renormalization:
```typescript
// lib/engine/select.ts (or a small internal helper — planner's discretion on file placement)
export const POLICY_MASS_THRESHOLD = 0.9; // D-11: separate from moveQuality.ts's 0.95

export function truncateAndRenormalize(policy: Record<string, number>): Map<string, number> {
  const sorted = Object.entries(policy).sort((a, b) => b[1] - a[1]);
  const kept: [string, number][] = [];
  let cumulative = 0;
  for (const [uci, prob] of sorted) {
    if (cumulative >= POLICY_MASS_THRESHOLD) break;
    kept.push([uci, prob]);
    cumulative += prob;
  }
  const total = kept.reduce((sum, [, p]) => sum + p, 0);
  return new Map(kept.map(([uci, p]) => [uci, total > 0 ? p / total : 0]));
}
```
**When to use:** Called once per expansion (root or non-root) on the raw `policy()` output, BEFORE the root-only prior-floor boost (D-05) is applied. The prior-floor boost is a SEPARATE, root-only transform layered on top (only affects the exploration term per D-05, never the renormalized values `backup.ts` consumes) — do not conflate the two into one function; they have different scopes (all nodes vs. root-only) and different consumers (backup values vs. PUCT exploration term).
**Trade-offs:** Mirrors `moveQuality.ts`'s `selectCandidatesByMass` cumulative-mass-cut PATTERN (loop, break on threshold, keep set) exactly, but with a different threshold constant and no hard cap (`CANDIDATE_HARD_CAP` is a display concern from a different module, not reused here per D-11's independent-tuning rationale) — do not import `moveQuality.ts`'s constant or its `CANDIDATE_HARD_CAP` into the engine core.

### Pattern 5: Buffer-then-apply-in-canonical-order (ENGINE-07 determinism)
**What:** At `concurrency > 1` (D-03's mandated `concurrency=2` test), multiple in-flight `grade()`/`policy()` calls can resolve in any order. To keep output deterministic, results must be buffered and applied to the tree in a canonical order (e.g., sorted by a stable node-id assigned at dispatch time, not insertion/arrival order) at each synchronization point — never applied to the tree in raw `Promise.race`/arrival order.
**When to use:** Inside `mctsSearch.ts`'s concurrency-aware loop (D-03). This is Pitfall 5 from the prior milestone research, directly applicable here since D-03 requires the `concurrency=2` test to prove determinism holds even with multiple expansions in flight.
**Trade-offs:** Slightly more bookkeeping (a pending-results buffer + a sort step) than naively applying whichever promise resolves first, but it is the ONLY way to satisfy ENGINE-07 once `concurrency > 1` is real (even with a deterministic FAKE provider whose promises may still resolve in whatever order the microtask queue happens to schedule them, unless the orchestration itself imposes order).

### Anti-Patterns to Avoid
- **Deriving `prior` from `value`, `visits`, or anything backup-produced:** the single bug this design's tests exist to catch (Pitfall 3). `backup.ts`'s `BackupChild.prior` must only ever be populated from a fresh `policy()` call's (truncated, renormalized) output.
- **Flipping the leaf-conversion `mover` argument per ply** (Pattern 3, this phase's own new finding): reusing `useStockfishGradingEngine.ts`'s "always convert with the CURRENT mover" convention inside `leafScore.ts` silently corrupts every backup value below ply 1.
- **Conflating the root prior-floor boost (D-05) with the universal mass-truncation (D-11):** they are different transforms, different scopes, different consumers — do not implement them as one function with an `isRoot` flag that branches internally in a way that makes it easy to accidentally apply the floor to backup values.
- **Depth-parity-based side-to-move inference** (`depth % 2`): always derive `side` from `fen.split(' ')[1]` (the existing project-wide convention, confirmed in `maiaEncoding.ts`, `useStockfishGradingEngine.ts`, `liveFlaw.ts`'s `sideToMoveFromFen`) at each node's OWN fen, never from ply count or root color parity — this is Pitfall 4, directly targeted by ENGINE-04's oracle test.
- **Applying worker-arrival order directly to the tree** once `concurrency > 1` — Pattern 5 above; breaks ENGINE-07 the moment D-03's `concurrency=2` test is written if not handled.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Eval → win% conversion (ENGINE-05) | A new sigmoid / new constant | `evalToExpectedScore()` in `frontend/src/lib/liveFlaw.ts` (already imports `LICHESS_K = 0.00368208` from the generated, backend-sourced `flawThresholds.ts`) | Verified: this is the EXACT lichess sigmoid SEED-082 calls for, already shipped, already unit-tested (`moveQuality.test.ts` exercises it), zero risk of drift from the backend's own copy |
| Legal move generation / child FEN derivation | Custom chess move-generation | `chess.js@1.4.0`, already a project dependency | Already used identically by `maiaEncoding.ts` (`chess.moves({verbose:true})`), `sanToSquares.ts`; no reason for a second implementation |
| UCI move parsing (from/to/promotion) | A regex/string-slicing helper from scratch | `uciToSquares()` in `frontend/src/lib/sanToSquares.ts` | Already exists, already handles the 4-vs-5-char (promotion) case, already used by the grading hook |
| Mass-truncation loop shape | A new "take until threshold" utility from scratch | The exact loop SHAPE (not the constant) from `moveQuality.ts`'s `selectCandidatesByMass` | Proven, reviewed pattern; only the threshold constant and the "no hard cap" behavior differ (D-11) |

**Key insight:** Every numerical primitive this phase needs (sigmoid, UCI parsing, legal-move enumeration, mass-truncation shape) already exists and is already unit-tested elsewhere in this codebase. The ENTIRE new-code surface of Phase 153 is the two things SEED-082 calls genuinely novel — the backup rule and the asymmetric ELO/root-relative-frame plumbing — plus the orchestration loop that ties them together. Do not let `mctsSearch.ts` accumulate incidental reimplementations of any of the above; import them.

## Common Pitfalls

### Pitfall 1: Backup rule silently degenerates to textbook MCTS (Pitfall 3 in prior milestone research)
**What goes wrong:** `backupExpectation` gets accidentally written to weight by visit count instead of (or blended with) the frozen Maia prior.
**Why it happens:** Every textbook MCTS reference implementation backs up via visit-count-weighted averages; this design intentionally diverges, making a "looks like MCTS so behaves like MCTS" copy-adaptation trap likely.
**How to avoid:** The `BackupChild.prior`/`value` interface (Pattern 2) structurally prevents deriving `prior` from anything backup-produced. Enforce with the negative-assertion fixture below.
**Warning signs:** Backup output happens to equal `children.reduce((s,c)=>s+c.value,0)/children.length` (naive average) or only reflects the most-visited child's value.

### Pitfall 2: Root-relative score frame flipped per ply (NEW — this phase's own finding, see Pattern 3)
**What goes wrong:** `leafScore.ts` converts each leaf using ITS OWN side-to-move as the `mover` argument (matching the rest of the codebase's convention for single-ply move classification), silently negating the practical-score contribution of every other ply.
**Why it happens:** The existing, correct-for-its-purpose convention in `useStockfishGradingEngine.ts`/`moveQuality.ts` (always convert relative to whoever is about to move) is the natural thing to copy, and it is subtly WRONG for this multi-ply accumulator, which needs a FIXED reference frame instead.
**How to avoid:** Thread `rootMover` as one constant, computed once from the root FEN, through the entire search; never recompute it per node. Write an explicit fixture (see below) with root=White and root=Black, each with at least 2 plies of alternation, asserting the SAME numeric leaf eval produces mirrored (not per-ply-flipping) contributions to the root's practical score.
**Warning signs:** A search where an objectively good line for the root player scores WORSE than a bad one specifically when the tree has an odd number of plies to a given leaf — a sign values are alternating sign by ply instead of staying root-relative.

### Pitfall 3: Asymmetric ELO crossed at the node level (Pitfall 4 in prior milestone research)
**What goes wrong:** ELO selection derived from ply/depth parity instead of the node's own FEN side-to-move field.
**Why it happens:** Side-to-move parity bugs are the most common chess-tree bug class; this project has already hit a related POV-sign bug once (`useStockfishGradingEngine.ts`'s white-POV normalization fix).
**How to avoid:** `side = fen.split(' ')[1] === 'b' ? 'b' : 'w'` computed at EACH node's own fen (matching the existing project-wide idiom), never from depth parity. Cover both root colors in the oracle test (see below).
**Warning signs:** The engine's practical score for a strong player analyzing a weak opponent's win looks worse than expected, or vice versa.

### Pitfall 4: Non-determinism from scheduling/arrival order despite "no Dirichlet noise" (Pitfall 5 in prior milestone research)
**What goes wrong:** `Map`/object iteration order, or raw worker/promise arrival order, leaks into tie-breaking or backup-application order.
**Why it happens:** "No randomness in RNG calls" is necessary but not sufficient once async concurrency (D-03) is real.
**How to avoid:** Canonical UCI-string sort for every tie-break (D-01); buffer-then-apply-in-canonical-order for concurrent results (Pattern 5). Test with a stubbed, deterministic provider under both `concurrency=1` and `concurrency=2` and assert bit-identical output across repeated runs.
**Warning signs:** A determinism test that passes at `concurrency=1` but flakes at `concurrency=2`.

### Pitfall 5: `multipv`-as-identity landmine reintroduced (Pitfall 6 in prior milestone research)
**What goes wrong:** Any new code parsing UCI `info` lines keys results by `multipv` rank instead of `pv[0]`.
**Why it happens:** `info depth N multipv K pv <move>` naturally reads like "K identifies the line."
**How to avoid:** Not directly applicable to Phase 153 itself — this phase's fabricated `EngineProviders` never parse raw UCI `info` lines (that's the real `workerPool.ts` adapter, Phase 154). Flagged here only so the planner does NOT introduce a UCI-line-parsing helper inside `lib/engine/` prematurely; if a test helper simulates raw engine output for realism, it must reuse `parseInfoLine` from `frontend/src/hooks/uciParser.ts` (already pv[0]-keyed) rather than inventing a second parser.
**Warning signs:** A new `parseInfoLine`-shaped function inside `lib/engine/` not importing the existing one.

### Pitfall 6: Terminal positions treated as ordinary expansion nodes
**What goes wrong:** A node that is checkmate/stalemate/insufficient-material has NO legal moves, so calling `policy()`/`grade()` on it either errors or returns an empty/degenerate distribution that then corrupts `backupExpectation`'s renormalization (`totalPrior === 0`).
**Why it happens:** The depth cutoff (6-10 plies) is the ONLY termination condition SEED-082's prose emphasizes; forced mates/stalemates reachable before that depth are an edge case easy to omit from the initial implementation.
**How to avoid:** Before expanding any node (root or not), check `chess.isGameOver()` (or the more granular `isCheckmate()`/`isStalemate()`/`isInsufficientMaterial()`/`isThreefoldRepetition()`/`isDraw()`) on that node's FEN via `chess.js`. If true, treat it as a leaf with a fixed terminal value (root-relative, per Pattern 3) — checkmate: 1.0 if the checkmated side is NOT `rootMover`, 0.0 if it IS; stalemate/draw: 0.5 — and never call `policy()`/`grade()` for it. This is Claude's-discretion territory per CONTEXT.md, but the mechanism (check before expand, short-circuit to a fixed value, never call providers on a position with no legal moves) is not optional — providers WILL be called with degenerate input otherwise.
**Warning signs:** A fixture position one ply from checkmate producing `NaN`/`0.5`-by-accident (division by zero in `backupExpectation`'s `totalPrior` guard) instead of a confident 1.0/0.0.

## Code Examples

### Backup Rule: Worked Fixture (ENGINE-03 / SC2)
The following hand-computed example is the recommended shape for `backup.test.ts`'s primary fixture. It deliberately mixes one expanded child (with its own backed-up value) and two unexpanded children (parent-time sigmoid estimates only), per D-02's explicit requirement:

```
Node N (non-root), truncated Maia top-k, 3 children after renormalization:
  child A: prior = 0.6, EXPANDED, its own subtree backed up to value = 0.72
  child B: prior = 0.3, NOT expanded, leaf estimate (sigmoid(shallowEval)) = 0.55
  child C: prior = 0.1, NOT expanded, leaf estimate = 0.40

Correct backupExpectation(N) = 0.6*0.72 + 0.3*0.55 + 0.1*0.40
                              = 0.432 + 0.165 + 0.040
                              = 0.637

Negative assertion #1 (naive average, IGNORES priors):
  (0.72 + 0.55 + 0.40) / 3 = 0.5567 ≠ 0.637  ← must NOT equal this

Negative assertion #2 (visit-count-weighted, the textbook-MCTS degeneration):
  if only child A has visits > 0 (n_A=8, n_B=0, n_C=0 — realistic for a
  wide, shallow-visited node), a visit-weighted average collapses to just
  child A's value = 0.72 ≠ 0.637  ← must NOT equal this either
```
Root-level companion fixture (D-01's "exactly one max node"):
```
Root, 2 candidates after the D-04 union + D-05 floor (floor affects ONLY the
PUCT exploration term, not these values — see Pattern 4):
  candidate 1: value = 0.60 (its own expanded subtree's backupExpectation)
  candidate 2: value = 0.66 (a not-yet-expanded root child's leaf estimate)

Correct backupRootMax(root) = max(0.60, 0.66) = 0.66

Negative assertion: Σ prior·value (the non-root formula applied by mistake)
  must NOT be the root's value — assert root uses backupRootMax, not
  backupExpectation, via a distinct test case (the "root-vs-non-root branch"
  pitfall from prior research, Pitfall 3's second sub-bug).
```

### ELO Oracle Fixture (ENGINE-04 / SC3)
```typescript
// A recording fake policy() that captures every (fen, elo, side) call.
const calls: Array<{ fen: string; elo: number; side: Side }> = [];
const fakePolicy: EngineProviders['policy'] = async (fen, elo, side) => {
  calls.push({ fen, elo, side });
  return { /* fixed fabricated distribution */ };
};

// Run a small fixed-depth search (2-3 plies) from a WHITE-to-move root, then
// again from a BLACK-to-move root (e.g. the position after 1.e4), with
// budget.elo = { w: 1500, b: 1800 }. Assert per recorded call:
//   side === 'w'  => elo === 1500
//   side === 'b'  => elo === 1800
// for BOTH root-color runs — proving elo selection is keyed on the NODE's
// own fen side-to-move, not on root color or ply parity.
```

### Root-Relative Frame Fixture (Pattern 3 / Pitfall 2 above)
```typescript
// Root = White to move. A 2-ply line (White's candidate, then Black's forced
// reply) where the LEAF (after Black's reply) has a fixed white-POV eval,
// e.g. evalCp = +200 (White is better).
//
// leafExpectedScore(grade, rootMover='white') must return
//   evalToExpectedScore(200, null, 'white') — a value > 0.5 (good for White,
//   the root player) — REGARDLESS of the fact that it is Black who is "to
//   move" conceptually at the point this eval was recorded (the eval itself
//   is already white-POV per the existing MoveGrade convention, so no sign
//   flip is needed at all here — the bug this fixture catches is a caller
//   erroneously computing `evalToExpectedScore(200, null, 'black')`, which
//   would flip it below 0.5 and corrupt the backup).
//
// Companion case: root = Black to move, same white-POV +200 leaf eval.
// leafExpectedScore(grade, rootMover='black') must return a value < 0.5
// (bad for Black, the root player) — evalToExpectedScore already handles
// the sign flip correctly for THIS single conversion; the fixture's real
// job is proving `rootMover` is threaded as a CONSTANT and never swapped
// mid-search when the actual side-to-move changes at deeper plies.
```

### Guardrail Swap-in (ENGINE-06 / SC5)
```typescript
// Same providers, same budget, same rootFen — only the SearchRunner differs.
const resultMcts = await mctsSearch(rootFen, budget, providers, onSnapshot, signal);
const resultFallback = await fallbackExpectimax(rootFen, budget, providers, onSnapshot, signal);
// Both satisfy `Promise<EngineSnapshot>` with no call-site changes — the
// literal assertion is "this compiles and runs with the SearchRunner type,
// unmodified" plus a structural sanity check (both return a non-empty
// rankedLines array for the same fabricated providers).
```

## MoveGrade Reuse

`moveQuality.ts` already exports `MoveGrade { evalCp: number | null; evalMate: number | null; depth: number }`, white-POV normalized, exactly matching what `grade()` needs to return under D-08. Recommend `lib/engine/types.ts` import and re-export this type (or a type-identical alias) rather than declaring a structurally-duplicate interface — CONTEXT.md's code_context explicitly flags "the `MoveGrade` shape should stay compatible" with the existing hook's output. A duplicate-but-compatible interface works too (structural typing means either compiles), but a shared type avoids drift if `moveQuality.ts`'s shape changes later. This is Claude's-discretion territory (mate-score representation) — the existing shape already carries `evalMate` as a signed mate-in-N (matching `ParsedInfoLine.scoreMate`'s convention: positive=winning, negative=losing, from the SAME white-POV frame `evalCp` uses) and `evalToExpectedScore` already knows how to consume it (maps to ±`MATE_CP_EQUIVALENT` before the sigmoid) — no new mate-handling logic is needed in `leafScore.ts` beyond passing `grade.evalMate` through unchanged.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| N/A — this is new subsystem | N/A | — | No existing FlawChess code does anything like this; nothing is being replaced |

**Deprecated/outdated:** None applicable — greenfield subsystem.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `MoveGrade`'s `evalMate` sign convention (positive=winning from white's POV) is safe to pass through `evalToExpectedScore` unchanged for leaf conversion, with no additional mate-specific handling in `leafScore.ts` | MoveGrade Reuse | LOW — `evalToExpectedScore`'s existing mate-handling is already unit-tested (`moveQuality.test.ts`) and used identically elsewhere; if wrong, the fix is localized to `leafScore.ts` |
| A2 | A linear array scan is fast enough for node/child selection at Phase 153's fabricated-provider test scale (a few dozen nodes per test) and does not need a priority-queue data structure yet | Standard Stack (Alternatives Considered) | LOW — this is explicitly a Phase 154+ concern per prior milestone SUMMARY.md research; if wrong, it's a Phase 154 performance finding, not a Phase 153 correctness issue |
| A3 | The recommended numeric fixture values (0.6/0.3/0.1 priors, 0.72/0.55/0.40 values) are illustrative only — the actual PLAN/executor may choose different numbers as long as the same qualitative property (expectation over the full truncated set, differs from both naive-average and visit-weighted-average) is preserved | Code Examples (Backup Rule Worked Fixture) | LOW — these are suggested test data, not a locked requirement; SC2's actual requirement is the property, not these exact numbers |

**If this table is empty:** N/A — see above; all three assumptions are LOW-risk implementation-detail suggestions, not disputed facts. No claim above concerns compliance, retention, or security posture.

## Open Questions (RESOLVED)

1. **Where does `truncateAndRenormalize` (Pattern 4) live — `select.ts` or a new small module?** *(RESOLVED: plan 153-03 places it in `select.ts`.)*
   - What we know: it's used both by root expansion (unioned with `extraRootMoves`, then floor-boosted for PUCT only) and by every non-root expansion (Maia-top-k only).
   - What's unclear: whether it belongs in `select.ts` (since PUCT consumes its output) or should be a standalone file for independent unit-testing.
   - Recommendation: planner's discretion; either is fine given it's a pure function either way — the important constraint (do not conflate with the D-05 root-floor boost, Pattern 4) holds regardless of file placement.

2. **Does `fallbackExpectimax.ts` need its own truncation/ELO/root-frame logic, or does it fully delegate to shared helpers?** *(RESOLVED: plan 153-05 requires it to import `leafScore.ts` and `truncateAndRenormalize`, not just `backup.ts`.)*
   - What we know: SC5 only requires it to reuse `backup.ts` and implement the identical `SearchRunner`; CONTEXT.md leaves its internals to Claude's discretion.
   - What's unclear: whether `leafScore.ts`'s root-relative-frame requirement (Pattern 3, this phase's own finding) applies equally to the fallback — it does, since both runners feed the same `backup.ts` and must produce comparable `practicalScore` semantics.
   - Recommendation: the planner should explicitly require `fallbackExpectimax.ts` to ALSO import `leafScore.ts`/`truncateAndRenormalize` (not just `backup.ts`) — otherwise the fallback could accidentally implement its own, inconsistent leaf-conversion logic and violate D-06's score-semantics contract silently.

## Environment Availability

Skipped — this phase has no external dependencies beyond the already-installed `chess.js`/`vitest`, both confirmed present. No new tools, services, or runtimes to probe.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest ^4.1.7 (existing, `frontend/package.json`) |
| Config file | `frontend/vite.config.ts` (no dedicated `test:` block found — vitest runs with its defaults; individual test files opt into `jsdom` via a `// @vitest-environment jsdom` pragma when needed. `lib/engine/__tests__/` is pure logic with no DOM — no pragma needed, runs under vitest's default `node` environment) |
| Quick run command | `cd frontend && npx vitest run src/lib/engine/__tests__/` |
| Full suite command | `cd frontend && npm test` (`vitest run`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENGINE-01 | Ranked root lines from a fixed FEN/budget/fabricated providers | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts` | ❌ Wave 0 |
| ENGINE-02 | Truncation/renormalization at ~90% mass | unit | `npx vitest run src/lib/engine/__tests__/select.test.ts` | ❌ Wave 0 |
| ENGINE-03 | Backup expectation ≠ naive avg, ≠ visit-weighted avg; root=max | unit | `npx vitest run src/lib/engine/__tests__/backup.test.ts` | ❌ Wave 0 |
| ENGINE-04 | ELO-oracle per-node-color-keyed selection, both root colors | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts` (or a dedicated `eloOracle.test.ts`) | ❌ Wave 0 |
| ENGINE-05 | Leaf sigmoid conversion, root-relative frame | unit | `npx vitest run src/lib/engine/__tests__/leafScore.test.ts` | ❌ Wave 0 |
| ENGINE-06 | Fallback swap-in behind identical interface | unit | `npx vitest run src/lib/engine/__tests__/fallbackExpectimax.test.ts` | ❌ Wave 0 |
| ENGINE-07 | Bit-identical repeated-run output, concurrency=1 and =2 | unit | `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the relevant single test file (`npx vitest run <file>`)
- **Per wave merge:** `cd frontend && npm test` (full frontend suite — fast, no workers/DOM in this phase's new tests)
- **Phase gate:** full suite green + `npm run lint` + `npx tsc -b` (per CLAUDE.md's frontend rules: `noUncheckedIndexedAccess`, knip dead-export detection) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/lib/engine/__tests__/` directory + all 5 test files listed above — net-new, no existing test infrastructure gap otherwise (vitest, TS config, and every reused primitive already has its own passing test suite)
- [ ] No new fixtures/conftest-equivalent needed — vitest test files are self-contained per this project's existing convention (see `moveQuality.test.ts`, `useStockfishGradingEngine.test.ts` for the established fabricated-input style)

*(Framework itself needs no install — vitest is already configured and running for 40+ existing frontend test files.)*

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json`, so this section is included per protocol. However, Phase 153 is a pure, offline, worker-free, network-free computation module (no fetch, no persistence, no user-facing input surface, no auth) — most ASVS categories are not applicable to THIS phase specifically; they become relevant once Phase 154 (real workers/network-adjacent WASM loading) and Phase 155 (React/user input) land.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth surface in this phase |
| V3 Session Management | No | No session/state persistence in this phase |
| V4 Access Control | No | No access-controlled resource in this phase |
| V5 Input Validation | Partial | `chess.js` already throws/rejects on malformed FEN and illegal moves (used defensively elsewhere, e.g. `sanToSquares.ts`'s try/catch-return-null style); fabricated test providers are trusted test doubles, not an external input surface — no NEW validation code is needed in this phase, but functions accepting a `fen: string` parameter should not assume it is well-formed if this core is ever called with a user-supplied/URL-derived FEN in a later phase (Phase 155's free-analysis surface) |
| V6 Cryptography | No | No cryptographic operation in this phase |

### Known Threat Patterns for this stack
Not applicable at this phase's scope (no network, no persistence, no auth, no rendered HTML). The one forward-looking note: this phase's `EngineProviders` interface will, in Phase 154, be backed by real Web Workers loading vendored WASM/ONNX binaries — CLAUDE.md's existing supply-chain discipline (SHA-256 verification, already applied to the server-side Stockfish binary) should extend to those client-vendored assets, but that is explicitly Phase 154 scope, not this phase's.

## Sources

### Primary (HIGH confidence)
- `.planning/phases/153-pure-search-core-guardrail-backup-mcts-fallback/153-CONTEXT.md` — locked D-01 through D-11 decisions (this phase's authoritative scope)
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` (referenced), `.planning/STATE.md` — requirement text, phase traceability, project state
- `.planning/seeds/SEED-082-human-playable-line-engine.md` — the locked algorithm formulas (backup rule, no-negation V(child) sum, root=max)
- Direct codebase reads (this session): `frontend/src/lib/liveFlaw.ts` (`evalToExpectedScore`, `sideToMoveFromFen`), `frontend/src/lib/maiaEncoding.ts` (`maskAndSoftmax` — confirmed SAN-keyed, correcting D-08's premise), `frontend/src/lib/moveQuality.ts` (`MoveGrade`, `selectCandidatesByMass`, `CUMULATIVE_MASS_THRESHOLD`), `frontend/src/hooks/useStockfishGradingEngine.ts` (grade/pv[0] protocol, white-POV normalization), `frontend/src/hooks/uciParser.ts` (`parseInfoLine`, `parseBestmove`), `frontend/src/lib/sanToSquares.ts` (`uciToSquares`, `sanToUci`), `frontend/src/generated/flawThresholds.ts` (confirmed `LICHESS_K = 0.00368208` already exists, generated from backend), `frontend/vite.config.ts`, `frontend/knip.json`, `frontend/tsconfig.app.json` (`noUncheckedIndexedAccess`), `frontend/package.json` (chess.js/vitest/knip versions), `frontend/src/lib/__tests__/moveQuality.test.ts` (established fixture-test style)
- `npm view chess.js version` (registry check, 2026-07-05) [VERIFIED: npm registry]

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md`, `.planning/research/SUMMARY.md`, `.planning/research/PITFALLS.md` — prior milestone-level research (module layout, build order, pitfall catalogue); this phase's research supersedes their example interfaces per D-08 and adds the root-relative-frame finding they did not surface

### Tertiary (LOW confidence)
None — no unverified web sources were needed for this phase; it is entirely a codebase-integration + locked-decision-implementation research task.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, existing versions verified via `npm view` and `package.json`
- Architecture: HIGH — directly derived from locked CONTEXT.md decisions + verified codebase primitives; the one new finding (root-relative frame) follows deductively from the locked SEED-082 formula, not speculation
- Pitfalls: HIGH — five of six pitfalls are carried forward (with Phase-153-specific scoping) from the already-adversarially-researched prior milestone PITFALLS.md; the sixth (root-relative frame) is newly derived this session directly from the locked math

**Research date:** 2026-07-05
**Valid until:** No external dependency to go stale; re-verify only if CONTEXT.md's locked decisions (D-01 through D-11) change, or if Phase 154 research reveals `maskAndSoftmax`'s actual SAN-keyed output requires a different re-keying approach than assumed here.
