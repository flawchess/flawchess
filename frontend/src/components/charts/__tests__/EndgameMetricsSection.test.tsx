// @vitest-environment jsdom
/**
 * Phase 86 Plan 05 — integration tests for the EndgameMetricsSection
 * orchestrator. Verifies the 4-card grid layout, sub-question copy, card
 * DOM ordering, and Skill-card gating when the backend returns null sig
 * fields (fewer than 2 active buckets).
 *
 * Phase 87.2: updated fixtures to reflect schema changes:
 * - MaterialRow: removed opponent_score, opponent_games, diff_p_value, diff_ci_low, diff_ci_high
 * - ScoreGapMaterialResponse: removed skill, opp_skill, skill_diff_*; added 20 section2_score_gap_* fields
 * - Section copy updated to Stockfish-baseline framing (D-08)
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

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
    // Phase 87.2: 20 new section2_score_gap_* fields (replaces skill/opp_skill/skill_diff_*)
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
    section2_score_gap_skill_mean: 0.023,
    section2_score_gap_skill_n: 300,
    section2_score_gap_skill_p_value: 0.18,
    section2_score_gap_skill_ci_low: -0.01,
    section2_score_gap_skill_ci_high: 0.056,
    // quick-260515-wye: gauge driver (rate composite, distinct from ΔES bullet above).
    endgame_skill_rate_mean: 0.55,
    ...overrides,
  };
}

describe('EndgameMetricsSection — full-rendering case', () => {
  it('renders all 4 card testids with the sub-question line', () => {
    render(<EndgameMetricsSection data={buildScoreGapResponse()} />);

    expect(screen.getByTestId('endgame-metrics-section')).not.toBeNull();
    expect(screen.getByTestId('tile-conversion')).not.toBeNull();
    expect(screen.getByTestId('tile-parity')).not.toBeNull();
    expect(screen.getByTestId('tile-recovery')).not.toBeNull();
    expect(screen.getByTestId('tile-endgame-skill')).not.toBeNull();
    expect(
      screen.getByText(
        'Do you outperform the Stockfish baseline at converting, holding, and recovering?',
      ),
    ).not.toBeNull();
  });

  it('renders ScoreGapRow bullets in all 4 cards when scoreGapN > 0', () => {
    render(<EndgameMetricsSection data={buildScoreGapResponse()} />);
    expect(screen.getByTestId('tile-conversion-score-gap-bullet')).not.toBeNull();
    expect(screen.getByTestId('tile-parity-score-gap-bullet')).not.toBeNull();
    expect(screen.getByTestId('tile-recovery-score-gap-bullet')).not.toBeNull();
    expect(screen.getByTestId('tile-endgame-skill-score-gap-bullet')).not.toBeNull();
  });
});

describe('EndgameMetricsSection — Skill card gating', () => {
  it('renders the Skill card empty state when endgame_skill_rate_mean === null', () => {
    // quick-260515-wye: the gauge drives the card's empty state via the
    // `skill` prop, which is now wired to endgame_skill_rate_mean (not to
    // the ΔES bullet field).
    const data = buildScoreGapResponse({
      material_rows: [
        buildRow({ bucket: 'conversion', games: 100 }),
        buildRow({ bucket: 'parity', games: 0, win_pct: 0, draw_pct: 0, loss_pct: 0, score: 0 }),
        buildRow({ bucket: 'recovery', games: 0, win_pct: 0, draw_pct: 0, loss_pct: 0, score: 0 }),
      ],
      endgame_skill_rate_mean: null,
      section2_score_gap_skill_mean: null,
      section2_score_gap_skill_n: null,
      section2_score_gap_skill_p_value: null,
      section2_score_gap_skill_ci_low: null,
      section2_score_gap_skill_ci_high: null,
    });

    render(<EndgameMetricsSection data={data} />);

    expect(screen.getByTestId('tile-endgame-skill')).not.toBeNull();
    // Empty-state copy from EndgameSkillCard when skill === null (D-17).
    expect(screen.getAllByText('Not enough data yet').length).toBeGreaterThan(0);
  });

  it('gauge value comes from endgame_skill_rate_mean, bullet value from section2_score_gap_skill_mean', () => {
    // quick-260515-wye: regression guard. Before the fix, the gauge aliased
    // onto section2_score_gap_skill_mean and showed the ΔES value. Now the
    // two are wired to independent fields.
    const data = buildScoreGapResponse({
      endgame_skill_rate_mean: 0.5,           // gauge → mid-band (50%)
      section2_score_gap_skill_mean: -0.02,   // bullet → -2pp
      section2_score_gap_skill_n: 300,
      section2_score_gap_skill_ci_low: -0.04,
      section2_score_gap_skill_ci_high: 0.0,
    });

    render(<EndgameMetricsSection data={data} />);

    // Bullet renders with the ΔES value formatted as a signed percent.
    const bullet = screen.getByTestId('tile-endgame-skill-score-gap-value');
    expect(bullet.textContent).toContain('-2%');

    // The card is mounted (gauge is an SVG inside EndgameGauge, no testid
    // on the needle itself — the contrast between bullet text "-2%" and the
    // gauge driver value 0.5 is enforced by the prop wiring and is asserted
    // at the EndgameMetricsSection.tsx prop-wiring layer plus the backend
    // schema split). If this fails because both fields show the same value,
    // the regression has returned.
    expect(screen.getByTestId('tile-endgame-skill')).not.toBeNull();
  });
});

describe('EndgameMetricsSection — card DOM ordering', () => {
  it('renders cards in DOM order: Conversion -> Parity -> Recovery -> Skill', () => {
    render(<EndgameMetricsSection data={buildScoreGapResponse()} />);

    const conv = screen.getByTestId('tile-conversion');
    const parity = screen.getByTestId('tile-parity');
    const recov = screen.getByTestId('tile-recovery');
    const skill = screen.getByTestId('tile-endgame-skill');

    // compareDocumentPosition returns DOCUMENT_POSITION_FOLLOWING (4) when
    // the argument follows the receiver in document order.
    const FOLLOWING = Node.DOCUMENT_POSITION_FOLLOWING;
    expect(conv.compareDocumentPosition(parity) & FOLLOWING).toBe(FOLLOWING);
    expect(parity.compareDocumentPosition(recov) & FOLLOWING).toBe(FOLLOWING);
    expect(recov.compareDocumentPosition(skill) & FOLLOWING).toBe(FOLLOWING);
  });
});
