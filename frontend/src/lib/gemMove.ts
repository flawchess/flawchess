/**
 * gemMove — pure, worker-free "gem move" detection (Phase 163, SEED-092).
 *
 * A gem is a played move that is BOTH hard for a human to find (C1: the Maia
 * policy probability at the rating-matched rung is at or below
 * GEM_MAIA_MAX_PROB) AND the only good move in the position (C2: it is the
 * graded best AND beats the runner-up by at least MISTAKE_DROP in expected
 * score). Reuses the project's canonical sigmoid (`evalToExpectedScore`) and
 * generated threshold (`MISTAKE_DROP`) verbatim — this module never re-derives
 * either (Phase 162's single-source-of-truth discipline).
 *
 * No opening-ply guard (D-02), no "still losing" exclusion (D-01): a
 * best-try in a lost position still qualifies as a gem as long as it clears
 * both C1 and C2. classifyGem has no color/ply parameter, so it applies
 * identically to both movers (D-04) and at any ply.
 */

import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { MISTAKE_DROP } from '@/generated/flawThresholds';

/** Maia policy-probability ceiling for C1 (D-07) — strict-side v1 constant.
 *  Deliberately a flat cutoff, not an ELO-scaled iso-rarity curve (D-08 defers
 *  that refinement to a future phase — this constant stays independent of
 *  any per-ELO reference-probability curve). */
export const GEM_MAIA_MAX_PROB = 0.05;

/**
 * C1 (hard to find) AND C2 (only good move). Callers resolve the played
 * move's Maia probability and the parent position's best/second-best
 * expected score BEFORE calling this — this function does no lookups.
 */
export function classifyGem(params: {
  /** Played move's Maia probability at the rating-matched rung. */
  maiaProbability: number | null;
  /** Played move === argmax over the parent position's graded candidates. */
  playedIsBest: boolean;
  /** Parent position's top expected score (mover POV). */
  bestEs: number | null;
  /** Parent position's runner-up expected score (mover POV). */
  secondBestEs: number | null;
}): boolean {
  const { maiaProbability, playedIsBest, bestEs, secondBestEs } = params;
  if (maiaProbability === null || maiaProbability > GEM_MAIA_MAX_PROB) return false;
  if (!playedIsBest || bestEs === null || secondBestEs === null) return false;
  return bestEs - secondBestEs >= MISTAKE_DROP;
}

/** One graded candidate's white-POV eval, keyed by SAN. */
export interface GemGrade {
  evalCp: number | null;
  evalMate: number | null;
}

/**
 * Reduces a per-SAN grade map to the argmax (bestSan/bestEs) and runner-up
 * (secondBestEs) expected score, in one pass, mover-agnostic (D-04) — the
 * mover argument only feeds `evalToExpectedScore`'s POV conversion.
 * Ungraded entries (null/null) are skipped entirely — they carry no evidence.
 * Empty (or all-ungraded) map → all fields null. Single graded entry →
 * secondBestEs null.
 */
export function summarizeForGem(
  gradeBySan: Map<string, GemGrade>,
  mover: MoverColor,
): { bestSan: string | null; bestEs: number | null; secondBestEs: number | null } {
  let bestSan: string | null = null;
  let bestEs = -Infinity;
  let secondBestEs = -Infinity;
  for (const [san, grade] of gradeBySan) {
    // Bug fix (163-REVIEW WR-02): an ungraded entry — qualityBySan explicitly
    // maps unresolved SANs to {evalCp: null, evalMate: null} — would read as a
    // fabricated 0.5 expected score through evalToExpectedScore's neutral
    // fallback. That phantom 0.5 could displace the real argmax in a lost
    // position (suppressing a legitimate D-01 best-try gem) or become the
    // runner-up in a winning one (inflating the gap into a spurious C2 pass).
    // No evidence → no contribution.
    if (grade.evalCp === null && grade.evalMate === null) continue;
    const es = evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
    if (es > bestEs) {
      secondBestEs = bestEs;
      bestEs = es;
      bestSan = san;
    } else if (es > secondBestEs) {
      secondBestEs = es;
    }
  }
  return {
    bestSan,
    bestEs: bestSan !== null ? bestEs : null,
    secondBestEs: secondBestEs > -Infinity ? secondBestEs : null,
  };
}
