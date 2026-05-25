// @vitest-environment jsdom
/**
 * Phase 88 — Vitest suite for EndgameTimePressureCard.
 *
 * Covers:
 * - TC-level hide when total < MIN_GAMES_PER_TC_CARD.
 * - Clock Gap bullet always renders when card is visible.
 * - SC-2: 3-column header row (You / Gap+info / Opp) above Clock Gap bullet.
 * - SC-3: ScoreGapByTimePressureChart renders in place of the bullet stack.
 * - Plan 88-14 A-3: top-zone stats (now via ClockGapHeaderRow + NetFlagRateRow).
 * - Post-UAT structural refinements.
 */

import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import type { ClockGapBullet, PressureQuintileBullet, TimePressureTcCard } from '@/types/endgames';

// Constants match the component — reference symbolically, not as magic numbers.
const MIN_GAMES_PER_TC_CARD = 20;

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }),
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
});

import { EndgameTimePressureCard } from '../EndgameTimePressureCard';

// ─── Fixture builders ────────────────────────────────────────────────────────

function makeClockGap(overrides?: Partial<ClockGapBullet>): ClockGapBullet {
  return {
    n: 100,
    mean_diff_pct: 0,
    p_value: 0.5,
    ci_low: -0.02,
    ci_high: 0.02,
    ...overrides,
  };
}

function makeBin(
  quintile_index: 0 | 1 | 2 | 3 | 4,
  n: number,
  delta: number,
  p_value: number | null,
  opp_score: number | null = n > 0 ? 0.5 : null,
): PressureQuintileBullet {
  const labels = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'] as const;
  return {
    quintile_index,
    quintile_label: labels[quintile_index]!,
    n,
    delta,
    p_value,
    ci_low: n > 0 ? delta - 0.02 : null,
    ci_high: n > 0 ? delta + 0.02 : null,
    opp_score,
  };
}

function makeCard(overrides?: Partial<TimePressureTcCard>): TimePressureTcCard {
  return {
    tc: 'bullet',
    total: 100,
    // Plan 88-14 A-3: top-zone summary stats. Defaults are plausible non-null
    // values so tests that don't care about the top zone still build a valid card.
    user_avg_pct: 0.47,
    user_avg_seconds: 215,
    opp_avg_pct: 0.52,
    opp_avg_seconds: 231,
    avg_clock_diff_seconds: -16,
    net_timeout_rate: -0.005,
    clock_gap: makeClockGap(),
    quintiles: [
      makeBin(0, 40, 0.0, 0.5),
      makeBin(1, 40, 0.0, 0.5),
      makeBin(2, 40, 0.0, 0.5),
      makeBin(3, 40, 0.0, 0.5),
      makeBin(4, 40, 0.0, 0.5),
    ],
    ...overrides,
  };
}

function renderCard(card: TimePressureTcCard) {
  return render(<EndgameTimePressureCard card={card} />);
}

// ─── Tests ──────────────────────────────────────────────────────────────────

describe('EndgameTimePressureCard — TC-level hide', () => {
  it('hides card when total < MIN_GAMES_PER_TC_CARD', () => {
    renderCard(makeCard({ total: MIN_GAMES_PER_TC_CARD - 1 }));
    expect(
      screen.queryByTestId('time-pressure-card-bullet'),
    ).toBeNull();
  });

  it('renders card when total === MIN_GAMES_PER_TC_CARD', () => {
    renderCard(makeCard({ total: MIN_GAMES_PER_TC_CARD }));
    expect(
      screen.queryByTestId('time-pressure-card-bullet'),
    ).not.toBeNull();
  });
});

