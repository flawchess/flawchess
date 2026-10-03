/**
 * mctsSearch — the primary `SearchRunner` orchestrator: select -> terminal
 * check -> expand -> backup -> snapshot (ENGINE-01/02/04/05/07).
 *
 * Composes the Plan 01-03 primitives (`leafScore.ts`, `backup.ts`,
 * `select.ts`) plus the shared tree helpers (`treeCommon.ts`, WR-06) into
 * the frozen `SearchRunner` contract from `guardrail.ts`.
 * Two correctness invariants are structural, not incidental, in this file:
 *
 *   - D-07 / ENGINE-04: every `providers.policy()` call's `elo`/`side` are
 *     derived from the CURRENT node's own fen side-to-move field
 *     (`fen.split(' ')[1]`), never from depth/ply parity.
 *   - Root-relative frame (153-01/153-RESEARCH.md Pattern 3): `rootMover` is
 *     computed exactly once via `sideToMoveFromFen(rootFen)` and threaded as
 *     a constant into every `leafExpectedScore()` call — never recomputed
 *     per node.
 *
 * D-09: one "node" = one expansion event (one `policy()` call + one batched
 * `grade()` call); `nodesEvaluated` increments once per expansion, never for
 * a terminal/depth-capped dead end (Pitfall 6 — those never call providers
 * at all). D-10: `onSnapshot` fires after EVERY completed backup; no
 * `Date.now()`/`performance.now()` anywhere in this file. D-03/D-04: root
 * children are Maia top-k unioned with `budget.extraRootMoves`, AFTER
 * truncation, so a near-zero-Maia-probability Stockfish candidate is never
 * dropped by the mass cut — AND (INJECT-01, 196-01) `applyRootCandidateHardCap`
 * receives the union's own added UCIs as an exemption set, so that same
 * candidate is never dropped by the root hard cap either. Before Phase 196
 * this second mechanism was NOT honoured: an injected candidate was seeded
 * with prior 0, sorted dead last by the cap's own comparator, and was the
 * cap's first casualty whenever the root exceeded it — the union survived
 * the mass cut but silently lost to the hard cap. And, at `concurrency > 1`,
 * multiple expansions are in flight at once. Each selected leaf is marked
 * `isPending` — the gate that keeps a later selection from re-picking it
 * while it is in flight (the infinite-penalty limit of virtual loss); visit
 * counts increment only at APPLY time, so intermediate `onSnapshot` counts
 * never depend on how many expansions were dispatched together. SEED-170
 * item 2 (D-06/D-07): an INTERIOR node whose only children are pending (or
 * closed) is not simply skipped in place — it is marked `isBlocked` for the
 * rest of the current FILL PASS (one round's fill in round mode, one
 * synchronous top-up in continuous mode) and the walk restarts from the
 * root, so a peaked non-root policy that collapses one subtree to a single
 * live child no longer starves every OTHER subtree's dispatch slot.
 *
 * Two dispatch loops share `selectPath`, `dispatchExpansion`,
 * `applyAndReport` (the one apply call site) and `stopRuleSatisfied`;
 * `SearchBudget.dispatchMode` picks between them (Phase 227 D-13):
 *
 *   - ROUND (`'round'` or omitted): fill up to `concurrency` expansions,
 *     `Promise.all`, then apply them strictly in their canonical dispatch
 *     order — Promise.all's order-preserving resolution, never raw
 *     promise-arrival order (Pattern 5).
 *   - CONTINUOUS (`'continuous'`, `runContinuousLoop`): keep up to
 *     `concurrency` expansions in flight and refill as each settles — fill
 *     (synchronous top-up), await exactly one wake, drain every settled
 *     result in ARRIVAL order. No round barrier, so Maia and Stockfish
 *     overlap (SEED-171 item 5). Its invariants are argued and reviewed in
 *     `reports/continuous-dispatch-227/design.md` and guarded by
 *     `mctsSearch.continuous.test.ts`: (a) block flags are scoped to one
 *     fill pass and cleared in a `finally`; (b) `nodesEvaluated + inFlight
 *     <= maxNodes` at all times (D-10); (c) at `concurrency = 1` the output
 *     is byte-identical to round mode; (d) no result is ever applied after
 *     abort or early stop, and an inner AbortController cancels in-flight
 *     grades and queued Maia requests when the loop exits (D-09); (e) no
 *     missing wakeup (a settled queue plus a single-shot wake, the check and
 *     the wake assignment in one synchronous run); a rejected provider call
 *     propagates after its siblings are cancelled (Y-8).
 *
 * Determinism scope (ENGINE-07/D-03, Phase 227 D-11): ROUND mode with
 * deterministic providers is bit-identical across repeated runs at the same
 * `budget.concurrency`, regardless of provider resolution jitter. CONTINUOUS
 * mode is NOT: it applies results in arrival order, so under the relaxed,
 * statistical contract (Phase 226 D-05 read through D-01) the tree depends on
 * provider timing whenever `concurrency > 1`; it is judged against d20 truth,
 * not by identity. Different concurrency levels may legitimately build
 * DIFFERENT trees in either mode: at c=1 the second selection happens AFTER
 * the first expansion is applied (it sees the backed-up value and may
 * re-descend the same subtree), while at c>1 pending-exclusion forces
 * concurrent selections onto different nodes. A c=1 vs c=2 output difference
 * is therefore NOT a bug — do not attempt to equalize the two levels.
 *
 * Phase 226 D-18/D-08: when a provider supplies `gradeRoot`, the root's one
 * grade call is routed to it instead of `grade` (see `dispatchExpansion`'s
 * provider-selection line) so a caller can fan that single call out across
 * multiple idle workers/engines below the `EngineProviders` boundary — this
 * file never sees the fan-out itself. Because the fan-out's shard count is
 * bounded by how many workers/engines are free/exist, any reproducibility
 * claim for a `gradeRoot`-splitting run (round mode over deterministic
 * providers; continuous mode at c>1 makes no identity claim at all, see
 * "Determinism scope") is scoped per (concurrency, pool size) pair, not
 * concurrency alone — the same `budget.concurrency` against two different
 * pool sizes may legitimately split the root grade into a different number
 * of shards.
 */

