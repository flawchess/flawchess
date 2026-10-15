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
  tourAnswerKind,
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
  ScoreBubbleOutcome,
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

const ALL_AUDIENCES: TrainCopyAudience[] = [
  AUDIENCE_HAS_GAMES,
  AUDIENCE_GUEST_WITH_GAMES,
  AUDIENCE_NO_GAMES,
  AUDIENCE_NO_GAMES_GUEST,
];
// The four D-19 audience welcomes, verbatim (Phase 240 D-01 keeps them).
const WELCOME_BY_AUDIENCE: [TrainCopyAudience, string][] = [
  [
    AUDIENCE_HAS_GAMES,
    'Welcome to FlawChess Train! You will improve by solving puzzles created from your own games.',
  ],
  [
    AUDIENCE_GUEST_WITH_GAMES,
    'Welcome to FlawChess Train! Sign up free and you will improve by solving puzzles created from your own mistakes.',
  ],
  [
    AUDIENCE_NO_GAMES,
    'Welcome to FlawChess Train! Import your games and you will improve by solving puzzles created from your own mistakes.',
  ],
  [
    AUDIENCE_NO_GAMES_GUEST,
    'Welcome to FlawChess Train! Import your games and sign up, and you will improve by solving puzzles created from your own mistakes.',
  ],
];

