/**
 * moveQuality — pure, worker-free 5-bucket move-quality classification and
 * candidate-set selection for the Moves-by-Rating chart (Phase 151.1).
 *
 * classifyMoveQuality reuses FlawChess's OWN existing grading pipeline
 * (evalToExpectedScore -> classifyLiveSeverity, from liveFlaw.ts) verbatim —
 * it does NOT re-derive the sigmoid or the inaccuracy/mistake/blunder
 * thresholds. Only two new buckets ("best", "good") are layered on top: the
 * grading search's own top-scoring candidate is "best"; any other candidate
 * whose expected-score drop against that best is below the inaccuracy
 * threshold is "good" (151.1-RESEARCH.md Pattern 3).
 *
 * selectCandidatesByMass implements D-02/D-06/D-07 (151.1-RESEARCH.md): the
 * Maia cumulative-probability >= 0.95 set at the SELECTED ELO (not
 * peak-across-all-ELO, which is what the superseded `capMovesByPeak` used),
 * capped to the top CANDIDATE_HARD_CAP by probability, always unioned with
 * {bestSan} and {playedSan} so the SF-best and the actually-played move are
 * never dropped even when below the cut.
 *
 * MoveQuality is a NEW, frontend-only type. FlawSeverity (types/library.ts)
 * is the cross-stack contract mirroring the backend's severity enum and must
 * NOT be extended with 'best'/'good' (RESEARCH Anti-Patterns).
 */

import { evalToExpectedScore, classifyLiveSeverity, type MoverColor } from '@/lib/liveFlaw';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';

// ─── Types ──────────────────────────────────────────────────────────────────

/** 5-bucket move quality (NEW, frontend-only — do not merge with FlawSeverity). */
export type MoveQuality = 'best' | 'good' | 'inaccuracy' | 'mistake' | 'blunder';

/** White-POV eval for one graded candidate move, as stored by the grading hook. */
export interface MoveGrade {
  evalCp: number | null;
  evalMate: number | null;
  depth: number;
}

export interface MoveQualityInfo {
  quality: MoveQuality;
  expectedScore: number;
}

// ─── Constants ──────────────────────────────────────────────────────────────

/** Maia cumulative-probability mass cutoff at the selected ELO (D-02). */
export const CUMULATIVE_MASS_THRESHOLD = 0.95;

/** Hard cap on displayed candidate lines after the mass cut (D-06). */
export const CANDIDATE_HARD_CAP = 5;

// ─── classifyMoveQuality ────────────────────────────────────────────────────

/**
 * Classifies each graded candidate into one of the 5 quality buckets.
 *
 * The "best" reference is the primary engine's top move (`designatedBestSan`,
 * the same move the eval bar + engine card show) whenever it's provided AND
 * already graded — so the chart's "best" never contradicts the rest of the
 * page (151.1 UAT: two independent Stockfish searches broke near-ties
 * differently, e.g. the engine card called Nf6 best while this grading pass's
 * own top scorer was d5, yielding a self-contradictory "Nf6 · best: Good"
 * tooltip). We fall back to this pass's own top scorer only when
 * `designatedBestSan` is null (no engine PV yet) or hasn't streamed a grade
 * yet (D-05 progressive fill), so lines still color before the primary engine
 * catches up.
 *
 * Every other candidate is graded via classifyLiveSeverity against that best,
 * with a null (clean) result — including a candidate scoring *above* the
 * designated best, which yields a negative drop — mapped to "good".
 */
export function classifyMoveQuality(
  gradeMap: Map<string, MoveGrade>,
  mover: MoverColor,
  designatedBestSan?: string | null,
): Map<string, MoveQualityInfo> {
  const scores = new Map<string, number>();
  let topSan: string | null = null;
  let topEs = -Infinity;
  for (const [san, grade] of gradeMap) {
    const es = evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
    scores.set(san, es);
    if (es > topEs) {
      topEs = es;
      topSan = san;
    }
  }

  // Prefer the primary engine's best move as the reference; fall back to this
  // pass's own top scorer until it's available/graded.
  const useDesignated = designatedBestSan != null && scores.has(designatedBestSan);
  const bestSan = useDesignated ? designatedBestSan : topSan;
  const bestEs = useDesignated ? scores.get(designatedBestSan)! : topEs;

  const result = new Map<string, MoveQualityInfo>();
  for (const [san, es] of scores) {
    if (san === bestSan) {
      result.set(san, { quality: 'best', expectedScore: es });
      continue;
    }
    const severity = classifyLiveSeverity(bestEs, es);
    result.set(san, { quality: severity ?? 'good', expectedScore: es });
  }
  return result;
}

// ─── selectCandidatesByMass ─────────────────────────────────────────────────

/**
 * Finds the perElo rung whose ELO is numerically closest to `target` (mirrors
 * useMaiaEngine's nearestByElo). Exported so positionVerdict.ts (quick
 * 260705-m3z) reuses this exact lookup instead of re-deriving it.
 */
