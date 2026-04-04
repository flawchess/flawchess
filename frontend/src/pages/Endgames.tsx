import { useState, useCallback } from 'react';
import { useNavigate, useLocation, Navigate, Link } from 'react-router-dom';
import { ChevronUp, ChevronDown, BarChart2Icon, Gamepad2Icon } from 'lucide-react';
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { FilterPanel } from '@/components/filters/FilterPanel';
import { useFilterStore } from '@/hooks/useFilterStore';
import { EndgameWDLChart } from '@/components/charts/EndgameWDLChart';
import { EndgamePerformanceSection } from '@/components/charts/EndgamePerformanceSection';
import { EndgameConvRecovChart } from '@/components/charts/EndgameConvRecovChart';
import { EndgameTimelineChart } from '@/components/charts/EndgameTimelineChart';
import { EndgameConvRecovTimelineChart } from '@/components/charts/EndgameConvRecovTimelineChart';
import { GameCardList } from '@/components/results/GameCardList';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { useEndgameStats, useEndgameGames, useEndgamePerformance, useEndgameTimeline, useEndgameConvRecovTimeline } from '@/hooks/useEndgames';
import { useDebounce } from '@/hooks/useDebounce';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { EndgameClass } from '@/types/endgames';

const PAGE_SIZE = 20;

const ENDGAME_CLASS_LABELS: Record<EndgameClass, string> = {
  mixed: 'Mixed',
  rook: 'Rook',
  minor_piece: 'Minor Piece',
  pawn: 'Pawn',
  queen: 'Queen',
  pawnless: 'Pawnless',
};

const DEFAULT_ENDGAME_CLASS: EndgameClass = 'mixed';

