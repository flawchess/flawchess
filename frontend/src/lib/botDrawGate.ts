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
 *
 * SUPERSEDED for STYLED bots only (Phase 182, D-07, STYLE-02): a styled bot
 * MAY resign (`wouldBotResign`, below) and its draw-accept target may be
 * shifted off dead-center 0.5 by a signed `contempt` knob (D-09). Unstyled
 * bots keep the exact Phase 169 D-02/D-03 behavior by construction — every
 * new parameter here defaults to the old no-op value (`contempt = 0`), and
 * `wouldBotResign` is opt-in: nothing calls it unless a style supplies a
 * resign threshold (wiring is Plan 07, not this module).
 */

import type { Chess } from 'chess.js';

/** D-04: user moves required after a declined draw offer before offering again. */
export const DRAW_OFFER_COOLDOWN_MOVES = 5;

/** D-01: near-equal band around a 0.5 expected score for the bot to consider a draw. */
export const DRAW_ACCEPT_SCORE_BAND = 0.05;

/** D-01: fallback endgame-gate fullmove threshold used when queens are still on the board. */
export const DRAW_ACCEPT_MIN_FULLMOVE = 40;

/**
 * D-08: earliest fullmove at which a styled bot is permitted to resign, even
 * if its score and hysteresis counter already qualify. Mirrors
 * DRAW_ACCEPT_MIN_FULLMOVE's role as a fallback "don't judge an unsettled
 * early position" gate — a losing opening shouldn't trigger a resignation
 * before the game has had a chance to develop. [ASSUMED] hand-tuned; retune
 * in place if resignations feel premature.
 */
export const RESIGN_MIN_FULLMOVE = 20;

/**
 * D-08: reference number of consecutive own turns rootPracticalScore must
 * stay at or below a style's resignThreshold before wouldBotResign returns
 * true. WR-03 (182-REVIEW.md): `BotStyleParams.hysteresisFloor` is a
 * REQUIRED field on every shipped bundle (`botStyle.ts`) and every
 * production call site (`useBotGame.ts`) sources it directly from
 * `settings.style.hysteresisFloor` — there is currently no code path that
 * falls back to this constant. It exists as the hand-tuned reference
 * magnitude the 4 bundles' own `hysteresisFloor` values were picked around
 * (`botStyleBundles.ts`'s cross-style ordering assertions compare against
 * it), NOT as a live runtime default. [ASSUMED] hand-tuned to avoid
 * resigning off a single bad move; retune in place.
 */
export const RESIGN_HYSTERESIS_TURNS = 4;

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
 * D-01: whether the bot would accept a draw offer RIGHT NOW.
 *
 * `rootPracticalScore` is a SENTINEL-BEARING parameter (Phase 169.5):
 * - `null` = the bot has not evaluated any position yet this game. It must
 *   NOT accept — a draw is a game-ending decision and the bot may never make
 *   one off a number it never computed. Refused immediately, before the board
 *   is even looked at. There is deliberately no numeric default here: the
 *   opening book (169.5) runs zero Stockfish evals for the whole book window,
 *   so this sentinel is genuinely reachable — and because the endgame gate
 *   below opens on queens-off ALONE, and the shipped ECO corpus contains
 *   queens-off lines inside the book's ply cap (openings.tsv:1065, the
 *   Caro-Kann Endgame Variation, has queens off by ply 9), a `0.5` default
 *   would sit dead-center in DRAW_ACCEPT_SCORE_BAND and hand out a draw in a
 *   position the bot never looked at.
 * - a number = a real root practicalScore from the bot's own last search
 *   (the same 0-1 expected score it already computed — reuse it, do NOT run a
 *   fresh grade).
 *
 * `contempt` (Phase 182, D-09) is an optional signed shift, in expected-score
 * units, off the dead-center 0.5 accept target — `drawValue = 0.5 + contempt`.
 * Positive contempt (e.g. Grinder) moves the target ABOVE 0.5, so the bot
 * must be genuinely ahead before a position counts as "near-equal enough to
 * accept" (it wants more than dead-equal before it settles). Negative
 * contempt (e.g. Wall) moves the target BELOW 0.5, so a slightly-worse
 * position can still be accepted. The band WIDTH (`DRAW_ACCEPT_SCORE_BAND`)
 * is unchanged — contempt shifts the center only, never widens or narrows
 * the window. Defaults to `0`, which reduces `drawValue` back to `0.5` —
 * byte-identical to the pre-182 behavior for every existing 2-arg caller.
 *
 * With a real score, BOTH must hold: (1) it is near the (possibly shifted)
 * draw value (within DRAW_ACCEPT_SCORE_BAND), and (2) the position is past an
 * endgame/material gate — queens off the board, OR the fullmove number has
 * reached DRAW_ACCEPT_MIN_FULLMOVE as a fallback for queens-still-on
 * positions. An early, lifeless-but-equal position correctly returns false:
 * the endgame gate hasn't opened yet, so play continues.
 */