import { sideToMoveFromFen, type MoverColor } from '@/lib/liveFlaw';
import type { SearchBudget, EngineProviders, EngineSnapshot, MoveGrade, BotStopRule } from './types';
import type { SearchRunner } from './guardrail';
import { truncateAndRenormalize, rootExplorationPriors, selectChild, type SelectionChild } from './select';
import { leafExpectedScore } from './leafScore';
import { DEFAULT_POLICY_TEMPERATURE, applyPolicyTemperature } from './policyTemperature';
import { gradingDepthForTreeDepth } from './gradingLadder';

/**
 * Local, non-exported widening of `EngineProviders.grade` used ONLY at the
 * `dispatchExpansion` call site below, so the frozen 3-param `types.ts`
 * interface (Phase 153) stays byte-unchanged while the resolved ladder rung
 * (LADDER-02) still reaches any concrete provider — `WorkerPool.grade` — that
 * accepts it. A function typed against `EngineProviders` cannot be CALLED
 * with a 4th argument even though a 4-optional-param implementation is
 * structurally ASSIGNABLE to that interface (Phase 194's `signal` precedent
 * one param further); this cast bridges exactly that gap without touching
 * the shared contract.
 */
type GradeWithLadderDepth = (
  fen: string,
  candidateUcis: string[],
  signal?: AbortSignal,
  gradingDepth?: number,
) => Promise<Map<string, MoveGrade>>;
import {
  NEUTRAL_EXPECTED_SCORE,
  type SearchTreeNode,
  fenSide,
  terminalValue,
  expandChildPositions,
  recomputeValue,
  buildSnapshot,
  sideMatchesMover,
  applyRootCandidateHardCap,
  mergeExtraRootMoves,
} from './treeCommon';

/**
 * One node in the search tree. Mutable — the orchestrator's private state.
 * Extends the shared node shape (`treeCommon.ts`, WR-06) with the fields
 * only THIS strategy needs: pending/closure bookkeeping and the root-only
 * floor-boosted exploration prior.
 */
interface EngineNode extends SearchTreeNode<EngineNode> {
  /** True while this node is selected-but-not-yet-applied, i.e. its expansion is in flight (virtual visit). */
  isPending: boolean;
  /**
   * True once this node can never yield another expansion: terminal,
   * depth-capped, or expanded with every child closed (WR-01 fix). Closure is
   * detected structurally and propagated root-ward the moment it happens —
   * previously a fully closed (sub)tree was only discovered by retrying
   * dead-end selection walks up to a 1000-attempt cap, each walk bumping
   * `visits` along its path, inflating RankedLine.visits by up to 3 orders
   * of magnitude and corrupting modalPath's most-visited-child choice.
   */
  isClosed: boolean;
  /**
   * True while this non-root node is blocked for the REST OF THE CURRENT
   * FILL PASS only (SEED-170 item 2, D-06/D-07): set when a walk reaches it
   * and finds zero selectable children (every child pending or closed), so
   * a later walk in the same pass restarts from the root instead of giving
   * up on the whole pass. A pass is one round's fill in round mode and one
   * synchronous top-up (`fillContinuous`) in continuous mode. Deliberately
   * a SEPARATE flag from `isPending` — that one means "dispatched, in
   * flight" and is read and reset at apply time (`applyExpansion`), which
   * runs BETWEEN passes, so a block can be stale by the next pass and must
   * be cleared at the end of every pass (design 2.2, Lemma 2). `isBlocked`
   * is read only by `selectPath` and cleared in bulk right after the fill
   * loop (round: before `Promise.all`; continuous: in a `finally`). Always
   * false outside an active fill loop.
   */
  isBlocked: boolean;
  /** Root-only floor-boosted exploration prior (D-05) — meaningful only when this node is a direct child of root. */
  rootExplorationPrior: number;
}

function createRoot(rootFen: string, rootMover: MoverColor): EngineNode {
  const node: EngineNode = {
    fen: rootFen,
    side: fenSide(rootFen),
    depth: 0,
    isRoot: true,
    uci: null,
    prior: 1,
    value: NEUTRAL_EXPECTED_SCORE,
    visits: 0,
    isPending: false,
    isTerminal: false,
    isExpanded: false,
    isClosed: false,
    isBlocked: false,
    objectiveEvalCp: null,
    objectiveEvalMate: null,
    rawMaiaProb: null,
    rootExplorationPrior: 0,
    children: new Map(),
  };
  const terminal = terminalValue(rootFen, rootMover);
  if (terminal !== null) {
    node.isTerminal = true;
    node.isExpanded = true;
    node.isClosed = true;
    node.value = terminal;
  }
  return node;
}

function createChildNode(
  fen: string,
  depth: number,
  uci: string,
  prior: number,
  value: number,
  objectiveEvalCp: number | null,
  objectiveEvalMate: number | null,
  rawMaiaProb: number | null,
  terminal: number | null,
): EngineNode {
  const node: EngineNode = {
    fen,
    side: fenSide(fen),
    depth,
    isRoot: false,
    uci,
    prior,
    value,
    visits: 0,
    isPending: false,
    isTerminal: false,
    isExpanded: false,
    isClosed: false,
    isBlocked: false,
    objectiveEvalCp,
    objectiveEvalMate,
    rawMaiaProb,
    rootExplorationPrior: 0,
    children: new Map(),
  };
  if (terminal !== null) {
    node.isTerminal = true;
    node.isExpanded = true;
    node.isClosed = true;
    node.value = terminal;
  }
  return node;
}

/** True when every child of `node` is closed (vacuously true for a childless node). */
function allChildrenClosed(node: EngineNode): boolean {
  for (const child of node.children.values()) {
    if (!child.isClosed) return false;
  }
  return true;
}

