/**
 * select — Maia top-k truncation/renormalization (ENGINE-02, D-11) and
 * deterministic PUCT child selection with the root/non-root formula split
 * plus the root-only floor-boosted exploration prior (D-01, D-05).
 *
 * `truncateAndRenormalize` and `rootExplorationPriors` are two DISTINCT
 * functions layered in sequence, never conflated (RESEARCH.md Anti-Patterns):
 * every node (root and non-root) truncates/renormalizes its raw `policy()`
 * output first; the root additionally floor-boosts that output for its PUCT
 * exploration term ONLY — `backup.ts` always consumes the plain renormalized
 * priors, never the floor-boosted ones.
 */

/**
 * Cumulative-mass truncation cutoff for the search core's own top-k
 * expansion (ENGINE-02, D-11). Deliberately separate from `moveQuality.ts`'s
 * `CUMULATIVE_MASS_THRESHOLD = 0.95` — search branching factor and chart
 * display set are different concerns tuned independently; do NOT import
 * `CUMULATIVE_MASS_THRESHOLD` or `CANDIDATE_HARD_CAP` from `moveQuality.ts`.
 */
export const POLICY_MASS_THRESHOLD = 0.9;

/** PUCT exploration coefficient (Claude's discretion, named tunable). */
export const C_PUCT = 1.4;

/**
 * Root-only exploration-prior floor (D-05, ~0.10). Ensures a Stockfish-
 * injected `extraRootMoves` candidate with ~0 Maia probability still
 * receives PUCT exploration visits at the root — it never affects the
 * renormalized values `backup.ts` consumes.
 */
export const ROOT_PRIOR_FLOOR = 0.1;

/**
 * Sorts `policy` by probability descending, keeps entries until cumulative
 * mass reaches `POLICY_MASS_THRESHOLD` (break AFTER the crossing move is
 * kept, mirroring `moveQuality.ts`'s `selectCandidatesByMass` loop shape),
 * then renormalizes the kept probabilities to sum to 1. No hard cap (D-11 —
 * unlike `moveQuality.ts`'s display-oriented `CANDIDATE_HARD_CAP`).
 *
 * Called once per expansion (root or non-root) on the raw `policy()` output,
 * BEFORE any root-only floor-boost (D-05) is applied.
 */
export function truncateAndRenormalize(policy: Record<string, number>): Map<string, number> {
  // Equal probabilities tie-break by ascending UCI string, never Record key
  // insertion order: when a tie straddles the mass boundary, WHICH move
  // survives truncation must not depend on the order the provider happened
  // to assemble its output Record (a real Maia provider can change that with
  // no code change here) — matches every other tie-break in the core.
  const sorted = Object.entries(policy).sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1));
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

/**
 * Root-only floor-boosted exploration prior (D-05): `max(P_maia(c),
 * ROOT_PRIOR_FLOOR)` renormalized over the root candidate set. The output of
 * this function is used ONLY in the root PUCT exploration term — NEVER as a
 * backup value. Do not conflate with `truncateAndRenormalize`: this is a
 * separate transform, root-only in scope, with a different consumer (PUCT
 * exploration vs. `backup.ts` expectation).
 */
export function rootExplorationPriors(renormalized: Map<string, number>): Map<string, number> {
  const floored = new Map<string, number>();
  let total = 0;
  for (const [uci, p] of renormalized) {
    const flooredP = Math.max(p, ROOT_PRIOR_FLOOR);
    floored.set(uci, flooredP);
    total += flooredP;
  }
  const result = new Map<string, number>();
  for (const [uci, p] of floored) {
    result.set(uci, total > 0 ? p / total : 0);
  }
  return result;
}

/**
 * One child candidate available to `selectChild` at a single node.
 *   - `uci`: the candidate move, canonical tie-break key (D-08).
 *   - `prior`: the plain (non-floor-boosted) renormalized Maia prior P̂ for
 *     this child — the exploration weight used at NON-root nodes.
 *   - `visits`: this child's current visit count `n`.
 *   - `q`: root-only backed-up value; ignored (and may be omitted) at
 *     non-root nodes since the Q term is dropped there (D-01).
 *   - `rootExplorationPrior`: root-only floor-boosted prior P_root from
 *     `rootExplorationPriors()`; ignored (and may be omitted) at non-root
 *     nodes.
 */
export interface SelectionChild {
  uci: string;
  prior: number;
  visits: number;
  q?: number;
  rootExplorationPrior?: number;
}

/**
 * Deterministic PUCT child selection (D-01). The tree has exactly one max
 * node — the root:
 *   - Root (`isRoot: true`): `argmax Q(c) + C_PUCT · P_root(c) · √N/(1+n(c))`.
 *   - Non-root: `argmax P̂(c) · √N/(1+n(c))` — the Q term is dropped
 *     entirely; refines what dominates the expectation backup.
 * Ties are broken by canonical ascending UCI-string order (never iteration
 * order — determinism, ENGINE-07).
 */
export function selectChild(
  children: readonly SelectionChild[],
  parentVisits: number,
  isRoot: boolean,
): string {
  if (children.length === 0) {
    throw new Error('selectChild: children must be non-empty');
  }
  const sqrtN = Math.sqrt(parentVisits);
  let bestUci: string | null = null;
  let bestScore = Number.NEGATIVE_INFINITY;
  for (const child of children) {
    const explorationWeight = isRoot ? (child.rootExplorationPrior ?? 0) : child.prior;
    const explorationTerm = explorationWeight * (sqrtN / (1 + child.visits));
    const score = isRoot ? (child.q ?? 0) + C_PUCT * explorationTerm : explorationTerm;
    const isBetter =
      bestUci === null || score > bestScore || (score === bestScore && child.uci < bestUci);
    if (isBetter) {
      bestUci = child.uci;
      bestScore = score;
    }
  }
  // bestUci is always set here: children is non-empty (guarded above) and the
  // loop's first iteration always satisfies `bestUci === null`.
  return bestUci as string;
}
