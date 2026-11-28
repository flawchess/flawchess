/**
 * The avatar's "Game move:" line (Phase 264). The table walks the seed's list "Possible
 * Sentences And Their Conditions" (SEED-261126-g8b): rows T1-T6, P1-P6, C1-C14.
 */
import { describe, expect, it } from 'vitest';
import { explainHeadline } from '@/lib/explainBar';
import type { TacticSlotInput } from '@/lib/explainBar';
import {
  MAX_COMMENTED_TACTIC_DEPTH,
  gameBlunderParts,
  gameBlunderSentence,
} from '@/lib/gameBlunderSentence';
import type { GameBlunderInput } from '@/lib/gameBlunderSentence';
import type { BlunderTypeLine } from '@/types/blunderCheck';
import type { FlawMarker } from '@/types/library';

/** A slot by the depth the user sees ("in 2"): the stored depth is 0-based. */
function slot(motif: string, shownDepth: number | null): TacticSlotInput {
  return { motif, depth: shownDepth === null ? null : shownDepth - 1 };
}

function input(overrides: Partial<GameBlunderInput> = {}): GameBlunderInput {
  // Unscored by default: the score part (D-23) has its own describe block below.
  return { allowedTactic: null, missedTactic: null, typeLine: null, facepalmScore: null, ...overrides };
}

function sentenceOf(overrides: Partial<GameBlunderInput>): string | null {
  return gameBlunderSentence(gameBlunderParts(input(overrides)));
}

const ALLOWED_FORK = slot('fork', 2);
const MISSED_FORK = slot('fork', 2);
const ALLOWED_PIN = slot('pin', 3);

describe('gameBlunderSentence: the seed table (AC-1)', () => {
  it.each<[string, Partial<GameBlunderInput>, string | null]>([
    // Tag part.
    ['T1', { allowedTactic: ALLOWED_FORK }, 'Game move: allowed fork in 2.'],
    ['T2', { missedTactic: MISSED_FORK }, 'Game move: missed fork in 2.'],
    ['T3', { missedTactic: MISSED_FORK, allowedTactic: ALLOWED_PIN }, 'Game move: missed fork in 2, allowed pin in 3.'],
    ['T4', { allowedTactic: slot('fork', null) }, 'Game move: allowed fork.'],
    ['T5', { allowedTactic: slot('back-rank-mate', 7) }, 'Game move: allowed checkmate in 7.'],
    ['T6', { allowedTactic: slot('fork', 6) }, null],
    // Type part.
    ['P1', { typeLine: 'allowed_material' }, 'Game move: loses material.'],
    ['P2', { typeLine: 'allowed_mate' }, 'Game move: allows checkmate.'],
    ['P3', { typeLine: 'missed_material' }, 'Game move: missed a chance to win material.'],
    ['P4', { typeLine: 'missed_mate' }, 'Game move: missed checkmate.'],
    ['P5/P6', { typeLine: null }, null],
    // Both parts.
    ['C1', { allowedTactic: ALLOWED_FORK, typeLine: 'allowed_material' }, 'Game move: allowed fork in 2, loses material.'],
    ['C2', { allowedTactic: ALLOWED_FORK, typeLine: 'allowed_mate' }, 'Game move: allowed fork in 2, allows checkmate.'],
    [
      'C3',
      { missedTactic: MISSED_FORK, typeLine: 'missed_material' },
      'Game move: missed fork in 2, missed a chance to win material.',
    ],
    ['C4', { missedTactic: MISSED_FORK, typeLine: 'missed_mate' }, 'Game move: missed fork in 2, missed checkmate.'],
    ['C5', { missedTactic: MISSED_FORK, typeLine: 'allowed_material' }, 'Game move: missed fork in 2, loses material.'],
    [
      'C6',
      { allowedTactic: ALLOWED_FORK, typeLine: 'missed_material' },
      'Game move: allowed fork in 2, missed a chance to win material.',
    ],
    [
      'C7',
      { missedTactic: MISSED_FORK, allowedTactic: ALLOWED_PIN, typeLine: 'allowed_material' },
      'Game move: missed fork in 2, allowed pin in 3, loses material.',
    ],
    // D-17: a checkmate tag suppresses the type part on the same side.
    ['C8', { allowedTactic: slot('mate', 2), typeLine: 'allowed_mate' }, 'Game move: allowed checkmate in 2.'],
    ['C9', { missedTactic: slot('mate', 3), typeLine: 'missed_mate' }, 'Game move: missed checkmate in 3.'],
    ['C10', { allowedTactic: slot('mate', 4), typeLine: 'allowed_material' }, 'Game move: allowed checkmate in 4.'],
    [
      'C10b',
      { missedTactic: slot('mate', 3), typeLine: 'allowed_material' },
      'Game move: missed checkmate in 3, loses material.',
    ],
    ['C11', { allowedTactic: slot('fork', 6), typeLine: 'allowed_material' }, 'Game move: loses material.'],
    ['C12', { allowedTactic: ALLOWED_FORK, typeLine: 'allowed_material' }, 'Game move: allowed fork in 2, loses material.'],
    ['C13', { allowedTactic: ALLOWED_FORK }, 'Game move: allowed fork in 2.'],
    ['C14', {}, null],
  ])('%s', (_row, overrides, expected) => {
    expect(sentenceOf(overrides)).toBe(expected);
  });
});

