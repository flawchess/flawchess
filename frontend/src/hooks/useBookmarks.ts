import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { bookmarksApi, timeSeriesApi } from '@/api/client';
import type { BookmarkCreate, BookmarkResponse, BookmarkUpdate, TimeSeriesRequest } from '@/types/bookmarks';

export function useBookmarks() {
  return useQuery({
    queryKey: ['bookmarks'],
    queryFn: bookmarksApi.list,
  });
}

export function useCreateBookmark() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BookmarkCreate) => bookmarksApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bookmarks'] }),
  });
}

export function useUpdateBookmarkLabel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: BookmarkUpdate }) =>
      bookmarksApi.updateLabel(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bookmarks'] }),
  });
}

export function useDeleteBookmark() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => bookmarksApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bookmarks'] }),
  });
}

type ReorderContext = { prev: unknown };

export function useReorderBookmarks() {
  const qc = useQueryClient();
  return useMutation<BookmarkResponse[], Error, number[], ReorderContext>({
    mutationFn: (orderedIds: number[]) =>
      bookmarksApi.reorder({ ids: orderedIds }),
    onMutate: async (orderedIds: number[]): Promise<ReorderContext> => {
      await qc.cancelQueries({ queryKey: ['bookmarks'] });
      const prev = qc.getQueryData(['bookmarks']);
      qc.setQueryData(['bookmarks'], (old: unknown) =>
        orderedIds
          .map((id: number) => (old as { id: number }[])?.find((b) => b.id === id))
          .filter(Boolean)
      );
      return { prev };
    },
    onError: (_: Error, __: number[], ctx: ReorderContext | undefined) => {
      qc.setQueryData(['bookmarks'], ctx?.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['bookmarks'] }),
  });
}

export function useTimeSeries(req: TimeSeriesRequest | null) {
  return useQuery({
    queryKey: ['timeSeries', req],
    queryFn: () => timeSeriesApi.fetch(req!),
    enabled: !!req && req.bookmarks.length > 0,
  });
}
