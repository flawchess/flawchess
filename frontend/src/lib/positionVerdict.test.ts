import { describe, expect, it } from 'vitest';
import {
  NAMED_MOVE_MIN_MASS,
  SAFE_MAX_BAD_MASS,
  STANDING_BETTER_CP,
  STANDING_DECISIVE_CP,
  TRICKY_MAX_BAD_MASS,
  classifyStanding,
  computePositionVerdict,
  formatVerdictEval,
  joinMoveNames,
  type VerdictMoveGrade,
} from '@/lib/positionVerdict';
import { formatPlayerPovEval } from '@/lib/playerPovEval';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';

const SELECTED_ELO = 1500;

/** One rung at SELECTED_ELO so nearestByElo picks it exactly (no rounding surprises). */
function rung(moveProbabilities: Record<string, number>): MoveCurvePoint[] {
  return [{ elo: SELECTED_ELO, moveProbabilities }];
}

/** computePositionVerdict defaults to a white mover in every pre-existing test below —
 *  this suite predates the mover param (quick 260709-o72) and its fixtures are already
 *  white-POV, so passing 'white' keeps every prior assertion unchanged. */
const WHITE = 'white' as const;

describe('computePositionVerdict — verdict tier thresholds (badMass = mistake + blunder mass)', () => {
  it('badMass just below 0.20 -> safe', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
      ['Bad1', { quality: 'mistake', evalCp: -80, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.81, Bad1: 0.19 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Bad1'], grades, WHITE);
    expect(verdict?.tier).toBe('safe');
  });

  it('badMass exactly 0.20 -> tricky', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
      ['Bad1', { quality: 'mistake', evalCp: -80, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.8, Bad1: SAFE_MAX_BAD_MASS });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Bad1'], grades, WHITE);
    expect(verdict?.tier).toBe('tricky');
  });

  it('badMass just above 0.20 -> tricky', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
      ['Bad1', { quality: 'mistake', evalCp: -80, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.79, Bad1: 0.21 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Bad1'], grades, WHITE);
    expect(verdict?.tier).toBe('tricky');
  });

  it('badMass just below 0.50 -> tricky', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
      ['Bad1', { quality: 'mistake', evalCp: -80, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.51, Bad1: 0.49 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Bad1'], grades, WHITE);
    expect(verdict?.tier).toBe('tricky');
  });

  it('badMass exactly 0.50 -> tricky', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
      ['Bad1', { quality: 'mistake', evalCp: -80, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.5, Bad1: TRICKY_MAX_BAD_MASS });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Bad1'], grades, WHITE);
    expect(verdict?.tier).toBe('tricky');
  });

  it('badMass just above 0.50 -> difficult', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
      ['Bad1', { quality: 'mistake', evalCp: -80, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.49, Bad1: 0.51 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Bad1'], grades, WHITE);
    expect(verdict?.tier).toBe('difficult');
  });
});

describe('computePositionVerdict — NAMED_MOVE_MIN_MASS floor filtering', () => {
  it('a good move at exactly 0.08 is included in the safe named list', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
      ['Good1', { quality: 'good', evalCp: 15, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.92, Good1: NAMED_MOVE_MIN_MASS });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Good1'], grades, WHITE);
    expect(verdict?.tier).toBe('safe');
    expect(verdict?.moves.map((m) => m.san)).toContain('Good1');
  });

  it('a good move just below 0.08 is excluded from the safe named list', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
      ['Good1', { quality: 'good', evalCp: 15, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.93, Good1: 0.07 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Good1'], grades, WHITE);
    expect(verdict?.moves.map((m) => m.san)).not.toContain('Good1');
  });

  it('a bad move at exactly 0.08 is included in the tricky named list', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
      ['Bad1', { quality: 'mistake', evalCp: -80, evalMate: null }],
      ['Bad2', { quality: 'mistake', evalCp: -90, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.62, Bad1: 0.3, Bad2: NAMED_MOVE_MIN_MASS });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Bad1', 'Bad2'], grades, WHITE);
    expect(verdict?.tier).toBe('tricky');
    expect(verdict?.moves.map((m) => m.san)).toContain('Bad2');
  });

  it('a bad move just below 0.08 is excluded from the tricky named list', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
      ['Bad1', { quality: 'mistake', evalCp: -80, evalMate: null }],
      ['Bad2', { quality: 'mistake', evalCp: -90, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.63, Bad1: 0.3, Bad2: 0.07 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Bad1', 'Bad2'], grades, WHITE);
    // Bad2 (0.07) is below the floor and excluded from the bad list, but it is
    // NOT the escape (it isn't 'best' quality), so it's simply omitted — no crash.
    expect(verdict?.moves.map((m) => m.san)).not.toContain('Bad2');
  });
});

describe('computePositionVerdict — safe tier with no good moves above the floor', () => {
  it('yields a verdict with an empty move list (verdict-only sentence), no crash', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 20, evalMate: null }],
    ]);
    // Best1 itself is below the floor -- badMass is 0 (safe) but nothing is named.
    const perElo = rung({ Best1: 0.05 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1'], grades, WHITE);
    expect(verdict?.tier).toBe('safe');
    expect(verdict?.moves).toEqual([]);
  });
});

