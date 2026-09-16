/**
 * trainBotCopy — Phase 222 (TRAINBOT-01..08): all bot-narrated Train copy and
 * the pure casting/resolver functions that select it. No React import
 * (mirrors `lib/trainGuessLabels.ts` / `lib/trainScore.ts`'s pure-module
 * convention) — every function here is a total function of values already
 * present on `SolveResponse` / `TrainSessionResponse` / `PERSONA_REGISTRY`.
 *
 * D-06 (LOCKED): copy is authored PER OUTCOME BUCKET with a few variants,
 * never per persona/bot. Bot identity carries only the face and name —
 * `pickBot` selects WHO speaks; the copy tables below say WHAT is said,
 * completely independent of the picked persona. This was ONE scoped
 * exception (2026-09-14, owner's call) for the /train LANDING greeting
 * (`landingHost`); Phase 223 generalised per-persona copy into the RULE for
 * every bot-voice surface (`lib/botGameCopy.ts` owns the `/bots` game and
 * roster surfaces), so `landingHost` is no longer this module's one
 * exception — it is simply /train's OWN per-persona rotation, sharing its
 * epoch and id order (below, both exported) with `botGameCopy.ts`'s
 * `rosterHost` so the same bot greets a user on /train and /bots on a given
 * day structurally, not coincidentally. Every OTHER /train surface
 * (prompts, verdicts, score bubble) still stays per-outcome, unaffected.
 *
 * Casting (D-01..D-05): `BY_TEMPERAMENT` groups all 24 `PERSONA_REGISTRY`
 * entries by their `temperament` field — never a hand-maintained id list, so
 * adding/removing a persona can never silently starve a pool as long as the
 * registry itself stays exhaustive (`Record<PersonaId, Persona>`).
 */

import { differenceInCalendarDays, parseISO } from 'date-fns';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import type { Persona, PersonaId, Temperament } from '@/lib/personas/personaRegistry';
import { GUESS_CALL_LABELS } from '@/lib/trainGuessLabels';
import type { Guess } from '@/lib/trainGuessLabels';
import type { TrainMoveTier, TrainRatingBand } from '@/lib/trainScore';

/**
 * D-05: the fixed teacher for the intro stepper (steps 2-3) and the first
 * reveal walkthrough. Always Hilda — never randomly cast.
 */
export const HILDA_ID: PersonaId = 'wall-1800';

/**
 * D-05: the fixed host for intro step 1 only. Always Tank — never randomly
 * cast.
 */
export const TANK_ID: PersonaId = 'grinder-1600';

/**
 * The /train landing greeting per persona (the D-06 exception documented in
 * the module header). Each line is TWO sentences in the bot's own voice: a
 * personal opener, then an in-voice statement that the puzzles come from
 * the user's own games — the landing bubble is the only explanation of what
 * the page is, so the second half is load-bearing, not decoration.
 * `trainBotCopy.test.ts` enforces that every entry names the user's own
 * games/blunders/mistakes. `Record<PersonaId, string>` makes a missing
 * persona a compile error, so the daily rotation (`landingHost`) can never
 * land on a bot with nothing to say.
 */
