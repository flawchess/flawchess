/**
 * botLineTrigger — Phase 223 (BOTVOICE-02/03): the pure resolver deciding
 * which in-game bubble line (if any) fires after the bot's own move. No
 * React import.
 *
 * Mirrors `components/train/trainBubbleState.ts`'s rationale verbatim:
 * extracting this resolution OUT of `BotsGame` (rather than inlining guard
 * blocks in JSX) is the mechanism that keeps the page's own cyclomatic
 * complexity from rising — `BotsGame` sits AT its eslint ceiling
 * (`frontend/eslint.config.js`, Phase 215 baseline region), so every new
 * branch this phase needs must land in a module like this one, never in the
 * page itself.
 *
 * Sign convention (BOTVOICE-03, D-01): `swingCp` is bot-POV. A POSITIVE
 * delta means the bot's own position improved over the move pair (the
 * earned tease, D-03, "delta is delta" — no optimality check against
 * whether the bot found the strongest punishment); a NEGATIVE delta means
 * it worsened (a swing against the bot, split by capture per D-04). The
 * caller (`useBotGameVoice`) is responsible for supplying `null` whenever
 * the two graded plies are not exactly one move pair apart
 * (`BOT_LINE_PAIR_PLY_SPAN`) — this resolver never re-derives ply adjacency
 * itself, and a `null` delta can never yield a swing key regardless of the
 * other fields (RESEARCH Pitfall 4: the book window, a failed grade, an
 * aborted turn, and a resumed game's first reply all surface this way).
 *
 * UNITS CHANGED in Phase 223 UAT, and this is the bug fix that made the bot
 * actually talk: the swing was originally measured as a delta in EXPECTED
 * SCORE (the `evalToExpectedScore` sigmoid), thresholded at 0.20. That
 * signal saturates. Once a game is decided — which is most of a game against
 * a sub-1400 rung — winning a further rook moves expected score by a couple
 * of hundredths, so no swing line could fire in exactly the games with the
 * most dramatic material swings. An instrumented 81-ply live game against
 * the 800 rung, with queens and rooks hanging in both directions, fired
 * ZERO swing lines. Clamped centipawns (`BOT_LINE_SWING_CLAMP_CP`) do not
 * saturate over the range where a swing is worth remarking on, and the
 * clamp is what keeps a decided game from re-announcing itself every move.
 *
 * TIMING MODEL, rewritten in Phase 223 UAT (the "comment when I take the
 * hanging piece" round). A swing AGAINST the bot is no longer spoken when
 * the bot's own grade lands. Three facts forced this:
 *
 *  1. The drop appears in the grade of the bot's OWN move — a depth-14
 *     search sees the knight hangs the instant it is played. Speaking there
 *     means the bot announces its own blunder BEFORE the player has touched
 *     it: wrong beat, and a spoiler.
 *  2. The pair delta has two authors (the player's move and the bot's
 *     reply), so a drop caused purely by the bot's own move was being keyed
 *     as `'nice-move'` — credited to whatever the player happened to play
 *     before it.
 *  3. The capture itself is an engine NON-EVENT. In the game that prompted
 *     this (`1.d4 e5 2.dxe5 Nc6 3.Nf3 Bc5 4.Bf4 Qe7 5.e3 Qf8 6.Nc3 Nf6??
 *     7.exf6`) the blunder moved the eval 276cp and the capture that
 *     punished it moved it 12cp — the engine had already priced the loss.
 *     So no amount of extra grading puts a line on the capture; only
 *     DEFERRING the reaction does.
 *
 * So a swing against the bot LATCHES instead of speaking (`isRegretSwing`),
 * and the latch resolves at whichever of these comes first:
 *
 *  - the player captures on their very next move — `resolveRegretPunishKey`
 *    fires `'punished-mistake'` right then, at the seam that used to do
 *    nothing but clear the bubble;
 *  - the bot's next grade shows the position RECOVERED by a full threshold
 *    — `'got-away'`, the bot wriggling off the hook;
 *  - the bot's next grade shows it did NOT recover — `'nice-move'`, the
 *    player's advantage held (they punished positionally, or the piece is
 *    simply still hanging).
 *
 * The recovery arm is what keeps `'got-away'` honest: a bot that leaves the
 * same piece hanging a second move shows no recovery and so never claims to
 * have escaped.
 *
 * Every `BotLineKey` is reachable through the locked precedence chain below
 * (BOTVOICE-02/03).
 *
 * Retired in Phase 223 UAT: the `'player-threat'` arm and its engine-free
 * `lib/botThreat.ts` detector. The detector compared the cheapest enemy
 * attacker against the piece's own value, which ignores defender count and
 * recapture value entirely, so it announced "my piece is hanging" during
 * ordinary exchanges — a recapturing piece is always attacked by whatever can
 * recapture it, and a knight defended three times still reads as threatened
 * when one pawn attacks it. Fixing it properly needs a static exchange
 * evaluation plus a before/after delta so the line describes what the
 * player's move actually created; judged not worth the accuracy risk for one
 * line, so the trigger was dropped rather than repaired.
 */

