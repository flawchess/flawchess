// @vitest-environment jsdom
/**
 * Phase 87.5 (Plan 02 Wave 0) — Endgame ELO Timeline section render tests.
 *
 * Phase 87.6 extension: adds tests for the 3-line + signed-band layout,
 * gradient ID uniqueness, hidden-combo cleanup, and tooltip content.
 *
 * 260530-pll: replaces computeDefaultHidden tests with computeDefaultHiddenByPrimaryTc
 * tests. Default visibility is now based on the primary TC (computePrimaryTc heuristic),
 * not the old active-weeks / top-1-by-games heuristic.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, act } from '@testing-library/react';
import { cloneElement, isValidElement } from 'react';
import type { ReactElement } from 'react';

import type {
  EndgameEloTimelineResponse,
} from '@/types/endgames';

// Recharts' <ResponsiveContainer> measures its parent with ResizeObserver;
// in jsdom the parent has zero dimensions so the inner chart refuses to render.
// Swap it for a fixed-size wrapper that injects explicit width/height into the
// chart child so Recharts skips its sizing guard.
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) => (
      <div style={{ width: 800, height: 400 }}>
        {isValidElement(children)
          ? cloneElement(children as ReactElement<{ width?: number; height?: number }>, {
              width: 800,
              height: 400,
            })
          : children}
      </div>
    ),
  };
});

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

// ── Fixture helpers ────────────────────────────────────────────────────────────

/** Build a minimal combo point. */
function buildPoint(
  date: string,
  perWeekTotalGames: number,
): EndgameEloTimelineResponse['combos'][number]['points'][number] {
  return {
    date,
    endgame_elo: 1620,
    non_endgame_elo: 1600,
    actual_elo: 1610,
    endgame_games_in_window: 50,
    per_week_endgame_games: Math.floor(perWeekTotalGames / 2),
    per_week_total_games: perWeekTotalGames,
  };
}

/** Build a combo with N weeks of data. */
function buildCombo(
  combo_key: string,
  platform: 'chess.com' | 'lichess',
  time_control: 'bullet' | 'blitz' | 'rapid' | 'classical',
  weeks: number,
  perWeekGames: number,
): EndgameEloTimelineResponse['combos'][number] {
  const points = Array.from({ length: weeks }, (_, i) => {
    const base = new Date('2026-01-05T00:00:00Z');
    base.setUTCDate(base.getUTCDate() + i * 7);
    return buildPoint(base.toISOString().slice(0, 10), perWeekGames);
  });
  return { combo_key, platform, time_control, points };
}

function buildResponse(): EndgameEloTimelineResponse {
  // chess_com_blitz: 2 weeks * 18 games = 36 total, weight = 36 * 180 = 6480
  // lichess_rapid:   3 weeks * 20 games = 60 total, weight = 60 * 600 = 36000 (PRIMARY)
  return {
    combos: [
      buildCombo('chess_com_blitz', 'chess.com', 'blitz', 2, 18),
      buildCombo('lichess_rapid', 'lichess', 'rapid', 3, 20),
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
    expect(screen.queryAllByText(/Conversion ELO/i)).toHaveLength(0);
  });
});