describe('introCopy / introSteps (Phase 240 D-01, D-02: two bubbles)', () => {
  it('is exactly INTRO_STEP_COUNT (2) steps for every audience and side', () => {
    expect(INTRO_STEP_COUNT).toBe(2);
    for (const audience of ALL_AUDIENCES) {
      for (const side of ['white', 'black'] as const) {
        expect(introSteps(side, audience)).toHaveLength(INTRO_STEP_COUNT);
      }
    }
  });

  it('step 0 is Hilda and the audience welcome, verbatim', () => {
    for (const [audience, welcome] of WELCOME_BY_AUDIENCE) {
      const step = introCopy(0, 'white', audience);
      expect(step.personaId).toBe(HILDA_ID);
      expect(step.copy).toBe(welcome);
    }
  });

  it('step 1 is Hilda and the closing prompt for the puzzle side, for every audience', () => {
    for (const audience of ALL_AUDIENCES) {
      for (const side of ['white', 'black'] as const) {
        const step = introCopy(1, side, audience);
        expect(step.personaId).toBe(HILDA_ID);
        expect(step.copy).toBe(
          `Decide first, then play. Your turn. You play ${side}. Is there only one good move, or several?`,
        );
      }
    }
  });

  it('no intro copy defines the vocabulary, gives the rationale or announces a warm-up', () => {
    for (const audience of ALL_AUDIENCES) {
      for (const side of ['white', 'black'] as const) {
        for (const step of introSteps(side, audience)) {
          expect(step.copy).not.toMatch(/warm-up/i);
          expect(step.copy).not.toContain('Only one:');
          expect(step.copy).not.toMatch(/practice/i);
          expect(step.copy).not.toContain('Every puzzle starts');
        }
      }
    }
  });

  it('a step index past the end resolves to the closing step instead of throwing', () => {
    const past = 5 as IntroStep;
    expect(introCopy(past, 'white', AUDIENCE_HAS_GAMES).copy).toBe(
      introCopy(1, 'white', AUDIENCE_HAS_GAMES).copy,
    );
  });

  // Plan 06 UAT: no internal scrolling in bubbles, every stepper step must
  // fit the calibrated phone budget (see STEPPER_COPY_MAX_CHARS).
  it('every intro step, for every audience and side, fits the phone copy budget', () => {
    for (const audience of ALL_AUDIENCES) {
      for (const side of ['white', 'black'] as const) {
        for (const step of introSteps(side, audience)) {
          expect(step.copy.length).toBeLessThanOrEqual(STEPPER_COPY_MAX_CHARS);
        }
      }
    }
  });

  it('quick 261015-pjr: a guest with games is never told its games are being analyzed and gets the sign-up pitch', () => {
    const welcome = introCopy(0, 'white', AUDIENCE_GUEST_WITH_GAMES).copy;
    expect(welcome).not.toMatch(/(are analyzed|analyzing your games)/i);
    expect(welcome.toLowerCase()).toContain('sign up');
    expect(welcome).not.toContain('created from your own games');
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
      expect(verdictStripLine(correct, tier, isBest)).toBe(`${guessLabel}, ${moveLabel}`);
    },
  );

  it('states the example clauses and strip lines from the plan', () => {
    expect(verdictCopy(3, true, 'good', true, () => 0).clause).toBe('Right call [+1], best move [+2].');
    expect(verdictCopy(2, false, 'good', false, () => 0).clause).toBe(
      'Wrong call [+0], but a good move [+2].',
    );
    expect(verdictStripLine(true, 'good', true)).toBe('Right call, best move');
    expect(verdictStripLine(false, 'good', false)).toBe('Wrong call, but a good move');
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
  it('a red_herring source in a warm-up session returns the warm-up tail regardless of due_date', () => {
    const phrase = returnPhrase({
      source: 'red_herring',
      is_warmup: true,
      due_date: '2020-01-01', // arbitrary, must be ignored
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
      audience: AUDIENCE_HAS_GAMES,
    });
    expect(phrase).toContain('warm-up');
    expect(phrase).toContain('Your own positions will');
  });

  it('a sharp_filler source in a warm-up session with a non-null due_date still returns the warm-up tail', () => {
    const phrase = returnPhrase({
      source: 'sharp_filler',
      is_warmup: true,
      due_date: '2026-12-25',
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
      audience: AUDIENCE_HAS_GAMES,
    });
    expect(phrase).toContain('warm-up');
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
        audience: AUDIENCE_HAS_GAMES,
      });
      expect(phrase).toContain("won't come back");
      expect(phrase).not.toContain('warm-up');
      expect(phrase).not.toContain('own positions');
    },
  );

  it('a red_herring names itself; a sharp_filler is a tactics puzzle', () => {
    expect(
      returnPhrase({ source: 'red_herring', is_warmup: false, audience: AUDIENCE_HAS_GAMES }),
    ).toContain('red herring');
    expect(
      returnPhrase({ source: 'sharp_filler', is_warmup: false, audience: AUDIENCE_HAS_GAMES }),
    ).toContain('tactics puzzle');
  });

  it('an absent is_warmup (pre-fix cached reveal) degrades to the neutral line, not the warm-up claim', () => {
    expect(returnPhrase({ source: 'red_herring', audience: AUDIENCE_HAS_GAMES })).not.toContain(
      'warm-up',
    );
  });

  it("item_status 'mastered' returns the mastered tail even when due_date is <= expires_on (stale-date trap)", () => {
    const phrase = returnPhrase({
      item_status: 'mastered',
      due_date: '2026-09-01', // stale — well before expires_on
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
      audience: AUDIENCE_HAS_GAMES,
    });
    expect(phrase).toContain("won't come back");
  });

  it("item_status 'mastered' returns the mastered tail even when due_date equals expires_on exactly", () => {
    const phrase = returnPhrase({
      item_status: 'mastered',
      due_date: '2026-09-14',
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
      audience: AUDIENCE_HAS_GAMES,
    });
    expect(phrase).toContain("won't come back");
  });

  it("item_status 'parked' returns the parked tail under the same stale-date conditions", () => {
    const phrase = returnPhrase({
      item_status: 'parked',
      due_date: '2026-08-01', // long stale
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
      audience: AUDIENCE_HAS_GAMES,
    });
    expect(phrase).toContain('parked');
  });

  it('due_date <= expires_on returns the next-session tail', () => {
    const phrase = returnPhrase({
      item_status: 'active',
      due_date: '2026-09-14',
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
      audience: AUDIENCE_HAS_GAMES,
    });
    expect(phrase).toBe("We'll try this one again in the next session.");
  });

  it('due_date > expires_on returns the "in N days" tail with N = differenceInCalendarDays(due_date, session_date)', () => {
    const phrase = returnPhrase({
      item_status: 'active',
      due_date: '2026-09-17',
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
      audience: AUDIENCE_HAS_GAMES,
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
        audience: AUDIENCE_HAS_GAMES,
      }),
    ).not.toThrow();
    expect(
      returnPhrase({
        item_status: 'active',
        due_date: null,
        session_date: '2026-09-13',
        expires_on: '2026-09-14',
        audience: AUDIENCE_HAS_GAMES,
      }),
    ).toBe('');
  });

  it('source, item_status and due_date all undefined returns an empty string', () => {
    expect(returnPhrase({ audience: AUDIENCE_HAS_GAMES })).toBe('');
  });
});

