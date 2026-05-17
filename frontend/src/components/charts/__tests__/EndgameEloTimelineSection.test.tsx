// @vitest-environment jsdom
/**
 * Phase 87.5 (Plan 02 Wave 0) — Endgame ELO Timeline section render tests.
 *
 * Inverts the Phase 87.4 naming end-to-end:
 * chart heading, info popover testid + aria-label, tooltip label, error copy
 * all read "Endgame ELO". Mock data uses the renamed `endgame_elo` field.
 *
 * Initially RED — Task 2 lands the source rename (file rename + types rename +
 * per-point field rename) and Task 3 wires the consumer, so the assertions
 * below pass only after the full rename cycle completes.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import type {
  EndgameEloTimelineResponse,
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

import { EndgameEloTimelineSection } from '../EndgameEloTimelineSection';

function buildResponse(): EndgameEloTimelineResponse {
  return {
    combos: [
      {
        combo_key: 'chess_com_blitz',
        platform: 'chess.com',
        time_control: 'blitz',
        points: [
          {
            date: '2026-04-06',
            endgame_elo: 1620,
            actual_elo: 1580,
            endgame_games_in_window: 50,
            per_week_endgame_games: 4,
          },
          {
            date: '2026-04-13',
            endgame_elo: 1640,
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

describe('EndgameEloTimelineSection — rename', () => {
  it('renders the new chart heading "Endgame ELO Timeline"', () => {
    render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    expect(screen.getByText('Endgame ELO Timeline')).not.toBeNull();
  });

  it('exposes the renamed info-popover testid "endgame-elo-timeline-info"', () => {
    render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    expect(screen.queryByTestId('endgame-elo-timeline-info')).not.toBeNull();
    expect(screen.queryByTestId('conversion-elo-timeline-info')).toBeNull();
  });

  it('renders the renamed error copy when isError is true', () => {
    render(
      <EndgameEloTimelineSection
        data={undefined}
        isLoading={false}
        isError={true}
      />,
    );
    expect(screen.getByText('Failed to load Endgame ELO timeline')).not.toBeNull();
    expect(screen.queryByText(/Failed to load Conversion ELO timeline/)).toBeNull();
  });

  it('does not render any "Conversion ELO" strings in the heading or popover', () => {
    render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    // queryAllByText for any "Conversion ELO" surface — heading + info popover.
    expect(screen.queryAllByText(/Conversion ELO/i)).toHaveLength(0);
  });
});
