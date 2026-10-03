// @vitest-environment jsdom
/**
 * Phase 229 (D-03, D-12 group 2): FilterPanel and the shared FilterActions footer
 * report one typed `filter-change` per user change, nothing on render, and nothing
 * on a Radix single-select re-tap. Uses the REAL analytics module with a
 * window.umami stub so the whole click -> trackFeature -> window.umami.track path
 * is exercised.
 */
import { useState } from 'react';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { DEFAULT_FILTERS, FilterPanel, type FilterState } from '../FilterPanel';

const track = vi.fn();

beforeAll(() => {
  // Radix ToggleGroup and FilterPanel's useIsMobile need these in jsdom.
  if (typeof window.ResizeObserver === 'undefined') {
    window.ResizeObserver = class ResizeObserver {
      observe = vi.fn();
      unobserve = vi.fn();
      disconnect = vi.fn();
    };
  }
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
});

beforeEach(() => {
  track.mockClear();
  window.umami = { track, identify: vi.fn() };
  window.history.pushState({}, '', '/openings');
});

afterEach(() => {
  cleanup();
  delete window.umami;
});

/** Stateful wrapper so re-tap semantics (Radix emits '') are real, not mocked. */
function Harness({ onApply, showPastedChip = false }: { onApply?: () => void; showPastedChip?: boolean }) {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  return (
    <FilterPanel filters={filters} onChange={setFilters} onApply={onApply} showPastedChip={showPastedChip} />
  );
}

function expectSingleEvent(args: Record<string, string>): void {
  expect(track).toHaveBeenCalledTimes(1);
  expect(track).toHaveBeenCalledWith('filter-change', { page: 'openings', ...args });
}

describe('FilterPanel filter-change tracking', () => {
  it('fires nothing on render', () => {
    render(<Harness onApply={vi.fn()} showPastedChip />);
    expect(track).not.toHaveBeenCalled();
  });

  it('reports a time-control chip with the toggled value', () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId('filter-time-control-blitz'));
    expectSingleEvent({ target: 'time-control', value: 'blitz' });
  });

  it('stays silent when the last active time control is tapped (clamped no-op)', () => {
    render(<Harness />);
    for (const tc of ['bullet', 'rapid', 'classical']) {
      fireEvent.click(screen.getByTestId(`filter-time-control-${tc}`));
    }
    expect(track).toHaveBeenCalledTimes(3);
    fireEvent.click(screen.getByTestId('filter-time-control-blitz'));
    expect(track).toHaveBeenCalledTimes(3);
  });

  it('reports a platform chip and the Pasted chip', () => {
    render(<Harness showPastedChip />);
    fireEvent.click(screen.getByTestId('filter-platform-lichess'));
    expectSingleEvent({ target: 'platform', value: 'lichess' });
    track.mockClear();
    fireEvent.click(screen.getByTestId('filter-platform-pasted'));
    expectSingleEvent({ target: 'platform', value: 'pasted' });
  });

  it('reports rated, and stays silent when the active item is re-tapped', () => {
    render(<Harness />);
    // DEFAULT_FILTERS.rated is true, so 'rated' is the active item.
    fireEvent.click(screen.getByTestId('filter-rated-rated'));
    expect(track).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('filter-rated-casual'));
    expectSingleEvent({ target: 'rated', value: 'casual' });
  });

  it('reports opponent type and played-as, and stays silent on a re-tap', () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId('filter-opponent-human'));
    expect(track).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('filter-opponent-bot'));
    expectSingleEvent({ target: 'opponent-type', value: 'bot' });
    track.mockClear();
    fireEvent.click(screen.getByTestId('filter-played-as-white'));
    expectSingleEvent({ target: 'played-as', value: 'white' });
    track.mockClear();
    fireEvent.click(screen.getByTestId('filter-played-as-white'));
    expect(track).not.toHaveBeenCalled();
  });

  it('reports reset and apply from the shared footer when onApply is set', () => {
    const onApply = vi.fn();
    render(<Harness onApply={onApply} />);
    fireEvent.click(screen.getByTestId('btn-filter-reset'));
    expectSingleEvent({ target: 'reset' });
    track.mockClear();
    fireEvent.click(screen.getByTestId('btn-filter-apply'));
    expect(onApply).toHaveBeenCalledTimes(1);
    expectSingleEvent({ target: 'apply' });
  });

  it('reports reset from the lone Reset button when onApply is absent', () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId('btn-reset-filters'));
    expectSingleEvent({ target: 'reset' });
  });

  it('sends nothing on an excluded route (D-14)', () => {
    window.history.pushState({}, '', '/admin');
    render(<Harness />);
    fireEvent.click(screen.getByTestId('filter-time-control-blitz'));
    expect(track).not.toHaveBeenCalled();
  });
});