describe('EndgameTimePressureCard — Clock Gap bullet', () => {
  it('always renders clock-gap bullet when card is visible', () => {
    renderCard(makeCard());
    expect(
      screen.queryByTestId('time-pressure-card-bullet-clock-gap-bullet'),
    ).not.toBeNull();
  });

  it('clock-gap bullet is present regardless of bin sparsity', () => {
    // All bins empty
    renderCard(
      makeCard({
        quintiles: [
          makeBin(0, 0, 0, null),
          makeBin(1, 0, 0, null),
          makeBin(2, 0, 0, null),
          makeBin(3, 0, 0, null),
          makeBin(4, 0, 0, null),
        ],
      }),
    );
    expect(
      screen.queryByTestId('time-pressure-card-bullet-clock-gap-bullet'),
    ).not.toBeNull();
  });
});

// ─── SC-2: 3-column header row ───────────────────────────────────────────────

describe('EndgameTimePressureCard — SC-2: 3-column header row', () => {
  it('renders You/Gap/Opp in a 3-column header row ABOVE the Clock Gap bullet', () => {
    renderCard(makeCard({ user_avg_pct: 0.33, user_avg_seconds: 99, opp_avg_pct: 0.57, opp_avg_seconds: 170 }));
    const header = screen.getByTestId('time-pressure-card-bullet-clock-gap-header');
    expect(header).not.toBeNull();
    expect(header.textContent).toContain('You');
    expect(header.textContent).toContain('Gap');
    expect(header.textContent).toContain('Opp');
  });

  it('Clock Gap MetricStatPopover info icon is in the header row (centered Gap cell)', () => {
    renderCard(makeCard());
    expect(screen.getByTestId('time-pressure-card-bullet-clock-gap-info')).not.toBeNull();
  });

  it('Net flag rate stays below the Clock Gap bullet, unchanged', () => {
    renderCard(makeCard({ net_timeout_rate: -0.03 }));
    const netRate = screen.getByTestId('time-pressure-card-bullet-net-flag-rate');
    expect(netRate.textContent).toContain('Net flag rate');
  });
});

// ─── SC-3: ScoreGapByTimePressureChart replaces bullet stack ─────────────────

describe('EndgameTimePressureCard — SC-3: ScoreGapByTimePressureChart replaces bullet stack', () => {
  it('renders the score gap chart container', () => {
    renderCard(makeCard());
    expect(screen.getByTestId('time-pressure-card-bullet-score-gap-chart')).not.toBeNull();
  });

  it('no per-bucket bullet testids present', () => {
    renderCard(makeCard());
    expect(screen.queryByTestId('time-pressure-card-bullet-bin-0-bullet')).toBeNull();
    expect(screen.queryByTestId('time-pressure-card-bullet-bin-0-info')).toBeNull();
  });
});

// ─── Plan 88-14 (A-3): top-zone stats via ClockGapHeaderRow + NetFlagRateRow ──

