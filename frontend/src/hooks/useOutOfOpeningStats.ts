import { useQuery } from '@tanstack/react-query';
import { openingsApi } from '@/api/client';

// Percentile rows only change on new imports, so a 5 minute stale time with no
// refetch-on-focus avoids redundant DB load (same as the Endgames ranked payload).
const OUT_OF_OPENING_STALE_TIME_MS = 5 * 60 * 1000;

// The out-of-the-opening ranking behind the Openings Stats tab. No filters
// argument: the endpoint ignores them by design. The key is invalidated on import
// completion and delete-all (App.tsx, Import.tsx).
export function useOutOfOpeningStats(options: { enabled?: boolean } = {}) {
  const { enabled = true } = options;
  return useQuery({
    queryKey: ['outOfOpeningStats'],
    queryFn: () => openingsApi.getOutOfOpeningStats(),
    staleTime: OUT_OF_OPENING_STALE_TIME_MS,
    refetchOnWindowFocus: false,
    // Gate on Tier-2 readiness: a fetch while the page is locked (Analyzing...) would
    // cache a pre-Stage-B payload that the staleTime then keeps serving after unlock.
    enabled,
  });
}
