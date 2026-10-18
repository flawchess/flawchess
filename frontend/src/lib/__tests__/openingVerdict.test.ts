import { describe, expect, it } from 'vitest';
import {
  EVAL_VERDICT_BAND,
  REPERTOIRE_MIN_GAMES_FOR_VERDICT,
  SCORE_VERDICT_BAND,
  evalBaselinePawns,
  formatEvalCompact,
  formatScorePercent,
  isFadedRow,
  openingVerdict,
  openingVerdictReason,
  openingVerdictSentence,
  scoreDelta,
  stripEcoSuffix,
  verdictBandRange,
  verdictPosition,
  type OpeningVerdictInput,
} from '@/lib/openingVerdict';

const BAND = 0.3;

function input(overrides: Partial<OpeningVerdictInput> = {}): OpeningVerdictInput {
  return { delta: 0.6, band: BAND, confidence: 'high', games: 40, ...overrides };
}

describe('openingVerdictReason', () => {
  it('is better / worse for a confident, large-sample, out-of-band delta', () => {
    expect(openingVerdictReason(input({ delta: 0.6 }))).toBe('better');
    expect(openingVerdictReason(input({ delta: -0.6 }))).toBe('worse');
  });

  it('is typical inside the band, and exactly on the band edge', () => {
    expect(openingVerdictReason(input({ delta: 0.1 }))).toBe('typical');
    expect(openingVerdictReason(input({ delta: BAND }))).toBe('typical');
    expect(openingVerdictReason(input({ delta: -BAND }))).toBe('typical');
  });

  it('treats computed score deltas at 45% and 55% identically (float noise, WR-03)', () => {
    const scoreInput = (score: number): OpeningVerdictInput =>
      input({ delta: scoreDelta(score), band: SCORE_VERDICT_BAND });
    expect(openingVerdictReason(scoreInput(0.45))).toBe('typical');
    expect(openingVerdictReason(scoreInput(0.55))).toBe('typical');
    expect(openingVerdictReason(scoreInput(0.44))).toBe('worse');
    expect(openingVerdictReason(scoreInput(0.56))).toBe('better');
  });

  it('is chance when outside the band but confidence is not high', () => {
    expect(openingVerdictReason(input({ confidence: 'medium' }))).toBe('chance');
    expect(openingVerdictReason(input({ confidence: 'low', delta: -0.6 }))).toBe('chance');
  });

  it('is too-few below the game floor, and the floor itself passes', () => {
    expect(openingVerdictReason(input({ games: REPERTOIRE_MIN_GAMES_FOR_VERDICT - 1 }))).toBe('too-few');
    expect(openingVerdictReason(input({ games: REPERTOIRE_MIN_GAMES_FOR_VERDICT }))).toBe('better');
  });

  it('applies too-few before typical before chance', () => {
    // too-few beats typical (inside band) and chance (low confidence, outside band)
    expect(openingVerdictReason(input({ games: 5, delta: 0.1 }))).toBe('too-few');
    expect(openingVerdictReason(input({ games: 5, confidence: 'low' }))).toBe('too-few');
    // typical beats chance: inside the band with low confidence is typical, not chance
    expect(openingVerdictReason(input({ delta: 0.1, confidence: 'low' }))).toBe('typical');
  });
});

describe('openingVerdict', () => {
  it('passes better / worse through and maps everything else to typical', () => {
    expect(openingVerdict(input({ delta: 0.6 }))).toBe('better');
    expect(openingVerdict(input({ delta: -0.6 }))).toBe('worse');
    expect(openingVerdict(input({ delta: 0.1 }))).toBe('typical');
    expect(openingVerdict(input({ confidence: 'medium' }))).toBe('typical');
    expect(openingVerdict(input({ games: 3 }))).toBe('typical');
  });
});

describe('evalBaselinePawns', () => {
  it('is +0.25 for White and -0.25 for Black', () => {
    expect(evalBaselinePawns('white')).toBe(0.25);
    expect(evalBaselinePawns('black')).toBe(-0.25);
  });
});

describe('EVAL_VERDICT_BAND', () => {
  it('is the symmetric +/-0.30 benchmark band', () => {
    expect(EVAL_VERDICT_BAND).toBe(0.3);
  });
});

describe('verdictPosition', () => {
  it('centres zero, puts the band edges at 25 / 75, and draws higher to the right', () => {
    expect(verdictPosition(0, BAND)).toBe(50);
    expect(verdictPosition(BAND, BAND)).toBeCloseTo(75, 6);
    expect(verdictPosition(-BAND, BAND)).toBeCloseTo(25, 6);
    expect(verdictPosition(0.1, BAND)).toBeGreaterThan(50);
    expect(verdictPosition(-0.1, BAND)).toBeLessThan(50);
  });

  it('saturates short of the track edges', () => {
    expect(verdictPosition(50, BAND)).toBeLessThanOrEqual(97);
    expect(verdictPosition(50, BAND)).toBeGreaterThan(90);
    expect(verdictPosition(-50, BAND)).toBeGreaterThanOrEqual(3);
    expect(verdictPosition(-50, BAND)).toBeLessThan(10);
  });
});