describe('returnPhrase — D-03 games-less warm-up tail audience branch (Phase 224)', () => {
  const NEVER_ANALYZED = /(are analyzed|analyzing your games)/i;
  const warmupTail = (audience: TrainCopyAudience): string =>
    returnPhrase({
      source: 'red_herring',
      is_warmup: true,
      session_date: '2026-09-13',
      expires_on: '2026-09-14',
      audience,
    });

  it('a registered account with games is byte-identical to today\'s warm-up tail', () => {
    expect(warmupTail(AUDIENCE_HAS_GAMES)).toBe(
      "That one was a warm-up, so it won't come back. Your own positions will.",
    );
  });

  it('quick 261015-pjr: a guest with games gets the sign-up tail, never the bare "your own positions will"', () => {
    const phrase = warmupTail(AUDIENCE_GUEST_WITH_GAMES);
    expect(phrase).not.toBe(warmupTail(AUDIENCE_HAS_GAMES));
    expect(phrase).toContain('Sign up free');
    expect(phrase).not.toContain('Import your games');
  });

  it('no zero-game audience claims its games are being analyzed', () => {
    expect(warmupTail(AUDIENCE_NO_GAMES)).not.toMatch(NEVER_ANALYZED);
    expect(warmupTail(AUDIENCE_NO_GAMES_GUEST)).not.toMatch(NEVER_ANALYZED);
  });

  it('a registered zero-game account reads import-only copy, never a sign-up ask', () => {
    const phrase = warmupTail(AUDIENCE_NO_GAMES);
    expect(phrase).not.toContain('sign up');
    expect(phrase).toContain('Import your games');
  });

  it('a zero-game guest reads import first, sign up second', () => {
    const phrase = warmupTail(AUDIENCE_NO_GAMES_GUEST);
    expect(phrase).toContain('sign up');
    const importIndex = phrase.toLowerCase().indexOf('mport');
    const signUpIndex = phrase.toLowerCase().indexOf('sign up');
    expect(importIndex).toBeGreaterThanOrEqual(0);
    expect(signUpIndex).toBeGreaterThan(importIndex);
  });
});