describe('EndgameTimePressureCard — Plan 88-14 A-3: top-zone stats', () => {
  it('renders You, Opp, and Net flag rate with correct formatted values', () => {
    renderCard(
      makeCard({
        user_avg_pct: 0.47,
        user_avg_seconds: 215,
        opp_avg_pct: 0.52,
        opp_avg_seconds: 231,
        avg_clock_diff_seconds: -16,
        net_timeout_rate: -0.03,
      }),
    );
    // SC-2: my-avg-time and opp-avg-time now live in ClockGapHeaderRow.
    const myAvg = screen.getByTestId('time-pressure-card-bullet-my-avg-time');
    const oppAvg = screen.getByTestId('time-pressure-card-bullet-opp-avg-time');
    const netRate = screen.getByTestId('time-pressure-card-bullet-net-flag-rate');

    // Header row uses "You" / "Opp" labels (SC-2 spec).
    expect(myAvg.textContent).toContain('You');
    expect(oppAvg.textContent).toContain('Opp');
    expect(netRate.textContent).toContain('Net flag rate');

    // Post-UAT 88.4: pct rounded to int only — raw seconds dropped from cell.
    expect(myAvg.textContent).toContain('47%');
    expect(myAvg.textContent).not.toContain('215s');
    expect(oppAvg.textContent).toContain('52%');
    expect(oppAvg.textContent).not.toContain('231s');
    // Net flag rate is integer-rounded (16bf43f0); negative shows a minus sign.
    expect(netRate.textContent).toContain('-3%');
  });

  it('shows em-dash when an average is null', () => {
    renderCard(
      makeCard({
        user_avg_pct: null,
        user_avg_seconds: null,
        opp_avg_pct: 0.5,
        opp_avg_seconds: 150,
        avg_clock_diff_seconds: null,
        net_timeout_rate: 0,
      }),
    );
    const myAvg = screen.getByTestId('time-pressure-card-bullet-my-avg-time');
    // Em-dash (U+2014) when the underlying value is null.
    expect(myAvg.textContent).toContain('—');
    // Opp side still renders normally.
    const oppAvg = screen.getByTestId('time-pressure-card-bullet-opp-avg-time');
    expect(oppAvg.textContent).toContain('50%');
    // 0% for net_timeout_rate === 0 (integer-rounded, no sign — 16bf43f0).
    const netRate = screen.getByTestId('time-pressure-card-bullet-net-flag-rate');
    expect(netRate.textContent).toContain('0%');
  });

  it('tints net flag rate green for positive above threshold and red for negative below', async () => {
    // 0.06 fraction = 6% — above the 5% threshold => green (ZONE_SUCCESS)
    const { unmount } = renderCard(makeCard({ net_timeout_rate: 0.06 }));
    const greenCell = screen.getByTestId('time-pressure-card-bullet-net-flag-rate');
    // The colored span is a child of the cell; locate by looking at all spans.
    const greenColoredSpan = greenCell.querySelector('span[style*="color"]');
    expect(greenColoredSpan).not.toBeNull();
    unmount();

    // -0.06 fraction = -6% — below the -5% threshold => red (ZONE_DANGER)
    renderCard(makeCard({ net_timeout_rate: -0.06 }));
    const redCell = screen.getByTestId('time-pressure-card-bullet-net-flag-rate');
    const redColoredSpan = redCell.querySelector('span[style*="color"]');
    expect(redColoredSpan).not.toBeNull();
    // Different color from the green case.
    expect((greenColoredSpan as HTMLElement).style.color).not.toBe(
      (redColoredSpan as HTMLElement).style.color,
    );
  });

  it('does NOT tint net flag rate when within the neutral threshold', () => {
    // 0.03 fraction = 3% — within the +/-5% neutral band.
    renderCard(makeCard({ net_timeout_rate: 0.03 }));
    const cell = screen.getByTestId('time-pressure-card-bullet-net-flag-rate');
    // The value span should have no inline color style.
    const coloredSpan = cell.querySelector('span[style*="color"]');
    expect(coloredSpan).toBeNull();
  });
});

// ─── Post-UAT structural refinements ────────────────────────────────────────

describe('EndgameTimePressureCard — post-UAT structural refinements', () => {
  it('renders a time-control icon next to the TC label in the title', () => {
    renderCard(makeCard({ tc: 'blitz' }));
    // The TimeControlIcon renders an <svg aria-label="blitz">.
    const card = screen.getByTestId('time-pressure-card-blitz');
    const icon = card.querySelector('h3 svg[aria-label="blitz"]');
    expect(icon).not.toBeNull();
  });

it('Clock Gap value renders in the header row (no separate "(N games)" suffix)', () => {
    renderCard(makeCard({ clock_gap: makeClockGap({ n: 123, mean_diff_pct: 0.05 }) }));
    const header = screen.getByTestId('time-pressure-card-bullet-clock-gap-header');
    // Clock-eligible count is reachable via the popover, not duplicated inline.
    expect(header.textContent).not.toContain('(123 games)');
  });

  it('title game count uses "Games: X% (N)" framing with a right-aligned sword icon when grandTotal is supplied', () => {
    render(<EndgameTimePressureCard card={makeCard({ total: 1234 })} grandTotal={4936} />);
    const total = screen.getByTestId('time-pressure-card-bullet-total');
    // 1234 / 4936 ≈ 25%; rounded to integer percent.
    expect(total.textContent).toContain('Games: 25% (1,234)');
    expect(total.textContent).not.toContain('(1,234 games)');
    // Right-aligned via `ml-auto` on the total span.
    expect(total.className).toContain('ml-auto');
    // Sword icon present (lucide Swords renders as an <svg>).
    expect(total.querySelector('svg')).not.toBeNull();
  });

  it('title falls back to "Games: N" when grandTotal is not supplied', () => {
    renderCard(makeCard({ total: 1234 }));
    const total = screen.getByTestId('time-pressure-card-bullet-total');
    // Without a grand total the percentage is suppressed; count-only fallback.
    expect(total.textContent).toContain('Games: 1,234');
    expect(total.textContent).not.toMatch(/Games: \d+%/);
  });
});

