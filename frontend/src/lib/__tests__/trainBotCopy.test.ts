/**
 * trainBotCopy.ts unit tests.
 *
 * Pure-module test template (mirrors `trainScore.test.ts`): one case per
 * behavior plus the boundary cases: the return-phrase truth table (status
 * checked BEFORE any date comparison, including the two stale-`due_date`
 * traps for mastered/parked items), the four verdict point buckets, the
 * injected-rng casting picker, and the score-bubble variant selection.
 */
import { describe, expect, it } from 'vitest';
import { scorePuzzle } from '@/lib/trainScore';
import type { TrainMoveTier } from '@/lib/trainScore';
import {
  BLUNDER_CHECK_RATIONALES,
  blunderCheckReadyCopy,
  blunderCheckScoreBubbleCopy,
  BY_TEMPERAMENT,
  GRADING_COPY,
  GUEST_SIGNUP_ASK_SCORE,
  HILDA_ID,
  INTRO_STEP_COUNT,
  LANDING_GREETINGS,
  LANDING_HOST_IDS,
  LANDING_ROTATION_EPOCH,
  STEPPER_COPY_MAX_CHARS,
  TANK_ID,
  TOUR_ICON_TOKEN,
  LANDING_HILDA_HANDOFF,
  dropNudgeCopy,
  introCopy,
  introSteps,
  isRevealTourDone,
  landingHost,
  lookCloserCopy,
  movePromptCopy,
  pickBot,
  pickPuzzleHost,
  promptCopy,
  returnPhrase,
  scoreBubbleCopy,
  tourPartForStage,
  tourPartSteps,
  tourStepCopy,
  verdictClauseParts,
  verdictCopy,
  verdictStripLine,
} from '@/lib/trainBotCopy';
import type {
  IntroStep,
  ScoreBubbleInput,
  TourStepId,
  TrainCopyAudience,
  TourContext,
  VerdictClauseInput,
} from '@/lib/trainBotCopy';
import { PERSONA_REGISTRY, personaForId } from '@/lib/personas/personaRegistry';
import type { PersonaId } from '@/lib/personas/personaRegistry';

// The three audience fixtures every branched-copy test selects between.
// `HAS_GAMES` is the original audience — the older assertions below keep
// exercising it, unchanged.
const AUDIENCE_HAS_GAMES: TrainCopyAudience = { hasGames: true, isGuest: false };
const AUDIENCE_NO_GAMES: TrainCopyAudience = { hasGames: false, isGuest: false };
const AUDIENCE_NO_GAMES_GUEST: TrainCopyAudience = { hasGames: false, isGuest: true };
// A guest WITH games is its own audience (guest games are never analyzed
// automatically), not folded into HAS_GAMES.
const AUDIENCE_GUEST_WITH_GAMES: TrainCopyAudience = { hasGames: true, isGuest: true };

describe('pickBot', () => {
  it('with an injected rng returning 0, resolves to a member of the requested pool', () => {
    const persona = pickBot('stern', () => 0);
    expect(BY_TEMPERAMENT.stern).toContain(persona);
    expect(BY_TEMPERAMENT.friendly).not.toContain(persona);
    expect(BY_TEMPERAMENT.smart).not.toContain(persona);
  });

  it('with an injected rng returning 0.999, resolves to a member of the requested pool', () => {
    const persona = pickBot('stern', () => 0.999);
    expect(BY_TEMPERAMENT.stern).toContain(persona);
    expect(BY_TEMPERAMENT.friendly).not.toContain(persona);
    expect(BY_TEMPERAMENT.smart).not.toContain(persona);
  });

  it("pickBot('stern', () => 0) and pickBot('stern', () => 0.999) both carry temperament 'stern'", () => {
    expect(pickBot('stern', () => 0).temperament).toBe('stern');
    expect(pickBot('stern', () => 0.999).temperament).toBe('stern');
  });

  it('never draws outside the requested pool for any of the three temperaments', () => {
    for (const temperament of ['stern', 'friendly', 'smart'] as const) {
      for (const draw of [0, 0.25, 0.5, 0.75, 0.999]) {
        const persona = pickBot(temperament, () => draw);
        expect(persona.temperament, `${temperament} @ ${draw}`).toBe(temperament);
      }
    }
  });
});

describe('pickPuzzleHost', () => {
  const draws = Array.from({ length: 48 }, (_, i) => i / 48);

  it('draws from every persona, all three temperaments included', () => {
    const ids = new Set(draws.map((d) => pickPuzzleHost(false, () => d).id));
    expect(ids.size).toBe(Object.keys(PERSONA_REGISTRY).length);
    expect(ids.has(HILDA_ID)).toBe(true);
  });

  it('never draws Hilda while the first-reveal tour is pending', () => {
    const ids = new Set(draws.map((d) => pickPuzzleHost(true, () => d).id));
    expect(ids.has(HILDA_ID)).toBe(false);
    expect(ids.size).toBe(Object.keys(PERSONA_REGISTRY).length - 1);
  });
});

describe('HILDA_ID / TANK_ID', () => {
  it("HILDA_ID resolves to Hilda the Hippo (temperament 'smart')", () => {
    const persona = personaForId(HILDA_ID);
    expect(persona?.name).toBe('Hilda the Hippo');
    expect(persona?.temperament).toBe('smart');
  });

  it("TANK_ID resolves to Tank the Ox (temperament 'stern')", () => {
    const persona = personaForId(TANK_ID);
    expect(persona?.name).toBe('Tank the Ox');
    expect(persona?.temperament).toBe('stern');
  });
});