/**
 * Root-children value extremes the stop-rule check needs (Phase 168.5
 * D-05/D-06, extended Phase 225 D-01/D-02): reads `root.children`'s own
 * `.value` fields directly — the same values `treeCommon.ts`'s
 * `buildRankedLines` surfaces as `RankedLine.practicalScore` — never the
 * findability-sorted `rankScore` (Pattern 2). Returns null when root has no
 * children yet (nothing to evaluate). `runnerUpValue` is `-Infinity` when
 * there is only one child, so a single-candidate root trivially satisfies
 * the clear-winner margin.
 *
 * `settled` (per entry) is `visits >= 1 || isClosed` — deliberately NOT
 * `isTerminal`. A closed root child (terminal, or degenerate-empty-candidate
 * WR-04 close) is filtered out of `selectPath`'s candidate set and can never
 * receive a visit, so a visits-only settled test would stall a mate-in-1
 * root's clear-winner stop forever (RESEARCH Pitfall 1).
 *
 * `hasUnsettledInWindow` (Phase 225 D-01, single pass, in the SAME collection
 * loop above — never a second pass with different semantics) is true when
 * any entry — the top child included, its own gap being 0 — is unsettled AND
 * within `guardWindow` of the top's value. An unvisited child's own first
 * expansion can raise its value by roughly the opponent's expected error
 * (the "boost" — D-02 measures its typical size), so a child up to
 * `marginThreshold + rootGuardBoostAllowance` below the CURRENT top can still
 * overtake it once expanded; comparing it against the top before that happens
 * is exactly the root-comparability bug SEED-170 item 1 reports. This guard
 * only WITHHOLDS the clear-winner stop until every in-window child settles —
 * it never corrects, blends, or otherwise touches any `.value`.
 */
function rootChildValueExtremes(
  root: EngineNode,
  guardWindow: number,
): {
  argmaxUci: string;
  topValue: number;
  runnerUpValue: number;
  minValue: number;
  maxValue: number;
  hasUnsettledInWindow: boolean;
} | null {
  const entries: { uci: string; value: number; settled: boolean }[] = [];
  for (const child of root.children.values()) {
    if (child.uci !== null) {
      entries.push({ uci: child.uci, value: child.value, settled: child.visits >= 1 || child.isClosed });
    }
  }
  const first = entries[0];
  if (first === undefined) return null;
  let top = first;
  let minValue = first.value;
  let maxValue = first.value;
  for (const entry of entries) {
    if (entry.value > top.value) top = entry;
    if (entry.value < minValue) minValue = entry.value;
    if (entry.value > maxValue) maxValue = entry.value;
  }
  let runnerUpValue = -Infinity;
  for (const entry of entries) {
    if (entry.uci === top.uci) continue;
    if (entry.value > runnerUpValue) runnerUpValue = entry.value;
  }
  const hasUnsettledInWindow = entries.some((entry) => !entry.settled && top.value - entry.value <= guardWindow);
  return { argmaxUci: top.uci, topValue: top.value, runnerUpValue, minValue, maxValue, hasUnsettledInWindow };
}

/**
 * Rolling argmax-stability state for the two-sided stop rule (Phase 168.5
 * D-05/D-06) — owned by a single `mctsSearch` invocation, mutated only by
 * `stopRuleSatisfied` below.
 */
interface StopRuleState {
  /** Argmax root-child UCI from the previous post-expansion check (null before the first). */
  stableArgmaxUci: string | null;
  /** Consecutive post-expansion checks the argmax UCI has held stable — reset to 1 whenever it changes. */
  stableCheckCount: number;
}

/**
 * Two-sided stop-rule check (Phase 168.5 D-05/D-06, guarded Phase 225
 * D-01/D-02), evaluated once per applied expansion by `applyAndReport`
 * (in canonical dispatch order in round mode, in arrival order in
 * continuous mode): updates `state`'s rolling stability counter
 * UNCONDITIONALLY (the stability semantics themselves are unchanged), then —
 * gated by BOTH the shared min-nodes floor and the stability window — fires
 * on EITHER a clear winner (top-vs-runner-up `.value` margin, AND no
 * unsettled root child within the guard window of the top) or near-tie
 * flatness (max-min `.value` spread — deliberately left unguarded, D-03).
 * Reads `root.children`'s own `.value` fields via `rootChildValueExtremes`,
 * never the findability-sorted `buildRankedLines` (Pattern 2). No wall-clock
 * signal anywhere — deterministic over the applied-expansion sequence, and
 * `deadlineSearch.ts`'s wall-clock cut stays unguarded (D-04).
 */
function stopRuleSatisfied(
  root: EngineNode,
  rule: BotStopRule,
  nodesEvaluated: number,
  state: StopRuleState,
): boolean {
  const guardWindow = rule.marginThreshold + rule.rootGuardBoostAllowance;
  const extremes = rootChildValueExtremes(root, guardWindow);
  if (!extremes) return false;
  state.stableCheckCount = extremes.argmaxUci === state.stableArgmaxUci ? state.stableCheckCount + 1 : 1;
  state.stableArgmaxUci = extremes.argmaxUci;
  if (nodesEvaluated < rule.minNodes || state.stableCheckCount < rule.stabilityWindow) return false;
  return (
    (extremes.topValue - extremes.runnerUpValue >= rule.marginThreshold && !extremes.hasUnsettledInWindow) ||
    extremes.maxValue - extremes.minValue <= rule.epsilonThreshold
  );
}

/**
 * Propagates closure root-ward along `path` after its last node was closed
 * (WR-01 fix): each ancestor whose children are now ALL closed is itself
 * closed, stopping at the first ancestor that still has an open child (its
 * own ancestors then necessarily have an open descendant too). This is what
 * lets `selectPath` skip fully searched subtrees structurally instead of
 * rediscovering the same dead ends by retry.
 */
function propagateClosure(path: readonly EngineNode[]): void {
  for (let i = path.length - 2; i >= 0; i -= 1) {
    const node = path[i];
    if (!node || !allChildrenClosed(node)) break;
    node.isClosed = true;
  }
}

/**
 * Walks root -> leaf via deterministic PUCT (`select.ts`), skipping pending
 * (in flight), closed (fully searched, WR-01), and blocked
 * (dead-end-this-pass, D-06/D-07) children. Returns the full path
 * (root-inclusive), ending either at a genuine leaf-to-expand
 * (`isExpanded === false`) or a freshly discovered dead end
 * (terminal/depth-capped — marked closed here, so it is returned at most
 * ONCE). A non-root node reached with zero selectable children is marked
 * `isBlocked` and the walk RESTARTS from the root instead of giving up,
 * because sibling subtrees may still have selectable work in this fill pass
 * (SEED-170 item 2 — see `blockedThisPass` below; the caller clears the
 * marks when its pass ends). Returns null only when the ROOT itself has
 * nothing selectable: it is closed (tree fully searched), pending (the
 * first expansion is in flight), or every root child is pending, closed, or
 * blocked this pass — mirroring the pre-fix behavior for the one node this
 * restart can never route around.
 */
