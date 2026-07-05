/**
 * positionVerdict — pure, worker-free prose position-evaluation module for the
 * text slot below the Maia move-quality bar (quick 260705-m3z; replaces the
 * static "Hover a segment..." resting-state help text in MaiaMoveQualityBar).
 *
 * Classifies "how hard is this position to play at the selected ELO" from the
 * summed Maia probability mass of Stockfish-graded mistakes + blunders among
 * the shown candidate moves ("badMass" — inaccuracies are excluded, they're
 * not severe enough to move the verdict), then selects which moves are worth
 * naming in the sentence:
 *   - safe (badMass < SAFE_MAX_BAD_MASS): name the clean ("best"/"good")
 *     moves above the NAMED_MOVE_MIN_MASS floor, probability-descending.
 *   - tricky / difficult (badMass >= SAFE_MAX_BAD_MASS): name the bad
 *     (mistake/blunder only) moves above the floor, probability-descending,
 *     plus the single grading-search "best" move as an always-named escape
 *     (even below the floor) so a difficult position never reads as having no
 *     way out.
 *
 * Reuses moveQuality.ts's nearestByElo rung lookup (the same ELO-ladder-
 * nearest logic the bar/chart already use) rather than re-deriving it.
 */

import { nearestByElo, type MoveQuality } from '@/lib/moveQuality';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';
import { MOVE_QUALITY_BEST, MOVE_QUALITY_BLUNDER, MOVE_QUALITY_GOOD, MOVE_QUALITY_MISTAKE } from '@/lib/theme';

// ─── Types ──────────────────────────────────────────────────────────────────

/** How hard the position is to play at the selected ELO, from the badMass thresholds. */
export type VerdictTier = 'safe' | 'tricky' | 'difficult';

/** One named move surfaced in the verdict sentence, ready to render + wire to a board arrow. */
export interface VerdictMove {
  san: string;
  /** Rounded Maia probability at the selected ELO, 0-100. */
  maiaPct: number;
  role: 'good' | 'bad' | 'escape';
  textColor: string;
  arrowColor: string;
  evalCp: number | null;
  evalMate: number | null;
}

export interface PositionVerdictResult {
  tier: VerdictTier;
  /**
   * Ordered for direct rendering: safe -> good moves (probability-descending);
   * tricky/difficult -> bad moves (probability-descending) followed by the
   * escape move last, when one exists.
   */
  moves: VerdictMove[];
}

/** Per-SAN grade the caller already has (mirrors MovesByRatingChart's MoveQualityEval shape). */
export interface VerdictMoveGrade {
  quality: MoveQuality;
  evalCp: number | null;
  evalMate: number | null;
}

// ─── Constants (no magic numbers) ──────────────────────────────────────────

/** badMass strictly below this -> 'safe'. */
export const SAFE_MAX_BAD_MASS = 0.2;
/** badMass at/below this (and >= SAFE_MAX_BAD_MASS) -> 'tricky'; above -> 'difficult'. */
export const TRICKY_MAX_BAD_MASS = 0.5;
/** Minimum Maia probability mass for a move to be named in the sentence. The escape move is exempt. */
export const NAMED_MOVE_MIN_MASS = 0.08;

// ─── Eval + list formatting (exported for direct unit testing) ────────────

/**
 * White-POV eval text for the verdict sentence/tooltip: "+1.2"/"-0.8" for
 * centipawns, "M3"/"-M2" for mate (M-notation — NOT the chart tooltip's own
 * "#3"/"#-3" notation, which stays untouched).
 */
export function formatVerdictEval(evalCp: number | null, evalMate: number | null): string {
  if (evalMate !== null) return evalMate > 0 ? `M${evalMate}` : `-M${Math.abs(evalMate)}`;
  if (evalCp !== null) {
    const pawns = evalCp / 100;
    return pawns >= 0 ? `+${pawns.toFixed(1)}` : pawns.toFixed(1);
  }
  return '—';
}

/**
 * Joins move names into prose grammar: 1 -> "A"; 2 -> "A {conjunction} B";
 * 3+ -> "A, B, ... {conjunction} Z" (no comma before the final conjunction).
 */
