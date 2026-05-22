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
  // buildResponse() has 2 combos: chess_com_blitz (2 pts, 40 total games) and
  // lichess_rapid (3 pts, 60 total games). With MAX_DEFAULT_VISIBLE=1, only
  // lichess_rapid (more total games) is visible on initial render.

  it('renders 3 Line elements for the single default-visible combo (recharts-line-curve class)', () => {
    const { container } = render(
      <EndgameEloTimelineSection
        data={buildResponse()}
        isLoading={false}
        isError={false}
      />,
    );
    const lineCurves = container.querySelectorAll('.recharts-line-curve');
    // 1 visible combo × 3 lines = 3 (chess_com_blitz is hidden by default)
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

    // Initially: 1 visible (lichess_rapid) × 3 lines = 3 curves; 1 area.
    // chess_com_blitz is hidden by default (less total games).
    const beforeLines = container.querySelectorAll('.recharts-line-curve');
    const beforeAreas = container.querySelectorAll('.recharts-area-area');
    expect(beforeLines.length).toBe(3);
    expect(beforeAreas.length).toBe(1);

    // Click the legend button for the hidden chess_com_blitz to show it
    const legendBtn = screen.getByTestId('endgame-elo-legend-chess_com_blitz');
    fireEvent.click(legendBtn);

    // After revealing one combo: visible = 2 combos × 3 lines = 6; 2 areas
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

    // chess_com_blitz starts hidden (less total games than lichess_rapid)
    const legendBtn = screen.getByTestId('endgame-elo-legend-chess_com_blitz');
    expect(legendBtn.getAttribute('aria-pressed')).toBe('false');
    expect(legendBtn.className).toContain('opacity-50');

    // Click to reveal — aria-pressed becomes true, opacity class removed
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

  it('caps default-visible combos to 1 when more qualify', () => {
    // 5 combos, all identical 20 active weeks (no filter trims) → expect
    // exactly 1 visible (top by total games), 4 hidden.
    const combos = ALL_KEYS.slice(0, 5).map((k, i) =>
      // Decreasing per-week games so rank is deterministic.
      buildCombo(k, 20, 30 - i * 4),
    );
    const data: EndgameEloTimelineResponse = { combos, timeline_window: 100 };
    const { container } = render(
      <EndgameEloTimelineSection data={data} isLoading={false} isError={false} />,
    );
    // 1 visible × 3 lines each = 3
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(3);
    // Legend still shows all 5
    for (const k of ALL_KEYS.slice(0, 5)) {
      expect(screen.getByTestId(`endgame-elo-legend-${k}`)).not.toBeNull();
    }
    // Top 1 (highest per-week-games) is aria-pressed=true; rest are false
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS[0]}`).getAttribute('aria-pressed'),
    ).toBe('true');
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS[1]}`).getAttribute('aria-pressed'),
    ).toBe('false');
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS[3]}`).getAttribute('aria-pressed'),
    ).toBe('false');
  });

  it('hides combos whose active weeks fall below 33% of the leader', () => {
    // Leader: 30 active weeks. Threshold: 9.9 weeks.
    //   combo A: 30 weeks (keep — but cap=1 shows only A)
    //   combo B: 20 weeks (pass ratio, but hidden by MAX_DEFAULT_VISIBLE=1 cap)
    //   combo C:  3 weeks (HIDE — sparse stray, below active-weeks threshold)
    const combos = [
      buildCombo(ALL_KEYS[0], 30, 25),
      buildCombo(ALL_KEYS[1], 20, 25),
      buildCombo(ALL_KEYS[2], 3, 25),
    ];
    const data: EndgameEloTimelineResponse = { combos, timeline_window: 100 };
    const { container } = render(
      <EndgameEloTimelineSection data={data} isLoading={false} isError={false} />,
    );
    // 1 visible (cap=1 keeps only the top ranked A) × 3 lines = 3
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(3);
    // Sparse stray (C) is hidden
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS[2]}`).getAttribute('aria-pressed'),
    ).toBe('false');
    // B is also hidden (cap bite, not ratio filter)
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS[1]}`).getAttribute('aria-pressed'),
    ).toBe('false');
    // A is visible (leader)
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS[0]}`).getAttribute('aria-pressed'),
    ).toBe('true');
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

