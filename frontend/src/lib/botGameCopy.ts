/**
 * botGameCopy — Phase 223 (BOTVOICE-01/02): all in-game bot-narrated copy for
 * the `/bots` speech bubble, keyed by trigger and then by persona. No React
 * import (mirrors `lib/trainBotCopy.ts`'s pure-module convention) — every
 * function here is a total function of already-computed values.
 *
 * Generalizes the "ONE scoped exception" `trainBotCopy.ts`'s own header
 * records for `LANDING_GREETINGS` (a per-persona /train landing line): this
 * phase makes per-persona voice the point for every in-game trigger, not a
 * one-off exception. `trainBotCopy.ts`'s per-outcome-bucket convention (D-06
 * there) is unaffected — this module owns a disjoint surface, the `/bots`
 * game itself, never /train.
 *
 * Copy accuracy constraint (carried verbatim from
 * `PersonaGrid.tsx`'s `BotWelcomeCard` doc comment): 16 of the 24
 * personas run at `HUMAN_BLEND` (rungs 800, 1000, 1200, 1400), where
 * `selectBotMove` makes exactly ONE Maia policy call and never searches. So
 * no line in any table below may claim a bot "calculated", "thought ahead",
 * "planned" or "saw it coming" — every line describes voice or the board,
 * never the bot's own reasoning process.
 *
 * Terminal-line visibility (the three tables `'bot-won'`/`'bot-lost'`/
 * `'game-drawn'`): these lines are rendered INSIDE `GameResultDialog` (with
 * the persona's avatar), so they are read in the dialog whether or not
 * `useWinCelebrationHold` delays it for that ending (it does after a human
 * win and after a bot checkmate; not after other losses or draws). This
 * module introduces no timing logic of its own; the hold lives entirely in
 * that hook.
 */

import { differenceInCalendarDays, parseISO } from 'date-fns';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import type { Persona, PersonaId } from '@/lib/personas/personaRegistry';
// 223-02: the roster rotation imports these SHARED primitives rather than
// declaring its own epoch/id list, so "the same bot greets you on /train
// and /bots today" is structural, never coincidental (see `rosterHost`).
import { LANDING_HOST_IDS, LANDING_ROTATION_EPOCH, TANK_ID } from '@/lib/trainBotCopy';

/**
 * The trigger keys a line can be authored for. A literal union, never a bare
 * `string` (root CLAUDE.md rule). Plan 01 shipped `'game-start'` only; this
 * plan (223-02) widens the union to the five move-triggered keys below in
 * the same edit as their `BOT_LINE_TABLES` entries, so exhaustiveness
 * (`Record<PersonaId, string>` per key) can never lapse for an added
 * trigger. The nine keys below are exhaustive; `'player-threat'` was
 * retired in Phase 223 UAT (see `botLineTrigger.ts`'s own note), and
 * `'got-away'` was added in the same round. The exhaustive
 * per-table/per-persona invariant test lives in
 * `lib/__tests__/botGameCopy.test.ts`.
 */
export type BotLineKey =
  | 'game-start'
  | 'first-capture'
  | 'earned-tease'
  | 'punished-mistake'
  | 'nice-move'
  | 'got-away'
  | 'draw-offer'
  | 'bot-won'
  | 'bot-lost'
  | 'game-drawn';

/**
 * Per-trigger, per-persona authored copy. `Record<BotLineKey,
 * Record<PersonaId, string>>` makes a missing persona (for any key) a
 * compile error, mirroring `trainBotCopy.ts`'s `LANDING_GREETINGS` shape.
 *
 * `'game-start'` (D-06): pure voice, in-game hellos. These lines fire before
 * a single move has been played, so they can never reference the position —
 * unlike every other trigger this phase adds, which describes something the
 * board has just shown. One line per persona, no em-dash, at most
 * `BOT_LINE_MAX_CHARS` characters.
 */
