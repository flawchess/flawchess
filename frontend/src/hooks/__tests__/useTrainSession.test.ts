// @vitest-environment jsdom
/**
 * useTrainSession.test.ts — coverage of `sessionSolvedCount`,
 * the session score's denominator. Computed as the session response's
 * `solved_results.length` plus the size of the internally tracked
 * solved-positions set, updating on exactly the same tick as `sessionScore`
 * (the solve mutation's success path) — never `currentIndex`.
 *
 * `sessionScore` and
 * `sessionSolvedCount` both now seed from `solved_results` on the session
 * response — server data, not a device-local localStorage tally.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider, onlineManager } from '@tanstack/react-query';
import { AxiosError, AxiosHeaders } from 'axios';
import { createElement } from 'react';
import type { ReactNode } from 'react';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    trainApi: {
      ...actual.trainApi,
      composeOrResumeSession: vi.fn(),
      solvePuzzle: vi.fn(),
    },
  };
});

import { trainApi } from '@/api/client';
import { useTrainSession } from '@/hooks/useTrainSession';
import { TRAIN_PROGRESS_QUERY_KEY } from '@/hooks/useTrainProgress';
import type {
  SolveRequest,
  SolveResponse,
  SolvedResult,
  TrainPuzzle,
  TrainSessionResponse,
} from '@/types/train';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function makePuzzle(overrides: Partial<TrainPuzzle> = {}): TrainPuzzle {
  return {
    position: 1,
    game_id: 100,
    ply: 20,
    fen: START_FEN,
    side_to_move: 'white',
    last_move_uci: 'd7d5',
    ...overrides,
  };
}

function makeSolvedResult(overrides: Partial<SolvedResult> = {}): SolvedResult {
  return {
    correct_guess: true,
    move_quality: 'good',
    source: 'sr_item',
    item_status: 'active',
    due_date: '2026-07-28',
    ...overrides,
  };
}

function makeSession(overrides: Partial<TrainSessionResponse> = {}): TrainSessionResponse {
  return {
    session_id: 1,
    session_date: '2026-07-25',
    expires_on: '2026-07-26',
    puzzle_count: 5,
    requested_count: 5,
    solved_count: 0,
    blob_pending_count: 0,
    puzzles: [makePuzzle()],
    solved_results: [],
    is_warmup: false,
    ...overrides,
  };
}

const SOLVE_RESPONSE: SolveResponse = {
  correct_guess: true,
  correct_move: true,
  move_quality: 'good',
  puzzle_type: 'sharp',
  source: 'sr_item',
  item_status: 'active',
  streak: 1,
  due_date: '2026-07-28',
  session_complete: false,
};

function makeWrapper(): ({ children }: { children: ReactNode }) => ReactNode {
  return function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    return createElement(QueryClientProvider, { client }, children);
  };
}

describe('useTrainSession — sessionSolvedCount', () => {
  beforeEach(() => {
    vi.mocked(trainApi.composeOrResumeSession).mockReset();
    vi.mocked(trainApi.solvePuzzle).mockReset();
  });

  it('is the session\'s frozen solved_results.length before any solve', async () => {
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(
      makeSession({
        solved_count: 3,
        solved_results: [makeSolvedResult(), makeSolvedResult(), makeSolvedResult()],
      }),
    );
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());
    expect(result.current.sessionSolvedCount).toBe(3);
  });

  it('seeds sessionScore and sessionSolvedCount from solved_results, not a device-local tally', async () => {
    // Regression coverage: with no localStorage read anywhere in
    // the hook, this is server data only. Three entries, each 1 (correct
    // guess) + 2 (good move) = 3 points -> total 9.
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(
      makeSession({
        solved_count: 3,
        solved_results: [
          makeSolvedResult({ correct_guess: true, move_quality: 'good' }),
          makeSolvedResult({ correct_guess: false, move_quality: 'inaccuracy' }),
          makeSolvedResult({ correct_guess: true, move_quality: 'wrong' }),
        ],
      }),
    );
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());
    // (1+2) + (0+1) + (1+0) = 5.
    expect(result.current.sessionScore).toBe(5);
    expect(result.current.sessionSolvedCount).toBe(3);

    // A subsequent solve still increments both live, on top of the seeded base.
    vi.mocked(trainApi.solvePuzzle).mockResolvedValue(SOLVE_RESPONSE);
    const body: SolveRequest = {
      position: 1,
      guess: 'critical',
      played_move: 'e2e4',
      move_quality: 'good',
    };
    await act(async () => {
      await result.current.solvePuzzle(body);
    });
    expect(result.current.sessionScore).toBe(8);
    expect(result.current.sessionSolvedCount).toBe(4);
  });

  it('increases by one after a successful solve mutation', async () => {
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession({ solved_count: 0 }));
    vi.mocked(trainApi.solvePuzzle).mockResolvedValue(SOLVE_RESPONSE);
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());
    expect(result.current.sessionSolvedCount).toBe(0);

    const body: SolveRequest = { position: 1, guess: 'critical', played_move: 'e2e4', move_quality: 'good' };
    await act(async () => {
      await result.current.solvePuzzle(body);
    });
    expect(result.current.sessionSolvedCount).toBe(1);
    // Updates on the SAME tick as sessionScore (both in the solve mutation's
    // success path), never derived from currentIndex. Correct
    // guess (1) + good move (2) = 3.
    expect(result.current.sessionScore).toBe(3);
  });

  it('a failed solve mutation does not increase sessionSolvedCount', async () => {
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession({ solved_count: 0 }));
    vi.mocked(trainApi.solvePuzzle).mockRejectedValue(new Error('network down'));
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());

    const body: SolveRequest = { position: 1, guess: 'critical', played_move: 'e2e4', move_quality: 'good' };
    await act(async () => {
      await expect(result.current.solvePuzzle(body)).rejects.toThrow();
    });
    expect(result.current.sessionSolvedCount).toBe(0);
  });
});

/**
 * `solvedOutcomes`, the score
 * screen's sole source for "what returns and when" — seeded from
 * `solved_results` on compose/resume, appended live from each solve's
 * `SolveResponse`. Required because `solved_results` is EMPTY for a session
 * composed and completed in one sitting.
 */