function selectPath(root: EngineNode, maxPlies: number, blockedThisPass: EngineNode[]): EngineNode[] | null {
  // Root is the one node the child-pending/closed/blocked filter below can
  // never protect (it's the walk's starting point, not reached via a
  // filtered `chosen` pick) — without this guard, two concurrent dispatch
  // slots before the root's expansion is applied would both select the
  // pending root itself, and a terminal/fully-searched root would keep
  // producing dead-end walks.
  if (root.isPending || root.isClosed) return null;
  let path: EngineNode[] = [root];
  let node = root;
  for (;;) {
    if (!node.isExpanded) {
      // Fresh node: close it permanently if it cannot be expanded further
      // (terminal, or the hard depth ceiling — ENGINE-05); otherwise this IS
      // the leaf to expand. Marking `isClosed` here means the child filter
      // below never routes a later walk into this dead end again (WR-01).
      if (node.isTerminal || node.depth >= maxPlies) {
        node.isExpanded = true;
        node.isClosed = true;
      }
      return path;
    }
    const candidates: EngineNode[] = [];
    for (const child of node.children.values()) {
      if (!child.isPending && !child.isClosed && !child.isBlocked) candidates.push(child);
    }
    if (candidates.length === 0) {
      // Nothing selectable below `node` this pass. At the root, that means
      // the pass is genuinely out of work — return null exactly as before
      // the fix (the fill loop's "nothing selectable" break).
      if (node.isRoot) return null;
      // D-06/D-07 fix (SEED-170 item 2): pre-fix, this branch was an
      // unconditional `return null`, collapsing the WHOLE fill pass to
      // whatever had already been dispatched — even when other root subtrees
      // still had selectable children. `apply-order-design.md` section 5
      // misread that null return as the saturated-tree case; it actually
      // fired whenever ONE favored subtree's only children were pending,
      // starving every OTHER subtree's dispatch slot (do not edit that
      // report — D-09). The fix: block this node for the rest of the pass
      // (its parent's filter above then excludes it) and restart the walk
      // from the root, so a peaked non-root policy no longer throttles
      // concurrency down to 1-2 of `budget.concurrency`.
      node.isBlocked = true;
      blockedThisPass.push(node);
      path = [root];
      node = root;
      continue;
    }

    const selectionChildren: SelectionChild[] = candidates.map((c) => ({
      uci: c.uci ?? '',
      prior: c.prior,
      visits: c.visits,
      q: node.isRoot ? c.value : undefined,
      rootExplorationPrior: node.isRoot ? c.rootExplorationPrior : undefined,
    }));
    const chosenUci = selectChild(selectionChildren, node.visits, node.isRoot);
    const chosen = node.children.get(chosenUci);
    if (!chosen) return null; // defensive; selectChild always returns a uci present in the input set
    path.push(chosen);
    node = chosen;
  }
}

interface DispatchedExpansion {
  leaf: EngineNode;
  path: EngineNode[];
  candidateMap: Map<string, number>;
  grades: Map<string, MoveGrade>;
  /** Raw `policy()` distribution at the leaf — the un-reshaped Maia probs each
   *  child's `rawMaiaProb` is read from (Phase 160), distinct from the
   *  renormalized `candidateMap` priors. */
  rawPolicy: Record<string, number>;
  rootExploration: Map<string, number> | null;
}

/** Applies a resolved expansion to the tree: creates children, recomputes the leaf's value, then propagates root-ward. */
function applyExpansion(result: DispatchedExpansion, rootMover: MoverColor): void {
  const { leaf, path, candidateMap, grades, rawPolicy, rootExploration } = result;
  if (candidateMap.size === 0) {
    // Degenerate empty candidate set (WR-04): close as a dead end with no
    // children, no visit bumps, and no backup — matching what
    // fallbackExpectimax does for the same input (the orchestrator also
    // skips nodesEvaluated/onSnapshot for it: nothing was expanded, D-09).
    leaf.isExpanded = true;
    leaf.isPending = false;
    leaf.isClosed = true;
    propagateClosure(path);
    return;
  }
  // 8XN-3: one chess.js instance for the whole expansion instead of one
  // `new Chess(leaf.fen)` per candidate (`applyUciMoveFen` inside this loop) —
  // see `expandChildPositions`'s doc comment for the bit-identical proof.
  const positions = expandChildPositions(leaf.fen, candidateMap.keys(), rootMover);
  for (const [uci, prior] of candidateMap) {
    const position = positions.get(uci);
    if (position === undefined) continue; // illegal/malformed provider candidate — deterministic drop, never a crash (WR-07)
    const grade = grades.get(uci);
    const value = grade ? leafExpectedScore(grade, rootMover) : NEUTRAL_EXPECTED_SCORE;
    const child = createChildNode(
      position.fen,
      leaf.depth + 1,
      uci,
      prior,
      value,
      grade?.evalCp ?? null,
      grade?.evalMate ?? null,
      rawPolicy[uci] ?? null,
      position.terminal,
    );
    if (leaf.isRoot && rootExploration) {
      child.rootExplorationPrior = rootExploration.get(uci) ?? 0;
    }
    leaf.children.set(uci, child);
  }
  leaf.isExpanded = true;
  leaf.isPending = false;
  // WR-01: an expansion whose children are ALL closed at creation (e.g.
  // every candidate is an immediate checkmate/draw) leaves nothing further
  // to search below this node — close it and propagate root-ward so the
  // selection loop never walks into the finished subtree again.
  if (allChildrenClosed(leaf)) {
    leaf.isClosed = true;
    propagateClosure(path);
  }
  recomputeValue(leaf);
  for (let i = path.length - 2; i >= 0; i -= 1) {
    const ancestor = path[i];
    if (ancestor) recomputeValue(ancestor);
  }
  // Visits increment at APPLY time (not at dispatch/selection time): the
  // `isPending` flag alone already prevents a re-pick of this node while it
  // is in flight (see selectPath), so deferring the visit bump to here keeps
  // intermediate onSnapshot visit counts a pure function of the applied
  // expansions, independent of how many were dispatched together. Note this
  // does NOT make output concurrency-level-independent (see the module
  // header's "Determinism scope"): WHICH nodes get selected still differs
  // between c=1 and c>1, because pending-exclusion forces concurrent
  // selections onto different nodes. Round mode delivers determinism per
  // concurrency level; continuous mode is timing-dependent at c>1.
  for (const node of path) node.visits += 1;
}