describe('gameBlunderSentence: a hanging-piece tag covers the material type part (D-21)', () => {
  it.each<[string, Partial<GameBlunderInput>, string]>([
    ['allowed + loses material', { allowedTactic: slot('hanging-piece', 1), typeLine: 'allowed_material' }, 'Game move: allowed hanging-piece in 1.'],
    ['missed + misses material', { missedTactic: slot('hanging-piece', 1), typeLine: 'missed_material' }, 'Game move: missed hanging-piece in 1.'],
    // Mate is new information: kept.
    ['allowed + allows checkmate', { allowedTactic: slot('hanging-piece', 1), typeLine: 'allowed_mate' }, 'Game move: allowed hanging-piece in 1, allows checkmate.'],
    // Sides differ: both shown, as for checkmate (C10b).
    ['missed + loses material', { missedTactic: slot('hanging-piece', 1), typeLine: 'allowed_material' }, 'Game move: missed hanging-piece in 1, loses material.'],
    ['allowed + misses material', { allowedTactic: slot('hanging-piece', 2), typeLine: 'missed_material' }, 'Game move: allowed hanging-piece in 2, missed a chance to win material.'],
    // Another tag on the same side does not cover it.
    ['allowed fork + loses material', { allowedTactic: slot('fork', 2), typeLine: 'allowed_material' }, 'Game move: allowed fork in 2, loses material.'],
  ])('%s', (_name, overrides, expected) => {
    expect(sentenceOf(overrides)).toBe(expected);
  });

  it('a hanging-piece tag dropped by the depth cut covers nothing', () => {
    expect(sentenceOf({ allowedTactic: slot('hanging-piece', 6), typeLine: 'allowed_material' })).toBe(
      'Game move: loses material.',
    );
  });
});

describe('gameBlunderSentence: nothing known and no numbers (AC-2)', () => {
  it('no visible tag and no type line gives no parts at all', () => {
    expect(gameBlunderParts(input())).toEqual([]);
    expect(gameBlunderSentence([])).toBeNull();
  });

  it('the only digits in any sentence are tag depths', () => {
    const typeLines: (BlunderTypeLine | null)[] = [
      null,
      'allowed_material',
      'allowed_mate',
      'missed_material',
      'missed_mate',
    ];
    for (const typeLine of typeLines) {
      // Without a depth there is no digit anywhere, whatever the type part.
      const noDepth = sentenceOf({ allowedTactic: slot('fork', null), missedTactic: slot('pin', null), typeLine });
      expect(noDepth).not.toMatch(/\d/);
      // With depths, removing each "in N" leaves no digit behind.
      const withDepth = sentenceOf({ allowedTactic: ALLOWED_FORK, missedTactic: slot('pin', 4), typeLine });
      expect(withDepth?.replace(/ in \d+/g, '')).not.toMatch(/\d/);
    }
  });
});

describe('gameBlunderSentence: the depth cut (AC-3, D-10)', () => {
  it('keeps a non-mate tag shown as "in 5" and drops "in 6", on both sides', () => {
    expect(MAX_COMMENTED_TACTIC_DEPTH).toBe(5);
    expect(sentenceOf({ allowedTactic: slot('fork', 5) })).toBe('Game move: allowed fork in 5.');
    expect(sentenceOf({ allowedTactic: slot('fork', 6) })).toBeNull();
    expect(sentenceOf({ missedTactic: slot('pin', 5) })).toBe('Game move: missed pin in 5.');
    expect(sentenceOf({ missedTactic: slot('pin', 6) })).toBeNull();
  });

  it('keeps a checkmate tag at any depth', () => {
    expect(sentenceOf({ missedTactic: slot('smothered-mate', 9) })).toBe('Game move: missed checkmate in 9.');
  });

  it('a dropped tag leaves the other tag and the type line in place', () => {
    expect(
      sentenceOf({ allowedTactic: slot('fork', 8), missedTactic: slot('pin', 2), typeLine: 'allowed_material' }),
    ).toBe('Game move: missed pin in 2, loses material.');
  });

  it('a dropped deep tag is not a checkmate, so it does not suppress the type part', () => {
    expect(sentenceOf({ allowedTactic: slot('skewer', 7), typeLine: 'allowed_mate' })).toBe(
      'Game move: allows checkmate.',
    );
  });
});

