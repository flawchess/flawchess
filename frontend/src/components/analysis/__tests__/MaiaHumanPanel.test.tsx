// @vitest-environment jsdom
/**
 * Phase 151 Plan 06 — MaiaHumanPanel tests.
 *
 * Thin composition component: a Card whose header carries the title + info tooltip
 * and whose body holds EloSelector + MovesByRatingChart. Verifies wiring, not the
 * child components' own behavior (each has its own test suite already).
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { MaiaHumanPanel } from '../MaiaHumanPanel';

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

describe('MaiaHumanPanel', () => {
  it('renders the ELO selector and the chart', () => {
    render(
      <MaiaHumanPanel
        selectedElo={1500}
        onEloChange={vi.fn()}
        perElo={[]}
        playedSan={null}
        bestSan={null}
        shownSans={[]}
        qualityBySan={new Map()}
        engineTopLines={[]}
      />,
    );
    expect(screen.getByTestId('analysis-elo-selector')).toBeTruthy();
    expect(screen.getByTestId('moves-by-rating-chart')).toBeTruthy();
  });

  it('renders the header title and the info tooltip trigger (UAT quick 260705-bm3)', () => {
    render(
      <MaiaHumanPanel
        selectedElo={1500}
        onEloChange={vi.fn()}
        perElo={[]}
        playedSan={null}
        bestSan={null}
        shownSans={[]}
        qualityBySan={new Map()}
        engineTopLines={[]}
      />,
    );
    expect(screen.getByTestId('maia-human-header').textContent).toMatch(/Human Move Probability/);
    expect(screen.getByTestId('maia-info-popover')).toBeTruthy();
  });

  it('no longer renders the removed attribution legal box (UAT quick 260705-bm3)', () => {
    render(
      <MaiaHumanPanel
        selectedElo={1500}
        onEloChange={vi.fn()}
        perElo={[]}
        playedSan={null}
        bestSan={null}
        shownSans={[]}
        qualityBySan={new Map()}
        engineTopLines={[]}
      />,
    );
    expect(screen.queryByTestId('maia-attribution')).toBeNull();
  });

  it('compact mode drops the header but keeps the chart + selector (151.1 UAT)', () => {
    render(
      <MaiaHumanPanel
        selectedElo={1500}
        onEloChange={vi.fn()}
        perElo={[]}
        playedSan={null}
        bestSan={null}
        shownSans={[]}
        qualityBySan={new Map()}
        engineTopLines={[]}
        compact
      />,
    );
    expect(screen.queryByTestId('maia-human-header')).toBeNull();
    expect(screen.getByTestId('analysis-elo-selector')).toBeTruthy();
    expect(screen.getByTestId('moves-by-rating-chart')).toBeTruthy();
  });
});
