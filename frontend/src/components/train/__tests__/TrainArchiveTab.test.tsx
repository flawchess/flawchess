// @vitest-environment jsdom
/**
 * TrainArchiveTab.test.tsx — the Archive tab on its own: the Mastered / Parked
 * toggle with counts and explainers, URL-held pagination, the per-list empty
 * states, and the placeholder-data rule that keeps the other list's cards off
 * the screen during a list switch. The card is stubbed (it has its own tests).
 */
import { useEffect } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, useLocation, useNavigate } from 'react-router';
import type { NavigateFunction } from 'react-router';
import { TooltipProvider } from '@/components/ui/tooltip';
import { parseTrainRoute } from '@/lib/trainRoute';
import type { ArchiveList, TrainArchiveItem, TrainArchiveResponse } from '@/types/train';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      ...actual.trainApi,
      getArchive: vi.fn(),
      getProgress: vi.fn(),
    },
  };
});

// The card has its own tests; the stub carries what the grid decides: its key and list.
vi.mock('@/components/train/TrainPuzzleCard', () => ({
  TrainPuzzleCard: ({ item, list }: { item: TrainArchiveItem; list: ArchiveList }) => (
    <div data-testid={`card-${item.game_id}-${item.ply}`} data-list={list} />
  ),
}));

import { trainApi } from '@/api/client';
import { TrainArchiveTab } from '@/components/train/TrainArchiveTab';

const getArchive = vi.mocked(trainApi.getArchive);
const getProgress = vi.mocked(trainApi.getProgress);

const PAGE_SIZE = 24;
const MASTERED_COUNT = 12;
const PARKED_COUNT = 3;

const PROGRESS = {
  session_streak_count: 0,
  shield_level: 0,
  current_week_completed: 0,
  current_week_required: null,
  streak_reset_notice: false,
  mastered_count: MASTERED_COUNT,
  parked_count: PARKED_COUNT,
  waiting_count: 0,
  pool_state: 'available',
  next_due_date: null,
  badge_visible: false,
} as const;

function makeItem(gameId: number, ply = 20): TrainArchiveItem {
  return {
    game_id: gameId,
    ply,
    fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    last_move_uci: 'd7d5',
    played_move_uci: 'g1f3',
    played_move_san: 'Nf3',
    severity: 'blunder',
    user_color: 'white',
    last_solved_at: '2026-10-03T10:00:00Z',
    fail_count: 0,
    white_username: 'me',
    black_username: 'rival',
    white_rating: 1500,
    black_rating: 1480,
    played_at: '2026-09-30T10:00:00Z',
    time_control_bucket: 'blitz',
    time_control_str: '600+0',
  };
}

function page(items: TrainArchiveItem[], total = items.length): TrainArchiveResponse {
  return { items, total };
}

/** A promise the test settles by hand, to observe the in-flight render. */
function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve: (value: T) => void = () => undefined;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

const navigateRef: { current: NavigateFunction | null } = { current: null };

function LocationProbe() {
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    navigateRef.current = navigate;
  }, [navigate]);
  return <div data-testid="location-probe">{location.pathname + location.search}</div>;
}

/** Mirrors the page: the list comes from the path, as `Train.tsx` passes it. */
function Harness() {
  const { pathname } = useLocation();
  const route = parseTrainRoute(pathname);
  if (route?.tab !== 'archive') return null;
  return <TrainArchiveTab list={route.list} />;
}

function renderTab(initialEntries: string[], initialIndex?: number) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={initialEntries} initialIndex={initialIndex}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <LocationProbe />
          <Harness />
        </TooltipProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

function currentPath(): string {
  return screen.getByTestId('location-probe').textContent ?? '';
}

function lastArchiveCall(): { list: string; limit: number; offset: number } {
  const call = getArchive.mock.calls.at(-1);
  if (!call) throw new Error('getArchive was never called');
  return call[0];
}