describe('gameBlunderSentence: the strip is the source of the tag text (AC-4, AC-7)', () => {
  const PLY = 12;

  function marker(missed: TacticSlotInput | null, allowed: TacticSlotInput | null): FlawMarker {
    return {
      ply: PLY,
      severity: 'blunder',
      tags: [],
      is_user: true,
      move_san: 'Nf3',
      allowed_tactic_motif: allowed?.motif ?? null,
      allowed_tactic_confidence: allowed === null ? null : 90,
      allowed_tactic_depth: allowed?.depth ?? null,
      missed_tactic_motif: missed?.motif ?? null,
      missed_tactic_confidence: missed === null ? null : 90,
      missed_tactic_depth: missed?.depth ?? null,
    };
  }

  it.each<[string, TacticSlotInput | null, TacticSlotInput | null]>([
    ['both', slot('discovered-attack', 2), slot('hanging-piece', 1)],
    ['allowed only', null, slot('trapped-piece', 3)],
    ['missed only', slot('capturing-defender', 4), null],
    ['no depth', slot('promotion', null), slot('en-passant', null)],
    ['named mates', slot('anastasia-mate', 3), slot('back-rank-mate', 2)],
  ])('writes each tag exactly as the analysis strip does: %s', (_name, missed, allowed) => {
    const strip = explainHeadline([marker(missed, allowed)], PLY)?.tactics ?? [];
    const parts = gameBlunderParts(input({ missedTactic: missed, allowedTactic: allowed }));
    expect(parts).toEqual(strip.map((tactic) => ({ kind: 'tactic', ...tactic })));
    expect(strip.length).toBeGreaterThan(0);
  });

  it('a family-less motif produces no sentence, like the strip (AC-7)', () => {
    for (const motif of ['self-interference', 'clearance']) {
      expect(sentenceOf({ allowedTactic: slot(motif, 2) })).toBeNull();
      expect(explainHeadline([marker(null, slot(motif, 2))], PLY)?.tactics).toEqual([]);
    }
  });

  it('missed comes first whatever the input order (D-18)', () => {
    const parts = gameBlunderParts(input({ allowedTactic: ALLOWED_PIN, missedTactic: MISSED_FORK }));
    expect(parts.map((part) => (part.kind === 'tactic' ? part.orientation : part.kind))).toEqual(['missed', 'allowed']);
  });
});

describe('gameBlunderSentence: neutral subject (AC-8, D-04 as amended)', () => {
  it('starts with the move when its SAN is known, and never names the fallback then', () => {
    const parts = gameBlunderParts(input({ allowedTactic: ALLOWED_FORK, typeLine: 'allowed_material' }));
    expect(gameBlunderSentence(parts, 'Ne7')).toBe('Ne7: allowed fork in 2, loses material.');
    expect(gameBlunderSentence(parts, null)).toBe('Game move: allowed fork in 2, loses material.');
    expect(gameBlunderSentence([], 'Ne7')).toBeNull();
  });

  it('without a SAN every sentence starts with "Game move:", and none says "your"', () => {
    const typeLines: (BlunderTypeLine | null)[] = [
      null,
      'allowed_material',
      'allowed_mate',
      'missed_material',
      'missed_mate',
    ];
    for (const typeLine of typeLines) {
      const sentence = sentenceOf({ allowedTactic: ALLOWED_FORK, missedTactic: MISSED_FORK, typeLine });
      expect(sentence?.startsWith('Game move: ')).toBe(true);
      expect(sentence?.toLowerCase()).not.toContain('your');
      expect(sentence?.toLowerCase()).not.toContain('facepalm');
    }
  });

});

