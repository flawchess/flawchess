import { useMemo } from 'react';
import { useBookmarks, useReorderBookmarks, useTimeSeries } from '@/hooks/useBookmarks';
import { BookmarkList } from '@/components/bookmarks/BookmarkList';
import { WinRateChart } from '@/components/bookmarks/WinRateChart';

export function BookmarksPage() {
  const { data: bookmarks = [], isLoading } = useBookmarks();
  const reorder = useReorderBookmarks();

  const handleReorder = (orderedIds: number[]) => {
    reorder.mutate(orderedIds);
  };

  // Build time-series request from current bookmarks
  const timeSeriesRequest = bookmarks.length > 0
    ? {
        bookmarks: bookmarks.map((b) => ({
          bookmark_id: b.id,
          target_hash: b.target_hash,
          match_side: b.match_side,
          color: b.color,
        })),
      }
    : null;

  const { data: tsData } = useTimeSeries(timeSeriesRequest);

  // Derive WDL stats per bookmark by aggregating all months from time-series
  const wdlStatsMap = useMemo(() => {
    const map: Record<number, { wins: number; draws: number; losses: number; total: number; win_pct: number; draw_pct: number; loss_pct: number }> = {};
    for (const s of tsData?.series ?? []) {
      let wins = 0, draws = 0, losses = 0;
      for (const p of s.data) {
        wins += p.wins;
        draws += p.draws;
        losses += p.losses;
      }
      const total = wins + draws + losses;
      map[s.bookmark_id] = {
        wins,
        draws,
        losses,
        total,
        win_pct: total > 0 ? Math.round((wins / total) * 1000) / 10 : 0,
        draw_pct: total > 0 ? Math.round((draws / total) * 1000) / 10 : 0,
        loss_pct: total > 0 ? Math.round((losses / total) * 1000) / 10 : 0,
      };
    }
    return map;
  }, [tsData]);

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
      <BookmarkList bookmarks={bookmarks} onReorder={handleReorder} wdlStatsMap={wdlStatsMap} />
      {tsData && (
        <div>
          <h2 className="text-lg font-medium mb-3">Win Rate Over Time</h2>
          <WinRateChart bookmarks={bookmarks} series={tsData.series} />
        </div>
      )}
    </div>
  );
}
