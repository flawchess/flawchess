import { describe, it, expect } from 'vitest';

import {
  ENGINE_ARROW_GRADE_MIN_DEPTH,
  buildRankedEngineBadges,
  engineBadgeMarker,
  gradeEngineLines,
  mergeEngineBadges,
  secondaryArrowAlpha,
  stockfishSecondaryArrowColor,
  stockfishSecondaryBadgeColor,
  flawChessSecondaryAlphas,
  flawChessSecondaryArrowColor,
  flawChessSecondaryBadgeColor,
  type EngineLineGrade,
} from '@/lib/engineArrowGrades';
import { BLUNDER_DROP } from '@/generated/flawThresholds';
import { classifyLiveSeverity, evalToExpectedScore } from '@/lib/liveFlaw';
import type { PvLine } from '@/hooks/uciParser';
import type { SquareMarker } from '@/components/board/ChessBoard';
import {
  STOCKFISH_ARROW_RGB,
  STOCKFISH_BADGE_SECONDARY,
  STOCKFISH_BADGE_PRIMARY,
  FLAWCHESS_ARROW_RGB,
  FLAWCHESS_ENGINE_BADGE_PRIMARY,
  FLAWCHESS_PRIMARY_ALPHA,
  ARROW_OPACITY,
  STOCKFISH_PRIMARY_ALPHA,
  STOCKFISH_SECONDARY_ALPHA_MIN,
  STOCKFISH_SECONDARY_LINE,
} from '@/lib/theme';

const WHITE_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const BLACK_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';
const DEEP = ENGINE_ARROW_GRADE_MIN_DEPTH + 2;
const SHALLOW = ENGINE_ARROW_GRADE_MIN_DEPTH - 1;

function line(
  multipv: number,
  firstMove: string,
  evalCp: number | null,
  depth = DEEP,
  evalMate: number | null = null,
): PvLine {
  return { multipv, depth, moves: [firstMove, 'e7e5'], evalCp, evalMate };
}

describe('secondaryArrowAlpha (D-08)', () => {
  it('drop 0 and a negative drop give the primary alpha (no gap to the top arrow)', () => {
    expect(secondaryArrowAlpha(0, STOCKFISH_PRIMARY_ALPHA)).toBe(STOCKFISH_PRIMARY_ALPHA);
    expect(secondaryArrowAlpha(-0.2, STOCKFISH_PRIMARY_ALPHA)).toBe(STOCKFISH_PRIMARY_ALPHA);
    expect(secondaryArrowAlpha(0, FLAWCHESS_PRIMARY_ALPHA)).toBe(FLAWCHESS_PRIMARY_ALPHA);
  });

  it('a tiny drop stays close to the primary alpha', () => {
    expect(STOCKFISH_PRIMARY_ALPHA - secondaryArrowAlpha(0.005, STOCKFISH_PRIMARY_ALPHA)).toBeLessThan(0.02);
  });

  it('drop at or beyond BLUNDER_DROP gives MIN', () => {
    expect(secondaryArrowAlpha(BLUNDER_DROP, STOCKFISH_PRIMARY_ALPHA)).toBeCloseTo(STOCKFISH_SECONDARY_ALPHA_MIN, 10);
    expect(secondaryArrowAlpha(0.5, STOCKFISH_PRIMARY_ALPHA)).toBe(STOCKFISH_SECONDARY_ALPHA_MIN);
  });

  it('half the blunder drop lands mid-range', () => {
    expect(secondaryArrowAlpha(BLUNDER_DROP / 2, STOCKFISH_PRIMARY_ALPHA)).toBeCloseTo(
      (STOCKFISH_PRIMARY_ALPHA + STOCKFISH_SECONDARY_ALPHA_MIN) / 2,
      10,
    );
  });
});

