import { useState, useCallback } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/api/client';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import { InfoPopover } from '@/components/ui/info-popover';
import { FilterPanel } from '@/components/filters/FilterPanel';
import { useFilterStore } from '@/hooks/useFilterStore';
import { useGlobalStats, useRatingHistory } from '@/hooks/useStats';
import { GlobalStatsCharts } from '@/components/stats/GlobalStatsCharts';
import { RatingChart } from '@/components/stats/RatingChart';
import { useUserProfile } from '@/hooks/useUserProfile';
import type { FilterState } from '@/components/filters/FilterPanel';

// ── Admin-only: Sentry error path test ───────────────────────────────────────
// Tests three error paths: event handler, TanStack Query, and React render.
function SentryTestButtons() {
  const [shouldCrash, setShouldCrash] = useState(false);
  const [tqEnabled, setTqEnabled] = useState(false);

  // TanStack Query error — fires only when enabled
  useQuery({
    queryKey: ['sentry-test-tq-error'],
    queryFn: async () => { throw new Error('[Sentry Test] TanStack Query error'); },
    enabled: tqEnabled,
    retry: false,
  });

  // React render error — triggers ErrorBoundary + Sentry
  if (shouldCrash) {
    throw new Error('[Sentry Test] React render error');
  }

  return (
    <div className="charcoal-texture rounded-md p-4 space-y-2">
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
        Sentry Error Test (temporary)
      </p>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="destructive"
          data-testid="btn-sentry-test-event"
          onClick={() => { throw new Error('[Sentry Test] Event handler error'); }}
        >
          Event handler error
        </Button>
        <Button
          size="sm"
          variant="destructive"
          data-testid="btn-sentry-test-tq"
          onClick={() => setTqEnabled(true)}
        >
          TanStack Query error
        </Button>
        <Button
          size="sm"
          variant="destructive"
          data-testid="btn-sentry-test-render"
          onClick={() => setShouldCrash(true)}
        >
          React render error
        </Button>
        <Button
          size="sm"
          variant="destructive"
          data-testid="btn-sentry-test-backend"
          onClick={() => apiClient.post('/users/sentry-test-error')}
        >
          Backend error
        </Button>
      </div>
    </div>
  );
}
// ── END Sentry test ──────────────────────────────────────────────────────────

function AdminTools() {
  const { data: profile } = useUserProfile();
  if (!profile?.is_superuser) return null;
  return <SentryTestButtons />;
}

export function GlobalStatsPage() {
  // Filter state shared across pages — GlobalStats only uses recency + platforms
  const [filters, setFilters] = useFilterStore();

  // Derive recency and platforms from FilterState for the stats hooks
  const recency = filters.recency;
  const selectedPlatforms = filters.platforms;

  const { data: ratingData, isLoading: ratingLoading } = useRatingHistory(recency, selectedPlatforms);
  const { data: globalStats, isLoading: statsLoading } = useGlobalStats(recency, selectedPlatforms);

  const isLoading = ratingLoading || statsLoading;

  // ── Mobile collapsible state ───────────────────────────────────────────────
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  const handleFilterChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
  }, [setFilters]);

  const content = isLoading ? (
    <div className="text-muted-foreground">Loading...</div>
  ) : (
    <div className="space-y-6">
      {/* Chess.com Rating section */}
      {(selectedPlatforms === null || selectedPlatforms.includes('chess.com')) && (
        <div className="charcoal-texture rounded-md p-4">
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
        </div>
      )}

      {/* Lichess Rating section */}
      {(selectedPlatforms === null || selectedPlatforms.includes('lichess')) && (
        <div className="charcoal-texture rounded-md p-4">
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
        </div>
      )}

      {/* WDL charts */}
      <div className="charcoal-texture rounded-md p-4">
        <GlobalStatsCharts
          byTimeControl={globalStats?.by_time_control ?? []}
          byColor={globalStats?.by_color ?? []}
        />
      </div>

      <AdminTools />
    </div>
  );

  return (
    <div data-testid="global-stats-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 md:py-6 md:px-6">

        {/* Desktop: two-column layout with sidebar */}
        <div className="hidden md:grid md:grid-cols-[280px_1fr] md:gap-8">
          <div className="min-w-0">
            <div className="charcoal-texture rounded-md p-2">
              <FilterPanel filters={filters} onChange={handleFilterChange} visibleFilters={['platform', 'recency']} />
            </div>
          </div>
          <div className="min-w-0">
            {content}
          </div>
        </div>

        {/* Mobile: single column */}
        <div className="md:hidden flex flex-col gap-4 min-w-0">
          {/* Mobile filters collapsible */}
          <div className="sticky top-0 z-20 bg-background pb-2">
            <div className="charcoal-texture rounded-md">
              <Collapsible open={mobileFiltersOpen} onOpenChange={setMobileFiltersOpen}>
                <CollapsibleTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-between px-3 text-sm font-medium min-h-11 rounded-none hover:bg-charcoal-hover!"
                    data-testid="section-filters-mobile"
                  >
                    Filters
                    {mobileFiltersOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="border-t border-border/20" />
                  <div className="p-2">
                    <FilterPanel filters={filters} onChange={handleFilterChange} visibleFilters={['platform', 'recency']} />
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </div>
          </div>

          {content}
        </div>
      </main>
    </div>
  );
}
