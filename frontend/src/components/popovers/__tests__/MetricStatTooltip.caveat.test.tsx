// @vitest-environment jsdom
/**
 * Phase 91 Plan 07: Tests for the pending-analysis caveat added to MetricStatTooltip.
 *
 * Covers:
 *   - caveat shown when isPending=true AND pendingCount > 0
 *   - caveat absent when isPending=false
 *   - caveat absent when isPending=true but pendingCount=0 (defensive edge case)
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { MetricStatTooltip } from '../MetricStatTooltip';

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

// Minimal required props for MetricStatTooltip (score-vocab, percent unit).
const baseProps = {
  name: 'Endgame Score',
  explanation: 'Test explanation.',
  value: 0.62,
  baseline: 0.5,
  unit: 'percent' as const,
  gameCount: 50,
  level: 'high' as const,
  pValue: 0.001,
  vocabulary: 'score' as const,
  neutralLower: 0.45,
  neutralUpper: 0.55,
  baselineLabel: '50%',
  methodology: 'Methodology footer.',
};

describe('MetricStatTooltip — pending-analysis caveat', () => {
  it('test_caveat_shown_when_pending: shows caveat with formatted count when isPending=true and pendingCount > 0', () => {
    render(
      <MetricStatTooltip
        {...baseProps}
        isPending={true}
        pendingCount={1432}
      />,
    );
    const caveat = screen.getByText(/Based on currently-evaluated games/);
    expect(caveat.textContent).toMatch(/1,432 more being analysed/);
    expect(caveat.textContent).toMatch(/refresh in a few minutes for updated values/);
  });

  it('test_caveat_absent_when_not_pending: caveat is absent from the DOM when isPending=false', () => {
    render(
      <MetricStatTooltip
        {...baseProps}
        isPending={false}
        pendingCount={500}
      />,
    );
    expect(screen.queryByText(/Based on currently-evaluated games/)).toBeNull();
  });

  it('test_caveat_absent_when_pending_count_zero: caveat is absent when isPending=true but pendingCount=0', () => {
    render(
      <MetricStatTooltip
        {...baseProps}
        isPending={true}
        pendingCount={0}
      />,
    );
    expect(screen.queryByText(/Based on currently-evaluated games/)).toBeNull();
  });

  it('caveat is absent when isPending and pendingCount props are omitted (default)', () => {
    render(<MetricStatTooltip {...baseProps} />);
    expect(screen.queryByText(/Based on currently-evaluated games/)).toBeNull();
  });
});