/**
 * Expands one leaf: `policy()` -> (Phase 159 D-05/D-06/D-07, root-mover side
 * only, short-circuited at the default temperature per Pitfall 1) temperature
 * reshape -> `truncateAndRenormalize` -> (root only) union with
 * `budget.extraRootMoves` AFTER truncation (D-04 — never dropped by Maia's
 * mass cut regardless of its own probability, matching D-05's floor
 * rationale) -> (root only) `applyRootCandidateHardCap`, passed the union's
 * own added UCIs as an exemption set (D-07/Pitfall 6, INJECT-01, 196-01 —
 * never dropped by the root hard cap either) -> ONE batched `grade()` call
 * over the resulting candidate set. Before Phase 196 the cap received no
 * exemption and an injected candidate's prior was seeded at 0, so a wide
 * root silently discarded it here despite surviving the union above. Pure
 * with respect to the tree — does not mutate anything; `applyExpansion`
 * performs all mutation, when the dispatch loop applies the resolved result
 * (after `Promise.all` in round mode, in arrival order in continuous mode).
 */
async function dispatchExpansion(
  leaf: EngineNode,
  path: EngineNode[],
  budget: SearchBudget,
  providers: EngineProviders,
  rootMover: MoverColor,
  signal: AbortSignal,
): Promise<DispatchedExpansion> {
  // Phase 194 ABORT-01, updated 8XN-2: `policy()` now receives the search's
  // own signal too, so `maiaQueue` can drop this request from its own
  // not-yet-dispatched backlog if the search aborts before it is batched to
  // the shared worker. An in-flight ONNX inference is still not
  // interruptible and runs to completion regardless — a stale resolution is
  // unused and harmless once this expansion's result is discarded (mirrors
  // useFlawChessEngine.ts's own Pitfall-1 comment on maiaQueue).
  const rawPolicy = await providers.policy(leaf.fen, budget.elo[leaf.side], leaf.side, signal);
  const temperature = budget.policyTemperature ?? DEFAULT_POLICY_TEMPERATURE;
  const effectivePolicy =
    sideMatchesMover(leaf.side, rootMover) && temperature !== DEFAULT_POLICY_TEMPERATURE
      ? applyPolicyTemperature(rawPolicy, temperature)
      : rawPolicy;
  let candidateMap = truncateAndRenormalize(effectivePolicy);
  // WR-02 (196-REVIEW.md): the union/prior-seeding merge is shared with
  // fallbackExpectimax.ts's expandNode via treeCommon.ts's
  // mergeExtraRootMoves, so the two SearchRunner implementations cannot
  // silently diverge on this logic (see that function's own doc comment).
  let injectedUcis = new Set<string>();
  if (leaf.isRoot && budget.extraRootMoves && budget.extraRootMoves.length > 0) {
    ({ candidateMap, injectedUcis } = mergeExtraRootMoves(candidateMap, effectivePolicy, budget.extraRootMoves));
  }
  if (leaf.isRoot) {
    candidateMap = applyRootCandidateHardCap(candidateMap, injectedUcis);
  }
  const candidateUcis = Array.from(candidateMap.keys());
  if (candidateUcis.length === 0) {
    // Degenerate provider (no candidates for a non-terminal position, WR-04):
    // never call grade() with an empty candidate list — mirrors
    // fallbackExpectimax's guard so both SearchRunner implementations agree
    // on D-09 semantics for the identical input. applyExpansion closes the
    // leaf as a dead end and the orchestrator skips the node budget.
    return {
      leaf,
      path,
      candidateMap,
      grades: new Map<string, MoveGrade>(),
      rawPolicy,
      rootExploration: null,
    };
  }
  // Phase 194 ABORT-01: forward the search's own signal so an abort reaches
  // WorkerPool.grade's existing 3rd param — dequeuing an unstarted request or
  // posting `stop` to an in-flight one instead of running to completion.
  // Phase 195 LADDER-02: the grading rung is resolved HERE, not inside
  // WorkerPool, because `leaf.depth` — the tree depth-from-root — is only
  // known inside the search orchestrator.
  // Phase 226 D-18: route the ROOT's one grade call to `providers.gradeRoot`
  // when the provider offers one, else fall back to `grade` — the sole
  // routing change this plan makes. The first expansion of a search is
  // exactly the root (`selectPath`'s root-pending guard allows only one
  // dispatch until the root is applied), so this selects `gradeRoot` at most
  // ONCE per search, and only for the root; every other leaf (and every
  // provider that lacks `gradeRoot`) takes the unchanged `grade` path.
  // Selection (`selectPath`), the apply order of whichever dispatch loop is
  // running, and the stop rule (`stopRuleSatisfied`) are all untouched by
  // this selection — the fan-out and merge live entirely below this call,
  // inside whichever provider implements `gradeRoot`.
  const gradeFn = (leaf.isRoot ? providers.gradeRoot : undefined) ?? providers.grade;
  const gradeWithDepth = gradeFn as GradeWithLadderDepth;
  const grades = await gradeWithDepth(
    leaf.fen,
    candidateUcis,
    signal,
    gradingDepthForTreeDepth(leaf.depth),
  );
  // 8XN-7: a non-abort empty grade() Map means the pool resolved `new Map()`
  // without grading anything — watchdog fire, a dead pool, or no live slot
  // (workerPoolDispatch.ts / workerPoolWatchdog.ts / workerPoolLifecycle.ts).
  // Before this fix, `applyExpansion` then created EVERY candidate child at
  // NEUTRAL_EXPECTED_SCORE as if Stockfish had actually graded them — those
  // fake 0.5 values backed up through `recomputeValue` into ancestor values
  // and `RankedLine.practicalScore`, and the wasted expansion still spent
  // node budget. The fix: close this leaf as a dead end (the WR-04 shape
  // below) so it keeps the value its OWN parent's grade already gave it,
  // instead of fabricating a value for its children. Excluded on abort: the
  // dispatch loop discards an aborted result entirely (round mode: `if
  // (signal.aborted) break` before each apply; continuous mode: the drain's
  // `signal.aborted || earlyStop` check before `applyAndReport`), and the
  // pool also resolves empty on abort, so this branch would be redundant
  // there. A PARTIAL map (some candidates ungraded) is left
  // alone — those candidates keep the pre-existing NEUTRAL_EXPECTED_SCORE
  // fallback in `applyExpansion`, unchanged.
  //
  // The ROOT is exempt (orchestrator decision, not in the original review
  // finding): closing the root here would leave `rankedLines` empty and send
  // `selectBotMove` to `fallbackMove` (a uniformly random legal move) instead
  // of a Maia-informed one. Keeping today's behavior at the root — its
  // Maia candidates surface at NEUTRAL_EXPECTED_SCORE — is the better
  // degraded mode than "no move ranking at all".
  if (grades.size === 0 && !signal.aborted && !leaf.isRoot) {
    return {
      leaf,
      path,
      candidateMap: new Map<string, number>(),
      grades,
      rawPolicy,
      rootExploration: null,
    };
  }
  const rootExploration = leaf.isRoot ? rootExplorationPriors(candidateMap) : null;
  return { leaf, path, candidateMap, grades, rawPolicy, rootExploration };
}