describe('LANDING_GREETINGS / landingHost', () => {
  const ALL_IDS = Object.keys(PERSONA_REGISTRY) as PersonaId[];
  const SEEN = { introSeenAt: '2026-07-01T10:00:00Z' };
  // The landing bubble is the page's only explanation of what Train is, so
  // every voice must still say the puzzles come from the user's own games.
  const OWN_GAMES = /your (own )?(games|blunders|mistakes)/i;

  it('has a greeting for every registry persona that names the user\'s own games', () => {
    for (const id of ALL_IDS) {
      expect(LANDING_GREETINGS[id], id).toMatch(OWN_GAMES);
      expect(LANDING_GREETINGS[id].trim().length, id).toBeGreaterThan(0);
    }
  });

  it("Tank's greeting is the boot-camp line", () => {
    expect(LANDING_GREETINGS[TANK_ID]).toBe(
      "Welcome to boot camp, recruit! You'll learn from the mistakes in your own games and train your instinct for when a position hides a tactic.",
    );
  });

  it('is Tank until the intro has been seen (null or undefined), whatever the date', () => {
    for (const date of ['2026-07-25', '2026-07-26', '2026-08-13']) {
      expect(landingHost({ sessionDate: date, introSeenAt: null }).persona.id).toBe(TANK_ID);
      expect(landingHost({ sessionDate: date, introSeenAt: undefined }).persona.id).toBe(TANK_ID);
    }
  });

  it('hands off to Hilda only before the intro has been seen', () => {
    expect(landingHost({ sessionDate: '2026-07-25', introSeenAt: null }).copy).toBe(
      `${LANDING_GREETINGS[TANK_ID]} ${LANDING_HILDA_HANDOFF}`,
    );
    expect(landingHost({ sessionDate: null, ...SEEN }).copy).toBe(LANDING_GREETINGS[TANK_ID]);
  });

  it('is Tank with no session date (loading/error) or an unparseable one', () => {
    expect(landingHost({ sessionDate: null, ...SEEN }).persona.id).toBe(TANK_ID);
    expect(landingHost({ sessionDate: 'not-a-date', ...SEEN }).persona.id).toBe(TANK_ID);
  });

  it('always pairs the persona with that persona\'s own greeting', () => {
    for (let offset = 0; offset < ALL_IDS.length; offset += 1) {
      const date = new Date(Date.UTC(2026, 6, 1 + offset)).toISOString().slice(0, 10);
      const host = landingHost({ sessionDate: date, ...SEEN });
      expect(host.copy).toBe(LANDING_GREETINGS[host.persona.id]);
    }
  });

  it('is deterministic per date and cycles through all 24 personas over 24 consecutive days', () => {
    const seen = new Set<PersonaId>();
    for (let offset = 0; offset < ALL_IDS.length; offset += 1) {
      const date = new Date(Date.UTC(2026, 6, 1 + offset)).toISOString().slice(0, 10);
      const first = landingHost({ sessionDate: date, ...SEEN });
      const again = landingHost({ sessionDate: date, ...SEEN });
      expect(again.persona.id).toBe(first.persona.id);
      seen.add(first.persona.id);
    }
    expect(seen.size).toBe(ALL_IDS.length);
  });

  it('changes host between consecutive days and repeats after a full cycle', () => {
    const day0 = landingHost({ sessionDate: '2026-07-01', ...SEEN }).persona.id;
    const day1 = landingHost({ sessionDate: '2026-07-02', ...SEEN }).persona.id;
    const day24 = landingHost({ sessionDate: '2026-07-25', ...SEEN }).persona.id;
    expect(day1).not.toBe(day0);
    expect(day24).toBe(day0);
  });

  // LANDING_ROTATION_EPOCH/LANDING_HOST_IDS are exported (not module-private)
  // so `botGameCopy.ts`'s `rosterHost` can import this SAME epoch and id order
  // this SAME epoch and id order rather than declaring a second copy of
  // either. This is the import-side half of that contract: the primitives
  // are importable, and landingHost's own behavior (already pinned by every
  // other test in this describe block) is unchanged by the export.
  it('LANDING_ROTATION_EPOCH and LANDING_HOST_IDS are importable and landingHost is unchanged by exporting them', () => {
    expect(LANDING_HOST_IDS).toEqual(Object.keys(LANDING_GREETINGS));
    expect(LANDING_ROTATION_EPOCH).toBeInstanceOf(Date);
    // Same host resolved the un-exported way (Tank gate) and, once the
    // exported id list is consulted directly, a member of that SAME list —
    // proves the export changed nothing about which id resolves.
    const host = landingHost({ sessionDate: '2026-07-01', ...SEEN });
    expect(LANDING_HOST_IDS).toContain(host.persona.id);
    expect(host.copy).toBe(LANDING_GREETINGS[host.persona.id]);
  });
});

describe('promptCopy / movePromptCopy / GRADING_COPY', () => {
  it('promptCopy states the side to move and asks the vocabulary question', () => {
    expect(promptCopy('white')).toContain('white');
    expect(promptCopy('white')).toContain('only one good move, or several');
    expect(promptCopy('black')).toContain('black');
  });

  it('movePromptCopy tells the player to move for their own side', () => {
    expect(movePromptCopy('white')).toBe('Now play a move for white.');
    expect(movePromptCopy('black')).toBe('Now play a move for black.');
  });

  it('movePromptCopy echoes the committed call in the reveal card vocabulary', () => {
    expect(movePromptCopy('white', 'critical')).toBe(
      'Your call: only one good move. Now play a move for white.',
    );
    expect(movePromptCopy('black', 'several')).toBe(
      'Your call: several good moves. Now play a move for black.',
    );
  });

  it('GRADING_COPY is the checking-move line', () => {
    expect(GRADING_COPY).toBe('Checking your move…');
  });
});

const SIDES = ['white', 'black'] as const;
const NO_OWN_FLAGS = [false, true] as const;

