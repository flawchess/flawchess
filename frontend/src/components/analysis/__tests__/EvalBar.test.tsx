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

  it('(b) evalMate=3 with depth=10 drives a full white fill', () => {
    render(<EvalBar evalCp={null} evalMate={3} depth={10} />);
    expect(parsePercent(getWhiteFillHeight())).toBeCloseTo(100, 1);
  });

  it('(d) both null → balanced 50% fill', () => {
    render(<EvalBar evalCp={null} evalMate={null} depth={10} />);
    const height = parsePercent(getWhiteFillHeight());
    expect(height).toBeCloseTo(50, 1);
  });

  it('renders no numeric text inside the bar (eval shown in the engine lines)', () => {
    render(<EvalBar evalCp={120} evalMate={3} depth={12} />);
    expect(screen.queryByTestId('analysis-eval-readout')).toBeNull();
    expect(screen.getByTestId('analysis-eval-bar').textContent).toBe('');
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

  it("flipped (Black's view) puts the white fill at the top", () => {
    render(<EvalBar evalCp={null} evalMate={2} depth={10} flipped />);
    const whiteFill = screen.getByTestId('analysis-eval-bar').querySelector('div');
    if (!whiteFill) throw new Error('White fill div not found');
    // When flipped, White is at the top of the bar.
    expect(whiteFill.style.top).toBe('0px');
  });

  describe('whiteFraction override (Maia expected-score bar, Plan 05)', () => {
    it('whiteFraction=0.75 drives ~75% white fill regardless of evalCp', () => {
      // evalCp is a strongly negative eval — without the override this would yield
      // a low white fraction, proving the override truly bypasses the sigmoid.
      render(<EvalBar evalCp={-900} evalMate={null} depth={15} whiteFraction={0.75} />);
      expect(parsePercent(getWhiteFillHeight())).toBeCloseTo(75, 1);
    });

    it('whiteFraction ignores evalMate too', () => {
      render(<EvalBar evalCp={null} evalMate={-5} depth={15} whiteFraction={0.3} />);
      expect(parsePercent(getWhiteFillHeight())).toBeCloseTo(30, 1);
    });

    it('whiteFraction is clamped to 0..1', () => {
      const { unmount } = render(
        <EvalBar evalCp={null} evalMate={null} depth={15} whiteFraction={1.5} />,
      );
      expect(parsePercent(getWhiteFillHeight())).toBeCloseTo(100, 1);
      unmount();

      render(<EvalBar evalCp={null} evalMate={null} depth={15} whiteFraction={-0.5} />);
      expect(parsePercent(getWhiteFillHeight())).toBeCloseTo(0, 1);
    });

    it('whiteFraction respects the flipped orientation', () => {
      render(<EvalBar evalCp={null} evalMate={null} depth={15} whiteFraction={0.8} flipped />);
      const whiteFill = screen.getByTestId('analysis-eval-bar').querySelector('div');
      if (!whiteFill) throw new Error('White fill div not found');
      // Flipped: white fill anchors to the top, same as the non-override path.
      expect(whiteFill.style.top).toBe('0px');
      expect(parsePercent(whiteFill.style.height)).toBeCloseTo(80, 1);
    });

    it('drives a Maia-appropriate aria-label when whiteFraction is set', () => {
      render(<EvalBar evalCp={null} evalMate={null} depth={15} whiteFraction={0.62} />);
      const bar = screen.getByTestId('analysis-eval-bar');
      expect(bar.getAttribute('aria-label')).toMatch(/Maia expected score: 62%/);
    });

    it('the Stockfish (no-whiteFraction) path aria-label is unchanged', () => {
      render(<EvalBar evalCp={100} evalMate={null} depth={15} />);
      const bar = screen.getByTestId('analysis-eval-bar');
      expect(bar.getAttribute('aria-label')).toMatch(/^Engine evaluation:/);
    });

    it('a distinct testId prop renders a separately queryable bar', () => {
      render(
        <EvalBar
          evalCp={null}
          evalMate={null}
          depth={15}
          whiteFraction={0.5}
          testId="analysis-maia-eval-bar"
        />,
      );
      expect(screen.getByTestId('analysis-maia-eval-bar')).not.toBeNull();
      expect(screen.queryByTestId('analysis-eval-bar')).toBeNull();
    });
  });
});