describe('gradeEngineLines', () => {
  const top = line(1, 'e2e4', 30);

  it('grades a white-to-move list by the pipeline and aligns with the input', () => {
    const lines = [top, line(2, 'd2d4', 20), line(3, 'g1f3', -30), line(4, 'c2c4', -100), line(5, 'b2b3', -250)];
    const grades = gradeEngineLines(lines, WHITE_FEN);
    expect(grades).toHaveLength(lines.length);
    expect(grades[0]).toEqual({ quality: 'best', alpha: STOCKFISH_PRIMARY_ALPHA });
    const esTop = evalToExpectedScore(30, null, 'white');
    expect(grades.map((g) => g?.quality)).toEqual(['best', 'good', 'inaccuracy', 'mistake', 'blunder']);
    for (let k = 1; k < lines.length; k++) {
      const cp = lines[k]?.evalCp ?? 0;
      const esLine = evalToExpectedScore(cp, null, 'white');
      expect(grades[k]?.quality).toBe(classifyLiveSeverity(esTop, esLine) ?? 'good');
      expect(grades[k]?.alpha).toBe(secondaryArrowAlpha(esTop - esLine, STOCKFISH_PRIMARY_ALPHA));
    }
  });

  it('depth gate: a shallow top nulls everything, a shallow line nulls only itself', () => {
    expect(gradeEngineLines([line(1, 'e2e4', 30, SHALLOW), line(2, 'd2d4', 20)], WHITE_FEN)).toEqual([null, null]);
    const grades = gradeEngineLines([top, line(2, 'd2d4', 20, SHALLOW), line(3, 'g1f3', 20)], WHITE_FEN);
    expect(grades[0]).not.toBeNull();
    expect(grades[1]).toBeNull();
    expect(grades[2]).not.toBeNull();
  });

  it('an unscored line is null, an unscored top nulls everything, an empty list is []', () => {
    expect(gradeEngineLines([top, line(2, 'd2d4', null)], WHITE_FEN)[1]).toBeNull();
    expect(gradeEngineLines([line(1, 'e2e4', null), line(2, 'd2d4', 10)], WHITE_FEN)).toEqual([null, null]);
    expect(gradeEngineLines([], WHITE_FEN)).toEqual([]);
  });

  it('mate scores grade through the pipeline', () => {
    const mateTop = line(1, 'e2e4', null, DEEP, 3);
    const grades = gradeEngineLines([mateTop, line(2, 'd2d4', 300), line(3, 'g1f3', null, DEEP, -2)], WHITE_FEN);
    const esTop = evalToExpectedScore(null, 3, 'white');
    expect(grades[1]?.quality).toBe(classifyLiveSeverity(esTop, evalToExpectedScore(300, null, 'white')) ?? 'good');
    expect(grades[1]?.quality).toBe('blunder');
    expect(grades[2]).toEqual({ quality: 'blunder', alpha: STOCKFISH_SECONDARY_ALPHA_MIN });
  });

  it('grades from the side to move: black to move, top -200 vs line +100 is a blunder', () => {
    const grades = gradeEngineLines([line(1, 'e7e5', -200), line(2, 'd7d5', 100)], BLACK_FEN);
    expect(grades[1]?.quality).toBe('blunder');
    // Same lines from the white POV would wrongly read as good.
    expect(gradeEngineLines([line(1, 'e7e5', -200), line(2, 'd7d5', 100)], WHITE_FEN)[1]?.quality).toBe('good');
  });
});

describe('stockfishSecondaryArrowColor', () => {
  it('null falls back to the pre-gate color', () => {
    expect(stockfishSecondaryArrowColor(null)).toBe(STOCKFISH_SECONDARY_LINE);
  });

  it('a grade builds the rgba from the shared RGB and its alpha', () => {
    expect(stockfishSecondaryArrowColor({ quality: 'good', alpha: 0.5 })).toBe(`rgba(${STOCKFISH_ARROW_RGB}, 0.5)`);
  });
});

