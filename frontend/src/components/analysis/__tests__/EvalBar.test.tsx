// @vitest-environment jsdom
/**
 * Phase 137 Plan 02 — EvalBar render tests.
 *
 * Verifies:
 *  (a) positive evalCp → taller white fill than negative evalCp
 *  (b) evalMate=3 with depth=10 → M3 mate label rendered
 *  (c) evalMate=3 with depth=5 → NO mate label (depth-8 gate, D-04)
 *  (d) both null → no mate label and balanced (0.5) fill
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { EvalBar } from '../EvalBar';
import { EVAL_BAR_BLACK, EVAL_BAR_WHITE } from '@/lib/theme';

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

/**
 * Returns the computed white fill height string (e.g. "73.11%") from the
 * rendered bar by reading the first absolutely-positioned fill div's style.
 */
function getWhiteFillHeight(): string {
  const container = screen.getByTestId('analysis-eval-bar');
  // The white fill is the first child div
  const whiteFill = container.querySelector('div');
  if (!whiteFill) throw new Error('White fill div not found');
  return whiteFill.style.height;
}

function parsePercent(value: string): number {
  return parseFloat(value.replace('%', ''));
}

describe('EvalBar', () => {
  it('(a) positive evalCp yields a taller white fill than negative evalCp', () => {
    const { unmount } = render(
      <EvalBar evalCp={200} evalMate={null} depth={15} />,
    );
    const positiveHeight = parsePercent(getWhiteFillHeight());
    unmount();

    render(<EvalBar evalCp={-200} evalMate={null} depth={15} />);
    const negativeHeight = parsePercent(getWhiteFillHeight());

    expect(positiveHeight).toBeGreaterThan(negativeHeight);
    // Positive 200cp should be above 50%, negative below
    expect(positiveHeight).toBeGreaterThan(50);
    expect(negativeHeight).toBeLessThan(50);
  });

  it('(b) evalMate=3 with depth=10 renders an M3 mate label', () => {
    render(<EvalBar evalCp={null} evalMate={3} depth={10} />);
    expect(screen.getByText('M3')).toBeTruthy();
  });

  it('(c) evalMate=3 with depth=5 renders NO mate label (depth-8 gate)', () => {
    render(<EvalBar evalCp={null} evalMate={3} depth={5} />);
    expect(screen.queryByText('M3')).toBeNull();
  });

  it('(d) both null → no mate label, balanced 50% fill', () => {
    render(<EvalBar evalCp={null} evalMate={null} depth={10} />);
    expect(screen.queryByText(/^M\d/)).toBeNull();
    const height = parsePercent(getWhiteFillHeight());
    expect(height).toBeCloseTo(50, 1);
  });

  it('uses EVAL_BAR_WHITE and EVAL_BAR_BLACK from theme (not hard-coded oklch)', () => {
    render(<EvalBar evalCp={100} evalMate={null} depth={12} />);
    const container = screen.getByTestId('analysis-eval-bar');
    const fills = container.querySelectorAll('div');
    const whiteFill = fills[0];
    const blackFill = fills[1];
    if (!whiteFill || !blackFill) throw new Error('Fill divs not found');
    expect(whiteFill.style.background).toBe(EVAL_BAR_WHITE);
    expect(blackFill.style.background).toBe(EVAL_BAR_BLACK);
  });

  it('has data-testid="analysis-eval-bar", role="img", and aria-label', () => {
    render(<EvalBar evalCp={142} evalMate={null} depth={20} />);
    const bar = screen.getByTestId('analysis-eval-bar');
    expect(bar.getAttribute('role')).toBe('img');
    expect(bar.getAttribute('aria-label')).toMatch(/Engine evaluation:/);
  });

  it('white-winning mate label is at top, black-winning mate label is at bottom', () => {
    const { unmount } = render(
      <EvalBar evalCp={null} evalMate={2} depth={10} />,
    );
    const whiteLabel = screen.getByText('M2');
    expect(whiteLabel.className).toContain('top-2');
    unmount();

    render(<EvalBar evalCp={null} evalMate={-2} depth={10} />);
    const blackLabel = screen.getByText('M2');
    expect(blackLabel.className).toContain('bottom-2');
  });
});
