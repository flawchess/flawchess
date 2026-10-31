// @vitest-environment jsdom
/** The Stats tab "Out of the opening" card: rows, inverted words, states, colour switching. */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import type {
  OpeningOutRateOut,
  OutOfOpeningStatsResponse,
} from '@/types/openingOut';
import { OutOfOpeningSection } from '../OutOfOpeningSection';

const readinessState = { tier2: true };
const queryState: { data: OutOfOpeningStatsResponse | undefined; isError: boolean } = {
  data: undefined,
  isError: false,
};
const useOutOfOpeningStatsMock = vi.fn<(options?: { enabled?: boolean }) => unknown>(() => ({
  data: queryState.data,
  isError: queryState.isError,
}));

vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({ tier2: readinessState.tier2 }),
}));
vi.mock('@/hooks/useOutOfOpeningStats', () => ({
  useOutOfOpeningStats: (options?: { enabled?: boolean }) => useOutOfOpeningStatsMock(options),
}));

beforeEach(() => {
  readinessState.tier2 = true;
  queryState.data = undefined;
  queryState.isError = false;
  useOutOfOpeningStatsMock.mockClear();
});
afterEach(cleanup);

function rate(overrides: Partial<OpeningOutRateOut> = {}): OpeningOutRateOut {
  return {
    status: 'ranked',
    k: 330,
    n: 1491,
    rate: 0.22,
    floor_n: 1491,
    floor_required: 30,
    percentile_favorable: 58,
    ci_low: 0.201,
    ci_high: 0.243,
    p_value: 0.034,
    peer_p25: 0.15,
    peer_p50: 0.21,
    peer_p75: 0.28,
    significant: false,
    tcs: [],
    ...overrides,
  };
}

function belowFloor(n: number): OpeningOutRateOut {
  return rate({
    status: 'below_floor',
    rate: 0.25,
    n,
    k: 3,
    floor_n: n,
    percentile_favorable: null,
    ci_low: null,
    ci_high: null,
    p_value: null,
    peer_p25: null,
    peer_p50: null,
    peer_p75: null,
  });
}

function stats(overrides: Partial<OutOfOpeningStatsResponse> = {}): OutOfOpeningStatsResponse {
  return {
    white: { worse: rate(), better: rate({ rate: 0.1, percentile_favorable: 71 }) },
    black: { worse: belowFloor(12), better: belowFloor(12) },
    ...overrides,
  };
}

