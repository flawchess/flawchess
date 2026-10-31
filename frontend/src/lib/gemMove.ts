/**
 * gemMove — pure, worker-free "gem move" detection.
 *
 * A gem is a played move that is BOTH hard for a human to find (C1: the Maia
 * policy probability at the rating-matched rung is at or below
 * GEM_MAIA_MAX_PROB) AND the only good move in the position (C2: it is the
 * graded best AND beats the runner-up by at least MISTAKE_DROP in expected
 * score). Reuses the project's canonical sigmoid (`evalToExpectedScore`) and
 * generated threshold (`MISTAKE_DROP`) verbatim — this module never re-derives
 * either (single source of truth).
 *
 * No opening-ply guard, no "still losing" exclusion: a
 * best-try in a lost position still qualifies as a gem as long as it clears
 * both C1 and C2. classifyGem has no color/ply parameter, so it applies
 * identically to both movers and at any ply.
 */

import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { MISTAKE_DROP } from '@/generated/flawThresholds';

/** Maia policy-probability ceiling for C1.
 *  Deliberately a flat cutoff, not an ELO-scaled iso-rarity curve (this
 *  constant stays independent of any per-ELO reference-probability curve).
 *
 *  Retuned 0.2 -> 0.3 on 2026-10-31 (quick 261031-et9): at 0.2 a gem showed up
 *  in only 4.8% of prod player-games; 0.3 roughly doubles that ("fewer than ~3
 *  in 10 rating-peers would play it").
 *
 *  Original v1 rationale, 0.2 rather than 0.1: measured against the calibration TSV (`reports/data/gem-elo-calibration-2026-07-11T14-07-34-084Z.tsv`,
 *  3,000 positions x 6 rungs), 0.2 (vs 0.1) multiplies gem frequency by ~1.35x at
 *  Maia-600, rising to ~1.8x at 2200-2600 — and it NARROWS the 600-vs-2600 Elo
 *  skew from 3.8x to 2.9x (strong players were previously starved: only 2.9% of
 *  even the C2-qualifying positions cleared C1 at the 2600 rung). Caveat: the
 *  TSV's sample is enriched (21.8% of positions pass C2), so only the RATIOS
 *  above transfer to real games, not the absolute frequencies.
 *
 *  Cross-reference: mirrors the backend's
 *  authoritative `GEM_MAIA_MAX_PROB` in `app/services/best_move_candidates.py`.
 *  This frontend copy is used ONLY by the live-engine fallback path
 *  (classifyGem/classifyGreat, below) — the stored/mainline path always reads
 *  the backend-classified `EvalPoint.best_move_tier` instead. If the backend
 *  constant is ever retuned, update this copy too. */
export const GEM_MAIA_MAX_PROB = 0.3;

/** Maia policy-probability ceiling for the "great" tier's C1 band — great = maia_prob in (GEM_MAIA_MAX_PROB, GREAT_MAIA_MAX_PROB].
 *
 *  Cross-reference: mirrors the backend's authoritative `GREAT_MAIA_MAX_PROB`
 *  in `app/services/best_move_candidates.py` (retuned 0.5 -> 0.7 on 2026-10-31
 *  against real prod per-game frequency, quick 261031-et9). Fallback-only
 *  — the stored/mainline path never calls `classifyGreat`; it always
 *  reads the backend-classified `EvalPoint.best_move_tier` instead. If the
 *  backend constant is ever retuned, update this copy too. */
export const GREAT_MAIA_MAX_PROB = 0.7;

/**
 * Cap on the per-session live engine/Maia/flaw FIFO caches keyed by FEN or
 * node id (`Analysis.tsx`'s `engineEvalByFen`/`maiaCurveByFen`/
 * `liveFlawByNode`, and `useAnalysisGemMarkers.ts`'s parent-grade retention
 * cache) — hoisted here so the two files share one
 * bound instead of two independently-editable copies that could silently
 * diverge.
 */
export const LIVE_EVAL_CACHE_MAX = 256;

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

/**
 * C1 (moderately hard to find, one tier below gem) AND C2 (only good move —
 * SAME gate as classifyGem). Fallback-only: callers on the live
 * (unanalyzed) path resolve the played move's Maia probability and the
 * parent position's best/second-best expected score BEFORE calling this,
 * same contract as classifyGem. The stored/mainline path never calls this —
 * it reads the backend-classified `EvalPoint.best_move_tier` instead.
 */
export function classifyGreat(params: {
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
  if (maiaProbability === null) return false;
  if (maiaProbability <= GEM_MAIA_MAX_PROB || maiaProbability > GREAT_MAIA_MAX_PROB) return false;
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
 * (secondBestEs) expected score, in one pass, mover-agnostic — the
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
    // Bug fix: an ungraded entry — qualityBySan explicitly
    // maps unresolved SANs to {evalCp: null, evalMate: null} — would read as a
    // fabricated 0.5 expected score through evalToExpectedScore's neutral
    // fallback. That phantom 0.5 could displace the real argmax in a lost
    // position (suppressing a legitimate best-try gem) or become the
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