describe('useTrainSession — solvedOutcomes accumulator', () => {
  beforeEach(() => {
    vi.mocked(trainApi.composeOrResumeSession).mockReset();
    vi.mocked(trainApi.solvePuzzle).mockReset();
  });

  it('starts at [] for a fresh session (empty solved_results)', async () => {
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession({ solved_results: [] }));
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());
    expect(result.current.solvedOutcomes).toEqual([]);
  });

  it('appends one live outcome per successful solve, carrying source/item_status/due_date straight from the SolveResponse', async () => {
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession({ solved_results: [] }));
    vi.mocked(trainApi.solvePuzzle).mockResolvedValue({
      ...SOLVE_RESPONSE,
      source: 'sr_item',
      item_status: 'active',
      due_date: '2026-08-05',
    });
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());

    await act(async () => {
      await result.current.solvePuzzle({
        position: 1,
        guess: 'critical',
        played_move: 'e2e4',
        move_quality: 'good',
      });
    });

    expect(result.current.solvedOutcomes).toEqual([
      {
        correct_guess: true,
        move_quality: 'good',
        source: 'sr_item',
        item_status: 'active',
        due_date: '2026-08-05',
      },
    ]);
  });

  it('seeds solvedOutcomes from solved_results on a completed-session resume, without duplicating the seed against the live append', async () => {
    // A fresh compose against a COMPLETED session returns populated
    // solved_results via _resume_session — the
    // seed path must not double-count against anything the live append
    // would otherwise add (nothing does here, since no solvePuzzle call
    // follows the resume).
    const seeded: SolvedResult[] = [
      makeSolvedResult({ due_date: '2026-07-26' }),
      makeSolvedResult({ correct_guess: false, move_quality: 'wrong', due_date: '2026-08-01' }),
    ];
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(
      makeSession({ puzzles: [], solved_count: 2, solved_results: seeded }),
    );
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());

    expect(result.current.solvedOutcomes).toEqual(seeded);
    expect(result.current.solvedOutcomes).toHaveLength(2);
  });

  it('reseeds (never accumulates) on a fresh compose call — three live appends followed by a new startSession() reset to the new session\'s own seed', async () => {
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession({ solved_results: [] }));
    vi.mocked(trainApi.solvePuzzle).mockResolvedValue(SOLVE_RESPONSE);
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());

    for (const position of [1, 2, 3]) {
      await act(async () => {
        await result.current.solvePuzzle({
          position,
          guess: 'critical',
          played_move: 'e2e4',
          move_quality: 'good',
        });
      });
    }
    expect(result.current.solvedOutcomes).toHaveLength(3);

    // The landing-screen re-fire (e.g. after a schedule-settings save):
    // startSession() again, composing a session with its own empty seed.
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession({ solved_results: [] }));
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.solvedOutcomes).toHaveLength(0));
  });
});

/**
 * Every solve moves the nav badge. Server-side `waiting_count` is
 * `puzzle_count - solved_count` (get_waiting_puzzle_count branch 1), so it
 * decreases by one per solve and hits 0 on the last one — which is also the
 * tick that flips the session row to 'completed' and settles the
 * streak/shield. The nav badge dot and the progress row both read the cached
 * `TRAIN_PROGRESS_QUERY_KEY`, which nothing else on the Train page
 * invalidates, so it must be invalidated on EVERY solve. Gating it on
 * `session_complete` alone froze the counter at its start-of-session value
 * until the final puzzle, then jumped it straight to 0.
 */