describe('gameBlunderSentence: the facepalm score part (D-23, D-25, partly reversing D-11)', () => {
  const SCORE = 0.239;

  it.each<[number, string]>([
    [0.239, 'hard to spot (facepalm score 23%)'],
    [0, 'hard to spot (facepalm score 0%)'],
    // The bands follow the floored percent shown next to them, so 0.499 is still "hard".
    [0.499, 'hard to spot (facepalm score 49%)'],
    [0.5, 'fairly easy to spot (facepalm score 50%)'],
    [0.699, 'fairly easy to spot (facepalm score 69%)'],
    [0.7, 'easy to spot (facepalm score 70%)'],
    [1, 'easy to spot (facepalm score 100%)'],
  ])('a scored blunder with no tag and no type part says how hard it was to spot: %s', (facepalmScore, text) => {
    expect(gameBlunderParts(input({ facepalmScore }))).toEqual([{ kind: 'score', text }]);
    expect(sentenceOf({ facepalmScore })).toBe(`Game move: ${text}.`);
  });

  it('drops the band word when the bubble already says how hard it was (blunder check)', () => {
    expect(sentenceOf({ facepalmScore: 0.239, difficultySaid: true })).toBe('Game move: facepalm score 23%.');
    expect(sentenceOf({ facepalmScore: 0.239, difficultySaid: false })).toBe(
      'Game move: hard to spot (facepalm score 23%).',
    );
  });

  it('a tag dropped by the depth cut or a family-less motif leaves the score as the line', () => {
    expect(sentenceOf({ allowedTactic: slot('fork', 6), facepalmScore: SCORE })).toBe(
      'Game move: hard to spot (facepalm score 23%).',
    );
    expect(sentenceOf({ allowedTactic: slot('clearance', 2), facepalmScore: SCORE })).toBe(
      'Game move: hard to spot (facepalm score 23%).',
    );
  });

  it('an unscored blunder with nothing else known still gives no line', () => {
    expect(gameBlunderParts(input({ facepalmScore: null }))).toEqual([]);
  });

  it.each<[string, Partial<GameBlunderInput>, string]>([
    ['tag only', { allowedTactic: ALLOWED_FORK }, 'Game move: allowed fork in 2. Hard to spot (facepalm score 23%).'],
    ['type only', { typeLine: 'missed_material' }, 'Game move: missed a chance to win material. Hard to spot (facepalm score 23%).'],
    [
      'tag and type',
      { missedTactic: MISSED_FORK, allowedTactic: ALLOWED_PIN, typeLine: 'allowed_material' },
      'Game move: missed fork in 2, allowed pin in 3, loses material. Hard to spot (facepalm score 23%).',
    ],
    ['checkmate tag covering the type', { allowedTactic: slot('mate', 2), typeLine: 'allowed_mate' }, 'Game move: allowed checkmate in 2. Hard to spot (facepalm score 23%).'],
  ])('after a tag or a type part the score is its own sentence, always last (D-25): %s', (_name, overrides, expected) => {
    expect(sentenceOf({ ...overrides, facepalmScore: SCORE })).toBe(expected);
  });

  it('the band word is dropped after a tag or type part too, and the sentence is capitalized', () => {
    expect(sentenceOf({ typeLine: 'allowed_material', facepalmScore: SCORE, difficultySaid: true })).toBe(
      'Game move: loses material. Facepalm score 23%.',
    );
    expect(sentenceOf({ typeLine: 'allowed_material', facepalmScore: 0.84 })).toBe(
      'Game move: loses material. Easy to spot (facepalm score 84%).',
    );
  });

  it.each<[string, Partial<GameBlunderInput>]>([
    ['tag only', { allowedTactic: ALLOWED_FORK }],
    ['type only', { typeLine: 'missed_material' }],
    ['tag and type', { missedTactic: MISSED_FORK, allowedTactic: ALLOWED_PIN, typeLine: 'allowed_material' }],
    ['checkmate tag covering the type', { allowedTactic: slot('mate', 2), typeLine: 'allowed_mate' }],
    ['hanging piece covering the type', { allowedTactic: slot('hanging-piece', 1), typeLine: 'allowed_material' }],
  ])('the score never changes the tag or type parts (AC-4): %s', (_name, overrides) => {
    for (const facepalmScore of [0.05, 0.69, 0.7, 0.99]) {
      for (const difficultySaid of [false, true]) {
        const parts = gameBlunderParts(input({ ...overrides, facepalmScore, difficultySaid }));
        expect(parts.at(-1)?.kind).toBe('score');
        expect(parts.slice(0, -1)).toEqual(gameBlunderParts(input(overrides)));
      }
    }
  });
});
