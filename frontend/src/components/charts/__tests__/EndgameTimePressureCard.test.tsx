// @vitest-environment jsdom
/**
 * Phase 88 — Vitest suite for EndgameTimePressureCard.
 *
 * Covers:
 * - TC-level hide when total < MIN_GAMES_PER_TC_CARD.
 * - Clock Gap bullet always renders when card is visible.
 * - n=0 bin renders dash slot (empty testid), no bullet glyph; slot preserved.
 * - 0 < n < MIN_GAMES_PER_PRESSURE_BIN renders dimmed bullet + n=X chip.
 * - n >= MIN_GAMES_PER_PRESSURE_BIN + p > 0.05 → no font color.
 * - n >= MIN_GAMES_PER_PRESSURE_BIN + p < 0.05 + delta inside neutral band → no font color.
 * - Triple-gate passes (n >= MIN + p < 0.05 + delta outside neutral band) → font color applied.
 * - Plan 88-13 A-4: Q4 (80-100% clock remaining) row is filtered out from display.
 * - Plan 88-13 A-4: visible labels are qualitative ("High Pressure (0-20%)" …
 *   "Very Low Pressure (60-80%)"), not the raw `bin.quintile_label` range string.
 */

import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { UNRELIABLE_OPACITY } from '@/lib/theme';
import type { ClockGapBullet, PressureQuintileBullet, TimePressureTcCard } from '@/types/endgames';

// Constants match the component — reference symbolically, not as magic numbers.
const MIN_GAMES_PER_TC_CARD = 20;
const MIN_GAMES_PER_PRESSURE_BIN = 5;

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
      screen.queryByTestId('time-pressure-card-bullet-clock-gap'),
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
      screen.queryByTestId('time-pressure-card-bullet-clock-gap'),
    ).not.toBeNull();
  });
});