describe('reveal tour parts (Phase 240)', () => {
  const BASE_CTX: WalkthroughContext = {
    analyzeOpens: 'game',
    mergedChip: null,
    isDesktop: false,
    answerKind: 'sharp',
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

  it('part 1 is result + next, part 2 chips + stepping, part 3 sidelines + understand + analyze', () => {
    expect(tourPartSteps(0)).toEqual(['result', 'next']);
    expect(tourPartSteps(1)).toEqual(['chips', 'stepping']);
    expect(tourPartSteps(2)).toEqual(['sidelines', 'understand', 'analyze']);
  });

  it('soft and herring puzzles teach the several wording, sharp the only-one wording', () => {
    expect(tourAnswerKind('sharp')).toBe('sharp');
    expect(tourAnswerKind('soft')).toBe('several');
    expect(tourAnswerKind('herring')).toBe('several');
  });

  it('the result bubble is the D-19 sheet verbatim per device and answer kind, spotlighting the verdict', () => {
    const cases: Array<[boolean, 'sharp' | 'several', string]> = [
      [
        false,
        'sharp',
        'This strip is your result. Here only one move was good, every other move was a mistake. Tap the strip for the full feedback.',
      ],
      [
        false,
        'several',
        'This strip is your result. Here several moves were fine, so any good move works. Tap the strip for the full feedback.',
      ],
      [
        true,
        'sharp',
        'Your result is in the highlighted bubble. Here only one move was good, every other move was a mistake.',
      ],
      [
        true,
        'several',
        'Your result is in the highlighted bubble. Here several moves were fine, so any good move works.',
      ],
    ];
    for (const [isDesktop, answerKind, expected] of cases) {
      const step = tourStepCopy('result', { ...BASE_CTX, isDesktop, answerKind });
      expect(step.copy).toBe(expected);
      expect(step.spotlightTarget).toBe('verdict');
      // D-05: no scoring sentence; D-19: no em-dash.
      expect(step.copy).not.toMatch(/point/i);
      expect(step.copy).not.toContain('—');
      expect(step.copy.length).toBeLessThanOrEqual(STEPPER_COPY_MAX_CHARS);
    }
  });

  it('the next bubble spotlights the bar', () => {
    const step = tourStepCopy('next', BASE_CTX);
    expect(step.copy).toBe('Next takes you to the next puzzle.');
    expect(step.spotlightTarget).toBe('bar');
  });

  it('the Analyze bubble is the D-19 sheet per analyze target and spotlights the bar', () => {
    const game = tourStepCopy('analyze', { ...BASE_CTX, analyzeOpens: 'game' });
    const position = tourStepCopy('analyze', { ...BASE_CTX, analyzeOpens: 'position' });
    expect(game.copy).toBe(
      'The Analyze button opens the whole game one move before the mistake, so you can see how you got there.',
    );
    expect(position.copy).toBe('The Analyze button opens this position on the analysis board.');
    expect(game.spotlightTarget).toBe('bar');
    expect(position.spotlightTarget).toBe('bar');
  });

  it('chips, stepping, sidelines and understand are today\'s strings, per device and merged chip', () => {
    const { back, forward, rewind } = TOUR_ICON_TOKEN;
    const chips = 'The Move, Best, and Game chips are the lines, one per move. Tap one to focus it on the board.';
    expect(tourStepCopy('chips', BASE_CTX).copy).toBe(chips);
    expect(tourStepCopy('chips', { ...BASE_CTX, mergedChip: 'best' }).copy).toBe(
      `${chips} "Move = Best" means you found the best move.`,
    );
    expect(tourStepCopy('chips', { ...BASE_CTX, mergedChip: 'game' }).copy).toBe(
      `${chips} "Move = Game" means you played the game move.`,
    );
    expect(tourStepCopy('stepping', { ...BASE_CTX, isDesktop: false }).copy).toBe(
      `Step through the focused line with ${back} ${forward} in the bar, or tap a move in the list.`,
    );
    expect(tourStepCopy('stepping', { ...BASE_CTX, isDesktop: true }).copy).toBe(
      `Step through the focused line with ${back} ${forward} under the board, the arrow keys, or a tap on a move in the list.`,
    );
    expect(tourStepCopy('sidelines', { ...BASE_CTX, isDesktop: false }).copy).toBe(
      `Move a piece to try your own idea: it branches off as a sideline. ${rewind} in the bar takes you back to the puzzle position.`,
    );
    expect(tourStepCopy('sidelines', { ...BASE_CTX, isDesktop: true }).copy).toBe(
      `Move a piece to try your own idea: it branches off as a sideline. ${rewind} or Home takes you back to the puzzle position.`,
    );
    expect(tourStepCopy('understand', BASE_CTX).copy).toBe(
      "Understanding why a move works or fails by analyzing the lines is what makes the pattern stick. Don't just memorize the answer.",
    );
  });

  it('every step spotlights its target, whatever the context', () => {
    const targets: Record<TourStepId, string> = {
      result: 'verdict',
      next: 'bar',
      chips: 'chips',
      stepping: 'tree',
      sidelines: 'board',
      understand: 'lines',
      analyze: 'bar',
    };
    for (const [step, target] of Object.entries(targets)) {
      expect(tourStepCopy(step as TourStepId, BASE_CTX).spotlightTarget, step).toBe(target);
      expect(tourStepCopy(step as TourStepId, { ...BASE_CTX, isDesktop: true, answerKind: 'several' }).spotlightTarget, step).toBe(
        target,
      );
    }
  });

  // D-05, D-19, Phase 237 D-09: over every device, merged chip, analyze target and
  // answer kind, no step overruns the budget, uses an em-dash, mentions points or
  // scoring, or names a surface the reveal does not show.
  it('no step, in any context, overruns the budget, has an em-dash, a scoring word, or names a card, Solution button or eval bar', () => {
    const steps: TourStepId[] = ['result', 'next', 'chips', 'stepping', 'sidelines', 'understand', 'analyze'];
    const contexts: WalkthroughContext[] = [];
    for (const isDesktop of [false, true]) {
      for (const mergedChip of ['best', 'game', null] as const) {
        for (const analyzeOpens of ['game', 'position'] as const) {
          for (const answerKind of ['sharp', 'several'] as const) {
            contexts.push({ isDesktop, mergedChip, analyzeOpens, answerKind });
          }
        }
      }
    }
    expect(contexts).toHaveLength(24);
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
      }
    }
  });
});