describe('stockfishSecondaryBadgeColor', () => {
  const lightness = (rgb: string): number =>
    (rgb.match(/\d+/g) ?? []).map(Number).reduce((sum, c) => sum + c, 0);

  it('null falls back to the fixed secondary badge fill', () => {
    expect(stockfishSecondaryBadgeColor(null)).toBe(STOCKFISH_BADGE_SECONDARY);
  });

  it('a top-equal line (primary alpha) gets the same fill as the best-line badge', () => {
    expect(stockfishSecondaryBadgeColor({ quality: 'good', alpha: STOCKFISH_PRIMARY_ALPHA })).toBe(
      STOCKFISH_BADGE_PRIMARY,
    );
  });

  it('a blunder-sized drop (alpha MIN) is the half-and-half mix with the light square', () => {
    expect(stockfishSecondaryBadgeColor({ quality: 'blunder', alpha: STOCKFISH_SECONDARY_ALPHA_MIN })).toBe(
      'rgb(139, 159, 209)',
    );
  });

  it('is opaque and fades lighter as the grade alpha drops', () => {
    const good = stockfishSecondaryBadgeColor({ quality: 'good', alpha: STOCKFISH_PRIMARY_ALPHA });
    const mid = stockfishSecondaryBadgeColor({ quality: 'mistake', alpha: 0.4 });
    const bad = stockfishSecondaryBadgeColor({ quality: 'blunder', alpha: STOCKFISH_SECONDARY_ALPHA_MIN });
    expect(mid).toMatch(/^rgb\(/);
    expect(lightness(good)).toBeLessThan(lightness(mid));
    expect(lightness(mid)).toBeLessThan(lightness(bad));
  });
});

describe('FlawChess grading', () => {
  it('alphas follow the practical-score drop vs the top line, aligned with the lines', () => {
    const alphas = flawChessSecondaryAlphas([
      { practicalScore: 0.6 },
      { practicalScore: 0.6 },
      { practicalScore: 0.55 },
      { practicalScore: 0.6 - BLUNDER_DROP },
    ]);
    expect(alphas).toEqual([
      FLAWCHESS_PRIMARY_ALPHA,
      FLAWCHESS_PRIMARY_ALPHA,
      secondaryArrowAlpha(0.6 - 0.55, FLAWCHESS_PRIMARY_ALPHA),
      STOCKFISH_SECONDARY_ALPHA_MIN,
    ]);
    expect(flawChessSecondaryAlphas([])).toEqual([]);
  });

  it('arrow color is the FlawChess gold at the graded alpha', () => {
    expect(flawChessSecondaryArrowColor(0.4)).toBe(`rgba(${FLAWCHESS_ARROW_RGB}, 0.4)`);
  });

  it('badge at the primary alpha matches the best-line badge; lower alphas fade toward the light square', () => {
    expect(flawChessSecondaryBadgeColor(FLAWCHESS_PRIMARY_ALPHA)).toBe(FLAWCHESS_ENGINE_BADGE_PRIMARY);
    expect(flawChessSecondaryBadgeColor(STOCKFISH_SECONDARY_ALPHA_MIN)).toBe('rgb(227, 185, 92)');
  });
});

describe('engineBadgeMarker', () => {
  it('maps quality to the marker glyph', () => {
    expect(engineBadgeMarker('e4', { quality: 'best', alpha: 0.6 }, false)).toEqual({ square: 'e4', best: true, opacity: STOCKFISH_PRIMARY_ALPHA * ARROW_OPACITY });
    expect(engineBadgeMarker('e4', { quality: 'good', alpha: 0.6 }, false)).toEqual({ square: 'e4', good: true, opacity: STOCKFISH_PRIMARY_ALPHA * ARROW_OPACITY });
    expect(engineBadgeMarker('e4', { quality: 'mistake', alpha: 0.6 }, false)).toEqual({
      square: 'e4',
      severity: 'mistake',
      opacity: STOCKFISH_PRIMARY_ALPHA * ARROW_OPACITY,
    });
  });

  it('translucent sets opacity to the grade alpha, solid to the primary arrow alpha', () => {
    const grade: EngineLineGrade = { quality: 'good', alpha: 0.4 };
    expect(engineBadgeMarker('d4', grade, true).opacity).toBe(0.4 * ARROW_OPACITY);
    expect(engineBadgeMarker('d4', grade, false).opacity).toBe(STOCKFISH_PRIMARY_ALPHA * ARROW_OPACITY);
  });
});

describe('buildRankedEngineBadges', () => {
  const lines = [line(1, 'e2e4', 30), line(2, 'd2d4', 20), line(3, 'g1f3', -250)];
  const grades = gradeEngineLines(lines, WHITE_FEN);

  it('rank 0 is a primary-alpha star, ranks 1+ translucent with their alpha, ascending order', () => {
    const badges = buildRankedEngineBadges(lines, 3, grades);
    expect(badges.map((b) => b.square)).toEqual(['e4', 'd4', 'f3']);
    expect(badges[0]).toEqual({ square: 'e4', best: true, opacity: STOCKFISH_PRIMARY_ALPHA * ARROW_OPACITY });
    expect(badges[1]?.opacity).toBe((grades[1]?.alpha ?? 0) * ARROW_OPACITY);
    expect(badges[2]?.opacity).toBe((grades[2]?.alpha ?? 0) * ARROW_OPACITY);
    expect(badges[2]?.severity).toBe('blunder');
  });

  it('count 0 gives [], a count above the line count is clamped', () => {
    expect(buildRankedEngineBadges(lines, 0, grades)).toEqual([]);
    expect(buildRankedEngineBadges(lines, 9, grades)).toHaveLength(3);
  });

  it('skips a malformed first move and an ungraded rank', () => {
    const mixed = [line(1, 'e2e4', 30), line(2, 'xx', 20), line(3, 'g1f3', 20, SHALLOW)];
    const badges = buildRankedEngineBadges(mixed, 3, gradeEngineLines(mixed, WHITE_FEN));
    expect(badges.map((b) => b.square)).toEqual(['e4']);
  });
});

describe('mergeEngineBadges (D-03)', () => {
  it('an existing marker on the same square wins', () => {
    const existing: SquareMarker[] = [{ square: 'e4', severity: 'mistake' }];
    const merged = mergeEngineBadges(existing, [{ square: 'e4', best: true }, { square: 'd4', good: true }]);
    expect(merged).toEqual([{ square: 'e4', severity: 'mistake' }, { square: 'd4', good: true }]);
  });

  it('two badges on one target keep the first', () => {
    const merged = mergeEngineBadges([], [
      { square: 'e4', best: true },
      { square: 'e4', good: true },
    ]);
    expect(merged).toEqual([{ square: 'e4', best: true }]);
  });

  it('returns the very same array when nothing is added', () => {
    const existing: SquareMarker[] = [{ square: 'e4', good: true }];
    expect(mergeEngineBadges(existing, [{ square: 'e4', best: true }])).toBe(existing);
    expect(mergeEngineBadges(existing, [])).toBe(existing);
  });
});
