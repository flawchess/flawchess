// @vitest-environment jsdom
/**
 * useTrainGradingEngine — regression coverage for the Phase 190-01 checkpoint
 * bug fix (manual browser UAT hit an indefinite "Checking your move…" hang).
 *
 * Two independent root causes, two regression tests:
 * 1. React StrictMode's dev-only mount->cleanup->mount double-invoke used to
 *    leave `gradeMove` permanently unresolved for the puzzle's actual
 *    generation (the interim cleanup's `abortGrading()` bumped the
 *    generation and discarded the in-flight search's result, but nothing
 *    re-started a search for the new generation — see
 *    `TrainSolveScreen.tsx`'s effect-site fix, mirrored here at the hook
 *    level by calling `startGrading` twice in immediate succession, exactly
 *    as the double-invoked effect does).
 * 2. No matter the cause, `gradeMove` must never hang forever — it now races
 *    against `TRAIN_GRADING_TIMEOUT_MS` and rejects.
 *
 * Task 2 of this plan (190-01) extends this same file (below the checkpoint
 * regression block) with the full grading-contract test suite: exact-match
 * fast path, threshold boundaries, mate scores, mover-sign consistency,
 * single-Worker reuse, and abort-then-restart isolation.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { Chess } from 'chess.js';
import {
  useTrainGradingEngine,
  TRAIN_GRADING_TIMEOUT_MS,
  TRAIN_GRADING_MULTIPV_WIDTH,
  TRAIN_GRADING_MOVETIME_MS,
  TRAIN_GRADING_MOUNT_MOVETIME_MS,
  TRAIN_GRADING_MAX_NODES,
  TRAIN_RECHECK_MOVETIME_MS,
  TRAIN_RECHECK_MAX_NODES,
  TRAIN_RECHECK_TIMEOUT_MS,
} from '../useTrainGradingEngine';
import { MISTAKE_DROP, BLUNDER_DROP, INACCURACY_DROP } from '@/generated/flawThresholds';
import { evalToExpectedScore } from '@/lib/liveFlaw';

// ─── stockfishWorkerSource mock (Phase 213-08, G-213-35) ───────────────────
//
// The worker-lifecycle effect now constructs through the shared source
// module, via `ensureStockfishWorkerUrl().then(setupWorker)`. This file's
// job is the hook's own grading state machine, not the shared-fetch
// mechanics (covered by `stockfishWorkerSource.test.ts`) — resolve via a
// synchronous "thenable" (a `.then` that invokes its callback in the SAME
// synchronous call, not a real deferred microtask) so every pre-existing
// test that reads `mockWorker` right after `renderHook()` — no await in
// between — keeps working completely unchanged.
function syncThenable<T>(value: T): PromiseLike<T> {
  return {
    then<TResult1 = T>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | null): PromiseLike<TResult1> {
      const result = onfulfilled ? onfulfilled(value) : (value as unknown as TResult1);
      return Promise.resolve(result);
    },
  };
}
vi.mock('@/lib/engine/stockfishWorkerSource', () => ({
  ensureStockfishWorkerUrl: vi.fn(() => syncThenable<string | null>(null)),
  createStockfishWorker: vi.fn((sharedUrl: string | null) => {
    const WorkerCtor = globalThis.Worker as unknown as new (url: string) => Worker;
    return sharedUrl === null
      ? new WorkerCtor('/engine/stockfish-18-lite-single.js')
      : new WorkerCtor(`/engine/stockfish-18-lite-single.js#${encodeURIComponent(sharedUrl)}`);
  }),
}));

// ─── Mock Worker ─────────────────────────────────────────────────────────────

class MockWorker {
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  messages: string[] = [];
  terminated = false;

  postMessage(msg: string): void {
    this.messages.push(msg);
  }

  terminate(): void {
    this.terminated = true;
  }

  simulateMessage(data: string): void {
    this.onmessage?.(new MessageEvent('message', { data }));
  }
}

let mockWorker: MockWorker;

const FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function driveInit(worker: MockWorker): void {
  act(() => {
    worker.simulateMessage('uciok');
  });
  act(() => {
    worker.simulateMessage('readyok');
  });
}

describe('useTrainGradingEngine — checkpoint regression', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('survives a StrictMode-style double startGrading (mount->abort->mount) without hanging gradeMove', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    // First "mount": starts a search (sends the first `go`).
    act(() => {
      result.current.startGrading(FEN);
    });
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(1);

    // StrictMode's interim cleanup: abort discards the in-flight search and
    // sends `stop`.
    act(() => {
      result.current.abortGrading();
    });
    expect(mockWorker.messages).toContain('stop');

    // The stale bestmove from the aborted search arrives (discarded).
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    // Second "mount" (same puzzle fen): starts a FRESH search for the new
    // generation — this is the call the old ref-guard used to suppress.
    act(() => {
      result.current.startGrading(FEN);
    });
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(2);

    // Settle the second (real) search.
    act(() => {
      mockWorker.simulateMessage('info depth 10 multipv 1 score cp 20 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    // gradeMove for the exact-match move must resolve promptly (not hang) —
    // race it against a short fake-timer advance well under the hard timeout.
    const gradePromise = result.current.gradeMove(FEN, 'e2e4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });
    const grade = await gradePromise;
    expect(grade.moveTier).toBe('good');
  });

  it('gradeMove rejects instead of hanging forever when the engine never responds', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    // Never simulate a bestmove — the search is permanently stuck.

    const gradePromise = result.current.gradeMove(FEN, 'e2e4');
    const assertion = expect(gradePromise).rejects.toThrow();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(TRAIN_GRADING_TIMEOUT_MS + 100);
    });

    await assertion;
  });

  it('startGrading called before the Worker reports ready queues the search instead of fabricating a null result (CR-01)', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    // Do NOT driveInit yet — start grading while the Worker's UCI handshake
    // is still outstanding (the normal state for the first puzzle of a
    // session).
    act(() => {
      result.current.startGrading(FEN);
    });
    // The pre-fix behavior resolved immediately with a fabricated null
    // result WITHOUT ever dispatching a `go` — same observation here, but
    // for a different reason (queued, not yet drained).
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(0);

    // The engine now completes its handshake — the queued search must
    // dispatch for real instead of having already settled as fabricated.
    driveInit(mockWorker);
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(1);

    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 40 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const grade = await result.current.gradeMove(FEN, 'e2e4');
    // A fabricated-null pre-fix result would have left bestMoveUci null
    // forever (the D-06 exact-match fast path could never trigger) and
    // esBefore pinned at the neutral 0.5 fallback.
    expect(grade.bestMoveUci).toBe('e2e4');
    expect(grade.moveTier).toBe('good');
  });

  it('surfaces hasError and rejects any in-flight gradeMove when the Worker errors', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });

    const gradePromise = result.current.gradeMove(FEN, 'e2e4');
    const assertion = expect(gradePromise).rejects.toThrow();

    act(() => {
      mockWorker.onerror?.(new Event('error'));
    });

    await assertion;
    expect(result.current.hasError).toBe(true);
  });
});

// ─── Task 2: grading-contract pinning ──────────────────────────────────────

// Two legal replies to 1.e4 e5 2.Nf3 (black to move) — used for the
// mover-sign test below. Nf6 is the engine's chosen "best" move; Nc6 is the
// DIFFERENT move actually played, forcing the second-search branch.
const BLACK_TO_MOVE_FEN = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 3 2';

describe('useTrainGradingEngine — grading contract (Task 2)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('exact match to the engine top move resolves moveTier="good" with exactly one go dispatched (fast path)', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 40 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const grade = await result.current.gradeMove(FEN, 'e2e4');
    expect(grade.moveTier).toBe('good');
    expect(grade.esAfter).toBe(grade.esBefore);
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(1);
  });

  it('a trailing lowerbound/upperbound info line never clobbers the previous exact iteration\'s full PV (190.1 UAT round 4)', async () => {
    // Real engine behavior at the end of a movetime budget: an aspiration-
    // window fail emits e.g. "depth 20 ... upperbound ... pv <2 moves>" as
    // the LAST rank-1 line. Latest-wins committing used to shrink the reveal
    // lines to 2-3 moves.
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 40 nodes 1000 pv e2e4 e7e5 g1f3 b8c6');
    });
    act(() => {
      mockWorker.simulateMessage('info depth 13 multipv 1 score cp 55 upperbound nodes 2000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const grade = await result.current.gradeMove(FEN, 'e2e4');
    expect(grade.bestLine.moves).toEqual(['e2e4', 'e7e5', 'g1f3', 'b8c6']);
    // The eval too comes from the exact line, never the bound line.
    expect(grade.bestLine.evalCp).toBe(40);
  });

  it('a drop of exactly MISTAKE_DROP resolves moveTier="wrong"', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    // esBefore ~= 0.676 (cp 230, white to move).
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 230 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    // Played move (d2d4) differs from the engine's top move (e2e4) -> second
    // search runs on the post-move fen, which is BLACK to move (whitePovSign
    // -1 for that search) — raw UCI cp -110 normalizes to a stored white-POV
    // evalCp of +110, giving esBefore - esAfter just over MISTAKE_DROP (0.10)
    // — see 190-01-SUMMARY.md for the exact derivation of these cp values.
    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -110 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    expect(grade.esBefore - grade.esAfter).toBeGreaterThanOrEqual(MISTAKE_DROP);
    expect(grade.moveTier).toBe('wrong');
  });

  it('a drop just under MISTAKE_DROP (inside the inaccuracy band) resolves moveTier="inaccuracy" — SEED-119 substantive new coverage: this previously only asserted the optimistic correctMove boolean', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 230 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // Raw UCI cp -111 (post-move fen is black to move, whitePovSign -1) ->
    // stored evalCp +111 -> drop just under MISTAKE_DROP, still >= INACCURACY_DROP.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -111 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    expect(grade.esBefore - grade.esAfter).toBeLessThan(MISTAKE_DROP);
    expect(grade.esBefore - grade.esAfter).toBeGreaterThanOrEqual(INACCURACY_DROP);
    expect(grade.moveTier).toBe('inaccuracy');
  });

  it('a drop just under INACCURACY_DROP (below the inaccuracy threshold) resolves moveTier="good"', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 230 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // Raw UCI cp -222 (post-move fen is black to move, whitePovSign -1) ->
    // stored evalCp +222 -> drop just under INACCURACY_DROP (a clean move).
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -222 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    expect(grade.esBefore - grade.esAfter).toBeLessThan(INACCURACY_DROP);
    expect(grade.moveTier).toBe('good');
  });

  it('a drop at or over BLUNDER_DROP resolves moveTier="wrong"', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 230 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // Raw UCI cp -54 (post-move fen is black to move, whitePovSign -1) ->
    // stored evalCp +54 -> drop >= BLUNDER_DROP.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -54 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    expect(grade.esBefore - grade.esAfter).toBeGreaterThanOrEqual(BLUNDER_DROP);
    expect(grade.moveTier).toBe('wrong');
  });

  it('a mate score is converted through evalToExpectedScore, not treated as a null eval', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    // Mate-in-3 for white (mover) at the root -> esBefore should read near 1,
    // not the neutral 0.5 a null-eval fallback would produce.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score mate 3 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // A large drop back to roughly equal after the (non-mating) played move.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 0 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    // A mate score misread as null would make esBefore = 0.5, collapsing the
    // drop to ~0 (clean/correct). The real mate-derived esBefore is close to
    // 1, so the drop is unambiguously blunder-sized.
    expect(grade.esBefore).toBeGreaterThan(0.9);
    expect(grade.esBefore - grade.esAfter).toBeGreaterThanOrEqual(BLUNDER_DROP);
    expect(grade.moveTier).toBe('wrong');
  });

  it('esBefore and esAfter are computed with the SAME mover — a black-to-move position where a sign error would flip the verdict', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(BLACK_TO_MOVE_FEN);
    });
    // BLACK_TO_MOVE_FEN is black-to-move, so the hook's whitePovSign for this
    // search is -1: raw UCI cp -200 (mover=black POV) normalizes to a stored
    // white-POV evalCp of +200 (white slightly better).
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -200 nodes 1000 pv g8f6');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove g8f6');
    });

    // Played move (Nc6, b8c6) differs from the engine's top move (Nf6) ->
    // second search on the post-move fen, which is WHITE to move (whitePovSign
    // +1): raw UCI cp 500 (mover=white POV) stores as white-POV evalCp +500
    // unchanged — a further worsening for black.
    const gradePromise = result.current.gradeMove(BLACK_TO_MOVE_FEN, 'b8c6');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 500 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const grade = await gradePromise;
    // Using the SAME mover ('black') for both esBefore/esAfter: esBefore
    // ~0.324, esAfter ~0.137, a blunder-sized drop for black. A sign-error
    // bug (re-deriving mover from the post-move fen, i.e. 'white', for
    // esAfter) would instead read as a large GAIN (negative drop) and
    // resolve moveTier="good" — the exact regression this test pins.
    expect(grade.esBefore).toBeGreaterThan(grade.esAfter);
    expect(grade.esBefore - grade.esAfter).toBeGreaterThanOrEqual(BLUNDER_DROP);
    expect(grade.moveTier).toBe('wrong');
  });

  it('calling startGrading for a second puzzle does not construct a second Worker', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 20 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    act(() => {
      result.current.startGrading(BLACK_TO_MOVE_FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 10 nodes 1000 pv g8f6');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove g8f6');
    });

    const WorkerCtor = vi.mocked(globalThis.Worker as unknown as new () => Worker);
    expect(WorkerCtor).toHaveBeenCalledTimes(1);
  });

  it('abortGrading() followed by a new startGrading never resolves the first search into the second puzzle', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    // Puzzle A: dispatch starts, but never settles before being aborted.
    act(() => {
      result.current.startGrading(FEN);
    });
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(1);

    act(() => {
      result.current.abortGrading();
    });
    expect(mockWorker.messages).toContain('stop');

    // Puzzle B starts while the engine is still winding down from the abort
    // -> queued, not dispatched yet.
    act(() => {
      result.current.startGrading(BLACK_TO_MOVE_FEN);
    });
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(1);

    // Puzzle A's stale bestmove (the stop's termination echo) arrives,
    // discarded, and fires the queued dispatch for puzzle B.
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(2);

    // Settle puzzle B's real search.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 30 nodes 1000 pv d2d4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d2d4');
    });

    const gradeB = await result.current.gradeMove(BLACK_TO_MOVE_FEN, 'd2d4');
    expect(gradeB.bestMoveUci).toBe('d2d4');

    // Puzzle A's fen never got a matching settled search for the CURRENT
    // generation — gradeMove must not silently serve puzzle B's verdict for
    // puzzle A's fen (the defensive fallback path, not a leaked match).
    const gradeAStale = await result.current.gradeMove(FEN, 'e2e4');
    expect(gradeAStale.bestMoveUci).toBeNull();
  });
});

// ─── 190.1-01 Task 2: startGameMoveSearch honesty + cancellation safety ────

describe('useTrainGradingEngine — startGameMoveSearch (190.1-01 Task 2)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('rejects instead of hanging forever when the engine never emits bestmove', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    const searchPromise = result.current.startGameMoveSearch(FEN, 'e2e4');
    const assertion = expect(searchPromise).rejects.toThrow();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(TRAIN_GRADING_TIMEOUT_MS + 100);
    });

    await assertion;
  });

  it('a search superseded by a newer startGrading before it settles never resolves the stale payload, and eventually rejects via the timeout', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    const searchPromise = result.current.startGameMoveSearch(FEN, 'e2e4');
    const assertion = expect(searchPromise).rejects.toThrow();

    // Supersede the in-flight search with a new puzzle (bumps generationRef)
    // before the engine responds — the hook's single-Worker serialization
    // sends `stop`, so the superseded search's own pendingRef is silently
    // discarded on the termination echo (never resolved/rejected directly);
    // it can only ever settle via the timeout race below.
    act(() => {
      result.current.startGrading(BLACK_TO_MOVE_FEN);
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5'); // stop-termination echo — discarded
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 10 nodes 1000 pv g8f6');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove g8f6'); // settles the NEW startGrading search, not ours
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(TRAIN_GRADING_TIMEOUT_MS + 100);
    });

    await assertion;
  });
});

// ─── 211-02 Task 1: width-1 mount search, kept PV, no client alternatives ──

describe('useTrainGradingEngine — width-1 mount search (211-02 Task 1)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('the mount search is width 1 (D-05) and its setoption line carries the exported constant; the after-move search also posts width 1', async () => {
    // The mutation proof VETFINE-05 asks for: restoring the width to 4 turns
    // this assertion red. The message assertion below stays symbolic (the
    // exported constant), so THIS line is the one that pins the value.
    expect(TRAIN_GRADING_MULTIPV_WIDTH).toBe(1);

    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    // driveInit already sent 'uci' and 'isready' — everything posted after
    // that belongs to the mount search dispatch.
    const messagesAfterInit = mockWorker.messages.slice(2);
    expect(messagesAfterInit[0]).toBe(`setoption name MultiPV value ${TRAIN_GRADING_MULTIPV_WIDTH}`);

    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 40 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    // Non-matching played move -> triggers the after-move (width 1) search.
    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    // EVERY dispatched search in this session requested width 1 — the whole
    // 1.5s budget goes to one line (D-05).
    const setoptionMessages = mockWorker.messages.filter((m) => m.startsWith('setoption name MultiPV value '));
    expect(setoptionMessages).toHaveLength(2);
    expect(setoptionMessages.every((m) => m === 'setoption name MultiPV value 1')).toBe(true);

    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -30 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });
    await gradePromise;
  });

  it('a played move that is NOT the top move dispatches exactly TWO searches (mount + after-move) and grades from the after-move eval (211-02)', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 230 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // Raw UCI cp -110 (post-move fen is black to move, whitePovSign -1) ->
    // stored white-POV evalCp +110: a mistake-sized drop from 230.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -110 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(2);
    // The tier comes from the AFTER-MOVE eval (esAfter = ES of +110), never
    // from a mount rank.
    expect(grade.esAfter).toBe(evalToExpectedScore(110, null, 'white'));
    expect(grade.moveTier).toBe('wrong');
  });

  it('the retired mount-rank shortcut must not resurrect: a played move present as an extra rank in the settled lines STILL runs the after-move search (211-02 mutation guard)', async () => {
    // The mutation proof VETFINE-05 asks for: re-adding gradeMoveInner's
    // rank-match branch makes this grade from the (spurious) rank-2 entry
    // with ONE go dispatched and moveTier 'good' — turning both assertions
    // below red. The extra multipv-2 line stands in for any stale rank the
    // commit path might retain; production width-1 searches don't emit one,
    // but the grading rule must not depend on that.
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 230 nodes 1000 pv e2e4');
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 2 score cp 225 nodes 1000 pv d2d4');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // The after-move search grades d2d4 a genuine blunder — the rank-2 entry
    // (cp 225, a "good" reading) must play no part in the verdict.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -54 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(2);
    expect(grade.esBefore - grade.esAfter).toBeGreaterThanOrEqual(BLUNDER_DROP);
    expect(grade.moveTier).toBe('wrong');
  });

  it('a mount search that returns fewer ranks than requested (none at all) never throws', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    // The engine settles with a bestmove but no exact info line at all —
    // rank 1 is missing from the committed lines. The grade must resolve
    // (null evals degrade to the neutral ES), never throw.
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const grade = await result.current.gradeMove(FEN, 'e2e4');
    expect(grade.moveTier).toBe('good');
    expect(grade.bestMoveUci).toBe('e2e4');
  });

  it('the exact-match fast path returns esAfter === esBefore, posts no second go, and playedLine deep-equals bestLine', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 40 nodes 1000 pv e2e4 e7e5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const grade = await result.current.gradeMove(FEN, 'e2e4');
    expect(grade.esAfter).toBe(grade.esBefore);
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(1);
    expect(grade.playedLine).toEqual(grade.bestLine);
    expect(grade.bestLine.moves).toEqual(['e2e4', 'e7e5']);
  });

  it('a non-matching played move returns playedLine.moves[0] === playedMoveUci followed by the after-search PV moves', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 230 nodes 1000 pv e2e4 e7e5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -110 nodes 1000 pv d7d5 g1f3');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    expect(grade.playedLine.moves).toEqual(['d2d4', 'd7d5', 'g1f3']);
  });
});

describe('useTrainGradingEngine — consistent evals & display clamp (190.1 UAT round 9, narrowed by 211-02)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  // NOTE (211-02): the two "played move matching a non-top mount rank grades
  // from that rank without a second search" tests that used to live here were
  // RETIRED with the mount-rank shortcut itself (D-05). Their replacement —
  // proving that even a spurious extra rank never short-circuits the
  // after-move search — lives in the width-1 mount search block above
  // ("the retired mount-rank shortcut must not resurrect").

  it('a played move whose after-search reads BETTER than the best move gets its displayed eval clamped to the best line', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 230 nodes 1000 pv e2e4 e7e5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // Raw UCI cp -260 (post-move fen is black to move, whitePovSign -1) ->
    // stored white-POV +260: the played move READS better than the best
    // move's 230 — the inversion this round fixes.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -260 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    // The verdict stays honest ("better than best" is correct)…
    expect(grade.moveTier).toBe('good');
    expect(grade.esAfter).toBeGreaterThan(grade.esBefore);
    // …but the DISPLAYED eval never contradicts the "best move" label.
    expect(grade.playedLine.evalCp).toBe(grade.bestLine.evalCp);
    expect(grade.playedLine.moves).toEqual(['d2d4', 'd7d5']);
  });

  it("startGameMoveSearch resolves a game move that IS the engine's top move straight from the settled mount search, dispatching no new search (211-02 consumer ledger row 4)", async () => {
    // At width 1 the only rank the exact-UCI lookup can match is the
    // engine's own top move — the deliberately RETAINED consumer of
    // rankLineForMove, narrowed from the old "any mount rank" behavior.
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 230 nodes 1000 pv e2e4 e7e5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });
    // Flush the mount search's resolution microtask so bestSearchRef is
    // settled — in production the reveal (this call's only caller) opens
    // only after gradeMove resolved, which guarantees the same.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    const goCountBefore = mockWorker.messages.filter((m) => m.startsWith('go ')).length;
    const line = await result.current.startGameMoveSearch(FEN, 'e2e4');
    expect(mockWorker.messages.filter((m) => m.startsWith('go ')).length).toBe(goCountBefore);
    expect(line.moves).toEqual(['e2e4', 'e7e5']);
    expect(line.evalCp).toBe(230);
  });

  it('startGameMoveSearch clamps a non-rank game move whose after-search reads better than the best move', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 230 nodes 1000 pv e2e4 e7e5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });
    // Flush the mount search's resolution microtask (see the rank-reuse test
    // above) so the clamp's best-line lookup sees the settled search.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    const linePromise = result.current.startGameMoveSearch(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -260 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const line = await linePromise;
    expect(line.moves).toEqual(['d2d4', 'd7d5']);
    expect(line.evalCp).toBe(230);
  });
});

// ─── Phase 235 (D-01/D-08): key-anchored grading ───────────────────────────

/** The FEN after a legal UCI move from `fen`, computed independently with chess.js. */
function fenAfter(fen: string, uci: string): string {
  const chess = new Chess(fen);
  chess.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.slice(4, 5) || undefined });
  return chess.fen();
}

