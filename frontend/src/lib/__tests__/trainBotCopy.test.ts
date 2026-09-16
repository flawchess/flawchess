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
import {
  BY_TEMPERAMENT,
  GRADING_COPY,
  HILDA_ID,
  LANDING_GREETINGS,
  LANDING_HOST_IDS,
  LANDING_ROTATION_EPOCH,
  STEPPER_COPY_MAX_CHARS,
  TANK_ID,
  WALKTHROUGH_STEP_COUNT,
  dropNudgeCopy,
  introCopy,
  introStepCount,
  introSteps,
  landingHost,
  lookCloserCopy,
  movePromptCopy,
  pickBot,
  promptCopy,
  returnPhrase,
  scoreBubbleCopy,
  verdictCopy,
  walkthroughCopy,
} from '@/lib/trainBotCopy';
import type { IntroStep, ScoreBubbleInput, ScoreBubbleOutcome, WalkthroughStep } from '@/lib/trainBotCopy';
import { PERSONA_REGISTRY, personaForId } from '@/lib/personas/personaRegistry';
import type { PersonaId } from '@/lib/personas/personaRegistry';

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
      "Welcome to boot camp, recruit! Your own blunders are today's drill.",
    );
  });

  it('is Tank until the intro has been seen (null or undefined), whatever the date', () => {
    for (const date of ['2026-07-25', '2026-07-26', '2026-08-13']) {
      expect(landingHost({ sessionDate: date, introSeenAt: null }).persona.id).toBe(TANK_ID);
      expect(landingHost({ sessionDate: date, introSeenAt: undefined }).persona.id).toBe(TANK_ID);
    }
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

describe('introCopy', () => {
  it('step 0 is hosted by Tank and welcomes the user to the boot camp', () => {
    expect(introCopy(0, 'white', false).personaId).toBe(TANK_ID);
    expect(introCopy(0, 'white', false).copy).toContain('boot camp');
    expect(introCopy(0, 'white', false).copy).toContain('your own games');
  });

  it('steps 1-2 are hosted by Hilda and define the guess vocabulary', () => {
    expect(introCopy(1, 'white', false).personaId).toBe(HILDA_ID);
    expect(introCopy(1, 'white', false).copy).toContain('only one good move');
    // Quick task 260914-uer: reworded opening clause (was "Every move in a
    // game starts with..."); this assertion is what makes the reword
    // regression-proof.
    expect(introCopy(1, 'white', false).copy).toContain('Every puzzle starts with one question:');
    const step = introCopy(2, 'white', false);
    expect(step.personaId).toBe(HILDA_ID);
    expect(step.copy).toContain('Only one');
    expect(step.copy).toContain('Several');
  });

  it('step 3 carries the D-21 "when to spend time vs. play quickly" message', () => {
    const step = introCopy(3, 'white', false);
    expect(step.personaId).toBe(HILDA_ID);
    expect(step.copy).toContain('slow down and calculate');
    expect(step.copy).toContain('good enough move played quickly');
  });

  it('the last step is hosted by Hilda and asks the actual guess question for the puzzle side', () => {
    const count = introStepCount(false);
    expect(count).toBe(5);
    const step = introCopy((count - 1) as IntroStep, 'black', false);
    expect(step.personaId).toBe(HILDA_ID);
    expect(step.copy).toContain('black');
    expect(step.copy).toContain('only one good move, or several');
  });

  // Phase 222 UAT round 3: a warm-up first session (games still being
  // analyzed) gets one extra step right before the closing guess step.
  it('a warm-up session inserts the "still analyzing" step before the closing step', () => {
    expect(introStepCount(true)).toBe(6);
    const warmup = introCopy(4, 'white', true);
    expect(warmup.personaId).toBe(HILDA_ID);
    expect(warmup.copy).toContain('still analyzing your games');
    expect(warmup.copy).toContain('warm-up session');
    expect(introCopy(5, 'white', true).copy).toContain('only one good move, or several');
    // The regular run never mentions the warm-up.
    const regular = introSteps('white', false).map((step) => step.copy);
    expect(regular.some((copy) => copy.includes('warm-up'))).toBe(false);
  });

  it('a step index past the end resolves to the closing step instead of throwing', () => {
    expect(introCopy(5, 'white', false).copy).toBe(introCopy(4, 'white', false).copy);
  });

  // Plan 06 UAT: no internal scrolling in bubbles — every stepper step must
  // fit the calibrated phone budget (see STEPPER_COPY_MAX_CHARS).
  it('every intro step, for both sides and both session kinds, fits the phone copy budget', () => {
    for (const isWarmup of [false, true]) {
      for (const side of ['white', 'black'] as const) {
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

describe('verdictCopy', () => {
  it('0-point bucket: wrong guess + wrong move, carries the look-closer line', () => {
    const copy = verdictCopy(0, false, 'wrong', () => 0);
    expect(['Not this time.', 'Not quite.']).toContain(copy.opener);
    expect(copy.clause).toBe('Wrong call [+0], wrong move [+0].');
    expect(copy.lookCloser).toBe('Step through the best line and your own move to see why.');
  });

  it('1-point bucket via correct guess + wrong move, carries the look-closer line', () => {
    const copy = verdictCopy(1, true, 'wrong', () => 0);
    expect(['Close.', 'Halfway there.']).toContain(copy.opener);
    expect(copy.clause).toBe('Right call [+1], wrong move [+0].');
    expect(copy.lookCloser).not.toBeNull();
  });

  it('1-point bucket via wrong guess + inaccuracy, same opener bucket, different clause', () => {
    const copy = verdictCopy(1, false, 'inaccuracy', () => 0);
    expect(['Close.', 'Halfway there.']).toContain(copy.opener);
    expect(copy.clause).toBe('Wrong call [+0], decent move [+1].');
  });

  it('2-point bucket via correct guess + inaccuracy, no look-closer line', () => {
    const copy = verdictCopy(2, true, 'inaccuracy', () => 0);
    expect(['Nice.', 'Solid.']).toContain(copy.opener);
    expect(copy.clause).toBe('Right call [+1], decent move [+1].');
    expect(copy.lookCloser).toBeNull();
  });

  it('2-point bucket via wrong guess + good move, no look-closer line', () => {
    const copy = verdictCopy(2, false, 'good', () => 0);
    expect(['Nice.', 'Solid.']).toContain(copy.opener);
    expect(copy.clause).toBe('Wrong call [+0], but the right move [+2].');
    expect(copy.lookCloser).toBeNull();
  });

  it('3-point bucket: correct guess + good move, no look-closer line', () => {
    const copy = verdictCopy(3, true, 'good', () => 0);
    expect(['Good job!', 'Clean.']).toContain(copy.opener);
    expect(copy.clause).toBe('Right call [+1], right move [+2].');
    expect(copy.lookCloser).toBeNull();
  });

  it('the injected rng selects between the two opener variants deterministically', () => {
    expect(verdictCopy(3, true, 'good', () => 0).opener).toBe('Good job!');
    expect(verdictCopy(3, true, 'good', () => 0.999).opener).toBe('Clean.');
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
      });
      expect(phrase).toContain("won't come back");
      expect(phrase).not.toContain('warm-up');
      expect(phrase).not.toContain('own positions');
    },
  );

  it('a red_herring names itself; a sharp_filler is a tactics puzzle', () => {
    expect(returnPhrase({ source: 'red_herring', is_warmup: false })).toContain('red herring');
    expect(returnPhrase({ source: 'sharp_filler', is_warmup: false })).toContain('tactics puzzle');
  });

  it('an absent is_warmup (pre-fix cached reveal) degrades to the neutral line, not the warm-up claim', () => {
    expect(returnPhrase({ source: 'red_herring' })).not.toContain('warm-up');
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

describe('walkthroughCopy', () => {
  it('step 0 spotlights the verdict bubble and explains the two point sources', () => {
    expect(walkthroughCopy(0, true).spotlightTarget).toBe('verdict');
    expect(walkthroughCopy(0, true).copy).toContain('One point for a correct call');
    expect(walkthroughCopy(0, true).copy).toContain('up to two for the move');
  });

  it('steps 1 and 2 spotlight the line cards: tap highlights, arrows step (phase 222 UAT split)', () => {
    expect(walkthroughCopy(1, true).spotlightTarget).toBe('lines');
    expect(walkthroughCopy(1, true).copy).toContain('Tap a card to highlight');
    expect(walkthroughCopy(2, true).spotlightTarget).toBe('lines');
    expect(walkthroughCopy(2, true).copy).toContain('arrows inside a card');
  });

  it('step 3 spotlights the board for free play with the eval bar', () => {
    expect(walkthroughCopy(3, true).spotlightTarget).toBe('board');
    expect(walkthroughCopy(3, true).copy).toContain('eval bar');
  });

  it('step 4 carries the "understand, don\'t just memorize" line on the line cards', () => {
    expect(walkthroughCopy(4, true).spotlightTarget).toBe('lines');
    expect(walkthroughCopy(4, true).copy).toContain("Don't just memorize the answer");
  });

  // Phase 222 UAT round 4: the cards sit below the board on phones and to
  // its right on desktop — the tap step names both placements.
  it('step 1 covers both the phone (below) and desktop (right) card placement', () => {
    expect(walkthroughCopy(1, true).copy).toContain('The cards below or on the right');
  });

  it('the last step spotlights the action row', () => {
    expect(walkthroughCopy(5, true).spotlightTarget).toBe('actions');
    expect(WALKTHROUGH_STEP_COUNT).toBe(6);
  });

  it('the last step describes Analyze only when the puzzle comes from an own game (UAT: warm-up first reveal)', () => {
    expect(walkthroughCopy(5, true).copy).toMatch(/^Analyze opens the whole game/);
    const warmup = walkthroughCopy(5, false);
    expect(warmup.spotlightTarget).toBe('actions');
    expect(warmup.copy).toMatch(/^Next takes you to the next puzzle/);
    expect(warmup.copy).toContain('Analyze appears once puzzles come from your own games');
  });

  // Phase 222 UAT round 3: the free-play step departs the board, so the
  // action row usually carries Solution by the last step — describe it.
  it('the last step describes Solution only when the board is departed', () => {
    expect(walkthroughCopy(5, true, false).copy).not.toContain('Solution');
    expect(walkthroughCopy(5, true, true).copy).toMatch(/^The Solution button restores the board\. Analyze/);
    expect(walkthroughCopy(5, false, true).copy).toMatch(/^The Solution button restores the board\. Next/);
  });

  it('every walkthrough step, with and without Analyze/Solution, fits the phone copy budget', () => {
    const steps: WalkthroughStep[] = [0, 1, 2, 3, 4, 5];
    for (const step of steps) {
      for (const hasAnalyze of [true, false]) {
        for (const hasSolution of [true, false]) {
          expect(walkthroughCopy(step, hasAnalyze, hasSolution).copy.length).toBeLessThanOrEqual(
            STEPPER_COPY_MAX_CHARS,
          );
        }
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

  it('UAT round 6: a perfect later session with nothing left to ask for (none) stays a one-liner', () => {
    const copy = scoreBubbleCopy({
      ...BASE,
      outcomes: [activeOutcome('2026-09-14')],
      missedCount: 0,
      isFirstCompletedSession: false,
      reminderAsk: 'none',
    });
    expect(copy.lines).toHaveLength(1);
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