/** Read-only inputs one `mctsSearch` invocation shares between its dispatch loop and the helpers they both call. */
interface SearchContext {
  root: EngineNode;
  budget: SearchBudget;
  providers: EngineProviders;
  rootMover: MoverColor;
  onSnapshot: (snapshot: EngineSnapshot) => void;
}

/** The mutable counters of one `mctsSearch` invocation (formerly four loop locals). */
interface SearchCounters {
  nodesEvaluated: number;
  budgetExhausted: boolean;
  // Phase 168.5 D-05/D-06: `earlyStop` is a third stop cause, distinct from
  // both budget exhaustion and abort (see EngineSnapshot.stopReason). Stays
  // false forever when `budget.stopRule` is undefined (Pattern 2 backward-
  // compat guard — no wall-clock signal anywhere in this check).
  earlyStop: boolean;
  // Rolling "has the argmax UCI held stable for stopRule.stabilityWindow
  // consecutive post-expansion checks" state, shared by BOTH sides of the
  // two-sided rule (D-05/D-06) — mutated only inside `stopRuleSatisfied`.
  stopState: StopRuleState;
}

function stopReasonOf(st: SearchCounters): EngineSnapshot['stopReason'] {
  return st.earlyStop ? 'early-stop' : st.budgetExhausted ? 'budget' : null;
}

function snapshotOf(ctx: SearchContext, st: SearchCounters): EngineSnapshot {
  return buildSnapshot(ctx.root, st.nodesEvaluated, st.budgetExhausted, ctx.budget.elo[ctx.root.side], stopReasonOf(st));
}

/**
 * Freshly discovered dead end (terminal or depth-capped) returned by
 * `selectPath`: a single visit-bump, no provider calls (D-09/Pitfall 6).
 * `selectPath` marked it closed, so this discovery — and its visit bump —
 * happens at most ONCE per node (WR-01: the old retry probe re-walked closed
 * dead ends up to 1000 times, inflating RankedLine.visits). Shared by both
 * dispatch loops' fills.
 */
function discoverDeadEnd(ctx: SearchContext, st: SearchCounters, leaf: EngineNode, path: EngineNode[]): void {
  if (!leaf.isTerminal && leaf.depth >= ctx.budget.maxPlies) {
    // WR-05: a NON-terminal node cut by the depth ceiling means
    // maxPlies stopped part of the search — the types.ts contract
    // ("maxNodes/maxPlies stopped the search") requires reporting it.
    st.budgetExhausted = true;
  }
  for (const node of path) node.visits += 1;
  propagateClosure(path);
}

/**
 * Applies one resolved expansion to the tree, then reports it: counts the node
 * (a degenerate empty-candidate close is NOT an expansion event, D-09, and
 * emits no snapshot), evaluates the two-sided stop rule, and fires
 * `onSnapshot`. The ONE apply call site both dispatch loops share.
 */
function applyAndReport(ctx: SearchContext, st: SearchCounters, result: DispatchedExpansion): void {
  applyExpansion(result, ctx.rootMover);
  if (result.candidateMap.size === 0) return; // degenerate close (WR-04): not an expansion event (D-09), no snapshot
  st.nodesEvaluated += 1;
  if (st.nodesEvaluated >= ctx.budget.maxNodes) st.budgetExhausted = true;

  // Phase 168.5 D-05/D-06: two-sided stop-rule check, evaluated once per
  // applied expansion (Pattern 2) — see `stopRuleSatisfied`. Skipped entirely
  // when budget.stopRule is undefined (byte-identical to today, Pitfall 1).
  if (ctx.budget.stopRule && stopRuleSatisfied(ctx.root, ctx.budget.stopRule, st.nodesEvaluated, st.stopState)) {
    st.earlyStop = true;
  }

  ctx.onSnapshot(snapshotOf(ctx, st));
}

/**
 * The round dispatch loop (the A21S barrier loop, `dispatchMode` omitted or
 * `'round'`): fill up to `budget.concurrency` expansions, `Promise.all`, apply
 * in canonical dispatch order, repeat.
 */
