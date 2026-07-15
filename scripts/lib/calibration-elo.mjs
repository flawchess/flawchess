#!/usr/bin/env node
/**
 * calibration-elo.mjs — advisory per-cell ELO estimate via anchor-logistic
 * inversion (Phase 168, Plan 03, Task 3, D-05).
 *
 * Standard Elo expected-score inversion: `E = 1 / (1 + 10^((R_anchor -
 * R_bot)/400))`, solved for `R_bot` given an OBSERVED score against one
 * anchor of known rating. `invertAnchorElo` does this per anchor;
 * `combineAnchorEstimates` combines several anchors' estimates into one
 * point estimate, weighting each by inverse squared Wilson-CI width
 * (`wilsonBounds`, imported from the live frontend — "Trust the established
 * Wilson stat method" project convention, never re-derived).
 *
 * Pitfall 4 (168-RESEARCH.md): a lopsided small-sample result (score = 0 or
 * 1) makes the raw inversion blow up to +/-Infinity (`log10(1/E - 1)` at
 * E in {0,1}). `invertAnchorElo` clamps the observed score into
 * `[epsilon, 1-epsilon]` first (`epsilon = 1 / (SCORE_CLAMP_EPSILON_DIVISOR
 * * games)`, a standard small-sample continuity correction) so the result is
 * always finite — advisory-only, low blast radius (D-05: this never touches
 * the primary raw W/D/L matrix, D-04).
 *
 * SEED-091 caveat (carried into the summary TSV's metadata, not here): this
 * whole estimate is COARSE — the anchors themselves are approximate (esp.
 * the Stockfish Skill Level -> Elo mapping, 168-RESEARCH.md Open Question 2)
 * — an estimate, not a precise ELO.
 */
import { wilsonBounds } from '@/lib/scoreConfidence';

/** Continuity-correction divisor: `epsilon = 1 / (SCORE_CLAMP_EPSILON_DIVISOR * games)` (Pitfall 4). */
export const SCORE_CLAMP_EPSILON_DIVISOR = 2;

/** Floor on the Wilson-CI width used as an inverse-variance weight — guards a divide-by-zero at a perfect 0/N or N/N CI. */
export const MIN_CI_WIDTH = 0.01;

/** Clamps `observedScore` into `[epsilon, 1-epsilon]` for `games` games — the same clamp `invertAnchorElo` applies before inverting. */
function clampScore(observedScore, games) {
  const epsilon = 1 / (SCORE_CLAMP_EPSILON_DIVISOR * games);
  return Math.min(1 - epsilon, Math.max(epsilon, observedScore));
}

/**
 * Inverts the standard Elo expected-score formula for `R_bot` given an
 * observed score against one anchor of `anchorRating`, over `games` games.
 * Always finite (Pitfall 4 clamp) — never NaN/Infinity even at a 0/N or N/N
 * observed score.
 */
export function invertAnchorElo(observedScore, anchorRating, games) {
  const clamped = clampScore(observedScore, games);
  return anchorRating - 400 * Math.log10(1 / clamped - 1);
}

/** True if `observedScore` was clamped (i.e. hit the continuity-correction epsilon) before inversion — flags a low-confidence per-anchor estimate. */
export function wasScoreClamped(observedScore, games) {
  if (games <= 0) return false;
  const epsilon = 1 / (SCORE_CLAMP_EPSILON_DIVISOR * games);
  return observedScore <= epsilon || observedScore >= 1 - epsilon;
}

/**
 * Combines several anchors' per-anchor Elo estimates into one point estimate,
 * weighted by inverse squared Wilson-CI width (tighter CI = more weight).
 * Returns `null` if every anchor has zero games (nothing to combine).
 */
export function combineAnchorEstimates(perAnchor) {
  let weightedSum = 0;
  let totalWeight = 0;
  for (const { score, games, anchorRating } of perAnchor) {
    if (games <= 0) continue;
    const estimate = invertAnchorElo(score, anchorRating, games);
    const [ciLow, ciHigh] = wilsonBounds(score, games);
    const ciWidth = Math.max(ciHigh - ciLow, MIN_CI_WIDTH);
    const weight = 1 / (ciWidth * ciWidth);
    weightedSum += estimate * weight;
    totalWeight += weight;
  }
  return totalWeight > 0 ? weightedSum / totalWeight : null;
}