describe('EndgameTimePressureCard — n=0 bin slot', () => {
  it('renders dash for n=0 bin, preserving slot', () => {
    renderCard(
      makeCard({
        quintiles: [
          makeBin(0, 0, 0, null),
          makeBin(1, 40, 0, 0.5),
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    // Empty slot testid present for Q0
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-0-empty'),
    ).not.toBeNull();
    // Bin Q0 bullet testid absent (no bullet glyph for n=0)
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-0'),
    ).toBeNull();
    // Q1 still renders normally
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-1'),
    ).not.toBeNull();
  });
});

describe('EndgameTimePressureCard — sparse bins (0 < n < MIN_GAMES_PER_PRESSURE_BIN)', () => {
  it('dims bullet at UNRELIABLE_OPACITY when 0 < bin.n < MIN_GAMES_PER_PRESSURE_BIN', () => {
    const sparseBin = makeBin(2, MIN_GAMES_PER_PRESSURE_BIN - 1, 0.0, 0.5);
    renderCard(
      makeCard({
        quintiles: [
          makeBin(0, 40, 0, 0.5),
          makeBin(1, 40, 0, 0.5),
          sparseBin,
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    const binRow = screen.getByTestId('time-pressure-card-bullet-bin-2');
    // The bin row wrapper carries inline opacity when dimmed.
    expect((binRow as HTMLElement).style.opacity).toBe(`${UNRELIABLE_OPACITY}`);
  });

  it('renders n=X chip on dimmed bullet rows', () => {
    const sparseBin = makeBin(1, MIN_GAMES_PER_PRESSURE_BIN - 1, 0.0, null);
    renderCard(
      makeCard({
        quintiles: [
          makeBin(0, 40, 0, 0.5),
          sparseBin,
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    const chip = screen.queryByTestId('time-pressure-card-bullet-bin-1-n');
    expect(chip).not.toBeNull();
    expect(chip!.textContent).toBe(`n=${MIN_GAMES_PER_PRESSURE_BIN - 1}`);
  });

  it('does NOT render n-chip when bin.n >= MIN_GAMES_PER_PRESSURE_BIN', () => {
    renderCard(makeCard());
    // Default bins all have n=40, so no n-chip expected.
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-0-n'),
    ).toBeNull();
  });
});

describe('EndgameTimePressureCard — triple-gate font coloring', () => {
  it('no font color when p_value is null (below gate)', () => {
    renderCard(
      makeCard({
        quintiles: [
          // delta 0.10 is outside neutral band [-0.06, 0.06], but p=null
          makeBin(0, 50, 0.10, null),
          makeBin(1, 40, 0, 0.5),
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    const valueEl = screen.queryByTestId('time-pressure-card-bullet-bin-0-value');
    expect(valueEl).not.toBeNull();
    expect((valueEl as HTMLElement).style.color).toBeFalsy();
  });

  it('no font color when p_value above 0.05', () => {
    renderCard(
      makeCard({
        quintiles: [
          // delta outside neutral band, but p > 0.05
          makeBin(0, 50, 0.10, 0.10),
          makeBin(1, 40, 0, 0.5),
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    const valueEl = screen.queryByTestId('time-pressure-card-bullet-bin-0-value');
    expect(valueEl).not.toBeNull();
    expect((valueEl as HTMLElement).style.color).toBeFalsy();
  });

  it('no font color when delta inside neutral band even if p < 0.05', () => {
    renderCard(
      makeCard({
        quintiles: [
          // delta 0.03 inside band [-0.06, 0.06], strong p
          makeBin(0, 50, 0.03, 0.001),
          makeBin(1, 40, 0, 0.5),
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    const valueEl = screen.queryByTestId('time-pressure-card-bullet-bin-0-value');
    expect(valueEl).not.toBeNull();
    expect((valueEl as HTMLElement).style.color).toBeFalsy();
  });

  it('no font color when n < MIN_GAMES_PER_PRESSURE_BIN even with strong p and outside band', () => {
    renderCard(
      makeCard({
        quintiles: [
          // n=2 (sparse), strong p, delta outside band — n-gate blocks color
          makeBin(0, 2, 0.10, 0.001),
          makeBin(1, 40, 0, 0.5),
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    const valueEl = screen.queryByTestId('time-pressure-card-bullet-bin-0-value');
    expect(valueEl).not.toBeNull();
    // Dimmed (opacity), but no font color.
    expect((valueEl as HTMLElement).style.color).toBeFalsy();
  });

  it('applies font color when triple-gate passes (n >= MIN, p < 0.05, delta outside neutral band)', () => {
    renderCard(
      makeCard({
        quintiles: [
          // n=50 >= 5, p=0.001 < 0.05, delta=0.10 > neutralMax=0.06 → ZONE_SUCCESS
          makeBin(0, 50, 0.10, 0.001),
          makeBin(1, 40, 0, 0.5),
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    const valueEl = screen.queryByTestId('time-pressure-card-bullet-bin-0-value');
    expect(valueEl).not.toBeNull();
    expect((valueEl as HTMLElement).style.color).toBeTruthy();
  });
});

describe('EndgameTimePressureCard — Phase 88.1 opp-quintile rename (Plan 88-11)', () => {
  it('uses opp_score from the bin payload (renamed from cohort_score)', () => {
    // Render with a known opp_score and assert the popover trigger exists.
    // The opp_score is consumed by the popover's baselineLabel; we open the
    // popover (Radix click trigger) and verify the formatted percent appears.
    renderCard(
      makeCard({
        quintiles: [
          makeBin(0, 50, 0.0, 0.5, 0.48),
          makeBin(1, 40, 0, 0.5),
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    const trigger = screen.getByTestId('time-pressure-card-bullet-bin-0-info');
    fireEvent.click(trigger);
    // Popover content portals to document.body; query the whole document.
    expect(document.body.textContent ?? '').toContain('48.0%');
  });

  it('popover copy says "opponent" not "cohort"', () => {
    renderCard(
      makeCard({
        quintiles: [
          makeBin(0, 50, 0.0, 0.5, 0.48),
          makeBin(1, 40, 0, 0.5),
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    const trigger = screen.getByTestId('time-pressure-card-bullet-bin-0-info');
    fireEvent.click(trigger);
    const body = (document.body.textContent ?? '').toLowerCase();
    expect(body).toContain('opponent');
    expect(body).not.toContain('cohort');
  });

  it('handles out-of-range quintile_index gracefully (getPressureBinBand returns null → row renders no glyph)', () => {
    // A malformed bin with quintile_index=5 has no defined band.
    // The QuintileRow should early-return null instead of throwing.
    const malformed: PressureQuintileBullet = {
      quintile_index: 5,
      quintile_label: 'BAD',
      n: 40,
      delta: 0.0,
      p_value: 0.5,
      ci_low: -0.02,
      ci_high: 0.02,
      opp_score: 0.5,
    };
    expect(() =>
      renderCard(
        makeCard({
          // Replace Q4 with a malformed bin (quintile_index=5).
          quintiles: [
            makeBin(0, 40, 0, 0.5),
            makeBin(1, 40, 0, 0.5),
            makeBin(2, 40, 0, 0.5),
            makeBin(3, 40, 0, 0.5),
            malformed,
          ],
        }),
      ),
    ).not.toThrow();
    // The malformed quintile's value cell must not render. Plan 88-13 A-4 added a
    // parent-side filter `quintile_index <= 3`, so quintile_index=5 is dropped before
    // reaching the row (defense-in-depth: getPressureBinBand also returns null).
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-5-value'),
    ).toBeNull();
  });
});

// ─── Plan 88-13 (A-4 + A-5) ─────────────────────────────────────────────────

describe('EndgameTimePressureCard — Plan 88-13 A-4: Q4 (80-100%) row hidden', () => {
  it('renders only 4 quintile rows (Q0..Q3), Q4 is filtered out', () => {
    renderCard(makeCard());

    // Q0..Q3 render normally (default fixture has n=40 for all 5).
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-0-value'),
    ).not.toBeNull();
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-1-value'),
    ).not.toBeNull();
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-2-value'),
    ).not.toBeNull();
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-3-value'),
    ).not.toBeNull();

    // Q4 is filtered out — neither the QuintileRow nor any EmptyBinRow path
    // should render for quintile_index=4.
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-4-value'),
    ).toBeNull();
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-4-empty'),
    ).toBeNull();
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-4'),
    ).toBeNull();
  });

  it('hides Q4 even when Q4 has n=0 (would otherwise render EmptyBinRow)', () => {
    renderCard(
      makeCard({
        quintiles: [
          makeBin(0, 40, 0, 0.5),
          makeBin(1, 40, 0, 0.5),
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 0, 0, null), // n=0 normally renders EmptyBinRow
        ],
      }),
    );
    expect(
      screen.queryByTestId('time-pressure-card-bullet-bin-4-empty'),
    ).toBeNull();
  });
});

describe('EndgameTimePressureCard — Plan 88-13 A-4: new qualitative pressure labels', () => {
  it('Q0 visible row uses "High Pressure (0-20%)" label, not the raw "0-20%"', () => {
    renderCard(makeCard());
    const row = screen.getByTestId('time-pressure-card-bullet-bin-0');
    expect(row.textContent).toContain('High Pressure (0-20%)');
    // Raw range-only label no longer appears as a label in the row.
    // (the percent string still appears inside the new label — that's the point)
    expect(row.textContent).not.toMatch(/^0-20%:/m);
  });

  it('Q1 visible row uses "Medium Pressure (20-40%)" label', () => {
    renderCard(makeCard());
    const row = screen.getByTestId('time-pressure-card-bullet-bin-1');
    expect(row.textContent).toContain('Medium Pressure (20-40%)');
  });

  it('Q2 visible row uses "Low Pressure (40-60%)" label', () => {
    renderCard(makeCard());
    const row = screen.getByTestId('time-pressure-card-bullet-bin-2');
    expect(row.textContent).toContain('Low Pressure (40-60%)');
  });

  it('Q3 visible row uses "Very Low Pressure (60-80%)" label', () => {
    renderCard(makeCard());
    const row = screen.getByTestId('time-pressure-card-bullet-bin-3');
    expect(row.textContent).toContain('Very Low Pressure (60-80%)');
  });

  it('EmptyBinRow for Q0 (n=0) uses "High Pressure (0-20%)" label', () => {
    renderCard(
      makeCard({
        quintiles: [
          makeBin(0, 0, 0, null), // empty
          makeBin(1, 40, 0, 0.5),
          makeBin(2, 40, 0, 0.5),
          makeBin(3, 40, 0, 0.5),
          makeBin(4, 40, 0, 0.5),
        ],
      }),
    );
    const empty = screen.getByTestId('time-pressure-card-bullet-bin-0-empty');
    expect(empty.textContent).toContain('High Pressure (0-20%)');
    expect(empty.textContent).toContain('no games');
  });

  it('popover for Q0 references "High Pressure" not the raw range', () => {
    renderCard(makeCard());
    const trigger = screen.getByTestId('time-pressure-card-bullet-bin-0-info');
    fireEvent.click(trigger);
    const body = document.body.textContent ?? '';
    expect(body).toContain('High Pressure (0-20%)');
  });

  it('title popover no longer mentions Q4 or 80-100%', () => {
    renderCard(makeCard());
    const trigger = screen.getByTestId('time-pressure-card-bullet-title-info');
    fireEvent.click(trigger);
    const body = document.body.textContent ?? '';
    // Must surface the four visible labels' framing.
    expect(body).toContain('High Pressure');
    expect(body).toContain('Very Low Pressure');
    // Must NOT surface the legacy Q0/Q4 framing.
    expect(body).not.toContain('Q0 = 0-20%');
    expect(body).not.toContain('Q4 = 80-100%');
  });
});
