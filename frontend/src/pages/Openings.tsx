import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { usePositionBookmarks, useTimeSeries } from '@/hooks/usePositionBookmarks';
import { WinRateChart } from '@/components/charts/WinRateChart';
import { WDLBarChart } from '@/components/charts/WDLBarChart';
import { apiClient } from '@/api/client';
import { cn } from '@/lib/utils';
import type { TimeControl, Recency, Platform, OpponentType, Color, MatchSide } from '@/types/api';
import { resolveMatchSide, legacyToMatchSide } from '@/types/api';
import type { TimeSeriesRequest } from '@/types/position_bookmarks';

interface StatsFilters {
  timeControls: TimeControl[] | null;
  platforms: Platform[] | null;
  rated: boolean | null;
  opponentType: OpponentType;
  recency: Recency | null;
}

const DEFAULT_STATS_FILTERS: StatsFilters = {
  timeControls: null,
  platforms: null,
  rated: null,
  opponentType: 'human',
  recency: null,
};

const TIME_CONTROLS: TimeControl[] = ['bullet', 'blitz', 'rapid', 'classical'];
const TIME_CONTROL_LABELS: Record<TimeControl, string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classical',
};
const PLATFORMS: Platform[] = ['chess.com', 'lichess'];
const PLATFORM_LABELS: Record<Platform, string> = {
  'chess.com': 'Chess.com',
  lichess: 'Lichess',
};