describe('scoreBubbleCopy', () => {
  const BASE: ScoreBubbleInput = {
    outcomes: [],
    missedCount: 0,
    isFirstCompletedSession: false,
    isWarmup: false,
    reminderAsk: 'remind_me',
    band: 'yellow',
    session_date: '2026-09-13',
    expires_on: '2026-09-14',
    audience: AUDIENCE_HAS_GAMES,
  };

  const activeOutcome = (dueDate: string): ScoreBubbleOutcome => ({
    source: 'sr_item',
    item_status: 'active',
    due_date: dueDate,
  });

  it('first completed session is two lines: result + returns, then the habit sentence and ask (UAT round 6 cut the origin/goal messages)', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-14'), activeOutcome('2026-09-17')],
      missedCount: 2,
      isFirstCompletedSession: true,
    });
    expect(copy.lines).toHaveLength(2);
    expect(copy.lines[0]).toContain('come');
    expect(copy.lines[1]).toContain('Reminders build the habit that makes Train work.');
    const text = copy.lines.join(' ');
    expect(text).not.toContain('ordinary puzzles');
    expect(text).not.toContain('memorizing');
  });

  it('a later (non-first) session returns a one-liner, without the full SR explanation', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-14')],
      missedCount: 1,
      isFirstCompletedSession: false,
    });
    expect(copy.lines).toHaveLength(1);
    expect(copy.lines[0]).not.toContain('ordinary puzzles');
    expect(copy.lines[0]).toContain('See you tomorrow.');
  });

  it('a warm-up session (isWarmup, no SR items) returns the warm-up variant', () => {
    const copy = scoreBubbleCopy({ ...BASE, isWarmup: true, missedCount: 0 });
    const text = copy.lines.join(' ');
    expect(text).toContain('warm-ups');
    expect(text).toContain('Remind me');
  });

  // Phase 222 UAT round 5: the ask names what is actually on screen below the
  // row (the row button, the QR block, or nothing when the phone already has
  // reminders). The three must-survive messages are platform-independent.
  it('scan_qr first completed session keeps the habit sentence and asks for the phone scan, not Remind me', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-14')],
      missedCount: 1,
      isFirstCompletedSession: true,
      reminderAsk: 'scan_qr',
    });
    const text = copy.lines.join(' ');
    expect(text).toContain('Reminders build the habit that makes Train work.');
    expect(text).toContain('scan the code below');
    expect(text).not.toContain('Remind me');
  });

  it('none (phone reminders already on) first completed session asks for nothing', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-14')],
      missedCount: 1,
      isFirstCompletedSession: true,
      reminderAsk: 'none',
    });
    const text = copy.lines.join(' ');
    expect(text).toContain('Reminders build the habit that makes Train work.');
    expect(text).toContain('already on');
    expect(text).not.toContain('Remind me');
    expect(text).not.toContain('scan');
  });

  it('scan_qr warm-up session asks for the phone scan, not Remind me', () => {
    const copy = scoreBubbleCopy({ ...BASE, isWarmup: true, missedCount: 0, reminderAsk: 'scan_qr' });
    const text = copy.lines.join(' ');
    expect(text).toContain('warm-ups');
    expect(text).toContain('Scan the code below');
    expect(text).not.toContain('Remind me');
  });

  it('later session is the same one-liner for every ask (no ask at all)', () => {
    for (const reminderAsk of ['remind_me', 'scan_qr', 'none'] as const) {
      const copy = scoreBubbleCopy({
        ...BASE,
        outcomes: [activeOutcome('2026-09-14')],
        missedCount: 1,
        reminderAsk,
      });
      expect(copy.lines).toHaveLength(1);
      expect(copy.lines[0]).not.toContain('scan');
    }
  });

  it('every session opens with the result comment per band (first, later, warm-up), neutral with no band', () => {
    const variants: Array<Partial<ScoreBubbleInput>> = [
      { outcomes: [activeOutcome('2026-09-14')], missedCount: 1, isFirstCompletedSession: true },
      { outcomes: [activeOutcome('2026-09-14')], missedCount: 1, isFirstCompletedSession: false },
      { isWarmup: true, missedCount: 0 },
    ];
    for (const variant of variants) {
      const first = (band: ScoreBubbleInput['band']): string =>
        scoreBubbleCopy({ ...BASE, ...variant, band }).lines[0] ?? '';
      expect(first('green')).toMatch(/^Strong session\./);
      expect(first('yellow')).toMatch(/^Solid session/);
      expect(first('red')).toMatch(/^Tough session/);
      expect(first(null)).toMatch(/^Session done\./);
    }
  });

  it('the first-session opener leads straight into the return counts', () => {
    for (const band of ['green', 'yellow', 'red', null] as const) {
      const copy = scoreBubbleCopy({
        ...BASE,
        outcomes: [activeOutcome('2026-09-14')],
        missedCount: 1,
        isFirstCompletedSession: true,
        band,
      });
      expect(copy.lines[0]).toContain('1 comes back next session.');
    }
  });

  it('the nothing-missed variant keeps its own opener, no band comment', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-14')],
      missedCount: 0,
      band: 'green',
    });
    expect(copy.lines[0]).toMatch(/^Nothing got away today\./);
  });

  it('"nothing missed" (missedCount === 0) returns its own variant', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-14')],
      missedCount: 0,
      isFirstCompletedSession: true,
    });
    expect(copy.lines[0]).toContain('Nothing got away today.');
  });

  it('UAT round 6: a perfect first session still closes on the habit sentence + reminder ask', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-14')],
      missedCount: 0,
      isFirstCompletedSession: true,
      reminderAsk: 'scan_qr',
    });
    expect(copy.lines).toHaveLength(2);
    expect(copy.lines[1]).toMatch(/^Reminders build the habit/);
    expect(copy.lines[1]).toContain('scan the code below');
  });

  it('UAT round 6: a perfect later session on desktop without a phone install still asks for the QR scan', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-14')],
      missedCount: 0,
      isFirstCompletedSession: false,
      reminderAsk: 'scan_qr',
    });
    expect(copy.lines).toHaveLength(2);
    expect(copy.lines[1]).toContain('scan the code below');
    expect(copy.lines[1]).not.toContain('Reminders build the habit');
  });

  it('a perfect later session with nothing left to ask for (none) closes with the understanding tip, not a reminder ask', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-14')],
      missedCount: 0,
      isFirstCompletedSession: false,
      reminderAsk: 'none',
    });
    expect(copy.lines).toHaveLength(2);
    expect(copy.lines[1]).toContain('analyze why the moves work or fail');
    expect(copy.lines[1]).not.toContain('Remind me');
  });

  it('return counts are grouped by WHEN, never by position identifier — two items due the same day collapse into one count', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-17'), activeOutcome('2026-09-17')],
      missedCount: 2,
      isFirstCompletedSession: false,
    });
    expect(copy.lines[0]).toContain('2 in 4 days');
  });

  it('mastered/parked/non-sr_item outcomes are excluded from the grouped return counts', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [
        { source: 'sr_item', item_status: 'mastered', due_date: '2026-09-01' },
        { source: 'sr_item', item_status: 'parked', due_date: '2026-09-01' },
        { source: 'red_herring', item_status: null, due_date: null },
        activeOutcome('2026-09-14'),
      ],
      missedCount: 1,
      isFirstCompletedSession: false,
    });
    expect(copy.lines[0]).toContain('1 comes back next session');
  });
});

