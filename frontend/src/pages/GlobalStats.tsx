import { useState, useCallback, useMemo } from 'react';
import { SlidersHorizontal, X } from 'lucide-react';
import { SidebarLayout } from '@/components/layout/SidebarLayout';
import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import { Tooltip } from '@/components/ui/tooltip';
import { InfoPopover } from '@/components/ui/info-popover';
import { FilterPanel, DEFAULT_FILTERS, areFiltersEqual, FILTER_DOT_FIELDS } from '@/components/filters/FilterPanel';
import { useFilterStore } from '@/hooks/useFilterStore';
import { useGlobalStats, useRatingHistory } from '@/hooks/useStats';
import { GlobalStatsCharts } from '@/components/stats/GlobalStatsCharts';
import { RatingChart } from '@/components/stats/RatingChart';
import type { FilterState } from '@/components/filters/FilterPanel';

export function GlobalStatsPage() {
  // Filter state shared across pages — GlobalStats only uses recency + platforms
  const [filters, setFilters] = useFilterStore();

  // Derive recency and platforms from FilterState for the stats hooks
  const recency = filters.recency;
  const selectedPlatforms = filters.platforms;

  const { data: ratingData, isLoading: ratingLoading } = useRatingHistory(
    recency, selectedPlatforms, filters.opponentType, filters.opponentStrength,
  );
  const { data: globalStats, isLoading: statsLoading } = useGlobalStats(
    recency, selectedPlatforms, filters.opponentType, filters.opponentStrength,
  );

  const isLoading = ratingLoading || statsLoading;

  // ── Mobile collapsible state ───────────────────────────────────────────────
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // ── Desktop sidebar state ───────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState<string | null>(null);

  const handleFilterChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
  }, [setFilters]);

  // Modified-dot uses the uniform FILTER_DOT_FIELDS comparison (all FilterState keys except
  // `color`). GlobalStats's own UI only exposes platform + recency, but the dot reflects the
  // shared filter store — if the user set e.g. timeControls on Openings, the GlobalStats dot
  // lights up, and clicking Reset here will clear those too (global reset semantics).
  const isFiltersModified = useMemo(
    () => !areFiltersEqual(filters, DEFAULT_FILTERS, FILTER_DOT_FIELDS),
    [filters],
  );
  // NOTE: no pulse on GlobalStats — it's immediate-apply.

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
    </div>
  );

  return (
    <div data-testid="global-stats-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 md:py-6 md:px-6">

        {/* Desktop: sidebar strip + filter panel + content */}
        <SidebarLayout
          panels={[
            {
              id: 'filters',
              label: 'Filters',
              icon: <SlidersHorizontal className="h-5 w-5" />,
              notificationDot: isFiltersModified ? (
                <span
                  className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                  data-testid="filters-modified-dot"
                  aria-hidden="true"
                >
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
                </span>
              ) : undefined,
              content: (
                <div className="p-3">
                  <FilterPanel filters={filters} onChange={handleFilterChange} visibleFilters={['platform', 'recency']} />
                </div>
              ),
            },
          ]}
          activePanel={sidebarOpen}
          onActivePanelChange={setSidebarOpen}
        >
          {content}
        </SidebarLayout>

        {/* Mobile: single column */}
        <div className="md:hidden flex flex-col gap-4 min-w-0">
          {/* Sticky filter button (top right) */}
          <div className="sticky top-0 z-20 flex justify-end pb-2">
            <Tooltip content="Open filters" side="left">
              <Button
                variant="ghost"
                size="icon"
                className="relative h-11 w-11 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80"
                onClick={() => setMobileFiltersOpen(true)}
                data-testid="btn-open-filter-drawer"
                aria-label="Open filters"
              >
                <SlidersHorizontal className="h-4 w-4" />
                {isFiltersModified && (
                  <span
                    className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                    data-testid="filters-modified-dot-mobile"
                    aria-hidden="true"
                  >
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
                  </span>
                )}
              </Button>
            </Tooltip>
          </div>

          {/* Filter drawer */}
          <Drawer open={mobileFiltersOpen} onOpenChange={setMobileFiltersOpen} direction="right">
            <DrawerContent className="!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[85vh]" data-testid="drawer-filter-sidebar">
              <DrawerHeader className="flex flex-row items-center justify-between">
                <DrawerTitle>Filters</DrawerTitle>
                <Tooltip content="Close filters">
                  <DrawerClose asChild>
                    <Button variant="ghost" size="icon" aria-label="Close filters" data-testid="btn-close-filter-drawer">
                      <X className="h-4 w-4" />
                    </Button>
                  </DrawerClose>
                </Tooltip>
              </DrawerHeader>
              <div className="overflow-y-auto flex-1 p-4 space-y-4">
                <FilterPanel filters={filters} onChange={handleFilterChange} visibleFilters={['platform', 'recency']} />
              </div>
            </DrawerContent>
          </Drawer>

          {content}
        </div>
      </main>
    </div>
  );
}