export const LANDING_GREETINGS: Record<PersonaId, string> = {
  'attacker-800': 'Bzzz! Sting first, plan later. Today we sting the blunders from your own games.',
  'attacker-1000': "Woof! I sniffed out every hanging piece in your games. Let's chase them down.",
  'attacker-1200': "I've been circling your games. Every mistake I spotted is a puzzle now.",
  'attacker-1400': "Show me a weakness and I'll tear into it. Today's weaknesses come from your own games.",
  'attacker-1600': "Head down, horns out. Your own blunders are the wall we're charging today.",
  'attacker-1800': "In your games the pressure came too late to feel. Today you'll feel it early.",
  'trickster-800': "Ooh, shiny! I collected every trap from your games. Let's see if you spot them this time.",
  'trickster-1000': "Psst. I slipped your own mistakes into today's puzzles. Notice them this time.",
  'trickster-1200': "In your games you never quite knew which game you were in. Today's puzzles will tell you.",
  'trickster-1400': 'I dug through your games and stole your mistakes. You can have them back as puzzles.',
  'trickster-1600': "Sure about that move? You were last time, too. Let's replay the moments in your games that fooled you.",
  'trickster-1800': 'Ha! Your games are a goldmine of chaos. I turned the best bits into puzzles.',
  'grinder-800': "One small step at a time. Today's steps are the mistakes from your own games.",
  'grinder-1000': "I dug up the old positions from your games. The leaky ones are today's puzzles.",
  'grinder-1200': "Nice and calm now. We'll paddle back to the spots where your games went under.",
  'grinder-1400': "Take your time. Your own mistakes are waiting, and they aren't going anywhere.",
  'grinder-1600': "Welcome to boot camp, recruit! Your own blunders are today's drill.",
  'grinder-1800': 'A long fight is the good part. Today we fight the positions your games lost.',
  'wall-800': 'No rush. Slow and solid beats fast and sorry, and your games have a few sorry moments to fix.',
  'wall-1000': "Curl up, stay sharp. Today's puzzles are the moments your games weren't.",
  'wall-1200': 'Same routine every day: replay the mistakes from your own games until they stop happening.',
  'wall-1400': "I'd offer you a draw, but this is training. Your own mistakes are on the board today.",
  'wall-1600': "Everything under control? Your games say otherwise. Let's tidy up those positions.",
  'wall-1800': "Quiet position, clear head. Let's think through the moments your games went wrong.",
};

/**
 * Rotation order for `landingHost`: the authored order of `LANDING_GREETINGS`.
 * Exported (223-02) so `botGameCopy.ts`'s `rosterHost` imports this SAME id
 * order rather than declaring its own — "the same bot greets you on /train
 * and /bots today" is then structural, not two coincidentally-identical
 * lists that could silently drift apart.
 */
export const LANDING_HOST_IDS: readonly PersonaId[] = Object.keys(LANDING_GREETINGS) as PersonaId[];

/**
 * Day-zero for the landing rotation's day counter. Any fixed date works;
 * the epoch keeps the arithmetic obvious. Exported (223-02) for the same
 * reason as `LANDING_HOST_IDS` above — `rosterHost` imports this exact
 * epoch so the two rotations can never disagree about which day is which.
 */
export const LANDING_ROTATION_EPOCH = parseISO('1970-01-01');

export interface LandingHostInput {
  /** `TrainSessionResponse.session_date` (ISO `YYYY-MM-DD`), or null while
   * the session is loading/errored. Server-supplied so this module keeps its
   * D-15 "no `new Date()`" rule and the Train dev clock drives the pick. */
  sessionDate: string | null;
  /** `TrainSettingsResponse.intro_seen_at`; null (or undefined while the
   * settings query is pending/failed) means the intro has not been seen. */
  introSeenAt: string | null | undefined;
}

export interface LandingHost {
  persona: Persona;
  copy: string;
}

/**
 * Picks the /train landing host + greeting. Tank (D-05) until the intro
 * stepper has been completed, so the landing page introduces the same host
 * who opens intro step 1 ("my chess boot camp") — after that, one persona
 * per calendar day, cycling through all 24 in `LANDING_GREETINGS` order via
 * days-since-epoch modulo the roster size. Every user sees the same host on
 * a given day, which keeps the rotation explainable. Tank also covers the
 * no-date case (session still loading or errored).
 */
export function landingHost(input: LandingHostInput): LandingHost {
  const tank: LandingHost = {
    persona: PERSONA_REGISTRY[TANK_ID],
    copy: LANDING_GREETINGS[TANK_ID],
  };
  if (input.introSeenAt == null) return tank;
  if (input.sessionDate === null) return tank;
  const day = differenceInCalendarDays(parseISO(input.sessionDate), LANDING_ROTATION_EPOCH);
  if (Number.isNaN(day)) return tank;
  const index = ((day % LANDING_HOST_IDS.length) + LANDING_HOST_IDS.length) % LANDING_HOST_IDS.length;
  const id = LANDING_HOST_IDS[index];
  if (id === undefined) return tank;
  return { persona: PERSONA_REGISTRY[id], copy: LANDING_GREETINGS[id] };
}

/**
 * All 24 `PERSONA_REGISTRY` entries partitioned by `temperament` (D-01).
 * Built once at module load by reducing `Object.values(PERSONA_REGISTRY)` —
 * NOT a hand-maintained id list — so the three pools always reflect the
 * registry's current `temperament` assignments.
 */