export const BOT_LINE_TABLES: Record<BotLineKey, Record<PersonaId, string>> = {
  'game-start': {
    'attacker-800': "Bzzz! I'm Ziggy. Let's see who stings first today.",
    'attacker-1000': "Woof, I'm Duke! Ready to sniff out a fight?",
    'attacker-1200': "Talon here. Circling already. Let's go.",
    'attacker-1400': "Fury. Show me a weakness and I'll take it.",
    'attacker-1600': 'Butch the Ram, horns down. Charging in.',
    'attacker-1800': "Diesel. I don't slow down. Neither should you.",
    'trickster-800': 'Ooh, shiny! Miko here. Watch for my traps.',
    'trickster-1000': "Psst, Slinky. I've got a few tricks ready.",
    'trickster-1200': "Vix here. Guess which game we're playing.",
    'trickster-1400': "Riko. I dig up trouble. Let's find some.",
    'trickster-1600': 'Sly the Coyote. Sure about that move?',
    'trickster-1800': 'Cackle here. Chaos is my favorite opening.',
    'grinder-800': "Pip the Ant. Let's trade and simplify early.",
    'grinder-1000': "Dig here. I'm burrowing toward an endgame.",
    'grinder-1200': 'Otto the Otter, paddling calmly into it.',
    'grinder-1400': "Nell. I outlast people. Let's begin.",
    'grinder-1600': 'Tank the Ox. Boot camp starts now, recruit.',
    'grinder-1800': 'Gus here. I like a long, fair fight.',
    'wall-800': 'Sheldon the Snail. No rush, slow and solid.',
    'wall-1000': 'Spike here, curled up tight. Try me.',
    'wall-1200': 'Shelly the Turtle. Same system, every time.',
    'wall-1400': 'Bruno the Badger. I might offer a draw early.',
    'wall-1600': 'Rocco the Armadillo. Good luck cracking this.',
    'wall-1800': 'Hilda here. Calm and steady, as always.',
  },

  /**
   * `'first-capture'` (D-06/223-CONTEXT): fires once, right after the first
   * capture of the game by either side, when the bot has just replied. Pure
   * mood ("the game is real now") — never a claim about who stands better.
   */
  'first-capture': {
    'attacker-800': "Ooh, first blood! Now it's a real fight.",
    'attacker-1000': "There's the first bite. Let's keep going.",
    'attacker-1200': "First capture. Now we're really flying.",
    'attacker-1400': 'Claws out. The real game starts now.',
    'attacker-1600': 'Horns down, first contact made.',
    'attacker-1800': 'First hit landed. Now it gets serious.',
    'trickster-800': 'Ooh, shiny! Pieces are coming off now.',
    'trickster-1000': 'First trade. Watch your pockets.',
    'trickster-1200': 'Now we trade tricks, not just pieces.',
    'trickster-1400': 'First capture. I love how it gets messy.',
    'trickster-1600': 'First blood. Chaos loves company.',
    'trickster-1800': 'Ha! First trade. The fun begins.',
    'grinder-800': 'First trade. Fewer pieces, happier me.',
    'grinder-1000': 'One piece down. Simpler already.',
    'grinder-1200': 'First trade made. Smooth sailing.',
    'grinder-1400': "There it is. One trade closer to the end.",
    'grinder-1600': 'First contact, recruit. Trade on.',
    'grinder-1800': 'First trade. I like where this heads.',
    'wall-800': 'Careful now, first piece is off.',
    'wall-1000': "First capture. I'll stay curled up.",
    'wall-1200': 'First trade. Same plan either way.',
    'wall-1400': 'First piece gone. I might offer a draw soon.',
    'wall-1600': 'First contact. My shell holds.',
    'wall-1800': 'First capture. Steady as ever.',
  },

  /**
   * `'earned-tease'` (D-03/223-CONTEXT): fires when the bot's OWN move just
   * cashed in a large swing in its favor. The teasing register: points at
   * what is now visible on the board. Never claims the bot planned,
   * calculated or foresaw it — 16 of the 24 personas make exactly one
   * policy call and never search (module header constraint, above).
   *
   * Two further accuracy constraints, both forced by how the trigger is
   * measured (`botLineTrigger.ts`, `BOT_LINE_PAIR_PLY_SPAN`), and both
   * guarded by `TEASE_TIMING_CLAIM_PATTERN` in `botGameCopy.test.ts`:
   *
   *  - NO DURATION CLAIM. The swing is a delta over exactly ONE move pair,
   *    so the mistake it reacts to is always the player's LAST move. The
   *    original table said "loose for a while" / "a whole move" / "far too
   *    long", which was false every single time it fired (the piece was hung
   *    one ply ago and is being remarked on now). Every line below describes
   *    an instant: "that last move", "just now", "there it is".
   *  - NO CAPTURE CLAIM. A depth-14 grade prices a hanging piece the ply it
   *    is hung, so the tease fires on the bot's reply whether or not that
   *    reply captured anything (a capture one move later is an engine
   *    non-event, exactly as the file header of `botLineTrigger.ts` records
   *    for the regret arm). So no line may say "I took it" or name a piece
   *    as taken; "that piece is loose" (present tense, still on the board)
   *    is the strongest a line goes.
   */
  'earned-tease': {
    'attacker-800': 'Bzzz! That last move left a piece just sitting there.',
    'attacker-1000': 'Woof! Something is hanging after that one.',
    'attacker-1200': 'That last move opened a gap. Diving in.',
    'attacker-1400': 'You left a gap just now. Claws in.',
    'attacker-1600': 'That last move dropped your guard. Horns down.',
    'attacker-1800': 'That move cost you. Pressing right away.',
    'trickster-800': 'Ooh! That last move left something out for me.',
    'trickster-1000': 'Tsk. That one just came loose.',
    'trickster-1200': 'You left that hanging just now, and I noticed.',
    'trickster-1400': "That piece is loose after that move. Can't resist.",
    'trickster-1600': 'Sure about that last move? Something is loose.',
    'trickster-1800': 'Ha! That last move left the door wide open.',
    'grinder-800': 'That last move left a piece just sitting there.',
    'grinder-1000': 'That one just came loose, you know.',
    'grinder-1200': 'Nice and calm, but that last move left a gap.',
    'grinder-1400': 'That piece is unguarded after that move.',
    'grinder-1600': 'That last move left a piece loose, recruit. Noted.',
    'grinder-1800': 'That move left something open. Pressing on.',
    'wall-800': 'That last move left a piece just sitting there, oddly.',
    'wall-1000': "That one just came loose, didn't it?",
    'wall-1200': 'Same routine, but that last move left a gap.',
    'wall-1400': 'That piece is hanging after that move. I noticed.',
    'wall-1600': 'That last move left a piece open, you know.',
    'wall-1800': 'That move left something loose. Calm as ever.',
  },

  /**
   * `'punished-mistake'` (D-04/223-CONTEXT): fires when a large swing
   * against the bot pairs with a capture by the player in the same move
   * pair. Self-deprecating, good-humoured, never sulky — describes the
   * board, never the player.
   */
  'punished-mistake': {
    'attacker-800': 'Ouch, I left that hanging. My bad.',
    'attacker-1000': "Yeah, I shouldn't have left that there.",
    'attacker-1200': 'Well, that one stings. Nice grab.',
    'attacker-1400': "Oof. I gave you that piece, didn't I.",
    'attacker-1600': 'Rough trade for me. Fair catch.',
    'attacker-1800': 'I left that open. Good take.',
    'trickster-800': 'Oops! You caught my own trap.',
    'trickster-1000': 'Ha, the trick backfired on me.',
    'trickster-1200': 'Well played, you saw through that one.',
    'trickster-1400': 'Ouch, I dug my own hole there.',
    'trickster-1600': 'Nice. My trick just cost me.',
    'trickster-1800': 'Ha! Chaos bit me this time.',
    'grinder-800': 'Oops, that trade favored you.',
    'grinder-1000': 'Well, that trade went your way.',
    'grinder-1200': 'Not my best trade. Fair enough.',
    'grinder-1400': 'That one cost me. Fair play.',
    'grinder-1600': 'Rough one, recruit. You earned it.',
    'grinder-1800': 'Well, I gave that trade away.',
    'wall-800': 'Oh no, that slipped past my shell.',
    'wall-1000': 'Ouch. My shell had a gap there.',
    'wall-1200': 'Same system, wrong result there.',
    'wall-1400': "Well, I'd like that piece back.",
    'wall-1600': 'My shell cracked a little there.',
    'wall-1800': 'I left a gap. Well caught.',
  },

  /**
   * `'nice-move'` (D-04/223-CONTEXT): fires when a large swing against the
   * bot has NO capture in that move pair. A genuine compliment on a move
   * the board now shows was strong.
   */
  'nice-move': {
    'attacker-800': 'Whoa, nice move! That one stings.',
    'attacker-1000': 'Good move! That shifted things your way.',
    'attacker-1200': 'Sharp move. That changed things fast.',
    'attacker-1400': 'Strong move. That shifted the board hard.',
    'attacker-1600': 'Good one. That really turned the tide.',
    'attacker-1800': 'Sharp move. The board tilted your way.',
    'trickster-800': 'Ooh, sneaky good move!',
    'trickster-1000': 'Nice move! That one caught me off guard.',
    'trickster-1200': 'Clever move. The game just shifted.',
    'trickster-1400': 'Sly move! That flipped the script.',
    'trickster-1600': 'Nice one. That turned the tables.',
    'trickster-1800': 'Ha, good move! Chaos favors you now.',
    'grinder-800': 'Nice move! That trade helped you.',
    'grinder-1000': 'Good move. That simplified in your favor.',
    'grinder-1200': 'Calm and sharp. Nice move there.',
    'grinder-1400': 'Solid move. That shifted things your way.',
    'grinder-1600': 'Good move, recruit. That helped you.',
    'grinder-1800': "Strong move. That's a real shift.",
    'wall-800': 'Nice move! That got past my shell.',
    'wall-1000': 'Good move. That found a gap.',
    'wall-1200': 'Solid move. That broke my system a bit.',
    'wall-1400': 'Nice move. I might reconsider that draw offer.',
    'wall-1600': 'Good move. That cracked my shell some.',
    'wall-1800': 'Strong move. Well played, truly.',
  },

  /**
   * `'draw-offer'` (D-12/223-CONTEXT): the copy the Accept and Decline
   * buttons in the bubble sit under. Reads as an offer, in the persona's own
   * voice, in one sentence — replaces the retired draw-offer banner
   * component's generic wording.
   */
  'draw-offer': {
    'attacker-800': 'Truce? Even wasps need a break sometimes.',
    'attacker-1000': 'How about a draw? Just this once.',
    'attacker-1200': "Draw? I'll circle back another day.",
    'attacker-1400': 'Truce for now. Care for a draw?',
    'attacker-1600': 'How about we call this one a draw?',
    'attacker-1800': 'Draw? Even I can offer an olive branch.',
    'trickster-800': 'Draw? Or is that also a trick?',
    'trickster-1000': 'How about a draw? No tricks, promise.',
    'trickster-1200': 'Draw? Might be my sneakiest offer yet.',
    'trickster-1400': 'Care for a draw? Genuinely, this time.',
    'trickster-1600': 'Draw? Chaos needs a pause too.',
    'trickster-1800': 'How about a draw? Ha, no catch.',
    'grinder-800': 'Draw? Simplest result for us both.',
    'grinder-1000': 'How about we call it a draw?',
    'grinder-1200': 'Draw? Calm waters for both of us.',
    'grinder-1400': 'Care for a draw? Fair result here.',
    'grinder-1600': "Draw, recruit? Sometimes that's the win.",
    'grinder-1800': "How about a draw? Long fight, fair split.",
    'wall-800': 'Draw? Slow and steady says yes.',
    'wall-1000': "Care for a draw? I'm curled up either way.",
    'wall-1200': 'How about a draw? Same system, fair end.',
    'wall-1400': "I'd offer a draw, of course. Care for one?",
    'wall-1600': 'Draw? My shell prefers a quiet end.',
    'wall-1800': 'Care for a draw? Calm suits us both.',
  },

  /**
   * `'got-away'` (Phase 223 UAT): fires when the bot blundered, the player
   * did NOT punish it, and the bot's own next move recovered the position by
   * a full `BOT_LINE_SWING_THRESHOLD_CP`. Relief, never gloating — the bot
   * knows it was losing something and is saying so out loud, which is the
   * only reason it is allowed to mention it at all.
   *
   * The recovery condition is what keeps these lines honest: a bot that
   * leaves the same piece hanging a second move shows no recovery, so it
   * never gets to claim it escaped (see `botLineTrigger.ts`).
   */
  'got-away': {
    'attacker-800': 'Phew! You let me buzz out of that one.',
    'attacker-1000': 'Whew, I wriggled out. Lucky me.',
    'attacker-1200': 'Close one. I slipped away from that.',
    'attacker-1400': 'That was close. I got out in time.',
    'attacker-1600': 'Lucky escape. I was in trouble there.',
    'attacker-1800': 'That could have hurt. I got out.',
    'trickster-800': 'Hee! You missed it. I scampered off.',
    'trickster-1000': 'Ooh, lucky me. That was nearly gone.',
    'trickster-1200': 'You let that one slip. I got away.',
    'trickster-1400': 'Phew, I dug myself out of that hole.',
    'trickster-1600': 'Close call. I slipped the net there.',
    'trickster-1800': 'Ha! I escaped my own mess.',
    'grinder-800': 'Phew, I got that piece back to safety.',
    'grinder-1000': 'Lucky. I tidied that up in time.',
    'grinder-1200': 'Close one. Back to the calm plan.',
    'grinder-1400': 'That was loose. I fixed it just in time.',
    'grinder-1600': 'You let me off, recruit. Noted.',
    'grinder-1800': 'Close one. I got that back in order.',
    'wall-800': 'Phew, I pulled that back in my shell.',
    'wall-1000': 'Lucky. I curled up again in time.',
    'wall-1200': 'Close one. System restored.',
    'wall-1400': 'That was nearly bad. I got away with it.',
    'wall-1600': 'Lucky escape. The shell holds after all.',
    'wall-1800': 'Close one. Calm restored, thankfully.',
  },

  /**
   * The three terminal tables below (`'bot-won'`/`'bot-lost'`/
   * `'game-drawn'`). Each is rendered inside `GameResultDialog`, so it is
   * read there regardless of whether `useWinCelebrationHold` delays the
   * dialog; see this file's header. No timing logic is introduced here.
   */

  /** `'bot-won'`: gracious in the persona's own register, never gloating. */
  'bot-won': {
    'attacker-800': 'Good game! You made me work for that sting.',
    'attacker-1000': 'Good game! You gave me a real fight.',
    'attacker-1200': 'Good game. You made me earn that one.',
    'attacker-1400': 'Good game. That was a real scrap.',
    'attacker-1600': 'Good game. You put up a real fight.',
    'attacker-1800': "Good game. That one wasn't easy.",
    'trickster-800': 'Good game! You almost caught my trick.',
    'trickster-1000': 'Good game. That was close, honestly.',
    'trickster-1200': 'Good game. You made me work for it.',
    'trickster-1400': 'Good game. Nearly got outfoxed there.',
    'trickster-1600': "Good game. That chaos could've gone either way.",
    'trickster-1800': 'Good game! You kept me guessing.',
    'grinder-800': 'Good game! That trade line was tough.',
    'grinder-1000': 'Good game. That grind was close.',
    'grinder-1200': 'Good game. You held on well.',
    'grinder-1400': 'Good game. That was a fair, long fight.',
    'grinder-1600': 'Good game, recruit. You made me earn it.',
    'grinder-1800': 'Good game. That fight ran the distance.',
    'wall-800': 'Good game. You cracked my shell today.',
    'wall-1000': 'Good game. You found the gap eventually.',
    'wall-1200': 'Good game. My system held, barely.',
    'wall-1400': 'Good game. Almost offered a draw too soon.',
    'wall-1600': 'Good game. My shell nearly cracked.',
    'wall-1800': 'Good game. That was a real test.',
  },

  /** `'bot-lost'`: congratulating without being saccharine. */
  'bot-lost': {
    'attacker-800': "Well. Sting's on me this time.",
    'attacker-1000': "Well played. I'd like that one back.",
    'attacker-1200': 'Nice win. I overextended there.',
    'attacker-1400': 'Well. That attack backfired on me.',
    'attacker-1600': 'Nice win. I charged too hard there.',
    'attacker-1800': 'Well played. I pushed too far.',
    'trickster-800': 'Well. The trap caught me instead.',
    'trickster-1000': 'Nice win. My own trick got me.',
    'trickster-1200': 'Well played. I lost that game of wits.',
    'trickster-1400': 'Well. I dug a hole and fell in it.',
    'trickster-1600': 'Nice win. Chaos favored you today.',
    'trickster-1800': 'Well played. You out-chaosed me.',
    'grinder-800': 'Well played. That trade line beat me.',
    'grinder-1000': 'Nice win. The grind went your way.',
    'grinder-1200': 'Well played. That endgame was yours.',
    'grinder-1400': "Nice win. Fair result, I'll take it.",
    'grinder-1600': 'Well played, recruit. You earned this one.',
    'grinder-1800': 'Well played. Long fight, fair loss.',
    'wall-800': 'Well. My shell finally cracked.',
    'wall-1000': 'Well played. My shell had its limits.',
    'wall-1200': 'Well played. My system met its match.',
    'wall-1400': "Well. I'd like that draw offer back.",
    'wall-1600': 'Well played. My shell gave way today.',
    'wall-1800': 'Well played. Calm as ever, even now.',
  },

  /** `'game-drawn'`: a draw by any means, in the persona's own register. */
  'game-drawn': {
    'attacker-800': "A draw! Guess we're evenly matched today.",
    'attacker-1000': 'A draw. Fair enough, for now.',
    'attacker-1200': "A draw. We'll settle this another day.",
    'attacker-1400': 'A draw. Neither of us blinked.',
    'attacker-1600': 'A draw. Even horns need a rest.',
    'attacker-1800': "A draw. We'll finish this later.",
    'trickster-800': 'A draw! No tricks won this time.',
    'trickster-1000': 'A draw. Nobody outfoxed anybody.',
    'trickster-1200': 'A draw. Even chaos needed a break.',
    'trickster-1400': 'A draw. We both dug in equally.',
    'trickster-1600': 'A draw. Chaos called it even.',
    'trickster-1800': 'A draw! Nobody out-chaosed the other.',
    'grinder-800': 'A draw. Simplest fair result.',
    'grinder-1000': 'A draw. Neither side simplified enough.',
    'grinder-1200': 'A draw. Calm waters for us both.',
    'grinder-1400': 'A draw. A fair, quiet result.',
    'grinder-1600': 'A draw, recruit. An honest result.',
    'grinder-1800': 'A draw. Long fight, fair split.',
    'wall-800': 'A draw. Slow and steady held.',
    'wall-1000': 'A draw. My shell stayed closed.',
    'wall-1200': 'A draw. Same system, fair end.',
    'wall-1400': 'A draw. I always did want one.',
    'wall-1600': "A draw. My shell stood its ground.",
    'wall-1800': 'A draw. Calm, quiet, and fair.',
  },
};

