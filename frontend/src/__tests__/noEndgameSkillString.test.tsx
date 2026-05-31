// @vitest-environment jsdom
/**
 * Phase 87.4 (Plan 02, SC#8) + Phase 87.5 (Plan 02, SC#1) — RTL regression tests.
 *
 * Phase 97 D-10: EndgameMetricsSection is deleted (superseded by per-TC cards).
 * The SC#8 blocks that mounted EndgameMetricsSection are removed; the
 * EndgameEloTimelineSection regression guards (SC#1 / Phase 87.5) remain.
 *
 * Whitelist: CHANGELOG.md historical entries are excluded by test scope (we
 * mount components, not markdown content).
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';

// useEvalCoverage calls useQuery which requires a QueryClientProvider.
// Return safe defaults so the component renders without a provider.
vi.mock('@/hooks/useEvalCoverage', () => ({
  useEvalCoverage: () => ({ isPending: false, pendingCount: 0, pct: 100, totalCount: 0, isLoading: false }),
}));

import type { EndgameEloTimelineResponse } from '@/types/endgames';

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

import { EndgameEloTimelineSection } from '@/components/charts/EndgameEloTimelineSection';

function buildEmptyTimeline(): EndgameEloTimelineResponse {
  return { combos: [], timeline_window: 100 };
}

// Phase 87.5 (Plan 02 SC#1 frontend half): after the rename, the rendered
// surfaces must contain zero matches for "Conversion ELO" — chart heading,
// info popover, tooltip, and error copy all read "Endgame ELO" now. The
// per-bucket Conv/Parity/Recov gauge labels (the literal word "Conversion"
// without "ELO") are SAFE — this regression test searches for the two-word
// phrase only.
// Phase 97 D-10: EndgameMetricsSection block removed (component deleted).
describe('SC#1 (Phase 87.5) — no "Conversion ELO" string in rendered Endgames surfaces', () => {
  it('EndgameEloTimelineSection (empty state): no "Endgame Skill" in rendered output', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildEmptyTimeline()}
        isLoading={false}
        isError={false}
      />,
    );
    const rendered = (container.textContent ?? '').toLowerCase();
    expect(rendered).not.toContain('endgame skill');
  });

  it('EndgameEloTimelineSection (rendered chart): no "Conversion ELO" phrase in rendered text', () => {
    const buildPopulatedTimeline = (): EndgameEloTimelineResponse => ({
      combos: [
        {
          combo_key: 'chess_com_blitz',
          platform: 'chess.com',
          time_control: 'blitz',
          points: [
            {
              // Midpoint property: 1620 + 1540 == 2 * 1580.
              date: '2026-04-06',
              endgame_elo: 1620,
              non_endgame_elo: 1540,
              actual_elo: 1580,
              endgame_games_in_window: 50,
              per_week_endgame_games: 4,
              per_week_total_games: 16,
            },
          ],
        },
      ],
      timeline_window: 100,
    });
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildPopulatedTimeline()}
        isLoading={false}
        isError={false}
      />,
    );
    const rendered = (container.textContent ?? '').toLowerCase();
    expect(rendered).not.toContain('conversion elo');
  });

  it('EndgameEloTimelineSection (error state): "Conversion ELO" phrase absent from error copy', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={undefined}
        isLoading={false}
        isError={true}
      />,
    );
    const rendered = (container.textContent ?? '').toLowerCase();
    expect(rendered).not.toContain('conversion elo');
  });
});