describe('introCopy / introSteps (two bubbles)', () => {
  it('is exactly INTRO_STEP_COUNT (2) steps for every side and no-own-puzzles flag', () => {
    expect(INTRO_STEP_COUNT).toBe(2);
    for (const side of SIDES) {
      for (const noOwnPuzzles of NO_OWN_FLAGS) {
        expect(introSteps(side, noOwnPuzzles)).toHaveLength(INTRO_STEP_COUNT);
      }
    }
  });

  it('step 0 is Hilda and the welcome, verbatim, per no-own-puzzles flag', () => {
    const own = introCopy(0, 'white', false);
    expect(own.personaId).toBe(HILDA_ID);
    expect(own.copy).toBe(
      'Hi there! You will improve by solving puzzles created from your own games.',
    );
    const noOwn = introCopy(0, 'white', true);
    expect(noOwn.personaId).toBe(HILDA_ID);
    expect(noOwn.copy).toBe(
      'Hi there! These puzzles come from games of players at your level. Once some of your games ' +
        'are imported and analyzed, puzzles will come from your own games.',
    );
    expect(introSteps('black', true)[0]?.copy).toBe(noOwn.copy);
    expect(introSteps('black', false)[0]?.copy).toBe(own.copy);
  });

  // No import or sign-up ask before the first puzzle (it would
  // send a new user away); the score screen makes that ask. The no-own welcome
  // only says imported games will become the puzzle source.
  it('the own-games welcome never asks to import or sign up', () => {
    const copy = introCopy(0, 'white', false).copy;
    expect(copy).not.toMatch(/import|sign up/i);
    expect(copy).not.toContain('Welcome');
    expect(introCopy(0, 'white', true).copy).not.toMatch(/sign up/i);
  });

  it('step 1 is Hilda and the closing prompt for the puzzle side', () => {
    for (const side of SIDES) {
      for (const noOwnPuzzles of NO_OWN_FLAGS) {
        const step = introCopy(1, side, noOwnPuzzles);
        expect(step.personaId).toBe(HILDA_ID);
        expect(step.copy).toBe(
          `Decide first, then play. You play ${side}. Only one: a single move works, ` +
            'the others are mistakes. Several: there are at least two good moves.',
        );
      }
    }
  });

  it('only the closing step defines the vocabulary; no rationale', () => {
    for (const side of SIDES) {
      for (const noOwnPuzzles of NO_OWN_FLAGS) {
        const [welcome, closing] = introSteps(side, noOwnPuzzles);
        expect(welcome?.copy).not.toContain('Only one:');
        expect(closing?.copy).toContain('Only one:');
        expect(closing?.copy).toContain('Several:');
        for (const step of introSteps(side, noOwnPuzzles)) {
          expect(step.copy).not.toMatch(/practice/i);
          expect(step.copy).not.toContain('Every puzzle starts');
        }
      }
    }
  });

  it('a step index past the end resolves to the closing step instead of throwing', () => {
    const past = 5 as IntroStep;
    expect(introCopy(past, 'white', false).copy).toBe(introCopy(1, 'white', false).copy);
  });

  // No internal scrolling in bubbles, every stepper step must
  // fit the calibrated phone budget (see STEPPER_COPY_MAX_CHARS).
  // The owner's no-own welcome wording (D-12) is 155 chars, over the 145-char
  // guard. Seven 24px lines is the calibrated phone maximum (~24 chars a line, see
  // STEPPER_COPY_MAX_CHARS), so it is held to that bound instead; it still needs
  // the 375x667 device measurement the budget's doc comment asks for.
  const NO_OWN_WELCOME_MAX_CHARS = 7 * 24;

  it('every intro step fits the phone copy budget; the no-own welcome fits seven lines', () => {
    for (const side of SIDES) {
      for (const noOwnPuzzles of NO_OWN_FLAGS) {
        const [welcome, closing] = introSteps(side, noOwnPuzzles);
        expect(closing?.copy.length).toBeLessThanOrEqual(STEPPER_COPY_MAX_CHARS);
        expect(welcome?.copy.length).toBeLessThanOrEqual(
          noOwnPuzzles ? NO_OWN_WELCOME_MAX_CHARS : STEPPER_COPY_MAX_CHARS,
        );
      }
    }
  });
});

describe('dropNudgeCopy', () => {
  it('leads with "Decide first, then move" and re-asks the guess question', () => {
    const copy = dropNudgeCopy('white');
    expect(copy).toContain('Decide first, then move.');
    expect(copy).toContain('only one good move, or several');
  });
});

describe('verdictClauseParts / verdictStripLine', () => {
  const base: VerdictClauseInput = {
    puzzleType: 'sharp',
    correctGuess: true,
    moveTier: 'good',
    isBest: true,
    fromOwnBlunder: false,
    fromForeignGame: false,
    disagreement: false,
    keySan: null,
  };

  /** The sentence as the details body renders it, pills as [+N]. */
  function sentence(input: VerdictClauseInput): string {
    const p = verdictClauseParts(input);
    return `${p.fact} ${p.guessLabel} [+${p.guessPoints}]${p.joiner}${p.moveLabel} [+${p.movePoints}].`;
  }

  // [puzzle type, correct call, tier, isBest, sentence, strip line]
  const TABLE: ReadonlyArray<
    readonly [VerdictClauseInput['puzzleType'], boolean, TrainMoveTier, boolean, string, string]
  > = [
    ['sharp', true, 'good', true, 'Only one move works here. You called it [+1] and found it [+2].', 'Called it, found it'],
    ['sharp', true, 'wrong', false, 'Only one move works here. You called it [+1], but missed it [+0].', 'Called it, missed it'],
    ['sharp', false, 'good', true, 'Only one move works here. Wrong call [+0], but you found it [+2].', 'Wrong call, but found it'],
    ['sharp', false, 'wrong', false, 'Only one move works here. Wrong call [+0] and you missed it [+0].', 'Wrong call, missed it'],
    ['herring', true, 'good', true, 'Several moves work here. You called it [+1] and played the best one [+2].', 'Called it, best move'],
    ['herring', true, 'good', false, 'Several moves work here. You called it [+1] and played a good one [+2].', 'Called it, good move'],
    ['herring', true, 'inaccuracy', false, 'Several moves work here. You called it [+1], but played an inaccurate move [+1].', 'Called it, inaccurate move'],
    ['herring', true, 'wrong', false, "Several moves work here. You called it [+1], but yours isn't one of them [+0].", 'Called it, wrong move'],
    ['herring', false, 'good', false, 'Several moves work here. Wrong call [+0], but you played a good one [+2].', 'Wrong call, but good move'],
    ['herring', false, 'inaccuracy', false, 'Several moves work here. Wrong call [+0] and you played an inaccurate move [+1].', 'Wrong call, inaccurate move'],
    ['herring', false, 'wrong', false, "Several moves work here. Wrong call [+0] and yours isn't one of them [+0].", 'Wrong call, wrong move'],
  ];

  it.each(TABLE)('%s correct=%s tier=%s isBest=%s', (puzzleType, correctGuess, moveTier, isBest, text, strip) => {
    const input = { ...base, puzzleType, correctGuess, moveTier, isBest };
    expect(sentence(input)).toBe(text);
    expect(verdictStripLine(input)).toBe(strip);
  });

  it('the points always equal scorePuzzle (isBest only selects wording)', () => {
    for (const [puzzleType, correctGuess, moveTier, isBest] of TABLE) {
      const parts = verdictClauseParts({ ...base, puzzleType, correctGuess, moveTier, isBest });
      expect(parts.guessPoints + parts.movePoints).toBe(scorePuzzle(correctGuess, moveTier));
    }
  });

  // A sharp puzzle's only good move is the key by construction, so the phone
  // engine's isBest never turns "found it" into "a good one".
  it('a sharp good move is "found it" whatever isBest says', () => {
    expect(verdictClauseParts({ ...base, isBest: false }).moveLabel).toBe('and found it');
  });

  // "Several moves work here" alone read as "nothing happened here" at one
  // of the user's own blunders; the soft fact names the game move instead.
  it('a several-move fact on the user own blunder names the game move; a sharp fact never does', () => {
    const soft = { ...base, puzzleType: 'soft' as const, fromOwnBlunder: true };
    expect(verdictClauseParts(soft).fact).toBe('Several moves work here, just not your game move.');
    expect(verdictClauseParts({ ...base, fromOwnBlunder: true }).fact).toBe('Only one move works here.');
  });

  // D-20: a foreign puzzle's game move is a stranger's, so the sentence never says "your".
  it('a several-move fact on a foreign game says "the game move"; a herring keeps the plain fact', () => {
    const foreign = { ...base, puzzleType: 'soft' as const, fromForeignGame: true };
    expect(verdictClauseParts(foreign).fact).toBe('Several moves work here, just not the game move.');
    expect(verdictClauseParts({ ...base, puzzleType: 'herring' as const }).fact).toBe(
      'Several moves work here.',
    );
    expect(verdictClauseParts({ ...base, fromForeignGame: true }).fact).toBe('Only one move works here.');
  });

  it('a credited disagreement names the key and credits either call', () => {
    const input = { ...base, isBest: false, disagreement: true, keySan: 'Qh4' };
    expect(sentence(input)).toBe(
      "Qh4 is the engine's pick, but not the only good move. Either call counts [+1], and your move holds up [+2].",
    );
    expect(verdictStripLine(input)).toBe('Two good moves, yours holds up');
  });

  it('a credited disagreement without a key SAN still drops the "only one move" fact', () => {
    expect(verdictClauseParts({ ...base, disagreement: true }).fact).toBe('Two moves work here.');
  });

  it('a disagreement flag on an uncredited solve falls through to the normal sentence', () => {
    const input = { ...base, correctGuess: false, moveTier: 'wrong' as const, disagreement: true, keySan: 'Qh4' };
    expect(verdictClauseParts(input).fact).toBe('Only one move works here.');
  });
});