/**
 * Resolves the authored line for `key`/`personaId`. `noUncheckedIndexedAccess`
 * narrowing (the `landingHost` idiom at `trainBotCopy.ts:120`): an explicit
 * `undefined` guard, never a `!` non-null assertion. `BOT_LINE_TABLES` is
 * exhaustive over every `PersonaId` for every `BotLineKey`, so the guard is
 * structurally unreachable in practice — a defensive fallback, not a real gap.
 */
export function botLineCopy(key: BotLineKey, personaId: PersonaId): string {
  const table = BOT_LINE_TABLES[key];
  const line = table[personaId];
  if (line === undefined) return '';
  return line;
}

/**
 * Phone copy budget for the in-game bubble, in characters. Derived from
 * `trainBotCopy.ts`'s `STEPPER_COPY_MAX_CHARS = 145` calibration (145 chars
 * at a 204px-wide, avatar-ABOVE-bubble Train layout, `text-sm` at 16px/24px,
 * ~24 chars/line over 6 lines). The in-game bubble keeps the avatar BESIDE
 * the copy on phones instead of above it (`BotGameBubble.tsx`), so at 375px
 * the copy box is estimated at ~271px wide (375 minus the avatar column,
 * gaps and padding) instead of Train's 204px — roughly 32 chars/line, and
 * this bubble is capped at two lines (D-07), giving roughly 64 characters.
 * The budget is a guard on that ESTIMATE, not a substitute for it — plan 06's
 * UAT re-measures the real rendered bubble at 375x667 and adjusts this
 * number if the estimate was off.
 */
