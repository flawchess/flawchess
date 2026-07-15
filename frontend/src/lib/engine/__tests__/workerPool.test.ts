// @vitest-environment jsdom
/**
 * workerPool.ts mock-Worker unit tests.
 *
 * Task 1 covers the pure priority-queue (POOL-02) and adaptive pool-sizing
 * (POOL-04/D-01) functions in isolation — no Worker instantiation needed yet.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import * as Sentry from '@sentry/react';
import {
  enqueue,
  dequeueHighestPriority,
  computePoolSize,
  createWorkerPool,
  DESKTOP_POOL_MIN,
  DESKTOP_POOL_MAX,
  MOBILE_POOL_SIZE,
  type QueuedGradeRequest,
  type WorkerPool,
} from '../workerPool';
import type { EngineProviders } from '../types';

// @sentry/react's ESM module namespace is not configurable, so vi.spyOn cannot
// redefine captureException on the real module — mock the module instead
// (mirrors maiaQueue.test.ts).
vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

// ─── Mock Worker (multi-instance — a pool spawns N separate Worker()s) ──────

class MockWorker {
  onmessage: ((e: MessageEvent<string>) => void) | null = null;
  onerror: ((e: ErrorEvent) => void) | null = null;
  messages: string[] = [];
  terminated = false;

  postMessage(msg: string): void {
    this.messages.push(msg);
  }

  terminate(): void {
    this.terminated = true;
  }

  /** Fire the onmessage handler with a synthetic UCI line. */
  simulateMessage(data: string): void {
    this.onmessage?.(new MessageEvent('message', { data }));
  }

  /** Fire the onerror handler (async script-load failure — never a sync throw). */
  simulateError(): void {
    this.onerror?.(new ErrorEvent('error', { message: 'simulated worker load failure' }));
  }
}

let createdWorkers: MockWorker[];

function stubWorkerCtor(): void {
  createdWorkers = [];
  vi.stubGlobal(
    'Worker',
    vi.fn(function (this: unknown) {
      const w = new MockWorker();
      createdWorkers.push(w);
      return w;
    }),
  );
}

/** Drive one mock worker through the full UCI init sequence (uciok -> Hash -> isready -> readyok). */
function driveInit(worker: MockWorker): void {
  worker.simulateMessage('uciok');
  worker.simulateMessage('readyok');
}

function stubDesktopSizing(cores: number): void {
  Object.defineProperty(navigator, 'hardwareConcurrency', {
    writable: true,
    configurable: true,
    value: cores,
  });
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
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
}

// Black-to-move FEN after 1. e4 — used for white-POV negation assertions.
const TEST_FEN = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
const TEST_FEN_2 = 'rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1';

// ─── Priority queue (POOL-02) ───────────────────────────────────────────────

describe('enqueue / dequeueHighestPriority', () => {
  it('dequeues the higher-priority request first, regardless of enqueue order', () => {
    const pending: QueuedGradeRequest[] = [];
    enqueue(pending, { fen: 'FEN_A', candidateUcis: ['e2e4'], priority: 0.2, depth: 3, resolve: vi.fn() });
    enqueue(pending, { fen: 'FEN_B', candidateUcis: ['d7d5'], priority: 0.8, depth: 3, resolve: vi.fn() });
    // FEN_A was enqueued FIRST (would win under FIFO) but has LOWER priority.
    const next = dequeueHighestPriority(pending);
    expect(next?.fen).toBe('FEN_B'); // priority wins, not arrival order
    expect(pending).toHaveLength(1);
    expect(pending[0]?.fen).toBe('FEN_A');
  });

  it('breaks a priority tie by shallower depth first', () => {
    const pending: QueuedGradeRequest[] = [];
    enqueue(pending, { fen: 'FEN_DEEP', candidateUcis: ['e2e4'], priority: 0.5, depth: 5, resolve: vi.fn() });
    enqueue(pending, { fen: 'FEN_SHALLOW', candidateUcis: ['d7d5'], priority: 0.5, depth: 2, resolve: vi.fn() });
    const next = dequeueHighestPriority(pending);
    expect(next?.fen).toBe('FEN_SHALLOW');
  });

  it('breaks a priority+depth tie by ascending candidateUcis[0] string', () => {
    const pending: QueuedGradeRequest[] = [];
    enqueue(pending, { fen: 'FEN_LATER', candidateUcis: ['e2e4'], priority: 0.5, depth: 3, resolve: vi.fn() });
    enqueue(pending, { fen: 'FEN_EARLIER', candidateUcis: ['a2a4'], priority: 0.5, depth: 3, resolve: vi.fn() });
    const next = dequeueHighestPriority(pending);
    expect(next?.fen).toBe('FEN_EARLIER'); // 'a2a4' < 'e2e4'
  });

  it('returns undefined on an empty pending array', () => {
    expect(dequeueHighestPriority([])).toBeUndefined();
  });
});

