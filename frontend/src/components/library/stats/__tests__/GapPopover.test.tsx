// @vitest-environment jsdom
/** Phase 239 D-00c / D-00d / D-11 / D-14: the gap popover copy on the shared shell, and GapRow. */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { GapCell } from '@/lib/gapBar';
import { GapPopover } from '../GapPopover';
import { GapRow } from '../GapRow';

afterEach(cleanup);

const TRIGGER_ID = 'library-gap-blunder-tc-blitz';
const BASIS = 'Based on your 1,000 analyzed blitz games in the current filters.';

/** Sketch 010 blitz blunder row: you 5.46, opponents 6.12, band -0.31 to 0.25. */
function blunderCell(overrides: Partial<GapCell> = {}): GapCell {
  return {
    delta: -0.6607,
    zoneLo: -0.31,
    zoneHi: 0.25,
    hasZone: true,
    significant: true,
    youRate: 5.4569,
    oppRate: 6.1176,
    ciLow: -1.0028,
    ciHigh: -0.3185,
    pValue: 0.0002,
    youEvents: 1916,
    oppEvents: 1982,
    ...overrides,
  };
}

function openPopover(cell: GapCell): HTMLElement {
  render(
    <GapPopover
      testId={TRIGGER_ID}
      label="Blunders"
      definition="Moves that dropped your expected score by 15+ points"
      unit="per 100 moves"
      noun="blunders"
      basis={BASIS}
      cell={cell}
    />,
  );
  fireEvent.click(screen.getByTestId(TRIGGER_ID));
  const popover = screen.queryByTestId(`${TRIGGER_ID}-popover`);
  expect(popover, 'popover open').not.toBeNull();
  return popover as HTMLElement;
}

describe('GapPopover (D-00c)', () => {
  it('shows every section in order for a zoned, normal cell', () => {
    const text = openPopover(blunderCell()).textContent ?? '';
    const parts = [
      'Blunders: Moves that dropped your expected score by 15+ points. Fewer is better.',
      'You: 5.46 per 100 moves. Opponents: 6.12.',
      'That is 0.66 fewer than the players you faced.',
      'Typical gap for players at your level: 0.31 fewer to 0.25 more. You are better than typical.',
      BASIS,
      '1,916 vs. 1,982 blunders · gap 99% CI −1.00 to −0.32 · p < 0.001',
    ];
    const indexes = parts.map((part) => text.indexOf(part));
    indexes.forEach((index, i) => expect(index, `missing: ${parts[i]}`).toBeGreaterThanOrEqual(0));
    expect([...indexes].sort((a, b) => a - b)).toEqual(indexes);
  });

  it('puts the statistics below a separator in a greyed footer', () => {
    const popover = openPopover(blunderCell());
    expect(popover.querySelector('hr')).not.toBeNull();
    expect(screen.getByTestId(`${TRIGGER_ID}-footer`).className).toContain('text-background/60');
  });

  it('names a worse and a typical verdict', () => {
    expect(openPopover(blunderCell({ delta: 0.5 })).textContent).toContain(
      'You are worse than typical.',
    );
    cleanup();
    expect(openPopover(blunderCell({ delta: 0.1 })).textContent).toContain('You are typical.');
  });

  it('keeps the range but says it could be chance for an out-of-band gap that is not significant', () => {
    const text = openPopover(blunderCell({ significant: false })).textContent ?? '';
    expect(text).toContain('Typical gap for players at your level: 0.31 fewer to 0.25 more.');
    expect(text).toContain('This could be chance, there are not enough games to be sure.');
    expect(text).not.toContain('You are better than typical.');
  });

  it('still calls an in-band gap typical when it is not significant', () => {
    const text = openPopover(blunderCell({ delta: 0.1, significant: false })).textContent ?? '';
    expect(text).toContain('You are typical.');
    expect(text).not.toContain('could be chance');
  });

  it('has no typical-gap line for a zoneless cell', () => {
    const text = openPopover(blunderCell({ hasZone: false })).textContent ?? '';
    expect(text).not.toContain('Typical gap');
    expect(text).not.toContain('You are');
    expect(text).toContain(BASIS);
  });

  it('reads a same gap as the same as the players you faced', () => {
    const text = openPopover(blunderCell({ delta: 0.004 })).textContent ?? '';
    expect(text).toContain('The same as the players you faced.');
    expect(text).not.toContain('That is');
  });

  it('omits the p part of the footer for a null p-value', () => {
    openPopover(blunderCell({ pValue: null }));
    const footer = screen.getByTestId(`${TRIGGER_ID}-footer`).textContent ?? '';
    expect(footer).toContain('gap 99% CI');
    expect(footer).not.toMatch(/\bp [<=]/);
  });

  it('writes a non-tiny p-value to three decimals', () => {
    openPopover(blunderCell({ pValue: 0.0148 }));
    expect(screen.getByTestId(`${TRIGGER_ID}-footer`).textContent).toContain('p = 0.015');
  });

  it.each([
    ['zoned', {}],
    ['not-significant', { significant: false }],
    ['zoneless', { hasZone: false }],
  ])('never says "event" in a %s popover (D-00d)', (_name, overrides) => {
    const popover = openPopover(blunderCell(overrides));
    expect(popover.textContent ?? '').not.toMatch(/\bevents?\b/i);
  });
});

describe('GapRow', () => {
  function renderRow(cell: GapCell, withPopover = true) {
    return render(
      <GapRow
        label="Blunders"
        hint="Moves that dropped your expected score by 15+ points"
        cell={cell}
        testId="row"
        popover={withPopover ? <span data-testid="row-popover-trigger" /> : undefined}
      />,
    );
  }

  it('shows the label, hint, bar and popover trigger', () => {
    renderRow(blunderCell());
    const row = screen.getByTestId('row');
    expect(row.textContent).toContain('Blunders');
    expect(row.textContent).toContain('Moves that dropped your expected score by 15+ points');
    expect(screen.getByTestId('row-bar')).toBeTruthy();
    expect(screen.getByTestId('row-popover-trigger')).toBeTruthy();
  });

  it('never fades a row, also when the gap is not significant (D-14 replaced the D-12 fade)', () => {
    renderRow(blunderCell({ significant: false }));
    expect(screen.getByTestId('row').style.opacity).toBe('');
  });
});
