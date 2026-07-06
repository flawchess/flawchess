/**
 * backup — the Maia-prior-weighted expectation (non-root) + max (root) backup
 * rule (ENGINE-03, D-01/D-02).
 *
 * This is the single genuinely novel, highest-risk file in the v2.0 FlawChess
 * Engine milestone (SEED-082's own framing). The `BackupChild` interface
 * structurally closes Pitfall 1 ("silently degenerates into textbook MCTS"):
 * `prior` is an explicit field supplied independently of `value` and of any
 * visit count — nothing in this file ever derives a weight from visits, so a
 * reviewer can see at a glance that the backup rule cannot quietly become a
 * visit-count-weighted average. No `visits`/`n` field or term appears
 * anywhere below.
 *
 * Pure math over arrays — no I/O, no try/catch — matches moveQuality.ts's
 * convention for pure-transform files.
 */

/**
 * One child contribution to a node's backup. `prior` and `value` are always
 * populated independently:
 *   - `prior`: the renormalized Maia prior for this child at THIS node
 *     (D-02) — frozen at expansion time from a fresh `policy()` call. NEVER
 *     re-derived from visits or values (Pitfall 1).
 *   - `value`: either the child's own backed-up expectation (if its subtree
 *     is expanded) or the parent-time `sigmoid(shallowEval)` leaf estimate
 *     via `leafExpectedScore()` (if not) — D-02. Both kinds may appear mixed
 *     in the same children array; no probability mass is ever dropped.
 */
export interface BackupChild {
  prior: number;
  value: number;
}

/**
 * Non-root nodes: Maia-prior-weighted expectation over the FULL truncated
 * top-k set (D-02) — mixing expanded (backed-up) and unexpanded (leaf-
 * estimate) children with no mass dropped. Renormalizes `prior` by the
 * summed `totalPrior` in case the caller's set doesn't sum to exactly 1
 * (e.g. floating-point drift). Returns `0.5` as a degenerate guard when
 * `totalPrior === 0` — this should not occur post-renormalization upstream,
 * but a node with no legal moves must never divide by zero here.
 */
export function backupExpectation(children: readonly BackupChild[]): number {
  const totalPrior = children.reduce((sum, c) => sum + c.prior, 0);
  if (totalPrior === 0) return 0.5;
  return children.reduce((sum, c) => sum + (c.prior / totalPrior) * c.value, 0);
}

/**
 * Root only: plain max over candidate values (D-01's "exactly one max node
 * in the tree"). Distinct from `backupExpectation` — the root never averages
 * over its children's priors, it picks the best one.
 */
export function backupRootMax(children: readonly BackupChild[]): number {
  // Degenerate guard mirroring backupExpectation's: Math.max of an empty
  // array is -Infinity, which would silently flow into practicalScore
  // (documented 0-1). This is an exported public primitive of the locked
  // Phase 153 surface, so it must be safe standalone — not only behind the
  // orchestrators' own children.size === 0 early returns.
  if (children.length === 0) return 0.5;
  return Math.max(...children.map((c) => c.value));
}