// ─── Adaptive pool sizing (POOL-04/D-01) ───────────────────────────────────

describe('computePoolSize', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubMatchMedia(matches: boolean): void {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  }

  function stubCores(cores: number | undefined): void {
    Object.defineProperty(navigator, 'hardwareConcurrency', {
      writable: true,
      configurable: true,
      value: cores,
    });
  }

  it('returns MOBILE_POOL_SIZE when hardwareConcurrency <= 4', () => {
    stubMatchMedia(false);
    stubCores(4);
    expect(computePoolSize()).toBe(MOBILE_POOL_SIZE);
  });

  it('returns MOBILE_POOL_SIZE when matchMedia(pointer: coarse) matches, even if cores > 4', () => {
    stubMatchMedia(true);
    stubCores(8);
    expect(computePoolSize()).toBe(MOBILE_POOL_SIZE);
  });

  it('returns clamp(cores-2, 2, 4) on desktop: cores=8 -> 4', () => {
    stubMatchMedia(false);
    stubCores(8);
    expect(computePoolSize()).toBe(DESKTOP_POOL_MAX);
  });

  it('returns clamp(cores-2, 2, 4) on desktop: cores=6 -> 4', () => {
    stubMatchMedia(false);
    stubCores(6);
    expect(computePoolSize()).toBe(4);
  });

  it('returns clamp(cores-2, 2, 4) on desktop: cores=5 -> 3', () => {
    stubMatchMedia(false);
    stubCores(5);
    expect(computePoolSize()).toBe(3);
  });

  it('falls back to DESKTOP_POOL_MIN when hardwareConcurrency is undefined/0', () => {
    stubMatchMedia(false);
    stubCores(0);
    expect(computePoolSize()).toBe(DESKTOP_POOL_MIN);
  });
});

// ─── createWorkerPool: grade() dispatch (POOL-01, SC5) ─────────────────────