export function EndgamesPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const needsRedirect =
    location.pathname === '/endgames' || location.pathname === '/endgames/';
  // Redirect old /endgames/statistics URL to /endgames/stats after tab rename
  const needsLegacyRedirect = location.pathname.endsWith('/statistics');
  const activeTab = location.pathname.includes('/games') ? 'games' : 'stats';

  // ── Filter state (shared across pages) — color and matchSide are not used for endgames ──
  const [filters, setFilters] = useFilterStore();
  const debouncedFilters = useDebounce(filters, 300);

  // ── Category selection state ─────────────────────────────────────────────────
  const [selectedCategory, setSelectedCategory] = useState<EndgameClass>(DEFAULT_ENDGAME_CLASS);
  const [gamesOffset, setGamesOffset] = useState(0);

  // ── Mobile collapsible state ───────────────────────────────────────────────
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // ── Data ─────────────────────────────────────────────────────────────────────
  const { data: statsData, isLoading: statsLoading, isError: statsError } = useEndgameStats(debouncedFilters);
  const { data: perfData } = useEndgamePerformance(debouncedFilters);
  const { data: timelineData } = useEndgameTimeline(debouncedFilters);
  const { data: convRecovData } = useEndgameConvRecovTimeline(debouncedFilters);
  const { data: gamesData, isLoading: gamesLoading, isError: gamesError } = useEndgameGames(
    selectedCategory,
    debouncedFilters,
    gamesOffset,
    PAGE_SIZE,
  );

  // ── Filter change handler — wraps setFilters + resets pagination ────────────
  const handleFilterChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    setGamesOffset(0); // D-03: reset pagination on filter change
  }, [setFilters]);

  // ── Category selection handler ──────────────────────────────────────────────

  const handleCategorySelect = useCallback((category: EndgameClass) => {
    // Select category, reset pagination, and scroll to top — user navigates via link icon
    setSelectedCategory(category);
    setGamesOffset(0);
    window.scrollTo(0, 0);
  }, []);

  // ── Stats tab content ──────────────────────────────────────────────────────

  // Summary line + collapsible explaining endgame concepts and metric limitations
  const endgameSummary = statsData ? (
    statsData.total_games === 0 ? null : (
      <div data-testid="endgame-summary">
        <p className="text-sm text-muted-foreground mb-2">
          {statsData.endgame_games} of {statsData.total_games} games
          ({(statsData.endgame_games / statsData.total_games * 100).toFixed(1)}%) reached an endgame phase
        </p>
        <Accordion type="single" collapsible>
          <AccordionItem value="concepts" className="charcoal-texture rounded-md px-4" data-testid="endgame-concepts-trigger">
            <AccordionTrigger className="text-muted-foreground hover:no-underline">
              Endgame statistics concepts
            </AccordionTrigger>
            <AccordionContent className="text-muted-foreground space-y-2">
              <p>
                <strong>Endgame phase:</strong> positions where the total count of major and minor pieces
                (queens, rooks, bishops, knights) across both sides is at most 6. Kings and pawns are not
                counted. This follows the Lichess definition.
              </p>
              <p>
                <strong>Endgame types:</strong> Rook, Minor Piece (bishops/knights), Pawn (king and pawns only),
                Queen, Mixed (two or more piece types), and Pawnless (no pawns on board). A game is counted
                for a type only if it spent at least 3 full moves (6 half-moves) in that type. A single game
                can pass through multiple types — for example, a rook endgame where the rooks get traded
                becomes a pawn endgame, so the game counts toward both.
              </p>
              <p>
                <strong>Conversion:</strong> your win rate when you entered an endgame sequence
                with a material advantage of at least 3 points. <strong>Recovery:</strong> your
                draw+win rate when you entered an endgame sequence with a material deficit of at
                least 3 points. Since a game can pass through multiple endgame types, it can
                contribute a conversion or recovery entry to each type independently.
              </p>
              <p>
                These rates reflect your performance against opponents at your current rating level.
                As your rating changes, you face stronger or weaker opponents, so trends may not
                directly indicate improvement or stagnation in absolute terms.
              </p>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
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
          {perfData && perfData.endgame_wdl.total > 0 && (
            <div className="charcoal-texture rounded-md p-4">
              <EndgamePerformanceSection data={perfData} />
            </div>
          )}
          {convRecovData && (convRecovData.conversion.length > 0 || convRecovData.recovery.length > 0) && (
            <div className="charcoal-texture rounded-md p-4">
              <EndgameConvRecovTimelineChart data={convRecovData} />
            </div>
          )}
          <div className="charcoal-texture rounded-md p-4">
            <EndgameWDLChart
              categories={statsData.categories}
              onCategorySelect={handleCategorySelect}
            />
          </div>
          {statsData && statsData.categories.length > 0 && (
            <div className="charcoal-texture rounded-md p-4">
              <EndgameConvRecovChart categories={statsData.categories} />
            </div>
          )}
          {timelineData && timelineData.overall.length > 0 && (
            <div className="charcoal-texture rounded-md p-4">
              <EndgameTimelineChart data={timelineData} />
            </div>
          )}
        </>
      ) : statsError ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">Failed to load endgame data</p>
          <p className="text-sm text-muted-foreground">
            Something went wrong. Please try again in a moment.
          </p>
        </div>
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

  // ── Endgame type dropdown (used in Games tab) ──────────────────────────────
  const endgameTypeDropdown = (
    <div className="flex items-center gap-2">
      <p className="text-xs text-muted-foreground whitespace-nowrap">Endgame type</p>
      <Select
        value={selectedCategory}
        onValueChange={(v) => {
          setSelectedCategory(v as EndgameClass);
          setGamesOffset(0);
        }}
      >
        <SelectTrigger size="sm" data-testid="filter-endgame-type" className="min-h-11 sm:min-h-0 w-full sm:w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {(Object.entries(ENDGAME_CLASS_LABELS) as [EndgameClass, string][]).map(([value, label]) => (
            <SelectItem key={value} value={value}>{label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );

  const selectedCategoryStats = statsData?.categories.find(c => c.endgame_class === selectedCategory);

  const gamesContent = (
    <div className="flex flex-col gap-4">
      {selectedCategoryStats && selectedCategoryStats.total > 0 && (
        <div className="charcoal-texture rounded-md p-4">
          <WDLChartRow
            data={selectedCategoryStats}
            label={`${ENDGAME_CLASS_LABELS[selectedCategory]} Endgame Results`}
            barHeight="h-6"
            testId="wdl-endgame-games"
          />
        </div>
      )}
      {endgameTypeDropdown}
      {gamesLoading ? (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading games...</p>
        </div>
      ) : gamesError ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">Failed to load games</p>
          <p className="text-sm text-muted-foreground">
            Something went wrong. Please try again in a moment.
          </p>
        </div>
      ) : gamesData && gamesData.games.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">No games matched</p>
          <p className="text-sm text-muted-foreground">
            Try adjusting the time control, platform, or recency filters.
          </p>
        </div>
      ) : gamesData ? (
        <GameCardList
          games={gamesData.games}
          matchedCount={gamesData.matched_count}
          totalGames={statsData?.endgame_games ?? gamesData.matched_count}
          offset={gamesOffset}
          limit={PAGE_SIZE}
          onPageChange={setGamesOffset}
          matchLabel={statsData ? (
            <>
              {gamesData.matched_count} of {statsData.endgame_games}{' '}
              ({(gamesData.matched_count / statsData.endgame_games * 100).toFixed(1)}%){' '}
              games with an endgame matched
            </>
          ) : undefined}
        />
      ) : null}
    </div>
  );

  // ── Render ───────────────────────────────────────────────────────────────────

  if (needsRedirect) {
    return <Navigate to="/endgames/stats" replace />;
  }

  if (needsLegacyRedirect) {
    return <Navigate to="/endgames/stats" replace />;
  }

  return (
    <div data-testid="endgames-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 md:py-6 md:px-6">

        {/* Desktop: two-column layout */}
        <div className="hidden md:grid md:grid-cols-[280px_1fr] md:gap-8">
          <div className="min-w-0">
            <div className="border border-border rounded-md p-2">
              <FilterPanel filters={filters} onChange={handleFilterChange} />
            </div>
          </div>
          <div className="min-w-0">
            <Tabs value={activeTab} onValueChange={(val) => navigate(`/endgames/${val}`)}>
              <TabsList variant="brand" className="w-full" data-testid="endgames-tabs">
                <TabsTrigger value="stats" data-testid="tab-stats" className="flex-1">
                  <BarChart2Icon className="mr-1.5 h-4 w-4" />
                  Stats
                  <span
                    data-testid="badge-beta"
                    className="text-[10px] font-semibold uppercase tracking-wide bg-amber-500/15 text-amber-600 dark:text-amber-400 px-1.5 py-0.5 rounded-full ml-1.5"
                  >
                    Beta
                  </span>
                </TabsTrigger>
                <TabsTrigger value="games" data-testid="tab-games" className="flex-1">
                  <Gamepad2Icon className="mr-1.5 h-4 w-4" />
                  Games
                </TabsTrigger>
              </TabsList>
              <TabsContent value="stats" className="mt-4">
                {statisticsContent}
              </TabsContent>
              <TabsContent value="games" className="mt-4">
                {gamesContent}
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Mobile: single column */}
        <div className="md:hidden flex flex-col min-w-0">
          <Tabs value={activeTab} onValueChange={(val) => navigate(`/endgames/${val}`)}>
            {/* Sticky filters */}
            <div className="sticky top-0 z-20 bg-background pb-2">
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
            </div>

            {/* Tabs: Stats / Games */}
            <hr className="border-t border-white/10 mb-3" />
            <TabsList variant="brand" className="w-full h-11!" data-testid="endgames-tabs-mobile">
              <TabsTrigger value="stats" className="flex-1" data-testid="tab-stats-mobile">
                <BarChart2Icon className="mr-1.5 h-4 w-4" />
                Stats
                <span
                  data-testid="badge-beta"
                  className="text-[10px] font-semibold uppercase tracking-wide bg-amber-500/15 text-amber-600 dark:text-amber-400 px-1.5 py-0.5 rounded-full ml-1.5"
                >
                  Beta
                </span>
              </TabsTrigger>
              <TabsTrigger value="games" className="flex-1" data-testid="tab-games-mobile">
                <Gamepad2Icon className="mr-1.5 h-4 w-4" />
                Games
              </TabsTrigger>
            </TabsList>

            <TabsContent value="stats" className="mt-4">
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
