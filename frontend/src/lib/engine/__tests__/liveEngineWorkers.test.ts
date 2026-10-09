/**
 * liveEngineWorkers.ts unit tests (SEED-195): the live Stockfish worker count
 * attached to Maia failure captures.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  readLiveEngineWorkers,
  resetLiveEngineWorkersForTests,
  trackStockfishWorker,
} from '../liveEngineWorkers';

function fakeWorker(): { worker: Worker; terminate: ReturnType<typeof vi.fn> } {
  const terminate = vi.fn();
  return { worker: { terminate } as unknown as Worker, terminate };
}

afterEach(() => {
  resetLiveEngineWorkersForTests();
});

describe('liveEngineWorkers', () => {
  it('starts at zero', () => {
    expect(readLiveEngineWorkers()).toEqual({
      stockfishPool: 0,
      stockfishSingle: 0,
      stockfishGrading: 0,
      stockfishTrainGrading: 0,
      stockfishTotal: 0,
    });
  });

  it('counts tracked workers per role and in the total', () => {
    trackStockfishWorker(fakeWorker().worker, 'pool');
    trackStockfishWorker(fakeWorker().worker, 'pool');
    trackStockfishWorker(fakeWorker().worker, 'single');
    trackStockfishWorker(fakeWorker().worker, 'train-grading');

    expect(readLiveEngineWorkers()).toEqual(
      expect.objectContaining({ stockfishPool: 2, stockfishSingle: 1, stockfishTrainGrading: 1, stockfishTotal: 4 }),
    );
  });

  it('decrements on terminate and still terminates the real worker', () => {
    const { worker, terminate } = fakeWorker();
    trackStockfishWorker(worker, 'grading');

    worker.terminate();

    expect(terminate).toHaveBeenCalledTimes(1);
    expect(readLiveEngineWorkers().stockfishGrading).toBe(0);
  });

  it('decrements only once when a worker is terminated twice', () => {
    const { worker, terminate } = fakeWorker();
    trackStockfishWorker(worker, 'pool');
    trackStockfishWorker(fakeWorker().worker, 'pool');

    worker.terminate();
    worker.terminate();

    expect(terminate).toHaveBeenCalledTimes(2);
    expect(readLiveEngineWorkers().stockfishPool).toBe(1);
  });
});