export const BY_TEMPERAMENT: Record<Temperament, Persona[]> = (() => {
  const pools: Record<Temperament, Persona[]> = { stern: [], friendly: [], smart: [] };
  for (const persona of Object.values(PERSONA_REGISTRY)) {
    pools[persona.temperament].push(persona);
  }
  return pools;
})();

/**
 * Picks a random persona from `temperament`'s pool. `rng` defaults to
 * `Math.random` but is injectable so unit tests are deterministic without
 * patching the global (component tests may still prefer `vi.spyOn(Math,
 * 'random')` for the rendered cast — RESEARCH "do both" recommendation).
 *
 * `noUncheckedIndexedAccess` is on: the computed index is narrowed via a
 * local before being trusted, never asserted with `!`.
 */
export function pickBot(temperament: Temperament, rng: () => number = Math.random): Persona {
  const pool = BY_TEMPERAMENT[temperament];
  const index = Math.floor(rng() * pool.length);
  const picked = pool[index];
  if (picked !== undefined) return picked;
  // Every pool is proven non-empty by personaRegistry.test.ts, and rng() is
  // contracted to [0, 1), so this branch is unreachable in practice — a
  // guard-clause fallback rather than a `!` assertion.
  const fallback = pool[0];
  if (fallback !== undefined) return fallback;
  throw new Error(`pickBot: temperament pool "${temperament}" is unexpectedly empty`);
}

/**
 * D-22 regular guess prompt, spoken by the random smart host on every
 * puzzle after the first (and inside Hilda's step-3 intro bubble on the
 * very first). `sideToMove` is always the puzzle's own `side_to_move`.
 */
export function promptCopy(sideToMove: 'white' | 'black'): string {
  return `You play ${sideToMove}. Is there only one good move, or several?`;
}

/**
 * D-22 move prompt, spoken by the SAME host bubble once the guess is
 * committed (D-07: one persisting chat-row slot, copy swaps in place).
 * Phase 222 UAT: the prompt echoes the call just made (`guess`), in the
 * reveal card's own "Your call: …" vocabulary, so the answer stays on screen
 * while the move is chosen. `null` (no call recorded) drops the echo.
 */
export function movePromptCopy(sideToMove: 'white' | 'black', guess: Guess | null = null): string {
  const movePrompt = `Now play a move for ${sideToMove}.`;
  if (guess === null) return movePrompt;
  return `Your call: ${GUESS_CALL_LABELS[guess]}. ${movePrompt}`;
}

/** D-22 grading copy — shown while the move is being checked. */
export const GRADING_COPY = 'Checking your move…';

/**
 * Phone copy budget for every stepper bubble (intro + first-reveal
 * walkthrough), in characters. Calibrated in the browser at 375x667 (plan 06
 * UAT): the board column sits at its 240px floor there, the bubble copy is
 * 204px wide, and the phone base font renders `text-sm` at 16px/24px, so a
 * line holds ~24 characters. With the progress row, the 240px board, the
 * compact avatar header and a 48px button row, seven 24px lines is the most
 * that keeps the Next/guess row above the fixed bottom bar without any
 * scrolling; 143 characters measured at six lines. The budget is a guard on
 * that calibration, not a substitute for it — a new step near the limit
 * should be re-measured. The user's call: no internal scrolling in bubbles,
 * shorten or split into more steps instead.
 */
export const STEPPER_COPY_MAX_CHARS = 145;

/**
 * D-22 intro stepper step index. Five steps on a regular first session, six
 * on a warm-up one (`introStepCount`) — the union covers the longer run.
 */
export type IntroStep = 0 | 1 | 2 | 3 | 4 | 5;

/** D-22: the first-session intro stepper's speaking persona + copy per step. */
export interface IntroStepCopy {
  personaId: PersonaId;
  copy: string;
}

