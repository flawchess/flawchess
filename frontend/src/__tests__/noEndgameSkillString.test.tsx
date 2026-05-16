// @vitest-environment jsdom
/**
 * Phase 87.4 (Plan 02, SC#8) — RTL regression test.
 *
 * Renders the two surfaces where Endgame Skill could leak (the Section 2 card
 * grid and the renamed Conversion ELO Timeline) and asserts the phrase "Endgame
 * Skill" never appears in rendered output. The tile-endgame-skill testid is
 * likewise gone.
 *
 * Whitelist: CHANGELOG.md historical entries are excluded by test scope (we
 * mount components, not markdown content).
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import type {
  MaterialRow,
  ScoreGapMaterialResponse,
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

import { EndgameMetricsSection } from '@/components/charts/EndgameMetricsSection';
import { ConversionEloTimelineSection } from '@/components/charts/ConversionEloTimelineSection';

function buildRow(overrides?: Partial<MaterialRow>): MaterialRow {
  return {
    bucket: 'conversion',
    label: 'Conversion',
    games: 100,
    win_pct: 65,
    draw_pct: 10,
    loss_pct: 25,
    score: 0.7,
    ...overrides,
  };
}

function buildScoreGapResponse(): ScoreGapMaterialResponse {
  return {
    endgame_score: 0.55,
    non_endgame_score: 0.5,
    score_difference: 0.05,
    material_rows: [
      buildRow({ bucket: 'conversion', label: 'Conversion' }),
      buildRow({ bucket: 'parity', label: 'Parity', win_pct: 50, draw_pct: 20, loss_pct: 30, score: 0.6 }),
      buildRow({ bucket: 'recovery', label: 'Recovery', win_pct: 10, draw_pct: 30, loss_pct: 60, score: 0.25 }),
    ],
    timeline: [],
    timeline_window: 100,
    score_difference_p_value: 0.001,
    score_difference_ci_low: 0.02,
    score_difference_ci_high: 0.08,
    section2_score_gap_conv_mean: 0.08,
    section2_score_gap_conv_n: 100,
    section2_score_gap_conv_p_value: 0.001,
    section2_score_gap_conv_ci_low: 0.03,
    section2_score_gap_conv_ci_high: 0.13,
    section2_score_gap_parity_mean: 0.03,
    section2_score_gap_parity_n: 100,
    section2_score_gap_parity_p_value: 0.15,
    section2_score_gap_parity_ci_low: -0.02,
    section2_score_gap_parity_ci_high: 0.08,
    section2_score_gap_recov_mean: -0.04,
    section2_score_gap_recov_n: 100,
    section2_score_gap_recov_p_value: 0.25,
    section2_score_gap_recov_ci_low: -0.09,
    section2_score_gap_recov_ci_high: 0.01,
  };
}

function buildEmptyTimeline(): ConversionEloTimelineResponse {
  return { combos: [], timeline_window: 100 };
}

describe('SC#8 — no "Endgame Skill" string in rendered Endgames surfaces', () => {
  it('EndgameMetricsSection: rendered output contains zero matches for /endgame skill/i', () => {
    render(<EndgameMetricsSection data={buildScoreGapResponse()} />);
    expect(screen.queryAllByText(/endgame skill/i)).toHaveLength(0);
  });

  it('EndgameMetricsSection: the tile-endgame-skill testid is gone', () => {
    render(<EndgameMetricsSection data={buildScoreGapResponse()} />);
    expect(screen.queryByTestId('tile-endgame-skill')).toBeNull();
  });

  it('ConversionEloTimelineSection (empty state): rendered output contains zero matches for /endgame skill/i', () => {
    render(
      <ConversionEloTimelineSection
        data={buildEmptyTimeline()}
        isLoading={false}
        isError={false}
      />,
    );
    expect(screen.queryAllByText(/endgame skill/i)).toHaveLength(0);
  });
});