export function OpeningsPage() {
  const { data: bookmarks = [], isLoading } = usePositionBookmarks();
  const [filters, setFilters] = useState<StatsFilters>(DEFAULT_STATS_FILTERS);
  const [activeRequest, setActiveRequest] = useState<TimeSeriesRequest | null>(null);

  const update = useCallback((partial: Partial<StatsFilters>) => {
    setFilters((prev) => ({ ...prev, ...partial }));
  }, []);

  const toggleTimeControl = (tc: TimeControl) => {
    const current = filters.timeControls ?? TIME_CONTROLS;
    if (current.includes(tc)) {
      const next = current.filter((t) => t !== tc);
      update({ timeControls: next.length === TIME_CONTROLS.length ? null : next.length === 0 ? [tc] : next });
    } else {
      const next = [...current, tc];
      update({ timeControls: next.length === TIME_CONTROLS.length ? null : next });
    }
  };

  const isTimeControlActive = (tc: TimeControl) => {
    if (filters.timeControls === null) return true;
    return filters.timeControls.includes(tc);
  };

  const togglePlatform = (p: Platform) => {
    const current = filters.platforms ?? PLATFORMS;
    if (current.includes(p)) {
      const next = current.filter((x) => x !== p);
      update({ platforms: next.length === PLATFORMS.length ? null : next.length === 0 ? [p] : next });
    } else {
      const next = [...current, p];
      update({ platforms: next.length === PLATFORMS.length ? null : next });
    }
  };

  const isPlatformActive = (p: Platform) => {
    if (filters.platforms === null) return true;
    return filters.platforms.includes(p);
  };

  const handleAnalyze = useCallback(() => {
    if (bookmarks.length === 0) return;
    setActiveRequest({
      bookmarks: bookmarks.map((b) => ({
        bookmark_id: b.id,
        target_hash: b.target_hash,
        match_side: resolveMatchSide(
          legacyToMatchSide(b.match_side) as MatchSide,
          (b.color ?? 'white') as Color,
        ),
        color: b.color,
      })),
      time_control: filters.timeControls,
      platform: filters.platforms,
      rated: filters.rated,
      opponent_type: filters.opponentType,
      recency: filters.recency === 'all' ? null : filters.recency,
    });
  }, [bookmarks, filters]);

  // Auto-analyze on first load when bookmarks are available
  const [autoAnalyzed, setAutoAnalyzed] = useState(false);
  if (!autoAnalyzed && bookmarks.length > 0 && !isLoading) {
    setAutoAnalyzed(true);
    setActiveRequest({
      bookmarks: bookmarks.map((b) => ({
        bookmark_id: b.id,
        target_hash: b.target_hash,
        match_side: resolveMatchSide(
          legacyToMatchSide(b.match_side) as MatchSide,
          (b.color ?? 'white') as Color,
        ),
        color: b.color,
      })),
      time_control: filters.timeControls,
      platform: filters.platforms,
      rated: filters.rated,
      opponent_type: filters.opponentType,
      recency: filters.recency === 'all' ? null : filters.recency,
    });
  }

  const { data: tsData, isFetching } = useTimeSeries(activeRequest);

  // Total game count for the user
  const { data: gameCountData } = useQuery<{ count: number }>({
    queryKey: ['gameCount'],
    queryFn: async () => {
      const response = await apiClient.get<{ count: number }>('/games/count');
      return response.data;
    },
    staleTime: 30_000,
  });
  const totalGames = gameCountData?.count ?? null;

  // Total matched games across all bookmarks (union of unique games)
  const matchedGames = useMemo(() => {
    if (!tsData) return null;
    // Sum all game_counts across all bookmarks and months
    let total = 0;
    for (const s of tsData.series) {
      for (const p of s.data) {
        total += p.game_count;
      }
    }
    return total;
  }, [tsData]);

  // Derive WDL stats per bookmark
  const wdlStatsMap = useMemo(() => {
    const map: Record<number, { wins: number; draws: number; losses: number; total: number }> = {};
    for (const s of tsData?.series ?? []) {
      let wins = 0, draws = 0, losses = 0;
      for (const p of s.data) {
        wins += p.wins;
        draws += p.draws;
        losses += p.losses;
      }
      const total = wins + draws + losses;
      map[s.bookmark_id] = { wins, draws, losses, total };
    }
    return map;
  }, [tsData]);

  if (isLoading) {
    return <div className="p-8 text-muted-foreground">Loading...</div>;
  }

  if (bookmarks.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        <p className="text-lg">No bookmarks yet.</p>
        <p className="mt-2 text-sm">
          Save positions on the{' '}
          <a href="/" className="underline">Games</a>{' '}
          page to see stats here.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="openings-page" className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">Openings</h1>

      {/* Filters */}
      <div className="space-y-3">
        <div className="flex flex-wrap gap-x-6 gap-y-3">
          {/* Time controls */}
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Time control</p>
            <div className="flex flex-wrap gap-1">
              {TIME_CONTROLS.map((tc) => (
                <button
                  key={tc}
                  onClick={() => toggleTimeControl(tc)}
                  className={cn(
                    'rounded border px-2 py-0.5 text-xs transition-colors',
                    isTimeControlActive(tc)
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border bg-transparent text-muted-foreground hover:border-foreground hover:text-foreground',
                  )}
                >
                  {TIME_CONTROL_LABELS[tc]}
                </button>
              ))}
            </div>
          </div>

          {/* Platform */}
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Platform</p>
            <div className="flex flex-wrap gap-1">
              {PLATFORMS.map((p) => (
                <button
                  key={p}
                  onClick={() => togglePlatform(p)}
                  className={cn(
                    'rounded border px-2 py-0.5 text-xs transition-colors',
                    isPlatformActive(p)
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border bg-transparent text-muted-foreground hover:border-foreground hover:text-foreground',
                  )}
                >
                  {PLATFORM_LABELS[p]}
                </button>
              ))}
            </div>
          </div>

          {/* Rated */}
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Rated</p>
            <ToggleGroup
              type="single"
              value={filters.rated === null ? 'all' : filters.rated ? 'rated' : 'casual'}
              onValueChange={(v) => {
                if (!v) return;
                update({ rated: v === 'all' ? null : v === 'rated' });
              }}
              variant="outline"
              size="sm"
            >
              <ToggleGroupItem value="all">All</ToggleGroupItem>
              <ToggleGroupItem value="rated">Rated</ToggleGroupItem>
              <ToggleGroupItem value="casual">Casual</ToggleGroupItem>
            </ToggleGroup>
          </div>

          {/* Opponent */}
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Opponent</p>
            <ToggleGroup
              type="single"
              value={filters.opponentType}
              onValueChange={(v) => {
                if (!v) return;
                update({ opponentType: v as OpponentType });
              }}
              variant="outline"
              size="sm"
            >
              <ToggleGroupItem value="human">Human</ToggleGroupItem>
              <ToggleGroupItem value="bot">Bot</ToggleGroupItem>
              <ToggleGroupItem value="both">Both</ToggleGroupItem>
            </ToggleGroup>
          </div>

          {/* Recency */}
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Recency</p>
            <Select
              value={filters.recency ?? 'all'}
              onValueChange={(v) => update({ recency: v === 'all' ? null : (v as Recency) })}
            >
              <SelectTrigger size="sm">
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
        </div>

        <div className="flex items-center gap-4">
          <Button onClick={handleAnalyze} disabled={isFetching} size="lg" data-testid="openings-btn-analyze">
            {isFetching ? 'Analyzing...' : 'Analyze'}
          </Button>
          {matchedGames !== null && totalGames !== null && (
            <span className="text-sm text-muted-foreground">
              {matchedGames.toLocaleString()} of {totalGames.toLocaleString()} games matched
            </span>
          )}
        </div>
      </div>

      {/* WDL Bar Chart */}
      {tsData && (
        <div>
          <h2 className="text-lg font-medium mb-3">Win / Draw / Loss</h2>
          <WDLBarChart bookmarks={bookmarks} wdlStatsMap={wdlStatsMap} />
        </div>
      )}

      {/* Win Rate Over Time */}
      {tsData && (
        <div>
          <h2 className="text-lg font-medium mb-3">Win Rate Over Time</h2>
          <WinRateChart bookmarks={bookmarks} series={tsData.series} />
        </div>
      )}
    </div>
  );
}
