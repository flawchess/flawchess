// @vitest-environment jsdom
/**
 * Phase 86 Plan 05 — integration tests for the EndgameMetricsSection
 * orchestrator. Verifies the 3-card grid layout (Phase 87.4), sub-question
 * copy, card DOM ordering, and display-shift wiring for Conv/Recov bullets.
 *
 * Phase 87.2: updated fixtures to reflect schema changes:
 * - MaterialRow: removed opponent_score, opponent_games, diff_p_value, diff_ci_low, diff_ci_high
 * - ScoreGapMaterialResponse: removed skill, opp_skill, skill_diff_*; added 20 section2_score_gap_* fields
 * - Section copy updated to Stockfish-baseline framing (D-08)
 * Phase 87.4: EndgameSkillCard / tile-endgame-skill / endgameWdl prop /
 * ConnectorArrows / 6 skill fields all deleted. Bullets now display-shifted
 * uniformly via SECTION2_DISPLAY_SHIFT.
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

// useEvalCoverage calls useQuery which requires a QueryClientProvider.
// Return safe defaults so the component renders without a provider.
vi.mock('@/hooks/useEvalCoverage', () => ({
  useEvalCoverage: () => ({ isPending: false, pendingCount: 0, pct: 100, totalCount: 0, isLoading: false }),
}));

import type {
  MaterialRow,
  ScoreGapMaterialResponse,
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

import { EndgameMetricsSection } from '../EndgameMetricsSection';

function buildRow(overrides?: Partial<MaterialRow>): MaterialRow {
  // Phase 87.2: opponent_score, opponent_games, diff_p_value, diff_ci_low, diff_ci_high
  // deleted from MaterialRow per D-05.
  return {
    bucket: 'conversion',
    label: 'Conversion',
    games: 100,
    win_pct: 65,
    draw_pct: 10,
    loss_pct: 25,
    score: 0.70,
    ...overrides,
  };
}

function buildScoreGapResponse(
  overrides?: Partial<ScoreGapMaterialResponse>,
): ScoreGapMaterialResponse {
  const conv = buildRow({ bucket: 'conversion', label: 'Conversion', win_pct: 65, draw_pct: 10, loss_pct: 25, score: 0.70 });
  const parity = buildRow({ bucket: 'parity', label: 'Parity', win_pct: 50, draw_pct: 20, loss_pct: 30, score: 0.60 });
  const recov = buildRow({ bucket: 'recovery', label: 'Recovery', win_pct: 10, draw_pct: 30, loss_pct: 60, score: 0.25 });
  return {
    endgame_score: 0.55,
    non_endgame_score: 0.50,
    score_difference: 0.05,
    material_rows: [conv, parity, recov],
    timeline: [],
    timeline_window: 100,
    score_difference_p_value: 0.001,
    score_difference_ci_low: 0.02,
    score_difference_ci_high: 0.08,
    // Phase 87.2: 15 section2_score_gap_* fields (3 buckets × 5). Skill fields
    // were deleted in Phase 87.4 D-05.
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
    ...overrides,
  };
}

describe('EndgameMetricsSection — full-rendering case (Phase 87.4: 3 cards)', () => {
  it('renders all 3 card testids with the sub-question line', () => {
    render(<EndgameMetricsSection data={buildScoreGapResponse()} />);

    expect(screen.getByTestId('endgame-metrics-section')).not.toBeNull();
    expect(screen.getByTestId('tile-conversion')).not.toBeNull();
    expect(screen.getByTestId('tile-parity')).not.toBeNull();
    expect(screen.getByTestId('tile-recovery')).not.toBeNull();
    // Phase 87.4: tile-endgame-skill no longer exists.
    expect(screen.queryByTestId('tile-endgame-skill')).toBeNull();
    expect(
      screen.getByText(
        'How do you score from winning, balanced, and losing endgames?',
      ),
    ).not.toBeNull();
  });

  it('renders ScoreGapRow bullets in all 3 cards when scoreGapN > 0', () => {
    render(<EndgameMetricsSection data={buildScoreGapResponse()} />);
    expect(screen.getByTestId('tile-conversion-score-gap-bullet')).not.toBeNull();
    expect(screen.getByTestId('tile-parity-score-gap-bullet')).not.toBeNull();
    expect(screen.getByTestId('tile-recovery-score-gap-bullet')).not.toBeNull();
    // Phase 87.4: tile-endgame-skill-score-gap-bullet is gone.
    expect(screen.queryByTestId('tile-endgame-skill-score-gap-bullet')).toBeNull();
  });
});

describe('EndgameMetricsSection — display-shift wiring (Phase 87.4 D-03/D-04)', () => {
  it('applies SECTION2_DISPLAY_SHIFT to the Conversion bullet value', () => {
    // Conv raw = PIVOT (-0.0474) → shifted = -0.0474 + -0.055 = -0.1024 → rounded -10%.
    // The card renders the shifted value as a signed percent.
    const data = buildScoreGapResponse({
      section2_score_gap_conv_mean: -0.0474,
      section2_score_gap_conv_n: 100,
      section2_score_gap_conv_ci_low: -0.10,
      section2_score_gap_conv_ci_high: 0.0,
    });

    render(<EndgameMetricsSection data={data} />);

    const convBullet = screen.getByTestId('tile-conversion-score-gap-value');
    // -0.0474 + -0.055 = -0.1024 → rounded to integer percent = -10%.
    expect(convBullet.textContent).toContain('-10%');
  });

  it('Parity bullet is unshifted (shift = 0)', () => {
    const data = buildScoreGapResponse({
      section2_score_gap_parity_mean: 0.03,
      section2_score_gap_parity_n: 100,
      section2_score_gap_parity_ci_low: -0.02,
      section2_score_gap_parity_ci_high: 0.08,
    });

    render(<EndgameMetricsSection data={data} />);

    const parityBullet = screen.getByTestId('tile-parity-score-gap-value');
    // 0.03 + 0 = +0.03 → +3%.
    expect(parityBullet.textContent).toContain('+3%');
  });

  it('Recovery bullet is shifted by +0.06', () => {
    // Recov raw = -0.04 → shifted = -0.04 + 0.06 = +0.02 → rounded +2%.
    const data = buildScoreGapResponse({
      section2_score_gap_recov_mean: -0.04,
      section2_score_gap_recov_n: 100,
      section2_score_gap_recov_ci_low: -0.09,
      section2_score_gap_recov_ci_high: 0.01,
    });

    render(<EndgameMetricsSection data={data} />);

    const recovBullet = screen.getByTestId('tile-recovery-score-gap-value');
    expect(recovBullet.textContent).toContain('+2%');
  });
});

describe('EndgameMetricsSection — card DOM ordering', () => {
  it('renders cards in DOM order: Conversion -> Parity -> Recovery (no Skill)', () => {
    render(<EndgameMetricsSection data={buildScoreGapResponse()} />);

    const conv = screen.getByTestId('tile-conversion');
    const parity = screen.getByTestId('tile-parity');
    const recov = screen.getByTestId('tile-recovery');

    // compareDocumentPosition returns DOCUMENT_POSITION_FOLLOWING (4) when
    // the argument follows the receiver in document order.
    const FOLLOWING = Node.DOCUMENT_POSITION_FOLLOWING;
    expect(conv.compareDocumentPosition(parity) & FOLLOWING).toBe(FOLLOWING);
    expect(parity.compareDocumentPosition(recov) & FOLLOWING).toBe(FOLLOWING);
  });
});
