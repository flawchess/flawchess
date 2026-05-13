// @vitest-environment jsdom
/**
 * Phase 85 Plan 03: tests for EndgameGamesWithWithoutSection.
 *
 * Covers:
 * - Layout: section h3 + both card titles + footer h3 render.
 * - Math: per-card chess-score matches (W + 0.5·D)/n on both sides.
 * - Footer gap formatting: signed percentage with explicit '+' prefix
 *   when positive, '-' prefix when negative.
 * - Empty state: per-card 'Not enough data yet' copy when wdl.total === 0.
 * - Sig gating: low-n suppresses zone font color on the score value;
 *   sufficient n + non-null p < 0.05 + outside neutral band paints
 *   the score with the zone color.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';

import { ZONE_SUCCESS } from '@/lib/theme';
import type {
  EndgamePerformanceResponse,
  EndgameWDLSummary,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

// Spy on MiniBulletChart so we do not render its recharts internals under
// jsdom; keeps the test focused on prop-driven behavior rather than the
// chart primitive's DOM.
vi.mock('@/components/charts/MiniBulletChart', () => ({
  MiniBulletChart: vi.fn(
    (props: Record<string, unknown>) => (
      <div
        data-testid="mock-mini-bullet"
        data-domain={String(props.domain)}
        data-center={String(props.center)}
      />
    ),
  ),
}));

// jsdom ships without matchMedia / ResizeObserver; the InfoPopover nested
// inside the section indirectly touches matchMedia via radix's portal.
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

import { EndgameGamesWithWithoutSection } from '../EndgameGamesWithWithoutSection';

// jsdom normalizes oklch trailing zeros ('0.50' → '0.5') when reading
// element.style.color back. Compare on a normalized form so the assertions
// are robust to jsdom's cosmetic rewrite without weakening the contract.
function normalizeColor(value: string): string {
  return value.replace(/(\d+)\.(\d*?)0+(?=\D|$)/g, (match, intPart: string, frac: string) => {
    if (frac === '') return `${intPart}`;
    return `${intPart}.${frac}`;
  });
}

function buildWdl(
  wins: number,
  draws: number,
  losses: number,
  total = wins + draws + losses,
): EndgameWDLSummary {
  const safeTotal = total === 0 ? 1 : total;
  return {
    wins,
    draws,
    losses,
    total,
    win_pct: (wins / safeTotal) * 100,
    draw_pct: (draws / safeTotal) * 100,
    loss_pct: (losses / safeTotal) * 100,
  };
}

function makeData(
  overrides?: Partial<EndgamePerformanceResponse>,
): EndgamePerformanceResponse {
  return {
    endgame_wdl: buildWdl(25, 10, 15),
    non_endgame_wdl: buildWdl(20, 8, 12),
    endgame_win_rate: 0.5,
    entry_eval_mean_pawns: 0,
    entry_eval_n: 0,
    entry_eval_p_value: null,
    endgame_score_p_value: null,
    non_endgame_score_p_value: null,
    entry_eval_ci_low_pawns: null,
    entry_eval_ci_high_pawns: null,
    entry_expected_score: 0.5,
    entry_expected_score_n: 0,
    entry_expected_score_p_value: null,
    entry_expected_score_ci_low: null,
    entry_expected_score_ci_high: null,
    ...overrides,
  };
}

function makeScoreGap(
  overrides?: Partial<ScoreGapMaterialResponse>,
): ScoreGapMaterialResponse {
  return {
    endgame_score: 0.5,
    non_endgame_score: 0.5,
    score_difference: 0,
    material_rows: [],
    timeline: [],
    timeline_window: 100,
    ...overrides,
  };
}

describe('EndgameGamesWithWithoutSection', () => {
  it('renders both card titles, section header, and footer gap title', () => {
    render(
      <EndgameGamesWithWithoutSection data={makeData()} scoreGap={makeScoreGap()} />,
    );
    expect(screen.getByTestId('endgame-games-with-without-section')).toBeTruthy();
    expect(screen.getByTestId('tile-games-without-endgame')).toBeTruthy();
    expect(screen.getByTestId('tile-games-with-endgame')).toBeTruthy();
    expect(screen.getByTestId('score-gap-footer')).toBeTruthy();
    // Section h3 (occurs in document; just assert text presence).
    expect(screen.getByText(/Games with vs without Endgame/i)).toBeTruthy();
    expect(screen.getByText(/Games without Endgame/i)).toBeTruthy();
    expect(screen.getByText(/^Games with Endgame$/i)).toBeTruthy();
    expect(screen.getByText(/Score Gap \(Yes − No\)/i)).toBeTruthy();
  });

  it('per-card score percentage matches (W + 0.5·D)/n', () => {
    render(
      <EndgameGamesWithWithoutSection
        data={makeData({
          // 100% score: 10 wins, 0 draws, 0 losses
          non_endgame_wdl: buildWdl(10, 0, 0),
          // 50% score: 5 wins, 0 draws, 5 losses
          endgame_wdl: buildWdl(5, 0, 5),
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    const left = within(screen.getByTestId('tile-games-without-endgame'));
    const right = within(screen.getByTestId('tile-games-with-endgame'));
    expect(left.getByTestId('score-value-no').textContent).toBe('100%');
    expect(right.getByTestId('score-value-yes').textContent).toBe('50%');
  });

  it('footer gap shows signed score_difference with explicit + or - prefix', () => {
    const { rerender } = render(
      <EndgameGamesWithWithoutSection
        data={makeData()}
        scoreGap={makeScoreGap({ score_difference: 0.07 })}
      />,
    );
    expect(screen.getByTestId('score-gap-difference').textContent).toBe('+7%');

    rerender(
      <EndgameGamesWithWithoutSection
        data={makeData()}
        scoreGap={makeScoreGap({ score_difference: -0.12 })}
      />,
    );
    expect(screen.getByTestId('score-gap-difference').textContent).toBe('-12%');
  });

  it('renders "Not enough data yet" inside the left tile when non_endgame_wdl.total === 0', () => {
    render(
      <EndgameGamesWithWithoutSection
        data={makeData({
          non_endgame_wdl: buildWdl(0, 0, 0, 0),
          // Keep right side intact
          endgame_wdl: buildWdl(20, 8, 12),
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    const left = within(screen.getByTestId('tile-games-without-endgame'));
    expect(left.getByText(/Not enough data yet/i)).toBeTruthy();
    expect(left.queryByTestId('score-value-no')).toBeNull();
    // Right tile unaffected
    const right = within(screen.getByTestId('tile-games-with-endgame'));
    expect(right.queryByTestId('score-value-yes')).toBeTruthy();
  });

  it(
    'score-value-yes has NO inline color when total >= 10 but p-value > 0.05 ' +
      '(sig gating: low confidence suppresses zone font color)',
    () => {
      render(
        <EndgameGamesWithWithoutSection
          data={makeData({
            // 90% score (far outside [0.45, 0.55] neutral band) but not sig
            endgame_wdl: buildWdl(9, 0, 1),
            endgame_score_p_value: 0.20,
          })}
          scoreGap={makeScoreGap()}
        />,
      );
      const valueSpan = within(screen.getByTestId('tile-games-with-endgame')).getByTestId(
        'score-value-yes',
      );
      expect(valueSpan.style.color).toBe('');
    },
  );

  it(
    'score-value-yes also has NO inline color when total < MIN_GAMES_FOR_RELIABLE_STATS ' +
      '(score row falls into empty-state branch)',
    () => {
      render(
        <EndgameGamesWithWithoutSection
          data={makeData({
            // total = 5, below the n >= 10 floor → score row hidden entirely
            endgame_wdl: buildWdl(3, 0, 2),
            endgame_score_p_value: null,
          })}
          scoreGap={makeScoreGap()}
        />,
      );
      const right = within(screen.getByTestId('tile-games-with-endgame'));
      // Score row hidden; value testid absent.
      expect(right.queryByTestId('score-value-yes')).toBeNull();
      // Empty-state copy rendered in its place.
      expect(right.getByText(/Not enough data yet/i)).toBeTruthy();
    },
  );

  it(
    'score-value-yes is painted with scoreZoneColor(0.9) when confident + outside neutral band',
    () => {
      render(
        <EndgameGamesWithWithoutSection
          data={makeData({
            // 9 wins, 0 draws, 1 loss → score = 0.90 (well outside [0.45, 0.55])
            endgame_wdl: buildWdl(9, 0, 1),
            endgame_score_p_value: 0.001,
          })}
          scoreGap={makeScoreGap()}
        />,
      );
      const valueSpan = within(screen.getByTestId('tile-games-with-endgame')).getByTestId(
        'score-value-yes',
      );
      expect(normalizeColor(valueSpan.style.color)).toBe(normalizeColor(ZONE_SUCCESS));
    },
  );
});
