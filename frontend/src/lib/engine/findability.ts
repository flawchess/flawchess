/**
 * findability — root-only ranking weight that folds the root player's OWN
 * move-probability (`P_you`) back into `buildRankedLines`'s sort (Phase 159
 * D-01/SEED-085), without touching `V(X)` (the per-move practical score),
 * the search core, the backup rule, or leaf grades at all.
 *
 * `rankScore` is a SATURATING linear factor blended toward a fallback value,
 * NEVER toward zero (Phase 225 D-10a, SEED-170 item 3):
 * `f * V + (1 - f) * min(V, V_fallback)`, with `f = min(1, P_you/P_ref)` as
 * before (beta fixed at 1, no exponent). Invariants:
 *   - `f = 1` (P_you >= P_ref) gives EXACTLY `V` — the modal/highest-prior
 *     move can NEVER be boosted above its own V, same as before.
 *   - `min(V, V_fallback) <= rankScore <= V` ALWAYS — rankScore can only
 *     demote a move toward what the player would typically score (never
 *     below that, and never above its own V).
 *   - A move whose V is already below V_fallback sorts by its own V: it is
 *     NEVER promoted for being hard to find, and never penalized further —
 *     `min(V, V_fallback) = V` in that case, so `rankScore = V` regardless
 *     of `f`.
 *
 * Why the `min()` clamp exists: the seeded, unclamped form
 * `f * V + (1 - f) * V_fallback` would pull a hard-to-find BLUNDER (V well
 * below V_fallback) UP toward the average — directly breaking this module's
 * founding argument that rankScore can only demote a move, never promote
 * one above its own V (Phase 159's whole point). The clamp is what keeps
 * "findability demotes a hard-to-find winning move toward what the player
 * would typically score" true without also implying "findability promotes a
 * hard-to-find blunder toward the average".
 *
 * What `V_fallback` is (`rankFallbackValue`, D-10b amended): what the player
 * scores by just playing like a human at their rating — the prior-weighted
 * MEAN of the root's own children, using `child.prior` (the same `pYou`
 * `rankScore` already reads), normalized by the total prior because the
 * root's hard candidate cap and any injected `extraRootMoves` leave root
 * priors NOT summing to 1. Computed ONCE per `buildRankedLines` call, never
 * per child (same anti-pattern guard as `pRef`). Guarded to `0` — not
 * `backupExpectation`'s own `0.5` degenerate default — when the total prior
 * is `<= 0`, because `0` reduces the whole formula to today's pre-Phase-225
 * `f * V` with no NaN (D-10b), while `0.5` would silently reintroduce a
 * fallback pull under conditions this module never intended.
 *
 * `P_REF_ANCHORS`/`pRefForElo` are UNCHANGED by this phase (D-10e) — item 3
 * is entirely the blend target (toward `V_fallback` instead of toward 0),
 * never the findability curve itself. This intentionally reverses Phase
 * 159's original showcase fixture (a hard-to-find move far better than the
 * findable alternative now ranks FIRST instead of last) — an accepted,
 * user-confirmed consequence (D-10e), not a regression.
 *
 * Rejected alternative: raw `P^beta * V`. P spans orders of magnitude while V
 * does not, so the workable beta window is narrow and position-dependent (in
 * the 600-ELO regression case below, beta must land in ~(0.15, 0.25) or the
 * 57%-prior Mistake wins) — every miscalibration fails toward the rejected
 * greedy modal-move engine. The saturating factor has no such knife-edge: it
 * can only ever demote a below-P_ref move toward V_fallback, never promote
 * one above its own V.
 */

import { type BackupChild, backupExpectation } from './backup';

