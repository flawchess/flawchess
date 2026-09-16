/**
 * botLineTrigger.test.ts — Phase 223 Plan 01 Task 2 / Plan 04 Task 2
 * (BOTVOICE-01/02/03, Wave 0). Pure-module test, no jsdom directive.
 *
 * `baseInput` returns a fully-populated `ResolveBotLineInput` with every
 * flag off EXCEPT `botMovesSinceLastLine`, which defaults to
 * `BOT_LINE_MIN_SPACING_MOVES` — "already spaced enough" — mirroring the
 * codebase's own `DRAW_OFFER_COOLDOWN_MOVES` convention ("initialized at
 * the cooldown value so a draw can be offered from the very start of a
 * fresh game"): nothing has fired yet, so nothing needs to wait. Each case
 * overrides exactly the field(s) it needs, including `botMovesSinceLastLine`
 * itself for the pacing-suppression cases below.
 */
import { describe, expect, it } from 'vitest';
import {
  resolveBotLine,
  BOT_LINE_SWING_THRESHOLD_CP,
  BOT_LINE_SWING_CLAMP_CP,
  BOT_LINE_SWING_SPACING_MOVES,
  clampedMoverPovCp,
  isRegretSwing,
  resolveRegretPunishKey,
  BOT_LINE_MIN_SPACING_MOVES,
  BOT_LINE_PAIR_PLY_SPAN,
} from '@/lib/botLineTrigger';
import type { ResolveBotLineInput } from '@/lib/botLineTrigger';
import type { BotLineKey } from '@/lib/botGameCopy';

function baseInput(overrides: Partial<ResolveBotLineInput> = {}): ResolveBotLineInput {
  return {
    gameStartPending: false,
    swingCp: null,
    recoveryCp: null,
    firstCapturePending: false,
    drawOfferLive: false,
    outcomeKind: null,
    botMovesSinceLastLine: BOT_LINE_MIN_SPACING_MOVES,
    ...overrides,
  };
}

describe('resolveBotLine — full precedence chain (BOTVOICE-02/03)', () => {
  it('returns the game-start key when the greeting is pending and nothing else is', () => {
    expect(resolveBotLine(baseInput({ gameStartPending: true }))).toBe('game-start');
  });

  it(
    'returns the first-capture key over game-start when both are pending, proving the ' +
      "resolver's own precedence chain enforces this — not just the caller's game-start latch",
    () => {
      expect(
        resolveBotLine(baseInput({ gameStartPending: true, firstCapturePending: true })),
      ).toBe('first-capture');
    },
  );

  /** One case per reachable trigger, each named for the requirement that
   * wired it. `expected` is the real key `resolveBotLine` must now return —
   * these entries replace the plan-01 "returns null today" table now that
   * every arm is implemented. */
  const REACHABLE_CASES: ReadonlyArray<{
    name: string;
    overrides: Partial<ResolveBotLineInput>;
    expected: BotLineKey;
  }> = [
    {
      name: 'a large positive swing yields the earned tease (BOTVOICE-03, D-03)',
      overrides: { swingCp: 900 },
      expected: 'earned-tease',
    },
    {
      name: 'a live regret latch that RECOVERED yields got-away (Phase 223 UAT)',
      overrides: { recoveryCp: BOT_LINE_SWING_THRESHOLD_CP },
      expected: 'got-away',
    },
    {
      name: 'a live regret latch that did NOT recover yields nice-move (Phase 223 UAT)',
      overrides: { recoveryCp: 0 },
      expected: 'nice-move',
    },
    {
      name: 'a swing magnitude exceeding BOT_LINE_SWING_THRESHOLD_CP yields the earned tease (BOTVOICE-03)',
      overrides: { swingCp: BOT_LINE_SWING_THRESHOLD_CP + 50 },
      expected: 'earned-tease',
    },
    {
      name: 'a swing magnitude exactly AT BOT_LINE_SWING_THRESHOLD yields the earned tease ("at or beyond")',
      overrides: { swingCp: BOT_LINE_SWING_THRESHOLD_CP },
      expected: 'earned-tease',
    },
    {
      name: 'a pending first capture yields the first-capture key (BOTVOICE-02)',
      overrides: { firstCapturePending: true },
      expected: 'first-capture',
    },
    {
      name: "the bot's own live outgoing draw offer yields the draw-offer key (BOTVOICE-02, D-12)",
      overrides: { drawOfferLive: true },
      expected: 'draw-offer',
    },
    {
      name: 'a win outcome yields the bot-won key (BOTVOICE-02)',
      overrides: { outcomeKind: 'win' },
      expected: 'bot-won',
    },
    {
      name: 'a loss outcome yields the bot-lost key (BOTVOICE-02)',
      overrides: { outcomeKind: 'loss' },
      expected: 'bot-lost',
    },
    {
      name: 'a draw outcome yields the game-drawn key (BOTVOICE-02)',
      overrides: { outcomeKind: 'draw' },
      expected: 'game-drawn',
    },
  ];

  it.each(REACHABLE_CASES)('$name', ({ overrides, expected }) => {
    expect(resolveBotLine(baseInput(overrides))).toBe(expected);
  });

  it('returns null for the fully-default input (no trigger pending at all)', () => {
    expect(resolveBotLine(baseInput())).toBeNull();
  });
});

