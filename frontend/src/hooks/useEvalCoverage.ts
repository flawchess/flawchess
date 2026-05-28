import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { EvalCoverageResponse } from '@/types/api';

const EVAL_COVERAGE_POLL_INTERVAL_MS = 3_000;
const EVAL_COVERAGE_STALE_TIME_MS = 3_000;

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

  // NOTE: Auto-reload on eval completion was removed in Phase 96 Plan 03
  // (Constraint 4 / SC-5). Reactive reveal via useReadiness tier2 flag replaces
  // the forced full-page reload. EvalCoverageHeader (driven by this hook) still
  // shows the global progress bar while analysis is pending; per-row reveal on
  // Openings cards is handled by EvalCpuPlaceholder gated on useReadiness.tier2.

  return {
    pendingCount: data?.pending_count ?? 0,
    totalCount: data?.total_count ?? 0,
    pct: data?.pct_complete ?? 100,
    isPending,
    isLoading: query.isLoading,
  };
}