describe('verdictCopy', () => {
  it('0 and 1 point buckets carry the look-closer line', () => {
    expect(['Not this time.', 'Not quite.']).toContain(verdictCopy(0, () => 0).opener);
    expect(verdictCopy(0, () => 0).lookCloser).toBe('Step through the lines to see why.');
    expect(['Close.', 'Halfway there.']).toContain(verdictCopy(1, () => 0).opener);
    expect(verdictCopy(1, () => 0).lookCloser).not.toBeNull();
  });

  it('2 and 3 point buckets carry no look-closer line', () => {
    expect(['Nice.', 'Solid.']).toContain(verdictCopy(2, () => 0).opener);
    expect(verdictCopy(2, () => 0).lookCloser).toBeNull();
    expect(['Good job!', 'Clean.']).toContain(verdictCopy(3, () => 0).opener);
    expect(verdictCopy(3, () => 0).lookCloser).toBeNull();
  });

  it('the injected rng selects between the two opener variants deterministically', () => {
    expect(verdictCopy(3, () => 0).opener).toBe('Good job!');
    expect(verdictCopy(3, () => 0.999).opener).toBe('Clean.');
  });

  it('lookCloserCopy mirrors verdictCopy.lookCloser for all four buckets', () => {
    expect(lookCloserCopy(0)).not.toBeNull();
    expect(lookCloserCopy(1)).not.toBeNull();
    expect(lookCloserCopy(2)).toBeNull();
    expect(lookCloserCopy(3)).toBeNull();
  });
});

describe('returnPhrase (truth table)', () => {
  // The tail is per puzzle: no session input exists any more, so a foreign
  // blunder shows the same neutral line in an all-foreign session and in a mixed one.
  it('a foreign_blunder source returns the neutral foreign line, whatever its dates say', () => {
    expect(
      returnPhrase({
        source: 'foreign_blunder',
        due_date: '2020-01-01', // arbitrary, must be ignored
        session_date: '2026-09-13',
        expires_on: '2026-09-14',
      }),
    ).toBe("From a similarly rated player's game, so it won't come back.");
    expect(returnPhrase({ source: 'foreign_blunder' })).toBe(
      "From a similarly rated player's game, so it won't come back.",
    );
  });

  it('a red_herring source always names itself, whatever its dates say', () => {
    expect(
      returnPhrase({
        source: 'red_herring',
        due_date: '2020-01-01', // arbitrary, must be ignored
        session_date: '2026-09-13',
        expires_on: '2026-09-14',
      }),
    ).toBe("A red herring, so it won't come back.");
  });

  // A cached verdict or an old solved result from before the lichess fillers were
  // retired still reports 'sharp_filler'; it shows no tail.
  it('a legacy sharp_filler source returns no tail, even with a due_date', () => {
    expect(
      returnPhrase({
        source: 'sharp_filler',
        due_date: '2026-12-25',
        session_date: '2026-09-13',
        expires_on: '2026-09-14',
      }),
    ).toBe('');
  });

  it("item_status 'mastered' returns the mastered tail even when due_date is <= expires_on (stale-date trap)", () => {
    const phrase = returnPhrase({
      item_status: 'mastered',
      due_date: '2026-09-01', // stale — well before expires_on
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
    });
    expect(phrase).toContain('retired');
    expect(phrase).toContain('Two in a row');
  });

  it("item_status 'mastered' returns the mastered tail even when due_date equals expires_on exactly", () => {
    const phrase = returnPhrase({
      item_status: 'mastered',
      due_date: '2026-09-14',
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
    });
    expect(phrase).toContain('retired');
  });

  it("item_status 'parked' returns the parked tail under the same stale-date conditions", () => {
    const phrase = returnPhrase({
      item_status: 'parked',
      due_date: '2026-08-01', // long stale
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
    });
    expect(phrase).toContain('parked');
  });

  it('due_date <= expires_on returns the next-session tail', () => {
    const phrase = returnPhrase({
      item_status: 'active',
      due_date: '2026-09-14',
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
    });
    expect(phrase).toBe('Back next session.');
  });

  it('due_date > expires_on returns the "in N days" tail with N = differenceInCalendarDays(due_date, session_date)', () => {
    const phrase = returnPhrase({
      item_status: 'active',
      due_date: '2026-09-17',
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
    });
    expect(phrase).toBe('Back in 4 days.');
  });

  it('due_date == null with an active status returns an empty string, never a crash', () => {
    expect(() =>
      returnPhrase({
        item_status: 'active',
        due_date: null,
        session_date: '2026-09-13',
        expires_on: '2026-09-14',
      }),
    ).not.toThrow();
    expect(
      returnPhrase({
        item_status: 'active',
        due_date: null,
        session_date: '2026-09-13',
        expires_on: '2026-09-14',
      }),
    ).toBe('');
  });

  it('source, item_status and due_date all undefined returns an empty string', () => {
    expect(returnPhrase({})).toBe('');
  });
});