/**
 * Anchor curve for P_ref(ELO): aggressive suppression at low ELO (findability
 * matters a lot — a 600-rated player rarely finds a 5%-probability move),
 * near-off at the top of the Maia ladder (findability barely matters — most
 * top engine moves are "findable" to a 2600). ASSUMED starting point (D-02
 * is fully Claude's discretion; only the qualitative shape is locked) — the
 * D-03 regression cases in findability.test.ts are the acceptance bar,
 * not a numeric proof that this exact curve is correct; live UAT may retune
 * these anchors without touching rankScore's saturating-factor mechanism.
 * Unchanged since Phase 159 (Phase 225 D-10e: item 3 touches only the blend
 * target, never this curve).
 */
export const P_REF_ANCHORS: readonly [elo: number, pRef: number][] = [
  [600, 0.12],
  [1000, 0.08],
  [1400, 0.05],
  [1800, 0.03],
  [2200, 0.015],
  [2600, 0.005],
];

/**
 * Linear interpolation between `P_REF_ANCHORS`, clamped to the first/last
 * anchor's `pRef` outside [600, 2600] (T-159-01). Every array index is bound
 * to a local and null-checked before use (`noUncheckedIndexedAccess`) — never
 * asserted with `!`.
 */
export function pRefForElo(elo: number): number {
  const first = P_REF_ANCHORS[0];
  const last = P_REF_ANCHORS[P_REF_ANCHORS.length - 1];
  if (!first || !last) return 0; // defensive; P_REF_ANCHORS is a non-empty const
  if (elo <= first[0]) return first[1];
  if (elo >= last[0]) return last[1];
  for (let i = 0; i < P_REF_ANCHORS.length - 1; i += 1) {
    const lo = P_REF_ANCHORS[i];
    const hi = P_REF_ANCHORS[i + 1];
    if (!lo || !hi) continue; // noUncheckedIndexedAccess
    if (elo >= lo[0] && elo <= hi[0]) {
      const t = (elo - lo[0]) / (hi[0] - lo[0]);
      return lo[1] + t * (hi[1] - lo[1]);
    }
  }
  return last[1]; // unreachable given the guards above; defensive
}

/**
 * D-10a's saturating findability factor, blended toward `fallbackValue`
 * (never toward 0 — Phase 225 SEED-170 item 3): `f * value + (1 - f) *
 * min(value, fallbackValue)`, with `f = min(1, pYou/pRef)`, beta = 1
 * (locked). Returns exactly `value` when `pYou >= pRef` (saturation — the
 * upper bound of rankScore is always `value`, for any `pYou`, any
 * `fallbackValue`). Guards `pRef <= 0` by returning `value` unmodified
 * (degenerate case, mirrors `backup.ts`'s `totalPrior===0` convention —
 * never divides by zero or propagates `NaN`/`Infinity` into the sort,
 * T-159-02). See the module header for the full invariant
 * (`min(value, fallbackValue) <= rankScore <= value`) and why the `min()`
 * clamp exists.
 */
export function rankScore(
  pYou: number,
  pRef: number,
  value: number,
  fallbackValue: number,
): number {
  if (pRef <= 0) return value;
  const f = Math.min(1, pYou / pRef);
  return f * value + (1 - f) * Math.min(value, fallbackValue);
}

/**
 * `V_fallback` (D-10b amended): the prior-weighted MEAN of the root's own
 * children — "what the player scores by just playing like a human at their
 * rating". Reuses `backupExpectation` (RESEARCH C-4: no hand-rolled third
 * expectation formula) behind an explicit zero-total guard that returns `0`
 * instead of `backupExpectation`'s own `0.5` default — `0` is what makes
 * `rankScore` reduce to the pre-Phase-225 `f * value` when there is no prior
 * mass to average over (D-10b), not a neutral 0.5 pull. Computed ONCE per
 * `buildRankedLines` call (never per child) from every root child's
 * `{ prior, value }` — see `treeCommon.ts`'s call site.
 */
export function rankFallbackValue(children: readonly BackupChild[]): number {
  const totalPrior = children.reduce((sum, c) => sum + c.prior, 0);
  if (totalPrior <= 0) return 0;
  return backupExpectation(children);
}
