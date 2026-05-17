// @vitest-environment jsdom
/**
 * Phase 87.5 (Plan 02 Wave 0) — Endgame ELO Timeline section render tests.
 *
 * Phase 87.6 extension: adds tests for the 3-line + signed-band layout,
 * gradient ID uniqueness, hidden-combo cleanup, and tooltip content.
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

function buildResponse(): EndgameEloTimelineResponse {
  return {
    combos: [
      {
        combo_key: 'chess_com_blitz',
        platform: 'chess.com',
        time_control: 'blitz',
        points: [
          {
            // Endgame leads; midpoint property: 1620 + 1600 == 2 * 1610.
            date: '2026-04-06',
            endgame_elo: 1620,
            non_endgame_elo: 1600,
            actual_elo: 1610,
            endgame_games_in_window: 50,
            per_week_endgame_games: 4,
            per_week_total_games: 18,
          },
          {
            // Endgame leads; midpoint property: 1640 + 1610 == 2 * 1625.
            date: '2026-04-13',
            endgame_elo: 1640,
            non_endgame_elo: 1610,
            actual_elo: 1625,
            endgame_games_in_window: 55,
            per_week_endgame_games: 5,
            per_week_total_games: 22,
          },
        ],
      },
      {
        combo_key: 'lichess_rapid',
        platform: 'lichess',
        time_control: 'rapid',
        points: [
          {
            // Endgame leads (green band)
            date: '2026-04-06',
            endgame_elo: 1700,
            non_endgame_elo: 1650,
            actual_elo: 1675,
            endgame_games_in_window: 50,
            per_week_endgame_games: 4,
            per_week_total_games: 16,
          },
          {
            // Endgame trails (red band — crossover)
            date: '2026-04-13',
            endgame_elo: 1700,
            non_endgame_elo: 1750,
            actual_elo: 1725,
            endgame_games_in_window: 55,
            per_week_endgame_games: 5,
            per_week_total_games: 20,
          },
          {
            // Endgame leads again (crossover back)
            date: '2026-04-20',
            endgame_elo: 1750,
            non_endgame_elo: 1700,
            actual_elo: 1725,
            endgame_games_in_window: 60,
            per_week_endgame_games: 6,
            per_week_total_games: 24,
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
    expect(screen.queryAllByText(/Conversion ELO/i)).toHaveLength(0);
  });
});

describe('EndgameEloTimelineSection — 3-line + signed-band layout', () => {
  it('renders 3 Line elements per visible combo (recharts-line-curve class)', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const lineCurves = container.querySelectorAll('.recharts-line-curve');
    // 2 combos × 3 lines = 6
    expect(lineCurves.length).toBe(6);
  });

  it('renders 1 Area element per visible combo (recharts-area-area class)', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const areas = container.querySelectorAll('.recharts-area-area');
    // 2 combos × 1 area = 2
    expect(areas.length).toBe(2);
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
    // 2 combos × (1 dashed Endgame + 1 dotted Non-Endgame) = 4 dash-arrayed lines.
    // The solid Actual ELO line carries no stroke-dasharray.
    expect(dashedPaths.length).toBe(4);
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

  it('hides all 4 per-combo elements when the combo legend is clicked', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );

    // Initially: 2 combos × 3 lines = 6 curves; 2 combos × 1 area = 2 areas
    const beforeLines = container.querySelectorAll('.recharts-line-curve');
    const beforeAreas = container.querySelectorAll('.recharts-area-area');
    expect(beforeLines.length).toBe(6);
    expect(beforeAreas.length).toBe(2);

    // Click the legend button for chess_com_blitz to hide it
    const legendBtn = screen.getByTestId('endgame-elo-legend-chess_com_blitz');
    fireEvent.click(legendBtn);

    // After hiding one combo: visible = 1 combo × 3 lines = 3; 1 area
    const afterLines = container.querySelectorAll('.recharts-line-curve');
    const afterAreas = container.querySelectorAll('.recharts-area-area');
    expect(afterLines.length).toBe(3);
    expect(afterAreas.length).toBe(1);
  });

  it('legend button reflects hidden state via aria-pressed and opacity class', () => {
    render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );

    const legendBtn = screen.getByTestId('endgame-elo-legend-chess_com_blitz');
    expect(legendBtn.getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(legendBtn);
    expect(legendBtn.getAttribute('aria-pressed')).toBe('false');
    expect(legendBtn.className).toContain('opacity-50');
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

describe('EndgameEloTimelineSection — default-hidden filter (Phase 87.6 amendment)', () => {
  // Builds a response with `count` combos, each carrying a configurable
  // (active_weeks, per_week_games) profile. combo_keys cycle through the 8
  // valid EloComboKey values so legend testids are deterministic.
  const ALL_KEYS = [
    'chess_com_bullet',
    'chess_com_blitz',
    'chess_com_rapid',
    'chess_com_classical',
    'lichess_bullet',
    'lichess_blitz',
    'lichess_rapid',
    'lichess_classical',
  ] as const;

  function buildCombo(
    combo_key: (typeof ALL_KEYS)[number],
    activeWeeks: number,
    perWeekGames: number,
  ): EndgameEloTimelineResponse['combos'][number] {
    const points = Array.from({ length: activeWeeks }, (_, i) => {
      // Monday dates spaced 7 days apart starting 2026-01-05.
      const base = new Date('2026-01-05T00:00:00Z');
      base.setUTCDate(base.getUTCDate() + i * 7);
      const date = base.toISOString().slice(0, 10);
      return {
        date,
        endgame_elo: 1600,
        non_endgame_elo: 1580,
        actual_elo: 1590,
        endgame_games_in_window: 50,
        per_week_endgame_games: Math.floor(perWeekGames / 2),
        per_week_total_games: perWeekGames,
      };
    });
    const [platform, ...tcParts] = combo_key.split('_');
    const platformLabel = platform === 'chess' ? 'chess.com' : 'lichess';
    const tc = (platform === 'chess' ? tcParts.slice(1) : tcParts).join('_');
    return {
      combo_key,
      platform: platformLabel as 'chess.com' | 'lichess',
      time_control: tc as 'bullet' | 'blitz' | 'rapid' | 'classical',
      points,
    };
  }

  it('caps default-visible combos to 3 when more qualify', () => {
    // 5 combos, all identical 20 active weeks (no filter trims) → expect
    // exactly 3 visible (top by total games), 2 hidden.
    const combos = ALL_KEYS.slice(0, 5).map((k, i) =>
      // Decreasing per-week games so rank is deterministic.
      buildCombo(k, 20, 30 - i * 4),
    );
    const data: EndgameEloTimelineResponse = { combos, timeline_window: 100 };
    const { container } = render(
      <EndgameEloTimelineSection data={data} isLoading={false} isError={false} />,
    );
    // 3 visible × 3 lines each = 9
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(9);
    // Legend still shows all 5
    for (const k of ALL_KEYS.slice(0, 5)) {
      expect(screen.getByTestId(`endgame-elo-legend-${k}`)).not.toBeNull();
    }
    // Top 3 (highest per-week-games) are aria-pressed=true; last 2 are false
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS[0]}`).getAttribute('aria-pressed'),
    ).toBe('true');
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS[3]}`).getAttribute('aria-pressed'),
    ).toBe('false');
  });

  it('hides combos whose active weeks fall below 33% of the leader', () => {
    // Leader: 30 active weeks. Threshold: 9.9 weeks.
    //   combo A: 30 weeks (keep)
    //   combo B: 20 weeks (keep — passes ratio)
    //   combo C:  3 weeks (HIDE — sparse stray)
    // Only 3 combos so top-3 cap doesn't bite; only the active-weeks filter does.
    const combos = [
      buildCombo(ALL_KEYS[0], 30, 25),
      buildCombo(ALL_KEYS[1], 20, 25),
      buildCombo(ALL_KEYS[2], 3, 25),
    ];
    const data: EndgameEloTimelineResponse = { combos, timeline_window: 100 };
    const { container } = render(
      <EndgameEloTimelineSection data={data} isLoading={false} isError={false} />,
    );
    // 2 visible × 3 lines = 6
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(6);
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS[2]}`).getAttribute('aria-pressed'),
    ).toBe('false');
  });

  it('keeps a hidden combo in the legend, clickable to re-show', () => {
    const combos = [
      buildCombo(ALL_KEYS[0], 30, 25),
      buildCombo(ALL_KEYS[1], 3, 25),
    ];
    const data: EndgameEloTimelineResponse = { combos, timeline_window: 100 };
    const { container } = render(
      <EndgameEloTimelineSection data={data} isLoading={false} isError={false} />,
    );
    // Only leader is visible: 3 lines
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(3);
    // Click the dimmed legend item — it should activate.
    const dimmedBtn = screen.getByTestId(`endgame-elo-legend-${ALL_KEYS[1]}`);
    expect(dimmedBtn.className).toContain('opacity-50');
    fireEvent.click(dimmedBtn);
    // Now both visible: 6 lines
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(6);
  });
});

describe('EndgameEloTimelineSection — info popover content', () => {
  it('info popover frames the band symmetrically around Actual ELO', async () => {
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
      await screen.findByText(/symmetrically around your/i),
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