describe('useTrainSession — progress invalidation on every solve', () => {
  beforeEach(() => {
    vi.mocked(trainApi.composeOrResumeSession).mockReset();
    vi.mocked(trainApi.solvePuzzle).mockReset();
  });

  function makeClientWrapper(): {
    client: QueryClient;
    wrapper: ({ children }: { children: ReactNode }) => ReactNode;
  } {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    return {
      client,
      wrapper: ({ children }: { children: ReactNode }) =>
        createElement(QueryClientProvider, { client }, children),
    };
  }

  const BODY: SolveRequest = {
    position: 1,
    guess: 'critical',
    played_move: 'e2e4',
    move_quality: 'good',
  };

  it('invalidates the train progress query when the solve completes the session', async () => {
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession());
    vi.mocked(trainApi.solvePuzzle).mockResolvedValue({ ...SOLVE_RESPONSE, session_complete: true });
    const { client, wrapper } = makeClientWrapper();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    const { result } = renderHook(() => useTrainSession(), { wrapper });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());

    await act(async () => {
      await result.current.solvePuzzle(BODY);
    });

    expect(invalidate).toHaveBeenCalledWith({ queryKey: TRAIN_PROGRESS_QUERY_KEY });
  });

  it('invalidates the train progress query on a mid-session solve too', async () => {
    // The badge counter must tick down as the user works through the session,
    // not sit frozen until the last puzzle. This is the case that regressed
    // when the invalidation was gated on `session_complete`.
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession());
    vi.mocked(trainApi.solvePuzzle).mockResolvedValue({
      ...SOLVE_RESPONSE,
      session_complete: false,
    });
    const { client, wrapper } = makeClientWrapper();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    const { result } = renderHook(() => useTrainSession(), { wrapper });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());

    await act(async () => {
      await result.current.solvePuzzle(BODY);
    });

    expect(invalidate).toHaveBeenCalledWith({ queryKey: TRAIN_PROGRESS_QUERY_KEY });
  });

  it('invalidates once per solve across a multi-puzzle session', async () => {
    // Guards the shape of the fix rather than a single call: three
    // consecutive mid-session solves must each refresh the counter, so a
    // future "only invalidate sometimes" optimisation cannot silently
    // re-freeze it.
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession());
    vi.mocked(trainApi.solvePuzzle).mockResolvedValue({
      ...SOLVE_RESPONSE,
      session_complete: false,
    });
    const { client, wrapper } = makeClientWrapper();
    const invalidate = vi.spyOn(client, 'invalidateQueries');
    const { result } = renderHook(() => useTrainSession(), { wrapper });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());

    for (const position of [1, 2, 3]) {
      await act(async () => {
        await result.current.solvePuzzle({ ...BODY, position });
      });
    }

    const progressInvalidations = invalidate.mock.calls.filter(
      ([arg]) => arg?.queryKey === TRAIN_PROGRESS_QUERY_KEY,
    );
    expect(progressInvalidations).toHaveLength(3);
  });
});

/**
 * FLAWCHESS-24: the session load and the solve save repeat themselves up to twice when the
 * connection drops (axios ERR_NETWORK), and fail at once for anything else. The wrapper sets
 * `retryDelay: 0` so the repeats are immediate (the hook sets no delay of its own).
 */
function makeRetryWrapper(): ({ children }: { children: ReactNode }) => ReactNode {
  return function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false, retryDelay: 0 } },
    });
    return createElement(QueryClientProvider, { client }, children);
  };
}

function networkError(): AxiosError {
  return new AxiosError('Network Error', AxiosError.ERR_NETWORK);
}

function timeoutError(): AxiosError {
  return new AxiosError('timeout of 10000ms exceeded', AxiosError.ECONNABORTED);
}

function serverError(): AxiosError {
  const config = { headers: new AxiosHeaders() };
  const response = {
    data: {},
    status: 500,
    statusText: 'Internal Server Error',
    headers: {},
    config,
  };
  return new AxiosError(
    'Request failed with status code 500',
    AxiosError.ERR_BAD_RESPONSE,
    config,
    null,
    response,
  );
}

const RETRY_SOLVE_BODY: SolveRequest = {
  position: 1,
  guess: 'critical',
  played_move: 'e2e4',
  move_quality: 'good',
};

