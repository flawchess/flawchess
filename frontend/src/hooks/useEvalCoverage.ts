import { useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { EvalCoverageResponse } from '@/types/api';

export const EVAL_COVERAGE_POLL_INTERVAL_MS = 3_000;
const EVAL_COVERAGE_STALE_TIME_MS = 3_000;

// When tracking full-analysis progress (trackFullAnalysis), stop polling after this
// many consecutive *fetches* with no newly-analyzed game. Without a backstop, a
// permanently-stuck game (e.g. an engine outage that re-fails the same game, leaving
// analyzed_count < total_count forever) would poll indefinitely on a focused tab.
const MAX_STALL_POLLS = 5;

interface UseEvalCoverageOptions {
  /**
   * Keep polling while full-game analysis is incomplete (analyzed_count <
   * total_count), so the "N of M analyzed" coverage badge ticks up live as the
   * background tier-3 drain works through the backlog.
   *
   * Off by default: readiness-gate consumers (Endgames / Openings / Import) only
   * care about entry-ply completion (pct_complete) and must not keep polling for
   * the whole full-analysis backlog. Only the badge surfaces (Games / Flaws tabs)
   * opt in. Polling backs off once progress stalls (MAX_STALL_POLLS) and pauses
   * while the tab is hidden (refetchIntervalInBackground defaults to false).
   */
  trackFullAnalysis?: boolean;
}

/** Poll GET /imports/eval-coverage while Stockfish analysis is pending.
 *
 * Defaults to pct=100 / isPending=false before the first fetch resolves, so the
 * header bar and per-metric caveats do not flash on initial page load.
 *
 * Poll-stop conditions:
 * - Always poll while entry-ply evals are pending (pct_complete < 100) or an
 *   explicit single-game (tier-1) job is in flight (in_flight_count > 0).
 * - total_count === 0 (new user / pre-import): keep polling so the header appears
 *   once an in-flight import starts landing rows (backend short-circuits pct=100).
 * - Readiness consumers (trackFullAnalysis = false): stop once entry-ply evals are
 *   done and nothing is in flight.
 * - Badge consumers (trackFullAnalysis = true): additionally keep polling while
 *   full analysis is incomplete (analyzed_count < total_count), backing off once
 *   progress stalls so stuck games don't poll forever.
 *
 * All consumers on the same page share one in-flight request via the shared
 * queryKey ['imports', 'eval-coverage'] — TanStack Query deduplicates them.
 *
 * NOTE: Auto-reload on eval completion was removed in Phase 96 Plan 03
 * (Constraint 4 / SC-5). Reactive reveal via useReadiness tier2 flag replaces the
 * forced full-page reload.
 */
export function useEvalCoverage(options?: UseEvalCoverageOptions) {
  const trackFullAnalysis = options?.trackFullAnalysis ?? false;

  // Stall tracker for the trackFullAnalysis poll loop. dataUpdatedAt changes once
  // per successful fetch, so we advance the stall counter only on a genuine new
  // fetch — never on incidental re-renders that also re-run refetchInterval.
  const stallRef = useRef({ lastAnalyzed: -1, stalls: 0, lastUpdatedAt: 0 });

  const query = useQuery<EvalCoverageResponse>({
    queryKey: ['imports', 'eval-coverage'],
    queryFn: async () => {
      const response = await apiClient.get<EvalCoverageResponse>('/imports/eval-coverage');
      return response.data;
    },
    staleTime: EVAL_COVERAGE_STALE_TIME_MS,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Pre-data / new user (no games yet): keep polling.
      if (!data || data.total_count === 0) return EVAL_COVERAGE_POLL_INTERVAL_MS;

      // Entry-ply evals still running, or an explicit single-game (tier-1) job in
      // flight → always poll. Reset the background-stall tracker.
      const inFlight = data.in_flight_count ?? 0;
      if (data.pct_complete < 100 || inFlight > 0) {
        stallRef.current = { lastAnalyzed: data.analyzed_count, stalls: 0, lastUpdatedAt: 0 };
        return EVAL_COVERAGE_POLL_INTERVAL_MS;
      }

      // Readiness consumers stop here (original behavior).
      if (!trackFullAnalysis) return false;

      // Full analysis complete → nothing left to watch.
      if (data.analyzed_count >= data.total_count) return false;

      // Background full-analysis (tier-3) in progress: poll while it makes
      // progress, back off once it stalls. Advance the counter only on a new fetch.
      const s = stallRef.current;
      if (query.state.dataUpdatedAt !== s.lastUpdatedAt) {
        s.stalls = data.analyzed_count > s.lastAnalyzed ? 0 : s.stalls + 1;
        s.lastAnalyzed = data.analyzed_count;
        s.lastUpdatedAt = query.state.dataUpdatedAt;
      }
      if (s.stalls >= MAX_STALL_POLLS) return false;
      return EVAL_COVERAGE_POLL_INTERVAL_MS;
    },
  });

  const data = query.data;
  const isPending = (data?.pct_complete ?? 100) < 100;

  return {
    pendingCount: data?.pending_count ?? 0,
    totalCount: data?.total_count ?? 0,
    pct: data?.pct_complete ?? 100,
    isPending,
    isLoading: query.isLoading,
    isError: query.isError,
    analyzedCount: data?.analyzed_count ?? 0,
    inFlightCount: data?.in_flight_count ?? 0,
  };
}
