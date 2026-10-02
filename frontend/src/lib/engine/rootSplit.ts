/**
 * rootSplit — pure round-robin partition/merge helpers for the root grade
 * split (Phase 226 D-18/L-2/L-3). Shared by the app worker pool
 * (`workerPoolDispatch.ts`, landing in Plan 226-11) and every harness pool
 * (`scripts/lib/stockfish-pool.mjs`, `createGradePool`, the depth-ab
 * closures) so the fan-out logic lives in exactly one place below the
 * `EngineProviders.grade`/`gradeRoot` boundary — never duplicated per
 * caller (L-3).
 *
 * Round 1 of every search is exactly the root expansion (`mctsSearch.ts`'s
 * `selectPath` root-pending guard: the root is the only node reachable
 * before any child is discovered), so `gradeRoot` is called AT MOST ONCE
 * per search — splitting that one call is the whole point. On a
 * `concurrency`-4 pool the unsplit root grade serializes through ONE
 * worker while the other three sit idle for the entirety of round 1
 * (SEED-171 item 1, the underfill this phase targets).
 *
 * `partitionCandidates` assigns candidate `i` to shard `i % k`
 * (round-robin), never a contiguous chunk split. Candidates arrive in Maia
 * policy-mass order (`truncateAndRenormalize`'s output — highest
 * probability first), so a contiguous split would put every high-prior
 * move in shard 0 and every low-prior move in the last shard, making shard
 * 0's Stockfish process the long pole every time. Round-robin spreads the
 * high-prior moves evenly across shards instead.
 *
 * `mergeShardGrades` NEVER fabricates a grade for a candidate missing from
 * every shard (L-2): a partial shard result (e.g. one shard's engine died
 * mid-grade) surfaces as a partial merged Map — `applyExpansion`'s existing
 * `NEUTRAL_EXPECTED_SCORE` fallback for an ungraded candidate is unchanged.
 * A candidate present in more than one shard (never expected —
 * `partitionCandidates` assigns each candidate to exactly one shard) takes
 * the FIRST shard's grade in iteration order, never a later one.
 */

import type { MoveGrade } from './types';
import { DESKTOP_POOL_MAX } from './workerPoolState';

/**
 * The fan-out never exceeds the largest worker pool a caller can build
 * (D-18) — mirrors the desktop pool's own ceiling so a caller with more
 * free engines than `DESKTOP_POOL_MAX` (never happens today, but this is
 * the shared cap every caller clamps against) still gets a bounded shard
 * count.
 */
export const ROOT_SPLIT_MAX_SHARDS = DESKTOP_POOL_MAX;

/**
 * Splits `candidateUcis` into round-robin shards (candidate `i` -> shard
 * `i % k`). `shardCount` is clamped to `[1, candidateUcis.length]`:
 *   - `shardCount` above `candidateUcis.length` clamps down to
 *     `candidateUcis.length` (n singleton shards — never more shards than
 *     candidates to fill).
 *   - `shardCount` at or below 0 clamps up to 1 (one shard holding
 *     everything, degrading to the pre-split behavior).
 *   - An empty `candidateUcis` (`length === 0`) always returns exactly one
 *     empty shard, regardless of `shardCount` — `Math.min(shardCount, 0)`
 *     is never positive, so the floor of 1 always wins.
 */
export function partitionCandidates(candidateUcis: readonly string[], shardCount: number): string[][] {
  const k = Math.max(1, Math.min(shardCount, candidateUcis.length));
  const shards: string[][] = Array.from({ length: k }, () => []);
  candidateUcis.forEach((uci, i) => {
    // Safe: `i % k` is always in `[0, k)` and `shards.length === k` by
    // construction above (`noUncheckedIndexedAccess` narrowing exemption —
    // index is provably in bounds, per frontend/CLAUDE.md).
    shards[i % k]!.push(uci);
  });
  return shards;
}

/**
 * Merges completed per-shard grade Maps in ORIGINAL `candidateUcis` order
 * (L-2/L-3): for each candidate, takes the first shard (in iteration order)
 * that has it. A candidate present in NO shard is simply absent from the
 * result — never fabricated as a neutral/default grade (L-2). Callers must
 * pass only shards that resolved; a failed/incomplete shard should be
 * surfaced as a throw by the caller (mirrors the harness `withEngine`
 * failure semantics: "the request errors", never a silently partial merge
 * masquerading as complete data).
 */
export function mergeShardGrades(
  candidateUcis: readonly string[],
  shards: readonly Map<string, MoveGrade>[],
): Map<string, MoveGrade> {
  const merged = new Map<string, MoveGrade>();
  for (const uci of candidateUcis) {
    for (const shard of shards) {
      const grade = shard.get(uci);
      if (grade) {
        merged.set(uci, grade);
        break;
      }
    }
  }
  return merged;
}