describe('reveal tour parts', () => {
  const BASE_CTX: TourContext = {
    analyzeOpens: 'game',
    isDesktop: false,
  };

  it('the stage picks the part due: 0, 1, 2 map to parts, 3 means done', () => {
    expect([0, 1, 2, 3].map((stage) => tourPartForStage(stage as 0 | 1 | 2 | 3))).toEqual([0, 1, 2, null]);
    expect([0, 1, 2, 3].map((stage) => isRevealTourDone(stage as 0 | 1 | 2 | 3))).toEqual([
      false,
      false,
      false,
      true,
    ]);
  });

  it('part 1 is the result alone, part 2 chips + stepping, part 3 sidelines + understand + analyze', () => {
    expect(tourPartSteps(0)).toEqual(['result']);
    expect(tourPartSteps(1)).toEqual(['chips', 'stepping']);
    expect(tourPartSteps(2)).toEqual(['sidelines', 'understand', 'analyze']);
  });

  it('the result bubble points at the verdict box; only phones add the tap hint', () => {
    const phone = tourStepCopy('result', { ...BASE_CTX, isDesktop: false });
    const desktop = tourStepCopy('result', { ...BASE_CTX, isDesktop: true });
    expect(phone.copy).toBe(
      'Your result is in the highlighted box. Tap it for details. Proceed with Next when ready.',
    );
    expect(desktop.copy).toBe('Your result is in the highlighted box. Proceed with Next when ready.');
    for (const step of [phone, desktop]) {
      expect(step.spotlightTarget).toBe('verdict');
      // No move feedback, the verdict box already gives it.
      expect(step.copy).not.toMatch(/only one|several/i);
      // No scoring sentence, no em-dash.
      expect(step.copy).not.toMatch(/point/i);
      expect(step.copy).not.toContain('—');
      expect(step.copy.length).toBeLessThanOrEqual(STEPPER_COPY_MAX_CHARS);
    }
  });

  it('the Analyze bubble is the per-analyze-target sheet and spotlights the Analyze button', () => {
    const game = tourStepCopy('analyze', { ...BASE_CTX, analyzeOpens: 'game' });
    const position = tourStepCopy('analyze', { ...BASE_CTX, analyzeOpens: 'position' });
    expect(game.copy).toBe(
      'The Analyze button opens the whole game one move before the mistake, so you can see how you got there.',
    );
    expect(position.copy).toBe('The Analyze button opens this position on the analysis board.');
    expect(game.spotlightTarget).toBe('analyze');
    expect(position.spotlightTarget).toBe('analyze');
  });

  it('chips, stepping, sidelines and understand are one string each, whatever the device or chip set', () => {
    const { back, forward, rewind } = TOUR_ICON_TOKEN;
    expect(tourStepCopy('chips', BASE_CTX).copy).toBe(
      "Each chip is a line: your Move, the engine's Best, and the Game move if known. Same moves share a chip. Tap or click a chip to show its line.",
    );
    expect(tourStepCopy('stepping', BASE_CTX).copy).toBe(
      `Step through the line with ${back} ${forward}, or tap or click a move in the list.`,
    );
    expect(tourStepCopy('sidelines', BASE_CTX).copy).toBe(
      `Move a piece to try your own idea: it branches off as a sideline. ${rewind} takes you back to the puzzle position.`,
    );
    expect(tourStepCopy('understand', BASE_CTX).copy).toBe(
      "Understanding why a move works or fails by analyzing the lines is what makes the pattern stick. Don't just memorize the answer.",
    );
  });

  it('every step spotlights its target, whatever the context', () => {
    const targets: Record<TourStepId, string> = {
      result: 'verdict',
      chips: 'chips',
      stepping: 'tree',
      sidelines: 'board',
      understand: 'lines',
      analyze: 'analyze',
    };
    for (const [step, target] of Object.entries(targets)) {
      expect(tourStepCopy(step as TourStepId, BASE_CTX).spotlightTarget, step).toBe(target);
      expect(tourStepCopy(step as TourStepId, { ...BASE_CTX, isDesktop: true }).spotlightTarget, step).toBe(
        target,
      );
    }
  });

  // Over every analyze target and device, no
  // step overruns the budget, uses an em-dash, mentions points or scoring, or
  // names a surface the reveal does not show. Nor uses wording
  // that only fits one device (a lone "tap", hover, swipe, keys, the phone
  // strip or a bar location), except the phone-only result tap hint.
  it('no step, in any context, overruns the budget, has an em-dash, a scoring word, or names a card, Solution button or eval bar', () => {
    const steps: TourStepId[] = ['result', 'chips', 'stepping', 'sidelines', 'understand', 'analyze'];
    const contexts: TourContext[] = [];
    for (const analyzeOpens of ['game', 'position'] as const) {
      for (const isDesktop of [false, true]) {
        contexts.push({ analyzeOpens, isDesktop });
      }
    }
    expect(contexts).toHaveLength(4);
    for (const step of steps) {
      for (const ctx of contexts) {
        const { copy } = tourStepCopy(step, ctx);
        const label = `${step} ${JSON.stringify(ctx)}`;
        expect(copy.length, label).toBeGreaterThan(0);
        expect(copy.length, label).toBeLessThanOrEqual(STEPPER_COPY_MAX_CHARS);
        expect(copy, label).not.toContain('—');
        expect(copy, label).not.toMatch(/\bpoints?\b/i);
        expect(copy, label).not.toMatch(/\bscor(e|es|ing)\b/i);
        expect(copy, label).not.toMatch(/\bcards?\b/i);
        expect(copy, label).not.toMatch(/solution/i);
        expect(copy, label).not.toMatch(/eval(uation)?\s+bar/i);
        const phoneTapHint = step === 'result' && !ctx.isDesktop;
        if (/\btap\b/i.test(copy) && !phoneTapHint) expect(copy, label).toMatch(/\btap or click\b/i);
        expect(copy, label).not.toMatch(/\b(hover|swipe|arrow keys?|home|strip)\b/i);
        expect(copy, label).not.toMatch(/\b(in|under|below) the (bar|board)\b/i);
      }
    }
  });
});

