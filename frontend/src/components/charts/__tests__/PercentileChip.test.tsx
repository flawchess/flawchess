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
//   2. Recent-games basis     — "most recent 1000 rated games"
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
    expect(body).toMatch(/most recent 1000 rated games/i);
    expect(body).toMatch(/opponents of similar strength/i);
    expect(body).toMatch(/UI filters do not affect/i);
    // Paragraph 1 now incorporates metricLabel and a "better than X%" framing.
    expect(body).toMatch(/Your Endgame Score Gap is better than 73% of/i);
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

// ── Phase 94.3: direction inversion + per-TC popover (Plan F) ────────────────
//
// 12 new flavors (3 metric families × 4 TCs) extend the chip surface. The 4
// `net_flag_rate_{tc}` flavors map to `lower_is_better`:
//   - Top X% label uses raw `Math.round(pct)` instead of `Math.round(100 - pct)`.
//   - Band color: green at low pct, red at high pct.
//   - Flame thresholds: p1 / p5 / p10 (instead of p99 / p95 / p90).
//   - Popover prepends "Lower is better — you have fewer net timeouts than
//     X% of {tc} players." line (CONTEXT.md D-3).
// All other 12 flavors (4 originals + 4 time_pressure_score_gap_{tc} + 4
// clock_gap_{tc}) stay `higher_is_better` (regression-covered above).

import { DIRECTION_BY_FLAVOR } from '../PercentileChip';

const PER_TC_FLAVORS: ReadonlyArray<{
  flavor: PercentileChipFlavor;
  tcLabel: string;
  metricLabel: string;
}> = [
  { flavor: 'time_pressure_score_gap_bullet', tcLabel: 'bullet', metricLabel: 'Time Pressure Score Gap (bullet)' },
  { flavor: 'time_pressure_score_gap_blitz', tcLabel: 'blitz', metricLabel: 'Time Pressure Score Gap (blitz)' },
  { flavor: 'time_pressure_score_gap_rapid', tcLabel: 'rapid', metricLabel: 'Time Pressure Score Gap (rapid)' },
  { flavor: 'time_pressure_score_gap_classical', tcLabel: 'classical', metricLabel: 'Time Pressure Score Gap (classical)' },
  { flavor: 'clock_gap_bullet', tcLabel: 'bullet', metricLabel: 'Clock Gap (bullet)' },
  { flavor: 'clock_gap_blitz', tcLabel: 'blitz', metricLabel: 'Clock Gap (blitz)' },
  { flavor: 'clock_gap_rapid', tcLabel: 'rapid', metricLabel: 'Clock Gap (rapid)' },
  { flavor: 'clock_gap_classical', tcLabel: 'classical', metricLabel: 'Clock Gap (classical)' },
  { flavor: 'net_flag_rate_bullet', tcLabel: 'bullet', metricLabel: 'Net Flag Rate (bullet)' },
  { flavor: 'net_flag_rate_blitz', tcLabel: 'blitz', metricLabel: 'Net Flag Rate (blitz)' },
  { flavor: 'net_flag_rate_rapid', tcLabel: 'rapid', metricLabel: 'Net Flag Rate (rapid)' },
  { flavor: 'net_flag_rate_classical', tcLabel: 'classical', metricLabel: 'Net Flag Rate (classical)' },
];

function renderChipFor(percentile: number, flavor: PercentileChipFlavor, metricLabel: string) {
  return render(
    <PercentileChip
      percentile={percentile}
      flavor={flavor}
      metricLabel={metricLabel}
      testId={TID}
    />,
  );
}

function parseOklch(s: string): readonly [number, number, number] | null {
  const m = s.match(/oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)/);
  if (!m) return null;
  return [Number(m[1]), Number(m[2]), Number(m[3])] as const;
}