export function wouldBotAcceptDraw(
  rootPracticalScore: number | null,
  chess: Chess,
  contempt = 0,
): boolean {
  // Not-yet-evaluated: refuse before anything else (see the sentinel note above).
  if (rootPracticalScore === null) return false;

  // CR-01 fix (182-REVIEW.md): this was `0.5 - contempt`, which inverted
  // every style's documented draw-accept behavior (positive contempt was
  // producing a BELOW-0.5 target — accepting off a losing score — and
  // negative contempt an ABOVE-0.5 target). `rootPracticalScore` is the
  // bot's own-POV expected score (higher = better for the bot), so a
  // "wants more before settling" style (positive contempt, e.g. Grinder)
  // must raise the target ABOVE 0.5, and a "settles for less" style
  // (negative contempt, e.g. Wall) must lower it BELOW 0.5 — i.e. `+`.
  const drawValue = 0.5 + contempt; // D-09: contempt shifts the accept target, never the band width.
  const isNearEqual = Math.abs(rootPracticalScore - drawValue) <= DRAW_ACCEPT_SCORE_BAND;
  if (!isNearEqual) return false;

  return queensAreOff(chess) || chess.moveNumber() >= DRAW_ACCEPT_MIN_FULLMOVE;
}

/**
 * D-07/D-08 (Phase 182, STYLE-02): whether a styled bot would resign RIGHT
 * NOW. A pure predicate over its five arguments — it holds NO state itself
 * (Pitfall 3, 182-RESEARCH.md). The hysteresis counter
 * (`consecutiveLowTurns`) is the CALLER's job: `useBotGame.ts` owns a
 * per-game ref, incremented/reset alongside the game's other latches
 * (`hasLeftBookRef`, `lastRootPracticalScoreRef`) and reset in `newGame()`.
 * This function never reads or writes any external or module-level state,
 * so calling it twice with identical arguments always yields the identical
 * result (idempotent).
 *
 * `rootPracticalScore` is the SAME sentinel-bearing parameter as
 * `wouldBotAcceptDraw`'s: `null` means the bot has not evaluated any
 * position yet this game (Human rungs, which never search, and the opening
 * book window, which runs zero Stockfish evals). It is refused FIRST and
 * UNCONDITIONALLY, before any other argument is even looked at — a bot must
 * never resign off a score it never computed (D-08: Human-rung bots
 * therefore automatically never resign, with no extra branching required
 * here).
 *
 * With a real score, ALL of the following must hold for a resign:
 * 1. `rootPracticalScore <= resignThreshold` — the position is genuinely
 *    losing by the style's own bar (a style param, not a constant here).
 * 2. `consecutiveLowTurns >= hysteresisFloor` — the score has stayed at or
 *    below the threshold for enough of the bot's OWN consecutive turns in a
 *    row (also a style param); a single bad move never triggers a
 *    resignation.
 * 3. `chess.moveNumber() >= RESIGN_MIN_FULLMOVE` — the game is past the
 *    early-development window (mirrors DRAW_ACCEPT_MIN_FULLMOVE's role).
 */
/**
 * D-07/Pitfall 1 (Phase 183, RESEARCH.md): near-equal band around the
 * (possibly contempt-shifted) draw target the BOT itself uses when deciding
 * whether to OFFER a draw. Independent of `DRAW_ACCEPT_SCORE_BAND` by
 * construction (Pitfall 7: no gate here may blindly reuse another gate's
 * value) but currently tuned to the same width — offering and accepting
 * should agree on what counts as a legitimately equal position, and there is
 * no signal yet that the offer trigger needs a tighter/looser window. Retune
 * in place if bots offer draws that feel premature or too rare relative to
 * their own accept behavior. [ASSUMED] hand-tuned; retune in place.
 */
export const BOT_DRAW_OFFER_SCORE_BAND = 0.05;

/**
 * D-07/Pitfall 7 (Phase 183): earliest fullmove at which a bot is permitted
 * to OFFER a draw, even if its score and cooldown already qualify. Picked
 * independently from `DRAW_ACCEPT_MIN_FULLMOVE` (40) and `RESIGN_MIN_FULLMOVE`
 * (20): offering is a bot-INITIATED, declarative action (stronger than merely
 * tolerating a user's offer or an ongoing loss), so it sits between the two —
 * later than a resignation floor (a losing bot shouldn't need to wait as long
 * to give up as an equal bot needs to wait to propose a truce), earlier than
 * the accept fallback (a bot doesn't need to wait for `wouldBotAcceptDraw`'s
 * full endgame-adjacent floor before it's willing to PROPOSE, only before it
 * accepts one). [ASSUMED] hand-tuned; retune in place if offers feel
 * premature or too late relative to how a real opponent would propose one.
 */
