/**
 * liveEngineWorkers — counts the Stockfish Workers alive on this page, for
 * Sentry triage of engine memory failures (SEED-195).
 *
 * Every Stockfish Worker (pool slots, the single analysis engine, both
 * grading hooks) holds its own wasm Memory. The Mac Safari Maia OOM
 * (FLAWCHESS-CP/B2: `[wasm] RangeError: Out of memory` at session create) is
 * suspected to be a per-page wasm reservation budget that the Stockfish
 * workers have already used up by the time Maia spawns. This count is
 * attached to Maia failure captures so the next events can confirm or rule
 * that out.
 *
 * "Alive" means constructed through `createStockfishWorker()` and not yet
 * `terminate()`d. A worker that dies on its own without its owner calling
 * `terminate()` keeps counting, which is acceptable for telemetry.
 */

/** Which owner constructed a Stockfish Worker. */
export type StockfishWorkerRole = 'pool' | 'single' | 'grading' | 'train-grading';

const liveCounts: Record<StockfishWorkerRole, number> = {
  pool: 0,
  single: 0,
  grading: 0,
  'train-grading': 0,
};

/**
 * Counts `worker` as alive under `role` and wraps its `terminate()` so the
 * count drops exactly once, however many times the owner terminates it.
 */
export function trackStockfishWorker(worker: Worker, role: StockfishWorkerRole): void {
  liveCounts[role] += 1;
  const terminate = worker.terminate.bind(worker);
  let alive = true;
  worker.terminate = (): void => {
    if (alive) {
      alive = false;
      liveCounts[role] -= 1;
    }
    terminate();
  };
}

/** Snapshot for Sentry context: per-role live counts plus the total. */
export function readLiveEngineWorkers(): Record<string, number> {
  const { pool, single, grading } = liveCounts;
  const trainGrading = liveCounts['train-grading'];
  return {
    stockfishPool: pool,
    stockfishSingle: single,
    stockfishGrading: grading,
    stockfishTrainGrading: trainGrading,
    stockfishTotal: pool + single + grading + trainGrading,
  };
}

/** Test-only: zeroes every count. */
export function resetLiveEngineWorkersForTests(): void {
  for (const role of Object.keys(liveCounts) as StockfishWorkerRole[]) liveCounts[role] = 0;
}
