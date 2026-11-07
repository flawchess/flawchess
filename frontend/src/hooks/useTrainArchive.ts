import { useQuery } from '@tanstack/react-query';
import { trainApi } from '@/api/client';
import type { ArchiveList, TrainArchiveResponse } from '@/types/train';

/** Cards per Archive page. The backend allows more; 20 matches the Library lists. */
export const ARCHIVE_PAGE_SIZE = 20;

/**
 * GET /train/archive, one page of the mastered or parked puzzles.
 *
 * `refetchOnMount: 'always'`: solving a puzzle changes list membership and
 * nothing else invalidates this key, so every visit to the tab reads fresh.
 * That also makes a return from Analysis (browser Back) show current data.
 *
 * `placeholderData` keeps the previous page only while the LIST is unchanged.
 * Plain `keepPreviousData` would show the other list's cards under the new
 * toggle selection while the request is in flight, and each card's status line
 * ("Mastered ..." / "Parked ...") would then name the wrong list. Paging within
 * a list keeps the old cards (no flicker); switching lists shows the skeleton.
 *
 * No Sentry capture here: the global QueryCache.onError already reports failed
 * queries (same as `useTrainLeaderboard`).
 */
export function useTrainArchive(list: ArchiveList, page: number) {
  return useQuery<TrainArchiveResponse>({
    queryKey: ['train', 'archive', list, page],
    queryFn: () =>
      trainApi.getArchive({
        list,
        limit: ARCHIVE_PAGE_SIZE,
        offset: (page - 1) * ARCHIVE_PAGE_SIZE,
      }),
    refetchOnMount: 'always',
    placeholderData: (previous, previousQuery) =>
      previousQuery?.queryKey[2] === list ? previous : undefined,
  });
}
