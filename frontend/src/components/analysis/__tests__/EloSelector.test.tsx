// @vitest-environment jsdom
/**
 * Phase 151 Plan 05 — EloSelector tests (D-06).
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { EloSelector } from '../EloSelector';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';

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

describe('EloSelector', () => {
  it('renders the current value', () => {
    render(<EloSelector value={1500} onChange={vi.fn()} />);
    expect(screen.getByTestId('analysis-elo-selector-value').textContent).toBe('1500');
  });

  it('has data-testid="analysis-elo-selector" and an aria-label', () => {
    render(<EloSelector value={1500} onChange={vi.fn()} />);
    const el = screen.getByTestId('analysis-elo-selector');
    expect(el.getAttribute('aria-label')).toMatch(/ELO/);
  });

  it('bounds derive from the ladder prop (not a hard-coded 1100-2000)', () => {
    render(<EloSelector value={1000} onChange={vi.fn()} ladder={[600, 1000, 1400]} />);
    const thumb = screen.getByRole('slider');
    expect(thumb.getAttribute('aria-valuemin')).toBe('600');
    expect(thumb.getAttribute('aria-valuemax')).toBe('1400');
  });

  it('defaults to MAIA_ELO_LADDER bounds when no ladder prop is passed', () => {
    render(<EloSelector value={1500} onChange={vi.fn()} />);
    const thumb = screen.getByRole('slider');
    expect(thumb.getAttribute('aria-valuemin')).toBe(String(MAIA_ELO_LADDER[0]));
    expect(thumb.getAttribute('aria-valuemax')).toBe(
      String(MAIA_ELO_LADDER[MAIA_ELO_LADDER.length - 1]),
    );
  });

  it('interacting (ArrowRight on the thumb) fires onChange with the next ladder value', () => {
    const onChange = vi.fn();
    render(<EloSelector value={1500} onChange={onChange} ladder={[1100, 1200, 1300]} />);
    const thumb = screen.getByRole('slider');
    thumb.focus();
    fireEvent.keyDown(thumb, { key: 'ArrowRight' });
    expect(onChange).toHaveBeenCalledWith(1300);
  });

  it('interacting (ArrowLeft) fires onChange with the previous ladder value', () => {
    const onChange = vi.fn();
    render(<EloSelector value={1300} onChange={onChange} ladder={[1100, 1200, 1300]} />);
    const thumb = screen.getByRole('slider');
    thumb.focus();
    fireEvent.keyDown(thumb, { key: 'ArrowLeft' });
    expect(onChange).toHaveBeenCalledWith(1200);
  });

  it('does not fire onChange with a value outside the ladder bounds (Home clamps to min)', () => {
    const onChange = vi.fn();
    render(<EloSelector value={1200} onChange={onChange} ladder={[1100, 1200, 1300]} />);
    const thumb = screen.getByRole('slider');
    thumb.focus();
    fireEvent.keyDown(thumb, { key: 'Home' });
    expect(onChange).toHaveBeenCalledWith(1100);
    onChange.mock.calls.forEach(([elo]) => {
      expect(elo).toBeGreaterThanOrEqual(1100);
      expect(elo).toBeLessThanOrEqual(1300);
    });
  });
});