describe('MAX_DEFAULT_VISIBLE = 1', () => {
  // Helper used by both cases: builds a response with N combos, each with a
  // configurable (activeWeeks, perWeekGames) profile. combo_keys cycle from
  // ALL_KEYS so testids are deterministic.
  const ALL_KEYS_MDV = [
    'chess_com_bullet',
    'chess_com_blitz',
    'chess_com_rapid',
    'chess_com_classical',
    'lichess_bullet',
    'lichess_blitz',
    'lichess_rapid',
    'lichess_classical',
  ] as const;

  function buildMdvCombo(
    combo_key: (typeof ALL_KEYS_MDV)[number],
    activeWeeks: number,
    perWeekGames: number,
  ): EndgameEloTimelineResponse['combos'][number] {
    const points = Array.from({ length: activeWeeks }, (_, i) => {
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

  it('(a) 3-combo payload: only the most-active combo is visible; the other two are hidden', () => {
    // Combo A: 20 active weeks, 30 per-week games → highest total (600)
    // Combo B: 20 active weeks, 20 per-week games → total 400
    // Combo C: 20 active weeks, 10 per-week games → total 200
    // MAX_DEFAULT_VISIBLE=1: only A is visible on first render.
    const combos = [
      buildMdvCombo(ALL_KEYS_MDV[0], 20, 30), // A — most-active
      buildMdvCombo(ALL_KEYS_MDV[1], 20, 20), // B
      buildMdvCombo(ALL_KEYS_MDV[2], 20, 10), // C
    ];
    const data: EndgameEloTimelineResponse = { combos, timeline_window: 100 };
    const { container } = render(
      <EndgameEloTimelineSection data={data} isLoading={false} isError={false} />,
    );
    // 1 visible × 3 lines = 3
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(3);
    // Most-active (A) is visible
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS_MDV[0]}`).getAttribute('aria-pressed'),
    ).toBe('true');
    // Less-active combos are hidden
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS_MDV[1]}`).getAttribute('aria-pressed'),
    ).toBe('false');
    expect(
      screen.getByTestId(`endgame-elo-legend-${ALL_KEYS_MDV[2]}`).getAttribute('aria-pressed'),
    ).toBe('false');
    // All 3 legend entries are still shown (togglable)
    for (const k of [ALL_KEYS_MDV[0], ALL_KEYS_MDV[1], ALL_KEYS_MDV[2]]) {
      expect(screen.getByTestId(`endgame-elo-legend-${k}`)).not.toBeNull();
    }
  });

  it('(b) 1-combo payload: nothing is hidden (single-series auto-behaviour unchanged)', () => {
    // With only 1 combo, ranked.slice(0, 1) = [that combo], hidden = {}.
    const combos = [buildMdvCombo(ALL_KEYS_MDV[0], 10, 20)];
    const data: EndgameEloTimelineResponse = { combos, timeline_window: 100 };
    const { container } = render(
      <EndgameEloTimelineSection data={data} isLoading={false} isError={false} />,
    );
    // 1 combo × 3 lines = 3
    expect(container.querySelectorAll('.recharts-line-curve').length).toBe(3);
    // The single legend entry is visible (not dimmed)
    const legendBtn = screen.getByTestId(`endgame-elo-legend-${ALL_KEYS_MDV[0]}`);
    expect(legendBtn.getAttribute('aria-pressed')).toBe('true');
    expect(legendBtn.className).not.toContain('opacity-50');
  });
});

describe('gap annotations', () => {
  // A response where two points are more than 56 days apart.
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
              // 90 days later — exceeds the 56-day threshold
              date: '2025-04-06',
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

  it('renders inactivity-gap-label testid when allDates contains a >56-day gap', () => {
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

  it('renders inactivity-gap-glyph (Palmtree) when allDates contains a >56-day gap', () => {
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
