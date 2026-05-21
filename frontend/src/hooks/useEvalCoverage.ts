import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { EvalCoverageResponse } from '@/types/api';

const EVAL_COVERAGE_POLL_INTERVAL_MS = 10_000;
const EVAL_COVERAGE_STALE_TIME_MS = 10_000;

/** Poll GET /imports/eval-coverage every 10s while Stockfish analysis is pending.
 *
 * Defaults to pct=100 / isPending=false before the first fetch resolves, so
 * the header bar and per-metric caveats do not flash on initial page load.
 * Polling stops automatically when pct_complete reaches 100.
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
    refetchInterval: (query) =>
      query.state.data?.pct_complete === 100 ? false : EVAL_COVERAGE_POLL_INTERVAL_MS,
  });

  const data = query.data;
  return {
    pendingCount: data?.pending_count ?? 0,
    totalCount: data?.total_count ?? 0,
    pct: data?.pct_complete ?? 100,
    isPending: (data?.pct_complete ?? 100) < 100,
    isLoading: query.isLoading,
  };
}