export const BOT_DRAW_OFFER_MIN_FULLMOVE = 30;

/**
 * D-07 (Phase 183): minimum number of the BOT's OWN moves that must pass
 * between two successive outgoing offers. This is a SEPARATE counter from
 * `DRAW_OFFER_COOLDOWN_MOVES` (which throttles the USER's offer BUTTON) —
 * `movesSinceOwnOffer` is caller-owned (mirrors `wouldBotResign`'s
 * caller-owned hysteresis counter; Plan 03 wires the ref), incremented each
 * bot turn and reset to 0 whenever the bot itself offers. [ASSUMED]
 * hand-tuned to prevent offer spam every few moves; retune in place.
 */
export const BOT_DRAW_OFFER_COOLDOWN_MOVES = 6;

/**
 * D-07/Pitfall 1 (Phase 183, RESEARCH.md A4): whether a styled bot would
 * OFFER a draw RIGHT NOW — the outgoing counterpart to `wouldBotAcceptDraw`
 * (which only answers "would the bot accept a USER-initiated offer"). A
 * pure predicate over its four arguments — it holds NO state itself (mirrors
 * `wouldBotResign`'s Pitfall-3 discipline): the own-offer cooldown counter
 * (`movesSinceOwnOffer`) is the CALLER's job (Plan 03's `useBotGame.ts`
 * owns the ref, incremented/reset alongside its other per-game latches),
 * never read from or written to module-level state here. Calling this
 * function twice with identical arguments always yields the identical
 * result.
 *
 * `rootPracticalScore` is the SAME sentinel-bearing parameter as
 * `wouldBotAcceptDraw`/`wouldBotResign`'s: `null` means the bot has not
 * evaluated any position yet this game (Human rungs, and the opening book's
 * zero-Stockfish-eval window). It is refused FIRST and UNCONDITIONALLY,
 * before any other argument is even looked at — a bot must never propose a
 * game-ending offer off a score it never computed.
 *
 * `contempt` (A4 resolution) is the SAME signed knob `wouldBotAcceptDraw`
 * already reads off `BotStyleParams` — no new field is added. `drawValue =
 * 0.5 + contempt`, exactly mirroring the accept gate's shift direction: a
 * positive-contempt style (e.g. Grinder, "wants more than dead-equal") needs
 * a score genuinely above 0.5 before it will even PROPOSE a draw, so it
 * offers far more rarely; a negative-contempt style (e.g. Wall, "settles for
 * less") will propose off a slightly-worse-than-equal score, so it offers
 * more readily. The band WIDTH (`BOT_DRAW_OFFER_SCORE_BAND`) is unchanged by
 * contempt — it shifts the center only.
 *
 * With a real score, ALL of the following must hold for an offer:
 * 1. `Math.abs(rootPracticalScore - drawValue) <= BOT_DRAW_OFFER_SCORE_BAND`
 *    — the position is near the (possibly shifted) draw target.
 * 2. `chess.moveNumber() >= BOT_DRAW_OFFER_MIN_FULLMOVE` — the game is past
 *    its own early-development floor (Pitfall 7).
 * 3. `movesSinceOwnOffer >= BOT_DRAW_OFFER_COOLDOWN_MOVES` — enough of the
 *    bot's own moves have passed since it last offered (no spam).
 */
export function wouldBotOfferDraw(
  rootPracticalScore: number | null,
  chess: Chess,
  contempt: number,
  movesSinceOwnOffer: number,
): boolean {
  // Not-yet-evaluated: refuse before anything else (matches wouldBotAcceptDraw/wouldBotResign's sentinel discipline).
  if (rootPracticalScore === null) return false;

  const drawValue = 0.5 + contempt; // Same shift direction as wouldBotAcceptDraw's D-09 target.
  const isNearEqual = Math.abs(rootPracticalScore - drawValue) <= BOT_DRAW_OFFER_SCORE_BAND;

  return (
    isNearEqual &&
    chess.moveNumber() >= BOT_DRAW_OFFER_MIN_FULLMOVE &&
    movesSinceOwnOffer >= BOT_DRAW_OFFER_COOLDOWN_MOVES
  );
}

export function wouldBotResign(
  rootPracticalScore: number | null,
  resignThreshold: number,
  consecutiveLowTurns: number,
  hysteresisFloor: number,
  chess: Chess,
): boolean {
  // Not-yet-evaluated: refuse before anything else (matches wouldBotAcceptDraw's sentinel discipline).
  if (rootPracticalScore === null) return false;

  return (
    rootPracticalScore <= resignThreshold &&
    consecutiveLowTurns >= hysteresisFloor &&
    chess.moveNumber() >= RESIGN_MIN_FULLMOVE
  );
}