beforeEach(() => {
  navigateRef.current = null;
  vi.stubGlobal('scrollTo', vi.fn());
  getArchive.mockReset();
  getArchive.mockImplementation(async () => page([makeItem(1)]));
  getProgress.mockReset();
  getProgress.mockImplementation(async () => ({ ...PROGRESS }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('toggle', () => {
  it('shows the counts from progress', async () => {
    renderTab(['/train/archive']);

    await waitFor(() =>
      expect(screen.getByTestId('train-archive-toggle-mastered').textContent).toBe(
        `Mastered ${MASTERED_COUNT}`,
      ),
    );
    expect(screen.getByTestId('train-archive-toggle-parked').textContent).toBe(
      `Parked ${PARKED_COUNT}`,
    );
  });

  it('carries no number while progress is pending, never 0', async () => {
    getProgress.mockImplementation(() => new Promise(() => undefined));
    renderTab(['/train/archive']);

    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());
    expect(screen.getByTestId('train-archive-toggle-mastered').textContent).toBe('Mastered');
    expect(screen.getByTestId('train-archive-toggle-parked').textContent).toBe('Parked');
  });

  it('carries no number when progress errors, never 0', async () => {
    getProgress.mockImplementation(async () => {
      throw new Error('progress failed');
    });
    renderTab(['/train/archive']);

    await waitFor(() => expect(getProgress).toHaveBeenCalled());
    await act(async () => {});
    expect(screen.getByTestId('train-archive-toggle-mastered').textContent).toBe('Mastered');
    expect(screen.getByTestId('train-archive-toggle-parked').textContent).toBe('Parked');
  });

  it('clicking Parked moves the URL, drops the page param and asks for parked at offset 0', async () => {
    renderTab(['/train/archive?page=2']);
    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());

    fireEvent.click(screen.getByTestId('train-archive-toggle-parked'));

    expect(currentPath()).toBe('/train/archive/parked');
    await waitFor(() => expect(lastArchiveCall()).toEqual({ list: 'parked', limit: PAGE_SIZE, offset: 0 }));
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0 });
  });

  it('re-tapping the active item does nothing', async () => {
    renderTab(['/train/archive']);
    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());
    const calls = getArchive.mock.calls.length;

    fireEvent.click(screen.getByTestId('train-archive-toggle-mastered'));

    await act(async () => {});
    expect(currentPath()).toBe('/train/archive');
    expect(getArchive.mock.calls.length).toBe(calls);
    expect(window.scrollTo).not.toHaveBeenCalled();
  });

  it('hides the pills on Mastered once progress reports nothing parked, keeping the sentence', async () => {
    getProgress.mockImplementation(async () => ({ ...PROGRESS, parked_count: 0 }));
    renderTab(['/train/archive']);

    await waitFor(() => expect(screen.queryByTestId('train-archive-toggle')).toBeNull());
    expect(screen.getByTestId('train-archive-explainer').textContent).toBe(
      'Solved correctly twice in a row.',
    );
  });

  it('keeps the pills on an empty Parked list, as the way back to Mastered', async () => {
    getProgress.mockImplementation(async () => ({ ...PROGRESS, parked_count: 0 }));
    getArchive.mockImplementation(async () => page([], 0));
    renderTab(['/train/archive/parked']);

    await waitFor(() =>
      expect(screen.getByTestId('train-archive-toggle-parked').textContent).toBe('Parked 0'),
    );
    fireEvent.click(screen.getByTestId('train-archive-toggle-mastered'));
    expect(currentPath()).toBe('/train/archive');
  });

  it.each([
    ['/train/archive', 'Solved correctly twice in a row.'],
    ['/train/archive/parked', 'Missed 3 or more times and set aside.'],
  ])('on %s the sentence below the toggle explains the selected list', async (path, copy) => {
    renderTab([path]);
    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());

    expect(screen.getByTestId('train-archive-explainer').textContent).toBe(copy);
  });

  it('the sentence follows the toggle', async () => {
    renderTab(['/train/archive']);
    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());

    fireEvent.click(screen.getByTestId('train-archive-toggle-parked'));

    expect(screen.getByTestId('train-archive-explainer').textContent).toBe(
      'Missed 3 or more times and set aside.',
    );
  });
});