async function runRoundLoop(ctx: SearchContext, st: SearchCounters, signal: AbortSignal): Promise<void> {
  const { root, budget, providers, rootMover } = ctx;
  while (st.nodesEvaluated < budget.maxNodes && !signal.aborted && !st.earlyStop) {
    const toExpand: { leaf: EngineNode; path: EngineNode[] }[] = [];
    // D-06/D-07: nodes `selectPath` blocked-for-this-round only, owned by
    // this round's fill loop — cleared right below, before `Promise.all`,
    // so the flag never leaks into the next round.
    const blockedThisRound: EngineNode[] = [];

    // Termination is structural (WR-01/D-06), no retry cap needed: every
    // iteration either breaks (nothing selectable at the root), permanently
    // closes a dead-end node (each node closes at most once), blocks a
    // dead-end-this-round node and restarts from the root (each node blocks
    // at most once per round — its parent's filter then excludes it,
    // mirroring `propagateClosure`'s closes-at-most-once argument), or fills
    // a dispatch slot (bounded by concurrency).
    while (toExpand.length < budget.concurrency && st.nodesEvaluated + toExpand.length < budget.maxNodes) {
      const path = selectPath(root, budget.maxPlies, blockedThisRound);
      if (path === null) break; // nothing selectable this round (root closed, or every root child pending/closed/blocked)
      const leaf = path[path.length - 1];
      if (leaf === undefined) break; // defensive; selectPath always returns a non-empty path

      if (leaf.isExpanded) {
        discoverDeadEnd(ctx, st, leaf, path);
        continue;
      }

      // Pending marker (Pattern 5): the ONLY thing needed to keep a
      // subsequent selection within the SAME round from re-picking this
      // exact node — `selectPath` filters out pending children (and the
      // pending root) at every level. Visits increment later, at apply time
      // (see `applyExpansion`), so intermediate onSnapshot counts never
      // depend on how many expansions were dispatched together.
      leaf.isPending = true;
      toExpand.push({ leaf, path });
    }

    // D-06/D-07: clear this round's block flags now, right after the fill
    // loop and before `Promise.all` — `isBlocked` is read only by
    // `selectPath`, which is called only inside the fill loop above, so
    // clearing here is behaviorally identical to clearing "after
    // Promise.all" while keeping the invariant fully local. This also
    // covers the nothing-dispatched break immediately below: a round that
    // ends up dispatching nothing must still not leak blocked nodes into
    // the next round.
    for (const node of blockedThisRound) node.isBlocked = false;
    blockedThisRound.length = 0;

    if (toExpand.length === 0) {
      // Tree fully searched before maxNodes (WR-05): this is NOT budget
      // exhaustion by itself — a terminal root (or a tree whose every leaf
      // is terminal) was searched to completion, nothing stopped it. If the
      // maxPlies ceiling cut any node along the way, the dead-end branch
      // above already set budgetExhausted.
      break;
    }

    // ROUND MODE ONLY — buffer-then-apply-in-canonical-order (Pattern 5):
    // Promise.all resolves to an array in INPUT order regardless of which
    // promise settles first, so applying `results` in order is never raw
    // arrival order. (Continuous mode deliberately applies in arrival order;
    // see `runContinuousLoop`.)
    const results = await Promise.all(
      toExpand.map(({ leaf, path }) => dispatchExpansion(leaf, path, budget, providers, rootMover, signal)),
    );

    for (const result of results) {
      if (signal.aborted) break;
      applyAndReport(ctx, st, result);
      if (st.earlyStop) break; // stop applying further dispatched results this round (mirrors the signal.aborted break above)
    }
  }
}

/** A settled expansion captured as a value, so a rejection can never surface as an unhandled rejection. */
type Settled = { kind: 'ok'; result: DispatchedExpansion } | { kind: 'rejected'; error: unknown };

/**
 * One continuous-mode FILL PASS (design 2.1/2.2): synchronously top up to
 * `budget.concurrency` expansions in flight, subject to the D-10 budget guard
 * (`nodesEvaluated + inFlight + dispatched < maxNodes`, so a node is never
 * dispatched that could push `nodesEvaluated` past `maxNodes`; `maxNodes` is
 * assumed to be a positive integer, a budget precondition this guard relies
 * on and does not validate). Returns how many it dispatched. Every dispatch
 * receives `dispatchSignal` (the inner controller), never the caller's outer
 * signal, and its settlement is handed to `onSettle` as a value.
 *
 * Round-3 review repair: the loop also stops once `dispatchSignal` is aborted
 * (the outer abort listener aborts the inner controller synchronously). A
 * provider's synchronous prefix (`dispatchExpansion` calls `providers.policy`
 * synchronously) can abort the search in the MIDDLE of a pass; without this
 * term the rest of the pass would keep dispatching leaves onto an aborted
 * signal and keep bumping visits / setting `budgetExhausted` after the abort.
 * It cannot change c = 1 behavior: the one dispatch is the pass's last action.
 *
 * Block flags (`selectPath`) are scoped to this one pass and cleared in the
 * `finally`, so a throw cannot leak marks into the next pass (design 2.2: a
 * block can be stale by the next pass, because `isPending` clears at apply
 * time, which runs between passes). Termination is structural, by the round
 * loop's argument: each iteration breaks, closes a dead end once, blocks a
 * node once per pass, or dispatches (bounded by concurrency).
 */
function fillContinuous(
  ctx: SearchContext,
  st: SearchCounters,
  inFlight: number,
  dispatchSignal: AbortSignal,
  onSettle: (settled: Settled) => void,
): number {
  const { root, budget, providers, rootMover } = ctx;
  const blockedThisPass: EngineNode[] = [];
  let dispatched = 0;
  try {
    while (
      !dispatchSignal.aborted &&
      inFlight + dispatched < budget.concurrency &&
      st.nodesEvaluated + inFlight + dispatched < budget.maxNodes
    ) {
      const path = selectPath(root, budget.maxPlies, blockedThisPass);
      if (path === null) break; // nothing selectable (root pending/closed, or every root child pending/closed/blocked)
      const leaf = path[path.length - 1];
      if (leaf === undefined) break; // defensive; selectPath always returns a non-empty path
      if (leaf.isExpanded) {
        discoverDeadEnd(ctx, st, leaf, path);
        continue;
      }
      leaf.isPending = true;
      dispatched += 1;
      // dispatchExpansion is async, so a provider that throws synchronously becomes a rejection here, never a throw
      // out of the fill. The rejection handler makes every outcome a value: no unhandled rejection can exist.
      dispatchExpansion(leaf, path, budget, providers, rootMover, dispatchSignal).then(
        (result) => onSettle({ kind: 'ok', result }),
        (error: unknown) => onSettle({ kind: 'rejected', error }),
      );
    }
  } finally {
    for (const node of blockedThisPass) node.isBlocked = false;
  }
  return dispatched;
}