describe('scoreBubbleCopy', () => {
  const RATIONALE = 'Practice teaches you when to calculate and when a quick good move is enough.';
  const HABIT = 'Reminders build the habit that makes Train work.';
  const ASK = {
    remind_me: 'Turn on Remind me and let the next session find you.',
    scan_qr:
      'Train works best on your phone: scan the code below to install FlawChess there ' +
      'and turn on reminders.',
    none: 'Yours are already on, so the next session will find you.',
  } as const;
  const NO_OWN_ASK = {
    remind_me: 'Turn on Remind me so the habit is there when they arrive.',
    scan_qr:
      'Scan the code below to install FlawChess on your phone and turn on reminders, so ' +
      'the habit is ready when they arrive.',
    none: 'Your reminders are on, so the habit will be there when they arrive.',
  } as const;
  const OPENER = {
    green: 'Strong session.',
    yellow: 'Solid session, with a few that got away.',
    red: 'Tough session. That is exactly what Train is for.',
  } as const;
  const NOTE_FIRST = 'Those puzzles came from games of players at your level.';
  const NOTE_LATER = 'Those came from games of players at your level, so nothing comes back yet.';
  // Registered audiences; the guest audiences are covered separately below.
  const NO_OWN_CLAUSE = [
    [AUDIENCE_HAS_GAMES, 'Once your games are analyzed, your own mistakes take over.'],
    [AUDIENCE_NO_GAMES, 'Import your games and your own mistakes take over.'],
  ] as const;
  const GUEST_WITH_GAMES_CLAUSE =
    'Guest games are not analyzed automatically, so your own mistakes are not here yet.';
  const BASE: ScoreBubbleInput = {
    missedCount: 0,
    isFirstCompletedSession: false,
    noOwnPuzzles: false,
    reminderAsk: 'remind_me',
    band: 'yellow',
    audience: AUDIENCE_HAS_GAMES,
    nextSessionSeeYou: 'tomorrow',
  };

  it('regular first completed session: opener + rationale, then the habit line and the reminder ask, for every band and ask', () => {
    for (const band of ['green', 'yellow', 'red'] as const) {
      for (const reminderAsk of ['remind_me', 'scan_qr', 'none'] as const) {
        const copy = scoreBubbleCopy({
          ...BASE,
          missedCount: 2,
          isFirstCompletedSession: true,
          band,
          reminderAsk,
        });
        expect(copy.lines).toEqual([
          `${OPENER[band]} ${RATIONALE}`,
          `${HABIT} ${ASK[reminderAsk]}`,
        ]);
      }
    }
  });

  it('regular first completed session with no band uses the neutral opener', () => {
    const copy = scoreBubbleCopy({ ...BASE, missedCount: 1, isFirstCompletedSession: true, band: null });
    expect(copy.lines[0]).toBe(`Session done. ${RATIONALE}`);
  });

  it('regular later session is one line: opener + "See you tomorrow.", for every ask', () => {
    for (const band of ['green', 'yellow', 'red'] as const) {
      for (const reminderAsk of ['remind_me', 'scan_qr', 'none'] as const) {
        const copy = scoreBubbleCopy({ ...BASE, missedCount: 1, band, reminderAsk });
        expect(copy.lines).toEqual([`${OPENER[band]} See you tomorrow.`]);
      }
    }
    expect(scoreBubbleCopy({ ...BASE, missedCount: 1, band: null }).lines).toEqual([
      'Session done. See you tomorrow.',
    ]);
  });

  it('regular later session names the real next day, not always tomorrow', () => {
    expect(scoreBubbleCopy({ ...BASE, missedCount: 1, nextSessionSeeYou: 'Friday' }).lines).toEqual([
      `${OPENER.yellow} See you Friday.`,
    ]);
    expect(scoreBubbleCopy({ ...BASE, missedCount: 1, nextSessionSeeYou: 'on Nov 14' }).lines).toEqual([
      `${OPENER.yellow} See you on Nov 14.`,
    ]);
  });

  it('perfect first session: "Nothing got away today." + rationale, then the habit line and ask, ignoring the band', () => {
    for (const band of ['green', 'yellow', 'red', null] as const) {
      for (const reminderAsk of ['remind_me', 'scan_qr', 'none'] as const) {
        const copy = scoreBubbleCopy({ ...BASE, isFirstCompletedSession: true, band, reminderAsk });
        expect(copy.lines).toEqual([
          `Nothing got away today. ${RATIONALE}`,
          `${HABIT} ${ASK[reminderAsk]}`,
        ]);
      }
    }
  });

  it('perfect later session: "Nothing got away today." plus the ask, or the understanding tip when there is none', () => {
    for (const reminderAsk of ['remind_me', 'scan_qr'] as const) {
      const copy = scoreBubbleCopy({ ...BASE, reminderAsk });
      expect(copy.lines).toEqual(['Nothing got away today.', ASK[reminderAsk]]);
    }
    expect(scoreBubbleCopy({ ...BASE, reminderAsk: 'none' }).lines).toEqual([
      'Nothing got away today.',
      'Remember to analyze why the moves work or fail, not just memorize the best move.',
    ]);
  });

  it('no-own first session: rationale and the first note in line 1, the audience clause after', () => {
    for (const [audience, clause] of NO_OWN_CLAUSE) {
      const copy = scoreBubbleCopy({
        ...BASE,
        noOwnPuzzles: true,
        isFirstCompletedSession: true,
        band: 'red',
        audience,
      });
      expect(copy.lines[0]).toBe(`${OPENER.red} ${RATIONALE} ${NOTE_FIRST} ${clause}`);
      expect(copy.lines[0]).toContain('Those puzzles came from games of players at your level.');
    }
  });

  it('no-own later session: the later note in line 1, no rationale', () => {
    for (const [audience, clause] of NO_OWN_CLAUSE) {
      const copy = scoreBubbleCopy({ ...BASE, noOwnPuzzles: true, band: 'green', audience });
      expect(copy.lines[0]).toBe(`${OPENER.green} ${NOTE_LATER} ${clause}`);
      expect(copy.lines[0]).not.toContain(RATIONALE);
    }
  });

  it('a guest gets the note too, then the sign-up ask; a zero-game guest gets no clause', () => {
    const firstNoGames = scoreBubbleCopy({
      ...BASE,
      noOwnPuzzles: true,
      isFirstCompletedSession: true,
      band: 'yellow',
      audience: AUDIENCE_NO_GAMES_GUEST,
    });
    expect(firstNoGames.lines).toEqual([
      `${OPENER.yellow} ${RATIONALE} ${NOTE_FIRST}`,
      GUEST_SIGNUP_ASK_SCORE,
    ]);
    const laterNoGames = scoreBubbleCopy({
      ...BASE,
      noOwnPuzzles: true,
      band: 'green',
      audience: AUDIENCE_NO_GAMES_GUEST,
    });
    expect(laterNoGames.lines).toEqual([`${OPENER.green} ${NOTE_LATER}`, GUEST_SIGNUP_ASK_SCORE]);
    const firstWithGames = scoreBubbleCopy({
      ...BASE,
      noOwnPuzzles: true,
      isFirstCompletedSession: true,
      band: 'red',
      audience: AUDIENCE_GUEST_WITH_GAMES,
    });
    expect(firstWithGames.lines[0]).toBe(
      `${OPENER.red} ${RATIONALE} ${NOTE_FIRST} ${GUEST_WITH_GAMES_CLAUSE}`,
    );
  });

  it('the guest sign-up ask is the new line and no longer mentions where the puzzles came from', () => {
    expect(GUEST_SIGNUP_ASK_SCORE).toBe(
      'Sign up free and your own blunders become your puzzles. Your streak and everything you ' +
        'have solved stay exactly where they are.',
    );
  });

  it('no-own line 2: guest sign-up ask, has_games reminder ask, nothing for no_games', () => {
    for (const isFirstCompletedSession of [true, false]) {
      const input = { ...BASE, noOwnPuzzles: true, isFirstCompletedSession };
      for (const reminderAsk of ['remind_me', 'scan_qr', 'none'] as const) {
        expect(scoreBubbleCopy({ ...input, reminderAsk }).lines[1]).toBe(NO_OWN_ASK[reminderAsk]);
      }
      expect(scoreBubbleCopy({ ...input, audience: AUDIENCE_NO_GAMES_GUEST }).lines[1]).toBe(
        GUEST_SIGNUP_ASK_SCORE,
      );
      expect(scoreBubbleCopy({ ...input, audience: AUDIENCE_GUEST_WITH_GAMES }).lines[1]).toBe(
        GUEST_SIGNUP_ASK_SCORE,
      );
      expect(scoreBubbleCopy({ ...input, audience: AUDIENCE_NO_GAMES }).lines).toHaveLength(1);
    }
  });

  // Whatever the branch, the bubble is at most two lines and
  // never says how many puzzles come back or when.
  it('matrix: at most 2 lines and no returning counts in any branch, band, audience and reminder ask', () => {
    const RETURN_TEXT = /come back|comes back|coming back|in \d+ days|next session\./i;
    const bands = ['green', 'yellow', 'red', null] as const;
    const asks = ['remind_me', 'scan_qr', 'none'] as const;
    const flags = [false, true];
    const inputs: ScoreBubbleInput[] = flags.flatMap((noOwnPuzzles) =>
      flags.flatMap((isFirstCompletedSession) =>
        [0, 1].flatMap((missedCount) =>
          bands.flatMap((band) =>
            asks.flatMap((reminderAsk) =>
              [
                AUDIENCE_HAS_GAMES,
                AUDIENCE_GUEST_WITH_GAMES,
                AUDIENCE_NO_GAMES,
                AUDIENCE_NO_GAMES_GUEST,
              ].map((audience) => ({
                noOwnPuzzles,
                isFirstCompletedSession,
                missedCount,
                band,
                reminderAsk,
                audience,
              })),
            ),
          ),
        ),
      ),
    );
    expect(inputs).toHaveLength(2 * 2 * 2 * 4 * 3 * 4);
    for (const input of inputs) {
      const { lines } = scoreBubbleCopy(input);
      expect(lines.length).toBeGreaterThanOrEqual(1);
      expect(lines.length).toBeLessThanOrEqual(2);
      // The no-own later note says that nothing comes back yet: it is not a
      // returning-counts sentence, so it is the one allowed match.
      const checked = lines.map((line) => line.replace(NOTE_LATER, ''));
      for (const line of checked) expect(line).not.toMatch(RETURN_TEXT);
    }
  });

  it('the rationale appears in line 1 only on a first completed session', () => {
    for (const noOwnPuzzles of [false, true]) {
      for (const missedCount of [0, 1]) {
        const first = scoreBubbleCopy({ ...BASE, noOwnPuzzles, missedCount, isFirstCompletedSession: true });
        const later = scoreBubbleCopy({ ...BASE, noOwnPuzzles, missedCount, isFirstCompletedSession: false });
        expect(first.lines[0]).toContain(RATIONALE);
        expect(later.lines.join(' ')).not.toContain(RATIONALE);
      }
    }
  });
});

