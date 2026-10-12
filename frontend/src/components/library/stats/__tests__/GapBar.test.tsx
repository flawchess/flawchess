// @vitest-environment jsdom
/** Phase 239 D-00a / D-00b / D-11 / D-12: the rendered gap bar, words and dot colours. */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import { cellPosition, type GapCell } from '@/lib/gapBar';
import { GapBar, GapGateSlot } from '../GapBar';

afterEach(cleanup);

/** jsdom normalizes color strings (oklch(0.50 ..) -> oklch(0.5 ..)); compare normalized forms. */
function normalized(color: string): string {
  const probe = document.createElement('div');
  probe.style.color = color;
  return probe.style.color;
}

function cell(overrides: Partial<GapCell> = {}): GapCell {
  return {
    delta: -0.66,
    zoneLo: -0.31,
    zoneHi: 0.25,
    hasZone: true,
    lowSample: false,
    youRate: 5.46,
    oppRate: 6.12,
    ciLow: -1.0,
    ciHigh: -0.32,
    pValue: 0.0002,
    youEvents: 1916,
    oppEvents: 1982,
    ...overrides,
  };
}

describe('GapBar', () => {
  it('draws the band, the zero tick at 50% and the dot at the cell position', () => {
    const c = cell();
    render(<GapBar cell={c} testId="bar" />);
    expect(screen.getByTestId('bar-band')).toBeTruthy();
    expect(screen.getByTestId('bar-zero').style.left).toBe('50%');
    expect(screen.getByTestId('bar-dot').style.left).toBe(`${cellPosition(c)}%`);
  });

  it.each([
    ['better', { delta: -0.66 }, ZONE_SUCCESS, true],
    ['worse', { delta: 0.5 }, ZONE_DANGER, true],
    ['typical', { delta: 0.1 }, GAUGE_NEUTRAL, false],
    ['low-sample', { delta: -0.66, lowSample: true }, GAUGE_NEUTRAL, false],
    ['zoneless', { delta: -0.66, hasZone: false }, GAUGE_NEUTRAL, false],
  ] as const)('colours a %s cell', (_name, overrides, dotColor, coloredWords) => {
    render(<GapBar cell={cell(overrides)} testId="bar" />);
    expect(screen.getByTestId('bar-dot').style.backgroundColor).toBe(normalized(dotColor));
    const words = screen.getByTestId('bar-words');
    if (coloredWords) {
      expect(words.style.color).toBe(normalized(dotColor));
      expect(words.className).not.toContain('text-foreground');
    } else {
      expect(words.style.color).toBe('');
      expect(words.className).toContain('text-foreground');
    }
  });

  it('writes the gap in words', () => {
    render(<GapBar cell={cell({ delta: -1.74 })} testId="bar" />);
    expect(screen.getByTestId('bar-words').textContent).toBe('1.7 fewer');
    expect(screen.getByTestId('bar-track').getAttribute('aria-label')).toBe(
      '1.7 fewer flaws than your opponents',
    );
  });

  it('draws no band for a zoneless cell', () => {
    render(<GapBar cell={cell({ hasZone: false })} testId="bar" />);
    expect(screen.queryByTestId('bar-band')).toBeNull();
    expect(screen.getByTestId('bar-dot')).toBeTruthy();
  });

  it('keeps the band for a low-sample cell', () => {
    render(<GapBar cell={cell({ lowSample: true })} testId="bar" />);
    expect(screen.getByTestId('bar-band')).toBeTruthy();
  });

  it('renders "No flaws yet" and no track for a gap-less cell', () => {
    render(<GapBar cell={cell({ delta: null })} testId="bar" />);
    expect(screen.getByTestId('bar-empty').textContent).toBe('No flaws yet');
    expect(screen.queryByTestId('bar-track')).toBeNull();
  });

  it('renders the trailing node after the words', () => {
    render(<GapBar cell={cell()} testId="bar" trailing={<span data-testid="trail" />} />);
    expect(screen.getByTestId('trail')).toBeTruthy();
  });
});

describe('GapGateSlot', () => {
  it('shows the analyzed count against the gate', () => {
    render(<GapGateSlot analyzedN={12} gate={20} testId="gate" />);
    expect(screen.getByTestId('gate').textContent).toBe(
      'Not enough analyzed games yet (12 of 20)',
    );
  });
});
