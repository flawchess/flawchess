// @vitest-environment jsdom
/**
 * Phase 94 Plan 02 Task 2: PercentileChip component tests.
 *
 * Covers:
 *  - Label formatter `Top X%` (rounding, p=0 literal, p=99.9 floor at 1)
 *  - Band-color dispatch (red < 25, neutral 25..75, green > 75)
 *  - Flame tier dispatch (highest tier only — 0 / 1 / 2 / 3)
 *  - Popover open + flavor-routed copy (skill-isolating vs improvement-focus)
 *  - aria-label + data-testid contract
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

import { PercentileChip } from '../PercentileChip';
import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';

const TID = 'test-pctl-chip';

function renderChip(percentile: number, flavor: 'skill-isolating' | 'improvement-focus' = 'skill-isolating') {
  return render(
    <PercentileChip
      percentile={percentile}
      flavor={flavor}
      metricLabel="Endgame Score Gap"
      testId={TID}
    />,
  );
}

describe('PercentileChip', () => {
  // ── Label formatter ──
  it('renders "Top 27%" for percentile=73', () => {
    renderChip(73);
    expect(screen.getByTestId(TID).textContent ?? '').toContain('Top 27%');
  });

  it('renders "Top 50%" for percentile=50 (literal near median per D-07)', () => {
    renderChip(50);
    expect(screen.getByTestId(TID).textContent ?? '').toContain('Top 50%');
  });

  it('renders "Top 100%" for percentile=0 (honest literal lower edge per D-06)', () => {
    renderChip(0);
    expect(screen.getByTestId(TID).textContent ?? '').toContain('Top 100%');
  });

  it('floors at "Top 1%" for percentile=99.9 (no "Top 0%" per Pitfall 7)', () => {
    renderChip(99.9);
    const txt = screen.getByTestId(TID).textContent ?? '';
    expect(txt).toContain('Top 1%');
    expect(txt).not.toContain('Top 0%');
  });

  // ── Band-color dispatch ──
  it('routes red band background for percentile=10', () => {
    renderChip(10);
    const chip = screen.getByTestId(TID);
    expect(chip.style.backgroundColor).toBe(ZONE_DANGER);
  });

  it('routes blue neutral band for percentile=50', () => {
    renderChip(50);
    const chip = screen.getByTestId(TID);
    expect(chip.style.backgroundColor).toBe(GAUGE_NEUTRAL);
  });

  it('routes green band for percentile=85', () => {
    renderChip(85);
    const chip = screen.getByTestId(TID);
    expect(chip.style.backgroundColor).toBe(ZONE_SUCCESS);
  });

  // ── Flame tier dispatch (highest tier only) ──
  it('renders 0 flame icons for percentile=89', () => {
    renderChip(89);
    const chip = screen.getByTestId(TID);
    expect(within(chip).queryAllByTestId(`${TID}-flame`)).toHaveLength(0);
  });

  it('renders 1 flame icon for percentile=90', () => {
    renderChip(90);
    const chip = screen.getByTestId(TID);
    expect(within(chip).queryAllByTestId(`${TID}-flame`)).toHaveLength(1);
  });

  it('renders 2 flame icons for percentile=95', () => {
    renderChip(95);
    const chip = screen.getByTestId(TID);
    expect(within(chip).queryAllByTestId(`${TID}-flame`)).toHaveLength(2);
  });

  it('renders 3 flame icons for percentile=99 (highest tier only — NOT 6 from 1+2+3)', () => {
    renderChip(99);
    const chip = screen.getByTestId(TID);
    expect(within(chip).queryAllByTestId(`${TID}-flame`)).toHaveLength(3);
  });

  // ── Popover flavor routing ──
  it('opens popover with skill-isolating copy when flavor="skill-isolating"', () => {
    renderChip(73, 'skill-isolating');
    // Tap toggles popover on mobile path via onOpenChange — simulate via click.
    fireEvent.click(screen.getByTestId(TID));
    const popover = screen.getByTestId(`${TID}-popover`);
    expect(popover.textContent ?? '').toMatch(/Mostly independent of rating/i);
  });

  it('opens popover with improvement-focus copy when flavor="improvement-focus"', () => {
    renderChip(20, 'improvement-focus');
    fireEvent.click(screen.getByTestId(TID));
    const popover = screen.getByTestId(`${TID}-popover`);
    expect(popover.textContent ?? '').toMatch(/Conversion tracks rating closely/i);
  });

  // ── Accessibility / contract ──
  it('chip trigger has aria-label including metricLabel and the rendered percentile label', () => {
    renderChip(73);
    const chip = screen.getByTestId(TID);
    const aria = chip.getAttribute('aria-label') ?? '';
    expect(aria).toContain('Endgame Score Gap');
    expect(aria).toContain('Top 27%');
  });

  it('chip trigger has the supplied data-testid; popover Content has `${testId}-popover`', () => {
    renderChip(85);
    expect(screen.getByTestId(TID)).toBeTruthy();
    fireEvent.click(screen.getByTestId(TID));
    expect(screen.getByTestId(`${TID}-popover`)).toBeTruthy();
  });
});