const INTRO_WELCOME: IntroStepCopy = {
  personaId: TANK_ID,
  copy:
    'Welcome to FlawChess Train, my chess boot camp! You will improve by solving puzzles ' +
    'created from your own games.',
};
const INTRO_QUESTION: IntroStepCopy = {
  personaId: HILDA_ID,
  copy:
    'Every puzzle starts with one question: is there only one good move ' +
    'here, or several?',
};
const INTRO_VOCABULARY: IntroStepCopy = {
  personaId: HILDA_ID,
  copy:
    'Only one: a single move is clearly best, all other moves are mistakes. ' +
    'Several: a normal position, just play a good move.',
};
const INTRO_PRACTICE: IntroStepCopy = {
  personaId: HILDA_ID,
  copy:
    "With practice, you'll learn when to slow down and calculate, and when a good " +
    'enough move played quickly is right.',
};
/**
 * Phase 222 UAT round 3: shown only on a warm-up first session. Train unlocks
 * once an import has completed, but the analysis that finds the user's own
 * mistakes may still be running, so the session is served from warm-up
 * puzzles (`TrainSessionResponse.is_warmup`). On a first-ever session that is
 * the only cause of `is_warmup` — the "caught up" cause needs prior sessions.
 */
const INTRO_WARMUP: IntroStepCopy = {
  personaId: HILDA_ID,
  copy:
    "We're still analyzing your games to find your mistakes. In the meantime, " +
    "let's start with a warm-up session.",
};

/**
 * D-22 intro stepper (D-05: Tank hosts the welcome, Hilda teaches). Short
 * steps rather than the CONTEXT's three: the plan 06 phone UAT showed the
 * three-step copy at 8-9 lines each in the 204px phone bubble, and the user
 * chose more Next clicks over internal scrolling (D-21 lets the copy be
 * tightened and split). The warm-up step is inserted right before the
 * closing step only when the session is a warm-up; the closing step asks
 * the actual guess question, so it takes `sideToMove` like `promptCopy`.
 */
export function introSteps(sideToMove: 'white' | 'black', isWarmup: boolean): IntroStepCopy[] {
  const steps: IntroStepCopy[] = [INTRO_WELCOME, INTRO_QUESTION, INTRO_VOCABULARY, INTRO_PRACTICE];
  if (isWarmup) steps.push(INTRO_WARMUP);
  steps.push({
    personaId: HILDA_ID,
    copy: `Decide first, then play. Your turn. ${promptCopy(sideToMove)}`,
  });
  return steps;
}

/** Number of intro steps for this session (5 regular, 6 warm-up). */
export function introStepCount(isWarmup: boolean): number {
  return introSteps('white', isWarmup).length;
}

/**
 * The intro step's copy for `step`. A step index past the end (a stale
 * state value after the step list shrank) resolves to the closing step
 * rather than throwing — the closing step is the one that carries the guess
 * buttons, so the user is never stranded without a control.
 */
export function introCopy(
  step: IntroStep,
  sideToMove: 'white' | 'black',
  isWarmup: boolean,
): IntroStepCopy {
  const steps = introSteps(sideToMove, isWarmup);
  const closing = steps[steps.length - 1];
  if (closing === undefined) throw new Error('introSteps: unexpectedly empty');
  return steps[step] ?? closing;
}

/**
 * D-08/D-22: the "decide first" nudge shown when a piece is dropped before
 * the guess. Reuses `promptCopy` for the question half so the two never
 * drift apart.
 */
export function dropNudgeCopy(sideToMove: 'white' | 'black'): string {
  return `Decide first, then move. ${promptCopy(sideToMove)}`;
}

/** D-23: the verdict bubble's structured copy — an opener, the scoring
 * clause, and (for the 0-1 point buckets only) the look-closer line. The
 * return tail is resolved SEPARATELY by `returnPhrase` — this type carries
 * no return-date knowledge. */
export interface VerdictCopy {
  opener: string;
  clause: string;
  lookCloser: string | null;
}

/** D-23 openers, two variants per point bucket. */
const VERDICT_OPENERS: Record<0 | 1 | 2 | 3, readonly [string, string]> = {
  0: ['Not this time.', 'Not quite.'],
  1: ['Close.', 'Halfway there.'],
  2: ['Nice.', 'Solid.'],
  3: ['Good job!', 'Clean.'],
};

/** D-23: shown only for the 0 and 1 point buckets. */
const LOOK_CLOSER_LINE = 'Step through the best line and your own move to see why.';

/**
 * D-23's scoring clause — fully determined by the (correctGuess, moveQuality)
 * pair (which also determines `points`, but `points` is never re-derived
 * here — it is passed in by the caller from `scorePuzzle`). Guard-clause
 * returns, no nesting.
 */
