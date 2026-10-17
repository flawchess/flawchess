// @vitest-environment jsdom
/**
 * OpeningFindings: the phone "Show more" (D-08) and its single Umami event, the collapsed
 * "Not clear yet (n)" cards (D-09, D-10), the empty-state copy (D-11), the older-games chip
 * (D-04) and the Moves / Games deep-link callbacks.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { OpeningFindings } from '@/components/openings/stats/OpeningFindings';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { OpeningInsightFinding, OpeningInsightsResponse } from '@/types/insights';

const trackFeature = vi.hoisted(() => vi.fn());
const insightsQuery = vi.hoisted(() => ({
  current: {
    data: undefined as unknown,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  },
}));

vi.mock('@/lib/analytics', async () => {
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics');
  return { ...actual, trackFeature };
});

vi.mock('@/hooks/useOpeningInsights', () => ({
  useOpeningInsights: () => insightsQuery.current,
}));

vi.mock('@/components/board/LazyMiniBoard', () => ({
  LazyMiniBoard: () => <div data-testid="lazy-mini-board" />,
}));

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({ tier1: true, tier2: true, pendingCount: 0, totalCount: 0, isLoading: false }),
}));

const FILTERS: FilterState = {
  color: 'white',
  matchSide: 'both',
  recency: 'year',
  customRange: null,
  timeControls: null,
  platforms: null,
  rated: null,
  opponentType: 'human',
  opponentStrength: { min: null, max: null },
};

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function makeFinding(overrides: Partial<OpeningInsightFinding> = {}): OpeningInsightFinding {
  return {
    color: 'white',
    classification: 'weakness',
    severity: 'major',
    opening_name: 'Sicilian Defense (B20)',
    opening_eco: 'B20',
    display_name: 'Sicilian Defense (B20)',
    entry_fen: START_FEN,
    entry_san_sequence: [],
    entry_full_hash: '0',
    candidate_move_san: 'e4',
    resulting_full_hash: '0',
    n_games: 50,
    wins: 10,
    draws: 10,
    losses: 30,
    score: 0.3,
    confidence: 'high',
    p_value: 0.001,
    ci_low: 0.2,
    ci_high: 0.4,
    ci99_low: 0.18,
    ci99_high: 0.44,
    avg_eval_pawns: -0.6,
    eval_n: 40,
    eval_p_value: 0.001,
    eval_confidence: 'high',
    eval_ci99_low_pawns: -0.9,
    eval_ci99_high_pawns: -0.3,
    last_played_at: '2026-09-01T00:00:00Z',
    is_current: true,
    ...overrides,
  };
}

function emptyResponse(overrides: Partial<OpeningInsightsResponse> = {}): OpeningInsightsResponse {
  return {
    white_weaknesses: [],
    black_weaknesses: [],
    white_strengths: [],
    black_strengths: [],
    white_weaknesses_not_clear: [],
    black_weaknesses_not_clear: [],
    white_strengths_not_clear: [],
    black_strengths_not_clear: [],
    white_weaknesses_not_clear_count: 0,
    black_weaknesses_not_clear_count: 0,
    white_strengths_not_clear_count: 0,
    black_strengths_not_clear_count: 0,
    current_cutoff_white: null,
    current_cutoff_black: null,
    eval_baseline_pawns_white: 0.25,
    eval_baseline_pawns_black: -0.25,
    ...overrides,
  };
}

function renderFindings(
  data: OpeningInsightsResponse,
  color: 'white' | 'black' = 'white',
  handlers: {
    onOpenMoves?: (f: OpeningInsightFinding) => void;
    onOpenGames?: (f: OpeningInsightFinding) => void;
  } = {},
) {
  insightsQuery.current = { data, isLoading: false, isError: false, refetch: vi.fn() };
  return render(
    <OpeningFindings
      color={color}
      debouncedFilters={FILTERS}
      onOpenMoves={handlers.onOpenMoves ?? (() => {})}
      onOpenGames={handlers.onOpenGames ?? (() => {})}
    />,
  );
}

function panelOpenTargets(): string[] {
  return trackFeature.mock.calls
    .filter(([name]) => name === 'panel-open')
    .map(([, props]) => (props as { target: string }).target);
}

beforeEach(() => {
  trackFeature.mockClear();
});

afterEach(() => {
  cleanup();
});

describe('OpeningFindings cards and Show more', () => {
  const fiveCards = Array.from({ length: 5 }, (_, i) => makeFinding({ n_games: 50 + i }));

  it('hides cards 3-5 on phones until Show more, and tracks the expand once', () => {
    renderFindings(emptyResponse({ white_weaknesses: fiveCards }));

    const card = (i: number) => screen.getByTestId(`opening-findings-weakness-card-${i}`);
    expect(card(0).parentElement?.className).not.toContain('max-md:hidden');
    expect(card(1).parentElement?.className).not.toContain('max-md:hidden');
    expect(card(2).parentElement?.className).toContain('max-md:hidden');
    expect(card(4).parentElement?.className).toContain('max-md:hidden');

    const more = screen.getByTestId('opening-findings-weakness-btn-more');
    expect(more.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(more);
    expect(card(2).parentElement?.className).not.toContain('max-md:hidden');
    expect(card(4).parentElement?.className).not.toContain('max-md:hidden');
    expect(panelOpenTargets()).toEqual(['opening-insights-more']);

    // Collapsing never tracks.
    fireEvent.click(more);
    expect(card(4).parentElement?.className).toContain('max-md:hidden');
    expect(panelOpenTargets()).toEqual(['opening-insights-more']);
  });

  it('renders no Show more button when a section has at most two cards', () => {
    renderFindings(emptyResponse({ white_weaknesses: fiveCards.slice(0, 2) }));
    expect(screen.queryByTestId('opening-findings-weakness-btn-more')).toBeNull();
  });

  it('shows only the selected colour and leads each card with the move', () => {
    renderFindings(
      emptyResponse({
        white_weaknesses: [makeFinding({ candidate_move_san: 'e4' })],
        black_weaknesses: [
          makeFinding({ color: 'black', entry_san_sequence: ['e4'], candidate_move_san: 'e6' }),
        ],
      }),
      'black',
    );
    expect(screen.getByTestId('opening-findings-weakness-card-0-move').textContent).toBe('After 1... e6');
    expect(screen.queryByTestId('opening-findings-weakness-card-1')).toBeNull();
  });

  it('marks findings from older games with a chip and leaves current ones bare', () => {
    renderFindings(
      emptyResponse({
        white_strengths: [
          makeFinding({ classification: 'strength', is_current: true }),
          makeFinding({ classification: 'strength', is_current: false }),
        ],
      }),
    );
    expect(screen.queryByTestId('opening-findings-strength-card-0-older')).toBeNull();
    const chip = screen.getByTestId('opening-findings-strength-card-1-older');
    expect(chip.textContent).toBe('older games');
    expect(chip.getAttribute('title')).toMatch(/^Last seen September 2026$/);
  });

  it('calls the Moves and Games callbacks with the finding', () => {
    const finding = makeFinding();
    const onOpenMoves = vi.fn();
    const onOpenGames = vi.fn();
    renderFindings(emptyResponse({ white_weaknesses: [finding] }), 'white', { onOpenMoves, onOpenGames });
    fireEvent.click(screen.getByTestId('opening-findings-weakness-card-0-btn-moves'));
    fireEvent.click(screen.getByTestId('opening-findings-weakness-card-0-btn-games'));
    expect(onOpenMoves).toHaveBeenCalledWith(finding);
    expect(onOpenGames).toHaveBeenCalledWith(finding);
  });

  it('renders the em dash instead of an eval bar without eval data', () => {
    renderFindings(
      emptyResponse({
        white_weaknesses: [makeFinding({ avg_eval_pawns: null, eval_n: 0 })],
      }),
    );
    expect(screen.getByTestId('opening-findings-weakness-card-0-eval-none')).toBeTruthy();
    expect(screen.queryByTestId('opening-findings-weakness-card-0-eval')).toBeNull();
  });
});

describe('OpeningFindings Not clear yet', () => {
  const tenRows = Array.from({ length: 10 }, (_, i) =>
    makeFinding({ confidence: 'medium', score: 0.4, n_games: 30 + i }),
  );

  it('uses the full backend count in the header and hides the rows until expanded', () => {
    renderFindings(
      emptyResponse({
        white_weaknesses: [makeFinding()],
        white_weaknesses_not_clear: tenRows,
        white_weaknesses_not_clear_count: 12,
      }),
    );
    const toggle = screen.getByTestId('opening-findings-weakness-unclear-toggle');
    expect(toggle.textContent).toContain('Not clear yet (12)');
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(screen.queryByTestId('opening-findings-weakness-unclear-list')).toBeNull();
  });

  it('expands to uncoloured finding cards and tracks the expand once', () => {
    renderFindings(
      emptyResponse({
        white_weaknesses: [makeFinding()],
        white_weaknesses_not_clear: [
          ...tenRows.slice(0, 2),
          makeFinding({ confidence: 'medium', is_current: false }),
        ],
        white_weaknesses_not_clear_count: 3,
      }),
    );
    const toggle = screen.getByTestId('opening-findings-weakness-unclear-toggle');
    fireEvent.click(toggle);

    const card0 = screen.getByTestId('opening-findings-weakness-unclear-card-0');
    expect(card0.textContent).toContain('After 1. e4');
    expect(card0.textContent).toContain('30 games');
    // Medium confidence never passes the 99% gate, so the score stays uncoloured.
    const score0 = screen.getByTestId('opening-findings-weakness-unclear-card-0-score');
    expect(score0.textContent).toBe('40%');
    expect(score0.style.color).toBe('');
    expect(screen.queryByTestId('opening-findings-weakness-unclear-card-0-older')).toBeNull();
    expect(screen.getByTestId('opening-findings-weakness-unclear-card-2-older').textContent).toBe(
      'older games',
    );
    expect(panelOpenTargets()).toEqual(['opening-findings-unclear']);

    // Collapsing never tracks.
    fireEvent.click(toggle);
    expect(screen.queryByTestId('opening-findings-weakness-unclear-list')).toBeNull();
    expect(panelOpenTargets()).toEqual(['opening-findings-unclear']);
  });

  it('is hidden entirely when the medium count is zero', () => {
    renderFindings(emptyResponse({ white_weaknesses: [makeFinding()] }));
    expect(screen.queryByTestId('opening-findings-weakness-unclear-toggle')).toBeNull();
  });
});

describe('OpeningFindings empty state', () => {
  it('says nothing is clear yet and counts the leaning moves', () => {
    renderFindings(emptyResponse({ black_weaknesses_not_clear_count: 3 }), 'black');
    expect(screen.getByTestId('opening-findings-weakness-empty').textContent).toBe(
      'Nothing clear yet as Black. 3 moves lean this way, but could still be chance.',
    );
  });

  it('uses the singular for one leaning move', () => {
    renderFindings(emptyResponse({ white_strengths_not_clear_count: 1 }), 'white');
    expect(screen.getByTestId('opening-findings-strength-empty').textContent).toBe(
      'Nothing clear yet as White. 1 move leans this way, but could still be chance.',
    );
  });

  it('shows only the first sentence when no moves lean', () => {
    renderFindings(emptyResponse(), 'black');
    expect(screen.getByTestId('opening-findings-weakness-empty').textContent).toBe(
      'Nothing clear yet as Black.',
    );
  });
});

describe('OpeningFindings loading and error', () => {
  it('shows the skeleton while loading', () => {
    insightsQuery.current = { data: undefined, isLoading: true, isError: false, refetch: vi.fn() };
    render(
      <OpeningFindings color="white" debouncedFilters={FILTERS} onOpenMoves={() => {}} onOpenGames={() => {}} />,
    );
    expect(screen.getByTestId('opening-findings-loading')).toBeTruthy();
  });

  it('shows the load error with a retry that refetches, never an empty state', () => {
    const refetch = vi.fn();
    insightsQuery.current = { data: undefined, isLoading: false, isError: true, refetch };
    render(
      <OpeningFindings color="white" debouncedFilters={FILTERS} onOpenMoves={() => {}} onOpenGames={() => {}} />,
    );
    expect(screen.getByRole('alert').textContent).toMatch(/Failed to load opening insights/);
    expect(screen.queryByTestId('opening-findings-weakness-empty')).toBeNull();
    fireEvent.click(screen.getByTestId('btn-opening-findings-retry'));
    expect(refetch).toHaveBeenCalledTimes(1);
  });
});