describe('PercentileChip — direction inversion + per-TC popover (Phase 94.3)', () => {
  // ── Exhaustiveness ──
  it('DIRECTION_BY_FLAVOR has exactly 16 entries', () => {
    expect(Object.keys(DIRECTION_BY_FLAVOR).length).toBe(16);
  });

  it('DIRECTION_BY_FLAVOR maps exactly 4 net_flag_rate_{tc} flavors to lower_is_better', () => {
    const lowerEntries = Object.entries(DIRECTION_BY_FLAVOR).filter(
      ([, dir]) => dir === 'lower_is_better',
    );
    expect(lowerEntries.length).toBe(4);
    const flavors = lowerEntries.map(([f]) => f).sort();
    expect(flavors).toEqual([
      'net_flag_rate_blitz',
      'net_flag_rate_bullet',
      'net_flag_rate_classical',
      'net_flag_rate_rapid',
    ]);
  });

  // ── Direction inversion: Top X% formatter ──
  it('lower_is_better flavor renders "Top 5%" at percentile=5 (not "Top 95%")', () => {
    renderChipFor(5, 'net_flag_rate_bullet', 'Net Flag Rate (bullet)');
    const txt = screen.getByTestId(TID).textContent ?? '';
    expect(txt).toContain('Top 5%');
    expect(txt).not.toContain('Top 95%');
  });

  it('lower_is_better flavor floors at "Top 1%" for percentile=0 (no "Top 0%")', () => {
    renderChipFor(0, 'net_flag_rate_bullet', 'Net Flag Rate (bullet)');
    const txt = screen.getByTestId(TID).textContent ?? '';
    expect(txt).toContain('Top 1%');
    expect(txt).not.toContain('Top 0%');
  });

  // ── Direction inversion: band color ──
  it('lower_is_better flavor band is green (ZONE_SUCCESS) at percentile=5', () => {
    renderChipFor(5, 'net_flag_rate_bullet', 'Net Flag Rate (bullet)');
    const chip = screen.getByTestId(TID);
    expect(parseOklch(chip.style.backgroundColor)).toEqual(parseOklch(ZONE_SUCCESS));
  });

  it('lower_is_better flavor band is red (ZONE_DANGER) at percentile=99', () => {
    renderChipFor(99, 'net_flag_rate_bullet', 'Net Flag Rate (bullet)');
    const chip = screen.getByTestId(TID);
    expect(parseOklch(chip.style.backgroundColor)).toEqual(parseOklch(ZONE_DANGER));
  });

  // ── Direction inversion: flame tiers ──
  it('lower_is_better flavor renders 3 flames at percentile=1 (p1 → tier 3)', () => {
    renderChipFor(1, 'net_flag_rate_bullet', 'Net Flag Rate (bullet)');
    const chip = screen.getByTestId(TID);
    expect(within(chip).queryAllByTestId(`${TID}-flame`)).toHaveLength(3);
  });

  it('lower_is_better flavor renders 2 flames at percentile=5 (p5 → tier 2)', () => {
    renderChipFor(5, 'net_flag_rate_bullet', 'Net Flag Rate (bullet)');
    const chip = screen.getByTestId(TID);
    expect(within(chip).queryAllByTestId(`${TID}-flame`)).toHaveLength(2);
  });

  it('lower_is_better flavor renders 1 flame at percentile=10 (p10 → tier 1)', () => {
    renderChipFor(10, 'net_flag_rate_bullet', 'Net Flag Rate (bullet)');
    const chip = screen.getByTestId(TID);
    expect(within(chip).queryAllByTestId(`${TID}-flame`)).toHaveLength(1);
  });

  it('lower_is_better flavor renders 0 flames at percentile=50', () => {
    renderChipFor(50, 'net_flag_rate_bullet', 'Net Flag Rate (bullet)');
    const chip = screen.getByTestId(TID);
    expect(within(chip).queryAllByTestId(`${TID}-flame`)).toHaveLength(0);
  });

  // ── Higher-is-better regression for new per-TC variants ──
  it('higher_is_better per-TC flavor renders "Top 27%" at percentile=73 (clock_gap_blitz)', () => {
    renderChipFor(73, 'clock_gap_blitz', 'Clock Gap (blitz)');
    const txt = screen.getByTestId(TID).textContent ?? '';
    expect(txt).toContain('Top 27%');
  });

  it('higher_is_better per-TC flavor renders 3 flames at percentile=99 (time_pressure_score_gap_bullet)', () => {
    renderChipFor(99, 'time_pressure_score_gap_bullet', 'Time Pressure Score Gap (bullet)');
    const chip = screen.getByTestId(TID);
    expect(within(chip).queryAllByTestId(`${TID}-flame`)).toHaveLength(3);
  });

  // ── D-3: Net Flag "Lower is better" prepended popover line ──
  it.each(['bullet', 'blitz', 'rapid', 'classical'] as const)(
    'Net Flag chip prepends "Lower is better" line for tc=%s with the correct TC token',
    (tc) => {
      const flavor = `net_flag_rate_${tc}` as PercentileChipFlavor;
      renderChipFor(20, flavor, `Net Flag Rate (${tc})`);
      fireEvent.click(screen.getByTestId(TID));
      const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
      // Phase 94.3 CR-01: percentile=20 for lower_is_better means user beats
      // cohortOutranked = 100 - 20 = 80% of cohort. Both this line and bullet-1
      // now share that single source of truth (previously bullet-1 said "5%"
      // here while this line said "80%" — contradictory).
      expect(body).toContain(`Lower is better, you have fewer net timeouts than 80% of ${tc} players.`);
    },
  );

  it('non-Net-Flag chip does NOT include the "Lower is better" line', () => {
    renderChipFor(73, 'clock_gap_bullet', 'Clock Gap (bullet)');
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).not.toMatch(/Lower is better/i);
  });

  it('original 4 flavors do NOT include the "Lower is better" line (regression)', () => {
    renderChipFor(73, 'score-gap', 'Endgame Score Gap');
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).not.toMatch(/Lower is better/i);
  });

  // ── D-13: TC-scoped bullets 1 and 2 for per-TC flavors ──
  it.each(PER_TC_FLAVORS)(
    'per-TC flavor=$flavor: bullet 1 mentions the TC name in "in $tcLabel, all ratings"',
    ({ flavor, tcLabel, metricLabel }) => {
      renderChipFor(40, flavor, metricLabel);
      fireEvent.click(screen.getByTestId(TID));
      const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
      // For lower_is_better the leading prepended line uses TC too; we still
      // expect "in {tc}, all ratings" to appear in bullet 1 verbatim.
      expect(body).toContain(`in ${tcLabel}, all ratings`);
    },
  );

  it.each(PER_TC_FLAVORS)(
    'per-TC flavor=$flavor: bullet 2 mentions "most recent 1000 rated games in $tcLabel"',
    ({ flavor, tcLabel, metricLabel }) => {
      renderChipFor(40, flavor, metricLabel);
      fireEvent.click(screen.getByTestId(TID));
      const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
      expect(body).toContain(`most recent 1000 rated games in ${tcLabel}`);
    },
  );

  it('original flavor (score-gap) bullet 2 keeps the per-time-control wording (regression)', () => {
    renderChipFor(73, 'score-gap', 'Endgame Score Gap');
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    // Regression: original copy says "per time control" — keep it for the
    // 4 original flavors.
    expect(body).toMatch(/per time control/i);
  });

  // ── Bullet 4: per-(metric × TC) rating-correlation copy from Plan A ──
  // Spot checks lifted verbatim from 94.3-01-SUMMARY.md's tier table.
  it('net_flag_rate_bullet bullet 4 carries the bullet-specific tier copy from Plan A', () => {
    renderChipFor(40, 'net_flag_rate_bullet', 'Net Flag Rate (bullet)');
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain(
      'At bullet, net flag rate slightly tracks rating in the opposite of the intuitive direction',
    );
  });

  it('time_pressure_score_gap_rapid bullet 4 carries the "heavy" rating-proxy copy from Plan A', () => {
    renderChipFor(40, 'time_pressure_score_gap_rapid', 'Time Pressure Score Gap (rapid)');
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('This rapid score-gap tracks rating strongly');
  });

  it('clock_gap_bullet bullet 4 carries the rating-invariant tier copy', () => {
    renderChipFor(40, 'clock_gap_bullet', 'Clock Gap (bullet)');
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('This bullet clock-management gap is mostly independent of rating');
  });

  it('time_pressure_score_gap_bullet bullet 4 carries the moderate-coupling tier copy', () => {
    renderChipFor(40, 'time_pressure_score_gap_bullet', 'Time Pressure Score Gap (bullet)');
    fireEvent.click(screen.getByTestId(TID));
    const body = screen.getByTestId(`${TID}-popover`).textContent ?? '';
    expect(body).toContain('This bullet score-gap partly tracks rating');
  });
});
