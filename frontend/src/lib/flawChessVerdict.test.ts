import { describe, expect, it } from 'vitest';
import {
  computeFlawChessVerdict,
  computeFindabilityGate,
  FINDABILITY_MARGIN,
  SHARP_DROP_THRESHOLD,
} from '@/lib/flawChessVerdict';
import { evalToExpectedScore } from '@/lib/liveFlaw';
import type { RankedLine } from '@/lib/engine/types';
import type { PvLine } from '@/hooks/uciParser';

/** Minimal RankedLine fixture — objectiveEvalCp/objectiveEvalMate are the only eval fields this module reads besides rootMove. */
function fcLine(
  rootMove: string,
  objectiveEvalCp: number | null,
  objectiveEvalMate: number | null = null,
): RankedLine {
  return {
    rootMove,
    practicalScore: 0.5,
    objectiveEvalCp,
    objectiveEvalMate,
    modalPath: [rootMove],
    modalStats: [{ objectiveEvalCp, objectiveEvalMate, maiaProb: null }],
    visits: 1,
  };
}

/** Minimal PvLine fixture — evalCp/evalMate + moves[0] are the only fields this module reads. */
function sfLine(move: string, evalCp: number | null, evalMate: number | null = null): PvLine {
  return {
    multipv: 1,
    depth: 10,
    moves: [move],
    evalCp,
    evalMate,
  };
}

describe('computeFlawChessVerdict — D-04 aligned', () => {
  it('same UCI move on both sides -> aligned, drop 0', () => {
    const fc = fcLine('g1f3', 30);
    const sf = sfLine('g1f3', 30);
    const result = computeFlawChessVerdict(fc, sf, 'white');
    expect(result?.tier).toBe('aligned');
    expect(result?.drop).toBe(0);
  });
});

describe('computeFlawChessVerdict — D-05 safe divergence', () => {
  it('divergent picks with a small win%-drop -> safe', () => {
    // white to move: FC objective +30cp, SF objective +60cp — self-checking via evalToExpectedScore
    const fcEvalCp = 30;
    const sfEvalCp = 60;
    const expectedDrop = evalToExpectedScore(sfEvalCp, null, 'white') - evalToExpectedScore(fcEvalCp, null, 'white');
    expect(expectedDrop).toBeLessThan(SHARP_DROP_THRESHOLD);

    const fc = fcLine('e2e4', fcEvalCp);
    const sf = sfLine('d2d4', sfEvalCp);
    const result = computeFlawChessVerdict(fc, sf, 'white');
    expect(result?.tier).toBe('safe');
    expect(result?.drop).toBeCloseTo(expectedDrop, 6);
  });
});

describe('computeFlawChessVerdict — D-05 sharp divergence', () => {
  it('divergent picks with a large win%-drop (trap) -> sharp', () => {
    // white to move: SF objective +300cp trap vs FC objective +40cp
    const fcEvalCp = 40;
    const sfEvalCp = 300;
    const expectedDrop = evalToExpectedScore(sfEvalCp, null, 'white') - evalToExpectedScore(fcEvalCp, null, 'white');
    expect(expectedDrop).toBeGreaterThanOrEqual(SHARP_DROP_THRESHOLD);

    const fc = fcLine('e2e4', fcEvalCp);
    const sf = sfLine('d1a4', sfEvalCp);
    const result = computeFlawChessVerdict(fc, sf, 'white');
    expect(result?.tier).toBe('sharp');
  });

  it('a drop exactly at SHARP_DROP_THRESHOLD maps to sharp (inclusive edge)', () => {
    // Solve for sfEvalCp such that the expected-score drop from fcEvalCp lands
    // exactly at SHARP_DROP_THRESHOLD, using the inverse of evalToExpectedScore's sigmoid.
    const fcEvalCp = 0;
    const fcExpectedScore = evalToExpectedScore(fcEvalCp, null, 'white');
    const targetExpectedScore = fcExpectedScore + SHARP_DROP_THRESHOLD;
    // LICHESS_K inverse: cp = ln(es/(1-es)) / K. Ceil (not round) so the resulting
    // drop lands strictly at-or-above the threshold, keeping the >= inclusive-edge
    // assertion meaningful rather than flaky under floating-point rounding.
    const LICHESS_K = 0.00368208;
    const sfEvalCp = Math.ceil(Math.log(targetExpectedScore / (1 - targetExpectedScore)) / LICHESS_K);

    const expectedDrop = evalToExpectedScore(sfEvalCp, null, 'white') - evalToExpectedScore(fcEvalCp, null, 'white');
    expect(expectedDrop).toBeCloseTo(SHARP_DROP_THRESHOLD, 2);

    const fc = fcLine('e2e4', fcEvalCp);
    const sf = sfLine('d1a4', sfEvalCp);
    const result = computeFlawChessVerdict(fc, sf, 'white');
    expect(result?.tier).toBe('sharp');
  });
});

