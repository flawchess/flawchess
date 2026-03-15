import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { positionBookmarksApi, timeSeriesApi } from '@/api/client';
import type { PositionBookmarkCreate, PositionBookmarkResponse, PositionBookmarkUpdate, TimeSeriesRequest, MatchSideUpdateRequest } from '@/types/position_bookmarks';

export function usePositionBookmarks() {
  return useQuery({
    queryKey: ['position-bookmarks'],
    queryFn: positionBookmarksApi.list,
  });
}

export function useCreatePositionBookmark() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PositionBookmarkCreate) => positionBookmarksApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['position-bookmarks'] }),
  });
}

export function useUpdatePositionBookmarkLabel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: PositionBookmarkUpdate }) =>
      positionBookmarksApi.updateLabel(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['position-bookmarks'] }),
  });
}

export function useDeletePositionBookmark() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => positionBookmarksApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['position-bookmarks'] }),
  });
}

type ReorderContext = { prev: unknown };

export function useReorderPositionBookmarks() {
  const qc = useQueryClient();
  return useMutation<PositionBookmarkResponse[], Error, number[], ReorderContext>({
    mutationFn: (orderedIds: number[]) =>
      positionBookmarksApi.reorder({ ids: orderedIds }),
    onMutate: async (orderedIds: number[]): Promise<ReorderContext> => {
      await qc.cancelQueries({ queryKey: ['position-bookmarks'] });
      const prev = qc.getQueryData(['position-bookmarks']);
      qc.setQueryData(['position-bookmarks'], (old: unknown) =>
        orderedIds
          .map((id: number) => (old as { id: number }[])?.find((b) => b.id === id))
          .filter(Boolean)
      );
      return { prev };
    },
    onError: (_: Error, __: number[], ctx: ReorderContext | undefined) => {
      qc.setQueryData(['position-bookmarks'], ctx?.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['position-bookmarks'] }),
  });
}

export function useUpdateMatchSide() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: MatchSideUpdateRequest }) =>
      positionBookmarksApi.updateMatchSide(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['position-bookmarks'] });
    },
  });
}

export function useTimeSeries(req: TimeSeriesRequest | null) {
  return useQuery({
    queryKey: ['timeSeries', req],
    queryFn: () => timeSeriesApi.fetch(req!),
    enabled: !!req && req.bookmarks.length > 0,
  });
}

export function usePositionSuggestions() {
  return useQuery({
    queryKey: ['position-bookmark-suggestions'],
    queryFn: positionBookmarksApi.getSuggestions,
    staleTime: 60_000,
    enabled: false,  // only fetch when user clicks "Suggest bookmarks"
  });
}
