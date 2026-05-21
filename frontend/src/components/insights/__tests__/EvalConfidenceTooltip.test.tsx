// @vitest-environment jsdom
/**
 * Phase 91 Plan 07: Tests for the pending-analysis caveat added to EvalConfidenceTooltip.
 *
 * Covers:
 *   - caveat shown when isPending=true AND pendingCount > 0
 *   - caveat absent when isPending=false
 *   - caveat absent when isPending=true but pendingCount=0 (defensive edge case)
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { EvalConfidenceTooltip } from '../EvalConfidenceTooltip';

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

// Minimal required props for EvalConfidenceTooltip.
const baseProps = {
  level: 'medium' as const,
  pValue: 0.02,
  gameCount: 50,
  evalMeanPawns: 0.3,
  color: 'white' as const,
};

describe('EvalConfidenceTooltip — pending-analysis caveat', () => {
  it('test_caveat_shown_when_pending: shows caveat with formatted count when isPending=true and pendingCount > 0', () => {
    render(
      <EvalConfidenceTooltip
        {...baseProps}
        isPending={true}
        pendingCount={1432}
      />,
    );
    const caveat = screen.getByTestId('eval-pending-caveat');
    expect(caveat.textContent).toMatch(/Based on 50 currently-evaluated games/);
    expect(caveat.textContent).toMatch(/1,432 more across your library/);
    expect(caveat.textContent).toMatch(/may shift as analysis completes/);
  });

  it('test_caveat_absent_when_not_pending: caveat is absent from the DOM when isPending=false', () => {
    render(
      <EvalConfidenceTooltip
        {...baseProps}
        isPending={false}
        pendingCount={500}
      />,
    );
    expect(screen.queryByTestId('eval-pending-caveat')).toBeNull();
  });

  it('test_caveat_absent_when_pending_count_zero: caveat is absent when isPending=true but pendingCount=0', () => {
    render(
      <EvalConfidenceTooltip
        {...baseProps}
        isPending={true}
        pendingCount={0}
      />,
    );
    expect(screen.queryByTestId('eval-pending-caveat')).toBeNull();
  });

  it('caveat is absent when isPending and pendingCount props are omitted (default)', () => {
    render(<EvalConfidenceTooltip {...baseProps} />);
    expect(screen.queryByTestId('eval-pending-caveat')).toBeNull();
  });
});
