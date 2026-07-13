import { Chess } from 'chess.js';
import { describe, expect, it } from 'vitest';

import { canOfferDraw, DRAW_ACCEPT_MIN_FULLMOVE, DRAW_OFFER_COOLDOWN_MOVES, wouldBotAcceptDraw } from '../botDrawGate';

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
});
