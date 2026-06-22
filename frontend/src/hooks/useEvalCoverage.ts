import { useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { EvalCoverageResponse } from '@/types/api';

// Status poll (cheap eval-coverage count query). 1s for swift card flip / pill
// clear on the on-demand "Analyze" path — this gates how fast GamesTab notices
// analyzed_count rising and forces a games-list refetch.
const EVAL_COVERAGE_POLL_INTERVAL_MS = 1_000;
const EVAL_COVERAGE_STALE_TIME_MS = 1_000;

// Games-list refetch interval (heavier paginated query). Kept slower than the
// status poll: completion already triggers an immediate list invalidation in
// GamesTab, so this only paces the background backlog-drain refresh.
export const LIBRARY_GAMES_POLL_INTERVAL_MS = 3_000;

// When tracking full-analysis progress (trackFullAnalysis), stop polling after this
// many consecutive *fetches* with no newly-analyzed game. Without a backstop, a
// permanently-stuck game (e.g. an engine outage that re-fails the same game, leaving
// analyzed_count < total_count forever) would poll indefinitely on a focused tab.
// At the 1s poll interval, 30 keeps ~30s of wall-clock tolerance for backlog
// drains that legitimately pause between games before backing off.
const MAX_STALL_POLLS = 30;

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
 * - Always poll while entry-ply evals are pending (pct_complete < 100).
 * - total_count === 0 (new user / pre-import): keep polling so the header appears
 *   once an in-flight import starts landing rows (backend short-circuits pct=100).
 * - Readiness consumers (trackFullAnalysis = false): stop once entry-ply evals done.
 * - Badge consumers (trackFullAnalysis = true): additionally keep polling while
 *   full analysis is incomplete (analyzed_count < total_count), backing off once
 *   progress stalls so stuck games don't poll forever.
 *
 * All consumers on the same page share one in-flight request via the shared
 * queryKey ['imports', 'eval-coverage'] — TanStack Query deduplicates them.
 *
 * NOTE: in_flight_count removed in Phase 119-03 (tier-3 derived picks have no
 * eval_jobs rows, so the count was structurally blind to the dominant backlog
 * drain). The trackFullAnalysis branch (analyzed_count < total_count) is now
 * the sole driver of badge-surface polling.
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

      // Entry-ply evals still running → always poll. Reset the background-stall tracker.
      if (data.pct_complete < 100) {
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
  };
}
