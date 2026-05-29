// @vitest-environment jsdom
/**
 * Phase 85 Plan 05: tests for EndgameOverallPerformanceSection.
 * Phase 88.3 Plan 03 (SC-3): updated for 2-column responsive card layout.
 *
 * Covers:
 * - Section structure: section container, all 4 testids (tile-games-without-endgame,
 *   tile-games-with-endgame, tile-at-endgame-entry, endgame-score-differences),
 *   section question line, and all card title texts render.
 * - SC-3 layout assertions: outer charcoal-texture card present; 3-column grid
 *   and ConnectorArrows overlay absent; both surviving divider patterns present.
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

// useEvalCoverage calls useQuery which requires a QueryClientProvider.
// Return safe defaults so the component renders without a provider.
vi.mock('@/hooks/useEvalCoverage', () => ({
  useEvalCoverage: () => ({ isPending: false, pendingCount: 0, pct: 100, totalCount: 0, isLoading: false }),
}));

import { ZONE_SUCCESS } from '@/lib/theme';
import type {
  EndgamePerformanceResponse,
  EndgameWDLSummary,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

// Spy on MiniBulletChart so we do not render recharts internals under jsdom;
// keeps the test focused on prop-driven behavior. Surface ciLow / ciHigh as
// data-attrs so per-row assertions can verify CI prop threading (SEC1-11).
vi.mock('@/components/charts/MiniBulletChart', () => ({
  MiniBulletChart: vi.fn((props: Record<string, unknown>) => {
    const dataAttrs: Record<string, string> = {};
    if (props.ciLow !== undefined) dataAttrs['data-ci-low'] = String(props.ciLow);
    if (props.ciHigh !== undefined) dataAttrs['data-ci-high'] = String(props.ciHigh);
    return (
      <div
        data-testid="mock-mini-bullet"
        data-domain={String(props.domain)}
        data-center={String(props.center)}
        data-aria-label={String(props.ariaLabel)}
        {...dataAttrs}
      />
    );
  }),
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
    achievable_score_gap: 0,
    achievable_score_gap_p_value: null,
    achievable_score_gap_ci_low: null,
    achievable_score_gap_ci_high: null,
    achievable_score_gap_percentile: null,
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
    score_difference_p_value: null,
    score_difference_ci_low: null,
    score_difference_ci_high: null,
    score_gap_percentile: null,
    score_gap_conv_percentile: null,
    score_gap_parity_percentile: null,
    ...overrides,
  };
}

describe('EndgameOverallPerformanceSection', () => {
  // ── Section structure ────────────────────────────────────────────────────

  it('renders the section container, all 3 card testids, score-differences card, question line, and card titles', () => {
    render(
      <EndgameOverallPerformanceSection data={makeData()} scoreGap={makeScoreGap()} />,
    );
    expect(screen.getByTestId('endgame-overall-performance-section')).toBeTruthy();
    expect(screen.getByTestId('tile-games-without-endgame')).toBeTruthy();
    expect(screen.getByTestId('tile-at-endgame-entry')).toBeTruthy();
    expect(screen.getByTestId('tile-games-with-endgame')).toBeTruthy();
    expect(screen.getByTestId('endgame-score-differences')).toBeTruthy();
    expect(screen.getByText('Games without Endgame')).toBeTruthy();
    expect(screen.getByText('Eval at Endgame Entry')).toBeTruthy();
    expect(screen.getByText('Games with Endgame')).toBeTruthy();
    expect(screen.getByText('Endgame Score Differences')).toBeTruthy();
    expect(screen.getByText('Endgame Score Gap:')).toBeTruthy();
    expect(screen.getByText('Achievable Score Gap:')).toBeTruthy();
    expect(screen.getByText(/Do you perform better or worse when games reach an endgame/)).toBeTruthy();
  });

  it('negative: legacy section testids and legacy text strings are absent', () => {
    render(
      <EndgameOverallPerformanceSection data={makeData()} scoreGap={makeScoreGap()} />,
    );
    expect(screen.queryByText('Games with vs without Endgame')).toBeNull();
    expect(screen.queryByTestId('endgame-games-with-without-section')).toBeNull();
    expect(screen.queryByTestId('endgame-start-vs-end-section')).toBeNull();
    expect(screen.queryByTestId('tile-entry-eval')).toBeNull();
    expect(screen.queryByTestId('tile-endgame-score')).toBeNull();
    expect(screen.queryByTestId('score-gap-footer')).toBeNull();
    expect(screen.queryByTestId('perf-section-info')).toBeNull();
  });

  // ── SC-3 layout: 2-column card (88.3-F, 88.3-G) ─────────────────────────

  it('SC-3: outer charcoal-texture card is present inside the section', () => {
    render(
      <EndgameOverallPerformanceSection data={makeData()} scoreGap={makeScoreGap()} />,
    );
    const section = screen.getByTestId('endgame-overall-performance-section');
    // The outer card shell has the charcoal-texture class.
    const outerCard = section.querySelector('.charcoal-texture');
    expect(outerCard).toBeTruthy();
  });

  it('SC-3: 3-column grid is absent (replaced by flex layout)', () => {
    render(
      <EndgameOverallPerformanceSection data={makeData()} scoreGap={makeScoreGap()} />,
    );
    const section = screen.getByTestId('endgame-overall-performance-section');
    // The old grid class targeted via Tailwind's lg: responsive prefix.
    // querySelector with attribute selector covers both class list forms.
    const oldGrid = section.querySelector('[class*="grid-cols-3"]');
    expect(oldGrid).toBeNull();
  });

  it('SC-3: ConnectorArrows absolute overlay is absent (no pointer-events-none aria-hidden SVG wrapper)', () => {
    render(
      <EndgameOverallPerformanceSection data={makeData()} scoreGap={makeScoreGap()} />,
    );
    const section = screen.getByTestId('endgame-overall-performance-section');
    // ConnectorArrows rendered a wrapper: class="absolute inset-0 hidden lg:block pointer-events-none" aria-hidden="true"
    // The pointer-events-none + aria-hidden combination is unique to the connector overlay.
    const arrowsOverlay = section.querySelector('[aria-hidden="true"][class*="pointer-events-none"]');
    expect(arrowsOverlay).toBeNull();
  });

  // ── Top-right games-count badge ──────────────────────────────────────────

  it('renders games-share badge top-right of Card 1 and Card 3 with NN.N% (count) + Swords icon', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({
          // Card 1: 2,961 games; Card 3: 2,100 games → shares 58.5% / 41.5%
          non_endgame_wdl: buildWdl(1480, 0, 1481, 2961),
          endgame_wdl: buildWdl(1050, 0, 1050, 2100),
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    const badge1 = within(screen.getByTestId('tile-games-without-endgame')).getByTestId(
      'games-count-no',
    );
    const badge3 = within(screen.getByTestId('tile-games-with-endgame')).getByTestId(
      'games-count-yes',
    );
    expect(badge1.textContent).toContain('Games: 59% (2,961)');
    expect(badge3.textContent).toContain('Games: 41% (2,100)');
  });

  it('hides the games-count badge when a card has zero games', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({
          non_endgame_wdl: buildWdl(0, 0, 0, 0),
          endgame_wdl: buildWdl(10, 0, 10, 20),
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    expect(
      within(screen.getByTestId('tile-games-without-endgame')).queryByTestId(
        'games-count-no',
      ),
    ).toBeNull();
    expect(
      within(screen.getByTestId('tile-games-with-endgame')).queryByTestId(
        'games-count-yes',
      ),
    ).toBeTruthy();
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
    const card1 = within(screen.getByTestId('tile-games-without-endgame'));
    const card3 = within(screen.getByTestId('tile-games-with-endgame'));
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
    expect(screen.getByTestId('endgame-score-gap-value').textContent).toBe('+7%');

    rerender(
      <EndgameOverallPerformanceSection
        data={makeData()}
        scoreGap={makeScoreGap({ score_difference: -0.12 })}
      />,
    );
    expect(screen.getByTestId('endgame-score-gap-value').textContent).toBe('-12%');
  });

  it('achievable score gap shows signed data.achievable_score_gap with explicit + or - prefix (server-sourced; SEC1-10)', () => {
    // Fixture proves the migration: server-sourced gap (0.10) deliberately
    // diverges from the legacy frontend derivation (withScore - achievable_score
    // = 0.60 - 0.50 = 0.10 here is incidental; use a non-matching fixture to
    // demonstrate the component reads from achievable_score_gap directly).
    const { rerender } = render(
      <EndgameOverallPerformanceSection
        data={makeData({
          endgame_wdl: buildWdl(6, 0, 4), // legacy "withScore" = 0.60
          entry_expected_score: 0.50,
          entry_expected_score_n: 50,
          // Server-computed achievable_score_gap intentionally differs from
          // the (withScore - entry_expected_score) = +10% the old code returned.
          achievable_score_gap: 0.07,
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    expect(screen.getByTestId('achievable-score-gap-value').textContent).toBe('+7%');

    // Negative case: server-computed -15% gap with arbitrary endgame_wdl /
    // entry_expected_score that would have computed differently under the
    // legacy derivation.
    rerender(
      <EndgameOverallPerformanceSection
        data={makeData({
          endgame_wdl: buildWdl(6, 0, 4),
          entry_expected_score: 0.75,
          entry_expected_score_n: 50,
          achievable_score_gap: -0.15,
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    expect(screen.getByTestId('achievable-score-gap-value').textContent).toBe('-15%');
  });

  // ── CI prop threading on both ScoreGapRow rows (SEC1-11) ────────────────

  it('forwards achievable_score_gap_ci_low/high into the Achievable Score Gap bullet', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({
          achievable_score_gap: 0.04,
          achievable_score_gap_ci_low: -0.02,
          achievable_score_gap_ci_high: 0.10,
        })}
        scoreGap={makeScoreGap()}
      />,
    );
    // The mock surfaces ciLow / ciHigh as data-attrs and tags the aria-label
    // so we can locate the achievable bullet specifically.
    const bullets = screen.getAllByTestId('mock-mini-bullet');
    const achievableBullet = bullets.find((b) =>
      (b.getAttribute('data-aria-label') ?? '').startsWith('Achievable Score Gap'),
    );
    expect(achievableBullet).toBeTruthy();
    expect(achievableBullet?.getAttribute('data-ci-low')).toBe('-0.02');
    expect(achievableBullet?.getAttribute('data-ci-high')).toBe('0.1');
  });

  it('forwards score_difference_ci_low/high into the Endgame Score Gap bullet', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData()}
        scoreGap={makeScoreGap({
          score_difference: 0.05,
          score_difference_ci_low: -0.01,
          score_difference_ci_high: 0.12,
        })}
      />,
    );
    const bullets = screen.getAllByTestId('mock-mini-bullet');
    const endgameBullet = bullets.find((b) =>
      (b.getAttribute('data-aria-label') ?? '').startsWith('Endgame Score Gap'),
    );
    expect(endgameBullet).toBeTruthy();
    expect(endgameBullet?.getAttribute('data-ci-low')).toBe('-0.01');
    expect(endgameBullet?.getAttribute('data-ci-high')).toBe('0.12');
  });

  it('omits CI attrs when backend fields are null (?? undefined coercion)', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({
          achievable_score_gap: 0,
          achievable_score_gap_ci_low: null,
          achievable_score_gap_ci_high: null,
        })}
        scoreGap={makeScoreGap({
          score_difference_ci_low: null,
          score_difference_ci_high: null,
        })}
      />,
    );
    const bullets = screen.getAllByTestId('mock-mini-bullet');
    const achievableBullet = bullets.find((b) =>
      (b.getAttribute('data-aria-label') ?? '').startsWith('Achievable Score Gap'),
    );
    const endgameBullet = bullets.find((b) =>
      (b.getAttribute('data-aria-label') ?? '').startsWith('Endgame Score Gap'),
    );
    expect(achievableBullet?.getAttribute('data-ci-low')).toBeNull();
    expect(achievableBullet?.getAttribute('data-ci-high')).toBeNull();
    expect(endgameBullet?.getAttribute('data-ci-low')).toBeNull();
    expect(endgameBullet?.getAttribute('data-ci-high')).toBeNull();
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
    const card1 = within(screen.getByTestId('tile-games-without-endgame'));
    expect(card1.getByText(/Not enough data yet/i)).toBeTruthy();
    expect(card1.queryByTestId('score-value-no')).toBeNull();
    // Card 3 unaffected
    const card3 = within(screen.getByTestId('tile-games-with-endgame'));
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
      const valueSpan = within(screen.getByTestId('tile-games-with-endgame')).getByTestId(
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
      const card3 = within(screen.getByTestId('tile-games-with-endgame'));
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
      const valueSpan = within(screen.getByTestId('tile-games-with-endgame')).getByTestId(
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
      within(screen.getByTestId('tile-at-endgame-entry')).queryByText('Win/Draw/Loss'),
    ).toBeNull();
  });

  // ── Phase 94 PCTL-03/04/06: percentile chip rendering ─────────────────────

  it('renders Endgame Score Gap percentile chip when score_gap_percentile is non-null', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData()}
        scoreGap={makeScoreGap({ score_gap_percentile: 73 })}
      />,
    );
    expect(screen.getByTestId('endgame-score-gap-percentile-chip')).toBeTruthy();
  });

  it('does NOT render Endgame Score Gap percentile chip when score_gap_percentile is null', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData()}
        scoreGap={makeScoreGap({ score_gap_percentile: null })}
      />,
    );
    expect(screen.queryByTestId('endgame-score-gap-percentile-chip')).toBeNull();
  });

  it('renders Achievable Score Gap percentile chip when achievable_score_gap_percentile is non-null', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({ achievable_score_gap_percentile: 88 })}
        scoreGap={makeScoreGap()}
      />,
    );
    expect(screen.getByTestId('achievable-score-gap-percentile-chip')).toBeTruthy();
  });

  it('does NOT render Achievable Score Gap percentile chip when achievable_score_gap_percentile is null', () => {
    render(
      <EndgameOverallPerformanceSection
        data={makeData({ achievable_score_gap_percentile: null })}
        scoreGap={makeScoreGap()}
      />,
    );
    expect(screen.queryByTestId('achievable-score-gap-percentile-chip')).toBeNull();
  });
});
