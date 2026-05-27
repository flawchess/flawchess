import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { EvalCoverageResponse } from '@/types/api';

const EVAL_COVERAGE_POLL_INTERVAL_MS = 3_000;
const EVAL_COVERAGE_STALE_TIME_MS = 3_000;

// Module-level guard so the reload only fires once across all hook consumers
// in a single page lifetime. Reset implicitly when the page reloads.
let evalCompletionReloadFired = false;

/** Poll GET /imports/eval-coverage every 10s while Stockfish analysis is pending.
 *
 * Defaults to pct=100 / isPending=false before the first fetch resolves, so
 * the header bar and per-metric caveats do not flash on initial page load.
 *
 * Polling stops only when pct_complete=100 AND total_count>0 — i.e. the user
 * has games and all of them are evaluated. A 0-game response (new user, or
 * landing on /import before any games are imported) keeps polling, otherwise
 * the header would never appear once an in-flight import starts landing rows
 * (the backend short-circuits to pct=100 when total=0).
 *
 * All consumers on the same page share one in-flight request via the shared
 * queryKey ['imports', 'eval-coverage'] — TanStack Query deduplicates them.
 */
export function useEvalCoverage() {
  const query = useQuery<EvalCoverageResponse>({
    queryKey: ['imports', 'eval-coverage'],
    queryFn: async () => {
      const response = await apiClient.get<EvalCoverageResponse>('/imports/eval-coverage');
      return response.data;
    },
    staleTime: EVAL_COVERAGE_STALE_TIME_MS,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && data.pct_complete === 100 && data.total_count > 0) return false;
      return EVAL_COVERAGE_POLL_INTERVAL_MS;
    },
  });

  const data = query.data;
  const isPending = (data?.pct_complete ?? 100) < 100;

  // Reload the page once Stockfish finishes so eval-dependent stats
  // (Conversion/Parity/Recovery, etc.) refresh without manual reload.
  // Only triggers on a true pending→complete transition observed in this
  // session — never on initial load when eval is already at 100%.
  const wasPendingRef = useRef(false);
  useEffect(() => {
    if (isPending) {
      wasPendingRef.current = true;
      return;
    }
    if (
      wasPendingRef.current &&
      !evalCompletionReloadFired &&
      data &&
      data.total_count > 0 &&
      data.pct_complete === 100
    ) {
      evalCompletionReloadFired = true;
      window.location.reload();
    }
  }, [isPending, data]);

  return {
    pendingCount: data?.pending_count ?? 0,
    totalCount: data?.total_count ?? 0,
    pct: data?.pct_complete ?? 100,
    isPending,
    isLoading: query.isLoading,
  };
}