export const BOT_LINE_MAX_CHARS = 64;

/**
 * The `/bots` roster page's per-persona welcome table (D-13/223-CONTEXT),
 * rendered by `PersonaGrid`'s welcome bubble. Deliberately SEPARATE from
 * `BOT_LINE_TABLES['game-start']`: a roster greeting welcomes the VISITOR
 * and may invite them to pick an opponent, while an in-game hello opens a
 * game already in progress — the two surfaces read differently even though
 * both are per-persona one-liners in the same voice. Same tone rules, same
 * `BOT_LINE_MAX_CHARS` budget, same forbidden claims as every table above.
 */
/**
 * Phase 223 UAT: the one claim every roster greeting makes in common,
 * appended after the day's host line rather than written into all 24 voices
 * — it is a product claim about the engine, not a character trait, so it
 * must read identically whichever persona is hosting. Exempt from
 * `BOT_LINE_MAX_CHARS`: that budget calibrates the IN-GAME bubble's
 * two-line slot, while the roster bubble wraps freely.
 */
export const ROSTER_HUMAN_LIKE_LINE = 'Careful, we play like humans, not like computers!';

export const ROSTER_GREETINGS: Record<PersonaId, string> = {
  'attacker-800': "Bzzz! Ziggy here. Pick a fight, any fight.",
  'attacker-1000': "Woof! Duke here. Pick a bot and let's go.",
  'attacker-1200': 'Talon here. Pick your challenger.',
  'attacker-1400': 'Fury here. Pick a fight worth having.',
  'attacker-1600': 'Butch here. Pick an opponent, charge in.',
  'attacker-1800': 'Diesel here. Pick your challenger, if you dare.',
  'trickster-800': 'Miko here! Pick a bot, any bot.',
  'trickster-1000': 'Slinky here. Pick your opponent.',
  'trickster-1200': 'Vix here. Pick one, if you dare.',
  'trickster-1400': 'Riko here. Pick a bot to outsmart.',
  'trickster-1600': 'Sly here. Pick your poison.',
  'trickster-1800': 'Cackle here! Pick chaos, any chaos.',
  'grinder-800': 'Pip here. Pick an opponent to trade with.',
  'grinder-1000': 'Dig here. Pick a bot, start digging.',
  'grinder-1200': 'Otto here. Pick your opponent, calmly.',
  'grinder-1400': 'Nell here. Pick a bot to outlast.',
  'grinder-1600': 'Tank here, recruit. Pick your opponent.',
  'grinder-1800': 'Gus here. Pick a fight worth finishing.',
  'wall-800': 'Sheldon here. Pick your opponent, slowly.',
  'wall-1000': 'Spike here. Pick a bot, no rush.',
  'wall-1200': 'Shelly here. Pick your challenger.',
  'wall-1400': 'Bruno here. Pick an opponent, or a draw.',
  'wall-1600': 'Rocco here. Pick your challenger.',
  'wall-1800': 'Hilda here. Pick an opponent, calmly.',
};

