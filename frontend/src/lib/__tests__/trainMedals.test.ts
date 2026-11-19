import { describe, expect, it } from 'vitest';
import {
  BOARD_LABEL,
  MEDAL_KIND_ORDER,
  groupMedalsByWeek,
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
    expect(tallyAriaLabel({ gold: 3, silver: 1, bronze: 0 }, 'points')).toBe('3 gold, 1 silver Puzzles Points medals');
  });

  it('uses the singular noun for exactly one medal in total', () => {
    expect(tallyAriaLabel({ gold: 1, silver: 0, bronze: 0 }, 'accuracy')).toBe('1 gold Puzzles Accuracy medal');
  });

  it('lists all three types', () => {
    expect(tallyAriaLabel({ gold: 12, silver: 10, bronze: 11 }, 'points')).toBe(
      '12 gold, 10 silver, 11 bronze Puzzles Points medals',
    );
  });
});

describe('BOARD_LABEL', () => {
  it('names all four boards with their mode', () => {
    expect(BOARD_LABEL).toEqual({
      points: 'Puzzles Points',
      accuracy: 'Puzzles Accuracy',
      blunder_check_points: 'Blunder check Points',
      blunder_check_score: 'Blunder check Score %',
    });
  });
});

describe('lastWeekFinishCopy', () => {
  it('words the rank as a plain finish', () => {
    expect(lastWeekFinishCopy(12)).toBe('You: #12');
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
    expect(medalEntryLabel('gold', 'points', true)).toBe('Gold, Puzzles Points (shared)');
    expect(medalEntryLabel('bronze', 'accuracy', false)).toBe('Bronze, Puzzles Accuracy');
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

describe('groupMedalsByWeek', () => {
  const medal = (week_start: string, board: UnclaimedMedal['board']): UnclaimedMedal => ({
    week_start,
    board,
    medal: 'gold',
    value: 1,
    shared: false,
  });

  it('groups by week, newest first, keeping the API board order inside a week', () => {
    const groups = groupMedalsByWeek([
      medal('2026-09-28', 'points'),
      medal('2026-10-05', 'blunder_check_points'),
      medal('2026-09-28', 'blunder_check_score'),
      medal('2026-10-05', 'points'),
    ]);
    expect(groups.map((g) => g.weekStart)).toEqual(['2026-10-05', '2026-09-28']);
    expect(groups[0]!.medals.map((m) => m.board)).toEqual(['blunder_check_points', 'points']);
    expect(groups[1]!.medals.map((m) => m.board)).toEqual(['points', 'blunder_check_score']);
  });

  it('returns no groups for no medals and one group for a single week', () => {
    expect(groupMedalsByWeek([])).toEqual([]);
    expect(groupMedalsByWeek([medal('2026-10-05', 'points'), medal('2026-10-05', 'accuracy')])).toHaveLength(1);
  });
});