function verdictClause(correctGuess: boolean, moveQuality: TrainMoveTier): string {
  if (correctGuess && moveQuality === 'good') return 'Right call [+1], right move [+2].';
  if (correctGuess && moveQuality === 'inaccuracy') return 'Right call [+1], decent move [+1].';
  if (correctGuess) return 'Right call [+1], wrong move [+0].';
  if (moveQuality === 'good') return 'Wrong call [+0], but the right move [+2].';
  if (moveQuality === 'inaccuracy') return 'Wrong call [+0], decent move [+1].';
  return 'Wrong call [+0], wrong move [+0].';
}

/**
 * D-23: resolves the verdict bubble's opener + clause + optional
 * look-closer line. `points` comes from `scorePuzzle(correctGuess,
 * moveQuality)` at the call site — never re-derived here (Option B, LOCKED).
 * `rng` is injectable per the `pickBot` convention above.
 */
export function verdictCopy(
  points: 0 | 1 | 2 | 3,
  correctGuess: boolean,
  moveQuality: TrainMoveTier,
  rng: () => number = Math.random,
): VerdictCopy {
  const openers = VERDICT_OPENERS[points];
  const opener = rng() < 0.5 ? openers[0] : openers[1];
  return {
    opener,
    clause: verdictClause(correctGuess, moveQuality),
    lookCloser: points <= 1 ? LOOK_CLOSER_LINE : null,
  };
}

/** D-23's look-closer line, exported so callers can render it identically
 * to `verdictCopy`'s own `lookCloser` field without re-typing the string. */
export function lookCloserCopy(points: 0 | 1 | 2 | 3): string | null {
  return points <= 1 ? LOOK_CLOSER_LINE : null;
}

/** D-23 return tails (D-15/D-16). */
const NEXT_SESSION_TAIL = "We'll try this one again in the next session.";
const MASTERED_TAIL = "Three in a row. You have this one down, it won't come back.";
const PARKED_TAIL = 'This one keeps slipping, so it is parked for now. On to positions that stick.';
const WARMUP_TAIL = "That one was a warm-up, so it won't come back. Your own positions will.";
/** Quick 260915-sht: the non-return lines for a herring/filler solved in a
 * REGULAR session. Bug: `returnPhrase` used to return `WARMUP_TAIL` for these
 * sources unconditionally, so a user with plenty of SR items was told a
 * routine red herring "was a warm-up" and that "your own positions will"
 * come, while the surrounding puzzles already were their own positions.
 * Warm-up is a SESSION property (`TrainSessionResponse.is_warmup`), not a
 * per-puzzle one. */
const HERRING_TAIL = "That one was a red herring, so it won't come back.";
const FILLER_TAIL = "That one was a tactics puzzle, not from your games, so it won't come back.";

/** Inputs for `returnPhrase` — every field optional so a pre-206 cached
 * reveal (RESEARCH Pitfall 7) or an incomplete fixture degrades to an empty
 * string rather than a throw or a TypeScript error at the call site. */
export interface ReturnPhraseInput {
  source?: 'sr_item' | 'red_herring' | 'sharp_filler';
  item_status?: 'active' | 'mastered' | 'parked' | null;
  due_date?: string | null;
  /** `TrainSessionResponse.is_warmup` — the SESSION is a warm-up (zero
   * surviving SR items at composition, Phase 206 D-06/D-07). Decides whether
   * a herring/filler tail says "warm-up" or just "won't come back". */
  is_warmup?: boolean;
  /** `TrainSessionResponse.session_date` — the session's own calendar date. */
  session_date?: string;
  /** `TrainSessionResponse.expires_on` — the first scheduled day strictly
   * after `session_date` (`app/services/train_scheduler.py`). */
  expires_on?: string;
}

/**
 * D-15/D-16: the return-date phrase for a single solved item. Herrings and
 * fillers never return: they get the warm-up line only in a warm-up SESSION
 * (`is_warmup`), else a neutral non-return line. Status is
 * checked strictly BEFORE any date comparison — `due_date` is a STALE value
 * for mastered/parked items (RESEARCH Finding E: `apply_result` leaves it
 * untouched on both branches), so phrasing it as a return date would lie.
 * Guard-clause returns, no nesting, no `new Date()`/`Date.now()` anywhere in
 * this module (D-15) — day arithmetic uses `differenceInCalendarDays` +
 * `parseISO`, which are DST-exact (verified in RESEARCH §Finding E).
 */
