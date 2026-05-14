// @vitest-environment jsdom
/**
 * Phase 86 Plan 05 — integration tests for the EndgameMetricsSection
 * orchestrator. Verifies the 4-card grid layout, sub-question copy, card
 * DOM ordering, and Skill-card gating when the backend returns null sig
 * fields (fewer than 2 active buckets).
 *
 * Mirrors `EndgameOverallPerformanceSection.test.tsx` (Phase 85): renders
 * the orchestrator + real card children, asserts on testid presence and
 * DOM position. Connector-arrows geometry is exercised indirectly via the
 * Phase 85 tests + the live integration check in the human-verify step.
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
  return {
    bucket: 'conversion',
    label: 'Conversion',
    games: 100,
    win_pct: 65,
    draw_pct: 10,
    loss_pct: 25,
    score: 0.70,
    opponent_score: 0.60,
    opponent_games: 100,
    diff_p_value: 0.001,
    diff_ci_low: 0.02,
    diff_ci_high: 0.18,
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
    skill: 0.65,
    opp_skill: 0.55,
    skill_diff_p_value: 0.001,
    skill_diff_ci_low: 0.05,
    skill_diff_ci_high: 0.15,
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
        'Do you outperform your opponents at converting, holding, and recovering?',
      ),
    ).not.toBeNull();
  });
});

describe('EndgameMetricsSection — Skill card gating', () => {
  it('renders the Skill card empty state when skill === null', () => {
    const data = buildScoreGapResponse({
      material_rows: [
        buildRow({ bucket: 'conversion', games: 100, win_pct: 65, draw_pct: 10, loss_pct: 25, score: 0.70 }),
        buildRow({ bucket: 'parity', games: 0, win_pct: 0, draw_pct: 0, loss_pct: 0, score: 0, opponent_score: null, opponent_games: 0, diff_p_value: null, diff_ci_low: null, diff_ci_high: null }),
        buildRow({ bucket: 'recovery', games: 0, win_pct: 0, draw_pct: 0, loss_pct: 0, score: 0, opponent_score: null, opponent_games: 0, diff_p_value: null, diff_ci_low: null, diff_ci_high: null }),
      ],
      skill: null,
      opp_skill: null,
      skill_diff_p_value: null,
      skill_diff_ci_low: null,
      skill_diff_ci_high: null,
    });

    render(<EndgameMetricsSection data={data} />);

    expect(screen.getByTestId('tile-endgame-skill')).not.toBeNull();
    // Empty-state copy from EndgameSkillCard when skill === null (D-17).
    expect(screen.getAllByText('Not enough data yet').length).toBeGreaterThan(0);
  });
});

describe('EndgameMetricsSection — card DOM ordering', () => {
  it('renders cards in DOM order: Conversion → Parity → Recovery → Skill', () => {
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