function goCount(): number {
  return mockWorker.messages.filter((m) => m.startsWith('go ')).length;
}

describe('useTrainGradingEngine — key-anchored grading (Phase 235 D-01/D-08)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('a keyed startGrading searches the position AFTER the key at the mount budget, never the root (D-08)', () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });

    const afterKey = fenAfter(FEN, 'd2d4');
    expect(mockWorker.messages).toContain(`position fen ${afterKey}`);
    expect(mockWorker.messages).not.toContain(`position fen ${FEN}`);
    expect(mockWorker.messages).toContain(
      `go movetime ${TRAIN_GRADING_MOUNT_MOVETIME_MS} nodes ${TRAIN_GRADING_MAX_NODES}`,
    );
    expect(goCount()).toBe(1);
  });

  it('playing the key grades GOOD with no further search, and the key line is rooted at the puzzle fen (D-01)', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -40 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await result.current.gradeMove(FEN, 'd2d4');
    expect(grade.moveTier).toBe('good');
    expect(grade.bestMoveUci).toBe('d2d4');
    expect(grade.bestLine.moves).toEqual(['d2d4', 'd7d5']);
    expect(grade.playedLine).toEqual(grade.bestLine);
    expect(grade.esAfter).toBe(grade.esBefore);
    // Only the anchor's own search ever ran: playing the key posts no further `go`.
    expect(goCount()).toBe(1);
  });

  it('an off-key move runs ONE after-move search and is graded against the after-key ES, naming the key as best (D-01/D-09)', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });
    // Black to move after d2d4: raw cp -40 (black POV) -> white-POV +40.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -40 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const gradePromise = result.current.gradeMove(FEN, 'e2e4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(mockWorker.messages).toContain(`position fen ${fenAfter(FEN, 'e2e4')}`);
    expect(goCount()).toBe(2);
    // Black to move after e2e4: raw cp 300 (black POV) -> white-POV -300. The
    // anchor read +40 for white, so this is a large white drop.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 300 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    expect(grade.moveTier).toBe('wrong');
    // D-09: the key, not the phone's own pick, is named best.
    expect(grade.bestMoveUci).toBe('d2d4');
    expect(grade.bestLine.moves.slice(0, 2)).toEqual(['d2d4', 'd7d5']);
    expect(grade.playedLine.moves[0]).toBe('e2e4');
    // esBefore is the after-key ES (white +40), not a root reading.
    expect(grade.esBefore).toBe(evalToExpectedScore(40, null, 'white'));
    expect(grade.esAfter).toBe(evalToExpectedScore(-300, null, 'white'));
  });

  it('keeps the grading budget unchanged: no global movetime raise (D-03)', () => {
    expect(TRAIN_GRADING_MOVETIME_MS).toBe(1500);
    expect(TRAIN_GRADING_MAX_NODES).toBe(2000000);
  });
});

