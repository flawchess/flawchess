import { describe, expect, it } from 'vitest';
import {
  BOARD_LABEL,
  MEDAL_KIND_ORDER,
  lastWeekFinishCopy,
  medalDialogTitle,
  medalEntryLabel,
  medalKeys,
  tallyAriaLabel,
  tallyEntries,
  weekOfLabel,
} from '@/lib/trainMedals';
import type { UnclaimedMedal } from '@/types/train';

describe('tallyEntries', () => {
  it('keeps non-zero types in gold, silver, bronze order', () => {
    expect(tallyEntries({ gold: 3, silver: 0, bronze: 1 })).toEqual([
      { kind: 'gold', count: 3 },
      { kind: 'bronze', count: 1 },
    ]);
  });

  it('returns an empty list when every count is zero', () => {
    expect(tallyEntries({ gold: 0, silver: 0, bronze: 0 })).toEqual([]);
  });

  it('keeps the fixed order whatever the counts are', () => {
    expect(tallyEntries({ gold: 1, silver: 5, bronze: 9 }).map((e) => e.kind)).toEqual([
      ...MEDAL_KIND_ORDER,
    ]);
  });
});

describe('tallyAriaLabel', () => {
  it('lists non-zero counts then the board label and a plural noun', () => {
    expect(tallyAriaLabel({ gold: 3, silver: 1, bronze: 0 }, 'points')).toBe('3 gold, 1 silver Points medals');
  });

  it('uses the singular noun for exactly one medal in total', () => {
    expect(tallyAriaLabel({ gold: 1, silver: 0, bronze: 0 }, 'accuracy')).toBe('1 gold Accuracy medal');
  });

  it('lists all three types', () => {
    expect(tallyAriaLabel({ gold: 12, silver: 10, bronze: 11 }, 'points')).toBe(
      '12 gold, 10 silver, 11 bronze Points medals',
    );
  });
});

describe('BOARD_LABEL', () => {
  it('names both boards', () => {
    expect(BOARD_LABEL).toEqual({ points: 'Points', accuracy: 'Accuracy' });
  });
});

describe('lastWeekFinishCopy', () => {
  it('words the rank as a plain finish', () => {
    expect(lastWeekFinishCopy(12)).toBe('You finished #12 last week');
  });
});

describe('medalDialogTitle', () => {
  it('is singular for one medal and counts otherwise', () => {
    expect(medalDialogTitle(1)).toBe('You won a medal!');
    expect(medalDialogTitle(3)).toBe('You won 3 medals!');
  });
});

describe('medalEntryLabel', () => {
  it('names the medal and board, marking a shared medal', () => {
    expect(medalEntryLabel('gold', 'points', true)).toBe('Gold, Points (shared)');
    expect(medalEntryLabel('bronze', 'accuracy', false)).toBe('Bronze, Accuracy');
  });
});

describe('weekOfLabel', () => {
  it('formats the Monday as "Week of Sep 28"', () => {
    expect(weekOfLabel('2026-09-28')).toBe('Week of Sep 28');
  });

  it('does not slip to the Sunday in a western time zone (parseISO, not new Date)', () => {
    const previousTz = process.env.TZ;
    process.env.TZ = 'America/Los_Angeles';
    try {
      // A UTC-midnight parse of '2026-09-28' renders as Sep 27 here.
      expect(weekOfLabel('2026-09-28')).toBe('Week of Sep 28');
    } finally {
      if (previousTz === undefined) delete process.env.TZ;
      else process.env.TZ = previousTz;
    }
  });
});

describe('medalKeys', () => {
  it('maps entries to { week_start, board } in order', () => {
    const medals: UnclaimedMedal[] = [
      { week_start: '2026-09-28', board: 'points', medal: 'gold', value: 412, shared: false },
      { week_start: '2026-09-21', board: 'accuracy', medal: 'silver', value: 87, shared: true },
    ];
    expect(medalKeys(medals)).toEqual([
      { week_start: '2026-09-28', board: 'points' },
      { week_start: '2026-09-21', board: 'accuracy' },
    ]);
  });
});
