// @vitest-environment jsdom
/**
 * Phase 239 D-00f, D-00j, D-14: the four context-tag cards.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ContextTagCards } from '../ContextTagCards';
import { RAPID_ENTRY, SKETCH_RAPID_ENTRY, makeTcEntry } from './flawStatsFixtures';

afterEach(cleanup);

const FEW_EVENTS = 15;

function text(testId: string): string {
  return screen.getByTestId(testId).textContent ?? '';
}

function rowIds(cardTestId: string): string[] {
  const card = screen.getByTestId(cardTestId);
  return Array.from(card.querySelectorAll('[data-testid^="context-row-"]'))
    .map((el) => el.getAttribute('data-testid') ?? '')
    .filter((id) => !id.endsWith('-bar') && !id.includes('-bar-'));
}

describe('ContextTagCards structure', () => {
  it('renders the four cards in order with their subtitles', () => {
    render(<ContextTagCards tcStats={SKETCH_RAPID_ENTRY} />);
    const cards = screen.getByTestId('context-tag-cards').children;
    expect(Array.from(cards).map((c) => c.getAttribute('data-testid'))).toEqual([
      'context-card-phase',
      'context-card-clock',
      'context-card-lost-advantages',
      'context-card-opponent-errors',
    ]);
    expect(text('context-card-clock')).toContain('how much time you had');
    expect(text('context-card-phase')).toContain('where the flaw happened');
    expect(text('context-card-opponent-errors')).toContain('chances you missed or got');
    expect(text('context-card-lost-advantages')).toContain('what the flaw cost');
  });

  it('lists the rows of each card in order and has no combo row', () => {
    render(<ContextTagCards tcStats={SKETCH_RAPID_ENTRY} />);
    expect(rowIds('context-card-clock')).toEqual([
      'context-row-unrushed',
      'context-row-hasty',
      'context-row-low-clock',
    ]);
    expect(rowIds('context-card-phase')).toEqual([
      'context-row-opening',
      'context-row-middlegame',
      'context-row-endgame-phase',
    ]);
    expect(rowIds('context-card-opponent-errors')).toEqual([
      'context-row-miss',
      'context-row-lucky',
    ]);
    expect(rowIds('context-card-lost-advantages')).toEqual([
      'context-row-reversed',
      'context-row-squandered',
    ]);
    expect(screen.queryByText(/hasty miss/i)).toBeNull();
    expect(screen.queryByText(/low-clock miss/i)).toBeNull();
  });

  it('shows each row with its unchanged name, hint and gap words', () => {
    render(<ContextTagCards tcStats={SKETCH_RAPID_ENTRY} />);
    const row = text('context-row-hasty');
    expect(row).toContain('Hasty');
    expect(row).toContain('Flaws played fast while you still had time');
    expect(text('context-row-hasty-bar-words')).toBe('2.1 fewer');
    expect(text('context-row-unrushed-bar-words')).toBe('0.50 more');
    expect(text('context-row-endgame-phase')).toContain('Endgame');
  });

  it('puts the better / worse caption at the bottom of each card', () => {
    render(<ContextTagCards tcStats={SKETCH_RAPID_ENTRY} />);
    for (const key of ['clock', 'phase', 'opponent-errors', 'lost-advantages']) {
      const axis = screen.getByTestId(`context-card-${key}-axis`);
      expect(Array.from(axis.children).map((c) => c.textContent)).toEqual([
        'better',
        'worse',
      ]);
    }
  });

  it('has no blunder or mistake row (they live in the tiles)', () => {
    render(<ContextTagCards tcStats={SKETCH_RAPID_ENTRY} />);
    expect(screen.queryByTestId('context-row-blunder')).toBeNull();
    expect(screen.queryByTestId('context-row-mistake')).toBeNull();
  });
});

describe('ContextTagCards popovers', () => {
  it('puts a per-TC Search popover on every row', () => {
    render(<ContextTagCards tcStats={RAPID_ENTRY} />);
    expect(screen.getByTestId('gap-popover-low-clock-tc-rapid')).not.toBeNull();
    expect(screen.getByTestId('gap-popover-endgame-phase-tc-rapid')).not.toBeNull();
    expect(screen.getByTestId('gap-popover-squandered-tc-rapid')).not.toBeNull();
  });

  it('says flaws with the TC basis in the popover, never events (D-00d)', () => {
    render(<ContextTagCards tcStats={SKETCH_RAPID_ENTRY} />);
    fireEvent.click(screen.getByTestId('gap-popover-squandered-tc-rapid'));
    const popover = text('gap-popover-squandered-tc-rapid-popover');
    expect(popover).toContain('Based on your 1,841 analyzed rapid games in the current filters.');
    expect(popover).toContain('500 vs. 500 squandered wins');
    expect(popover).not.toMatch(/\bevents?\b/i);
  });

  it('omits the popover and shows "No flaws yet" for a row without a gap', () => {
    const entry = makeTcEntry('rapid', {
      analyzedN: 1841,
      overrides: { reversed: { delta: null, player_rate: null, opp_rate: null } },
    });
    render(<ContextTagCards tcStats={entry} />);
    expect(text('context-row-reversed')).toContain('No flaws yet');
    expect(screen.queryByTestId('gap-popover-reversed-tc-rapid')).toBeNull();
  });
});

describe('ContextTagCards significance gate (D-14)', () => {
  const notSignificantEntry = makeTcEntry('rapid', {
    analyzedN: 1841,
    overrides: {
      hasty: {
        delta: -3,
        zone_lo: -0.23,
        zone_hi: 0.23,
        significant: false,
        player_events: FEW_EVENTS,
        opp_events: FEW_EVENTS,
      },
      // A significant strength next to it: this one gets the verdict colour.
      miss: { delta: -3, zone_lo: -0.11, zone_hi: 0.11 },
    },
  });

  it('shows a blue dot and no verdict colour', () => {
    render(<ContextTagCards tcStats={notSignificantEntry} />);
    const dot = screen.getByTestId('context-row-hasty-bar-dot');
    // A verdict dot would be the success green; a not-significant one is the neutral blue.
    const strengthDot = screen.getByTestId('context-row-miss-bar-dot');
    const typicalDot = screen.getByTestId('context-row-opening-bar-dot');
    expect(dot.style.backgroundColor).not.toBe('');
    expect(dot.style.backgroundColor).not.toBe(strengthDot.style.backgroundColor);
    expect(dot.style.backgroundColor).toBe(typicalDot.style.backgroundColor);
  });
});
