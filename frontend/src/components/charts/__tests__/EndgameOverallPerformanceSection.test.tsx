// @vitest-environment jsdom
/**
 * Phase 85 Plan 05: tests for EndgameOverallPerformanceSection.
 *
 * Covers:
 * - Section structure: section container, all 3 card testids, score-gap testid,
 *   section question line, and all card title texts render.
 * - Negative assertions: legacy testids and h3 strings are gone.
 * - Math: per-card chess-score matches (W + 0.5·D)/n on Cards 1 and 3.
 * - Score Gap formatting: signed percentage with explicit '+' or '-' prefix.
 * - Empty state: per-card "Not enough data yet" when wdl.total === 0 (Card 1).
 * - Sig gating on Card 3 (score-value-yes): low confidence, low-n, confident.
 * - Card 2 entry-eval and achievable-score row assertions (from legacy
 *   EndgameStartVsEndSection tests).
 * - Card 2 does NOT contain a WDL bar.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';

import { ZONE_SUCCESS } from '@/lib/theme';
import type {
  EndgamePerformanceResponse,
  EndgameWDLSummary,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

// Spy on MiniBulletChart so we do not render recharts internals under jsdom;
// keeps the test focused on prop-driven behavior.
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

import { EndgameOverallPerformanceSection } from '../EndgameOverallPerformanceSection';

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
    entry_eval_mean_pawns: 1.2,
    entry_eval_n: 50,
    entry_eval_p_value: 0.001,
    endgame_score_p_value: null,
    non_endgame_score_p_value: null,
    entry_eval_ci_low_pawns: 0.4,
    entry_eval_ci_high_pawns: 2.0,
    entry_expected_score: 0.5,
    entry_expected_score_n: 50,
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

describe('EndgameOverallPerformanceSection', () => {
  // ── Section structure ────────────────────────────────────────────────────

  it('renders the section container, all 3 card testids, score-gap, question line, and card titles', () => {
    render(
      <EndgameOverallPerformanceSection data={makeData()} scoreGap={makeScoreGap()} />,
    );
    expect(screen.getByTestId('endgame-overall-performance-section')).toBeTruthy();
    expect(screen.getByTestId('tile-games-ending-middlegame')).toBeTruthy();
    expect(screen.getByTestId('tile-at-endgame-entry')).toBeTruthy();
    expect(screen.getByTestId('tile-endgame-results')).toBeTruthy();
    expect(screen.getByTestId('endgame-score-gap')).toBeTruthy();
    expect(screen.getByText('Games ending in Middlegame')).toBeTruthy();
    expect(screen.getByText('At Endgame Entry')).toBeTruthy();
    expect(screen.getByText('Endgame results')).toBeTruthy();
    expect(screen.getByText('Endgame Score Gap')).toBeTruthy();
    expect(screen.getByText(/Do you perform better or worse when games reach an endgame/)).toBeTruthy();
  });

  it('negative: legacy section testids and legacy text strings are absent', () => {
    render(
      <EndgameOverallPerformanceSection data={makeData()} scoreGap={makeScoreGap()} />,
    );
    expect(screen.queryByText('Games with vs without Endgame')).toBeNull();
    expect(screen.queryByTestId('endgame-games-with-without-section')).toBeNull();
    expect(screen.queryByTestId('endgame-start-vs-end-section')).toBeNull();
    expect(screen.queryByTestId('tile-games-without-endgame')).toBeNull();
    expect(screen.queryByTestId('tile-games-with-endgame')).toBeNull();
    expect(screen.queryByTestId('tile-entry-eval')).toBeNull();
    expect(screen.queryByTestId('tile-endgame-score')).toBeNull();
    expect(screen.queryByTestId('score-gap-footer')).toBeNull();
    expect(screen.queryByTestId('perf-section-info')).toBeNull();
  });

  // ── Score math ───────────────────────────────────────────────────────────

  it('per-card score percentage matches (W + 0.5·D)/n on Card 1 and Card 3', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({
          // Card 1 (non_endgame_wdl): 100% score — 10 wins, 0 draws, 0 losses
          non_endgame_wdl: buildWdl(10, 0, 0),
          non_endgame_score_p_value: 0.001,
          // Card 3 (endgame_wdl): 50% score — 5 wins, 0 draws, 5 losses
          endgame_wdl: buildWdl(5, 0, 5),
          endgame_score_p_value: null,
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    const card1 = within(screen.getByTestId('tile-games-ending-middlegame'));
    const card3 = within(screen.getByTestId('tile-endgame-results'));
    expect(card1.getByTestId('score-value-no').textContent).toBe('100%');
    expect(card3.getByTestId('score-value-yes').textContent).toBe('50%');
  });

  // ── Score Gap formatting ─────────────────────────────────────────────────

  it('score gap shows signed score_difference with explicit + or - prefix', () => {
    const { rerender } = render(
      <EndgameOverallPerformanceSection
        data={makeData()}
        scoreGap={makeScoreGap({ score_difference: 0.07 })}
      />,
    );
    expect(screen.getByTestId('score-gap-difference').textContent).toBe('+7%');

    rerender(
      <EndgameOverallPerformanceSection
        data={makeData()}
        scoreGap={makeScoreGap({ score_difference: -0.12 })}
      />,
    );
    expect(screen.getByTestId('score-gap-difference').textContent).toBe('-12%');
  });

  // ── Empty state ──────────────────────────────────────────────────────────

  it('renders "Not enough data yet" inside Card 1 when non_endgame_wdl.total === 0', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({
          non_endgame_wdl: buildWdl(0, 0, 0, 0),
          endgame_wdl: buildWdl(20, 8, 12),
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    const card1 = within(screen.getByTestId('tile-games-ending-middlegame'));
    expect(card1.getByText(/Not enough data yet/i)).toBeTruthy();
    expect(card1.queryByTestId('score-value-no')).toBeNull();
    // Card 3 unaffected
    const card3 = within(screen.getByTestId('tile-endgame-results'));
    expect(card3.queryByTestId('score-value-yes')).toBeTruthy();
  });

  // ── Sig gating (Card 3 = score-value-yes) ───────────────────────────────

  it(
    'score-value-yes has NO inline color when total >= 10 but p-value > 0.05 ' +
      '(sig gating: low confidence suppresses zone font color)',
    () => {
      render(
        <EndgameOverallPerformanceSection
          data={makeData({
            endgame_wdl: buildWdl(9, 0, 1),
            endgame_score_p_value: 0.20,
          })}
          scoreGap={makeScoreGap()}
        />,
      );
      const valueSpan = within(screen.getByTestId('tile-endgame-results')).getByTestId(
        'score-value-yes',
      );
      expect(valueSpan.style.color).toBe('');
    },
  );

  it(
    'score-value-yes has NO inline color when total < MIN_GAMES_FOR_RELIABLE_STATS ' +
      '(score row falls into empty-state branch)',
    () => {
      render(
        <EndgameOverallPerformanceSection
          data={makeData({
            endgame_wdl: buildWdl(3, 0, 2),
            endgame_score_p_value: null,
          })}
          scoreGap={makeScoreGap()}
        />,
      );
      const card3 = within(screen.getByTestId('tile-endgame-results'));
      // Score row hidden; value testid absent.
      expect(card3.queryByTestId('score-value-yes')).toBeNull();
      // Empty-state copy rendered in its place.
      expect(card3.getByText(/Not enough data yet/i)).toBeTruthy();
    },
  );

  it(
    'score-value-yes is painted with ZONE_SUCCESS when confident + outside neutral band',
    () => {
      render(
        <EndgameOverallPerformanceSection
          data={makeData({
            // 9 wins, 0 draws, 1 loss → score = 0.90 (well outside [0.45, 0.55])
            endgame_wdl: buildWdl(9, 0, 1),
            endgame_score_p_value: 0.001,
          })}
          scoreGap={makeScoreGap()}
        />,
      );
      const valueSpan = within(screen.getByTestId('tile-endgame-results')).getByTestId(
        'score-value-yes',
      );
      expect(normalizeColor(valueSpan.style.color)).toBe(normalizeColor(ZONE_SUCCESS));
    },
  );

  // ── Card 2 entry-eval row ────────────────────────────────────────────────

  it('entry-eval-value exists inside tile-at-endgame-entry when entry_eval_n >= 10', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({
          entry_eval_mean_pawns: 1.2,
          entry_eval_n: 50,
          entry_eval_p_value: 0.001,
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    const card2 = screen.getByTestId('tile-at-endgame-entry');
    expect(within(card2).getByTestId('entry-eval-value')).toBeTruthy();
  });

  it('entry-eval row falls into "Not enough data yet" inside Card 2 when entry_eval_n < 10', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({ entry_eval_n: 5 })}
        scoreGap={makeScoreGap()}
      />,
    );
    const card2 = screen.getByTestId('tile-at-endgame-entry');
    expect(within(card2).queryByTestId('entry-eval-value')).toBeNull();
    expect(within(card2).getAllByText(/Not enough data yet/i).length).toBeGreaterThan(0);
  });

  // ── Card 2 achievable-score row ──────────────────────────────────────────

  it('achievable-score-value exists inside tile-at-endgame-entry when entry_expected_score_n >= 10', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({
          entry_expected_score: 0.62,
          entry_expected_score_n: 50,
          entry_expected_score_p_value: 0.001,
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    const card2 = screen.getByTestId('tile-at-endgame-entry');
    expect(within(card2).getByTestId('endgame-achievable-score')).toBeTruthy();
    expect(within(card2).getByTestId('achievable-score-value')).toBeTruthy();
  });

  it('achievable row falls into "Not enough data yet" inside Card 2 when entry_expected_score_n < 10', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({ entry_expected_score_n: 5 })}
        scoreGap={makeScoreGap()}
      />,
    );
    const card2 = screen.getByTestId('tile-at-endgame-entry');
    expect(within(card2).queryByTestId('achievable-score-value')).toBeNull();
    expect(within(card2).getAllByText(/Not enough data yet/i).length).toBeGreaterThan(0);
  });

  // ── Card 2 has NO WDL bar ────────────────────────────────────────────────

  it('Card 2 does NOT contain a WDL bar row', () => {
    render(
      <EndgameOverallPerformanceSection data={makeData()} scoreGap={makeScoreGap()} />,
    );
    expect(
      within(screen.getByTestId('tile-at-endgame-entry')).queryByText('Win / Draw / Loss:'),
    ).toBeNull();
  });
});