describe('createWorkerPool: grade() dispatch', () => {
  beforeEach(() => {
    stubDesktopSizing(6); // computePoolSize() -> 4 slots
    stubWorkerCtor();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('grade() resolves a Map keyed by pv[0] (UCI), white-POV normalized', async () => {
    const pool = createWorkerPool();
    const gradePromise = pool.grade(TEST_FEN, ['e7e5', 'c7c5']);
    expect(createdWorkers.length).toBeGreaterThan(0);
    const worker = createdWorkers[0]!;
    driveInit(worker);

    // TEST_FEN is black-to-move: UCI score cp 50 (mover=black POV) must
    // negate to white-POV = -50.
    worker.simulateMessage('info depth 10 multipv 1 score cp 50 nodes 1000 pv e7e5');
    worker.simulateMessage('info depth 10 multipv 2 score cp 30 nodes 1000 pv c7c5');
    worker.simulateMessage('bestmove e7e5');

    const grades = await gradePromise;
    expect(grades.get('e7e5')?.evalCp).toBe(-50);
    expect(grades.get('c7c5')?.evalCp).toBe(-30);
  });

  it('drops illegal/unparseable info lines without throwing', async () => {
    const pool = createWorkerPool();
    const gradePromise = pool.grade(TEST_FEN, ['e7e5']);
    const worker = createdWorkers[0]!;
    driveInit(worker);

    expect(() => worker.simulateMessage('info this is not a valid uci line')).not.toThrow();
    worker.simulateMessage('info depth 10 multipv 1 score cp 12 nodes 1000 pv e7e5');
    worker.simulateMessage('bestmove e7e5');

    const grades = await gradePromise;
    expect(grades.get('e7e5')?.evalCp).toBe(-12);
  });

  it('multipv-rank-swap regression: two lines swapping multipv rank between depths stay keyed by their own move', async () => {
    const pool = createWorkerPool();
    const gradePromise = pool.grade(TEST_FEN, ['e7e5', 'c7c5']);
    const worker = createdWorkers[0]!;
    driveInit(worker);

    // Depth 8: e7e5 is multipv 1, c7c5 is multipv 2.
    worker.simulateMessage('info depth 8 multipv 1 score cp 40 nodes 1000 pv e7e5');
    worker.simulateMessage('info depth 8 multipv 2 score cp 20 nodes 1000 pv c7c5');
    // Depth 10: ranks SWAP — c7c5 is now multipv 1, e7e5 is multipv 2.
    worker.simulateMessage('info depth 10 multipv 1 score cp 25 nodes 2000 pv c7c5');
    worker.simulateMessage('info depth 10 multipv 2 score cp 45 nodes 2000 pv e7e5');
    worker.simulateMessage('bestmove c7c5');

    const grades = await gradePromise;
    // Each move's grade reflects ITS OWN last-reported line, not the rank slot.
    expect(grades.get('e7e5')?.depth).toBe(10);
    expect(grades.get('e7e5')?.evalCp).toBe(-45);
    expect(grades.get('c7c5')?.depth).toBe(10);
    expect(grades.get('c7c5')?.evalCp).toBe(-25);
  });

  it('cache-hit: a repeat grade() for an already-graded FEN issues no additional go message', async () => {
    const pool = createWorkerPool();
    const first = pool.grade(TEST_FEN, ['e7e5', 'c7c5']);
    const worker = createdWorkers[0]!;
    driveInit(worker);
    worker.simulateMessage('info depth 14 multipv 1 score cp 10 nodes 1000 pv e7e5');
    worker.simulateMessage('info depth 14 multipv 2 score cp 5 nodes 1000 pv c7c5');
    worker.simulateMessage('bestmove e7e5');
    await first;

    const goCountBefore = worker.messages.filter((m) => m.startsWith('go ')).length;
    const second = await pool.grade(TEST_FEN, ['e7e5', 'c7c5']);
    const goCountAfter = worker.messages.filter((m) => m.startsWith('go ')).length;

    expect(goCountAfter).toBe(goCountBefore);
    expect(second.get('e7e5')?.evalCp).toBe(-10);
  });

  it('two concurrent grade() calls occupy two distinct free worker slots', async () => {
    const pool = createWorkerPool();
    const first = pool.grade(TEST_FEN, ['e7e5']);
    const second = pool.grade(TEST_FEN_2, ['d7d5']);
    expect(createdWorkers.length).toBeGreaterThanOrEqual(2);

    // Bring every spawned slot to readyok so dispatchNext can assign both
    // pending requests regardless of dispatch order.
    for (const w of createdWorkers) driveInit(w);

    const workerForFen = (fen: string): MockWorker | undefined =>
      createdWorkers.find((w) => w.messages.includes(`position fen ${fen}`));
    const w1 = workerForFen(TEST_FEN);
    const w2 = workerForFen(TEST_FEN_2);
    expect(w1).toBeDefined();
    expect(w2).toBeDefined();
    expect(w1).not.toBe(w2); // two DISTINCT slots, not one worker serializing both

    w1!.simulateMessage('info depth 14 multipv 1 score cp 10 nodes 1000 pv e7e5');
    w1!.simulateMessage('bestmove e7e5');
    w2!.simulateMessage('info depth 14 multipv 1 score cp -10 nodes 1000 pv d7d5');
    w2!.simulateMessage('bestmove d7d5');

    const grades1 = await first;
    const grades2 = await second;
    expect(grades1.get('e7e5')?.evalCp).toBe(-10);
    expect(grades2.get('d7d5')?.evalCp).toBe(10);
  });
});

// ─── createWorkerPool: lazy spawn + abort/lifecycle surface (POOL-04, D-02, D-03) ──

describe('createWorkerPool: lifecycle', () => {
  beforeEach(() => {
    stubDesktopSizing(6); // computePoolSize() -> 4 slots
    stubWorkerCtor();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('D-02: no Worker is constructed until the first grade() call (lazy spawn)', () => {
    createWorkerPool();
    expect(createdWorkers.length).toBe(0);
  });

  it('spawns computePoolSize() slots on the first grade() call', () => {
    const pool = createWorkerPool();
    void pool.grade(TEST_FEN, ['e7e5']);
    expect(createdWorkers.length).toBe(4); // stubDesktopSizing(6) -> 6-2 clamped -> 4
  });

  // ─── Prewarm (Phase 169.5, SC5) ─────────────────────────────────────────

  it('warm() spawns computePoolSize() workers', () => {
    const pool = createWorkerPool();
    pool.warm();
    expect(createdWorkers.length).toBe(computePoolSize());
  });

  it('warm() issues no search', () => {
    const pool = createWorkerPool();
    pool.warm();
    // Spawn-time UCI handshake traffic (uci / setoption / isready) is expected
    // and fine. A `go` is not — warm() must cost no movetime.
    for (const worker of createdWorkers) {
      expect(worker.messages.some((m) => m.startsWith('go'))).toBe(false);
    }
  });

  it('warm() is idempotent', () => {
    const pool = createWorkerPool();
    pool.warm();
    pool.warm();
    expect(createdWorkers.length).toBe(computePoolSize());
  });

  it('grade(fen, []) spawns nothing — WR-05 no-op (this is why warm() exists)', async () => {
    // Pins RESEARCH.md Pitfall 2. `grade()` returns on the WR-05
    // empty-candidates guard BEFORE ensureSpawned() runs, so the tempting
    // prewarm ping `grade(fen, [])` silently warms nothing — it does not
    // throw, it does not error, it just does not work. This test is what
    // makes a future "simplification" of warm() into grade(fen, []) go red
    // instead of shipping a prewarm that never warms.
    const pool = createWorkerPool();
    const grades = await pool.grade(TEST_FEN, []);
    expect(createdWorkers.length).toBe(0);
    expect(grades.size).toBe(0);
  });

  it('a real grade() after warm() reuses the warmed pool', async () => {
    const pool = createWorkerPool();
    pool.warm();
    const warmedCount = createdWorkers.length;
    expect(warmedCount).toBe(computePoolSize());

    const gradePromise = pool.grade(TEST_FEN, ['e7e5']);
    driveInit(createdWorkers[0]!);
    createdWorkers[0]!.simulateMessage('info depth 10 multipv 1 score cp 20 nodes 1000 pv e7e5');
    createdWorkers[0]!.simulateMessage('bestmove e7e5');
    await gradePromise;

    // The search ran on the pool warm() already spawned — not a throwaway one.
    expect(createdWorkers.length).toBe(warmedCount);
  });

  it('stopAll() sends stop to every thinking slot and clears the pending queue', async () => {
    const pool = createWorkerPool();
    const first = pool.grade(TEST_FEN, ['e7e5']);
    const second = pool.grade(TEST_FEN_2, ['d7d5']); // dequeues before `first` (tie-break: 'd7d5' < 'e7e5')

    driveInit(createdWorkers[0]!); // the only ready slot dispatches `second` (the DISPATCHED/in-flight request)

    pool.stopAll();

    expect(createdWorkers[0]!.messages).toContain('stop');
    // The still-pending `first` request is resolved (empty) rather than left hanging.
    await expect(first).resolves.toEqual(new Map());
    // CR-01: the DISPATCHED in-flight `second` request must ALSO settle, not just queued ones.
    await expect(second).resolves.toEqual(new Map());
  });

  it('CR-02: terminate() resolves an in-flight (dispatched) grade() promise instead of hanging it', async () => {
    const pool = createWorkerPool();
    const first = pool.grade(TEST_FEN, ['e7e5']);
    driveInit(createdWorkers[0]!); // dispatches `first` -> slot.current set, state 'thinking'

    pool.terminate();

    await expect(first).resolves.toEqual(new Map());
    for (const w of createdWorkers) {
      expect(w.terminated).toBe(true);
    }
  });

  it('terminate() calls worker.terminate() on every slot', () => {
    const pool = createWorkerPool();
    void pool.grade(TEST_FEN, ['e7e5']);
    expect(createdWorkers.length).toBe(4);

    pool.terminate();

    for (const w of createdWorkers) {
      expect(w.terminated).toBe(true);
    }
  });

  it('a later grade() call re-spawns workers after terminate()', () => {
    const pool = createWorkerPool();
    void pool.grade(TEST_FEN, ['e7e5']);
    pool.terminate();
    void pool.grade(TEST_FEN, ['e7e5']);
    expect(createdWorkers.length).toBe(8); // 4 initial + 4 re-spawned
  });

  it('an AbortSignal aborting an unstarted (still-pending) request removes it from the pending queue', async () => {
    const pool = createWorkerPool();
    const controller = new AbortController();
    const first = pool.grade(TEST_FEN, ['e7e5'], controller.signal);
    const second = pool.grade(TEST_FEN_2, ['d7d5']); // dequeues before `first` (tie-break: 'd7d5' < 'e7e5')

    driveInit(createdWorkers[0]!); // the only ready slot dispatches `second`, leaving `first` pending

    controller.abort();
    await expect(first).resolves.toEqual(new Map());

    // Clean up `second` so its promise settles too.
    createdWorkers[0]!.simulateMessage('info depth 14 multipv 1 score cp 5 nodes 1000 pv d7d5');
    createdWorkers[0]!.simulateMessage('bestmove d7d5');
    await second;
  });

  it('WR-01: a pre-aborted signal resolves grade() empty immediately with zero Worker constructions', async () => {
    const pool = createWorkerPool();
    const controller = new AbortController();
    controller.abort(); // aborted BEFORE grade() is even called
    const result = await pool.grade(TEST_FEN, ['e7e5'], controller.signal);
    expect(result).toEqual(new Map());
    expect(createdWorkers.length).toBe(0);
  });

  it('WR-05: an empty candidateUcis array resolves grade() empty without dispatching a go message', async () => {
    const pool = createWorkerPool();
    const result = await pool.grade(TEST_FEN, []);
    expect(result).toEqual(new Map());
    expect(createdWorkers.length).toBe(0);
    for (const w of createdWorkers) {
      expect(w.messages.some((m) => m.startsWith('go '))).toBe(false);
    }
  });

  it('grade is structurally assignable to EngineProviders.grade (D-08 two-arg call form)', () => {
    const pool: WorkerPool = createWorkerPool();
    const providerGrade: EngineProviders['grade'] = pool.grade;
    expect(typeof providerGrade).toBe('function');
  });

  it('graceful-degradation floor: a slot construction failure still leaves a smaller live pool, not a throw', () => {
    let calls = 0;
    vi.stubGlobal(
      'Worker',
      vi.fn(function (this: unknown) {
        calls += 1;
        if (calls === 2) throw new Error('simulated construction failure');
        const w = new MockWorker();
        createdWorkers.push(w);
        return w;
      }),
    );
    const pool = createWorkerPool();
    expect(() => pool.grade(TEST_FEN, ['e7e5'])).not.toThrow();
    // 4 attempted, 1 failed -> 3 live slots.
    expect(createdWorkers.length).toBe(3);
    // WR-03: the construction failure must be Sentry-visible, not a silent catch.
    expect(Sentry.captureException).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({ tags: expect.objectContaining({ source: 'stockfish-worker-pool' }) }),
    );
  });

  it('WR-04: worker.onerror settles the in-flight request and is Sentry-captured with the stockfish-worker-pool tag', async () => {
    const pool = createWorkerPool();
    const gradePromise = pool.grade(TEST_FEN, ['e7e5']);
    const worker = createdWorkers[0]!;
    driveInit(worker); // dispatches the request -> slot.current set, state 'thinking'

    worker.simulateError();

    await expect(gradePromise).resolves.toEqual(new Map());
    expect(Sentry.captureException).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({ tags: expect.objectContaining({ source: 'stockfish-worker-pool' }) }),
    );
  });

  it('WR-04: once every slot has failed via onerror, a still-pending (never-dispatched) request drains instead of hanging', async () => {
    const pool = createWorkerPool();
    // Do NOT driveInit any worker — every slot stays not-isReady, so this
    // request sits in `pending`, never assigned to a slot's `current`.
    const gradePromise = pool.grade(TEST_FEN, ['e7e5']);
    expect(createdWorkers.length).toBeGreaterThan(0);

    // Fail every spawned slot's onerror -> no live (isReady) slot remains.
    for (const w of createdWorkers) w.simulateError();

    await expect(gradePromise).resolves.toEqual(new Map());
  });
});
