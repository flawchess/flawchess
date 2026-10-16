/**
 * trainBotCopy.test.ts — Phase 222 Plan 01 Task 2 (TRAINBOT-01..08).
 *
 * Pure-module test template (mirrors `trainScore.test.ts`): one case per
 * `<behavior>` bullet plus the boundary cases the plan's acceptance criteria
 * call out by name — the D-15/D-16 return-phrase truth table (status
 * checked BEFORE any date comparison, including the two stale-`due_date`
 * traps for mastered/parked items), the four verdict point buckets, the
 * injected-rng casting picker, and the score-bubble variant selection.
 */
import { describe, expect, it } from 'vitest';
import { scorePuzzle } from '@/lib/trainScore';
import type { TrainMoveTier } from '@/lib/trainScore';
import {
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
  WalkthroughContext,
} from '@/lib/trainBotCopy';
import { PERSONA_REGISTRY, personaForId } from '@/lib/personas/personaRegistry';
import type { PersonaId } from '@/lib/personas/personaRegistry';

// D-03 (Phase 224): the three audience fixtures every branched-copy test
// selects between. `HAS_GAMES` is the pre-224 audience — every pre-existing
// assertion below keeps exercising it, unchanged.
const AUDIENCE_HAS_GAMES: TrainCopyAudience = { hasGames: true, isGuest: false };
const AUDIENCE_NO_GAMES: TrainCopyAudience = { hasGames: false, isGuest: false };
const AUDIENCE_NO_GAMES_GUEST: TrainCopyAudience = { hasGames: false, isGuest: true };
// Quick 261015-pjr: a guest WITH games is its own audience (guest games are
// never analyzed automatically), no longer folded into HAS_GAMES.
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

describe('pickPuzzleHost (Phase 237 UAT)', () => {
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

  // 223-02: LANDING_ROTATION_EPOCH/LANDING_HOST_IDS were promoted from
  // module-private to exported so `botGameCopy.ts`'s `rosterHost` can import
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
  it('promptCopy states the side to move and asks the D-09 vocabulary question', () => {
    expect(promptCopy('white')).toContain('white');
    expect(promptCopy('white')).toContain('only one good move, or several');
    expect(promptCopy('black')).toContain('black');
  });

  it('movePromptCopy tells the player to move for their own side', () => {
    expect(movePromptCopy('white')).toBe('Now play a move for white.');
    expect(movePromptCopy('black')).toBe('Now play a move for black.');
  });

  it('movePromptCopy echoes the committed call in the reveal card vocabulary (phase 222 UAT)', () => {
    expect(movePromptCopy('white', 'critical')).toBe(
      'Your call: only one good move. Now play a move for white.',
    );
    expect(movePromptCopy('black', 'several')).toBe(
      'Your call: several good moves. Now play a move for black.',
    );
  });

  it('GRADING_COPY is the D-22 checking-move line', () => {
    expect(GRADING_COPY).toBe('Checking your move…');
  });
});

const SIDES = ['white', 'black'] as const;
const WARMUP_FLAGS = [false, true] as const;