// ─── Phase 235 (D-07/D-09): legacy fallback, terminal positions, clamp ─────

// White to move, Ra8# is mate in one (back-rank).
const MATE_IN_ONE_FEN = '6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1';
// Two mating moves (Ra8# and Rb8#) plus a quiet king move (Kh1).
const TWO_MATES_FEN = '6k1/5ppp/8/8/8/8/5PPP/RR4K1 w - - 0 1';
// White to move; Qg6 is stalemate (black Kh8 has no move and is not in check).
const STALEMATE_FEN = '7k/5K2/8/6Q1/8/8/8/8 w - - 0 1';

describe('useTrainGradingEngine — anchor fallbacks, terminal positions, clamp (Phase 235 D-07/D-09)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  type StartArgs = [] | [null] | [string];
  it.each<[string, StartArgs]>([
    ['no key argument', []],
    ['a null key', [null]],
    ['an illegal key', ['e2e5']],
  ])('D-07: %s keeps the legacy root search and the exact-match fast path', async (_label, args) => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN, ...args);
    });
    expect(mockWorker.messages).toContain(`position fen ${FEN}`);
    expect(mockWorker.messages).toContain(`setoption name MultiPV value ${TRAIN_GRADING_MULTIPV_WIDTH}`);
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 40 nodes 1000 pv e2e4 e7e5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const grade = await result.current.gradeMove(FEN, 'e2e4');
    expect(grade.moveTier).toBe('good');
    expect(grade.bestMoveUci).toBe('e2e4');
    expect(grade.bestLine.moves).toEqual(['e2e4', 'e7e5']);
    expect(goCount()).toBe(1);
  });

  it('a mating key is scored without a search, and a weaker move is graded against the mate, not a neutral 0.5 (T-235-05)', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(MATE_IN_ONE_FEN, 'a1a8');
    });
    // The after-key position is checkmate: no `go` is dispatched for the anchor.
    expect(goCount()).toBe(0);

    const keyGrade = await result.current.gradeMove(MATE_IN_ONE_FEN, 'a1a8');
    expect(keyGrade.moveTier).toBe('good');
    expect(keyGrade.bestMoveUci).toBe('a1a8');
    expect(keyGrade.esBefore).toBeGreaterThan(0.9);
    expect(goCount()).toBe(0);

    // A quiet rook move: only the after-PLAYED position is searched.
    const gradePromise = result.current.gradeMove(MATE_IN_ONE_FEN, 'a1a2');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(goCount()).toBe(1);
    expect(mockWorker.messages).toContain(`position fen ${fenAfter(MATE_IN_ONE_FEN, 'a1a2')}`);
    // Black to move: raw cp -300 (black POV) -> white +300, still far below the mate.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -300 nodes 1000 pv g8f8');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove g8f8');
    });

    const grade = await gradePromise;
    expect(grade.moveTier).toBe('wrong');
    expect(grade.bestMoveUci).toBe('a1a8');
  });

  it('a played move that itself mates is scored without a search and grades good against a non-mating key', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    // Key = the quiet Kh1; the anchor search reads raw cp -100 (black POV) -> white +100.
    act(() => {
      result.current.startGrading(TWO_MATES_FEN, 'g1h1');
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -100 nodes 1000 pv g8f8');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove g8f8');
    });
    expect(goCount()).toBe(1);

    const grade = await result.current.gradeMove(TWO_MATES_FEN, 'b1b8');
    expect(grade.moveTier).toBe('good');
    expect(grade.esAfter).toBeGreaterThan(grade.esBefore);
    // The mating move needed no search at all.
    expect(goCount()).toBe(1);
  });

  it('a played move that stalemates is scored as a draw (evalCp 0) without a search', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    // Key = a queen move that keeps a big edge: raw cp -500 (black POV) -> white +500.
    act(() => {
      result.current.startGrading(STALEMATE_FEN, 'g5d5');
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -500 nodes 1000 pv h8g8');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove h8g8');
    });
    expect(goCount()).toBe(1);

    const grade = await result.current.gradeMove(STALEMATE_FEN, 'g5g6');
    expect(goCount()).toBe(1);
    expect(grade.playedLine.evalCp).toBe(0);
    expect(grade.esAfter).toBe(0.5);
    // Throwing away a won position into a draw is a blunder-sized drop.
    expect(grade.moveTier).toBe('wrong');
  });

  it('D-09 clamp: an off-key move whose after-search reads better than the key line grades good and its line is capped at the key line eval', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });
    // Key line: raw cp -40 (black POV) -> white +40.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -40 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const gradePromise = result.current.gradeMove(FEN, 'e2e4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // Played line reads raw cp -260 (black POV) -> white +260: better than the key.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -260 nodes 1000 pv e7e5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e7e5');
    });

    const grade = await gradePromise;
    expect(grade.moveTier).toBe('good');
    expect(grade.esAfter).toBeGreaterThan(grade.esBefore);
    expect(grade.playedLine.evalCp).toBe(grade.bestLine.evalCp);
    expect(grade.playedLine.evalCp).toBe(40);
    expect(grade.playedLine.moves).toEqual(['e2e4', 'e7e5']);
  });

  it('D-09 game move: a game move equal to the key resolves the key line with no search', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -40 nodes 1000 pv d7d5 g1f3');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    const goCountBefore = goCount();
    const line = await result.current.startGameMoveSearch(FEN, 'd2d4');
    expect(goCount()).toBe(goCountBefore);
    expect(line.moves).toEqual(['d2d4', 'd7d5', 'g1f3']);
    expect(line.evalCp).toBe(40);
  });

  it('D-09 game move: a different game move posts ONE after-move search and its eval is clamped to the key line', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -40 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    const goCountBefore = goCount();
    const linePromise = result.current.startGameMoveSearch(FEN, 'e2e4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(goCount()).toBe(goCountBefore + 1);
    expect(mockWorker.messages).toContain(`position fen ${fenAfter(FEN, 'e2e4')}`);
    // Raw cp -260 (black POV) -> white +260: better than the key line's +40.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -260 nodes 1000 pv e7e5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e7e5');
    });

    const line = await linePromise;
    expect(line.moves).toEqual(['e2e4', 'e7e5']);
    expect(line.evalCp).toBe(40);
  });
});