export function returnPhrase(input: ReturnPhraseInput): string {
  const neverReturns = input.source === 'red_herring' || input.source === 'sharp_filler';
  if (neverReturns && input.is_warmup === true) return WARMUP_TAIL;
  if (input.source === 'red_herring') return HERRING_TAIL;
  if (input.source === 'sharp_filler') return FILLER_TAIL;
  if (input.item_status === 'mastered') return MASTERED_TAIL;
  if (input.item_status === 'parked') return PARKED_TAIL;
  if (input.due_date == null) return '';
  if (input.expires_on == null) return '';
  // ISO "YYYY-MM-DD" strings compare lexicographically exactly like dates.
  if (input.due_date <= input.expires_on) return NEXT_SESSION_TAIL;
  if (input.session_date == null) return '';
  const days = differenceInCalendarDays(parseISO(input.due_date), parseISO(input.session_date));
  return `Let's see if you remember this in ${days} days.`;
}

/** D-24 first-reveal walkthrough step index (six steps since the phase 222
 * UAT: the line-card explanation is three steps — tap, step, free play —
 * before the "understand, don't just memorize" line). */
export type WalkthroughStep = 0 | 1 | 2 | 3 | 4 | 5;
export const WALKTHROUGH_STEP_COUNT = 6;

/** D-24: one first-reveal walkthrough step's copy + the element it spotlights.
 * `board` (phase 222 UAT) rings the board row itself, for the free-play step. */
export interface WalkthroughStepCopy {
  copy: string;
  spotlightTarget: 'verdict' | 'lines' | 'board' | 'actions';
}

/**
 * D-24: the Hilda walkthrough of the reveal, run once on the user's
 * first-ever reveal. Six steps (verdict, lines, lines, board, lines,
 * actions). The phase 222 UAT found the single line-card step unclear: a tap
 * on a card only HIGHLIGHTS its move, the arrows inside the card step
 * through the line, and the board itself accepts free moves with the eval
 * bar as the judge — three distinct interactions, so three short steps,
 * each within the phone copy budget (`STEPPER_COPY_MAX_CHARS`). Step 4
 * carries D-21's "understanding, not memorizing" message.
 *
 * `hasAnalyze` (plan 06 UAT): the action row only renders Analyze for a
 * puzzle that comes from one of the user's OWN games (`game_id` set). A
 * first-timer's first reveal is very often a warm-up puzzle (games still
 * being analyzed, `game_id` null), so the last step must not describe a
 * button that is not on screen — it explains Next and says when Analyze
 * appears instead.
 *
 * `hasSolution` (phase 222 UAT round 3): the free-play step invites the user
 * to move pieces, which departs the board and makes the action row grow a
 * Solution button — so by the time the last step describes that row, the
 * button is usually there. Same rule: only describe what is on screen.
 */
export function walkthroughCopy(
  step: WalkthroughStep,
  hasAnalyze: boolean,
  hasSolution: boolean = false,
): WalkthroughStepCopy {
  switch (step) {
    case 0:
      return {
        spotlightTarget: 'verdict',
        copy: 'This is your feedback. One point for a correct call and up to two for the move.',
      };
    case 1:
      return {
        spotlightTarget: 'lines',
        copy:
          // Phase 222 UAT round 4: the cards sit below the board on phones and
          // to its right on desktop, so the copy names both placements.
          "The cards below or on the right are the lines: your move, the best move, and the game's move. " +
          'Tap a card to highlight its move on the board.',
      };
    case 2:
      return {
        spotlightTarget: 'lines',
        copy:
          'The arrows inside a card play its line move by move on the board, so you ' +
          'can see how it continues.',
      };
    case 3:
      return {
        spotlightTarget: 'board',
        copy:
          'You can also move the pieces freely to test your own ideas. The eval bar ' +
          'next to the board judges every position.',
      };
    case 4:
      return {
        spotlightTarget: 'lines',
        copy:
          'Understanding why a move works or fails by analyzing the lines is what makes ' +
          "the pattern stick. Don't just memorize the answer.",
      };
    case 5:
      return { spotlightTarget: 'actions', copy: walkthroughActionsCopy(hasAnalyze, hasSolution) };
  }
}