describe('scoreBubbleCopy, games-less no-own-puzzles audience branch', () => {
  const NO_OWN: ScoreBubbleInput = {
    missedCount: 0,
    isFirstCompletedSession: false,
    noOwnPuzzles: true,
    reminderAsk: 'remind_me',
    band: 'yellow',
    audience: AUDIENCE_HAS_GAMES,
    nextSessionSeeYou: 'tomorrow',
  };
  const NEVER_ANALYZED = /(are analyzed|analyzing your games)/i;

  it('a guest sees GUEST_SIGNUP_ASK_SCORE as the second line whenever isGuest is true, for both hasGames values', () => {
    const guestNoGames = scoreBubbleCopy({ ...NO_OWN, audience: AUDIENCE_NO_GAMES_GUEST });
    const guestWithGames = scoreBubbleCopy({ ...NO_OWN, audience: { hasGames: true, isGuest: true } });
    expect(guestNoGames.lines[1]).toBe(GUEST_SIGNUP_ASK_SCORE);
    expect(guestWithGames.lines[1]).toBe(GUEST_SIGNUP_ASK_SCORE);
  });

  it('a registered account with games keeps its reminder ask, never the sign-up ask', () => {
    const registeredWithGames = scoreBubbleCopy({ ...NO_OWN, audience: AUDIENCE_HAS_GAMES });
    expect(registeredWithGames.lines[1]).not.toBe(GUEST_SIGNUP_ASK_SCORE);
    expect(registeredWithGames.lines[1]).toContain('Turn on Remind me');
  });

  it('a registered zero-game account gets the opener only, no reminder or sign-up line', () => {
    for (const reminderAsk of ['remind_me', 'scan_qr', 'none'] as const) {
      const copy = scoreBubbleCopy({ ...NO_OWN, reminderAsk, audience: AUDIENCE_NO_GAMES });
      expect(copy.lines).toHaveLength(1);
      expect(copy.lines[0]).toContain('Import your games');
    }
  });

  it('the has_games audience is unchanged in the opener clause', () => {
    const copy = scoreBubbleCopy({ ...NO_OWN, audience: AUDIENCE_HAS_GAMES });
    expect(copy.lines[0]).toContain('Once your games are analyzed, your own mistakes take over.');
  });

  it('a guest with games is never told its games will be analyzed', () => {
    const copy = scoreBubbleCopy({ ...NO_OWN, audience: AUDIENCE_GUEST_WITH_GAMES });
    expect(copy.lines[0]).not.toMatch(NEVER_ANALYZED);
    expect(copy.lines[0]).not.toContain('Once your games are analyzed');
    expect(copy.lines[1]).toBe(GUEST_SIGNUP_ASK_SCORE);
  });

  it('no zero-game audience is told its games are being analyzed', () => {
    for (const audience of [AUDIENCE_NO_GAMES, AUDIENCE_NO_GAMES_GUEST]) {
      const copy = scoreBubbleCopy({ ...NO_OWN, audience });
      expect(copy.lines[0]).not.toMatch(NEVER_ANALYZED);
    }
  });

  it('a registered zero-game account reads import-only copy in the opener clause', () => {
    const copy = scoreBubbleCopy({ ...NO_OWN, audience: AUDIENCE_NO_GAMES });
    expect(copy.lines[0]).not.toContain('sign up');
    expect(copy.lines[0]).toContain('Import your games');
  });

  it('a zero-game guest opener never repeats the sign-up ask of line 2', () => {
    const copy = scoreBubbleCopy({ ...NO_OWN, audience: AUDIENCE_NO_GAMES_GUEST });
    expect(copy.lines[0].toLowerCase()).not.toContain('sign up');
    expect(copy.lines[1]).toBe(GUEST_SIGNUP_ASK_SCORE);
  });

  it('the own-puzzles scoreBubbleCopy variants are audience-independent', () => {
    const ownPuzzlesInputs: ScoreBubbleInput[] = [
      { ...NO_OWN, noOwnPuzzles: false, missedCount: 0 },
      { ...NO_OWN, noOwnPuzzles: false, missedCount: 1, isFirstCompletedSession: true },
      { ...NO_OWN, noOwnPuzzles: false, missedCount: 1, isFirstCompletedSession: false },
    ];
    for (const input of ownPuzzlesInputs) {
      const hasGames = scoreBubbleCopy({ ...input, audience: AUDIENCE_HAS_GAMES });
      const noGames = scoreBubbleCopy({ ...input, audience: AUDIENCE_NO_GAMES });
      const noGamesGuest = scoreBubbleCopy({ ...input, audience: AUDIENCE_NO_GAMES_GUEST });
      expect(noGames).toEqual(hasGames);
      expect(noGamesGuest).toEqual(hasGames);
    }
  });
});

