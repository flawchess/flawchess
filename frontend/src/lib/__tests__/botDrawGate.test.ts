import { Chess } from 'chess.js';
import { describe, expect, it } from 'vitest';

import {
  canOfferDraw,
  DRAW_ACCEPT_MIN_FULLMOVE,
  DRAW_OFFER_COOLDOWN_MOVES,
  RESIGN_HYSTERESIS_TURNS,
  RESIGN_MIN_FULLMOVE,
  wouldBotAcceptDraw,
  wouldBotResign,
} from '../botDrawGate';

describe('canOfferDraw', () => {
  it('is false just below the cooldown threshold', () => {
    expect(canOfferDraw(DRAW_OFFER_COOLDOWN_MOVES - 1)).toBe(false);
  });

  it('is true once the cooldown threshold is reached', () => {
    expect(canOfferDraw(DRAW_OFFER_COOLDOWN_MOVES)).toBe(true);
  });
});

describe('wouldBotAcceptDraw', () => {
  it('declines a near-equal score in an early queens-on position', () => {
    const chess = new Chess(); // starting position: queens on, fullmove 1
    expect(wouldBotAcceptDraw(0.5, chess)).toBe(false);
  });

  it('accepts a near-equal score once queens are off the board', () => {
    const chess = new Chess('4k3/8/8/8/8/8/8/4K3 w - - 0 1');
    expect(wouldBotAcceptDraw(0.5, chess)).toBe(true);
  });

  it('accepts a near-equal score once the fullmove fallback threshold is reached with queens still on', () => {
    const chess = new Chess(`4k3/8/8/8/8/8/3Q4/4K3 w - - 0 ${DRAW_ACCEPT_MIN_FULLMOVE}`);
    expect(wouldBotAcceptDraw(0.5, chess)).toBe(true);
  });

  it('declines a lopsided score even past the endgame gate', () => {
    const chess = new Chess('4k3/8/8/8/8/8/8/4K3 w - - 0 1'); // queens off
    expect(wouldBotAcceptDraw(0.9, chess)).toBe(false);
  });

  it('declines a lopsided score with queens still on and past the fullmove fallback', () => {
    const chess = new Chess(`4k3/8/8/8/8/8/3Q4/4K3 w - - 0 ${DRAW_ACCEPT_MIN_FULLMOVE}`);
    expect(wouldBotAcceptDraw(0.05, chess)).toBe(false);
  });

  it('declines on the not-yet-evaluated sentinel even with queens off the board', () => {
    // Phase 169.5. The point of this case is precisely that it is QUEENS-OFF:
    // the endgame gate is wide open and a 0.5 score would be accepted here
    // (see the 'accepts a near-equal score once queens are off' case above,
    // same FEN). Only the null sentinel — the bot has evaluated nothing this
    // game — stops the accept. Reachable for real: the opening book runs zero
    // Stockfish evals, and the ECO corpus contains queens-off lines inside
    // the book's ply cap.
    const chess = new Chess('4k3/8/8/8/8/8/8/4K3 w - - 0 1');
    expect(wouldBotAcceptDraw(null, chess)).toBe(false);
  });

  describe('contempt (D-09, Phase 182)', () => {
    it('with contempt omitted, is identical to the pre-182 (no-contempt) behavior', () => {
      const chess = new Chess('4k3/8/8/8/8/8/8/4K3 w - - 0 1'); // queens off
      expect(wouldBotAcceptDraw(0.5, chess)).toBe(wouldBotAcceptDraw(0.5, chess, 0));
      expect(wouldBotAcceptDraw(0.5, chess, 0)).toBe(true);
    });

    it('positive contempt (Grinder-like) refuses a level position a neutral (contempt=0) bot would accept', () => {
      // CR-01 (182-REVIEW.md): asserts the DOCUMENTED behavioral intent, not
      // the formula — a positive-contempt style (e.g. Grinder, 0.15) "wants
      // meaningfully more than dead-equal before accepting," so it must keep
      // playing on a dead-equal (0.5) score that a neutral bot would accept.
      const chess = new Chess('4k3/8/8/8/8/8/8/4K3 w - - 0 1'); // queens off
      expect(wouldBotAcceptDraw(0.5, chess, 0)).toBe(true); // neutral: accepts dead-equal
      // drawValue = 0.5 + 0.2 = 0.7; a dead-equal 0.5 score is now outside the
      // shifted band [0.65, 0.75] — the Grinder-like bot refuses and plays on.
      expect(wouldBotAcceptDraw(0.5, chess, 0.2)).toBe(false);
      // And it DOES accept once genuinely ahead (0.7, inside the shifted
      // band) — the sign that actually distinguishes the fix from the
      // inverted formula (a lopsided-loss 0.5-refusal alone is ambiguous
      // between the two signs; this assertion is not).
      expect(wouldBotAcceptDraw(0.7, chess, 0.2)).toBe(true);
    });

    it('negative contempt (Wall-like) accepts a mildly-worse position a neutral (contempt=0) bot would decline', () => {
      // CR-01 (182-REVIEW.md): a negative-contempt style (e.g. Wall, -0.08)
      // "welcomes an early draw a bit more readily than dead-equal," so it
      // must accept even a mildly-worse-than-equal position.
      const chess = new Chess('4k3/8/8/8/8/8/8/4K3 w - - 0 1'); // queens off
      // drawValue = 0.5 + (-0.2) = 0.3; a mildly-worse 0.32 score falls inside
      // the shifted band [0.25, 0.35] — the Wall-like bot accepts.
      expect(wouldBotAcceptDraw(0.32, chess, -0.2)).toBe(true);
      // Unshifted (contempt=0), the same 0.32 score is refused (outside the
      // neutral 0.5 band [0.45, 0.55]) — proving the shift is what changed it.
      expect(wouldBotAcceptDraw(0.32, chess, 0)).toBe(false);
    });

    it('the null sentinel is refused regardless of contempt', () => {
      const chess = new Chess('4k3/8/8/8/8/8/8/4K3 w - - 0 1'); // queens off
      expect(wouldBotAcceptDraw(null, chess, 0.2)).toBe(false);
      expect(wouldBotAcceptDraw(null, chess, -0.2)).toBe(false);
    });
  });
});