describe('computeFlawChessVerdict — nearlySameEval / objectiveEvalGapCp gating', () => {
  it('genuinely close evals -> nearlySameEval true', () => {
    const result = computeFlawChessVerdict(fcLine('e2e4', 30), sfLine('d2d4', 60), 'white');
    expect(result?.tier).toBe('safe');
    expect(result?.objectiveEvalGapCp).toBe(30);
    expect(result?.nearlySameEval).toBe(true);
  });

  it('gap exactly at NEARLY_SAME_EVAL_CP is still "nearly the same" (inclusive)', () => {
    const result = computeFlawChessVerdict(fcLine('e2e4', 10), sfLine('d2d4', 60), 'white');
    expect(result?.objectiveEvalGapCp).toBe(50);
    expect(result?.nearlySameEval).toBe(true);
  });

  it('the screenshot case: FC pick grades HIGHER than SF best (cross-search disagreement) -> safe (drop clamps to 0) but NOT nearlySameEval', () => {
    // Qc7 objective +2.8 (a move-restricted grade) vs O-O objective +1.3 (Stockfish PV).
    const result = computeFlawChessVerdict(fcLine('d8c7', 280), sfLine('e8g8', 130), 'white');
    expect(result?.tier).toBe('safe');
    expect(result?.drop).toBe(0); // fc graded above sf -> negative pre-clamp -> 0
    expect(result?.objectiveEvalGapCp).toBe(150);
    expect(result?.nearlySameEval).toBe(false); // 150cp apart: prose must NOT say "nearly the same eval"
  });

  it('a real ~1.5-pawn concession that still classifies safe (sigmoid saturation) is NOT nearlySameEval', () => {
    // FC objective +1.3, SF objective +2.8: expected-score drop < threshold, but 150cp apart.
    const result = computeFlawChessVerdict(fcLine('e2e4', 130), sfLine('d2d4', 280), 'white');
    expect(result?.tier).toBe('safe');
    expect(result?.drop).toBeGreaterThan(0);
    expect(result?.drop).toBeLessThan(SHARP_DROP_THRESHOLD);
    expect(result?.objectiveEvalGapCp).toBe(150);
    expect(result?.nearlySameEval).toBe(false);
  });

  it('a mate on the Stockfish side -> objectiveEvalGapCp null, nearlySameEval false', () => {
    const result = computeFlawChessVerdict(fcLine('e2e4', 40), sfLine('d1h5', null, 3), 'white');
    expect(result?.objectiveEvalGapCp).toBeNull();
    expect(result?.nearlySameEval).toBe(false);
  });
});

describe('computeFlawChessVerdict — D-06 null gate', () => {
  it('flawChessLine null -> null result', () => {
    const sf = sfLine('g1f3', 30);
    expect(computeFlawChessVerdict(null, sf, 'white')).toBeNull();
  });

  it('stockfishLine null -> null result', () => {
    const fc = fcLine('g1f3', 30);
    expect(computeFlawChessVerdict(fc, null, 'white')).toBeNull();
  });

  it('FC objectiveEvalCp AND objectiveEvalMate both null -> null result', () => {
    const fc = fcLine('g1f3', null, null);
    const sf = sfLine('g1f3', 30);
    expect(computeFlawChessVerdict(fc, sf, 'white')).toBeNull();
  });

  it('SF with both evalCp and evalMate null -> null result', () => {
    const fc = fcLine('g1f3', 30);
    const sf = sfLine('d2d4', null, null);
    expect(computeFlawChessVerdict(fc, sf, 'white')).toBeNull();
  });
});