// ─── Phase 235 (D-11/D-13/D-16/D-20): disagreement re-check ────────────────

const RECHECK_GO = `go movetime ${TRAIN_RECHECK_MOVETIME_MS} nodes ${TRAIN_RECHECK_MAX_NODES}`;

/**
 * Answer the in-flight search of a position where BLACK is to move (every
 * after-move position in these tests): the raw UCI score is black-POV, so the
 * white-POV reading `whiteCp` is sent negated. `pv` is the engine line.
 */
function answerSearch(whiteCp: number, depth: number, pv: string): void {
  act(() => {
    mockWorker.simulateMessage(`info depth ${depth} multipv 1 score cp ${-whiteCp} nodes 1000 pv ${pv}`);
  });
  act(() => {
    mockWorker.simulateMessage(`bestmove ${pv.split(' ')[0]}`);
  });
}

async function flush(): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
}

interface FastReadings {
  keyWhiteCp: number;
  keyDepth: number;
  playedWhiteCp: number;
  playedDepth: number;
}

type GradingHook = { current: ReturnType<typeof useTrainGradingEngine> };

/** Run the keyed anchor search (key d2d4) and grade the off-key e2e4 from the 1.5 s readings. */
async function gradeOffKey(result: GradingHook, fast: FastReadings) {
  act(() => {
    result.current.startGrading(FEN, 'd2d4');
  });
  answerSearch(fast.keyWhiteCp, fast.keyDepth, 'd7d5 g1f3');
  const gradePromise = result.current.gradeMove(FEN, 'e2e4');
  await flush();
  answerSearch(fast.playedWhiteCp, fast.playedDepth, 'e7e5 g1f3');
  return gradePromise;
}

