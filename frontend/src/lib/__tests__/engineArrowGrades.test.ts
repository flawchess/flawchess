import { describe, it, expect } from 'vitest';

import {
  ENGINE_ARROW_GRADE_MIN_DEPTH,
  buildRankedEngineBadges,
  engineBadgeMarker,
  gradeEngineLines,
  mergeEngineBadges,
  secondaryArrowAlpha,
  stockfishSecondaryArrowColor,
  type EngineLineGrade,
} from '@/lib/engineArrowGrades';
import { BLUNDER_DROP } from '@/generated/flawThresholds';
import { classifyLiveSeverity, evalToExpectedScore } from '@/lib/liveFlaw';
import type { PvLine } from '@/hooks/uciParser';
import type { SquareMarker } from '@/components/board/ChessBoard';
import {
  STOCKFISH_ARROW_RGB,
  STOCKFISH_SECONDARY_ALPHA_MAX,
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
  it('drop 0 and a negative drop give MAX', () => {
    expect(secondaryArrowAlpha(0)).toBe(STOCKFISH_SECONDARY_ALPHA_MAX);
    expect(secondaryArrowAlpha(-0.2)).toBe(STOCKFISH_SECONDARY_ALPHA_MAX);
  });

  it('drop at or beyond BLUNDER_DROP gives MIN', () => {
    expect(secondaryArrowAlpha(BLUNDER_DROP)).toBeCloseTo(STOCKFISH_SECONDARY_ALPHA_MIN, 10);
    expect(secondaryArrowAlpha(0.5)).toBe(STOCKFISH_SECONDARY_ALPHA_MIN);
  });

  it('half the blunder drop lands mid-range', () => {
    expect(secondaryArrowAlpha(BLUNDER_DROP / 2)).toBeCloseTo(
      (STOCKFISH_SECONDARY_ALPHA_MAX + STOCKFISH_SECONDARY_ALPHA_MIN) / 2,
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
    expect(grades[0]).toEqual({ quality: 'best', alpha: STOCKFISH_SECONDARY_ALPHA_MAX });
    const esTop = evalToExpectedScore(30, null, 'white');
    expect(grades.map((g) => g?.quality)).toEqual(['best', 'good', 'inaccuracy', 'mistake', 'blunder']);
    for (let k = 1; k < lines.length; k++) {
      const cp = lines[k]?.evalCp ?? 0;
      const esLine = evalToExpectedScore(cp, null, 'white');
      expect(grades[k]?.quality).toBe(classifyLiveSeverity(esTop, esLine) ?? 'good');
      expect(grades[k]?.alpha).toBe(secondaryArrowAlpha(esTop - esLine));
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

describe('engineBadgeMarker', () => {
  it('maps quality to the marker glyph', () => {
    expect(engineBadgeMarker('e4', { quality: 'best', alpha: 0.6 }, false)).toEqual({ square: 'e4', best: true });
    expect(engineBadgeMarker('e4', { quality: 'good', alpha: 0.6 }, false)).toEqual({ square: 'e4', good: true });
    expect(engineBadgeMarker('e4', { quality: 'mistake', alpha: 0.6 }, false)).toEqual({
      square: 'e4',
      severity: 'mistake',
    });
  });

  it('translucent sets opacity to the grade alpha, solid leaves it absent', () => {
    const grade: EngineLineGrade = { quality: 'good', alpha: 0.4 };
    expect(engineBadgeMarker('d4', grade, true).opacity).toBe(0.4);
    expect('opacity' in engineBadgeMarker('d4', grade, false)).toBe(false);
  });
});

describe('buildRankedEngineBadges', () => {
  const lines = [line(1, 'e2e4', 30), line(2, 'd2d4', 20), line(3, 'g1f3', -250)];
  const grades = gradeEngineLines(lines, WHITE_FEN);

  it('rank 0 is an opaque star, ranks 1+ translucent with their alpha, ascending order', () => {
    const badges = buildRankedEngineBadges(lines, 3, grades);
    expect(badges.map((b) => b.square)).toEqual(['e4', 'd4', 'f3']);
    expect(badges[0]).toEqual({ square: 'e4', best: true });
    expect(badges[1]?.opacity).toBe(grades[1]?.alpha);
    expect(badges[2]?.opacity).toBe(grades[2]?.alpha);
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