describe('pagination', () => {
  it('/train/archive/parked?page=2 asks for parked at offset 24 and marks page 2 active', async () => {
    getArchive.mockImplementation(async () => page([makeItem(21)], 25));
    renderTab(['/train/archive/parked?page=2']);

    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());
    expect(lastArchiveCall()).toEqual({ list: 'parked', limit: PAGE_SIZE, offset: PAGE_SIZE });
    expect(screen.getByTestId('pagination-page-2').getAttribute('aria-current')).toBe('page');
  });

  it('clicking page 2 pushes ?page=2 and Back returns to page 1 and offset 0', async () => {
    getArchive.mockImplementation(async ({ offset }) =>
      page([makeItem(offset === 0 ? 1 : 21)], 25),
    );
    renderTab(['/train/archive']);
    await waitFor(() => expect(screen.getByTestId('card-1-20')).not.toBeNull());

    fireEvent.click(screen.getByTestId('pagination-page-2'));

    expect(currentPath()).toBe('/train/archive?page=2');
    await waitFor(() => expect(screen.getByTestId('card-21-20')).not.toBeNull());
    expect(lastArchiveCall().offset).toBe(PAGE_SIZE);
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0 });

    act(() => {
      navigateRef.current?.(-1);
    });

    expect(currentPath()).toBe('/train/archive');
    await waitFor(() => expect(screen.getByTestId('card-1-20')).not.toBeNull());
    expect(lastArchiveCall().offset).toBe(0);
  });

  it('clicking page 1 again leaves the canonical URL with no page param', async () => {
    getArchive.mockImplementation(async () => page([makeItem(21)], 25));
    renderTab(['/train/archive?page=2']);
    await waitFor(() => expect(screen.getByTestId('pagination-page-1')).not.toBeNull());

    fireEvent.click(screen.getByTestId('pagination-page-1'));

    expect(currentPath()).toBe('/train/archive');
  });

  it('shows no pagination when the list fits one page', async () => {
    getArchive.mockImplementation(async () => page([makeItem(1)], PAGE_SIZE));
    renderTab(['/train/archive']);

    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());
    expect(screen.queryByTestId('pagination-next')).toBeNull();
  });

  it('an over-range page replaces the URL with the last page, adding no history entry', async () => {
    getArchive.mockImplementation(async ({ offset }) =>
      offset >= 40 ? page([], 25) : page([makeItem(21)], 25),
    );
    // Two entries, so Back after the replace proves no entry was added.
    renderTab(['/train/archive', '/train/archive?page=99'], 1);

    await waitFor(() => expect(currentPath()).toBe('/train/archive?page=2'));
    await waitFor(() => expect(screen.getByTestId('card-21-20')).not.toBeNull());

    act(() => {
      navigateRef.current?.(-1);
    });
    expect(currentPath()).toBe('/train/archive');
  });

  it('?page=abc asks for offset 0', async () => {
    renderTab(['/train/archive?page=abc']);

    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());
    expect(lastArchiveCall().offset).toBe(0);
  });
});

