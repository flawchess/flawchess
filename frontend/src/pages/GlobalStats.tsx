import { useState } from 'react';
import { InfoPopover } from '@/components/ui/info-popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useGlobalStats, useRatingHistory } from '@/hooks/useStats';
import { GlobalStatsCharts } from '@/components/stats/GlobalStatsCharts';
import { RatingChart } from '@/components/stats/RatingChart';
import { cn } from '@/lib/utils';
import type { Platform, Recency } from '@/types/api';

export function GlobalStatsPage() {
  const [recency, setRecency] = useState<Recency | null>(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[] | null>(null);

  const { data: ratingData, isLoading: ratingLoading } = useRatingHistory(recency, selectedPlatforms);
  const { data: globalStats, isLoading: statsLoading } = useGlobalStats(recency, selectedPlatforms);

  const isLoading = ratingLoading || statsLoading;

  return (
    <div data-testid="global-stats-page" className="mx-auto max-w-4xl space-y-6 px-6 py-6">
      {/* Sticky filters */}
      <div className="sticky top-0 z-10 bg-background pb-2 -mx-6 px-6 pt-1">
        <div className="flex flex-wrap items-end gap-4">
        {/* Recency filter */}
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Recency</p>
          <Select
            value={recency ?? 'all'}
            onValueChange={(v) => setRecency(v === 'all' ? null : (v as Recency))}
          >
            <SelectTrigger size="sm" data-testid="filter-recency" className="min-h-11 sm:min-h-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All time</SelectItem>
              <SelectItem value="week">Past week</SelectItem>
              <SelectItem value="month">Past month</SelectItem>
              <SelectItem value="3months">3 months</SelectItem>
              <SelectItem value="6months">6 months</SelectItem>
              <SelectItem value="year">1 year</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Platform filter */}
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Platform</p>
          <div className="flex gap-1">
            {(['chess.com', 'lichess'] as Platform[]).map((p) => {
              const isActive = selectedPlatforms === null || selectedPlatforms.includes(p);
              return (
                <button
                  key={p}
                  onClick={() => {
                    setSelectedPlatforms((prev) => {
                      if (prev === null) return [p === 'chess.com' ? 'lichess' : 'chess.com'] as Platform[];
                      if (prev.length === 1 && prev[0] === p) return null; // re-select = show all
                      if (prev.includes(p)) return prev.filter((x) => x !== p) as Platform[];
                      return null; // both selected = all
                    });
                  }}
                  data-testid={`filter-platform-${p === 'chess.com' ? 'chess-com' : p}`}
                  aria-label={`${p} platform`}
                  aria-pressed={isActive}
                  className={cn(
                    'rounded border px-3 h-11 sm:h-7 sm:px-2 text-xs transition-colors',
                    isActive
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border bg-transparent text-muted-foreground hover:border-foreground hover:text-foreground',
                  )}
                >
                  {p === 'chess.com' ? 'Chess.com' : 'Lichess'}
                </button>
              );
            })}
          </div>
        </div>
        </div>
      </div>

      {isLoading ? (
        <div className="text-muted-foreground">Loading...</div>
      ) : (
        <>
          {/* Chess.com Rating section */}
          {(selectedPlatforms === null || selectedPlatforms.includes('chess.com')) && (
            <section data-testid="rating-section-chess-com" className="space-y-3">
              <h2 className="text-lg font-medium">
                <span className="inline-flex items-center gap-1">
                  Chess.com Rating
                  <InfoPopover ariaLabel="Chess.com rating info" testId="rating-chess-com-info" side="top">
                    Your Chess.com rating over time by time control. Granularity adapts automatically: daily for shorter spans, weekly or monthly for longer ones.
                  </InfoPopover>
                </span>
              </h2>
              <RatingChart data={ratingData?.chess_com ?? []} platform="Chess.com" />
            </section>
          )}

          {/* Lichess Rating section */}
          {(selectedPlatforms === null || selectedPlatforms.includes('lichess')) && (
            <section data-testid="rating-section-lichess" className="space-y-3">
              <h2 className="text-lg font-medium">
                <span className="inline-flex items-center gap-1">
                  Lichess Rating
                  <InfoPopover ariaLabel="Lichess rating info" testId="rating-lichess-info" side="top">
                    Your Lichess rating over time by time control. Granularity adapts automatically: daily for shorter spans, weekly or monthly for longer ones. Lichess uses Glicko-2 ratings which start at 1500 and tend to run 200-400 points higher than Chess.com, so the two are not directly comparable.
                  </InfoPopover>
                </span>
              </h2>
              <RatingChart data={ratingData?.lichess ?? []} platform="Lichess" />
            </section>
          )}

          {/* WDL charts — always shown */}
          <GlobalStatsCharts
            byTimeControl={globalStats?.by_time_control ?? []}
            byColor={globalStats?.by_color ?? []}
          />
        </>
      )}
    </div>
  );
}