describe('computePositionVerdict — escape move always present in tricky/difficult, even at low Maia %', () => {
  it('tricky: the best-graded move appears as the escape even far below the floor', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Escape1', { quality: 'best', evalCp: 5, evalMate: null }],
      ['Bad1', { quality: 'mistake', evalCp: -80, evalMate: null }],
    ]);
    const perElo = rung({ Escape1: 0.01, Bad1: 0.3 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Escape1', 'Bad1'], grades, WHITE);
    expect(verdict?.tier).toBe('tricky');
    const escape = verdict?.moves.find((m) => m.role === 'escape');
    expect(escape?.san).toBe('Escape1');
    expect(escape?.maiaPct).toBe(1);
  });

  it('difficult: the best-graded move appears as the escape even far below the floor', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Escape1', { quality: 'best', evalCp: 5, evalMate: null }],
      ['Bad1', { quality: 'blunder', evalCp: -400, evalMate: null }],
    ]);
    const perElo = rung({ Escape1: 0.02, Bad1: 0.7 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Escape1', 'Bad1'], grades, WHITE);
    expect(verdict?.tier).toBe('difficult');
    const escape = verdict?.moves.find((m) => m.role === 'escape');
    expect(escape?.san).toBe('Escape1');
    expect(escape?.maiaPct).toBe(2);
  });
});

describe('computePositionVerdict — no crash when no best-graded move exists', () => {
  it('omits the escape clause gracefully (no escape entry, bad list still present)', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Bad1', { quality: 'mistake', evalCp: -80, evalMate: null }],
      ['Bad2', { quality: 'blunder', evalCp: -400, evalMate: null }],
    ]);
    const perElo = rung({ Bad1: 0.3, Bad2: 0.3 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Bad1', 'Bad2'], grades, WHITE);
    expect(verdict?.tier).toBe('difficult');
    expect(verdict?.moves.some((m) => m.role === 'escape')).toBe(false);
    expect(verdict?.moves.map((m) => m.san).sort()).toEqual(['Bad1', 'Bad2']);
  });
});

describe('computePositionVerdict — not-ready sentinel', () => {
  it('returns null when perElo is empty (Maia not ready)', () => {
    expect(computePositionVerdict([], SELECTED_ELO, ['e4'], new Map(), WHITE)).toBeNull();
  });

  it('returns null when none of the shown moves have a grade yet', () => {
    const perElo = rung({ e4: 0.5, d4: 0.5 });
    expect(computePositionVerdict(perElo, SELECTED_ELO, ['e4', 'd4'], new Map(), WHITE)).toBeNull();
  });
});

describe('joinMoveNames — Oxford-comma-style grammar', () => {
  it('1 move -> "A"', () => {
    expect(joinMoveNames(['A'], 'and')).toBe('A');
  });

  it('2 moves -> "A and B"', () => {
    expect(joinMoveNames(['A', 'B'], 'and')).toBe('A and B');
  });

  it('3 moves -> "A, B and C"', () => {
    expect(joinMoveNames(['A', 'B', 'C'], 'and')).toBe('A, B and C');
  });

  it('4 moves with "or" -> "A, B, C or D"', () => {
    expect(joinMoveNames(['A', 'B', 'C', 'D'], 'or')).toBe('A, B, C or D');
  });

  it('2 moves with "or" -> "A or B"', () => {
    expect(joinMoveNames(['A', 'B'], 'or')).toBe('A or B');
  });

  it('3 moves with "or" -> "A, B or C"', () => {
    expect(joinMoveNames(['A', 'B', 'C'], 'or')).toBe('A, B or C');
  });
});

describe('formatVerdictEval — white-POV eval formatting', () => {
  it('formats a positive centipawn eval as "+1.2"', () => {
    expect(formatVerdictEval(120, null)).toBe('+1.2');
  });

  it('formats a negative centipawn eval as "-0.8"', () => {
    expect(formatVerdictEval(-80, null)).toBe('-0.8');
  });

  it('formats a positive mate eval as "M3" (not "#3")', () => {
    expect(formatVerdictEval(null, 3)).toBe('M3');
  });

  it('formats a negative mate eval as "-M2" (not "#-2")', () => {
    expect(formatVerdictEval(null, -2)).toBe('-M2');
  });

  it('formats an ungraded eval as an em dash', () => {
    expect(formatVerdictEval(null, null)).toBe('—');
  });
});

