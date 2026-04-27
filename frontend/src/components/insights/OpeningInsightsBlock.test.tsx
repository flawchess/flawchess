// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// IntersectionObserver is not available in jsdom — stub it for LazyMiniBoard inside OpeningFindingCard.
class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

// Avoid SVG/canvas rendering of the mini-board in jsdom.
vi.mock('react-chessboard', () => ({
  Chessboard: vi.fn(() => null),
}));

import { OpeningInsightsBlock } from './OpeningInsightsBlock';
import type { OpeningInsightFinding, OpeningInsightsResponse } from '@/types/insights';
import type { FilterState } from '@/components/filters/FilterPanel';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return { ...actual, apiClient: { post: vi.fn() } };
});
import { apiClient } from '@/api/client';

const DEFAULT_FILTERS: FilterState = {
  color: 'white',
  matchSide: 'both',
  recency: 'year',
  timeControls: null,
  platforms: null,
  rated: null,
  opponentType: 'human',
  opponentStrength: 'any',
};

function makeFinding(overrides: Partial<OpeningInsightFinding> = {}): OpeningInsightFinding {
  return {
    color: 'white',
    classification: 'weakness',
    severity: 'major',
    opening_name: 'Test Opening',
    opening_eco: 'A00',
    display_name: 'Test Opening',
    entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    entry_san_sequence: ['e4', 'c5', 'Nf3'],
    entry_full_hash: '111',
    candidate_move_san: 'd4',
    resulting_full_hash: '222',
    n_games: 25,
    wins: 5,
    draws: 5,
    losses: 15,
    win_rate: 0.20,
    loss_rate: 0.60,
    score: 0.30,
    ...overrides,
  };
}

const EMPTY_RESPONSE: OpeningInsightsResponse = {
  white_weaknesses: [],
  black_weaknesses: [],
  white_strengths: [],
  black_strengths: [],
};

function createWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

// Vitest 4 does not auto-cleanup RTL mounts — rendered DOM from a previous
// test bleeds into the next one's screen queries if we don't explicitly unmount.
afterEach(() => {
  cleanup();
});

describe('OpeningInsightsBlock', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders skeleton while loading', () => {
    // Never resolves — keeps query in loading state
    (apiClient.post as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise(() => {}));
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} />
      </Wrapper>,
    );
    expect(screen.getByTestId('opening-insights-block')).toBeTruthy();
    // Skeleton uses animate-pulse
    const block = screen.getByTestId('opening-insights-block');
    expect(block.querySelector('.animate-pulse')).not.toBeNull();
  });

  it('renders error state with role=alert and a Try again button', async () => {
    (apiClient.post as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network'));
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} />
      </Wrapper>,
    );
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeTruthy();
    });
    expect(screen.getByTestId('btn-opening-insights-retry')).toBeTruthy();
  });

  it('renders empty-block message when all four sections are empty', async () => {
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: EMPTY_RESPONSE });
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} />
      </Wrapper>,
    );
    await waitFor(() => {
      // Block-level empty message references the threshold copy
      expect(screen.getByTestId('opening-insights-block').textContent).toMatch(
        /No opening findings cleared the threshold/,
      );
    });
  });

  it('renders four sections when at least one has findings', async () => {
    const populated: OpeningInsightsResponse = {
      ...EMPTY_RESPONSE,
      white_weaknesses: [makeFinding({ color: 'white', classification: 'weakness' })],
      black_strengths: [makeFinding({ color: 'black', classification: 'strength', severity: 'minor', win_rate: 0.58 })],
    };
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: populated });
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} />
      </Wrapper>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('opening-insights-section-white-weaknesses')).toBeTruthy();
    });
    expect(screen.getByTestId('opening-insights-section-black-weaknesses')).toBeTruthy();
    expect(screen.getByTestId('opening-insights-section-white-strengths')).toBeTruthy();
    expect(screen.getByTestId('opening-insights-section-black-strengths')).toBeTruthy();
  });

  it('renders per-section empty message when only some sections have findings', async () => {
    const populated: OpeningInsightsResponse = {
      ...EMPTY_RESPONSE,
      white_weaknesses: [makeFinding()],
    };
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: populated });
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} />
      </Wrapper>,
    );
    await waitFor(() => {
      // The black-weaknesses section is empty — it should display a muted per-section message
      const blackWeaknesses = screen.getByTestId('opening-insights-section-black-weaknesses');
      expect(blackWeaknesses.textContent).toMatch(/No weakness findings cleared the threshold/);
    });
  });

  it('delegates card click to onFindingClick prop', async () => {
    const finding = makeFinding({ color: 'white', display_name: 'Click Me' });
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { ...EMPTY_RESPONSE, white_weaknesses: [finding] },
    });
    const onFindingClick = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={onFindingClick} />
      </Wrapper>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('opening-finding-card-0')).toBeTruthy();
    });
    fireEvent.click(screen.getByTestId('opening-finding-card-0'));
    expect(onFindingClick).toHaveBeenCalledWith(finding);
  });

});
