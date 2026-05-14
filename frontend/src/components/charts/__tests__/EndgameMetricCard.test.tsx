// @vitest-environment jsdom
/**
 * Phase 86 Plan 04: tests for EndgameMetricCard (Conv/Parity/Recov shared shell).
 *
 * Covers:
 * - Structural render: gauge + WDL bar + peer-bullet row present when games > 0
 *   and opponent_games >= MIN_OPPONENT_BASELINE_GAMES.
 * - Sig-gated diff color: confident + outside neutral band → inline color set;
 *   weak (non-confident) → no inline color.
 * - Empty state: row.games === 0 → "Not enough data yet" text + opacity-50
 *   gauge; no WDL bar; no peer-bullet row.
 * - Missing-opponent state: row.games > 0 but opponent_games < 10 → muted
 *   "n < 10, baseline unavailable" text replaces the peer-bullet row.
 * - tileTestId prop is the container's data-testid.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { ZONE_SUCCESS } from '@/lib/theme';
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

// jsdom normalizes oklch trailing zeros ('0.50' → '0.5') when reading
// element.style.color back. Compare on a normalized form for robust assertions.
function normalizeColor(value: string): string {
  return value.replace(/(\d+)\.(\d*?)0+(?=\D|$)/g, (match, intPart: string, frac: string) => {
    if (frac === '') return `${intPart}`;
    return `${intPart}.${frac}`;
  });
}

function buildRow(overrides?: Partial<MaterialRow>): MaterialRow {
  // Default: Conversion row, 100 games, 70/0/30 W/D/L → userRate = 0.70.
  // diff_p_value = 0.001 (highly confident), opponent_games = 100.
  return {
    bucket: 'conversion',
    label: 'Conversion',
    games: 100,
    win_pct: 70,
    draw_pct: 0,
    loss_pct: 30,
    score: 0.70,
    opponent_score: 0.60,
    opponent_games: 100,
    diff_p_value: 0.001,
    diff_ci_low: 0.05,
    diff_ci_high: 0.15,
    ...overrides,
  };
}

function buildMirror(overrides?: Partial<MaterialRow>): MaterialRow {
  // Default mirror (Recovery): 100 games, 40/0/60 W/D/L
  // → opponentRate for Conversion = mirror.loss_pct / 100 = 0.60.
  return {
    bucket: 'recovery',
    label: 'Recovery',
    games: 100,
    win_pct: 40,
    draw_pct: 0,
    loss_pct: 60,
    score: 0.40,
    opponent_score: 0.70,
    opponent_games: 100,
    diff_p_value: 0.001,
    diff_ci_low: -0.15,
    diff_ci_high: -0.05,
    ...overrides,
  };
}

describe('EndgameMetricCard — structural render', () => {
  it('renders container with tileTestId, gauge, WDL bar, and peer-bullet row', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow()}
        mirror={buildMirror()}
        sharePct={45.5}
        metricName="Conversion"
        metricExplanation="Test explanation"
        tileTestId="tile-conversion"
      />,
    );
    expect(screen.getByTestId('tile-conversion')).not.toBeNull();
    expect(screen.getByTestId('mini-wdl-bar')).not.toBeNull();
    expect(screen.getByTestId('mini-bullet-chart')).not.toBeNull();
  });

  it('renders share% and total games in the games-count row', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow({ games: 1234 })}
        mirror={buildMirror()}
        sharePct={45.5}
        metricName="Conversion"
        metricExplanation="Test explanation"
        tileTestId="tile-conversion"
      />,
    );
    // sharePct rendered to 1 decimal place + total in localized form
    expect(screen.getByText(/Games: 45\.5% \(1,234\)/)).not.toBeNull();
  });

  it('renders the bucket-with-metric label as title', () => {
    render(
      <EndgameMetricCard
        bucket="parity"
        row={buildRow({ bucket: 'parity', score: 0.50 })}
        mirror={buildMirror({ bucket: 'parity', score: 0.50 })}
        sharePct={30}
        metricName="Parity"
        metricExplanation="Test explanation"
        tileTestId="tile-parity"
      />,
    );
    expect(screen.getByText('Parity (Score)')).not.toBeNull();
  });
});

describe('EndgameMetricCard — sig-gated diff color', () => {
  it('paints diff with ZONE_SUCCESS when confident + outside neutral band (positive)', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow({ diff_p_value: 0.001, opponent_games: 100 })}
        mirror={buildMirror()}
        sharePct={45.5}
        metricName="Conversion"
        metricExplanation="Test explanation"
        tileTestId="tile-conversion"
      />,
    );
    const diffSpan = screen.getByTestId('tile-conversion-diff');
    expect(normalizeColor(diffSpan.style.color)).toBe(normalizeColor(ZONE_SUCCESS));
  });

  it('does NOT paint diff color when weak (p-value high)', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow({ diff_p_value: 0.5, opponent_games: 100 })}
        mirror={buildMirror()}
        sharePct={45.5}
        metricName="Conversion"
        metricExplanation="Test explanation"
        tileTestId="tile-conversion"
      />,
    );
    const diffSpan = screen.getByTestId('tile-conversion-diff');
    expect(diffSpan.style.color).toBe('');
  });
});

describe('EndgameMetricCard — empty state', () => {
  it('renders "Not enough data yet" when row.games === 0', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow({ games: 0, win_pct: 0, draw_pct: 0, loss_pct: 0, score: 0 })}
        mirror={buildMirror()}
        sharePct={0}
        metricName="Conversion"
        metricExplanation="Test explanation"
        tileTestId="tile-conversion"
      />,
    );
    expect(screen.queryByText(/Not enough data yet/)).not.toBeNull();
    // No WDL bar, no peer-bullet
    expect(screen.queryByTestId('mini-wdl-bar')).toBeNull();
    expect(screen.queryByTestId('mini-bullet-chart')).toBeNull();
  });
});

describe('EndgameMetricCard — missing-opponent state', () => {
  it('renders muted "n < 10, baseline unavailable" when opponent_games < 10', () => {
    render(
      <EndgameMetricCard
        bucket="conversion"
        row={buildRow({ opponent_games: 5 })}
        mirror={buildMirror({ games: 5 })}
        sharePct={45.5}
        metricName="Conversion"
        metricExplanation="Test explanation"
        tileTestId="tile-conversion"
      />,
    );
    expect(screen.getByTestId('tile-conversion-muted')).not.toBeNull();
    // No peer-bullet rendered
    expect(screen.queryByTestId('mini-bullet-chart')).toBeNull();
    // WDL bar still rendered
    expect(screen.queryByTestId('mini-wdl-bar')).not.toBeNull();
  });
});