import type { BotLineKey } from '@/lib/botGameCopy';

/**
 * Already-computed facts `resolveBotLine` needs — never re-derived here.
 * Every field is a plain value the caller (`useBotGameVoice`) has already
 * latched from the board-truth seams (`commitMove`, the grade continuation).
 */
export interface ResolveBotLineInput {
  /** True on the bot's first move of a fresh (non-resumed) game, latched
   * once by the caller so a resumed game never greets (D-06/D-07). */
  gameStartPending: boolean;
  /**
   * Bot-POV CLAMPED-CENTIPAWN delta (D-01) over exactly one move pair
   * (player move + bot reply): `newCp - previousCp`, each end already
   * clamped to ±`BOT_LINE_SWING_CLAMP_CP` by `clampedMoverPovCp`. `null`
   * whenever the pair is not adjacent (`BOT_LINE_PAIR_PLY_SPAN`), the grade
   * failed (best-effort, as today), or the game is still in the opening
   * book — RESEARCH Pitfall 4's three documented gaps. Positive = the bot
   * improved (earned tease, BOTVOICE-03 D-03); negative = a swing against
   * the bot (D-04). See the file header for why this is not expected score.
   */
  swingCp: number | null;
  /**
   * `null` while no regret latch is live. Otherwise the bot-POV clamped
   * centipawns the position has recovered since the blunder that set the
   * latch: `currentCp - cpAtBlunder`. A live latch takes priority over
   * `swingCp` entirely — the bot's own last blunder is the story until it
   * is settled, one way or the other, and it settles on the very next
   * grade (see the timing model in this file's header).
   */
  recoveryCp: number | null;
  /** True on the first capture of the game, by either side, not yet
   * announced. */
  firstCapturePending: boolean;
  /** True while the bot has a live outgoing draw offer (Phase 183 D-07). */
  drawOfferLive: boolean;
  /** The game's terminal outcome kind, or `null` while the game continues. */
  outcomeKind: 'win' | 'loss' | 'draw' | null;
  /** Bot moves elapsed since the last NON-terminal line fired — the
   * `BOT_LINE_MIN_SPACING_MOVES` pacing gate later arms consult. */
  botMovesSinceLastLine: number;
}

/**
 * Resolves the swing arm in isolation — split out of `resolveBotLine`'s own
 * body so the top-level precedence chain stays a flat, single-level list of
 * guard-clause returns (Claude's Discretion: project soft nesting depth 3).
 *
 * A live regret latch (`recoveryCp !== null`) is resolved FIRST and always
 * produces a key, because the caller clears the latch on this same grade
 * either way: leaving it to fall through would drop the bot's own blunder
 * on the floor unremarked. Otherwise only an improvement FOR the bot speaks
 * here; a swing against it latches instead (`isRegretSwing`) and falls
 * through to the lower-priority arms untouched for now.
 */
function resolveSwingKey(swingCp: number | null, recoveryCp: number | null): BotLineKey | null {
  if (recoveryCp !== null) {
    return recoveryCp >= BOT_LINE_SWING_THRESHOLD_CP ? 'got-away' : 'nice-move';
  }
  if (swingCp === null) return null;
  if (swingCp >= BOT_LINE_SWING_THRESHOLD_CP) return 'earned-tease';
  return null;
}

/**
 * True when a graded move pair is a swing AGAINST the bot big enough to be
 * worth reacting to — the caller's signal to LATCH regret rather than speak
 * (see the timing model in this file's header). Never a line by itself.
 */