describe('resolveBotLine — swing arm edge cases (BOTVOICE-03, D-01/D-04)', () => {
  it('yields no swing key for a null delta, and falls through to a lower-priority arm', () => {
    // The book window, a failed grade, an aborted turn, or a resumed game's
    // first reply all surface as `swingCp: null` — never treated as a
    // swing, whatever the other fields say.
    expect(resolveBotLine(baseInput({ swingCp: null }))).toBeNull();
    expect(
      resolveBotLine(baseInput({ swingCp: null, firstCapturePending: true })),
    ).toBe('first-capture');
  });

  it('yields no swing key for a delta strictly inside the threshold, and falls through', () => {
    const smallDelta = BOT_LINE_SWING_THRESHOLD_CP - 1;
    expect(resolveBotLine(baseInput({ swingCp: smallDelta }))).toBeNull();
    expect(resolveBotLine(baseInput({ swingCp: -smallDelta }))).toBeNull();
    expect(
      resolveBotLine(baseInput({ swingCp: smallDelta, gameStartPending: true })),
    ).toBe('game-start');
  });

  it(
    'a swing AGAINST the bot never speaks from this resolver — it latches instead ' +
      '(Phase 223 UAT: the bot must not announce its own blunder before the player takes it)',
    () => {
      expect(resolveBotLine(baseInput({ swingCp: -900 }))).toBeNull();
      // ...and it still lets a lower-priority arm through, so latching costs
      // the turn nothing.
      expect(resolveBotLine(baseInput({ swingCp: -900, firstCapturePending: true }))).toBe(
        'first-capture',
      );
      expect(isRegretSwing(-900)).toBe(true);
      expect(isRegretSwing(-BOT_LINE_SWING_THRESHOLD_CP)).toBe(true);
      expect(isRegretSwing(-BOT_LINE_SWING_THRESHOLD_CP + 1)).toBe(false);
      expect(isRegretSwing(900)).toBe(false);
      expect(isRegretSwing(null)).toBe(false);
    },
  );

  it(
    'an Attacker persona sacrifice — a flat delta despite the bot being down material — ' +
      'yields no key at all (D-01: the signal is the score, never the captured material)',
    () => {
      expect(resolveBotLine(baseInput({ swingCp: 0 }))).toBeNull();
    },
  );

  it('resolves a live regret latch ahead of a fresh swing in the other direction', () => {
    // The latch is consumed on this same grade by the caller, so it must
    // always win: the bot's own outstanding blunder is the story.
    expect(resolveBotLine(baseInput({ swingCp: 900, recoveryCp: 0 }))).toBe('nice-move');
    expect(
      resolveBotLine(baseInput({ swingCp: 900, recoveryCp: BOT_LINE_SWING_THRESHOLD_CP })),
    ).toBe('got-away');
  });

  it('never claims got-away while the recovery is short of a full threshold', () => {
    // The user's own constraint: a bot that leaves the same piece hanging a
    // second move has not escaped anything.
    expect(
      resolveBotLine(baseInput({ recoveryCp: BOT_LINE_SWING_THRESHOLD_CP - 1 })),
    ).toBe('nice-move');
    expect(resolveBotLine(baseInput({ recoveryCp: -500 }))).toBe('nice-move');
  });
});

describe('resolveRegretPunishKey — the one line that fires on the player\'s move', () => {
  it('owns up when the player captures while a blunder is outstanding', () => {
    expect(resolveRegretPunishKey(true, true)).toBe('punished-mistake');
  });

  it('says nothing without a live latch, or without a capture', () => {
    expect(resolveRegretPunishKey(false, true)).toBeNull();
    expect(resolveRegretPunishKey(true, false)).toBeNull();
    expect(resolveRegretPunishKey(false, false)).toBeNull();
  });
});

