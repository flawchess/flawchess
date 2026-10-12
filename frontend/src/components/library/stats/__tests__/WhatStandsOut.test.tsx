// @vitest-environment jsdom
/**
 * Phase 239 D-00g, D-12, D-13: the What stands out card ranks only the 10 context tags,
 * never blunder or mistake, and never a low-sample row.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { WhatStandsOut } from '../WhatStandsOut';
import { RAPID_ENTRY, SKETCH_RAPID_ENTRY, makeTcEntry } from './flawStatsFixtures';

afterEach(cleanup);

const LOW_SAMPLE_EVENTS = 15;

function text(testId: string): string {
  return screen.getByTestId(testId).textContent ?? '';
}

function itemTestIds(listTestId: string): string[] {
  const list = screen.getByTestId(listTestId);
  return Array.from(list.querySelectorAll('li')).map((li) => li.getAttribute('data-testid') ?? '');
}

describe('WhatStandsOut ranking', () => {
  it('lists at most 3 strengths and 3 weaknesses sorted by band-width distance', () => {
    render(<WhatStandsOut tcStats={SKETCH_RAPID_ENTRY} />);
    expect(itemTestIds('what-stands-out-strengths')).toEqual([
      'standout-hasty',
      'standout-opening',
      'standout-middlegame',
    ]);
    // reversed (0.13 band widths) is the fourth weakness and is cut.
    expect(itemTestIds('what-stands-out-weaknesses')).toEqual([
      'standout-low-clock',
      'standout-squandered',
      'standout-unrushed',
    ]);
  });

  it('ranks hasty first among the strengths and shows its gap in words', () => {
    render(<WhatStandsOut tcStats={SKETCH_RAPID_ENTRY} />);
    expect(text('standout-hasty-words')).toBe('2.1 fewer');
    expect(text('standout-hasty')).toContain('Hasty');
    expect(text('standout-hasty')).toContain('Flaws played fast while you still had time');
  });

  it('names the typical rows in card order on one Typical line', () => {
    render(<WhatStandsOut tcStats={SKETCH_RAPID_ENTRY} />);
    expect(text('what-stands-out-typical')).toBe('Typical: Endgame, Miss, Lucky.');
  });

  it('puts a Search popover with the standout testid on each item', () => {
    render(<WhatStandsOut tcStats={SKETCH_RAPID_ENTRY} />);
    expect(screen.getByTestId('gap-popover-standout-hasty-tc-rapid')).not.toBeNull();
    expect(screen.getByTestId('gap-popover-standout-low-clock-tc-rapid')).not.toBeNull();
  });

  it('says flaws in the popover, never events (D-00d)', () => {
    render(<WhatStandsOut tcStats={SKETCH_RAPID_ENTRY} />);
    fireEvent.click(screen.getByTestId('gap-popover-standout-hasty-tc-rapid'));
    const popover = text('gap-popover-standout-hasty-tc-rapid-popover');
    expect(popover).toContain('500 vs. 500 hasty flaws');
    expect(popover).not.toMatch(/\bevents?\b/i);
  });
});

describe('WhatStandsOut exclusions', () => {
  it('never lists blunder or mistake, even with a huge gap (D-13)', () => {
    const entry = makeTcEntry('rapid', {
      analyzedN: 1841,
      blunder: { delta: -4, zone_lo: -0.31, zone_hi: 0.25 },
      mistake: { delta: 4, zone_lo: -0.23, zone_hi: 0.2 },
    });
    render(<WhatStandsOut tcStats={entry} />);
    const card = text('what-stands-out');
    expect(card).not.toMatch(/blunder/i);
    expect(card).not.toMatch(/mistake/i);
    expect(screen.queryByTestId('standout-blunder')).toBeNull();
    expect(screen.queryByTestId('standout-mistake')).toBeNull();
  });

  it('drops a low-sample row from both lists and from the Typical line (D-12, D-13)', () => {
    const entry = makeTcEntry('rapid', {
      analyzedN: 1841,
      overrides: {
        // Huge strength, but only 30 flaws (you + opponents): must not qualify anywhere.
        hasty: {
          delta: -3,
          zone_lo: -0.28,
          zone_hi: 0.18,
          low_sample: true,
          player_events: LOW_SAMPLE_EVENTS,
          opp_events: LOW_SAMPLE_EVENTS,
        },
        // Inside its band but low-sample: not listed as typical either.
        miss: { delta: 0, low_sample: true, player_events: LOW_SAMPLE_EVENTS, opp_events: LOW_SAMPLE_EVENTS },
      },
    });
    render(<WhatStandsOut tcStats={entry} />);
    expect(screen.queryByTestId('standout-hasty')).toBeNull();
    expect(text('what-stands-out-typical')).not.toContain('Hasty');
    expect(text('what-stands-out-typical')).not.toContain('Miss');
  });

  it('drops a zoneless row (no band, no verdict)', () => {
    const entry = makeTcEntry('rapid', {
      analyzedN: 1841,
      overrides: { lucky: { delta: -2, has_zone: false, zone_lo: 0, zone_hi: 0 } },
    });
    render(<WhatStandsOut tcStats={entry} />);
    expect(screen.queryByTestId('standout-lucky')).toBeNull();
    expect(text('what-stands-out-typical')).not.toContain('Lucky');
  });

  it('drops a row with no flaws on either side', () => {
    const entry = makeTcEntry('rapid', {
      analyzedN: 1841,
      overrides: { reversed: { delta: null, player_rate: null, opp_rate: null } },
    });
    render(<WhatStandsOut tcStats={entry} />);
    expect(text('what-stands-out-typical')).not.toContain('Reversed');
  });
});

describe('WhatStandsOut empty sides', () => {
  it('reads "Nothing outside the typical range." on an empty side and omits an empty Typical line', () => {
    // RAPID_ENTRY's 10 context rows all sit inside the default band, so both sides are empty.
    render(<WhatStandsOut tcStats={RAPID_ENTRY} />);
    expect(text('what-stands-out-strengths')).toContain('Nothing outside the typical range.');
    expect(text('what-stands-out-weaknesses')).toContain('Nothing outside the typical range.');
    expect(text('what-stands-out-typical')).toBe(
      'Typical: Low-clock, Hasty, Unrushed, Opening, Middlegame, Endgame, Miss, Lucky, Reversed, Squandered.',
    );
  });

  it('omits the Typical line when no row is typical', () => {
    const allWorse = Object.fromEntries(
      (
        [
          'low_clock',
          'hasty',
          'unrushed',
          'opening',
          'middlegame',
          'endgame_phase',
          'miss',
          'lucky',
          'reversed',
          'squandered',
        ] as const
      ).map((tag) => [tag, { delta: 1 }]),
    );
    render(<WhatStandsOut tcStats={makeTcEntry('rapid', { analyzedN: 1841, overrides: allWorse })} />);
    expect(screen.queryByTestId('what-stands-out-typical')).toBeNull();
    expect(text('what-stands-out-strengths')).toContain('Nothing outside the typical range.');
  });
});