describe('scoreBubbleCopy — D-03/S-3 games-less warm-up audience branch (Phase 224)', () => {
  const WARM: ScoreBubbleInput = {
    outcomes: [],
    missedCount: 0,
    isFirstCompletedSession: false,
    isWarmup: true,
    reminderAsk: 'remind_me',
    band: 'yellow',
    session_date: '2026-09-13',
    expires_on: '2026-09-14',
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

  it('a zero-game guest opener clause reads import first, sign up second', () => {
    const copy = scoreBubbleCopy({ ...WARM, audience: AUDIENCE_NO_GAMES_GUEST });
    const importIndex = copy.lines[0].toLowerCase().indexOf('mport');
    const signUpIndex = copy.lines[0].toLowerCase().indexOf('sign up');
    expect(importIndex).toBeGreaterThanOrEqual(0);
    expect(signUpIndex).toBeGreaterThan(importIndex);
  });

  it('the four non-warm-up scoreBubbleCopy variants are unchanged for every audience', () => {
    const activeOutcome = (dueDate: string): ScoreBubbleOutcome => ({
      source: 'sr_item',
      item_status: 'active',
      due_date: dueDate,
    });
    const nonWarmupInputs: ScoreBubbleInput[] = [
      { ...WARM, isWarmup: false, missedCount: 0, outcomes: [activeOutcome('2026-09-14')] },
      {
        ...WARM,
        isWarmup: false,
        missedCount: 1,
        isFirstCompletedSession: true,
        outcomes: [activeOutcome('2026-09-14')],
      },
      {
        ...WARM,
        isWarmup: false,
        missedCount: 1,
        isFirstCompletedSession: false,
        outcomes: [activeOutcome('2026-09-14')],
      },
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