export function nearestByElo(perElo: MoveCurvePoint[], target: number): MoveCurvePoint | undefined {
  return perElo.reduce<MoveCurvePoint | undefined>((closest, point) => {
    if (closest === undefined) return point;
    return Math.abs(point.elo - target) < Math.abs(closest.elo - target) ? point : closest;
  }, undefined);
}

/**
 * Selects the SANs to display as chart lines: the Maia cumulative-probability
 * >= CUMULATIVE_MASS_THRESHOLD set at the perElo rung nearest `selectedElo`,
 * capped to the top CANDIDATE_HARD_CAP by probability, always unioned with
 * `bestSan` and `playedSan` (D-02/D-06/D-07). Returned in probability-
 * descending order for stable stacking/legend order.
 */
export function selectCandidatesByMass(
  perElo: MoveCurvePoint[],
  selectedElo: number,
  playedSan: string | null,
  bestSan: string | null,
): string[] {
  const rung = nearestByElo(perElo, selectedElo);
  if (rung === undefined) return [];

  const sorted = Object.entries(rung.moveProbabilities).sort((a, b) => b[1] - a[1]);
  const massSet: string[] = [];
  let cumulative = 0;
  for (const [san, prob] of sorted) {
    if (cumulative >= CUMULATIVE_MASS_THRESHOLD) break;
    massSet.push(san);
    cumulative += prob;
  }

  const keep = new Set(massSet.slice(0, CANDIDATE_HARD_CAP));
  if (bestSan != null) keep.add(bestSan);
  if (playedSan != null) keep.add(playedSan); // D-07: always show played, even below the cut

  return sorted.map(([san]) => san).filter((san) => keep.has(san));
}

// ─── bucketMovesByQuality (move-quality bar, quick 260705-kfg) ────────────────

/**
 * Ordered quality buckets for the Maia move-quality bar. The 5-bucket
 * `MoveQuality` grader is collapsed to four *display* buckets — the grader's
 * separate `best` and `good` fold into one green "good" segment (the bar only
 * distinguishes severity tiers, not the single engine-best move) — plus a
 * trailing `pending` bucket for candidates the streaming grading pass hasn't
 * classified yet, so the bar's segment widths stay stable while grades arrive.
 */
export type QualityBucketKey = 'blunder' | 'mistake' | 'inaccuracy' | 'good' | 'pending';

/** Fixed left→right segment order (worst → best, pending last). */
export const QUALITY_BUCKET_ORDER: readonly QualityBucketKey[] = [
  'blunder',
  'mistake',
  'inaccuracy',
  'good',
  'pending',
] as const;

/** One move inside a bucket: its SAN and raw Maia probability at the selected ELO. */
export interface QualityBucketMove {
  san: string;
  probability: number;
}

/** A display bucket: its moves (probability-descending) and their summed mass. */
export interface QualityBucket {
  key: QualityBucketKey;
  moves: QualityBucketMove[];
  probabilityMass: number;
}

/** Map a grader `MoveQuality` (or undefined = ungraded) to its display bucket. */
function bucketKeyForQuality(quality: MoveQuality | undefined): QualityBucketKey {
  switch (quality) {
    case 'blunder':
      return 'blunder';
    case 'mistake':
      return 'mistake';
    case 'inaccuracy':
      return 'inaccuracy';
    case 'best':
    case 'good':
      return 'good';
    default:
      return 'pending'; // not yet graded (D-05 progressive fill)
  }
}

/**
 * Groups the shown candidate SANs into the ordered display buckets, using each
 * move's raw Maia probability at the rung nearest `selectedElo` as its weight.
 * Every bucket in `QUALITY_BUCKET_ORDER` is present in the result (mass 0 when
 * empty) so callers can render/skip segments by mass without re-deriving order.
 * Moves inside a bucket are sorted probability-descending.
 */
export function bucketMovesByQuality(
  perElo: MoveCurvePoint[],
  selectedElo: number,
  shownSans: string[],
  qualityBySan: Map<string, { quality: MoveQuality }>,
): QualityBucket[] {
  const rung = nearestByElo(perElo, selectedElo);
  const byKey = new Map<QualityBucketKey, QualityBucketMove[]>();
  for (const key of QUALITY_BUCKET_ORDER) byKey.set(key, []);

  for (const san of shownSans) {
    const probability = rung?.moveProbabilities[san] ?? 0;
    const key = bucketKeyForQuality(qualityBySan.get(san)?.quality);
    byKey.get(key)!.push({ san, probability });
  }

  return QUALITY_BUCKET_ORDER.map((key) => {
    const moves = byKey.get(key)!.sort((a, b) => b.probability - a.probability);
    const probabilityMass = moves.reduce((sum, m) => sum + m.probability, 0);
    return { key, moves, probabilityMass };
  });
}