/** Answer both re-check searches (key, then played) with the given 3 s white-POV readings. */
async function answerRecheck(keyWhiteCp: number, keyDepth: number, playedWhiteCp: number, playedDepth: number) {
  answerSearch(keyWhiteCp, keyDepth, 'd7d5 b1c3');
  await flush();
  answerSearch(playedWhiteCp, playedDepth, 'e7e5 b1c3');
}

const GOOD_FAST: FastReadings = { keyWhiteCp: 40, keyDepth: 12, playedWhiteCp: 30, playedDepth: 11 };

describe('useTrainGradingEngine — disagreement re-check (Phase 235 D-11/D-13/D-16/D-20)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('(a) posts exactly two re-check dispatches, the after-key position first and the after-played one only after the first bestmove', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    await gradeOffKey(result, GOOD_FAST);

    const goBefore = goCount();
    const recheckPromise = result.current.recheckMove(FEN, 'e2e4');
    expect(goCount()).toBe(goBefore + 1);
    expect(mockWorker.messages.at(-1)).toBe(RECHECK_GO);
    expect(mockWorker.messages.at(-2)).toBe(`position fen ${fenAfter(FEN, 'd2d4')}`);

    answerSearch(40, 18, 'd7d5 b1c3');
    await flush();
    expect(goCount()).toBe(goBefore + 2);
    expect(mockWorker.messages.at(-1)).toBe(RECHECK_GO);
    expect(mockWorker.messages.at(-2)).toBe(`position fen ${fenAfter(FEN, 'e2e4')}`);

    answerSearch(30, 17, 'e7e5 b1c3');
    const outcome = await recheckPromise;
    expect(outcome).not.toBeNull();
    expect(mockWorker.messages.filter((m) => m === RECHECK_GO)).toHaveLength(2);
  });

  it('(b) confirmed: a played move still good at 3 s keeps its honest eval, and the payload carries the 1.5 s values and the matching depths', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    await gradeOffKey(result, GOOD_FAST);

    const recheckPromise = result.current.recheckMove(FEN, 'e2e4');
    // The played move now reads BETTER than the key (white +260 vs +40).
    await answerRecheck(40, 18, 260, 17);
    const outcome = await recheckPromise;

    expect(outcome?.recheck.outcome).toBe('confirmed');
    expect(outcome?.grade.moveTier).toBe('good');
    expect(outcome?.grade.bestMoveUci).toBe('d2d4');
    expect(outcome?.grade.bestLine.moves).toEqual(['d2d4', 'd7d5', 'b1c3']);
    expect(outcome?.grade.playedLine.moves).toEqual(['e2e4', 'e7e5', 'b1c3']);
    // D-16: NOT capped at the key line's +40.
    expect(outcome?.grade.playedLine.evalCp).toBe(260);
    expect(outcome?.recheck).toEqual({
      v: 1,
      outcome: 'confirmed',
      key_es: evalToExpectedScore(40, null, 'white'),
      played_es: evalToExpectedScore(30, null, 'white'),
      key_es_recheck: evalToExpectedScore(40, null, 'white'),
      played_es_recheck: evalToExpectedScore(260, null, 'white'),
      key_depth: 12,
      played_depth: 11,
      key_depth_recheck: 18,
      played_depth_recheck: 17,
    });
  });

  it('(c) resolved: a 3 s pair in the mistake band is graded wrong with the outcome resolved and the played line not above the key line', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    await gradeOffKey(result, GOOD_FAST);

    const recheckPromise = result.current.recheckMove(FEN, 'e2e4');
    await answerRecheck(40, 18, -300, 17);
    const outcome = await recheckPromise;

    expect(outcome?.recheck.outcome).toBe('resolved');
    expect(outcome?.grade.moveTier).toBe('wrong');
    expect(outcome?.grade.esBefore).toBe(evalToExpectedScore(40, null, 'white'));
    expect(outcome?.grade.esAfter).toBe(evalToExpectedScore(-300, null, 'white'));
    expect(outcome?.grade.playedLine.evalCp).toBeLessThanOrEqual(outcome?.grade.bestLine.evalCp ?? 0);
    expect(outcome?.recheck.played_es_recheck).toBe(evalToExpectedScore(-300, null, 'white'));
  });

  it('(d) a stalled re-check resolves null after TRAIN_RECHECK_TIMEOUT_MS and a late answer never changes the anchor (D-20)', async () => {
    expect(TRAIN_RECHECK_TIMEOUT_MS).toBeGreaterThan(2 * TRAIN_RECHECK_MOVETIME_MS);
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    await gradeOffKey(result, GOOD_FAST);

    const recheckPromise = result.current.recheckMove(FEN, 'e2e4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(TRAIN_RECHECK_TIMEOUT_MS);
    });
    expect(await recheckPromise).toBeNull();

    // The stalled searches are answered afterwards (a deep 3 s reading that
    // would have confirmed): the timed-out re-check must not swap the anchor.
    await answerRecheck(500, 30, 900, 29);
    await flush();

    const line = await result.current.startGameMoveSearch(FEN, 'd2d4');
    expect(line.moves).toEqual(['d2d4', 'd7d5', 'g1f3']);
    expect(line.evalCp).toBe(40);
  });

  it('(d2) a key search that lands AFTER the timeout never dispatches the played re-check search (WR-01)', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    await gradeOffKey(result, GOOD_FAST);

    const goBefore = goCount();
    const recheckPromise = result.current.recheckMove(FEN, 'e2e4');
    expect(goCount()).toBe(goBefore + 1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(TRAIN_RECHECK_TIMEOUT_MS);
    });
    expect(await recheckPromise).toBeNull();

    // The stalled key search finally answers. The timed-out re-check must not
    // go on to occupy the engine with its second (played) 3 s search.
    answerSearch(40, 18, 'd7d5 b1c3');
    await flush();
    expect(goCount()).toBe(goBefore + 1);
  });

  it('(e) a legacy (null-key) anchor resolves null without posting a search', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    act(() => {
      result.current.startGrading(FEN);
    });
    // Root search (white to move): raw cp is white-POV; best move d2d4.
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 40 nodes 1000 pv d2d4 d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d2d4');
    });
    const gradePromise = result.current.gradeMove(FEN, 'e2e4');
    await flush();
    answerSearch(30, 11, 'e7e5');
    await gradePromise;

    const goBefore = goCount();
    expect(await result.current.recheckMove(FEN, 'e2e4')).toBeNull();
    expect(goCount()).toBe(goBefore);
  });

  it('(f) after a confirmed re-check, startGameMoveSearch for a non-key game move resolves an unclamped eval', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    await gradeOffKey(result, GOOD_FAST);
    const recheckPromise = result.current.recheckMove(FEN, 'e2e4');
    await answerRecheck(40, 18, 260, 17);
    expect((await recheckPromise)?.recheck.outcome).toBe('confirmed');

    const linePromise = result.current.startGameMoveSearch(FEN, 'g1f3');
    await flush();
    answerSearch(300, 16, 'd7d5');
    const line = await linePromise;
    expect(line.evalCp).toBe(300);
  });

  it('(f) after a resolved re-check, a game move reading better than the key stays clamped to the 3 s key line', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    await gradeOffKey(result, GOOD_FAST);
    const recheckPromise = result.current.recheckMove(FEN, 'e2e4');
    await answerRecheck(55, 18, -300, 17);
    expect((await recheckPromise)?.recheck.outcome).toBe('resolved');

    const linePromise = result.current.startGameMoveSearch(FEN, 'g1f3');
    await flush();
    answerSearch(300, 16, 'd7d5');
    const line = await linePromise;
    // Capped at the 3 s key reading (white +55), not the 1.5 s one (+40).
    expect(line.evalCp).toBe(55);
  });

  it('(g) ordinary anchor, grade and game-move searches still post the 2M grading cap', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    await gradeOffKey(result, GOOD_FAST);
    const linePromise = result.current.startGameMoveSearch(FEN, 'g1f3');
    await flush();
    answerSearch(30, 16, 'd7d5');
    await linePromise;

    const goMessages = mockWorker.messages.filter((m) => m.startsWith('go '));
    expect(goMessages).toHaveLength(3);
    for (const message of goMessages) {
      expect(message).toBe(`go movetime ${TRAIN_GRADING_MOVETIME_MS} nodes ${TRAIN_GRADING_MAX_NODES}`);
    }
    expect(TRAIN_RECHECK_MAX_NODES).toBeGreaterThan(TRAIN_GRADING_MAX_NODES);
  });

  it('(h) the raised node cap survives the stop-queue drain when a re-check search is deferred behind a running search', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    await gradeOffKey(result, GOOD_FAST);

    // A reveal game-move search is still thinking when the re-check dispatches.
    void result.current.startGameMoveSearch(FEN, 'g1f3').catch(() => {});
    await flush();
    const recheckPromise = result.current.recheckMove(FEN, 'e2e4');
    expect(mockWorker.messages.at(-1)).toBe('stop');

    // The engine answers the stop; the queued re-check search then dispatches.
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });
    expect(mockWorker.messages.at(-1)).toBe(RECHECK_GO);
    answerSearch(40, 18, 'd7d5');
    await flush();
    answerSearch(30, 17, 'e7e5');
    expect(await recheckPromise).not.toBeNull();
  });
});

