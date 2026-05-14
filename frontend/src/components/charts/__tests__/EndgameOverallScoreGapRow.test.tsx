// @vitest-environment jsdom
/**
 * Phase 85.1 Plan 03 Task 1: ScoreGapRow CI prop threading.
 *
 * Verifies that `ScoreGapRow` forwards optional `ciLow` / `ciHigh` props into
 * the underlying `MiniBulletChart`. When either is omitted the chart receives
 * `undefined` for that prop (whisker suppression is then handled inside the
 * chart itself; per the WR-02 pattern we surface the prop value as a
 * `data-ci-*` attribute on the mock so the test can read it back).
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

// Mock MiniBulletChart so we can inspect the CI props passed in. We surface
// ciLow / ciHigh via data-ci-low / data-ci-high attributes (omitted when the
// prop is undefined so tests can assert presence/absence).
vi.mock('@/components/charts/MiniBulletChart', () => ({
  MiniBulletChart: vi.fn((props: Record<string, unknown>) => {
    const dataAttrs: Record<string, string> = {};
    if (props.ciLow !== undefined) dataAttrs['data-ci-low'] = String(props.ciLow);
    if (props.ciHigh !== undefined) dataAttrs['data-ci-high'] = String(props.ciHigh);
    return <div data-testid="mock-mini-bullet" {...dataAttrs} />;
  }),
}));

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

import { ScoreGapRow } from '../EndgameOverallScoreGapRow';

const baseProps = {
  label: 'Test Score Gap:',
  value: 0.05,
  formatted: '+5%',
  resultColor: undefined,
  valueTestId: 'test-score-gap-value',
  ariaLabel: 'Test Score Gap',
};

describe('ScoreGapRow CI prop threading', () => {
  it('renders without ciLow/ciHigh -> mock has no data-ci-low / data-ci-high attrs', () => {
    render(<ScoreGapRow {...baseProps} />);
    const bullet = screen.getByTestId('mock-mini-bullet');
    expect(bullet.getAttribute('data-ci-low')).toBeNull();
    expect(bullet.getAttribute('data-ci-high')).toBeNull();
  });

  it('forwards both ciLow and ciHigh when provided', () => {
    render(<ScoreGapRow {...baseProps} ciLow={-0.05} ciHigh={0.07} />);
    const bullet = screen.getByTestId('mock-mini-bullet');
    expect(bullet.getAttribute('data-ci-low')).toBe('-0.05');
    expect(bullet.getAttribute('data-ci-high')).toBe('0.07');
  });

  it('forwards ciLow alone (defensive: half-defined CI is allowed)', () => {
    render(<ScoreGapRow {...baseProps} ciLow={-0.05} />);
    const bullet = screen.getByTestId('mock-mini-bullet');
    expect(bullet.getAttribute('data-ci-low')).toBe('-0.05');
    expect(bullet.getAttribute('data-ci-high')).toBeNull();
  });
});