const WALKTHROUGH_SOLUTION_PART = 'The Solution button restores the board. ';
const WALKTHROUGH_NEXT_PART = 'Next takes you to the next puzzle.';
// Phase 222 UAT round 4: "The Solution button …" pushed the warm-up variant
// past `STEPPER_COPY_MAX_CHARS`, so the warm-up Analyze sentence is the short
// form.
const WALKTHROUGH_ANALYZE_LATER_PART = 'Analyze appears once puzzles come from your own games.';

/** The last walkthrough step, assembled from the buttons actually on screen. */
function walkthroughActionsCopy(hasAnalyze: boolean, hasSolution: boolean): string {
  const solution = hasSolution ? WALKTHROUGH_SOLUTION_PART : '';
  if (hasAnalyze) {
    return `${solution}Analyze opens the whole game one move before the mistake. ${WALKTHROUGH_NEXT_PART}`;
  }
  return `${solution}${WALKTHROUGH_NEXT_PART} ${WALKTHROUGH_ANALYZE_LATER_PART}`;
}

/**
 * D-21 named three must-survive messages for the first completed session:
 * origin ("these come from your own mistakes"), goal ("understanding, not
 * memorizing") and habit. Phase 222 UAT round 6 cut the first two from the
 * score bubble: at five lines it pushed the session score below the fold on
 * a phone, and the origin/goal messages are already told by the solve-loop
 * intro stepper and walkthrough. Only the habit sentence survives here, as
 * the lead-in to the reminder ask.
 */
const MUST_SURVIVE_HABIT = 'Reminders build the habit that makes Train work.';

/** The reminder ask, per `ReminderAsk`. `scan_qr` names the QR block the
 * desktop score screen renders below the button row (`useTrainReminderSlot`),
 * so "the code below" is a real on-screen element, never a dangling
 * reference. */
const REMINDER_ASK_COPY: Record<ReminderAsk, string> = {
  remind_me: 'Turn on Remind me and let the next session find you.',
  scan_qr:
    'Train works best on your phone: scan the code below to install FlawChess there ' +
    'and turn on reminders.',
  none: 'Yours are already on, so the next session will find you.',
};

const WARMUP_REMINDER_ASK_COPY: Record<ReminderAsk, string> = {
  remind_me: 'Turn on Remind me so the habit is there when they arrive.',
  scan_qr:
    'Scan the code below to install FlawChess on your phone and turn on reminders, so ' +
    'the habit is ready when they arrive.',
  none: 'Your reminders are on, so the habit will be there when they arrive.',
};

/** Every session's opener comments on the result (Phase 222 UAT round 5:
 * first, later and warm-up sessions alike; the nothing-missed variant is its
 * own comment), in D-21's voice: about the session, never about the user,
 * and always forward-looking. A `null` band (nothing scored) falls back to
 * the neutral opener. */
const SESSION_OPENER: Record<TrainRatingBand, string> = {
  green: 'Strong session.',
  yellow: 'Solid session, with a few that got away.',
  red: 'Tough session. That is exactly what Train is for.',
};
const SESSION_OPENER_NEUTRAL = 'Session done.';

function sessionOpener(band: TrainRatingBand | null): string {
  return band === null ? SESSION_OPENER_NEUTRAL : SESSION_OPENER[band];
}

/** One item this session's outcome, enough to classify its return bucket
 * (D-16) — mirrors the fields `SolvedResult` gains in a later plan task. */
export interface ScoreBubbleOutcome {
  source: 'sr_item' | 'red_herring' | 'sharp_filler';
  item_status: 'active' | 'mastered' | 'parked' | null;
  due_date: string | null;
}

export type ReminderAsk = 'remind_me' | 'scan_qr' | 'none';