describe('computeFlawChessVerdict — mate scores on either side (quick 260709)', () => {
  it('an SF pick expressed as mate still classifies (uses the mate mapping)', () => {
    const fc = fcLine('e2e4', 40);
    const sf = sfLine('d1h5', null, 3); // mate in 3, no evalCp
    const result = computeFlawChessVerdict(fc, sf, 'white');
    expect(result).not.toBeNull();
    expect(result?.tier).toBe('sharp'); // a mate line is always a huge win%-drop over a mere +0.4
    expect(result?.stockfishMove.evalMate).toBe(3);
    expect(result?.stockfishMove.evalCp).toBeNull();
    expect(result?.flawChessMove.evalMate).toBeNull();
  });

  it('a FORCED-MATE FlawChess pick (cp null, mate set) still classifies instead of dropping the whole verdict', () => {
    // The bug: a mate leaf grades to evalMate with cp null, so the old
    // `objectiveEvalCp == null` gate returned null and the verdict slot showed the
    // muted "Turn on Stockfish" prompt even with Stockfish on. Both engines agree
    // on the mating move here -> aligned, and the FC side carries the mate.
    const fc = fcLine('f3g5', null, -4); // FlawChess sees mate in 4 (black mated), cp null
    const sf = sfLine('f3g5', null, -4);
    const result = computeFlawChessVerdict(fc, sf, 'white');
    expect(result).not.toBeNull();
    expect(result?.tier).toBe('aligned');
    expect(result?.flawChessMove.evalMate).toBe(-4);
    expect(result?.flawChessMove.evalCp).toBeNull();
    // A mate is never "nearly the same eval" as a cp number, and no cp gap exists.
    expect(result?.objectiveEvalGapCp).toBeNull();
    expect(result?.nearlySameEval).toBe(false);
  });
});

describe('computeFindabilityGate — D-10/D-11/D-12', () => {
  it('fires when the FC pick clears the margin AND is in the plotted set', () => {
    const pYouFc = 0.4;
    const pYouSf = 0.1;
    expect(pYouFc).toBeGreaterThan(pYouSf + FINDABILITY_MARGIN);
    expect(computeFindabilityGate(pYouFc, pYouSf, true)).toBe(true);
  });

  it('fails when the margin is not exceeded, even though the pick is in the plotted set', () => {
    const pYouFc = 0.12;
    const pYouSf = 0.1;
    expect(pYouFc).toBeLessThanOrEqual(pYouSf + FINDABILITY_MARGIN);
    expect(computeFindabilityGate(pYouFc, pYouSf, true)).toBe(false);
  });

  it('fails when NOT in the plotted set, even though the margin is exceeded', () => {
    const pYouFc = 0.4;
    const pYouSf = 0.1;
    expect(pYouFc).toBeGreaterThan(pYouSf + FINDABILITY_MARGIN);
    expect(computeFindabilityGate(pYouFc, pYouSf, false)).toBe(false);
  });

  it('returns false without throwing when pYouFc is null', () => {
    expect(computeFindabilityGate(null, 0.1, true)).toBe(false);
  });

  it('returns false without throwing when pYouSf is null', () => {
    expect(computeFindabilityGate(0.4, null, true)).toBe(false);
  });

  it('returns false without throwing when both are null', () => {
    expect(computeFindabilityGate(null, null, true)).toBe(false);
  });

  it('does not fire exactly at the margin boundary (strict >, not >=)', () => {
    const pYouSf = 0.1;
    const pYouFc = pYouSf + FINDABILITY_MARGIN; // exactly at the margin
    expect(computeFindabilityGate(pYouFc, pYouSf, true)).toBe(false);
  });
});

describe('computeFlawChessVerdict — mover POV (black to move)', () => {
  it('flips the sign so the drop is computed from the movers POV and remains >= 0', () => {
    // black to move: more negative white-POV cp = better for black.
    // FC objective -30 (black slightly better), SF objective -60 (black more better).
    const fc = fcLine('e7e5', -30);
    const sf = sfLine('d7d5', -60);
    const result = computeFlawChessVerdict(fc, sf, 'black');
    expect(result).not.toBeNull();
    expect(result?.drop).toBeGreaterThanOrEqual(0);
  });
});