export function isRegretSwing(swingCp: number | null): boolean {
  return swingCp !== null && swingCp <= -BOT_LINE_SWING_THRESHOLD_CP;
}

/**
 * The player-commit half of the regret latch: the bot owns up the moment
 * the player CAPTURES while its own last blunder is still unanswered. This
 * is the one line in the system that fires on the player's move rather than
 * the bot's, and it is deliberately NOT paced — it is a direct answer to
 * something the player just did, never ambient chatter.
 *
 * A capture is a proxy for "punished", and an accepted one: it is exact for
 * the dominant case (a hanging piece taken) and merely early for the rest,
 * where the latch instead resolves on the bot's next grade as `'got-away'`
 * or `'nice-move'`.
 */
export function resolveRegretPunishKey(
  regretPending: boolean,
  playerCaptured: boolean,
): BotLineKey | null {
  if (!regretPending) return null;
  if (!playerCaptured) return null;
  return 'punished-mistake';
}

/**
 * Maps a non-null `outcomeKind` to its own key — the ONE arm that would
 * otherwise need three-way branching, extracted so the top-level chain
 * still reads as guard-clause returns rather than a switch. Called from arm
 * 1, ahead of every pacing/priority concern below: terminal lines are never
 * suppressed (see `BOT_LINE_MIN_SPACING_MOVES`'s own doc comment).
 */
function resolveOutcomeKey(outcomeKind: 'win' | 'loss' | 'draw'): BotLineKey {
  if (outcomeKind === 'win') return 'bot-won';
  if (outcomeKind === 'loss') return 'bot-lost';
  return 'game-drawn';
}

/**
 * Resolves the bubble's line key from already-computed inputs. Guard-clause
 * returns only — no `else`, no nesting — so the locked precedence chain
 * reads as a flat, ordered list (Claude's Discretion, 223-CONTEXT.md):
 *
 *   1. game end (win/loss/draw)
 *   2. the bot's own outgoing draw offer
 *   3. a swing in either direction (earned tease / punished mistake / nice
 *      move), gated by `BOT_LINE_SWING_THRESHOLD_CP`
 *   4. the game's first capture
 *   5. game start
 *
 * Arms 3 through 5 are paced: swings on `BOT_LINE_SWING_SPACING_MOVES`, the
 * mood arms on the wider `BOT_LINE_MIN_SPACING_MOVES`, each evaluated once
 * ahead of its arms, suppressing them while too few bot moves have passed
 * since the last line. Arms 1-2 (game end, draw offer) and the settle of a
 * live regret latch are checked BEFORE those guards and so are never
 * suppressed — a game ending, a draw offer, or the bot owning up to a
 * blunder it already latched is never noise.
 */
export function resolveBotLine(input: ResolveBotLineInput): BotLineKey | null {
  if (input.outcomeKind !== null) return resolveOutcomeKey(input.outcomeKind);
  if (input.drawOfferLive) return 'draw-offer';
  const swingKey = resolveSwingKey(input.swingCp, input.recoveryCp);
  // A live regret latch settles UNGATED (223-REVIEW CR-01): the hook clears the
  // latch on this grade whatever we return, so pacing this key did not delay
  // the bot's acknowledgement of its own blunder, it dropped it outright
  // whenever a mood line had fired a move earlier. Like the punish line, the
  // settle answers a specific latched event and is never noise.
  if (swingKey !== null && input.recoveryCp !== null) return swingKey;
  if (swingKey !== null) {
    return input.botMovesSinceLastLine >= BOT_LINE_SWING_SPACING_MOVES ? swingKey : null;
  }
  if (input.botMovesSinceLastLine < BOT_LINE_MIN_SPACING_MOVES) return null;
  if (input.firstCapturePending) return 'first-capture';
  if (input.gameStartPending) return 'game-start';
  return null;
}