export interface ScoreBubbleInput {
  /** Every item solved this session (D-17/RESEARCH Finding C). */
  outcomes: ScoreBubbleOutcome[];
  /** Count of items NOT fully correct this session (guess or move wrong) —
   * drives the "nothing missed" variant. Tracked separately from `outcomes`
   * because a fully-correct item still returns later (D-18), so "returning"
   * and "missed" are independent facts. */
  missedCount: number;
  isFirstCompletedSession: boolean;
  /** D-25: a warm-up session has zero surviving SR items — mirrors
   * `TrainSessionResponse.is_warmup`. */
  isWarmup: boolean;
  /** Phase 222 UAT round 5: which reminder ask closes the first-session and
   * warm-up variants. `remind_me` names the row button (mobile, standalone);
   * `scan_qr` points at the phone QR block the desktop score screen renders
   * below the row (desktop push only fires while the browser is running);
   * `none` is desktop with reminders already on a phone, where there is
   * nothing left to ask for. */
  reminderAsk: ReminderAsk;
  /** The session's rating band, for the result comment that opens every
   * variant except nothing-missed — `null` when nothing was scored
   * (`max === 0`). */
  band: TrainRatingBand | null;
  session_date: string;
  expires_on: string;
}

export interface ScoreBubbleCopy {
  lines: string[];
}

/**
 * D-18: groups returning `sr_item`/`active` outcomes by WHEN they return
 * ("next session" vs "in N days") — never by position identifier. Mastered,
 * parked, and non-`sr_item` sources never return (D-16) and are excluded.
 * Guard-clause `continue` per loop iteration, never a nested `if` (CLAUDE.md
 * nested-loop guidance).
 */
function returningCountsSentence(input: ScoreBubbleInput): string {
  let nextSessionCount = 0;
  const laterCounts = new Map<number, number>();
  for (const outcome of input.outcomes) {
    if (outcome.source !== 'sr_item') continue;
    if (outcome.item_status !== 'active') continue;
    if (outcome.due_date == null) continue;
    if (outcome.due_date <= input.expires_on) {
      nextSessionCount += 1;
      continue;
    }
    const days = differenceInCalendarDays(parseISO(outcome.due_date), parseISO(input.session_date));
    laterCounts.set(days, (laterCounts.get(days) ?? 0) + 1);
  }
  const parts: string[] = [];
  if (nextSessionCount > 0) {
    parts.push(`${nextSessionCount} come${nextSessionCount === 1 ? 's' : ''} back next session`);
  }
  for (const [days, count] of [...laterCounts.entries()].sort((a, b) => a[0] - b[0])) {
    parts.push(`${count} in ${days} days`);
  }
  if (parts.length === 0) return 'Nothing else is coming back yet.';
  return `${parts.join(', ')}.`;
}

/**
 * Phase 222 UAT round 6 bug fix: a perfect session used to end on the return
 * counts alone, so a desktop user who missed nothing never got the "scan the
 * code below" install ask (or the "Remind me" ask on a phone) — the one
 * variant that skipped it. The ask closes this variant too: a first
 * completed session keeps the habit sentence in front of it (the user has
 * never heard about reminders yet); later sessions get the ask on its own,
 * and skip it entirely when there is nothing left to ask for (`none`).
 */
function nothingMissedReminderAsk(input: ScoreBubbleInput): string[] {
  if (input.isFirstCompletedSession) {
    return [`${MUST_SURVIVE_HABIT} ${REMINDER_ASK_COPY[input.reminderAsk]}`];
  }
  if (input.reminderAsk === 'none') return [];
  return [REMINDER_ASK_COPY[input.reminderAsk]];
}

/**
 * D-25/D-18: the score screen's bubble copy — four mutually exclusive
 * variants, evaluated in this precedence order: warm-up session, nothing
 * missed, first completed session (result + returns, then the habit
 * sentence and reminder ask), later session (one-liner).
 */
export function scoreBubbleCopy(input: ScoreBubbleInput): ScoreBubbleCopy {
  if (input.isWarmup) {
    return {
      lines: [
        `${sessionOpener(input.band)} Those were warm-ups, nothing to bring back yet. ` +
          'Once your games are analyzed, your own mistakes take over.',
        WARMUP_REMINDER_ASK_COPY[input.reminderAsk],
      ],
    };
  }
  const returning = returningCountsSentence(input);
  if (input.missedCount === 0) {
    return { lines: [`Nothing got away today. ${returning}`, ...nothingMissedReminderAsk(input)] };
  }
  if (input.isFirstCompletedSession) {
    return {
      lines: [
        `${sessionOpener(input.band)} ${returning}`,
        `${MUST_SURVIVE_HABIT} ${REMINDER_ASK_COPY[input.reminderAsk]}`,
      ],
    };
  }
  return { lines: [`${sessionOpener(input.band)} ${returning} See you tomorrow.`] };
}