/**
 * Drains EVERY settled expansion in arrival order and returns how many it
 * removed from `settled`. The one place continuous mode applies a result.
 *
 * L-2/D-09 (claim (d)): a result is applied only if neither `signal.aborted`
 * nor `st.earlyStop` holds at the moment of the apply; the check and the
 * `applyAndReport` call are consecutive statements with no `await` between
 * them, so nothing can flip either flag in between. This also covers an abort
 * fired from inside `onSnapshot` (the deadline cut) while more results are
 * queued: each is discarded. A discarded item is never applied, because an
 * aborted grade settles an EMPTY Map, which `applyExpansion` would turn into
 * fabricated 0.5-valued children.
 *
 * R2A-6: the abort/early-stop test comes BEFORE the rejection test, so every
 * rejection drained after a stop or abort is dropped, whether it was queued
 * behind the stopping apply or arrived later. A rejection drained while the
 * search is live is rethrown (Y-8): the caller sees what `Promise.all` would
 * have produced, and `runContinuousLoop`'s `finally` cancels the siblings.
 */
function drainSettled(ctx: SearchContext, st: SearchCounters, settled: Settled[], signal: AbortSignal): number {
  let drained = 0;
  while (settled.length > 0) {
    const item = settled.shift();
    if (item === undefined) break;
    drained += 1;
    if (signal.aborted || st.earlyStop) continue;
    if (item.kind === 'rejected') throw item.error;
    applyAndReport(ctx, st, item.result);
  }
  return drained;
}

/**
 * The continuous dispatch loop (`dispatchMode: 'continuous'`, design 2.1):
 * fill (synchronous top-up), await exactly one wake, drain everything that has
 * settled, repeat. There is no round barrier, so a slot freed by one settled
 * expansion is refilled at once and Maia and Stockfish overlap.
 *
 * - Pending exclusion: in-flight leaves keep `isPending` and `selectPath`
 *   skips them (hard exclusion, the infinite-penalty limit of virtual loss).
 *   No commit-ordered apply, ring buffer or slot-release machinery exists (D-08).
 * - One inner `dispatchController` is handed to every `dispatchExpansion`; the
 *   `finally` aborts it, which cancels in-flight grades (the pool stops them)
 *   and drops queued Maia requests, on early stop, abort, rejection and
 *   normal exit alike (D-09). The loop returns without draining (Y-3).
 * - The outer signal gets exactly ONE listener, `{ once: true }`, removed in
 *   the `finally` (Pitfall 7); it aborts the inner controller and wakes the
 *   loop, so an abort frees a loop waiting on slow work.
 * - Wakeup (claim (e), X-8): a settlement pushes to `settled` and THEN calls
 *   `notify`, which clears `wake` before invoking it. The loop awaits in one
 *   place only, and the `settled.length` check immediately before it and the
 *   assignment of `wake` in the Promise executor run in one synchronous
 *   stretch, so no settlement can land between them (settlements are
 *   microtasks). R2B-2: an abort raised SYNCHRONOUSLY during a fill (a
 *   provider's synchronous prefix) lands while `wake` is null and would be
 *   lost, so the wait is also guarded by `!signal.aborted && !st.earlyStop`;
 *   the loop-top test then returns.
 * - Budget (claim (b), D-10): `fillContinuous` dispatches only while
 *   `nodesEvaluated + inFlight < maxNodes`, and `inFlight` counts every
 *   dispatched expansion until it is drained, so `nodesEvaluated` never
 *   exceeds `maxNodes` and `inFlight` is 0 when `nodesEvaluated === maxNodes`.
 */
async function runContinuousLoop(ctx: SearchContext, st: SearchCounters, signal: AbortSignal): Promise<void> {
  const dispatchController = new AbortController();
  const settled: Settled[] = []; // arrival order
  let wake: (() => void) | null = null;
  const notify = (): void => {
    const waiter = wake;
    wake = null;
    waiter?.();
  };
  const onOuterAbort = (): void => {
    dispatchController.abort();
    notify();
  };
  if (signal.aborted) onOuterAbort();
  else signal.addEventListener('abort', onOuterAbort, { once: true });
  const onSettle = (item: Settled): void => {
    settled.push(item);
    notify();
  };
  let inFlight = 0; // dispatched and not yet drained (includes settled-but-undrained)
  try {
    for (;;) {
      if (signal.aborted || st.earlyStop) return;
      inFlight += fillContinuous(ctx, st, inFlight, dispatchController.signal, onSettle);
      if (inFlight === 0 && settled.length === 0) return; // nothing running and nothing selectable
      if (settled.length === 0 && !signal.aborted && !st.earlyStop) {
        await new Promise<void>((resolve) => {
          wake = resolve;
        });
      }
      inFlight -= drainSettled(ctx, st, settled, signal);
    }
  } finally {
    signal.removeEventListener('abort', onOuterAbort);
    dispatchController.abort();
  }
}

/**
 * The MCTS orchestrator (`SearchRunner` impl #1). See the module header for
 * the correctness invariants this loop is structurally responsible for.
 * `budget.dispatchMode === 'continuous'` runs `runContinuousLoop`; anything
 * else (including omitted) runs the round loop.
 */
export const mctsSearch: SearchRunner = async (rootFen, budget, providers, onSnapshot, signal) => {
  const rootMover = sideToMoveFromFen(rootFen);
  const ctx: SearchContext = { root: createRoot(rootFen, rootMover), budget, providers, rootMover, onSnapshot };
  const st: SearchCounters = {
    nodesEvaluated: 0,
    budgetExhausted: false,
    earlyStop: false,
    stopState: { stableArgmaxUci: null, stableCheckCount: 0 },
  };
  if (budget.dispatchMode === 'continuous') {
    await runContinuousLoop(ctx, st, signal);
  } else {
    await runRoundLoop(ctx, st, signal);
  }
  return snapshotOf(ctx, st);
};
