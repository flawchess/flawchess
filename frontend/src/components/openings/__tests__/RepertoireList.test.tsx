// @vitest-environment jsdom
/**
 * RepertoireList / RepertoireCard: pinned bookmarks, the stale-bookmark chip, the collapsed
 * "Played before" group (and its single Umami event), the 20-game fade, the card links and the
 * lazily fetched score-over-time chart.
 * useRepertoireRows is covered for the colour-less bookmark and the ECO strip.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { RepertoireList } from '@/components/openings/stats/RepertoireList';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import {
  MOST_PLAYED_ROW_SERIES_ID,
  useOpeningRowTimeSeries,
} from '@/pages/openings/useOpeningRowTimeSeries';
import {
  useRepertoireRows,
  type RepertoireRowKind,
  type RepertoireRowModel,
} from '@/pages/openings/useRepertoireRows';
import { UNRELIABLE_OPACITY, ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import type { MostPlayedOpeningsResponse, OpeningWDL } from '@/types/stats';
import type {
  BookmarkTimeSeries,
  PositionBookmarkResponse,
  TimeSeriesResponse,
} from '@/types/position_bookmarks';

const trackFeature = vi.hoisted(() => vi.fn());
const useTimeSeriesMock = vi.hoisted(() => vi.fn());
const createMutate = vi.hoisted(() => vi.fn());
const deleteMutate = vi.hoisted(() => vi.fn());

vi.mock('@/hooks/usePositionBookmarks', () => ({
  useTimeSeries: useTimeSeriesMock,
  useCreatePositionBookmark: () => ({ mutate: createMutate, isPending: false }),
  useDeletePositionBookmark: () => ({ mutate: deleteMutate, isPending: false }),
}));

vi.mock('@/lib/analytics', async () => {
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics');
  return { ...actual, trackFeature };
});

vi.mock('@/components/board/LazyMiniBoard', () => ({
  LazyMiniBoard: ({ size }: { size: number }) => (
    <div data-testid="lazy-mini-board" data-size={size} />
  ),
}));

vi.mock('@/components/charts/ScoreChart', () => ({
  ScoreChart: ({ showVolume }: { showVolume?: boolean }) => (
    <div data-testid="score-chart-stub" data-volume={String(Boolean(showVolume))} />
  ),
}));

vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: vi.fn(() => ({
    tier1: true,
    tier2: true,
    pendingCount: 0,
    totalCount: 0,
    isLoading: false,
  })),
}));

beforeEach(() => {
  trackFeature.mockClear();
  createMutate.mockClear();
  deleteMutate.mockClear();
  useTimeSeriesMock.mockReset();
  useTimeSeriesMock.mockReturnValue({ data: undefined, isLoading: false, isError: false });
});

afterEach(() => {
  cleanup();
});

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function makeRow(overrides: Partial<RepertoireRowModel> & { key: string }): RepertoireRowModel {
  const kind: RepertoireRowKind = overrides.kind ?? 'current';
  return {
    kind,
    color: 'white',
    name: 'Sicilian Defense',
    moveLine: '1. e4 c5',
    fen: START_FEN,
    fullHash: '1',
    bookmark: null,
    games: 100,
    wins: 50,
    draws: 20,
    losses: 30,
    winPct: 50,
    drawPct: 20,
    lossPct: 30,
    lastPlayedAt: '2026-10-01T12:00:00Z',
    isCurrent: kind !== 'past',
    score: 0.6,
    scoreConfidence: 'high',
    scorePValue: 0.001,
    scoreCiLow: 0.5,
    scoreCiHigh: 0.7,
    avgEvalPawns: 0.9,
    evalN: 90,
    evalConfidence: 'high',
    evalPValue: 0.002,
    evalCiLow: 0.6,
    evalCiHigh: 1.2,
    series: null,
    ...overrides,
  };
}

function renderList(props: {
  bookmarkRows?: RepertoireRowModel[];
  currentRows?: RepertoireRowModel[];
  pastRows?: RepertoireRowModel[];
  currentCutoff?: string | null;
  onOpenMoves?: (pgn: string, color: 'white' | 'black') => void;
  onOpenGames?: (pgn: string, color: 'white' | 'black') => void;
  onOpenBookmarkGames?: (bookmark: PositionBookmarkResponse) => void;
}) {
  return render(
    <RepertoireList
      color="white"
      bookmarkRows={props.bookmarkRows ?? []}
      currentRows={props.currentRows ?? []}
      pastRows={props.pastRows ?? []}
      currentCutoff={props.currentCutoff ?? null}
      onOpenSuggestions={vi.fn()}
      debouncedFilters={DEFAULT_FILTERS}
      onOpenMoves={props.onOpenMoves ?? vi.fn()}
      onOpenGames={props.onOpenGames ?? vi.fn()}
      onOpenBookmarkGames={props.onOpenBookmarkGames ?? vi.fn()}
    />,
  );
}

function panelOpenCalls(): unknown[][] {
  return trackFeature.mock.calls.filter(([name]) => name === 'panel-open');
}

describe('RepertoireList bookmarks', () => {
  it('pins a bookmark card above the Most played group', () => {
    renderList({
      bookmarkRows: [makeRow({ key: 'bookmark-1', kind: 'bookmark', name: 'My Najdorf' })],
      currentRows: [makeRow({ key: 'mpo-1' })],
    });
    const rows = screen.getAllByTestId(/^repertoire-card-\d+$/);
    expect(rows).toHaveLength(2);
    expect(rows[0]?.textContent).toContain('My Najdorf');
    const bookmarkGroup = screen.getByTestId('repertoire-group-bookmarks');
    const mostPlayedGroup = screen.getByTestId('repertoire-group-most-played');
    // Document order: Bookmarks group (holding the bookmark card), then the Most played group.
    expect(
      bookmarkGroup.compareDocumentPosition(rows[0] as Node) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      rows[0]?.compareDocumentPosition(mostPlayedGroup) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it('shows the archive indicator only on cards outside the current repertoire', () => {
    renderList({
      bookmarkRows: [
        makeRow({ key: 'bookmark-1', kind: 'bookmark', isCurrent: false }),
        makeRow({ key: 'bookmark-2', kind: 'bookmark', isCurrent: true }),
      ],
    });
    expect(screen.getByTestId('repertoire-card-0-stale-icon').getAttribute('aria-label')).toBe(
      'Not played recently',
    );
    expect(screen.queryByTestId('repertoire-card-1-stale-icon')).toBeNull();
  });
});

describe('RepertoireList played before', () => {
  const past = [
    makeRow({ key: 'mpo-p1', kind: 'past', name: 'Queens Gambit' }),
    makeRow({ key: 'mpo-p2', kind: 'past', name: 'Dutch Defense' }),
    makeRow({ key: 'mpo-p3', kind: 'past', name: 'Colle System' }),
  ];

  it('renders collapsed with the count, hint and no past rows', () => {
    renderList({
      currentRows: [makeRow({ key: 'mpo-1' })],
      pastRows: past,
      currentCutoff: '2026-02-14T12:00:00Z',
    });
    const toggle = screen.getByTestId('repertoire-played-before-toggle');
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(toggle.textContent).toContain('Played before (3)');
    expect(toggle.textContent).toContain('not played as White since 14 Feb 2026');
    expect(screen.getAllByTestId(/^repertoire-card-\d+$/)).toHaveLength(1);
  });

  it('expands on click, tracks the expand once, and does not track the collapse', () => {
    renderList({ currentRows: [makeRow({ key: 'mpo-1' })], pastRows: past });
    const toggle = screen.getByTestId('repertoire-played-before-toggle');
    fireEvent.click(toggle);
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(screen.getAllByTestId(/^repertoire-card-\d+$/)).toHaveLength(4);
    expect(panelOpenCalls()).toEqual([['panel-open', { target: 'opening-stats-more' }]]);

    fireEvent.click(toggle);
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(screen.getAllByTestId(/^repertoire-card-\d+$/)).toHaveLength(1);
    expect(panelOpenCalls()).toHaveLength(1);
  });

  it('omits the toggle when nothing was played before', () => {
    renderList({ currentRows: [makeRow({ key: 'mpo-1' })] });
    expect(screen.queryByTestId('repertoire-played-before-toggle')).toBeNull();
  });
});

describe('RepertoireList intros and verdict sentence', () => {
  it('explains Score and Eval under the first heading only', () => {
    renderList({
      bookmarkRows: [makeRow({ key: 'bm-1', kind: 'bookmark' })],
      currentRows: [makeRow({ key: 'mpo-1' })],
      pastRows: [makeRow({ key: 'past-1', kind: 'past' })],
    });
    const bookmarks = screen.getByTestId('repertoire-group-bookmarks').textContent ?? '';
    const mostPlayed = screen.getByTestId('repertoire-group-most-played').textContent ?? '';
    expect(bookmarks).toContain('Score counts a draw as half a win.');
    expect(mostPlayed).toContain('Your most frequent openings as White lately. Older ones sit under Played before.');
    expect(mostPlayed).not.toContain('Score counts a draw');
    expect(screen.queryByTestId('repertoire-legend')).toBeNull();
  });

  it('reads both verdicts together on every card, including faded and ordinary ones', () => {
    renderList({
      currentRows: [
        makeRow({ key: 'mpo-big' }),
        makeRow({ key: 'mpo-small', games: 15, evalN: 15 }),
        makeRow({ key: 'mpo-plain', score: 0.5, scoreConfidence: 'low', avgEvalPawns: 0.25, evalConfidence: 'low' }),
      ],
    });
    expect(screen.getByTestId('repertoire-card-0-sentence').textContent).toBe(
      'You come out of the opening better and make it count.',
    );
    expect(screen.getByTestId('repertoire-card-1-sentence').textContent).toBe('Too few games to call it yet.');
    expect(screen.getByTestId('repertoire-card-2-sentence').textContent).toBe(
      'An ordinary opening for you: average positions and a typical score.',
    );
  });
});

describe('RepertoireList low-sample rows', () => {
  it('colours the left spine by the score verdict and leaves faded cards without one', () => {
    renderList({
      currentRows: [
        makeRow({ key: 'mpo-better', score: 0.7 }),
        makeRow({ key: 'mpo-worse', score: 0.3 }),
        makeRow({ key: 'mpo-typical', score: 0.52 }),
        makeRow({ key: 'mpo-small', games: 15, score: 0.9 }),
      ],
    });
    const spine = (i: number) => normalizeColor(screen.getByTestId(`repertoire-card-${i}`).style.borderLeftColor);
    expect(spine(0)).toBe(normalizeColor(ZONE_SUCCESS));
    expect(spine(1)).toBe(normalizeColor(ZONE_DANGER));
    expect(spine(2)).toBe(normalizeColor(ZONE_NEUTRAL));
    expect(spine(3)).toBe('');
  });

  it('fades a 15-game card and keeps its dots neutral despite high confidence', () => {
    renderList({
      currentRows: [
        makeRow({ key: 'mpo-small', games: 15, evalN: 15, score: 0.9, avgEvalPawns: 2.0 }),
        makeRow({ key: 'mpo-big', games: 100, score: 0.9, avgEvalPawns: 2.0 }),
      ],
    });
    const small = screen.getByTestId('repertoire-card-0');
    const big = screen.getByTestId('repertoire-card-1');
    expect(small.style.opacity).toBe(String(UNRELIABLE_OPACITY));
    expect(big.style.opacity).toBe('');
    expect(screen.getByTestId('repertoire-card-0-score').getAttribute('data-verdict')).toBe('typical');
    expect(screen.getByTestId('repertoire-card-0-eval-bar').getAttribute('data-verdict')).toBe('typical');
    expect(screen.getByTestId('repertoire-card-1-score').getAttribute('data-verdict')).toBe('better');
    expect(screen.getByTestId('repertoire-card-1-eval-bar').getAttribute('data-verdict')).toBe('better');
  });

  it('applies the 20-game floor to the eval sample, not the game count (WR-02)', () => {
    // 100 games but only 11 usable evals: the score may colour, the eval dot must stay neutral.
    renderList({
      currentRows: [makeRow({ key: 'mpo-thin-eval', games: 100, evalN: 11, score: 0.9, avgEvalPawns: 2.0 })],
    });
    expect(screen.getByTestId('repertoire-card-0-score').getAttribute('data-verdict')).toBe('better');
    expect(screen.getByTestId('repertoire-card-0-eval-bar').getAttribute('data-verdict')).toBe('typical');
  });

  it('centres the eval verdict on the colour baseline, not on zero', () => {
    // +0.25 is exactly an average White game: typical, however confident the test is.
    renderList({ currentRows: [makeRow({ key: 'mpo-avg', avgEvalPawns: 0.25 })] });
    expect(screen.getByTestId('repertoire-card-0-eval-bar').getAttribute('data-verdict')).toBe('typical');
  });
});

describe('RepertoireList card values', () => {
  it('shows compact score and eval values and an em dash without eval', () => {
    renderList({
      currentRows: [
        makeRow({ key: 'mpo-1', score: 0.56, avgEvalPawns: 0.91 }),
        makeRow({ key: 'mpo-2', avgEvalPawns: null, evalN: 0 }),
      ],
    });
    expect(screen.getByTestId('repertoire-card-0-score').textContent).toBe('56%');
    expect(screen.getByTestId('repertoire-card-0-eval-bar-value').textContent).toBe('+0.9');
    expect(screen.queryByTestId('repertoire-card-1-eval-bar')).toBeNull();
    expect(screen.getByTestId('repertoire-card-1-eval-none').textContent).toContain('—');
  });

  it('keeps distinct testids for cards that share a name', () => {
    renderList({
      currentRows: [
        makeRow({ key: 'mpo-1', name: 'Caro-Kann Defense: Advance Variation' }),
        makeRow({ key: 'mpo-2', name: 'Caro-Kann Defense: Advance Variation' }),
      ],
    });
    expect(screen.getByTestId('repertoire-card-0')).toBeTruthy();
    expect(screen.getByTestId('repertoire-card-1')).toBeTruthy();
    expect(screen.getByTestId('repertoire-card-0-score-info')).toBeTruthy();
    expect(screen.getByTestId('repertoire-card-1-score-info')).toBeTruthy();
  });
});

describe('RepertoireCard links and chart', () => {
  const series = {
    bookmark_id: MOST_PLAYED_ROW_SERIES_ID,
    data: [{ date: '2026-09-28', score: 0.6, game_count: 30, window_size: 50, per_week_games: 4 }],
    total_wins: 20,
    total_draws: 5,
    total_losses: 5,
    total_games: 30,
    score: 0.6,
    score_confidence: 'high' as const,
    score_p_value: 0.01,
    score_ci_low: 0.5,
    score_ci_high: 0.7,
    is_current: true,
  };

  function bookmarkOf(id: number): PositionBookmarkResponse {
    return {
      id,
      label: 'My Najdorf',
      target_hash: '99',
      fen: START_FEN,
      moves: ['e4', 'c5'],
      color: 'white',
      match_side: 'both',
      is_flipped: false,
      sort_order: 1,
    };
  }

  it('shows the 128px board, the score line and the eval bar, and opens the chart tracking the expand once', () => {
    useTimeSeriesMock.mockReturnValue({ data: { series: [series] }, isLoading: false, isError: false });
    renderList({ currentRows: [makeRow({ key: 'mpo-1' })] });
    const card = screen.getByTestId('repertoire-card-0');
    expect(card.querySelector('[data-testid="lazy-mini-board"]')?.getAttribute('data-size')).toBe('128');
    expect(screen.getByTestId('repertoire-card-0-score')).toBeTruthy();
    expect(screen.getByTestId('repertoire-card-0-eval-bar')).toBeTruthy();
    expect(screen.queryByTestId('repertoire-card-0-chart')).toBeNull();

    const toggle = screen.getByTestId('repertoire-card-0-toggle');
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(toggle);

    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByTestId('repertoire-card-0-chart')).toBeTruthy();
    expect(screen.getByTestId('score-chart-stub').getAttribute('data-volume')).toBe('true');
    expect(panelOpenCalls()).toEqual([['panel-open', { target: 'opening-row-expand' }]]);

    fireEvent.click(toggle);
    expect(screen.queryByTestId('repertoire-card-0-chart')).toBeNull();
    expect(panelOpenCalls()).toHaveLength(1);
  });

  it('shows no move line, only the opening name', () => {
    renderList({ currentRows: [makeRow({ key: 'mpo-1' })] });
    expect(screen.getByTestId('repertoire-card-0-name').textContent).toBe('Sicilian Defense');
    expect(screen.getByTestId('repertoire-card-0').textContent).not.toContain('1. e4 c5');
  });

  it('fetches a most-played row series only after the chart is opened', () => {
    renderList({ currentRows: [makeRow({ key: 'mpo-1' })] });
    expect(useTimeSeriesMock.mock.calls.every(([request]) => request === null)).toBe(true);
    fireEvent.click(screen.getByTestId('repertoire-card-0-toggle'));
    expect(useTimeSeriesMock.mock.calls.some(([request]) => request !== null)).toBe(true);
  });

  it('shows a chart error instead of an empty chart when the series request fails', () => {
    useTimeSeriesMock.mockReturnValue({ data: undefined, isLoading: false, isError: true });
    renderList({ currentRows: [makeRow({ key: 'mpo-1' })] });
    fireEvent.click(screen.getByTestId('repertoire-card-0-toggle'));
    expect(screen.getByTestId('repertoire-card-0-chart-error').textContent).toContain(
      'Failed to load the score chart',
    );
    expect(screen.queryByTestId('score-chart-stub')).toBeNull();
  });

  it('opens Moves and, for a most-played card, Games with the line and colour', () => {
    const onOpenMoves = vi.fn();
    const onOpenGames = vi.fn();
    renderList({ currentRows: [makeRow({ key: 'mpo-1', color: 'black' })], onOpenMoves, onOpenGames });
    fireEvent.click(screen.getByTestId('repertoire-card-0-btn-moves'));
    fireEvent.click(screen.getByTestId('repertoire-card-0-btn-games'));
    expect(onOpenMoves).toHaveBeenCalledWith('1. e4 c5', 'black');
    expect(onOpenGames).toHaveBeenCalledWith('1. e4 c5', 'black');
  });

  it('shows Remove bookmark on a bookmark card, deletes it and opens its Games via the bookmark', () => {
    const bookmark = bookmarkOf(7);
    const onOpenBookmarkGames = vi.fn();
    const onOpenGames = vi.fn();
    renderList({
      bookmarkRows: [makeRow({ key: 'bookmark-7', kind: 'bookmark', bookmark, series })],
      onOpenBookmarkGames,
      onOpenGames,
    });
    const link = screen.getByTestId('repertoire-card-0-btn-bookmark');
    expect(link.textContent).toContain('Remove bookmark');

    fireEvent.click(link);
    expect(deleteMutate).toHaveBeenCalledWith(7);
    expect(createMutate).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('repertoire-card-0-btn-games'));
    expect(onOpenBookmarkGames).toHaveBeenCalledWith(bookmark);
    expect(onOpenGames).not.toHaveBeenCalled();
    // A bookmark row reuses its loaded series: no per-row request.
    expect(useTimeSeriesMock.mock.calls.every(([request]) => request === null)).toBe(true);
  });

  it('creates a bookmark from a most-played card without the ECO code and with both sides', () => {
    renderList({
      currentRows: [makeRow({ key: 'mpo-1', name: 'Sicilian Defense', fullHash: '123', color: 'black' })],
    });
    const link = screen.getByTestId('repertoire-card-0-btn-bookmark');
    expect(link.textContent).toContain('Bookmark');
    expect(link.textContent).not.toContain('Remove');

    fireEvent.click(link);
    expect(createMutate).toHaveBeenCalledWith({
      label: 'Sicilian Defense',
      target_hash: '123',
      fen: START_FEN,
      moves: ['e4', 'c5'],
      color: 'black',
      match_side: 'both',
      is_flipped: true,
    });
    expect(deleteMutate).not.toHaveBeenCalled();
  });
});

function makeOpening(overrides: Partial<OpeningWDL> = {}): OpeningWDL {
  return {
    opening_eco: 'B12',
    opening_name: 'Caro-Kann Defense',
    display_name: 'Caro-Kann Defense (B12)',
    label: 'Caro-Kann Defense (B12)',
    pgn: '1. e4 c6',
    fen: START_FEN,
    full_hash: '42',
    wins: 10,
    draws: 5,
    losses: 5,
    total: 20,
    win_pct: 50,
    draw_pct: 25,
    loss_pct: 25,
    score: 0.625,
    score_confidence: 'low',
    score_p_value: 0.2,
    score_ci_low: 0.4,
    score_ci_high: 0.8,
    eval_n: 18,
    eval_confidence: 'low',
    is_current: true,
    ...overrides,
  };
}

function makeSeries(bookmarkId: number, games: number): BookmarkTimeSeries {
  return {
    bookmark_id: bookmarkId,
    data: [],
    total_wins: games,
    total_draws: 0,
    total_losses: 0,
    total_games: games,
    last_played_at: '2026-10-01T12:00:00Z',
    score: 1,
    score_confidence: 'high',
    score_p_value: 0.001,
    score_ci_low: 0.9,
    score_ci_high: 1,
    is_current: true,
  };
}

function makeBookmark(id: number, color: 'white' | 'black' | null): PositionBookmarkResponse {
  return {
    id,
    label: `Bookmark ${id} (C20)`,
    target_hash: String(1000 + id),
    fen: START_FEN,
    moves: ['e4', 'e5'],
    color,
    match_side: 'both',
    is_flipped: false,
    sort_order: id,
  };
}

describe('useRepertoireRows', () => {
  const mostPlayed: MostPlayedOpeningsResponse = {
    white: [makeOpening(), makeOpening({ full_hash: '43', is_current: false })],
    black: [],
    eval_baseline_pawns_white: 0.25,
    eval_baseline_pawns_black: -0.25,
    current_cutoff_white: null,
    current_cutoff_black: null,
  };

  it('strips the ECO suffix from most-played names and splits current from past', () => {
    const { result } = renderHook(() =>
      useRepertoireRows({
        color: 'white',
        mostPlayedData: mostPlayed,
        bookmarks: [],
        tsData: undefined,
        bookmarkPhaseEntryByHash: new Map(),
      }),
    );
    expect(result.current.currentRows.map((r) => r.name)).toEqual(['Caro-Kann Defense']);
    expect(result.current.pastRows.map((r) => r.key)).toEqual(['mpo-43']);
  });

  it('never shows a colour-less bookmark in either colour, and strips its ECO suffix', () => {
    const bookmarks = [makeBookmark(1, 'white'), makeBookmark(2, 'black'), makeBookmark(3, null)];
    const tsData: TimeSeriesResponse = {
      series: [makeSeries(1, 30), makeSeries(2, 30), makeSeries(3, 30)],
    };
    const rowsFor = (color: 'white' | 'black') =>
      renderHook(() =>
        useRepertoireRows({
          color,
          mostPlayedData: undefined,
          bookmarks,
          tsData,
          bookmarkPhaseEntryByHash: new Map(),
        }),
      ).result.current.bookmarkRows;
    expect(rowsFor('white').map((r) => r.key)).toEqual(['bookmark-1']);
    expect(rowsFor('black').map((r) => r.key)).toEqual(['bookmark-2']);
    expect(rowsFor('white')[0]?.name).toBe('Bookmark 1');
  });

  it('drops bookmarks without games and orders the rest by games', () => {
    const bookmarks = [makeBookmark(1, 'white'), makeBookmark(2, 'white'), makeBookmark(3, 'white')];
    const tsData: TimeSeriesResponse = {
      series: [makeSeries(1, 10), makeSeries(2, 0), makeSeries(3, 50)],
    };
    const { result } = renderHook(() =>
      useRepertoireRows({
        color: 'white',
        mostPlayedData: undefined,
        bookmarks,
        tsData,
        bookmarkPhaseEntryByHash: new Map(),
      }),
    );
    expect(result.current.bookmarkRows.map((r) => r.key)).toEqual(['bookmark-3', 'bookmark-1']);
  });
});

describe('useOpeningRowTimeSeries', () => {
  it('returns a bookmark row\'s own series and never requests one', () => {
    const series = makeSeries(5, 30);
    const row = makeRow({ key: 'bookmark-5', kind: 'bookmark', series });
    const { result } = renderHook(() =>
      useOpeningRowTimeSeries({ row, debouncedFilters: DEFAULT_FILTERS, enabled: true }),
    );
    expect(result.current.series).toBe(series);
    expect(useTimeSeriesMock).toHaveBeenCalledWith(null);
  });

  it('does not fetch a most-played row\'s series until enabled', () => {
    const row = makeRow({ key: 'mpo-1', fullHash: '777' });
    const { result } = renderHook(() =>
      useOpeningRowTimeSeries({ row, debouncedFilters: DEFAULT_FILTERS, enabled: false }),
    );
    expect(useTimeSeriesMock).toHaveBeenCalledWith(null);
    expect(result.current.series).toBeNull();
  });

  it('requests one full-position series for an enabled most-played row', () => {
    const series = makeSeries(MOST_PLAYED_ROW_SERIES_ID, 40);
    useTimeSeriesMock.mockReturnValue({ data: { series: [series] }, isLoading: false, isError: false });
    const row = makeRow({ key: 'mpo-1', fullHash: '777', color: 'black' });
    const { result } = renderHook(() =>
      useOpeningRowTimeSeries({ row, debouncedFilters: DEFAULT_FILTERS, enabled: true }),
    );
    const request = useTimeSeriesMock.mock.calls.at(-1)?.[0];
    expect(request.bookmarks).toEqual([
      { bookmark_id: MOST_PLAYED_ROW_SERIES_ID, target_hash: '777', match_side: 'full', color: 'black' },
    ]);
    expect(result.current.series).toBe(series);
  });
});

/** jsdom drops trailing zeros from oklch decimals (oklch(0.50 ...) reads back as oklch(0.5 ...)). */
function normalizeColor(value: string): string {
  return value.replace(/(\.\d*?)0+(?=\D|$)/g, '$1');
}