export function joinMoveNames(names: string[], conjunction: 'and' | 'or'): string {
  if (names.length === 0) return '';
  if (names.length === 1) return names[0]!;
  const last = names[names.length - 1]!;
  if (names.length === 2) return `${names[0]} ${conjunction} ${last}`;
  return `${names.slice(0, -1).join(', ')} ${conjunction} ${last}`;
}

// ─── Internal helpers ───────────────────────────────────────────────────────

interface RankedMove {
  san: string;
  probability: number;
  grade: VerdictMoveGrade;
}

/** shownSans paired with their rung probability + grade, only where a grade already arrived (D-05). */
function rankMoves(
  rung: MoveCurvePoint | undefined,
  shownSans: string[],
  qualityBySan: Map<string, VerdictMoveGrade>,
): RankedMove[] {
  const ranked: RankedMove[] = [];
  for (const san of shownSans) {
    const grade = qualityBySan.get(san);
    if (!grade) continue;
    ranked.push({ san, probability: rung?.moveProbabilities[san] ?? 0, grade });
  }
  return ranked.sort((a, b) => b.probability - a.probability);
}

function toVerdictMove(m: RankedMove, role: VerdictMove['role'], textColor: string, arrowColor: string): VerdictMove {
  return {
    san: m.san,
    maiaPct: Math.round(m.probability * 100),
    role,
    textColor,
    arrowColor,
    evalCp: m.grade.evalCp,
    evalMate: m.grade.evalMate,
  };
}

/** Severity color for a bad (mistake/blunder) move — text and arrow share the same severity color. */
function badMoveColor(quality: MoveQuality): string {
  return quality === 'blunder' ? MOVE_QUALITY_BLUNDER : MOVE_QUALITY_MISTAKE;
}

function isGoodQuality(quality: MoveQuality): boolean {
  return quality === 'best' || quality === 'good';
}

function isBadQuality(quality: MoveQuality): boolean {
  return quality === 'mistake' || quality === 'blunder';
}

// ─── computePositionVerdict ────────────────────────────────────────────────

/**
 * Computes the prose verdict + named moves for the text slot, or `null` when
 * there's nothing to narrate yet (Maia not ready for this position, or none
 * of the shown moves have a Stockfish grade yet) — the caller should render
 * the original static help text in that case.
 */
export function computePositionVerdict(
  perElo: MoveCurvePoint[],
  selectedElo: number,
  shownSans: string[],
  qualityBySan: Map<string, VerdictMoveGrade>,
): PositionVerdictResult | null {
  const rung = nearestByElo(perElo, selectedElo);
  const ranked = rankMoves(rung, shownSans, qualityBySan);
  const totalMass = ranked.reduce((sum, m) => sum + m.probability, 0);
  if (ranked.length === 0 || totalMass <= 0) return null;

  const badMass = ranked
    .filter((m) => isBadQuality(m.grade.quality))
    .reduce((sum, m) => sum + m.probability, 0);

  const tier: VerdictTier =
    badMass < SAFE_MAX_BAD_MASS ? 'safe' : badMass <= TRICKY_MAX_BAD_MASS ? 'tricky' : 'difficult';

  if (tier === 'safe') {
    const good = ranked.filter((m) => isGoodQuality(m.grade.quality) && m.probability >= NAMED_MOVE_MIN_MASS);
    return { tier, moves: good.map((m) => toVerdictMove(m, 'good', MOVE_QUALITY_GOOD, MOVE_QUALITY_GOOD)) };
  }

  const bad = ranked.filter((m) => isBadQuality(m.grade.quality) && m.probability >= NAMED_MOVE_MIN_MASS);
  const moves = bad.map((m) => {
    const color = badMoveColor(m.grade.quality);
    return toVerdictMove(m, 'bad', color, color);
  });

  const escape = ranked.find((m) => m.grade.quality === 'best');
  if (escape) moves.push(toVerdictMove(escape, 'escape', MOVE_QUALITY_GOOD, MOVE_QUALITY_BEST));

  return { tier, moves };
}
