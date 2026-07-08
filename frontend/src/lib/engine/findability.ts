/**
 * findability — root-only ranking weight that folds the root player's OWN
 * move-probability (`P_you`) back into `buildRankedLines`'s sort (Phase 159
 * D-01/SEED-085), without touching `V(X)` (the per-move practical score),
 * the search core, the backup rule, or leaf grades at all.
 *
 * `rankScore` is a SATURATING linear factor: `min(1, P_you/P_ref) * V(X)`,
 * with beta fixed at 1 (no exponent). Any move at or above `P_ref` gets
 * factor 1 — full V, unmodified — so the modal/highest-prior move can NEVER
 * be boosted above its own V. This is what makes the rejected greedy
 * "rank by P^beta*V" engine structurally impossible here, rather than merely
 * avoided by careful calibration.
 *
 * Rejected alternative: raw `P^beta * V`. P spans orders of magnitude while V
 * does not, so the workable beta window is narrow and position-dependent (in
 * the 600-ELO regression case below, beta must land in ~(0.15, 0.25) or the
 * 57%-prior Mistake wins) — every miscalibration fails toward the rejected
 * greedy modal-move engine. The saturating factor has no such knife-edge: it
 * can only ever demote a below-P_ref move, never promote one above its own V.
 */

/**
 * Anchor curve for P_ref(ELO): aggressive suppression at low ELO (findability
 * matters a lot — a 600-rated player rarely finds a 5%-probability move),
 * near-off at the top of the Maia ladder (findability barely matters — most
 * top engine moves are "findable" to a 2600). ASSUMED starting point (D-02
 * is fully Claude's discretion; only the qualitative shape is locked) — the
 * three D-03 regression cases in findability.test.ts are the acceptance bar,
 * not a numeric proof that this exact curve is correct; live UAT may retune
 * these anchors without touching rankScore's saturating-factor mechanism.
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
 * D-01's saturating findability factor: `min(1, pYou/pRef) * value`, beta = 1
 * (locked). Returns exactly `value` when `pYou >= pRef` (saturation — the
 * upper bound of rankScore is always `value`, for any `pYou`). Guards
 * `pRef <= 0` by returning `value` unmodified (degenerate case, mirrors
 * `backup.ts`'s `totalPrior===0` convention — never divides by zero or
 * propagates `NaN`/`Infinity` into the sort, T-159-02).
 */
export function rankScore(pYou: number, pRef: number, value: number): number {
  if (pRef <= 0) return value;
  return Math.min(1, pYou / pRef) * value;
}
