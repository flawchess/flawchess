import { useBookmarks, useReorderBookmarks } from '@/hooks/useBookmarks';
import { BookmarkList } from '@/components/bookmarks/BookmarkList';

export function BookmarksPage() {
  const { data: bookmarks = [], isLoading } = useBookmarks();
  const reorder = useReorderBookmarks();

  const handleReorder = (orderedIds: number[]) => {
    reorder.mutate(orderedIds);
  };

  if (isLoading) {
    return <div className="p-8 text-muted-foreground">Loading bookmarks...</div>;
  }

  if (bookmarks.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        <p className="text-lg">No bookmarks yet.</p>
        <p className="mt-2 text-sm">
          Analyze a position on the{' '}
          <a href="/" className="underline">
            Analysis
          </a>{' '}
          page and click ★ Bookmark to save it.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6">
      <h1 className="text-2xl font-semibold">Bookmarks</h1>
      <BookmarkList bookmarks={bookmarks} onReorder={handleReorder} />
      {/* WinRateChart added in plan 05 */}
    </div>
  );
}
