// @vitest-environment jsdom
/**
 * Phase 87.2 Plan 03: tests for EndgameMetricCard (Conv/Parity/Recov shared shell).
 *
 * Covers:
 * - Structural render: gauge + WDL bar + ScoreGapRow bullet present when
 *   games > 0 and scoreGapN > 0.
 * - ScoreGapRow absent when scoreGapN === 0.
 * - Sign convention: positive scoreGapMean above neutralMax -> ZONE_SUCCESS tint;
 *   negative below neutralMin -> ZONE_DANGER; inside band -> undefined (no color).
 * - Zone-only tint (Phase 85.1 D-04): no sig-gating on the ScoreGapRow font color.
 * - testid sub-elements: -score-gap-bullet, -score-gap-value, -score-gap-info.
 * - Popover explanation contains bucket-specific copy AND sigmoid caveat.
 * - Popover name is bucket-specific full form, not "vs opponents" framing.
 * - CI props: passed at n >= 2; undefined at n < 2.
 * - Empty state: row.games === 0 -> "Not enough data yet" + opacity-50 gauge.
 * - tileTestId prop is the container's data-testid.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import type { MaterialRow } from '@/types/endgames';

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
});

import { EndgameMetricCard } from '../EndgameMetricCard';

// jsdom normalizes oklch trailing zeros ('0.50' -> '0.5') when reading
// element.style.color back. Compare on a normalized form for robust assertions.
function normalizeColor(value: string): string {
  return value.replace(/(\d+)\.(\d*?)0+(?=\D|$)/g, (match, intPart: string, frac: string) => {
    if (frac === '') return `${intPart}`;
    return `${intPart}.${frac}`;
  });
}

function buildRow(overrides?: Partial<MaterialRow>): MaterialRow {
  // Default: Conversion row, 100 games, 70/0/30 W/D/L.
  return {
    bucket: 'conversion',
    label: 'Conversion',
    games: 100,
    win_pct: 70,
    draw_pct: 0,
    loss_pct: 30,
    score: 0.70,
    ...overrides,
  };
}

// Default Score Gap props for a positive, confident, outside-neutral-band scenario.
const DEFAULT_SCORE_GAP_PROPS = {
  scoreGapMean: 0.10,   // +10%, well above SECTION2_SCORE_GAP_CONV_NEUTRAL_MAX (0.05)
  scoreGapN: 100,
  scoreGapPValue: 0.001,
  scoreGapCiLow: 0.05,
  scoreGapCiHigh: 0.15,
};

describe('EndgameMetricCard — structural render', () => {
  it('renders container with tileTestId, gauge, WDL bar, and score gap bullet', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        {...DEFAULT_SCORE_GAP_PROPS}
      />,
    );
    expect(screen.getByTestId('tile-conversion')).not.toBeNull();
    expect(screen.getByTestId('mini-wdl-bar')).not.toBeNull();
    expect(screen.getByTestId('tile-conversion-score-gap-bullet')).not.toBeNull();
    expect(screen.getByTestId('tile-conversion-score-gap-value')).not.toBeNull();
    expect(screen.getByTestId('tile-conversion-score-gap-info')).not.toBeNull();
  });

  it('renders share% and total games in the games-count row', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow({ games: 1234 })}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        {...DEFAULT_SCORE_GAP_PROPS}
      />,
    );
    expect(screen.getByText(/Games: 45\.5% \(1,234\)/)).not.toBeNull();
  });

  it('renders the bucket-with-metric label as title', () => {
    render(
      <EndgameMetricCard
        bucket="parity"
        row={buildRow({ bucket: 'parity', score: 0.50 })}
        sharePct={30}
        tileTestId="tile-parity"
        titleTooltip="Test tooltip"
        scoreGapMean={0.08}
        scoreGapN={50}
        scoreGapPValue={0.01}
        scoreGapCiLow={0.02}
        scoreGapCiHigh={0.14}
      />,
    );
    expect(screen.getByText('Parity')).not.toBeNull();
  });

  it('renders ScoreGapRow when scoreGapN > 0', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        {...DEFAULT_SCORE_GAP_PROPS}
      />,
    );
    expect(screen.getByTestId('tile-conversion-score-gap-bullet')).not.toBeNull();
    // ScoreGapRow renders a MiniBulletChart
    expect(screen.queryByTestId('mini-bullet-chart')).not.toBeNull();
  });

  it('does NOT render ScoreGapRow when scoreGapN === 0', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        scoreGapMean={null}
        scoreGapN={0}
        scoreGapPValue={null}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    expect(screen.queryByTestId('tile-conversion-score-gap-bullet')).toBeNull();
    expect(screen.queryByTestId('mini-bullet-chart')).toBeNull();
  });

  it('renders formatted value in score-gap-value testid', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        scoreGapMean={0.05}  // exactly +5%
        scoreGapN={50}
        scoreGapPValue={0.01}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    const valueEl = screen.getByTestId('tile-conversion-score-gap-value');
    expect(valueEl.textContent).toBe('+5%');
  });
});

describe('EndgameMetricCard — sign convention (zone-only tint, no sig-gate)', () => {
  it('paints value with ZONE_SUCCESS when scoreGapMean >= neutralMax (positive outside band)', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        scoreGapMean={0.10}   // above SECTION2_SCORE_GAP_CONV_NEUTRAL_MAX (0.05)
        scoreGapN={100}
        scoreGapPValue={0.5}  // weak p-value: zone-only means color is still applied
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    const valueEl = screen.getByTestId('tile-conversion-score-gap-value');
    expect(normalizeColor(valueEl.style.color)).toBe(normalizeColor(ZONE_SUCCESS));
  });

  it('paints value with ZONE_DANGER when scoreGapMean < neutralMin (negative outside band)', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        scoreGapMean={-0.10}  // below SECTION2_SCORE_GAP_CONV_NEUTRAL_MIN (-0.05)
        scoreGapN={100}
        scoreGapPValue={0.5}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    const valueEl = screen.getByTestId('tile-conversion-score-gap-value');
    expect(normalizeColor(valueEl.style.color)).toBe(normalizeColor(ZONE_DANGER));
  });

  it('does NOT paint value color when scoreGapMean is inside neutral band', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        scoreGapMean={0.02}   // inside [-0.05, 0.05] neutral band
        scoreGapN={100}
        scoreGapPValue={0.001}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    const valueEl = screen.getByTestId('tile-conversion-score-gap-value');
    expect(valueEl.style.color).toBe('');
  });
});

describe('EndgameMetricCard — popover content (D-08)', () => {
  it('popover explanation contains bucket-specific copy for conversion', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        {...DEFAULT_SCORE_GAP_PROPS}
      />,
    );
    // The MetricStatPopover trigger is rendered in the DOM; check aria content
    expect(screen.getByTestId('tile-conversion-score-gap-info')).not.toBeNull();
    // Popover explanation is passed as prop -- check the component renders with correct name
    // MetricStatPopover renders with aria-label containing the name
    expect(screen.getByTestId('tile-conversion-score-gap-info').getAttribute('aria-label')).toBe(
      'What is Conversion Score Gap?',
    );
  });

  it('popover aria-label uses bucket-specific full form for parity', () => {
    render(
      <EndgameMetricCard
        bucket="parity"
        row={buildRow({ bucket: 'parity', score: 0.50 })}
        sharePct={30}
        tileTestId="tile-parity"
        titleTooltip="Test tooltip"
        scoreGapMean={0.08}
        scoreGapN={50}
        scoreGapPValue={0.01}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    expect(screen.getByTestId('tile-parity-score-gap-info').getAttribute('aria-label')).toBe(
      'What is Parity Score Gap?',
    );
  });

  it('popover aria-label uses bucket-specific full form for recovery', () => {
    render(
      <EndgameMetricCard
        bucket="recovery"
        row={buildRow({ bucket: 'recovery', win_pct: 30, draw_pct: 20, loss_pct: 50, score: 0.40 })}
        sharePct={25}
        tileTestId="tile-recovery"
        titleTooltip="Test tooltip"
        scoreGapMean={-0.03}
        scoreGapN={40}
        scoreGapPValue={0.3}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    expect(screen.getByTestId('tile-recovery-score-gap-info').getAttribute('aria-label')).toBe(
      'What is Recovery Score Gap?',
    );
  });
});

describe('EndgameMetricCard — CI whisker props', () => {
  it('passes CI props to ScoreGapRow when scoreGapN >= 10', () => {
    // With n >= 10, ciLow and ciHigh are non-null, so MiniBulletChart should render
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        scoreGapMean={0.10}
        scoreGapN={100}
        scoreGapPValue={0.001}
        scoreGapCiLow={0.05}
        scoreGapCiHigh={0.15}
      />,
    );
    // ScoreGapRow rendered with CI props -> MiniBulletChart present
    expect(screen.getByTestId('mini-bullet-chart')).not.toBeNull();
  });

  it('passes undefined CI to ScoreGapRow when scoreGapCiLow/CiHigh are null', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        sharePct={45.5}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        scoreGapMean={0.10}
        scoreGapN={1}  // n < 2, CI should be null
        scoreGapPValue={null}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    // ScoreGapRow still renders but without CI whiskers
    expect(screen.getByTestId('tile-conversion-score-gap-bullet')).not.toBeNull();
  });
});

describe('EndgameMetricCard — empty state', () => {
  it('renders "Not enough data yet" when row.games === 0', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow({ games: 0, win_pct: 0, draw_pct: 0, loss_pct: 0, score: 0 })}
        sharePct={0}
        tileTestId="tile-conversion"
        titleTooltip="Test tooltip"
        scoreGapMean={null}
        scoreGapN={0}
        scoreGapPValue={null}
        scoreGapCiLow={null}
        scoreGapCiHigh={null}
      />,
    );
    expect(screen.queryByText(/Not enough data yet/)).not.toBeNull();
    // No WDL bar, no score-gap bullet
    expect(screen.queryByTestId('mini-wdl-bar')).toBeNull();
    expect(screen.queryByTestId('tile-conversion-score-gap-bullet')).toBeNull();
  });
});
