/**
 * botGameEnd — chess.js-backed end-condition detection + outcome→result-copy
 * mapping (Phase 169, PLAY-06/PLAY-09).
 *
 * Pure, React-free: detectEndCondition wraps chess.js's own end-condition
 * methods (never re-derives repetition/fifty-move/insufficient-material by
 * hand — chess.js already tracks full position history internally for its
 * own isDraw()). resultCopy maps a finished game's outcome to the verbatim
 * UI-SPEC Copywriting Contract strings, from the human player's point of view.
 *
 * Timeout and resignation reasons are NOT detected here — those are
 * clock/user-action-driven concepts the game loop (useBotGame, plan 04) sets
 * directly; detectEndCondition only ever reads board state via chess.js.
 *
 * D-02/D-03 (169-CONTEXT.md): the bot never offers a draw and never
 * resigns — there is no bot-resign or bot-draw-offer branch anywhere in this
 * module, encoded as the absence of such an outcome on the bot's side.
 */

import type { Chess } from 'chess.js';

import type { MoverColor } from '@/lib/liveFlaw';

/** How a bot game ended. Board-derived conditions are 'checkmate'/'draw';
 * 'timeout'/'resignation' are set by the caller (useBotGame) — this module
 * only ever produces the board-derived subset. */
export type GameEndReason = 'checkmate' | 'draw' | 'timeout' | 'resignation';

/** Specific reason a drawn game ended, for result-copy specificity.
 * 'agreement' covers a mutually-accepted draw offer (D-01), which is not
 * board-derived and so is never returned by detectEndCondition. */
export type DrawReason =
  | 'stalemate'
  | 'threefold'
  | 'fifty-move'
  | 'insufficient-material'
  | 'agreement';

/**
 * A finished bot game's outcome: reason + optional winner (set for the
 * decisive reasons: checkmate/timeout/resignation) + optional drawReason
 * (set only when reason === 'draw').
 */
export interface BotGameOutcome {
  reason: GameEndReason;
  /** The winning side. Set for 'checkmate' | 'timeout' | 'resignation'; omitted for 'draw'. */
  winner?: MoverColor;
  /** Set only when reason === 'draw'; specifies which draw rule applies. */
  drawReason?: DrawReason;
}

/** detectEndCondition's return shape is the board-derived subset of BotGameOutcome
 * (reason is always 'checkmate' | 'draw'; winner is only ever set for checkmate). */
export type GameEndResult = BotGameOutcome;

/**
 * Detects a board-state end condition via chess.js's own rules methods —
 * checkmate (winner = the side NOT to move) or one of the four automatic
 * draw rules. Returns null when the game continues; flag-on-time is a
 * clock-driven condition the caller checks separately (chess.js has no view
 * of the clock).
 */
export function detectEndCondition(chess: Chess): GameEndResult | null {
  if (chess.isCheckmate()) {
    // The side to move is checkmated, so the OTHER side won.
    return { reason: 'checkmate', winner: chess.turn() === 'w' ? 'black' : 'white' };
  }
  if (chess.isStalemate()) return { reason: 'draw', drawReason: 'stalemate' };
  if (chess.isThreefoldRepetition()) return { reason: 'draw', drawReason: 'threefold' };
  if (chess.isDrawByFiftyMoves()) return { reason: 'draw', drawReason: 'fifty-move' };
  if (chess.isInsufficientMaterial()) return { reason: 'draw', drawReason: 'insufficient-material' };
  return null; // game continues
}

/**
 * Maps a finished game's outcome to the exact UI-SPEC Copywriting Contract
 * result string, from `userColor`'s point of view. No invented copy — every
 * branch below is a verbatim string from 169-UI-SPEC.md's Copywriting
 * Contract table, EXCEPT the bot-actor substitution added below.
 *
 * `personaName` (Phase 183, D-06) is optional and additive: when supplied
 * (a persona game), it is substituted into the branches where the BOT is the
 * grammatical actor — the bot winning by checkmate/timeout, or (the
 * D-03-unreachable) the bot resigning — e.g. "Riko the Raccoon wins on time"
 * / "Ziggy the Wasp wins — checkmate". Branches where the USER is the actor
 * (the user winning, or the user resigning) and the draw branches (no actor)
 * are UNCHANGED regardless of `personaName` — this stays the single copy
 * generator, no forked second table.
 */
export function resultCopy(
  outcome: BotGameOutcome,
  userColor: MoverColor,
  personaName?: string | null,
): string {
  const { reason, winner, drawReason } = outcome;

  if (reason === 'draw') {
    switch (drawReason) {
      case 'stalemate':
        return 'Draw — stalemate';
      case 'threefold':
        return 'Draw — repetition';
      case 'fifty-move':
        return 'Draw — 50-move rule';
      case 'insufficient-material':
        return 'Draw — insufficient material';
      case 'agreement':
      default:
        return 'Draw — by agreement';
    }
  }

  const userWon = winner === userColor;

  if (reason === 'checkmate') {
    if (userWon) return 'You won — checkmate';
    return personaName ? `${personaName} wins — checkmate` : 'You lost — checkmate';
  }
  if (reason === 'timeout') {
    if (userWon) return 'You won on time';
    return personaName ? `${personaName} wins on time` : 'You lost on time';
  }
  // reason === 'resignation'. D-03: the bot never resigns, so a bot-loss
  // resignation copy never actually occurs — only "You resigned" is reachable
  // in practice, but the win-side copy is kept for completeness of the copy table.
  if (userWon) {
    return personaName ? `You won — ${personaName} resigned` : 'You won — the bot resigned';
  }
  return 'You resigned';
}