/**
 * Input for `rosterHost`. Unlike `landingHost`'s `LandingHostInput`, there is
 * no field gating on whether the intro stepper has been seen — the roster
 * has no intro stepper to wait on, so every non-null, parseable date
 * resolves straight into the rotation.
 */
export interface RosterHostInput {
  /** ISO `YYYY-MM-DD`, computed by the caller from
   * `devClockNow(readDevClockOffsetMinutes())` — this pure module never
   * reads a clock itself. `null` while unavailable. */
  today: string | null;
}

export interface RosterHost {
  persona: Persona;
  copy: string;
}

/**
 * Picks the `/bots` roster's daily welcome host + greeting. Copies
 * `landingHost`'s day-index formula (`trainBotCopy.ts`) verbatim, importing
 * the SAME `LANDING_ROTATION_EPOCH`/`LANDING_HOST_IDS` rather than declaring
 * a second copy of either — so the roster and the /train landing page agree
 * on the day's host structurally, never by coincidence
 * (`botGameCopy.test.ts` asserts the agreement directly). Unlike
 * `landingHost`, this function has NO intro-stepper gate: its only Tank
 * (`TANK_ID`) return is the null-date / unparseable-date fallback below,
 * never a "hasn't seen the intro yet" pin, because the roster has no intro
 * to wait on.
 */
export function rosterHost(input: RosterHostInput): RosterHost {
  const tank: RosterHost = {
    persona: PERSONA_REGISTRY[TANK_ID],
    copy: ROSTER_GREETINGS[TANK_ID],
  };
  if (input.today === null) return tank;
  const day = differenceInCalendarDays(parseISO(input.today), LANDING_ROTATION_EPOCH);
  if (Number.isNaN(day)) return tank;
  const index = ((day % LANDING_HOST_IDS.length) + LANDING_HOST_IDS.length) % LANDING_HOST_IDS.length;
  const id = LANDING_HOST_IDS[index];
  if (id === undefined) return tank;
  return { persona: PERSONA_REGISTRY[id], copy: ROSTER_GREETINGS[id] };
}
