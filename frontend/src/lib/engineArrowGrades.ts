/**
 * engineArrowGrades — pure grading of live Stockfish lines for the board arrows
 * (quick 261012-a6m, D-01..D-08).
 *
 * ONE grade pass per position feeds BOTH the arrow alpha and the move-quality badge
 * (and the badge opacity), so an arrow and its icon can never disagree. The Analysis
 * board (useAnalysisBoardArrows) and the Train step/free-play boards (trainArrows)
 * share this module.
 *
 * Grading reuses the app's expected-score pipeline (liveFlaw): each line's eval is
 * converted to the side-to-move's expected score and compared with the top line via
 * classifyLiveSeverity, so no new cutoff is introduced. Rank 0 is 'best'; a line that
 * is not an inaccuracy/mistake/blunder is 'good' (D-05).
 *
 * Pure: no React, never throws.
 */

import type { SquareMarker } from '@/components/board/ChessBoard';
import type { PvLine } from '@/hooks/uciParser';
import { BLUNDER_DROP } from '@/generated/flawThresholds';
import {
  classifyLiveSeverity,
  evalToExpectedScore,
  sideToMoveFromFen,
  type FlawSeverity,
} from '@/lib/liveFlaw';
import { uciToSquares } from '@/lib/sanToSquares';
import {
  STOCKFISH_ARROW_RGB,
  STOCKFISH_SECONDARY_ALPHA_MAX,
  STOCKFISH_SECONDARY_ALPHA_MIN,
  STOCKFISH_SECONDARY_LINE,
} from '@/lib/theme';

/**
 * Minimum search depth (of the top line AND the graded line) before alpha and badges
 * appear (D-02). Same value as TRAIN_LIVE_ALT_MIN_DEPTH / GRADING_DEPTH_FLOOR, but its
 * own constant: trainArrows imports this module (importing back would be a cycle) and
 * retuning the bot grading ladder must not move this display gate.
 */
export const ENGINE_ARROW_GRADE_MIN_DEPTH = 10;

export type EngineArrowQuality = 'best' | 'good' | FlawSeverity;

export interface EngineLineGrade {
  quality: EngineArrowQuality;
  /** The translucent arrow's color alpha AND its badge opacity (D-08). */
  alpha: number;
}

/**
 * Linear alpha for a secondary arrow from its expected-score drop vs the top line:
 * drop <= 0 gives MAX, drop >= BLUNDER_DROP gives MIN (D-08).
 */
export function secondaryArrowAlpha(drop: number): number {
  const t = Math.min(Math.max(drop, 0), BLUNDER_DROP) / BLUNDER_DROP;
  return STOCKFISH_SECONDARY_ALPHA_MAX - t * (STOCKFISH_SECONDARY_ALPHA_MAX - STOCKFISH_SECONDARY_ALPHA_MIN);
}

function isGradable(line: PvLine | undefined): line is PvLine {
  if (line === undefined) return false;
  if (line.depth < ENGINE_ARROW_GRADE_MIN_DEPTH) return false;
  return line.evalCp !== null || line.evalMate !== null;
}

/**
 * Grades every line against the top line (index 0), aligned 1:1 with `lines`.
 * Everything is null until the top line is deep and scored (D-02); an individual
 * secondary is null when it is itself shallow or unscored.
 */
export function gradeEngineLines(
  lines: readonly PvLine[],
  fen: string,
): Array<EngineLineGrade | null> {
  const top = lines[0];
  if (!isGradable(top)) return lines.map(() => null);
  const mover = sideToMoveFromFen(fen);
  const esTop = evalToExpectedScore(top.evalCp, top.evalMate, mover);
  return lines.map((line, index) => {
    if (index === 0) return { quality: 'best', alpha: secondaryArrowAlpha(0) };
    if (!isGradable(line)) return null;
    const esLine = evalToExpectedScore(line.evalCp, line.evalMate, mover);
    return {
      quality: classifyLiveSeverity(esTop, esLine) ?? 'good',
      alpha: secondaryArrowAlpha(esTop - esLine),
    };
  });
}

/** Translucent Stockfish arrow color: the graded alpha, or the pre-gate fixed look. */
export function stockfishSecondaryArrowColor(grade: EngineLineGrade | null): string {
  if (grade === null) return STOCKFISH_SECONDARY_LINE;
  return `rgba(${STOCKFISH_ARROW_RGB}, ${grade.alpha})`;
}

/**
 * The corner badge for a graded arrow target. `translucent` badges take the grade
 * alpha as group opacity (they sit on a translucent arrow); solid ones stay opaque.
 */
export function engineBadgeMarker(
  square: string,
  grade: EngineLineGrade,
  translucent: boolean,
): SquareMarker {
  const marker: SquareMarker =
    grade.quality === 'best'
      ? { square, best: true }
      : grade.quality === 'good'
        ? { square, good: true }
        : { square, severity: grade.quality };
  return translucent ? { ...marker, opacity: grade.alpha } : marker;
}

/**
 * Badge candidates for ranks 0..min(count, lines.length)-1 in ASCENDING rank order
 * (precedence order for mergeEngineBadges). Rank 0 is the solid arrow (opaque star);
 * ranks 1+ are translucent. Malformed first moves and ungraded ranks are skipped.
 */
export function buildRankedEngineBadges(
  lines: readonly PvLine[],
  count: number,
  grades: ReadonlyArray<EngineLineGrade | null>,
): SquareMarker[] {
  const badges: SquareMarker[] = [];
  for (let rank = 0; rank < Math.min(count, lines.length); rank++) {
    const grade = grades[rank] ?? null;
    const squares = uciToSquares(lines[rank]?.moves[0] ?? null);
    if (grade === null || squares === null) continue;
    badges.push(engineBadgeMarker(squares.to, grade, rank > 0));
  }
  return badges;
}

/**
 * Single collision authority (D-03): an existing marker on a square wins, and of two
 * badges on one square the earlier (higher-ranked) one wins. Returns `existing` itself
 * when nothing is kept so memoized consumers keep a stable identity.
 */
export function mergeEngineBadges(
  existing: SquareMarker[],
  badges: readonly SquareMarker[],
): SquareMarker[] {
  const used = new Set(existing.map((m) => m.square));
  const kept: SquareMarker[] = [];
  for (const badge of badges) {
    if (used.has(badge.square)) continue;
    used.add(badge.square);
    kept.push(badge);
  }
  return kept.length === 0 ? existing : [...existing, ...kept];
}