// ─── Phase 236 (D-04/D-05/D-06): the phone_grade reading ───────────────────

describe('useTrainGradingEngine — phone reading (Phase 236 D-04/D-05/D-06)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  /** Settle a keyed anchor search at depth 12 reading raw cp -40 (black POV) after d2d4. */
  function settleKeyedAnchor(startGrading: (fen: string, key: string) => void): void {
    act(() => {
      startGrading(FEN, 'd2d4');
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp -40 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });
  }

  it('playing the key records a good tier with the played pair equal to the key pair (D-05)', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    settleKeyedAnchor(result.current.startGrading);

    const grade = await result.current.gradeMove(FEN, 'd2d4');
    expect(grade.phoneReading).toEqual({
      tier: 'good',
      keyEs: grade.esBefore,
      playedEs: grade.esBefore,
      keyDepth: 12,
      playedDepth: 12,
    });
  });

  it('an off-key move takes the key pair from the anchor and the played pair from the after-played search (D-04)', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    settleKeyedAnchor(result.current.startGrading);

    const gradePromise = result.current.gradeMove(FEN, 'e2e4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 9 multipv 1 score cp 300 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });

    const grade = await gradePromise;
    expect(grade.phoneReading).toEqual({
      tier: grade.moveTier,
      keyEs: grade.esBefore,
      playedEs: grade.esAfter,
      keyDepth: 12,
      playedDepth: 9,
    });
    expect(grade.moveTier).toBe('wrong');
  });

  it('the legacy root anchor records nothing, for the root bestmove and for an off-key move (D-06)', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);

    act(() => {
      result.current.startGrading(FEN);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 12 multipv 1 score cp 40 nodes 1000 pv e2e4 e7e5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove e2e4');
    });

    const keyGrade = await result.current.gradeMove(FEN, 'e2e4');
    expect(keyGrade.phoneReading ?? null).toBeNull();

    const gradePromise = result.current.gradeMove(FEN, 'd2d4');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    act(() => {
      mockWorker.simulateMessage('info depth 10 multipv 1 score cp 20 nodes 1000 pv d7d5');
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5');
    });
    const offKeyGrade = await gradePromise;
    expect(offKeyGrade.phoneReading ?? null).toBeNull();
  });

  it('the defensive fallbacks (anchor mismatch, illegal played move) record nothing', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    settleKeyedAnchor(result.current.startGrading);

    const illegal = await result.current.gradeMove(FEN, 'e2e5');
    expect(illegal.moveTier).toBe('good');
    expect(illegal.phoneReading ?? null).toBeNull();

    const mismatch = await result.current.gradeMove(fenAfter(FEN, 'e2e4'), 'e7e5');
    expect(mismatch.moveTier).toBe('good');
    expect(mismatch.phoneReading ?? null).toBeNull();
  });
});