describe('introCopy / introSteps (Phase 240 D-01, D-02: two bubbles)', () => {
  it('is exactly INTRO_STEP_COUNT (2) steps for every side and warm-up flag', () => {
    expect(INTRO_STEP_COUNT).toBe(2);
    for (const side of SIDES) {
      for (const isWarmup of WARMUP_FLAGS) {
        expect(introSteps(side, isWarmup)).toHaveLength(INTRO_STEP_COUNT);
      }
    }
  });

  it('step 0 is Hilda and the welcome, verbatim, per warm-up flag', () => {
    const regular = introCopy(0, 'white', false);
    expect(regular.personaId).toBe(HILDA_ID);
    expect(regular.copy).toBe(
      'Hi there! You will improve by solving puzzles created from your own games.',
    );
    const warmup = introCopy(0, 'white', true);
    expect(warmup.personaId).toBe(HILDA_ID);
    expect(warmup.copy).toBe(
      "Hi there! Let's start with some warm-up puzzles. They're not from your own games yet.",
    );
  });

  // Phase 240 UAT: no import or sign-up ask before the first puzzle (it would
  // send a new user away); the score screen makes that ask.
  it('the welcome never asks to import or sign up', () => {
    for (const isWarmup of WARMUP_FLAGS) {
      const copy = introCopy(0, 'white', isWarmup).copy;
      expect(copy).not.toMatch(/import|sign up/i);
      expect(copy).not.toContain('Welcome');
    }
  });

  it('step 1 is Hilda and the closing prompt for the puzzle side', () => {
    for (const side of SIDES) {
      for (const isWarmup of WARMUP_FLAGS) {
        const step = introCopy(1, side, isWarmup);
        expect(step.personaId).toBe(HILDA_ID);
        expect(step.copy).toBe(
          `Decide first, then play. You play ${side}. Only one: a single move works, ` +
            'the others are mistakes. Several: any good move will do.',
        );
      }
    }
  });

  it('only the closing step defines the vocabulary; no rationale; only a warm-up mentions warm-up', () => {
    for (const side of SIDES) {
      for (const step of introSteps(side, false)) {
        expect(step.copy).not.toMatch(/warm-up/i);
      }
      for (const isWarmup of WARMUP_FLAGS) {
        const [welcome, closing] = introSteps(side, isWarmup);
        expect(welcome?.copy).not.toContain('Only one:');
        expect(closing?.copy).toContain('Only one:');
        expect(closing?.copy).toContain('Several:');
      }
      for (const step of introSteps(side, true)) {
        expect(step.copy).not.toMatch(/practice/i);
        expect(step.copy).not.toContain('Every puzzle starts');
      }
    }
  });

  it('a step index past the end resolves to the closing step instead of throwing', () => {
    const past = 5 as IntroStep;
    expect(introCopy(past, 'white', false).copy).toBe(introCopy(1, 'white', false).copy);
  });

  // Plan 06 UAT: no internal scrolling in bubbles, every stepper step must
  // fit the calibrated phone budget (see STEPPER_COPY_MAX_CHARS).
  it('every intro step, for every side and warm-up flag, fits the phone copy budget', () => {
    for (const side of SIDES) {
      for (const isWarmup of WARMUP_FLAGS) {
        for (const step of introSteps(side, isWarmup)) {
          expect(step.copy.length).toBeLessThanOrEqual(STEPPER_COPY_MAX_CHARS);
        }
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

describe('verdictClauseParts / verdictCopy clause / verdictStripLine (Phase 237 D-05/D-06)', () => {
  // The full vocabulary table: [correct call, tier, isBest, guess label, move label,
  // guess points, move points].
  const TABLE: ReadonlyArray<readonly [boolean, TrainMoveTier, boolean, string, string, 0 | 1, 0 | 1 | 2]> = [
    [true, 'good', true, 'Right call', 'best move', 1, 2],
    [true, 'good', false, 'Right call', 'good move', 1, 2],
    [true, 'inaccuracy', false, 'Right call', 'decent move', 1, 1],
    [true, 'wrong', false, 'Right call', 'wrong move', 1, 0],
    [false, 'good', true, 'Wrong call', 'but the best move', 0, 2],
    [false, 'good', false, 'Wrong call', 'but a good move', 0, 2],
    [false, 'inaccuracy', false, 'Wrong call', 'decent move', 0, 1],
    [false, 'wrong', false, 'Wrong call', 'wrong move', 0, 0],
  ];

  it.each(TABLE)(
    'correct=%s tier=%s isBest=%s -> %s, %s',
    (correct, tier, isBest, guessLabel, moveLabel, guessPoints, movePoints) => {
      expect(verdictClauseParts(correct, tier, isBest)).toEqual({
        guessLabel,
        guessPoints,
        moveLabel,
        movePoints,
      });
      expect(verdictCopy(0, correct, tier, isBest, () => 0).clause).toBe(
        `${guessLabel} [+${guessPoints}], ${moveLabel} [+${movePoints}].`,
      );
      // Phase 240 UAT: the strip drops the article after "but".
      expect(verdictStripLine(correct, tier, isBest)).toBe(
        `${guessLabel}, ${moveLabel.replace(/^but (the|a) /, 'but ')}`,
      );
    },
  );

  it('states the example clauses and strip lines from the plan', () => {
    expect(verdictCopy(3, true, 'good', true, () => 0).clause).toBe('Right call [+1], best move [+2].');
    expect(verdictCopy(2, false, 'good', false, () => 0).clause).toBe(
      'Wrong call [+0], but a good move [+2].',
    );
    expect(verdictStripLine(true, 'good', true)).toBe('Right call, best move');
    expect(verdictStripLine(false, 'good', false)).toBe('Wrong call, but good move');
    expect(verdictStripLine(false, 'good', true)).toBe('Wrong call, but best move');
    expect(verdictStripLine(true, 'wrong', false)).toBe('Right call, wrong move');
  });

  it('isBest is ignored for the inaccuracy and wrong tiers', () => {
    for (const tier of ['inaccuracy', 'wrong'] as const) {
      expect(verdictClauseParts(true, tier, true)).toEqual(verdictClauseParts(true, tier, false));
      expect(verdictClauseParts(false, tier, true)).toEqual(verdictClauseParts(false, tier, false));
    }
  });

  it('the points always equal scorePuzzle (isBest only selects wording)', () => {
    for (const [correct, tier, isBest, , , guessPoints, movePoints] of TABLE) {
      expect(guessPoints + movePoints).toBe(scorePuzzle(correct, tier));
      const parts = verdictClauseParts(correct, tier, isBest);
      expect(parts.guessPoints + parts.movePoints).toBe(scorePuzzle(correct, tier));
    }
  });
});

describe('verdictCopy', () => {
  it('0-point bucket: wrong guess + wrong move, carries the look-closer line', () => {
    const copy = verdictCopy(0, false, 'wrong', false, () => 0);
    expect(['Not this time.', 'Not quite.']).toContain(copy.opener);
    expect(copy.clause).toBe('Wrong call [+0], wrong move [+0].');
    expect(copy.lookCloser).toBe('Step through the best line and your own move to see why.');
  });

  it('1-point bucket via correct guess + wrong move, carries the look-closer line', () => {
    const copy = verdictCopy(1, true, 'wrong', false, () => 0);
    expect(['Close.', 'Halfway there.']).toContain(copy.opener);
    expect(copy.clause).toBe('Right call [+1], wrong move [+0].');
    expect(copy.lookCloser).not.toBeNull();
  });

  it('1-point bucket via wrong guess + inaccuracy, same opener bucket, different clause', () => {
    const copy = verdictCopy(1, false, 'inaccuracy', false, () => 0);
    expect(['Close.', 'Halfway there.']).toContain(copy.opener);
    expect(copy.clause).toBe('Wrong call [+0], decent move [+1].');
  });

  it('2-point bucket via correct guess + inaccuracy, no look-closer line', () => {
    const copy = verdictCopy(2, true, 'inaccuracy', false, () => 0);
    expect(['Nice.', 'Solid.']).toContain(copy.opener);
    expect(copy.clause).toBe('Right call [+1], decent move [+1].');
    expect(copy.lookCloser).toBeNull();
  });

  it('2-point bucket via wrong guess + good move, no look-closer line', () => {
    const copy = verdictCopy(2, false, 'good', false, () => 0);
    expect(['Nice.', 'Solid.']).toContain(copy.opener);
    expect(copy.clause).toBe('Wrong call [+0], but a good move [+2].');
    expect(copy.lookCloser).toBeNull();
  });

  it('3-point bucket: correct guess + good move, no look-closer line', () => {
    const copy = verdictCopy(3, true, 'good', true, () => 0);
    expect(['Good job!', 'Clean.']).toContain(copy.opener);
    expect(copy.clause).toBe('Right call [+1], best move [+2].');
    expect(copy.lookCloser).toBeNull();
  });

  it('the injected rng selects between the two opener variants deterministically', () => {
    expect(verdictCopy(3, true, 'good', true, () => 0).opener).toBe('Good job!');
    expect(verdictCopy(3, true, 'good', true, () => 0.999).opener).toBe('Clean.');
  });

  it('lookCloserCopy mirrors verdictCopy.lookCloser for all four buckets', () => {
    expect(lookCloserCopy(0)).not.toBeNull();
    expect(lookCloserCopy(1)).not.toBeNull();
    expect(lookCloserCopy(2)).toBeNull();
    expect(lookCloserCopy(3)).toBeNull();
  });
});

describe('returnPhrase (D-15/D-16 truth table)', () => {
  // Phase 240 UAT: a warm-up herring/filler gets no tail. The per-puzzle
  // "That one was a warm-up ... your own positions will." line repeated the
  // import/sign-up ask on every warm-up puzzle.
  it('a red_herring source in a warm-up session returns no tail, regardless of due_date', () => {
    const phrase = returnPhrase({
      source: 'red_herring',
      is_warmup: true,
      due_date: '2020-01-01', // arbitrary, must be ignored
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
    });
    expect(phrase).toBe('');
  });

  it('a sharp_filler source in a warm-up session with a non-null due_date returns no tail', () => {
    const phrase = returnPhrase({
      source: 'sharp_filler',
      is_warmup: true,
      due_date: '2026-12-25',
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
    });
    expect(phrase).toBe('');
  });

  // Quick 260915-sht: a red herring is a regular part of every session. A
  // user with plenty of SR items was told a routine herring "was a warm-up"
  // and that "your own positions will" come — warm-up is a SESSION property.
  it.each(['red_herring', 'sharp_filler'] as const)(
    'a %s source in a REGULAR session gets a neutral non-return line, never the warm-up tail',
    (source) => {
      const phrase = returnPhrase({
        source,
        is_warmup: false,
        due_date: '2020-01-01', // arbitrary, must be ignored
        session_date: '2026-09-13',
        expires_on: '2026-09-14',
      });
      expect(phrase).toContain("won't come back");
      expect(phrase).not.toContain('warm-up');
      expect(phrase).not.toContain('own positions');
    },
  );

  it('a red_herring names itself; a sharp_filler is a tactics puzzle', () => {
    expect(
      returnPhrase({ source: 'red_herring', is_warmup: false }),
    ).toContain('red herring');
    expect(
      returnPhrase({ source: 'sharp_filler', is_warmup: false }),
    ).toContain('tactics puzzle');
  });

  it('an absent is_warmup (pre-fix cached reveal) degrades to the neutral line, not the warm-up claim', () => {
    expect(returnPhrase({ source: 'red_herring' })).not.toContain(
      'warm-up',
    );
  });

  it("item_status 'mastered' returns the mastered tail even when due_date is <= expires_on (stale-date trap)", () => {
    const phrase = returnPhrase({
      item_status: 'mastered',
      due_date: '2026-09-01', // stale — well before expires_on
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
    });
    expect(phrase).toContain("won't come back");
  });

  it("item_status 'mastered' returns the mastered tail even when due_date equals expires_on exactly", () => {
    const phrase = returnPhrase({
      item_status: 'mastered',
      due_date: '2026-09-14',
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
    });
    expect(phrase).toContain("won't come back");
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
    expect(phrase).toBe("We'll try this one again in the next session.");
  });

  it('due_date > expires_on returns the "in N days" tail with N = differenceInCalendarDays(due_date, session_date)', () => {
    const phrase = returnPhrase({
      item_status: 'active',
      due_date: '2026-09-17',
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
    });
    expect(phrase).toBe("Let's see if you remember this in 4 days.");
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

describe('reveal tour parts (Phase 240)', () => {
  const BASE_CTX: WalkthroughContext = {
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
      // Phase 240 UAT: no move feedback, the verdict box already gives it.
      expect(step.copy).not.toMatch(/only one|several/i);
      // D-05: no scoring sentence; D-19: no em-dash.
      expect(step.copy).not.toMatch(/point/i);
      expect(step.copy).not.toContain('—');
      expect(step.copy.length).toBeLessThanOrEqual(STEPPER_COPY_MAX_CHARS);
    }
  });

  it('the Analyze bubble is the D-19 sheet per analyze target and spotlights the Analyze button', () => {
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
      "Each chip is a line: your Move, the engine's Best, and your Game move if known. Same moves share a chip. Tap or click a chip to show its line.",
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

  // D-05, D-19, Phase 237 D-09: over every analyze target and device, no
  // step overruns the budget, uses an em-dash, mentions points or scoring, or
  // names a surface the reveal does not show. Phase 240 UAT: nor uses wording
  // that only fits one device (a lone "tap", hover, swipe, keys, the phone
  // strip or a bar location), except the phone-only result tap hint.
  it('no step, in any context, overruns the budget, has an em-dash, a scoring word, or names a card, Solution button or eval bar', () => {
    const steps: TourStepId[] = ['result', 'chips', 'stepping', 'sidelines', 'understand', 'analyze'];
    const contexts: WalkthroughContext[] = [];
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

describe('scoreBubbleCopy (Phase 240 D-16..D-19)', () => {
  const RATIONALE = 'Practice teaches you when to calculate and when a quick good move is enough.';
  const HABIT = 'Reminders build the habit that makes Train work.';
  const ASK = {
    remind_me: 'Turn on Remind me and let the next session find you.',
    scan_qr:
      'Train works best on your phone: scan the code below to install FlawChess there ' +
      'and turn on reminders.',
    none: 'Yours are already on, so the next session will find you.',
  } as const;
  const WARM_ASK = {
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
  // Registered audiences only: a guest's opening skips the warm-up note (its
  // sign-up line already says "instead of warm-ups"), covered separately below.
  const WARM_CLAUSE = [
    [AUDIENCE_HAS_GAMES, 'Once your games are analyzed, your own mistakes take over.'],
    [AUDIENCE_NO_GAMES, 'Import your games and your own mistakes take over.'],
  ] as const;
  const GUEST_WITH_GAMES_CLAUSE =
    'Guest games are not analyzed automatically, so your own mistakes are not here yet.';
  const BASE: ScoreBubbleInput = {
    missedCount: 0,
    isFirstCompletedSession: false,
    isWarmup: false,
    reminderAsk: 'remind_me',
    band: 'yellow',
    audience: AUDIENCE_HAS_GAMES,
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

  it('warm-up first session: rationale in line 1 before "Those were warm-ups.", the audience clause after', () => {
    for (const [audience, clause] of WARM_CLAUSE) {
      const copy = scoreBubbleCopy({
        ...BASE,
        isWarmup: true,
        isFirstCompletedSession: true,
        band: 'red',
        audience,
      });
      expect(copy.lines[0]).toBe(
        `${OPENER.red} ${RATIONALE} Those were warm-ups. ${clause}`,
      );
    }
  });

  it('warm-up later session: the unchanged "nothing to bring back yet" line 1, no rationale', () => {
    for (const [audience, clause] of WARM_CLAUSE) {
      const copy = scoreBubbleCopy({ ...BASE, isWarmup: true, band: 'green', audience });
      expect(copy.lines[0]).toBe(
        `${OPENER.green} Those were warm-ups, nothing to bring back yet. ${clause}`,
      );
      expect(copy.lines[0]).not.toContain(RATIONALE);
    }
  });

  it('UAT 240: a guest warm-up opening skips the warm-up note; a zero-game guest gets no clause', () => {
    const firstNoGames = scoreBubbleCopy({
      ...BASE,
      isWarmup: true,
      isFirstCompletedSession: true,
      band: 'yellow',
      audience: AUDIENCE_NO_GAMES_GUEST,
    });
    expect(firstNoGames.lines).toEqual([`${OPENER.yellow} ${RATIONALE}`, GUEST_SIGNUP_ASK_SCORE]);
    const laterNoGames = scoreBubbleCopy({
      ...BASE,
      isWarmup: true,
      band: 'green',
      audience: AUDIENCE_NO_GAMES_GUEST,
    });
    expect(laterNoGames.lines).toEqual([OPENER.green, GUEST_SIGNUP_ASK_SCORE]);
    const firstWithGames = scoreBubbleCopy({
      ...BASE,
      isWarmup: true,
      isFirstCompletedSession: true,
      band: 'red',
      audience: AUDIENCE_GUEST_WITH_GAMES,
    });
    expect(firstWithGames.lines[0]).toBe(`${OPENER.red} ${RATIONALE} ${GUEST_WITH_GAMES_CLAUSE}`);
    for (const audience of [AUDIENCE_NO_GAMES_GUEST, AUDIENCE_GUEST_WITH_GAMES]) {
      for (const isFirstCompletedSession of [true, false]) {
        const copy = scoreBubbleCopy({ ...BASE, isWarmup: true, isFirstCompletedSession, audience });
        expect(copy.lines[0]).not.toContain('warm-ups');
      }
    }
  });

  it('warm-up line 2 is unchanged in first and later sessions: guest sign-up ask, has_games reminder ask, nothing for no_games', () => {
    for (const isFirstCompletedSession of [true, false]) {
      const input = { ...BASE, isWarmup: true, isFirstCompletedSession };
      for (const reminderAsk of ['remind_me', 'scan_qr', 'none'] as const) {
        expect(scoreBubbleCopy({ ...input, reminderAsk }).lines[1]).toBe(WARM_ASK[reminderAsk]);
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

  // D-17/D-18/D-19: whatever the branch, the bubble is at most two lines and
  // never says how many puzzles come back or when.
  it('matrix: at most 2 lines and no returning text in any branch, band, audience and reminder ask', () => {
    const RETURN_TEXT = /come back|comes back|coming back|in \d+ days|next session\./i;
    const bands = ['green', 'yellow', 'red', null] as const;
    const asks = ['remind_me', 'scan_qr', 'none'] as const;
    const flags = [false, true];
    const inputs: ScoreBubbleInput[] = flags.flatMap((isWarmup) =>
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
                isWarmup,
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
      // The guest sign-up ask is a fixed, unchanged line (D-19) that says
      // "your own blunders come back": it is not a returning-counts
      // sentence, so it is the one allowed match.
      const checked = lines.filter((line) => line !== GUEST_SIGNUP_ASK_SCORE);
      for (const line of checked) expect(line).not.toMatch(RETURN_TEXT);
    }
  });

  it('the rationale appears in line 1 only on a first completed session', () => {
    for (const isWarmup of [false, true]) {
      for (const missedCount of [0, 1]) {
        const first = scoreBubbleCopy({ ...BASE, isWarmup, missedCount, isFirstCompletedSession: true });
        const later = scoreBubbleCopy({ ...BASE, isWarmup, missedCount, isFirstCompletedSession: false });
        expect(first.lines[0]).toContain(RATIONALE);
        expect(later.lines.join(' ')).not.toContain(RATIONALE);
      }
    }
  });
});

describe('scoreBubbleCopy, D-03/S-3 games-less warm-up audience branch (Phase 224)', () => {
  const WARM: ScoreBubbleInput = {
    missedCount: 0,
    isFirstCompletedSession: false,
    isWarmup: true,
    reminderAsk: 'remind_me',
    band: 'yellow',
    audience: AUDIENCE_HAS_GAMES,
  };
  const NEVER_ANALYZED = /(are analyzed|analyzing your games)/i;

  it('a guest sees GUEST_SIGNUP_ASK_SCORE as the second line whenever isGuest is true, for both hasGames values', () => {
    const guestNoGames = scoreBubbleCopy({ ...WARM, audience: AUDIENCE_NO_GAMES_GUEST });
    const guestWithGames = scoreBubbleCopy({ ...WARM, audience: { hasGames: true, isGuest: true } });
    expect(guestNoGames.lines[1]).toBe(GUEST_SIGNUP_ASK_SCORE);
    expect(guestWithGames.lines[1]).toBe(GUEST_SIGNUP_ASK_SCORE);
  });

  it('a registered account with games keeps the WARMUP_REMINDER_ASK_COPY entry, never the sign-up ask', () => {
    const registeredWithGames = scoreBubbleCopy({ ...WARM, audience: AUDIENCE_HAS_GAMES });
    expect(registeredWithGames.lines[1]).not.toBe(GUEST_SIGNUP_ASK_SCORE);
    expect(registeredWithGames.lines[1]).toContain('Turn on Remind me');
  });

  it('quick 260926-8p5: a registered zero-game account gets the opener only, no reminder or sign-up line', () => {
    for (const reminderAsk of ['remind_me', 'scan_qr', 'none'] as const) {
      const copy = scoreBubbleCopy({ ...WARM, reminderAsk, audience: AUDIENCE_NO_GAMES });
      expect(copy.lines).toHaveLength(1);
      expect(copy.lines[0]).toContain('Import your games');
    }
  });

  it('the has_games audience is byte-identical to today\'s warm-up opener clause', () => {
    const copy = scoreBubbleCopy({ ...WARM, audience: AUDIENCE_HAS_GAMES });
    expect(copy.lines[0]).toContain('Once your games are analyzed, your own mistakes take over.');
  });

  it('quick 261015-pjr: a guest with games is never told its games will be analyzed', () => {
    const copy = scoreBubbleCopy({ ...WARM, audience: AUDIENCE_GUEST_WITH_GAMES });
    expect(copy.lines[0]).not.toMatch(NEVER_ANALYZED);
    expect(copy.lines[0]).not.toContain('Once your games are analyzed');
    expect(copy.lines[1]).toBe(GUEST_SIGNUP_ASK_SCORE);
  });

  it('no zero-game audience is told its games are being analyzed', () => {
    for (const audience of [AUDIENCE_NO_GAMES, AUDIENCE_NO_GAMES_GUEST]) {
      const copy = scoreBubbleCopy({ ...WARM, audience });
      expect(copy.lines[0]).not.toMatch(NEVER_ANALYZED);
    }
  });

  it('a registered zero-game account reads import-only copy in the opener clause', () => {
    const copy = scoreBubbleCopy({ ...WARM, audience: AUDIENCE_NO_GAMES });
    expect(copy.lines[0]).not.toContain('sign up');
    expect(copy.lines[0]).toContain('Import your games');
  });

  it('UAT 240: a zero-game guest opener never repeats the sign-up ask of line 2', () => {
    const copy = scoreBubbleCopy({ ...WARM, audience: AUDIENCE_NO_GAMES_GUEST });
    expect(copy.lines[0].toLowerCase()).not.toContain('sign up');
    expect(copy.lines[1]).toBe(GUEST_SIGNUP_ASK_SCORE);
  });

  it('the non-warm-up scoreBubbleCopy variants are audience-independent', () => {
    const nonWarmupInputs: ScoreBubbleInput[] = [
      { ...WARM, isWarmup: false, missedCount: 0 },
      { ...WARM, isWarmup: false, missedCount: 1, isFirstCompletedSession: true },
      { ...WARM, isWarmup: false, missedCount: 1, isFirstCompletedSession: false },
    ];
    for (const input of nonWarmupInputs) {
      const hasGames = scoreBubbleCopy({ ...input, audience: AUDIENCE_HAS_GAMES });
      const noGames = scoreBubbleCopy({ ...input, audience: AUDIENCE_NO_GAMES });
      const noGamesGuest = scoreBubbleCopy({ ...input, audience: AUDIENCE_NO_GAMES_GUEST });
      expect(noGames).toEqual(hasGames);
      expect(noGamesGuest).toEqual(hasGames);
    }
  });
});