describe('useTrainSession — network retries (FLAWCHESS-24)', () => {
  beforeEach(() => {
    vi.mocked(trainApi.composeOrResumeSession).mockReset();
    vi.mocked(trainApi.solvePuzzle).mockReset();
    onlineManager.setOnline(true);
  });

  afterEach(() => {
    onlineManager.setOnline(true);
  });

  it('session: two ERR_NETWORK failures then success loads the session', async () => {
    vi.mocked(trainApi.composeOrResumeSession)
      .mockRejectedValueOnce(networkError())
      .mockRejectedValueOnce(networkError())
      .mockResolvedValue(makeSession());
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeRetryWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());
    expect(result.current.isSessionError).toBe(false);
    expect(trainApi.composeOrResumeSession).toHaveBeenCalledTimes(3);
  });

  it('session: ERR_NETWORK forever errors after exactly 3 calls', async () => {
    vi.mocked(trainApi.composeOrResumeSession).mockRejectedValue(networkError());
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeRetryWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.isSessionError).toBe(true));
    expect(trainApi.composeOrResumeSession).toHaveBeenCalledTimes(3);
  });

  it.each([
    ['an HTTP 500', serverError],
    ['a timeout (ECONNABORTED)', timeoutError],
  ])('session: %s errors after exactly 1 call', async (_label, makeError) => {
    vi.mocked(trainApi.composeOrResumeSession).mockRejectedValue(makeError());
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeRetryWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.isSessionError).toBe(true));
    expect(trainApi.composeOrResumeSession).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['an HTTP 500', serverError],
    ['a timeout (ECONNABORTED)', timeoutError],
  ])('solve: %s errors after exactly 1 call', async (_label, makeError) => {
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession());
    vi.mocked(trainApi.solvePuzzle).mockRejectedValue(makeError());
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeRetryWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());
    await act(async () => {
      await expect(result.current.solvePuzzle(RETRY_SOLVE_BODY)).rejects.toThrow();
    });
    await waitFor(() => expect(result.current.isSolveError).toBe(true));
    expect(trainApi.solvePuzzle).toHaveBeenCalledTimes(1);
  });

  it('session: going offline during the first attempt pauses the retry until reconnect', async () => {
    // The mock flips the device offline and then rejects, so the retry finds it offline and
    // waits (default networkMode). Offline BEFORE the first call would pause with zero calls.
    vi.mocked(trainApi.composeOrResumeSession)
      .mockImplementationOnce(() => {
        onlineManager.setOnline(false);
        return Promise.reject(networkError());
      })
      .mockResolvedValue(makeSession());
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeRetryWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(trainApi.composeOrResumeSession).toHaveBeenCalledTimes(1));
    // Give the retry every chance to run; it must stay paused.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(trainApi.composeOrResumeSession).toHaveBeenCalledTimes(1);
    expect(result.current.isSessionError).toBe(false);
    expect(result.current.isSessionPending).toBe(true);

    act(() => onlineManager.setOnline(true));
    await waitFor(() => expect(result.current.session).not.toBeNull());
    expect(result.current.isSessionError).toBe(false);
    expect(trainApi.composeOrResumeSession).toHaveBeenCalledTimes(2);
  });

  it('solve: two ERR_NETWORK failures then success resolves and is counted once', async () => {
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession());
    vi.mocked(trainApi.solvePuzzle)
      .mockRejectedValueOnce(networkError())
      .mockRejectedValueOnce(networkError())
      .mockResolvedValue(SOLVE_RESPONSE);
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeRetryWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());
    await act(async () => {
      await result.current.solvePuzzle(RETRY_SOLVE_BODY);
    });
    expect(trainApi.solvePuzzle).toHaveBeenCalledTimes(3);
    for (const call of vi.mocked(trainApi.solvePuzzle).mock.calls) {
      expect(call).toEqual([1, RETRY_SOLVE_BODY]);
    }
    expect(result.current.sessionSolvedCount).toBe(1);
    // Correct guess (1) + good move (2) = 3, added once.
    expect(result.current.sessionScore).toBe(3);
  });

  it('solve: offline with ERR_NETWORK forever errors after exactly 3 calls, never waiting for reconnect', async () => {
    vi.mocked(trainApi.composeOrResumeSession).mockResolvedValue(makeSession());
    vi.mocked(trainApi.solvePuzzle).mockRejectedValue(networkError());
    const { result } = renderHook(() => useTrainSession(), { wrapper: makeRetryWrapper() });
    act(() => result.current.startSession());
    await waitFor(() => expect(result.current.session).not.toBeNull());
    act(() => onlineManager.setOnline(false));
    await act(async () => {
      await expect(result.current.solvePuzzle(RETRY_SOLVE_BODY)).rejects.toThrow();
    });
    await waitFor(() => expect(result.current.isSolveError).toBe(true));
    expect(trainApi.solvePuzzle).toHaveBeenCalledTimes(3);
  });
});
