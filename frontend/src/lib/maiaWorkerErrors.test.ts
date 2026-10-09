/**
 * maiaWorkerErrors.ts unit tests (quick 260729-sod, FIX 2).
 *
 * Load-bearing case: the real FLAWCHESS-92 prod string matches BOTH the OOM
 * and the load patterns — classification order must put OOM first, since
 * memory exhaustion is the true root cause (see FINDINGS.md §1).
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import * as Sentry from '@sentry/react';
import {
  classifyMaiaWorkerError,
  captureMaiaWorkerError,
  MaiaWorkerError,
  isReportedMaiaWorkerError,
} from './maiaWorkerErrors';
import { resetLiveEngineWorkersForTests, trackStockfishWorker } from './engine/liveEngineWorkers';

vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

afterEach(() => {
  vi.clearAllMocks();
  resetLiveEngineWorkersForTests();
});

describe('classifyMaiaWorkerError', () => {
  it('classifies the real FLAWCHESS-92 OOM string as oom, not load', () => {
    const raw = 'no available backend found. ERR: [wasm] RangeError: Out of memory';
    expect(classifyMaiaWorkerError(raw)).toBe('oom');
  });

  it('classifies a bare "Load failed" as load', () => {
    expect(classifyMaiaWorkerError('Load failed')).toBe('load');
  });

  it('classifies a module-script import failure as load', () => {
    expect(classifyMaiaWorkerError('TypeError: Importing a module script failed.')).toBe('load');
  });

  it('classifies an arbitrary ONNX runtime message as inference', () => {
    expect(classifyMaiaWorkerError('Non-zero status code returned while running Clip node')).toBe('inference');
  });

  it('classifies a memory-access-out-of-bounds message as oom', () => {
    expect(classifyMaiaWorkerError('memory access out of bounds')).toBe('oom');
  });

  it('classifies the real FLAWCHESS-9D Android session-create allocation failure as oom', () => {
    const raw = "Can't create a session. failed to allocate a buffer of size 45683686.";
    expect(classifyMaiaWorkerError(raw)).toBe('oom');
  });
});

describe('captureMaiaWorkerError', () => {
  it('puts the raw text in context, not in the error message, and tags maia_failure', () => {
    const raw = 'no available backend found. ERR: [wasm] RangeError: Out of memory';
    captureMaiaWorkerError(raw, { source: 'maia-queue-worker', backend: null });

    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
    const [err, opts] = vi.mocked(Sentry.captureException).mock.calls[0]!;
    expect((err as Error).message).not.toContain(raw);
    expect(opts).toEqual(
      expect.objectContaining({
        tags: expect.objectContaining({
          source: 'maia-queue-worker',
          backend: 'unknown',
          maia_failure: 'oom',
        }),
        contexts: expect.objectContaining({ maia: { rawMessage: raw } }),
      }),
    );
  });

  it('does not vary the error message with the worker text (stable grouping)', () => {
    captureMaiaWorkerError('Load failed', { source: 'maia-worker', backend: 'webgpu' });
    captureMaiaWorkerError('Load failed: network hiccup', { source: 'maia-worker', backend: 'webgpu' });

    const calls = vi.mocked(Sentry.captureException).mock.calls;
    const [err1] = calls[0]!;
    const [err2] = calls[1]!;
    expect((err1 as Error).message).toBe((err2 as Error).message);
  });

  it('attaches engine_device context so the canonical capture keeps the triage data the gate used to add', () => {
    captureMaiaWorkerError('Load failed', { source: 'maia-worker', backend: null });

    const [, opts] = vi.mocked(Sentry.captureException).mock.calls[0]!;
    expect(opts).toEqual(
      expect.objectContaining({
        contexts: expect.objectContaining({ engine_device: expect.any(Object) }),
      }),
    );
  });

  it('SEED-195: tags the spawn path and attaches live Stockfish worker counts', () => {
    const pooled = { terminate: vi.fn() } as unknown as Worker;
    trackStockfishWorker(pooled, 'pool');
    trackStockfishWorker({ terminate: vi.fn() } as unknown as Worker, 'grading');

    captureMaiaWorkerError('RangeError: Out of memory', {
      source: 'maia-worker',
      backend: null,
      spawnPath: 'webgpu-failed-wasm',
    });

    const [, opts] = vi.mocked(Sentry.captureException).mock.calls[0]!;
    expect(opts).toEqual(
      expect.objectContaining({
        tags: expect.objectContaining({ maia_spawn_path: 'webgpu-failed-wasm' }),
        contexts: expect.objectContaining({
          engine_workers: expect.objectContaining({ stockfishPool: 1, stockfishGrading: 1, stockfishTotal: 2 }),
        }),
      }),
    );
  });

  it('SEED-195: tags maia_spawn_path as unknown when the caller has no spawn path', () => {
    captureMaiaWorkerError('Load failed', { source: 'maia-queue-worker', backend: null });

    const [, opts] = vi.mocked(Sentry.captureException).mock.calls[0]!;
    expect(opts).toEqual(
      expect.objectContaining({ tags: expect.objectContaining({ maia_spawn_path: 'unknown' }) }),
    );
  });

  it('returns a MaiaWorkerError carrying the raw message and kind, recognised by isReportedMaiaWorkerError', () => {
    const raw = "Can't create a session. failed to allocate a buffer of size 45683686.";
    const err = captureMaiaWorkerError(raw, { source: 'maia-worker', backend: 'wasm' });

    expect(err).toBeInstanceOf(MaiaWorkerError);
    expect(err.kind).toBe('oom');
    // Downstream `String(reason)` contract: the raw text is still the message.
    expect(err.message).toBe(raw);
    expect(isReportedMaiaWorkerError(err)).toBe(true);
    expect(isReportedMaiaWorkerError(new Error(raw))).toBe(false);
  });
});
