// @vitest-environment jsdom
/**
 * Page-level integration tests for the Endgames Stats tab
 * after the ranked-sample Overall section replaced the filtered composite.
 *
 * Strategy: full-page render of <EndgamesPage /> is heavy, so the data hooks are
 * mocked with a ranked-payload fixture plus a minimal filtered stats payload (which
 * only feeds the Games tab). Chart sub-components that
 * do not participate in the assertions are stubbed; EndgameScoreOverTimeChart and
 * the new OverallSection render for real.
 */

import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { cloneElement, isValidElement } from 'react';
import { TooltipProvider } from '@/components/ui/tooltip';
import {
  buildRankedResponse,
  buildRankedTc,
} from '@/components/endgames/stats/rankedFixtures';
import type {
  EndgameEloTimelineCombo,
  EndgameRankedStatsResponse,
  EndgameStatsResponse,
  ScoreGapTimelinePoint,
} from '@/types/endgames';

// ── Recharts: jsdom has zero-size parents; ResponsiveContainer would refuse
// to render. Replace it with a fixed-size shim so EndgameScoreOverTimeChart
// produces its testids.
vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) => (
      <div style={{ width: 800, height: 400 }}>
        {isValidElement(children)
          ? cloneElement(
              children as ReactElement<{ width?: number; height?: number }>,
              { width: 800, height: 400 },
            )
          : children}
      </div>
    ),
  };
});

// ── Mock heavy chart components that do not participate in the assertions.
vi.mock('@/components/charts/EndgameEloTimelineSection', () => ({
  EndgameEloTimelineSection: () => <div data-testid="mock-endgame-elo-timeline-section" />,
}));
vi.mock('@/components/results/GameCardList', () => ({
  GameCardList: () => <div data-testid="mock-game-card-list" />,
}));
vi.mock('@/components/insights/EndgameInsightsBlock', () => ({
  EndgameInsightsBlock: () => <div data-testid="mock-endgame-insights-block" />,
}));

// ── Mock data hooks.
const statsState: { data: EndgameStatsResponse | null } = { data: null };
const rankedState: { data: EndgameRankedStatsResponse | null } = { data: null };

vi.mock('@/hooks/useEndgames', () => ({
  useEndgameStats: () => ({
    data: statsState.data,
    isLoading: false,
    isError: false,
  }),
  useEndgameRankedStats: () => ({
    data: rankedState.data,
    isLoading: false,
    isError: false,
  }),
  useEndgameGames: () => ({
    data: { games: [], matched_count: 0, offset: 0, limit: 20 },
    isLoading: false,
    isError: false,
  }),
}));

vi.mock('@/hooks/useEndgameInsights', () => ({
  useEndgameInsightsGenerating: () => false,
  useCachedEndgameInsights: () => ({ data: null, isLoading: false, isError: false }),
  useEndgameInsights: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    error: null,
  }),
}));

vi.mock('@/hooks/useImport', () => ({
  useActiveJobs: () => ({ data: [], isLoading: false, isError: false }),
}));

// EvalCoverageHeader is mounted by the page; mock the hook so the test does not
// need a QueryClientProvider.
vi.mock('@/hooks/useEvalCoverage', () => ({
  useEvalCoverage: () => ({
    pendingCount: 0,
    totalCount: 0,
    pct: 100,
    hasPendingEvals: false,
    isLoading: false,
  }),
}));

// The page gates its content on useReadiness().tier2.
vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({
    tier1: true,
    tier2: true,
    pendingCount: 0,
    totalCount: 0,
    isLoading: false,
    isError: false,
  }),
}));

// jsdom shims required by the existing component.
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
  if (!('scrollTo' in window) || typeof window.scrollTo !== 'function') {
    window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  }
});

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
});

// Import the page after the mocks above are registered.
import { EndgamesPage } from '../Endgames';

// ── Fixture builders ──────────────────────────────────────────────────────
function buildStats(): EndgameStatsResponse {
  return {
    total_games: 100,
    endgame_games: 50,
    categories: [
      {
        endgame_class: 'mixed',
        label: 'Mixed',
        wins: 25,
        draws: 10,
        losses: 15,
        total: 50,
        win_pct: 50,
        draw_pct: 20,
        loss_pct: 30,
      },
    ],
  } as unknown as EndgameStatsResponse;
}

// A single point is enough for the score-over-time chart to render its outermost
// <div data-testid="endgame-score-timeline-chart">.
const SCORE_GAP_POINT: ScoreGapTimelinePoint = {
  date: '2026-01-05',
  score_difference: 0.05,
  endgame_game_count: 25,
  non_endgame_game_count: 25,
  per_week_total_games: 50,
  per_week_endgame_games: 25,
  endgame_score: 0.55,
  non_endgame_score: 0.5,
  endgame_opp_rating_avg: 1500,
  non_endgame_opp_rating_avg: 1500,
};