describe('EndgameEloTimelineSection — 3-line + signed-band layout', () => {
  // buildResponse() has 2 combos: chess_com_blitz and lichess_rapid.
  // lichess_rapid is the primary TC (60 total * 600 weight = 36000 > 36 * 180 = 6480).
  // With primary-TC visibility, only lichess_rapid combos are visible on initial render.

  it('renders 3 Line elements for the single default-visible combo (recharts-line-curve class)', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const lineCurves = container.querySelectorAll('.recharts-line-curve');
    // 1 visible combo (lichess_rapid) × 3 lines = 3 (chess_com_blitz is hidden)
    expect(lineCurves.length).toBe(3);
  });

  it('renders 1 Area element for the single default-visible combo (recharts-area-area class)', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const areas = container.querySelectorAll('.recharts-area-area');
    // 1 visible combo × 1 area = 1
    expect(areas.length).toBe(1);
  });

  it('renders Endgame ELO as dashed and Non-Endgame ELO as dotted (UAT 87.6 2026-05-17)', () => {
    // Per UAT feedback: use dashed lines for Endgame ELO and dotted lines for
    // Non-Endgame ELO so the two PR lines are distinguishable from each other
    // and from the bold solid Actual ELO line at a glance. Phase 87.5's "no
    // dashed line" rule is rescinded.
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const dashedPaths = container.querySelectorAll(
      '.recharts-line-curve[stroke-dasharray]:not([stroke-dasharray=""])',
    );
    // 1 visible combo × (1 dashed Endgame + 1 dotted Non-Endgame) = 2 dash-arrayed lines.
    // The solid Actual ELO line carries no stroke-dasharray.
    expect(dashedPaths.length).toBe(2);
    const patterns = new Set(
      Array.from(dashedPaths).map((p) => p.getAttribute('stroke-dasharray')),
    );
    // Two distinct dash patterns — one dashed, one dotted.
    expect(patterns.size).toBe(2);
  });

  it('renders the chart container', () => {
    render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    expect(screen.getByTestId('endgame-elo-timeline-chart')).not.toBeNull();
  });

  it('reveals hidden combo elements when its legend button is clicked', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );

    // Initially: 1 visible (lichess_rapid = primary TC) × 3 lines = 3; 1 area.
    const beforeLines = container.querySelectorAll('.recharts-line-curve');
    const beforeAreas = container.querySelectorAll('.recharts-area-area');
    expect(beforeLines.length).toBe(3);
    expect(beforeAreas.length).toBe(1);

    // Click the legend button for the hidden chess_com_blitz to show it.
    const legendBtn = screen.getByTestId('endgame-elo-legend-chess_com_blitz');
    fireEvent.click(legendBtn);

    // After revealing one combo: visible = 2 combos × 3 lines = 6; 2 areas.
    const afterLines = container.querySelectorAll('.recharts-line-curve');
    const afterAreas = container.querySelectorAll('.recharts-area-area');
    expect(afterLines.length).toBe(6);
    expect(afterAreas.length).toBe(2);
  });

  it('legend button reflects hidden state via aria-pressed and opacity class', () => {
    render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );

    // chess_com_blitz is hidden (not the primary TC).
    const legendBtn = screen.getByTestId('endgame-elo-legend-chess_com_blitz');
    expect(legendBtn.getAttribute('aria-pressed')).toBe('false');
    expect(legendBtn.className).toContain('opacity-50');

    // Click to reveal — aria-pressed becomes true, opacity class removed.
    fireEvent.click(legendBtn);
    expect(legendBtn.getAttribute('aria-pressed')).toBe('true');
    expect(legendBtn.className).not.toContain('opacity-50');
  });
});

describe('EndgameEloTimelineSection — gradient ID uniqueness', () => {
  it('renders one <linearGradient> per combo with unique IDs', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const gradients = container.querySelectorAll('linearGradient');
    // 2 combos → 2 gradients
    expect(gradients.length).toBe(2);
    // All IDs are unique
    const ids = Array.from(gradients).map((g) => g.getAttribute('id') ?? '');
    expect(new Set(ids).size).toBe(2);
  });

  it('gradient IDs include the combo_key for disambiguation', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const gradients = Array.from(container.querySelectorAll('linearGradient'));
    const ids = gradients.map((g) => g.getAttribute('id') ?? '');
    // Each gradient ID should contain the combo_key
    expect(ids.some((id) => id.includes('chess_com_blitz'))).toBe(true);
    expect(ids.some((id) => id.includes('lichess_rapid'))).toBe(true);
  });

  it('gradient IDs use the endgame-elo-band prefix', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const gradients = Array.from(container.querySelectorAll('linearGradient'));
    const ids = gradients.map((g) => g.getAttribute('id') ?? '');
    expect(ids.every((id) => id.startsWith('endgame-elo-band-'))).toBe(true);
  });
});

// ── 260530-pll: primary-TC default visibility tests ───────────────────────────
// These replace the old computeDefaultHidden (active-weeks/top-1-by-games)
// tests. The new heuristic uses computePrimaryTc via computeDefaultHiddenByPrimaryTc.