describe('empty and error states', () => {
  it.each([
    ['/train/archive', 'train-archive-empty-mastered', 'No mastered puzzles yet'],
    ['/train/archive/parked', 'train-archive-empty-parked', 'Nothing parked'],
  ])('%s empty list shows its own copy and a link to Today, no import button', async (path, testId, title) => {
    getArchive.mockImplementation(async () => page([], 0));
    renderTab([path]);

    await waitFor(() => expect(screen.getByTestId(testId)).not.toBeNull());
    expect(screen.getByTestId(testId).textContent).toContain(title);
    const other = testId.endsWith('mastered')
      ? 'train-archive-empty-parked'
      : 'train-archive-empty-mastered';
    expect(screen.queryByTestId(other)).toBeNull();

    const cta = screen.getByTestId('btn-train-archive-today');
    expect(cta.getAttribute('href')).toBe('/train');
    expect(screen.queryByText(/import/i)).toBeNull();
    expect(document.querySelector('a[href*="import"]')).toBeNull();
  });

  it('the empty list still shows the toggle so the other list is one tap away', async () => {
    getArchive.mockImplementation(async () => page([], 0));
    renderTab(['/train/archive/parked']);

    await waitFor(() => expect(screen.getByTestId('train-archive-empty-parked')).not.toBeNull());
    expect(screen.getByTestId('train-archive-toggle')).not.toBeNull();
  });

  it('a failed request shows the load error and neither empty copy', async () => {
    getArchive.mockImplementation(async () => {
      throw new Error('archive failed');
    });
    renderTab(['/train/archive']);

    await waitFor(() => expect(screen.getByTestId('train-archive-error')).not.toBeNull());
    expect(screen.queryByTestId('train-archive-empty-mastered')).toBeNull();
    expect(screen.queryByTestId('train-archive-empty-parked')).toBeNull();
    expect(screen.queryByTestId('train-archive-grid')).toBeNull();
  });

  it('shows the skeleton while the first page loads', async () => {
    getArchive.mockImplementation(() => new Promise(() => undefined));
    renderTab(['/train/archive']);

    await waitFor(() => expect(screen.getByTestId('train-archive-loading')).not.toBeNull());
    expect(screen.queryByTestId('train-archive-empty-mastered')).toBeNull();
  });
});

describe('placeholder data across navigation', () => {
  it('a list switch with the new request pending shows the skeleton, not the other list cards', async () => {
    renderTab(['/train/archive']);
    await waitFor(() => expect(screen.getByTestId('card-1-20')).not.toBeNull());

    const held = deferred<TrainArchiveResponse>();
    getArchive.mockImplementation(() => held.promise);
    fireEvent.click(screen.getByTestId('train-archive-toggle-parked'));

    await waitFor(() => expect(screen.getByTestId('train-archive-loading')).not.toBeNull());
    expect(screen.queryByTestId('card-1-20')).toBeNull();

    await act(async () => {
      held.resolve(page([makeItem(2)]));
    });
    await waitFor(() => expect(screen.getByTestId('card-2-20')).not.toBeNull());
    expect(screen.getByTestId('card-2-20').getAttribute('data-list')).toBe('parked');
  });

  it('a page change with the new request pending keeps the previous cards', async () => {
    getArchive.mockImplementation(async () => page([makeItem(1)], 25));
    renderTab(['/train/archive']);
    await waitFor(() => expect(screen.getByTestId('card-1-20')).not.toBeNull());

    const held = deferred<TrainArchiveResponse>();
    getArchive.mockImplementation(() => held.promise);
    fireEvent.click(screen.getByTestId('pagination-page-2'));

    await waitFor(() => expect(lastArchiveCall().offset).toBe(PAGE_SIZE));
    expect(screen.getByTestId('card-1-20')).not.toBeNull();
    expect(screen.queryByTestId('train-archive-loading')).toBeNull();

    await act(async () => {
      held.resolve(page([makeItem(21)], 25));
    });
    await waitFor(() => expect(screen.getByTestId('card-21-20')).not.toBeNull());
  });
});

describe('scope', () => {
  it('has no Retry, Stats or filter control (out of scope for this phase)', async () => {
    renderTab(['/train/archive']);
    await waitFor(() => expect(screen.getByTestId('train-archive-grid')).not.toBeNull());

    const tab = screen.getByTestId('train-archive-tab');
    expect(tab.querySelector('[data-testid*="retry"]')).toBeNull();
    expect(tab.querySelector('[data-testid*="filter"]')).toBeNull();
    expect(tab.textContent ?? '').not.toMatch(/retry|stats/i);
  });

  it('each card is keyed by game and ply and carries the list it was rendered for', async () => {
    getArchive.mockImplementation(async () => page([makeItem(7, 11), makeItem(7, 12)]));
    renderTab(['/train/archive/parked']);

    await waitFor(() => expect(screen.getByTestId('card-7-11')).not.toBeNull());
    expect(screen.getByTestId('card-7-12').getAttribute('data-list')).toBe('parked');
  });
});