describe('verdictBandRange', () => {
  it('is symmetric around the centre', () => {
    const { leftPct, widthPct } = verdictBandRange(BAND);
    expect(leftPct).toBeCloseTo(25, 6);
    expect(widthPct).toBeCloseTo(50, 6);
    expect(leftPct + widthPct / 2).toBeCloseTo(50, 6);
  });
});

describe('score and table helpers', () => {
  it('SCORE_VERDICT_BAND is the shared +/-5 point band (45% to 55%)', () => {
    expect(SCORE_VERDICT_BAND).toBe(0.05);
  });

  it('scoreDelta is the score minus 50%', () => {
    expect(scoreDelta(0.56)).toBeCloseTo(0.06, 10);
    expect(scoreDelta(0.5)).toBe(0);
    expect(scoreDelta(0.4)).toBeCloseTo(-0.1, 10);
  });

  it('formatScorePercent rounds to a whole percent', () => {
    expect(formatScorePercent(0.56)).toBe('56%');
    expect(formatScorePercent(0.5549)).toBe('55%');
    expect(formatScorePercent(0.555)).toBe('56%');
    expect(formatScorePercent(0)).toBe('0%');
  });

  it('formatEvalCompact signs, rounds to one decimal and zeroes below 0.05', () => {
    expect(formatEvalCompact(0.91)).toBe('+0.9');
    expect(formatEvalCompact(-0.44)).toBe('\u22120.4');
    expect(formatEvalCompact(0.049)).toBe('0.0');
    expect(formatEvalCompact(-0.049)).toBe('0.0');
    expect(formatEvalCompact(0.05)).toBe('+0.1');
    expect(formatEvalCompact(-1.26)).toBe('\u22121.3');
  });

  it('stripEcoSuffix drops only a trailing " (B12)" code', () => {
    expect(stripEcoSuffix('Caro-Kann Defense (B12)')).toBe('Caro-Kann Defense');
    expect(stripEcoSuffix('Caro-Kann Defense')).toBe('Caro-Kann Defense');
    expect(stripEcoSuffix("King's Pawn (Opening) Game")).toBe("King's Pawn (Opening) Game");
    expect(stripEcoSuffix('Queen\'s Gambit (D06) Accepted')).toBe("Queen's Gambit (D06) Accepted");
  });

  it('isFadedRow is true strictly below the verdict floor', () => {
    expect(isFadedRow(REPERTOIRE_MIN_GAMES_FOR_VERDICT - 1)).toBe(true);
    expect(isFadedRow(REPERTOIRE_MIN_GAMES_FOR_VERDICT)).toBe(false);
  });
});

describe('openingVerdictSentence', () => {
  it('says too few games before reading either bar', () => {
    expect(openingVerdictSentence('too-few', 'worse')).toBe('Too few games to call it yet.');
  });

  it('reads a clear score with a typical eval as the points slipping away later', () => {
    expect(openingVerdictSentence('worse', 'typical')).toBe(
      'You score below 50% even though the opening itself goes fine. The points slip away later.',
    );
  });

  it('falls back to the score-only sentence when the eval is unclear or missing', () => {
    const scoreOnly = 'You score clearly below 50% from these positions.';
    expect(openingVerdictSentence('worse', 'chance')).toBe(scoreOnly);
    expect(openingVerdictSentence('worse', 'too-few')).toBe(scoreOnly);
    expect(openingVerdictSentence('worse', null)).toBe(scoreOnly);
  });

  it('claims no "hold your own" when the score is only unclear', () => {
    expect(openingVerdictSentence('typical', 'worse')).toBe(
      'You come out of the opening worse but hold your own.',
    );
    expect(openingVerdictSentence('chance', 'worse')).toBe(
      'You come out of the opening worse than an average game.',
    );
  });

  it('still says something when neither bar stands out', () => {
    expect(openingVerdictSentence('typical', 'typical')).toBe(
      'An ordinary opening for you: average positions and a typical score.',
    );
    expect(openingVerdictSentence('typical', null)).toBe('You score in the typical range here.');
    expect(openingVerdictSentence('chance', 'typical')).toBe(
      'Average positions out of the opening. Your score could still be chance.',
    );
    expect(openingVerdictSentence('chance', 'chance')).toBe(
      'Nothing clear yet. The differences could still be chance.',
    );
  });
});
