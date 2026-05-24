// @vitest-environment jsdom
/**
 * Phase 94.2 Plan 05: PercentileChip component tests.
 *
 * Updated for the 4-flavor metric-named enum
 * (score-gap | achievable | parity | conversion).
 *
 * Covers:
 *  - Label formatter `Top X%` (rounding, p=0 literal, p=99.9 floor at 1)
 *  - Band-color dispatch (red < 25, neutral 25..75, green > 75)
 *  - Flame tier dispatch (highest tier only — 0 / 1 / 2 / 3)
 *  - Popover body discloses 4 D-4 bullets per flavor — benchmark composition,
 *    recent-games basis, filter independence, per-metric rating-correlation
 *    framing (calibrated per Cohen's d in
 *    reports/benchmarks-gap-metrics-percentile-candidacy.md).
 *  - aria-label + data-testid contract.
 *
 * The Phase 94.1 "minimalism budget" guard (POPOVER_MAX_CHARS) is intentionally
 * removed here: the percentile chip popover is the sanctioned exception to
 * feedback_popover_copy_minimalism (see feedback_percentile_chip_tooltip_disclosure
 * project memory). It MUST disclose all four bullets; a length cap would re-trip
 * the prior under-disclosure bug D-4 was filed to fix.
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

import { PercentileChip, type PercentileChipFlavor } from '../PercentileChip';
import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';

const TID = 'test-pctl-chip';

function renderChip(percentile: number, flavor: PercentileChipFlavor = 'score-gap') {
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
  // jsdom normalizes `oklch(0.50 ...)` to `oklch(0.5 ...)`, so we extract the
  // numeric triplet and compare against the theme constant's parsed triplet.
  function parseOklch(s: string): readonly [number, number, number] | null {
    const m = s.match(/oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)/);
    if (!m) return null;
    return [Number(m[1]), Number(m[2]), Number(m[3])] as const;
  }

  it('routes red band background for percentile=10', () => {
    renderChip(10);
    const chip = screen.getByTestId(TID);
    expect(parseOklch(chip.style.backgroundColor)).toEqual(parseOklch(ZONE_DANGER));
  });

  it('routes blue neutral band for percentile=50', () => {
    renderChip(50);
    const chip = screen.getByTestId(TID);
    expect(parseOklch(chip.style.backgroundColor)).toEqual(parseOklch(GAUGE_NEUTRAL));
  });

  it('routes green band for percentile=85', () => {
    renderChip(85);
    const chip = screen.getByTestId(TID);
    expect(parseOklch(chip.style.backgroundColor)).toEqual(parseOklch(ZONE_SUCCESS));
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

// ── Phase 94.2 Plan 05 (D-4): popover body discloses 4 bullets per metric ─────
//
// The four content blocks every flavor's popover MUST render:
//   1. Benchmark composition  — "benchmarked Lichess players"
//   2. Recent-games basis     — "most recent 1000 games"
//   3. Filter independence    — "UI filters do not affect"
//   4. Per-metric rating-correlation framing — differs per flavor (see below)
//
// Per-metric rating-correlation framing (per Cohen's d from
// reports/benchmarks-gap-metrics-percentile-candidacy.md):
//   score-gap   (d=0.19) — "mostly independent of rating" (rating-invariant)
//   achievable  (d=0.32) — "mildly correlates with rating"
//   parity      (d=0.30) — "mildly correlates with rating"
//   conversion  (d=1.37) — "tracks rating strongly"

const FLAVORS_WITH_SOFT_RATING_NOTE: ReadonlyArray<PercentileChipFlavor> = [
  'achievable',
  'parity',
];

const ALL_FLAVORS: ReadonlyArray<PercentileChipFlavor> = [
  'score-gap',
  'achievable',
  'parity',
  'conversion',
];

describe('PercentileChip — D-4 popover disclosure (Phase 94.2)', () => {
  it.each(ALL_FLAVORS)('flavor=%s discloses benchmark composition, recent-games basis, and filter independence', (flavor) => {
    renderChip(73, flavor);
    fireEvent.click(screen.getByTestId(TID));
    const popover = screen.getByTestId(`${TID}-popover`);
    const body = popover.textContent ?? '';
    expect(body).toMatch(/benchmarked Lichess players/i);
    expect(body).toMatch(/most recent 1000 games/i);
    expect(body).toMatch(/UI filters do not affect/i);
  });

  it('flavor=score-gap notes the metric is rating-invariant (no rating-coupling framing)', () => {
    renderChip(73, 'score-gap');
    fireEvent.click(screen.getByTestId(TID));
    const popover = screen.getByTestId(`${TID}-popover`);
    const body = popover.textContent ?? '';
    // score-gap (d=0.19) should NOT carry the soft "mildly correlates" or the
    // heavy "tracks rating strongly" framing. The rating note is either absent
    // or it explicitly says the metric is rating-invariant.
    expect(body).not.toMatch(/mildly correlates with rating/i);
    expect(body).not.toMatch(/tracks rating strongly/i);
    expect(body).toMatch(/mostly independent of rating|independent of rating/i);
  });

  it.each(FLAVORS_WITH_SOFT_RATING_NOTE)('flavor=%s carries a soft rating-coupling mention', (flavor) => {
    renderChip(73, flavor);
    fireEvent.click(screen.getByTestId(TID));
    const popover = screen.getByTestId(`${TID}-popover`);
    const body = popover.textContent ?? '';
    expect(body).toMatch(/mildly correlates with rating/i);
    // and NOT the heavy framing
    expect(body).not.toMatch(/tracks rating strongly/i);
  });

  it('flavor=conversion carries honest "tracks rating strongly" framing', () => {
    renderChip(73, 'conversion');
    fireEvent.click(screen.getByTestId(TID));
    const popover = screen.getByTestId(`${TID}-popover`);
    const body = popover.textContent ?? '';
    expect(body).toMatch(/tracks rating strongly/i);
    // and NOT the soft mild framing
    expect(body).not.toMatch(/mildly correlates with rating/i);
  });
});