const ELO_COMBO: EndgameEloTimelineCombo = {
  combo_key: 'chess_com_blitz',
  platform: 'chess.com',
  time_control: 'blitz',
  points: [
    {
      date: '2026-01-05',
      endgame_elo: 1620,
      non_endgame_elo: 1540,
      actual_elo: 1580,
      endgame_games_in_window: 50,
      per_week_endgame_games: 4,
      per_week_total_games: 18,
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/endgames/stats']}>
      <TooltipProvider>
        <EndgamesPage />
      </TooltipProvider>
    </MemoryRouter>,
  );
}

function firstText(testId: string): string {
  const nodes = screen.getAllByTestId(testId);
  return nodes[0]?.textContent ?? '';
}

// ── Tests ─────────────────────────────────────────────────────────────────
describe('Endgames page: ranked Overall section', () => {
  beforeEach(() => {
    statsState.data = buildStats();
    rankedState.data = buildRankedResponse([
      buildRankedTc('blitz', { ranked_games: 180 }),
      buildRankedTc('rapid', {
        ranked_games: 871,
        score_gap_timeline: [SCORE_GAP_POINT],
        elo_timeline: [ELO_COMBO],
      }),
    ]);
  });

  it('renders the Overall section with the score card for the default TC', () => {
    const { container } = renderPage();
    // Desktop and mobile layouts each mount the Stats tab, so jsdom sees two.
    expect(
      container.querySelectorAll('[data-testid="endgame-overall-section"]').length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      container.querySelectorAll('[data-testid="endgame-overall-score-card"]').length,
    ).toBeGreaterThanOrEqual(1);
  });

  it('shows both score columns and the Endgame Score Gap row from the ranked payload', () => {
    renderPage();
    // Fixture overall: no-endgame 57W/4D/39L -> 59.0%; endgame 45W/9D/46L -> 49.5%.
    expect(firstText('endgame-overall-no-endgame-score')).toBe('59.0%');
    expect(firstText('endgame-overall-endgame-score')).toBe('49.5%');
    expect(firstText('endgame-overall-score-gap-value')).toBe('+5%');
    expect(screen.getAllByTestId('endgame-overall-score-gap-bar').length).toBeGreaterThanOrEqual(1);
  });

  it('shows the entry flow and the Eval Score Gap row in the second card', () => {
    renderPage();
    expect(screen.getAllByTestId('endgame-overall-entry-card').length).toBeGreaterThanOrEqual(1);
    expect(firstText('endgame-overall-entry-eval')).toBe('+0.31');
    expect(firstText('endgame-overall-expected')).toBe('53.0%');
    expect(firstText('endgame-overall-actual')).toBe('48.7%');
    expect(firstText('endgame-overall-eval-score-gap-value')).toBe('+5%');
  });

  it('defaults to the TC with the most ranked games', () => {
    renderPage();
    const rapid = screen.getAllByTestId('tc-switch-endgame-stats-rapid')[0];
    const blitz = screen.getAllByTestId('tc-switch-endgame-stats-blitz')[0];
    expect(rapid?.getAttribute('aria-pressed')).toBe('true');
    expect(blitz?.getAttribute('aria-pressed')).toBe('false');
  });

  it('keeps the Score Gap timeline and renders the ELO timeline directly below it', () => {
    const { container } = renderPage();
    const scoreChart = container.querySelectorAll(
      '[data-testid="endgame-score-timeline-chart"]',
    )[0];
    const eloSection = container.querySelectorAll(
      '[data-testid="endgame-elo-timeline-section"]',
    )[0];
    expect(scoreChart).toBeTruthy();
    expect(eloSection).toBeTruthy();
    const relation = scoreChart!.compareDocumentPosition(eloSection!);
    expect(relation & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // The ELO section is a sibling inside the Overall section, not part of the metrics block.
    for (const metrics of container.querySelectorAll(
      '[data-testid="mock-endgame-metrics-section"]',
    )) {
      expect(metrics.contains(eloSection!)).toBe(false);
    }
  });

  it('contains the concepts accordion paragraphs ("Entry Eval" + "Endgame Score")', () => {
    const { container } = renderPage();
    openConceptsAccordion(container);
    expect(screen.getAllByText(/Entry Eval:/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Endgame Score:/).length).toBeGreaterThan(0);
  });

  it('places the Entry Eval and Endgame Score paragraphs after Recovery', () => {
    const { container } = renderPage();
    openConceptsAccordion(container);
    const accordionItem = container.querySelector('[data-testid="endgame-concepts-trigger"]');
    expect(accordionItem).not.toBeNull();
    const paragraphs = Array.from(accordionItem!.querySelectorAll('p')) as HTMLParagraphElement[];
    const text = paragraphs.map((p) => p.textContent ?? '');
    const recoveryIdx = text.findIndex((t) => /Recovery:/.test(t));
    const entryEvalIdx = text.findIndex((t) => /Entry Eval:/.test(t));
    const endgameScoreIdx = text.findIndex((t) => /Endgame Score:/.test(t));
    expect(recoveryIdx).toBeGreaterThanOrEqual(0);
    expect(entryEvalIdx).toBeGreaterThan(recoveryIdx);
    expect(endgameScoreIdx).toBeGreaterThan(entryEvalIdx);
  });

  // The wrapper renders the ELO section whenever ranked data
  // is present and delegates empty/error/loading to the component itself.
  it('renders the Endgame ELO Timeline wrapper even when combos array is empty', () => {
    rankedState.data = buildRankedResponse([buildRankedTc('rapid', { elo_timeline: [] })]);
    const { container } = renderPage();
    expect(
      container.querySelectorAll('[data-testid="endgame-elo-timeline-section"]').length,
    ).toBeGreaterThanOrEqual(1);
  });
});

/**
 * Click the first concepts-accordion trigger so radix mounts its
 * AccordionContent into the DOM.
 */
function openConceptsAccordion(container: HTMLElement): void {
  const trigger = container.querySelector(
    '[data-testid="endgame-concepts-trigger"] [data-slot="accordion-trigger"]',
  ) as HTMLButtonElement | null;
  if (trigger) {
    act(() => {
      fireEvent.click(trigger);
    });
  }
}