/**
 * D-02: the swing threshold, in bot-POV CLAMPED CENTIPAWNS over one move
 * pair (see the file header for the units change). 150cp is "a minor piece,
 * or a positional shift of that weight" — big enough that every fire is
 * obviously visible on the board, small enough that the bot has something to
 * say a few times per game.
 *
 * Calibrated, not guessed: replayed over 300 real analyzed games from the
 * dev DB (bot = one side, book exit at ply 12, this module's own
 * `BOT_LINE_MIN_SPACING_MOVES` gate applied), 150cp yields ~3.1 swing lines
 * per game — ~4 in-game lines with `'first-capture'`, ~6 including the
 * greeting and the terminal line. The neighbours were measured too: 100cp
 * gives ~4.2 swing lines (chatty), 250cp ~1.8 and 300cp ~1.5 (back toward
 * the silence this replaces). A magnitude exactly AT this threshold counts
 * ("at or beyond" per the locked behaviour).
 */
export const BOT_LINE_SWING_THRESHOLD_CP = 150;

/**
 * Both ends of a swing delta are clamped to ±this before subtracting, so a
 * decided game stops generating swings instead of re-announcing itself every
 * move: once the bot is past +1000cp, taking a further rook is a delta of
 * zero, not another `'earned-tease'`. It also keeps a mate score (which the
 * grader reports as a ±10000-equivalent) from producing one absurd delta and
 * then an equally absurd one back — a transition INTO mate still clears the
 * threshold comfortably, which is the behaviour we want.
 */
export const BOT_LINE_SWING_CLAMP_CP = 1000;

/**
 * Converts one grade's white-POV `evalCp`/`evalMate` pair into the bot-POV
 * clamped centipawn value `ResolveBotLineInput.swingCp` is a delta of.
 * Mirrors `evalToExpectedScore`'s own mate-before-cp convention and its
 * "no eval at all means dead level" fallback, so the two signals can never
 * disagree about which side is better — only about scale.
 */
export function clampedMoverPovCp(
  evalCp: number | null,
  evalMate: number | null,
  mover: 'white' | 'black',
): number {
  const sign = mover === 'white' ? 1 : -1;
  let cp: number;
  if (evalMate != null && evalMate !== 0) {
    cp = evalMate > 0 ? BOT_LINE_SWING_CLAMP_CP : -BOT_LINE_SWING_CLAMP_CP;
  } else {
    cp = evalCp ?? 0;
  }
  const moverPov = cp * sign;
  return Math.max(-BOT_LINE_SWING_CLAMP_CP, Math.min(BOT_LINE_SWING_CLAMP_CP, moverPov));
}

/**
 * Minimum number of bot moves between two MOOD lines (`'first-capture'`,
 * `'game-start'`) — the ambient ones that describe no particular move, so a
 * low-rung bot does not chatter. Terminal lines (game end, draw offer) are
 * exempt by construction: they are checked in `resolveBotLine` BEFORE this
 * guard is ever consulted.
 *
 * Phase 223 UAT: this gate no longer covers the swing arm, which has its
 * own, shorter `BOT_LINE_SWING_SPACING_MOVES`. The game that prompted the
 * round is the argument — `'first-capture'` fired for a routine ply-3 pawn
 * recapture and reset this counter, and two moves later the bot hung a
 * knight and said nothing, because the throwaway line was still holding the
 * gate. A mood line must never be able to eat a swing line.
 */
export const BOT_LINE_MIN_SPACING_MOVES = 3;

/**
 * Minimum number of bot moves between two SWING lines. Shorter than the
 * mood gate because a swing is the thing worth hearing about: it is already
 * rate-limited by `BOT_LINE_SWING_THRESHOLD_CP`, and the regret latch
 * serializes a blunder and its answer into a single exchange.
 *
 * Measured over the same 300-game dev-DB replay that calibrated the
 * threshold: ungated gives ~4.3 swing lines per game, `2` gives ~3.8, the
 * old shared `3` gives ~3.3. `2` keeps a pathologically swingy game from
 * speaking on consecutive bot moves without costing the normal case
 * anything. The deferred `'punished-mistake'` fires on the PLAYER's move
 * and is not gated at all (`resolveRegretPunishKey`).
 */
export const BOT_LINE_SWING_SPACING_MOVES = 2;

/**
 * RESEARCH Pitfall 4: a swing line must only ever describe a swing the board
 * just showed — exactly one move pair (the player's move, then the bot's
 * reply) — never an accumulation across several moves. `2` because a move
 * pair spans two plies (one per side); the caller compares this against the
 * ply distance between the two graded scores before treating a delta as
 * reportable.
 */
export const BOT_LINE_PAIR_PLY_SPAN = 2;