describe('resolveBotLine — pacing (Claude Discretion: BOT_LINE_MIN_SPACING_MOVES)', () => {
  it('paces a swing on its OWN shorter gate, not the mood gate', () => {
    // The regression this split fixes: a throwaway 'first-capture' used to
    // reset the shared counter and swallow a real blunder two moves later.
    expect(
      resolveBotLine(
        baseInput({ swingCp: 900, botMovesSinceLastLine: BOT_LINE_SWING_SPACING_MOVES }),
      ),
    ).toBe('earned-tease');
    expect(
      resolveBotLine(
        baseInput({ swingCp: 900, botMovesSinceLastLine: BOT_LINE_SWING_SPACING_MOVES - 1 }),
      ),
    ).toBeNull();
    // A mood line at that same count is still suppressed, since its own gate
    // is the wider one.
    expect(
      resolveBotLine(
        baseInput({
          firstCapturePending: true,
          botMovesSinceLastLine: BOT_LINE_MIN_SPACING_MOVES - 1,
        }),
      ),
    ).toBeNull();
  });

  it('never paces the settle of a live regret latch (223-REVIEW CR-01)', () => {
    // The hook clears the latch on this grade either way, so a paced settle
    // was a dropped acknowledgement, not a delayed one.
    expect(
      resolveBotLine(
        baseInput({ recoveryCp: BOT_LINE_SWING_THRESHOLD_CP, botMovesSinceLastLine: 0 }),
      ),
    ).toBe('got-away');
    expect(resolveBotLine(baseInput({ recoveryCp: 0, botMovesSinceLastLine: 0 }))).toBe(
      'nice-move',
    );
  });

  it('suppresses a non-terminal key when fewer bot moves have passed since the last line', () => {
    expect(
      resolveBotLine(
        baseInput({ swingCp: 900, botMovesSinceLastLine: BOT_LINE_SWING_SPACING_MOVES - 1 }),
      ),
    ).toBeNull();
    expect(
      resolveBotLine(
        baseInput({
          firstCapturePending: true,
          botMovesSinceLastLine: BOT_LINE_MIN_SPACING_MOVES - 1,
        }),
      ),
    ).toBeNull();
    expect(
      resolveBotLine(
        baseInput({ gameStartPending: true, botMovesSinceLastLine: BOT_LINE_MIN_SPACING_MOVES - 1 }),
      ),
    ).toBeNull();
  });

  it('does NOT suppress the terminal arm even when the pacing count is zero', () => {
    expect(
      resolveBotLine(baseInput({ outcomeKind: 'win', botMovesSinceLastLine: 0 })),
    ).toBe('bot-won');
  });

  it('does NOT suppress the draw-offer arm even when the pacing count is zero', () => {
    expect(
      resolveBotLine(baseInput({ drawOfferLive: true, botMovesSinceLastLine: 0 })),
    ).toBe('draw-offer');
  });
});

describe('botLineTrigger — named constants', () => {
  it('exports BOT_LINE_SWING_THRESHOLD_CP, BOT_LINE_SWING_CLAMP_CP, BOT_LINE_MIN_SPACING_MOVES, BOT_LINE_PAIR_PLY_SPAN as numbers', () => {
    expect(typeof BOT_LINE_SWING_THRESHOLD_CP).toBe('number');
    expect(typeof BOT_LINE_SWING_CLAMP_CP).toBe('number');
    expect(typeof BOT_LINE_MIN_SPACING_MOVES).toBe('number');
    expect(typeof BOT_LINE_PAIR_PLY_SPAN).toBe('number');
  });
});

describe('clampedMoverPovCp — the swing signal the resolver takes deltas of', () => {
  it('reports a white-POV eval from the mover\'s own point of view', () => {
    expect(clampedMoverPovCp(120, null, 'white')).toBe(120);
    expect(clampedMoverPovCp(120, null, 'black')).toBe(-120);
  });

  it('clamps both directions, so a decided game stops producing swings', () => {
    // The whole point of the clamp (and of leaving the expected-score
    // sigmoid behind): +1400 and +2500 are the same value, so taking a
    // further rook when already winning is a delta of zero rather than
    // another earned tease.
    const far = clampedMoverPovCp(2500, null, 'white');
    const farther = clampedMoverPovCp(1400, null, 'white');
    expect(far).toBe(BOT_LINE_SWING_CLAMP_CP);
    expect(far - farther).toBe(0);
    expect(clampedMoverPovCp(-2500, null, 'white')).toBe(-BOT_LINE_SWING_CLAMP_CP);
  });

  it('maps a mate score to the clamp, mate-before-cp, from the mover\'s POV', () => {
    expect(clampedMoverPovCp(50, 3, 'white')).toBe(BOT_LINE_SWING_CLAMP_CP);
    expect(clampedMoverPovCp(50, 3, 'black')).toBe(-BOT_LINE_SWING_CLAMP_CP);
    expect(clampedMoverPovCp(50, -3, 'white')).toBe(-BOT_LINE_SWING_CLAMP_CP);
  });

  it('treats a missing eval as dead level, matching evalToExpectedScore\'s own fallback', () => {
    expect(clampedMoverPovCp(null, null, 'white')).toBe(0);
    // `Object.is(-0, 0)` is false, so compare the value, not its sign bit:
    // a black-POV zero is `-0` and that is still dead level.
    expect(clampedMoverPovCp(null, 0, 'black')).toBeCloseTo(0);
  });

  it('crosses the threshold for a piece-sized swing that the old sigmoid could not see', () => {
    // The shipped regression, in one assertion: in a decided position
    // (+600 -> +900 for the bot) the expected-score delta is ~0.06, well
    // inside the old 0.20 threshold, while the cp delta clears 150.
    const before = clampedMoverPovCp(600, null, 'white');
    const after = clampedMoverPovCp(900, null, 'white');
    expect(Math.abs(after - before)).toBeGreaterThanOrEqual(BOT_LINE_SWING_THRESHOLD_CP);
    expect(resolveBotLine(baseInput({ swingCp: after - before }))).toBe('earned-tease');
  });
});