describe('OutOfOpeningSection', () => {
  it('renders the ranked white card with both rows, inverted hints and the bar number', () => {
    queryState.data = stats();
    render(<OutOfOpeningSection color="white" />);

    expect(screen.getByTestId('out-of-opening-heading').textContent).toBe('Out of the opening');
    expect(screen.queryByTestId('out-of-opening-status-card')).toBeNull();
    expect(screen.getByTestId('out-of-opening-card-worse').textContent).toContain('Came out worse');
    expect(screen.getByTestId('out-of-opening-card-better').textContent).toContain(
      'Came out better',
    );
    expect(screen.getByTestId('out-of-opening-card-worse-value').textContent).toBe('22%');
    expect(screen.getByTestId('out-of-opening-card-better-value').textContent).toBe('10%');
    expect(screen.getByTestId('out-of-opening-card-worse-hint').textContent).toBe(
      'Fewer bad openings than 58% of peers',
    );
    expect(screen.getByTestId('out-of-opening-card-better-hint').textContent).toBe(
      'More good openings than 71% of peers',
    );
    expect(screen.getByTestId('out-of-opening-card-worse-bar-number').textContent).toBe('58th');
  });

  it('labels the rate and puts the hint under the bar, not beside the value', () => {
    queryState.data = stats();
    render(<OutOfOpeningSection color="white" />);

    // UAT: "22% Fewer bad openings than 58%..." read as one sentence when the hint sat
    // next to the value. Order is now label + value, bar, hint.
    const text = screen.getByTestId('out-of-opening-card-worse').textContent ?? '';
    const label = text.indexOf('Share of your games');
    const value = text.indexOf('22%');
    const bar = text.indexOf('58th');
    const hint = text.indexOf('Fewer bad openings');
    expect(label).toBeGreaterThan(-1);
    expect(label).toBeLessThan(value);
    expect(value).toBeLessThan(bar);
    expect(bar).toBeLessThan(hint);
  });

  it('puts a popover trigger with a fixed literal testid on each row', () => {
    queryState.data = stats();
    render(<OutOfOpeningSection color="white" />);
    expect(screen.getByTestId('out-of-opening-worse-rate')).not.toBeNull();
    expect(screen.getByTestId('out-of-opening-better-rate')).not.toBeNull();
  });

  it('shows the selected colour only: black is below floor while white stays ranked', () => {
    queryState.data = stats();
    const { rerender } = render(<OutOfOpeningSection color="black" />);
    expect(screen.getByTestId('out-of-opening-card-worse-bar').textContent).toBe(
      'Not enough games to rank yet (12 of 30)',
    );
    expect(screen.queryByTestId('out-of-opening-card-worse-hint')).toBeNull();

    rerender(<OutOfOpeningSection color="white" />);
    expect(screen.getByTestId('out-of-opening-card-worse-bar-number').textContent).toBe('58th');
  });

  it('hides the value of a pending row and shows the analyzing line', () => {
    queryState.data = stats({
      white: {
        worse: rate({ status: 'pending', percentile_favorable: null }),
        better: rate({ status: 'pending', percentile_favorable: null }),
      },
    });
    render(<OutOfOpeningSection color="white" />);
    expect(screen.queryByTestId('out-of-opening-card-worse-value')).toBeNull();
    expect(screen.getByTestId('out-of-opening-card-worse-bar').textContent).toContain('Analyzing');
  });

  it('shows "Not ranked yet" for an unranked row', () => {
    queryState.data = stats({
      white: {
        worse: rate({ status: 'unranked', percentile_favorable: null }),
        better: rate({ status: 'unranked', percentile_favorable: null }),
      },
    });
    render(<OutOfOpeningSection color="white" />);
    expect(screen.getByTestId('out-of-opening-card-worse-bar').textContent).toBe('Not ranked yet');
  });

  it('keeps a not-significant ranked dot neutral even in the red zone', () => {
    queryState.data = stats({
      white: {
        worse: rate({ percentile_favorable: 10, significant: false }),
        better: rate({ percentile_favorable: 90, significant: false }),
      },
    });
    render(<OutOfOpeningSection color="white" />);
    const neutral = screen.getByTestId('out-of-opening-card-worse-bar-dot').style.backgroundColor;
    expect(screen.getByTestId('out-of-opening-card-better-bar-dot').style.backgroundColor).toBe(
      neutral,
    );
  });

  it('colours the dot only when significant', () => {
    queryState.data = stats({
      white: {
        worse: rate({ percentile_favorable: 10, significant: true }),
        better: rate({ percentile_favorable: 10, significant: false }),
      },
    });
    render(<OutOfOpeningSection color="white" />);
    expect(screen.getByTestId('out-of-opening-card-worse-bar-dot').style.backgroundColor).not.toBe(
      screen.getByTestId('out-of-opening-card-better-bar-dot').style.backgroundColor,
    );
  });

  it('shows the loading line while the data is missing', () => {
    render(<OutOfOpeningSection color="white" />);
    expect(screen.getByTestId('out-of-opening-loading')).not.toBeNull();
  });

  it('shows the load error copy', () => {
    queryState.isError = true;
    render(<OutOfOpeningSection color="white" />);
    expect(screen.getByTestId('out-of-opening-error').textContent).toBe(
      'Failed to load out-of-the-opening stats. Something went wrong. Please try again in a moment.',
    );
  });

  it('keeps showing cached data when a background refetch fails', () => {
    queryState.data = stats();
    queryState.isError = true;
    render(<OutOfOpeningSection color="white" />);
    expect(screen.queryByTestId('out-of-opening-error')).toBeNull();
    expect(screen.getByTestId('out-of-opening-card-worse-value').textContent).toBe('22%');
  });

  it('shows the analyzing line and keeps the query disabled while tier2 is false', () => {
    readinessState.tier2 = false;
    render(<OutOfOpeningSection color="white" />);
    expect(screen.getByTestId('out-of-opening-pending').textContent).toContain('Analyzing');
    expect(useOutOfOpeningStatsMock).toHaveBeenCalledWith({ enabled: false });
  });
});