describe('wouldBotResign (D-07/D-08, Phase 182)', () => {
  const RESIGN_THRESHOLD = 0.1;

  function pastMinMoveChess(): Chess {
    return new Chess(`4k3/8/8/8/8/8/8/4K3 w - - 0 ${RESIGN_MIN_FULLMOVE}`);
  }

  function earlyGameChess(): Chess {
    return new Chess('4k3/8/8/8/8/8/8/4K3 w - - 0 1');
  }

  it('returns false for the not-yet-evaluated null sentinel, regardless of the other args', () => {
    expect(wouldBotResign(null, RESIGN_THRESHOLD, RESIGN_HYSTERESIS_TURNS, RESIGN_HYSTERESIS_TURNS, pastMinMoveChess())).toBe(
      false,
    );
    expect(wouldBotResign(null, RESIGN_THRESHOLD, 0, 0, earlyGameChess())).toBe(false);
  });

  it('returns false when the losing score has not yet stayed below the hysteresis floor', () => {
    const chess = pastMinMoveChess();
    expect(
      wouldBotResign(0.05, RESIGN_THRESHOLD, RESIGN_HYSTERESIS_TURNS - 1, RESIGN_HYSTERESIS_TURNS, chess),
    ).toBe(false);
  });

  it('returns true once the losing score has stayed at the hysteresis floor past the min fullmove', () => {
    const chess = pastMinMoveChess();
    expect(wouldBotResign(0.05, RESIGN_THRESHOLD, RESIGN_HYSTERESIS_TURNS, RESIGN_HYSTERESIS_TURNS, chess)).toBe(
      true,
    );
  });

  it('returns false for an early-game losing score at/above the hysteresis floor but before RESIGN_MIN_FULLMOVE', () => {
    const chess = earlyGameChess();
    expect(wouldBotResign(0.05, RESIGN_THRESHOLD, RESIGN_HYSTERESIS_TURNS, RESIGN_HYSTERESIS_TURNS, chess)).toBe(
      false,
    );
  });

  it('returns false when the score is above the resign threshold, even past the floor and min fullmove', () => {
    const chess = pastMinMoveChess();
    expect(wouldBotResign(0.5, RESIGN_THRESHOLD, RESIGN_HYSTERESIS_TURNS, RESIGN_HYSTERESIS_TURNS, chess)).toBe(
      false,
    );
  });

  it('is idempotent: identical arguments always return the identical result', () => {
    const chess = pastMinMoveChess();
    const first = wouldBotResign(0.05, RESIGN_THRESHOLD, RESIGN_HYSTERESIS_TURNS, RESIGN_HYSTERESIS_TURNS, chess);
    const second = wouldBotResign(0.05, RESIGN_THRESHOLD, RESIGN_HYSTERESIS_TURNS, RESIGN_HYSTERESIS_TURNS, chess);
    expect(first).toBe(second);
    expect(first).toBe(true);
  });
});
