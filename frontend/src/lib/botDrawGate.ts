/**
 * botDrawGate — the two INDEPENDENT draw-related pure decisions (Phase 169,
 * PLAY-07): the D-04 offer-throttle counter and the D-01 bot accept-gate.
 * Modeled as two separate exported functions, never folded into one
 * boolean/enum (RESEARCH.md Pitfall 5) — "can the user click Offer draw
 * right now" (the throttle, a cooldown counter that persists across the
 * whole game) and "would the bot accept THIS offer" (an eval+endgame gate
 * evaluated fresh at each click) have different lifecycles and must stay
 * independently testable.
 *
 * D-02/D-03 (169-CONTEXT.md): the bot never offers a draw and never
 * resigns — no function in this module does either; this module only ever
 * answers "would the bot accept a user-initiated offer."
 */

import type { Chess } from 'chess.js';

/** D-04: user moves required after a declined draw offer before offering again. */
export const DRAW_OFFER_COOLDOWN_MOVES = 5;

/** D-01: near-equal band around a 0.5 expected score for the bot to consider a draw. */
export const DRAW_ACCEPT_SCORE_BAND = 0.05;

/** D-01: fallback endgame-gate fullmove threshold used when queens are still on the board. */
export const DRAW_ACCEPT_MIN_FULLMOVE = 40;

/**
 * D-04: whether the draw-offer button is currently clickable — true once at
 * least DRAW_OFFER_COOLDOWN_MOVES of the user's own moves have passed since
 * the last decline. This gates the BUTTON, not whether the bot would accept
 * — kept fully independent of wouldBotAcceptDraw's eval+endgame decision.
 */
export function canOfferDraw(movesSinceLastDecline: number): boolean {
  return movesSinceLastDecline >= DRAW_OFFER_COOLDOWN_MOVES;
}

/** True once neither side has a queen left on the board. */
function queensAreOff(chess: Chess): boolean {
  return chess.board().every((row) => row.every((piece) => piece?.type !== 'q'));
}

/**
 * D-01: whether the bot would accept a draw offer RIGHT NOW — both must
 * hold: (1) its last search's root practicalScore (the same 0-1 expected
 * score the bot already computed — reuse it, do NOT run a fresh grade) is
 * near-equal (within DRAW_ACCEPT_SCORE_BAND of 0.5), and (2) the position is
 * past an endgame/material gate — queens off the board, OR the fullmove
 * number has reached DRAW_ACCEPT_MIN_FULLMOVE as a fallback for
 * queens-still-on positions. An early, lifeless-but-equal position
 * correctly returns false: the endgame gate hasn't opened yet, so play
 * continues.
 */
export function wouldBotAcceptDraw(rootPracticalScore: number, chess: Chess): boolean {
  const isNearEqual = Math.abs(rootPracticalScore - 0.5) <= DRAW_ACCEPT_SCORE_BAND;
  if (!isNearEqual) return false;

  return queensAreOff(chess) || chess.moveNumber() >= DRAW_ACCEPT_MIN_FULLMOVE;
}