// ─── Phase 94.3 Plan 06: per-(metric × TC) chip slots (TPCTL-06 / TPCTL-07) ──
//
// 3 chips per card × 4 TCs = 12 placements. Each chip is gated on the
// corresponding `<...>_percentile != null` field; below-floor (null) suppresses
// the chip silently. The `time_pressure_score_gap_classical` cell is flagged
// in Plan A as a chip-suppression candidate (n_users=24 < 150 floor), but the
// backend handles the gate by returning null; the frontend gates uniformly on
// `!= null` so no per-TC special-case is needed in the component.

const TC_CASES = ['bullet', 'blitz', 'rapid', 'classical'] as const;

describe('EndgameTimePressureCard — Phase 94.3 chip slots', () => {
  it('renders all 3 chips when all 3 percentile fields are non-null (tc=bullet)', () => {
    renderCard(
      makeCard({
        tc: 'bullet',
        clock_gap_percentile: 80,
        net_flag_rate_percentile: 10,
        time_pressure_score_gap_percentile: 70,
      }),
    );
    expect(screen.queryByTestId('time-pressure-card-bullet-clock-gap-chip')).not.toBeNull();
    expect(screen.queryByTestId('time-pressure-card-bullet-net-flag-rate-chip')).not.toBeNull();
    expect(
      screen.queryByTestId('time-pressure-card-bullet-time-pressure-score-gap-chip'),
    ).not.toBeNull();
  });

  it('suppresses ONLY the Clock Gap chip when clock_gap_percentile is null', () => {
    renderCard(
      makeCard({
        clock_gap_percentile: null,
        net_flag_rate_percentile: 10,
        time_pressure_score_gap_percentile: 70,
      }),
    );
    expect(screen.queryByTestId('time-pressure-card-bullet-clock-gap-chip')).toBeNull();
    expect(screen.queryByTestId('time-pressure-card-bullet-net-flag-rate-chip')).not.toBeNull();
    expect(
      screen.queryByTestId('time-pressure-card-bullet-time-pressure-score-gap-chip'),
    ).not.toBeNull();
  });

  it('suppresses ONLY the Net Flag chip when net_flag_rate_percentile is null', () => {
    renderCard(
      makeCard({
        clock_gap_percentile: 80,
        net_flag_rate_percentile: null,
        time_pressure_score_gap_percentile: 70,
      }),
    );
    expect(screen.queryByTestId('time-pressure-card-bullet-clock-gap-chip')).not.toBeNull();
    expect(screen.queryByTestId('time-pressure-card-bullet-net-flag-rate-chip')).toBeNull();
    expect(
      screen.queryByTestId('time-pressure-card-bullet-time-pressure-score-gap-chip'),
    ).not.toBeNull();
  });

  it('suppresses ONLY the Time Pressure Score Gap chip when its percentile is null', () => {
    renderCard(
      makeCard({
        clock_gap_percentile: 80,
        net_flag_rate_percentile: 10,
        time_pressure_score_gap_percentile: null,
      }),
    );
    expect(screen.queryByTestId('time-pressure-card-bullet-clock-gap-chip')).not.toBeNull();
    expect(screen.queryByTestId('time-pressure-card-bullet-net-flag-rate-chip')).not.toBeNull();
    expect(
      screen.queryByTestId('time-pressure-card-bullet-time-pressure-score-gap-chip'),
    ).toBeNull();
  });

  it('suppresses all 3 chips when all 3 percentile fields are null (default)', () => {
    renderCard(makeCard()); // defaults leave all 3 fields undefined → no chip
    expect(screen.queryByTestId('time-pressure-card-bullet-clock-gap-chip')).toBeNull();
    expect(screen.queryByTestId('time-pressure-card-bullet-net-flag-rate-chip')).toBeNull();
    expect(
      screen.queryByTestId('time-pressure-card-bullet-time-pressure-score-gap-chip'),
    ).toBeNull();
  });

  // Pitfall 7: net_flag_rate_percentile === 0 is a VALID percentile (the
  // worst end of the cohort under higher_is_better). The chip MUST render —
  // gate is `!= null`, not falsy. Post-UAT: direction is higher_is_better, so
  // p=0 renders as "Bottom 1%" (chip label is floored at 1% to avoid "Bottom 0%").
  it('renders the Net Flag chip when net_flag_rate_percentile === 0 (NOT null)', () => {
    renderCard(
      makeCard({
        net_flag_rate_percentile: 0,
        clock_gap_percentile: null,
        time_pressure_score_gap_percentile: null,
      }),
    );
    const chip = screen.getByTestId('time-pressure-card-bullet-net-flag-rate-chip');
    expect(chip).not.toBeNull();
    expect(chip.textContent).toContain('Bottom 1%');
  });

  // Per-TC placement parity — confirm the testid template substitutes the TC
  // name correctly for all 4 cards. 12 assertions (3 chips × 4 TCs).
  it.each(TC_CASES)('renders all 3 chips for tc=%s when percentiles are non-null', (tc) => {
    renderCard(
      makeCard({
        tc,
        clock_gap_percentile: 80,
        net_flag_rate_percentile: 10,
        time_pressure_score_gap_percentile: 70,
      }),
    );
    expect(screen.queryByTestId(`time-pressure-card-${tc}-clock-gap-chip`)).not.toBeNull();
    expect(screen.queryByTestId(`time-pressure-card-${tc}-net-flag-rate-chip`)).not.toBeNull();
    expect(
      screen.queryByTestId(`time-pressure-card-${tc}-time-pressure-score-gap-chip`),
    ).not.toBeNull();
  });

  // Chip slots structurally placed near their owning labels.
  it('Clock Gap chip lives inside the ClockGapHeaderRow', () => {
    renderCard(
      makeCard({
        clock_gap_percentile: 80,
        net_flag_rate_percentile: 10,
        time_pressure_score_gap_percentile: 70,
      }),
    );
    const header = screen.getByTestId('time-pressure-card-bullet-clock-gap-header');
    expect(header.querySelector('[data-testid="time-pressure-card-bullet-clock-gap-chip"]')).not.toBeNull();
  });

  it('Net Flag chip lives inside the NetFlagRateRow', () => {
    renderCard(
      makeCard({
        clock_gap_percentile: 80,
        net_flag_rate_percentile: 10,
        time_pressure_score_gap_percentile: 70,
      }),
    );
    const row = screen.getByTestId('time-pressure-card-bullet-net-flag-rate-row');
    expect(row.querySelector('[data-testid="time-pressure-card-bullet-net-flag-rate-chip"]')).not.toBeNull();
  });

  it('Time Pressure Score Gap chip lives inside the quintiles subtitle', () => {
    renderCard(
      makeCard({
        clock_gap_percentile: 80,
        net_flag_rate_percentile: 10,
        time_pressure_score_gap_percentile: 70,
      }),
    );
    const subtitle = screen.getByTestId('time-pressure-card-bullet-quintiles-subtitle');
    expect(
      subtitle.querySelector(
        '[data-testid="time-pressure-card-bullet-time-pressure-score-gap-chip"]',
      ),
    ).not.toBeNull();
  });
});