// ─── Phase 236 (RESEARCH Pitfall 1): instant-path serialization ────────────

describe('useTrainGradingEngine: instant-path serialization (Phase 236 Pitfall 1)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  async function flush(): Promise<void> {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
  }

  /** Answer the search the Worker is currently running (raw cp is from the side to move). */
  function answerCurrentSearch(rawCp: number, depth: number, pv: string): void {
    act(() => {
      mockWorker.simulateMessage(
        `info depth ${depth} multipv 1 score cp ${rawCp} nodes 1000 pv ${pv}`,
      );
    });
    act(() => {
      mockWorker.simulateMessage(`bestmove ${pv.split(' ')[0]}`);
    });
  }

  function stopCount(): number {
    return mockWorker.messages.filter((m) => m === 'stop').length;
  }

  function positions(): string[] {
    return mockWorker.messages.filter((m) => m.startsWith('position fen '));
  }

  it('a game search started while the played search runs queues behind it, then runs after grading resolves', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });
    answerCurrentSearch(-40, 12, 'd7d5');

    const gradePromise = result.current.gradeMove(FEN, 'e2e4');
    await flush();
    expect(goCount()).toBe(2);

    const gamePromise = result.current.startGameMoveSearch(FEN, 'g1f3');
    await flush();
    // Pitfall 1: the reveal's search must neither stop the played search nor dispatch yet.
    expect(stopCount()).toBe(0);
    expect(goCount()).toBe(2);

    answerCurrentSearch(300, 9, 'd7d5');
    const grade = await gradePromise;
    expect(grade.phoneReading).not.toBeNull();
    expect(grade.phoneReading?.playedDepth).toBe(9);

    // Only now does the game search dispatch.
    await flush();
    expect(goCount()).toBe(3);
    expect(positions().at(-1)).toBe(`position fen ${fenAfter(FEN, 'g1f3')}`);
    expect(stopCount()).toBe(0);
    answerCurrentSearch(20, 10, 'd7d5');
    const line = await gamePromise;
    expect(line.moves[0]).toBe('g1f3');
  });

  it('a fast mover (gradeMove during the anchor search, then the game search) runs anchor -> played -> game with no stop', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });

    const gradePromise = result.current.gradeMove(FEN, 'e2e4');
    const gamePromise = result.current.startGameMoveSearch(FEN, 'g1f3');
    await flush();
    expect(stopCount()).toBe(0);
    expect(goCount()).toBe(1);

    answerCurrentSearch(-40, 12, 'd7d5'); // anchor settles
    await flush();
    expect(goCount()).toBe(2);
    expect(stopCount()).toBe(0);

    answerCurrentSearch(300, 9, 'd7d5'); // played settles
    const grade = await gradePromise;
    expect(grade.phoneReading).not.toBeNull();
    await flush();
    expect(goCount()).toBe(3);
    answerCurrentSearch(20, 10, 'd7d5'); // game
    const line = await gamePromise;
    expect(line.moves[0]).toBe('g1f3');

    expect(stopCount()).toBe(0);
    expect(positions()).toEqual([
      `position fen ${fenAfter(FEN, 'd2d4')}`,
      `position fen ${fenAfter(FEN, 'e2e4')}`,
      `position fen ${fenAfter(FEN, 'g1f3')}`,
    ]);
  });

  it('a game search queued behind grading never dispatches for the old puzzle once a new one starts, and rejects', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });
    answerCurrentSearch(-40, 12, 'd7d5');

    const gradePromise = result.current.gradeMove(FEN, 'e2e4');
    const gradeAssertion = expect(gradePromise).rejects.toThrow();
    await flush();
    const gamePromise = result.current.startGameMoveSearch(FEN, 'g1f3');
    const gameAssertion = expect(gamePromise).rejects.toThrow();
    await flush();

    // New puzzle: supersedes the stuck played search (the Worker is stopped).
    act(() => {
      result.current.startGrading(BLACK_TO_MOVE_FEN);
    });
    act(() => {
      mockWorker.simulateMessage('bestmove d7d5'); // stop echo, discarded
    });
    answerCurrentSearch(10, 12, 'g8f6'); // settles the NEW puzzle's anchor

    await act(async () => {
      await vi.advanceTimersByTimeAsync(TRAIN_GRADING_TIMEOUT_MS + 100);
    });
    await gameAssertion;
    await gradeAssertion;
    expect(positions()).not.toContain(`position fen ${fenAfter(FEN, 'g1f3')}`);
  });
});

