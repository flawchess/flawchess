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

// Stub the Tooltip primitive so card renders don't need a TooltipProvider wrapper.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => children,
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
  opponentStrength: { min: null, max: null },
};

function makeFinding(overrides: Partial<OpeningInsightFinding> = {}): OpeningInsightFinding {
  return {
    color: 'white',
    classification: 'weakness',
    severity: 'major',
    opening_name: 'Sample',
    opening_eco: 'A00',
    display_name: 'Sample',
    entry_fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR',
    entry_san_sequence: ['e4'],
    entry_full_hash: '0',
    candidate_move_san: 'e5',
    resulting_full_hash: '0',
    n_games: 50,
    wins: 10,
    draws: 10,
    losses: 30,
    score: 0.30,
    confidence: 'high',     // Phase 76 D-21
    p_value: 0.01,          // Phase 76 D-21
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
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} onOpenGames={() => {}} />
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
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} onOpenGames={() => {}} />
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
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} onOpenGames={() => {}} />
      </Wrapper>,
    );
    await waitFor(() => {
      // Block-level empty message references the threshold copy
      expect(screen.getByTestId('opening-insights-block').textContent).toMatch(
        /No opening findings/,
      );
    });
  });

  it('renders four sections when at least one has findings', async () => {
    const populated: OpeningInsightsResponse = {
      ...EMPTY_RESPONSE,
      white_weaknesses: [makeFinding({ color: 'white', classification: 'weakness' })],
      black_strengths: [makeFinding({ color: 'black', classification: 'strength', severity: 'minor', score: 0.58 })],
    };
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: populated });
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} onOpenGames={() => {}} />
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
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} onOpenGames={() => {}} />
      </Wrapper>,
    );
    await waitFor(() => {
      // The black-weaknesses section is empty — it should display a muted per-section message
      const blackWeaknesses = screen.getByTestId('opening-insights-section-black-weaknesses');
      expect(blackWeaknesses.textContent).toMatch(/No weakness findings/);
    });
  });

  it('delegates Moves link click to onFindingClick prop', async () => {
    const finding = makeFinding({ color: 'white', display_name: 'Click Me' });
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { ...EMPTY_RESPONSE, white_weaknesses: [finding] },
    });
    const onFindingClick = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <OpeningInsightsBlock
          debouncedFilters={DEFAULT_FILTERS}
          onFindingClick={onFindingClick}
          onOpenGames={() => {}}
        />
      </Wrapper>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('opening-finding-card-0')).toBeTruthy();
    });
    // Mobile + desktop layouts both render — click the first Moves button.
    const movesBtns = screen.getAllByTestId('opening-finding-card-0-moves');
    fireEvent.click(movesBtns[0]!);
    expect(onFindingClick).toHaveBeenCalledWith(finding);
  });

  it('delegates Games link click to onOpenGames prop', async () => {
    const finding = makeFinding({ color: 'white', display_name: 'Games Click', n_games: 42 });
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { ...EMPTY_RESPONSE, white_weaknesses: [finding] },
    });
    const onOpenGames = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <OpeningInsightsBlock
          debouncedFilters={DEFAULT_FILTERS}
          onFindingClick={() => {}}
          onOpenGames={onOpenGames}
        />
      </Wrapper>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('opening-finding-card-0')).toBeTruthy();
    });
    const gamesBtns = screen.getAllByTestId('opening-finding-card-0-games');
    fireEvent.click(gamesBtns[0]!);
    expect(onOpenGames).toHaveBeenCalledWith(finding);
  });

});

describe('Phase 76 — Section-title InfoPopover triggers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function renderBlock(responseOverrides: Partial<OpeningInsightsResponse> = {}) {
    const data: OpeningInsightsResponse = {
      ...EMPTY_RESPONSE,
      ...responseOverrides,
    };
    (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data });
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <OpeningInsightsBlock debouncedFilters={DEFAULT_FILTERS} onFindingClick={() => {}} onOpenGames={() => {}} />
      </Wrapper>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('opening-insights-section-white-weaknesses')).toBeTruthy();
    });
    return screen;
  }

  it('renders an InfoPopover trigger on each of the four section headers', async () => {
    await renderBlock({ white_weaknesses: [makeFinding()] });
    // The InfoPopover trigger renders an icon button; testid pattern matches all 4.
    const triggers = screen.getAllByTestId(/^opening-insights-section-(white|black)-(weaknesses|strengths)-info$/);
    expect(triggers).toHaveLength(4);
  });

  it('each trigger has an ARIA label matching the section title', async () => {
    await renderBlock({ white_weaknesses: [makeFinding()] });
    expect(
      screen.getByTestId('opening-insights-section-white-weaknesses-info').getAttribute('aria-label'),
    ).toContain('White Opening Weaknesses');
    expect(
      screen.getByTestId('opening-insights-section-black-weaknesses-info').getAttribute('aria-label'),
    ).toContain('Black Opening Weaknesses');
    expect(
      screen.getByTestId('opening-insights-section-white-strengths-info').getAttribute('aria-label'),
    ).toContain('White Opening Strengths');
    expect(
      screen.getByTestId('opening-insights-section-black-strengths-info').getAttribute('aria-label'),
    ).toContain('Black Opening Strengths');
  });

  it('does not render a block-level "Opening Insights" h2 title (D-18)', async () => {
    await renderBlock({ white_weaknesses: [makeFinding()] });
    // No top-level h2 with this exact text.
    const h2 = screen.queryByRole('heading', { level: 2, name: /Opening Insights/i });
    expect(h2).toBeNull();
  });
});
