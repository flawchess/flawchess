import { useState, useCallback, useMemo, useEffect } from 'react';
import { SlidersHorizontal, X } from 'lucide-react';
import { SidebarLayout } from '@/components/layout/SidebarLayout';
import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import { Tooltip } from '@/components/ui/tooltip';
import { InfoPopover } from '@/components/ui/info-popover';
import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { FilterPanel, DEFAULT_FILTERS, areFiltersEqual, FILTER_DOT_FIELDS } from '@/components/filters/FilterPanel';
import { useFilterStore } from '@/hooks/useFilterStore';
import { useGlobalStats, useRatingHistory } from '@/hooks/useStats';
import { useLibraryFlawStats } from '@/hooks/useLibrary';
import { DEFAULT_FLAW_FILTER } from '@/hooks/useFlawFilterStore';
import { FlawStatsPanel } from '@/components/library/FlawStatsPanel';
import { GlobalStatsCharts } from '@/components/stats/GlobalStatsCharts';
import { EvalCoverageHeader } from '@/components/EvalCoverageHeader';
import { RatingChart } from '@/components/stats/RatingChart';
import type { FilterState } from '@/components/filters/FilterPanel';

export function GlobalStatsPage() {
  // Filter state shared across pages — full filter set exposed on the Stats tab.
  // `filters` is the committed store value that queries read.
  // `pendingFilters` is the draft for both desktop sidebar and mobile drawer.
  const [filters, setFilters] = useFilterStore();
  const [pendingFilters, setPendingFilters] = useState<FilterState>(filters);

  // Sync pending -> committed when the filter store changes from another page/tab.
  useEffect(() => {
    setPendingFilters(filters);
  }, [filters]);

  const selectedPlatforms = filters.platforms;

  const { data: ratingData, isLoading: ratingLoading } = useRatingHistory(
    filters, selectedPlatforms, filters.opponentType, filters.opponentStrength,
  );
  const { data: globalStats, isLoading: statsLoading } = useGlobalStats(
    filters, selectedPlatforms, filters.opponentType, filters.opponentStrength,
  );

  const isLoading = ratingLoading || statsLoading;

  // ── Flaw stats (empty severity — severity scoped to Games tab only) ────────
  const {
    data: flawStatsData,
    isLoading: flawStatsLoading,
    isError: flawStatsError,
  } = useLibraryFlawStats(filters, DEFAULT_FLAW_FILTER);

  // ── Mobile collapsible state ───────────────────────────────────────────────
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // ── Desktop sidebar state ───────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState<string | null>(null);

  // Desktop sidebar open-change: snapshot committed filters as pending draft on open.
  const handleSidebarOpenChange = useCallback((panel: string | null) => {
    if (panel === 'filters' && sidebarOpen !== 'filters') {
      setPendingFilters(filters);
    }
    setSidebarOpen(panel);
  }, [sidebarOpen, filters]);

  // Desktop Apply: commit pending to store and close panel.
  const handleDesktopFiltersApply = useCallback(() => {
    setFilters(pendingFilters);
    setSidebarOpen(null);
  }, [pendingFilters, setFilters]);

  // Mobile drawer: snapshot committed on open; close without Apply discards draft.
  const handleMobileFiltersOpenChange = useCallback((open: boolean) => {
    if (open && !mobileFiltersOpen) {
      setPendingFilters(filters);
    }
    setMobileFiltersOpen(open);
  }, [mobileFiltersOpen, filters]);

  // Mobile Apply: commit pending to store and close drawer.
  const handleMobileFiltersApply = useCallback(() => {
    setFilters(pendingFilters);
    setMobileFiltersOpen(false);
  }, [pendingFilters, setFilters]);

  // Modified-dot uses the uniform FILTER_DOT_FIELDS comparison (all FilterState keys except
  // `color`). The dot reflects the shared filter store — if the user set e.g. timeControls
  // on Openings, the Stats dot lights up, and clicking Reset here will clear those too
  // (global reset semantics).
  const isFiltersModified = useMemo(
    () => !areFiltersEqual(filters, DEFAULT_FILTERS, FILTER_DOT_FIELDS),
    [filters],
  );

  const content = isLoading ? (
    <div className="text-muted-foreground">Loading...</div>
  ) : (
    <div className="space-y-6">
      {/* Chess.com Rating section */}
      {(selectedPlatforms === null || selectedPlatforms.includes('chess.com')) && (
        <Card as="section" data-testid="rating-section-chess-com">
          <CardHeader data-testid="rating-chess-com-header">
            Chess.com Rating
            <InfoPopover ariaLabel="Chess.com rating info" testId="rating-chess-com-info" side="top">
              Your Chess.com rating over time by time control. Granularity adapts automatically: daily for shorter spans, weekly or monthly for longer ones.
            </InfoPopover>
          </CardHeader>
          <CardBody>
            <RatingChart data={ratingData?.chess_com ?? []} platform="Chess.com" enabledTimeControls={filters.timeControls} />
          </CardBody>
        </Card>
      )}

      {/* Lichess Rating section */}
      {(selectedPlatforms === null || selectedPlatforms.includes('lichess')) && (
        <Card as="section" data-testid="rating-section-lichess">
          <CardHeader data-testid="rating-lichess-header">
            Lichess Rating
            <InfoPopover ariaLabel="Lichess rating info" testId="rating-lichess-info" side="top">
              Your Lichess rating over time by time control. Granularity adapts automatically: daily for shorter spans, weekly or monthly for longer ones. Lichess uses Glicko-2 ratings which start at 1500 and tend to run 200-400 points higher than Chess.com, so the two are not directly comparable.
            </InfoPopover>
          </CardHeader>
          <CardBody>
            <RatingChart data={ratingData?.lichess ?? []} platform="Lichess" enabledTimeControls={filters.timeControls} />
          </CardBody>
        </Card>
      )}

      {/* WDL charts — each card owns its own shell inside GlobalStatsCharts */}
      <GlobalStatsCharts
        byTimeControl={globalStats?.by_time_control ?? []}
        byColor={globalStats?.by_color ?? []}
        enabledTimeControls={filters.timeControls}
      />

      {/* Flaw stats panel — shared filters, empty severity (severity is scoped to Games tab) */}
      <FlawStatsPanel
        stats={flawStatsData}
        isLoading={flawStatsLoading}
        isError={flawStatsError}
      />
    </div>
  );

  return (
    // No own max-width/padding/main wrapper: this page only renders as the Library
    // "Stats" subtab, nested inside LibraryPage's max-w-7xl container and App's <main>.
    // Wrapping again would double the horizontal padding (narrower than the Games/Flaws
    // subtabs) and nest a second <main> landmark. Plain div = same width as Games/Flaws.
    <div data-testid="global-stats-page">

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
                  <FilterPanel filters={pendingFilters} onChange={setPendingFilters} onApply={handleDesktopFiltersApply} visibleFilters={['playedAs', 'timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency']} />
                </div>
              ),
            },
          ]}
          activePanel={sidebarOpen}
          onActivePanelChange={handleSidebarOpenChange}
        >
          <EvalCoverageHeader />
          {content}
        </SidebarLayout>

        {/* Mobile: single column */}
        <div className="md:hidden flex flex-col gap-4 min-w-0">
          <EvalCoverageHeader />
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

          {/* Filter drawer — staged Apply-only */}
          <Drawer open={mobileFiltersOpen} onOpenChange={handleMobileFiltersOpenChange} direction="right">
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
                <FilterPanel filters={pendingFilters} onChange={setPendingFilters} onApply={handleMobileFiltersApply} visibleFilters={['playedAs', 'timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency']} />
              </div>
            </DrawerContent>
          </Drawer>

          {content}
        </div>
    </div>
  );
}
