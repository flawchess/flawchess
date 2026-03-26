import { useState, useCallback } from 'react';
import { useNavigate, useLocation, Navigate, Link } from 'react-router-dom';
import { ChevronUp, ChevronDown, BarChart2Icon, Gamepad2Icon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { FilterPanel, DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import { EndgameWDLChart } from '@/components/charts/EndgameWDLChart';
import { GameCardList } from '@/components/results/GameCardList';
import { useEndgameStats, useEndgameGames } from '@/hooks/useEndgames';
import { useDebounce } from '@/hooks/useDebounce';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { EndgameClass } from '@/types/endgames';

const PAGE_SIZE = 20;

export function EndgamesPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const needsRedirect =
    location.pathname === '/endgames' || location.pathname === '/endgames/';
  const activeTab = location.pathname.includes('/games') ? 'games' : 'statistics';

  // ── Filter state — color and matchSide are fixed (not used for endgames per D-02) ──
  const [filters, setFilters] = useState<FilterState>({
    ...DEFAULT_FILTERS,
    color: 'white',    // Fixed — not used, FilterState requires it
    matchSide: 'both', // Fixed — not used
  });
  const debouncedFilters = useDebounce(filters, 300);

  // ── Category selection state ─────────────────────────────────────────────────
  const [selectedCategory, setSelectedCategory] = useState<EndgameClass | null>(null);
  const [gamesOffset, setGamesOffset] = useState(0);

  // ── Mobile collapsible state ───────────────────────────────────────────────
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // ── Data ─────────────────────────────────────────────────────────────────────
  const { data: statsData, isLoading: statsLoading } = useEndgameStats(debouncedFilters);
  const { data: gamesData, isLoading: gamesLoading } = useEndgameGames(
    selectedCategory,
    debouncedFilters,
    gamesOffset,
    PAGE_SIZE,
  );

  // ── Filter change handler — wraps setFilters + resets pagination ────────────
  const handleFilterChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    setGamesOffset(0); // D-03: reset pagination on filter change
  }, []);

  // ── Category click handlers ───────────────────────────────────────────────────

  const handleCategoryClick = useCallback((category: EndgameClass) => {
    // First click on a row selects it; reset pagination on category change (D-03)
    setSelectedCategory(category);
    setGamesOffset(0);
  }, []);

  const handleSelectedCategoryClick = useCallback(() => {
    // Second click on the already-selected category — navigate to games tab
    navigate('/endgames/games');
  }, [navigate]);

  // ── Statistics tab content ───────────────────────────────────────────────────

  // Summary line: "X of Y games (Z%) reached an endgame phase"
  const endgameSummary = statsData ? (
    statsData.total_games === 0 ? null : (
      <p className="text-sm text-muted-foreground mb-2" data-testid="endgame-summary">
        {statsData.endgame_games} of {statsData.total_games} games
        ({(statsData.endgame_games / statsData.total_games * 100).toFixed(1)}%) reached an endgame phase
      </p>
    )
  ) : null;

  const statisticsContent = (
    <div className="flex flex-col gap-4">
      {statsLoading ? (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading endgame statistics...</p>
        </div>
      ) : statsData && statsData.categories.length > 0 ? (
        <>
          {endgameSummary}
          <EndgameWDLChart
            categories={statsData.categories}
            selectedCategory={selectedCategory}
            onCategoryClick={handleCategoryClick}
            onSelectedCategoryClick={handleSelectedCategoryClick}
          />
        </>
      ) : statsData && statsData.categories.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">No endgame data yet</p>
          <p className="mb-6 text-sm text-muted-foreground">
            No games have reached an endgame phase yet with the current filters. Try adjusting
            the time control or recency filters.
          </p>
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">No games imported yet</p>
          <p className="mb-6 text-sm text-muted-foreground">
            Import your games from chess.com or lichess to see endgame analysis.
          </p>
          <Button variant="outline" size="sm" asChild>
            <Link to="/import">Import Games</Link>
          </Button>
        </div>
      )}
    </div>
  );

  // ── Games tab content ────────────────────────────────────────────────────────

  const selectedLabel =
    selectedCategory && statsData
      ? statsData.categories.find((c) => c.endgame_class === selectedCategory)?.label ?? null
      : null;

  const gamesContent = (
    <div className="flex flex-col gap-4">
      {selectedCategory === null ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="text-sm text-muted-foreground">
            Select an endgame category in the Statistics tab to view matching games.
          </p>
        </div>
      ) : gamesLoading ? (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading games...</p>
        </div>
      ) : gamesData && gamesData.games.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">No games matched</p>
          <p className="text-sm text-muted-foreground">
            Try adjusting the time control, platform, or recency filters.
          </p>
        </div>
      ) : gamesData ? (
        <div>
          {selectedLabel && (
            <p className="text-lg font-medium mb-3">{selectedLabel} Endgames</p>
          )}
          <GameCardList
            games={gamesData.games}
            matchedCount={gamesData.matched_count}
            totalGames={gamesData.matched_count}
            offset={gamesOffset}
            limit={PAGE_SIZE}
            onPageChange={setGamesOffset}
          />
        </div>
      ) : null}
    </div>
  );

  // ── Render ───────────────────────────────────────────────────────────────────

  if (needsRedirect) {
    return <Navigate to="/endgames/statistics" replace />;
  }

  return (
    <div data-testid="endgames-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 md:py-6 md:px-6">

        {/* Desktop: two-column layout */}
        <div className="hidden md:grid md:grid-cols-[280px_1fr] md:gap-8">
          <div className="min-w-0">
            <FilterPanel filters={filters} onChange={handleFilterChange} />
          </div>
          <div className="min-w-0">
            <Tabs value={activeTab} onValueChange={(val) => navigate(`/endgames/${val}`)}>
              <TabsList className="w-full" data-testid="endgames-tabs">
                <TabsTrigger value="statistics" data-testid="tab-statistics" className="flex-1">
                  <BarChart2Icon className="mr-1.5 h-4 w-4" />
                  Statistics
                </TabsTrigger>
                <TabsTrigger value="games" data-testid="tab-games" className="flex-1">
                  <Gamepad2Icon className="mr-1.5 h-4 w-4" />
                  Games
                </TabsTrigger>
              </TabsList>
              <TabsContent value="statistics" className="mt-4">
                {statisticsContent}
              </TabsContent>
              <TabsContent value="games" className="mt-4">
                {gamesContent}
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Mobile: single column */}
        <div className="md:hidden flex flex-col gap-2 min-w-0">

          {/* Filters collapsible — collapsed by default on mobile */}
          <Collapsible open={mobileFiltersOpen} onOpenChange={setMobileFiltersOpen}>
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-between px-2 text-sm font-medium bg-muted/50 hover:bg-muted! border border-border/40 rounded min-h-11 sm:min-h-0"
                data-testid="section-filters-mobile"
              >
                Filters
                {mobileFiltersOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="pt-2">
                <FilterPanel filters={filters} onChange={handleFilterChange} />
              </div>
            </CollapsibleContent>
          </Collapsible>

          <div className="border-t border-border/40" />

          {/* Tabs: Statistics / Games */}
          <Tabs value={activeTab} onValueChange={(val) => navigate(`/endgames/${val}`)}>
            <TabsList className="w-full h-11!" data-testid="endgames-tabs-mobile">
              <TabsTrigger value="statistics" className="flex-1" data-testid="tab-statistics-mobile">
                <BarChart2Icon className="mr-1.5 h-4 w-4" />
                Statistics
              </TabsTrigger>
              <TabsTrigger value="games" className="flex-1" data-testid="tab-games-mobile">
                <Gamepad2Icon className="mr-1.5 h-4 w-4" />
                Games
              </TabsTrigger>
            </TabsList>
            <TabsContent value="statistics" className="mt-4">
              {statisticsContent}
            </TabsContent>
            <TabsContent value="games" className="mt-4">
              {gamesContent}
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  );
}