describe('classifyStanding — standing-band boundaries (quick 260709-o72)', () => {
  it('white mover: mate>0 -> mate-for-you', () => {
    expect(classifyStanding(null, 4, 'white')).toBe('mate-for-you');
  });

  it('white mover: mate<0 -> mate-against', () => {
    expect(classifyStanding(null, -4, 'white')).toBe('mate-against');
  });

  it('white mover: cp exactly STANDING_DECISIVE_CP -> winning', () => {
    expect(classifyStanding(STANDING_DECISIVE_CP, null, 'white')).toBe('winning');
  });

  it('white mover: cp just below STANDING_DECISIVE_CP -> better', () => {
    expect(classifyStanding(STANDING_DECISIVE_CP - 1, null, 'white')).toBe('better');
  });

  it('white mover: cp exactly STANDING_BETTER_CP -> better', () => {
    expect(classifyStanding(STANDING_BETTER_CP, null, 'white')).toBe('better');
  });

  it('white mover: cp just below STANDING_BETTER_CP -> level', () => {
    expect(classifyStanding(STANDING_BETTER_CP - 1, null, 'white')).toBe('level');
  });

  it('white mover: cp exactly -STANDING_BETTER_CP -> worse', () => {
    expect(classifyStanding(-STANDING_BETTER_CP, null, 'white')).toBe('worse');
  });

  it('white mover: cp just above -STANDING_BETTER_CP -> level', () => {
    expect(classifyStanding(-STANDING_BETTER_CP + 1, null, 'white')).toBe('level');
  });

  it('white mover: cp exactly -STANDING_DECISIVE_CP -> losing', () => {
    expect(classifyStanding(-STANDING_DECISIVE_CP, null, 'white')).toBe('losing');
  });

  it('white mover: cp just above -STANDING_DECISIVE_CP -> worse', () => {
    expect(classifyStanding(-STANDING_DECISIVE_CP + 1, null, 'white')).toBe('worse');
  });

  it('white mover: null eval -> level', () => {
    expect(classifyStanding(null, null, 'white')).toBe('level');
  });

  it('black mover: cp exactly STANDING_DECISIVE_CP (white-POV, good for white) -> losing for black', () => {
    expect(classifyStanding(STANDING_DECISIVE_CP, null, 'black')).toBe('losing');
  });

  it('black mover: cp exactly -STANDING_DECISIVE_CP (white-POV, good for black) -> winning for black', () => {
    expect(classifyStanding(-STANDING_DECISIVE_CP, null, 'black')).toBe('winning');
  });

  it('black mover: cp exactly STANDING_BETTER_CP -> worse for black', () => {
    expect(classifyStanding(STANDING_BETTER_CP, null, 'black')).toBe('worse');
  });

  it('black mover: cp exactly -STANDING_BETTER_CP -> better for black', () => {
    expect(classifyStanding(-STANDING_BETTER_CP, null, 'black')).toBe('better');
  });

  it('black mover: a white-POV +M4 (white mates) -> mate-against for black', () => {
    expect(classifyStanding(null, 4, 'black')).toBe('mate-against');
  });

  it('black mover: a white-POV -M4 (black mates) -> mate-for-you for black', () => {
    expect(classifyStanding(null, -4, 'black')).toBe('mate-for-you');
  });
});

describe('computePositionVerdict — standing + bestMove (quick 260709-o72)', () => {
  it('a black-mover white-POV +M4 position classifies mate-against, standingEvalMate re-signs to "-M4"', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Qxc1', { quality: 'best', evalCp: null, evalMate: 4 }],
      ['Bad1', { quality: 'blunder', evalCp: null, evalMate: 4 }],
    ]);
    const perElo = rung({ Qxc1: 0.6, Bad1: 0.4 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Qxc1', 'Bad1'], grades, 'black');
    expect(verdict?.standing).toBe('mate-against');
    expect(verdict?.standingEvalMate).toBe(4);
    expect(
      formatPlayerPovEval(verdict?.standingEvalCp ?? null, verdict?.standingEvalMate ?? null, 'black'),
    ).toBe('-M4');
  });

  it('bestMove is the "best"-graded candidate, even when a bad candidate has a nominally higher raw cp', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Best1', { quality: 'best', evalCp: 40, evalMate: null }],
      ['Bad1', { quality: 'blunder', evalCp: 999, evalMate: null }],
    ]);
    const perElo = rung({ Best1: 0.6, Bad1: 0.4 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Best1', 'Bad1'], grades, 'white');
    expect(verdict?.bestMove?.san).toBe('Best1');
    expect(verdict?.standingEvalCp).toBe(40);
  });

  it('falls back to the highest mover-POV eval when no candidate is "best"-graded', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Good1', { quality: 'good', evalCp: 120, evalMate: null }],
      ['Mistake1', { quality: 'mistake', evalCp: -80, evalMate: null }],
    ]);
    const perElo = rung({ Good1: 0.6, Mistake1: 0.4 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Good1', 'Mistake1'], grades, 'white');
    expect(verdict?.bestMove?.san).toBe('Good1');
    expect(verdict?.standing).toBe('better');
  });

  it('no candidate has an eval -> standing level, standingEval* null, bestMove null', () => {
    const grades = new Map<string, VerdictMoveGrade>([
      ['Bad1', { quality: 'mistake', evalCp: null, evalMate: null }],
    ]);
    const perElo = rung({ Bad1: 0.5 });
    const verdict = computePositionVerdict(perElo, SELECTED_ELO, ['Bad1'], grades, 'white');
    expect(verdict?.standing).toBe('level');
    expect(verdict?.standingEvalCp).toBeNull();
    expect(verdict?.standingEvalMate).toBeNull();
    expect(verdict?.bestMove).toBeNull();
  });
});