describe('blunderCheckReadyCopy', () => {
  it('names the side and says it is the opponent\'s turn when the opponent moves first', () => {
    expect(blunderCheckReadyCopy('white', 'black')).toBe(
      'Check out the position: you play white, and your opponent moves next.',
    );
    expect(blunderCheckReadyCopy('black', 'white')).toBe(
      'Check out the position: you play black, and your opponent moves next.',
    );
  });

  it('says it is the user\'s turn when the start FEN has the user to move', () => {
    expect(blunderCheckReadyCopy('white', 'white')).toBe(
      'Check out the position: you play white, and your side moves next.',
    );
  });

  it('never says "your move" and has no em-dash', () => {
    for (const side of ['white', 'black'] as const) {
      for (const toMove of ['white', 'black'] as const) {
        const copy = blunderCheckReadyCopy(side, toMove);
        expect(copy).not.toMatch(/your move/i);
        expect(copy).not.toContain('\u2014');
      }
    }
  });
});

describe('blunderCheckScoreBubbleCopy', () => {
  it('follows the band opener with the rationale the rng selects', () => {
    BLUNDER_CHECK_RATIONALES.forEach((rationale, index) => {
      const rng = (): number => index / BLUNDER_CHECK_RATIONALES.length;
      expect(blunderCheckScoreBubbleCopy('green', rng).lines).toEqual([
        `Strong session. ${rationale}`,
      ]);
    });
  });

  it('stays in range when the rng returns its upper bound', () => {
    const lines = blunderCheckScoreBubbleCopy('red', () => 1).lines;
    const last = BLUNDER_CHECK_RATIONALES[BLUNDER_CHECK_RATIONALES.length - 1];
    expect(lines).toEqual([`Tough session. That is exactly what Train is for. ${last}`]);
  });

  it('keeps every rationale to a single em-dash-free line', () => {
    for (const rationale of BLUNDER_CHECK_RATIONALES) {
      expect(rationale).not.toMatch(/[\u2014\n]/);
    }
  });
});