// ─── Phase 236 (D-14): the early key-line callback ─────────────────────────

describe('useTrainGradingEngine: onKeyLine (Phase 236 D-14)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: 0 });
    mockWorker = new MockWorker();
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        return mockWorker;
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  function answerCurrentSearch(rawCp: number, depth: number, pv: string): void {
    act(() => {
      mockWorker.simulateMessage(
        `info depth ${depth} multipv 1 score cp ${rawCp} nodes 1000 pv ${pv}`,
      );
    });
    act(() => {
      mockWorker.simulateMessage(`bestmove ${pv.split(' ')[0]}`);
    });
  }

  it('a keyed anchor hands the key line over once, before the played search result', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });
    answerCurrentSearch(-40, 12, 'd7d5');

    const onKeyLine = vi.fn();
    const gradePromise = result.current.gradeMove(FEN, 'e2e4', { onKeyLine });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // The played search is still running: the key line is already out.
    expect(goCount()).toBe(2);
    expect(onKeyLine).toHaveBeenCalledTimes(1);
    expect(onKeyLine.mock.calls[0]?.[0]).toMatchObject({ moves: ['d2d4', 'd7d5'] });

    answerCurrentSearch(300, 9, 'd7d5');
    await gradePromise;
    expect(onKeyLine).toHaveBeenCalledTimes(1);
  });

  it('playing the key still calls onKeyLine once, then resolves as before', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });
    answerCurrentSearch(-40, 12, 'd7d5');

    const onKeyLine = vi.fn();
    const grade = await result.current.gradeMove(FEN, 'd2d4', { onKeyLine });
    expect(onKeyLine).toHaveBeenCalledTimes(1);
    expect(onKeyLine.mock.calls[0]?.[0]).toEqual(grade.bestLine);
    expect(grade.moveTier).toBe('good');
  });

  it('a legacy (null key) root anchor never calls onKeyLine', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    act(() => {
      result.current.startGrading(FEN);
    });
    answerCurrentSearch(40, 12, 'e2e4 e7e5');

    const onKeyLine = vi.fn();
    const keyGrade = await result.current.gradeMove(FEN, 'e2e4', { onKeyLine });
    expect(keyGrade.moveTier).toBe('good');
    expect(onKeyLine).not.toHaveBeenCalled();

    const offKey = result.current.gradeMove(FEN, 'd2d4', { onKeyLine });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    answerCurrentSearch(20, 10, 'd7d5');
    await offKey;
    expect(onKeyLine).not.toHaveBeenCalled();
  });

  it('works unchanged without options', async () => {
    const { result } = renderHook(() => useTrainGradingEngine({ enabled: true }));
    driveInit(mockWorker);
    act(() => {
      result.current.startGrading(FEN, 'd2d4');
    });
    answerCurrentSearch(-40, 12, 'd7d5');
    const grade = await result.current.gradeMove(FEN, 'd2d4');
    expect(grade.moveTier).toBe('good');
  });
});