describe('EndgameEloTimelineSection — primary-TC default visibility (260530-pll)', () => {
  it('shows primary-TC combo visible and non-primary hidden by default', () => {
    // rapid is primary (60 * 600 = 36000 weight) vs blitz (36 * 180 = 6480).
    render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    // lichess_rapid (primary) is visible
    expect(
      screen.getByTestId('endgame-elo-legend-lichess_rapid').getAttribute('aria-pressed'),
    ).toBe('true');
    // chess_com_blitz (non-primary) is hidden
    expect(
      screen.getByTestId('endgame-elo-legend-chess_com_blitz').getAttribute('aria-pressed'),
    ).toBe('false');
  });

  it('shows BOTH platform combos when primary TC was played on both chess.com and lichess', () => {
    // Both chess_com_rapid and lichess_rapid qualify: 50 * 600 = 30000 each.
    // blitz: 30 * 180 = 5400 — not primary.
    const data: EndgameEloTimelineResponse = {
      combos: [
        buildCombo('chess_com_rapid', 'chess.com', 'rapid', 5, 10),   // 50 * 600 = 30000
        buildCombo('lichess_rapid', 'lichess', 'rapid', 5, 10),        // 50 * 600 = 30000
        buildCombo('chess_com_blitz', 'chess.com', 'blitz', 5, 6),    // 30 * 180 = 5400
      ],
      timeline_window: 100,
    };
    render(
      <EndgameEloTimelineSection data={data} isLoading={false} isError={false} />,
    );
    // Both rapid combos are visible (primary TC = rapid, both platforms).
    expect(
      screen.getByTestId('endgame-elo-legend-chess_com_rapid').getAttribute('aria-pressed'),
    ).toBe('true');
    expect(
      screen.getByTestId('endgame-elo-legend-lichess_rapid').getAttribute('aria-pressed'),
    ).toBe('true');
    // Blitz combo is hidden.
    expect(
      screen.getByTestId('endgame-elo-legend-chess_com_blitz').getAttribute('aria-pressed'),
    ).toBe('false');
    // 2 visible combos × 3 lines = 6.
    const { container } = render(
      <EndgameEloTimelineSection data={data} isLoading={false} isError={false} />,
    );
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(6);
  });

  it('keeps hidden combos in the legend, clickable to re-show', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    // Only primary (lichess_rapid) visible: 3 lines.
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(3);
    // Click the dimmed legend item.
    const dimmedBtn = screen.getByTestId('endgame-elo-legend-chess_com_blitz');
    expect(dimmedBtn.className).toContain('opacity-50');
    fireEvent.click(dimmedBtn);
    // Now both visible: 6 lines.
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(6);
  });

  it('shows nothing hidden when only one combo exists', () => {
    const data: EndgameEloTimelineResponse = {
      combos: [buildCombo('chess_com_rapid', 'chess.com', 'rapid', 5, 10)],
      timeline_window: 100,
    };
    const { container } = render(
      <EndgameEloTimelineSection data={data} isLoading={false} isError={false} />,
    );
    // 1 combo × 3 lines = 3; the single legend entry is visible.
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(3);
    const legendBtn = screen.getByTestId('endgame-elo-legend-chess_com_rapid');
    expect(legendBtn.getAttribute('aria-pressed')).toBe('true');
    expect(legendBtn.className).not.toContain('opacity-50');
  });
});

describe('gap annotations', () => {
  // A response where two points are more than 90 days apart.
  function buildResponseWithGap(): EndgameEloTimelineResponse {
    return {
      combos: [
        {
          combo_key: 'chess_com_blitz',
          platform: 'chess.com',
          time_control: 'blitz',
          points: [
            {
              date: '2025-01-06',
              endgame_elo: 1620,
              non_endgame_elo: 1600,
              actual_elo: 1610,
              endgame_games_in_window: 50,
              per_week_endgame_games: 4,
              per_week_total_games: 18,
            },
            {
              // 120 days later — exceeds the 90-day threshold
              date: '2025-05-06',
              endgame_elo: 1640,
              non_endgame_elo: 1610,
              actual_elo: 1625,
              endgame_games_in_window: 55,
              per_week_endgame_games: 5,
              per_week_total_games: 22,
            },
          ],
        },
      ],
      timeline_window: 100,
    };
  }

  it('renders inactivity-gap-label testid when allDates contains a >90-day gap', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponseWithGap()}
        isLoading={false}
        isError={false}
      />,
    );
    // The shared helper renders data-testid="inactivity-gap-label" for each gap.
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).not.toBeNull();
  });

  it('renders inactivity-gap-glyph (Palmtree) when allDates contains a >90-day gap', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponseWithGap()}
        isLoading={false}
        isError={false}
      />,
    );
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).not.toBeNull();
  });

  it('renders no inactivity-gap annotation when all dates are 7 days apart', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}  // buildResponse dates are 7 days apart
        isLoading={false}
        isError={false}
      />,
    );
    expect(container.querySelector('[data-testid="inactivity-gap-label"]')).toBeNull();
    expect(container.querySelector('[data-testid="inactivity-gap-glyph"]')).toBeNull();
  });
});

describe('EndgameEloTimelineSection — info popover content', () => {
  it('info popover names the endgame vs non-endgame lines', async () => {
    render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const trigger = screen.getByTestId('endgame-elo-timeline-info');
    await act(async () => {
      fireEvent.pointerDown(trigger, { button: 0, pointerType: 'mouse' });
      fireEvent.mouseDown(trigger, { button: 0 });
      fireEvent.click(trigger);
    });
    expect(
      await screen.findByText(/your Endgame ELO/i),
    ).not.toBeNull();
  });

  it('info popover names the green-lift / red-drag sign convention', async () => {
    render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const trigger = screen.getByTestId('endgame-elo-timeline-info');
    await act(async () => {
      fireEvent.pointerDown(trigger, { button: 0, pointerType: 'mouse' });
      fireEvent.mouseDown(trigger, { button: 0 });
      fireEvent.click(trigger);
    });
    expect(
      await screen.findByText(/lift \(green\) or drag \(red\)/i),
    ).not.toBeNull();
  });
});
