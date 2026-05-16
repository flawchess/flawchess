// @vitest-environment jsdom
/**
 * Phase 87.4 (Plan 02 Wave 0) — Conversion ELO Timeline section render tests.
 *
 * Replaces the implicit "Endgame ELO Timeline" naming end-to-end:
 * chart heading, info popover testid + aria-label, tooltip label, error copy.
 * Mock data uses the renamed conversion_elo field on each point.
 *
 * Initially RED — Task 4 lands the source rename to satisfy these tests.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import type {
  ConversionEloTimelineResponse,
} from '@/types/endgames';

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
});

import { ConversionEloTimelineSection } from '../ConversionEloTimelineSection';

function buildResponse(): ConversionEloTimelineResponse {
  return {
    combos: [
      {
        combo_key: 'chess_com_blitz',
        platform: 'chess.com',
        time_control: 'blitz',
        points: [
          {
            date: '2026-04-06',
            conversion_elo: 1620,
            actual_elo: 1580,
            endgame_games_in_window: 50,
            per_week_endgame_games: 4,
          },
          {
            date: '2026-04-13',
            conversion_elo: 1640,
            actual_elo: 1590,
            endgame_games_in_window: 55,
            per_week_endgame_games: 5,
          },
        ],
      },
    ],
    timeline_window: 100,
  };
}

describe('ConversionEloTimelineSection — rename', () => {
  it('renders the new chart heading "Conversion ELO Timeline"', () => {
    render(
      <ConversionEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    expect(screen.getByText('Conversion ELO Timeline')).not.toBeNull();
  });

  it('exposes the renamed info-popover testid "conversion-elo-timeline-info"', () => {
    render(
      <ConversionEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    expect(screen.queryByTestId('conversion-elo-timeline-info')).not.toBeNull();
    expect(screen.queryByTestId('endgame-elo-timeline-info')).toBeNull();
  });

  it('renders the renamed error copy when isError is true', () => {
    render(
      <ConversionEloTimelineSection
        data={undefined}
        isLoading={false}
        isError={true}
      />,
    );
    expect(screen.getByText('Failed to load Conversion ELO timeline')).not.toBeNull();
    expect(screen.queryByText(/Failed to load Endgame ELO timeline/)).toBeNull();
  });

  it('does not render any "Endgame ELO" strings in the heading or popover', () => {
    render(
      <ConversionEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    // queryAllByText for both literal forms — heading + info popover surfaces.
    expect(screen.queryAllByText(/Endgame ELO Timeline/i)).toHaveLength(0);
  });
});
