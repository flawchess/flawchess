// @vitest-environment jsdom
/**
 * Tests for EvalConfidenceTooltip after removing the
 * pending-analysis caveat (Constraint 7).
 *
 * The eval-pending-caveat block (data-testid="eval-pending-caveat") has been
 * removed — the global EvalCoverageHeader bar + per-row EvalCpuPlaceholder
 * are now the only in-progress signals. This file asserts the caveat is gone
 * under all prop combinations the component still accepts.
 *
 * The caveat block no longer exists.
 * The tests assert
 * the caveat element is absent from the DOM.
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
};

describe('EvalConfidenceTooltip — pending-analysis caveat removed (Constraint 7)', () => {
  it('eval-pending-caveat is absent under base props (no pending props)', () => {
    render(<EvalConfidenceTooltip {...baseProps} />);
    expect(screen.queryByTestId('eval-pending-caveat')).toBeNull();
  });

  it('eval-pending-caveat is absent with low confidence', () => {
    render(<EvalConfidenceTooltip {...baseProps} level="low" />);
    expect(screen.queryByTestId('eval-pending-caveat')).toBeNull();
  });

  it('eval-pending-caveat is absent with high confidence', () => {
    render(<EvalConfidenceTooltip {...baseProps} level="high" />);
    expect(screen.queryByTestId('eval-pending-caveat')).toBeNull();
  });


  it('renders the metric line with signed pawns and game count', () => {
    render(<EvalConfidenceTooltip {...baseProps} />);
    // Should still render the metric content (caveat removal does not affect the main content)
    const container = document.querySelector('.text-left');
    expect(container).not.toBeNull();
    expect(container?.textContent).toMatch(/\+0.30 pawns/);
    expect(container?.textContent).toMatch(/50 games/);
    expect(container?.textContent).toMatch(/endgame begins/);
  });
});
