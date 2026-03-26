import { useState, useCallback } from 'react';
import { useNavigate, useLocation, Navigate, Link } from 'react-router-dom';
import { ChevronUp, ChevronDown, BarChart2Icon, Gamepad2Icon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import { EndgameWDLChart } from '@/components/charts/EndgameWDLChart';
import { useEndgameStats } from '@/hooks/useEndgames';
import { useDebounce } from '@/hooks/useDebounce';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { TimeControl, Platform, OpponentType, Recency } from '@/types/api';
import type { EndgameClass } from '@/types/endgames';

const PAGE_SIZE = 20;

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

  // ── Collapsible state ────────────────────────────────────────────────────────
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(false);
  const [moreFiltersMobileOpen, setMoreFiltersMobileOpen] = useState(false);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // ── Data ─────────────────────────────────────────────────────────────────────
  const { data: statsData, isLoading: statsLoading } = useEndgameStats(debouncedFilters);

  // ── Filter handlers ───────────────────────────────────────────────────────────

  const update = useCallback((partial: Partial<FilterState>) => {
    setFilters((prev) => ({ ...prev, ...partial }));
    setGamesOffset(0); // D-03: reset pagination on filter change
  }, []);

  const toggleTimeControl = useCallback((tc: TimeControl) => {
    const current = filters.timeControls ?? TIME_CONTROLS;
    if (current.includes(tc)) {
      const next = current.filter((t) => t !== tc);
      update({ timeControls: next.length === TIME_CONTROLS.length ? null : next.length === 0 ? [tc] : next });
    } else {
      const next = [...current, tc];
      update({ timeControls: next.length === TIME_CONTROLS.length ? null : next });
    }
  }, [filters.timeControls, update]);

  const isTimeControlActive = (tc: TimeControl) => {
    if (filters.timeControls === null) return true;
    return filters.timeControls.includes(tc);
  };

  const togglePlatform = useCallback((p: Platform) => {
    const current = filters.platforms ?? PLATFORMS;
    if (current.includes(p)) {
      const next = current.filter((x) => x !== p);
      update({ platforms: next.length === PLATFORMS.length ? null : next.length === 0 ? [p] : next });
    } else {
      const next = [...current, p];
      update({ platforms: next.length === PLATFORMS.length ? null : next });
    }
  }, [filters.platforms, update]);

  const isPlatformActive = (p: Platform) => {
    if (filters.platforms === null) return true;
    return filters.platforms.includes(p);
  };

  // ── Category click handler ────────────────────────────────────────────────────

  const handleCategoryClick = useCallback((category: EndgameClass) => {
    // Clicking the same row deselects it
    setSelectedCategory((prev) => (prev === category ? null : category));
  }, []);

  // ── Filter panel content (Time Control, Platform, Recency) ───────────────────

  const mainFilterContent = (
    <div className="space-y-3">
      {/* Time Control */}
      <div>
        <p className="mb-1 text-xs text-muted-foreground">Time control</p>
        <div className="flex flex-wrap gap-1">
          {TIME_CONTROLS.map((tc) => (
            <button
              key={tc}
              onClick={() => toggleTimeControl(tc)}
              data-testid={`filter-time-control-${tc}`}
              aria-label={`${TIME_CONTROL_LABELS[tc]} time control`}
              aria-pressed={isTimeControlActive(tc)}
              className={
                'rounded border px-3 h-11 sm:h-7 sm:px-2 text-xs transition-colors ' +
                (isTimeControlActive(tc)
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-transparent text-muted-foreground hover:border-foreground hover:text-foreground')
              }
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
              data-testid={`filter-platform-${p === 'chess.com' ? 'chess-com' : p}`}
              aria-label={`${PLATFORM_LABELS[p]} platform`}
              aria-pressed={isPlatformActive(p)}
              className={
                'rounded border px-3 h-11 sm:h-7 sm:px-2 text-xs transition-colors ' +
                (isPlatformActive(p)
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-transparent text-muted-foreground hover:border-foreground hover:text-foreground')
              }
            >
              {PLATFORM_LABELS[p]}
            </button>
          ))}
        </div>
      </div>

      {/* Recency */}
      <div>
        <p className="mb-1 text-xs text-muted-foreground">Recency</p>
        <Select
          value={filters.recency ?? 'all'}
          onValueChange={(v) => update({ recency: v === 'all' ? null : (v as Recency) })}
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
    </div>
  );

  // ── More filters content (Rated, Opponent Type) ───────────────────────────────

  const moreFilterContent = (
    <div className="space-y-3">
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
          data-testid="filter-rated"
        >
          <ToggleGroupItem value="all" data-testid="filter-rated-all" className="min-h-11 sm:min-h-0">All</ToggleGroupItem>
          <ToggleGroupItem value="rated" data-testid="filter-rated-rated" className="min-h-11 sm:min-h-0">Rated</ToggleGroupItem>
          <ToggleGroupItem value="casual" data-testid="filter-rated-casual" className="min-h-11 sm:min-h-0">Casual</ToggleGroupItem>
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
          data-testid="filter-opponent"
        >
          <ToggleGroupItem value="human" data-testid="filter-opponent-human" className="min-h-11 sm:min-h-0">Human</ToggleGroupItem>
          <ToggleGroupItem value="bot" data-testid="filter-opponent-bot" className="min-h-11 sm:min-h-0">Bot</ToggleGroupItem>
          <ToggleGroupItem value="both" data-testid="filter-opponent-both" className="min-h-11 sm:min-h-0">Both</ToggleGroupItem>
        </ToggleGroup>
      </div>
    </div>
  );

  // ── Statistics tab content ───────────────────────────────────────────────────

  const statisticsContent = (
    <div className="flex flex-col gap-4">
      {statsLoading ? (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading endgame statistics...</p>
        </div>
      ) : statsData && statsData.categories.length > 0 ? (
        <EndgameWDLChart
          categories={statsData.categories}
          selectedCategory={selectedCategory}
          onCategoryClick={handleCategoryClick}
        />
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

  // ── Games tab content (placeholder — Plan 03 will wire GameCardList) ─────────

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
      ) : (
        <div>
          {selectedLabel && (
            <p className="text-sm font-medium mb-3">{selectedLabel} Endgames</p>
          )}
          {/* Games list placeholder — Plan 03 will implement GameCardList integration */}
          <p className="text-sm text-muted-foreground">
            Games list coming in Plan 03. Offset: {gamesOffset}, limit: {PAGE_SIZE}.
          </p>
        </div>
      )}
    </div>
  );

  // ── Desktop sidebar ──────────────────────────────────────────────────────────

  const desktopSidebar = (
    <div className="flex flex-col gap-2 min-w-0">
      {mainFilterContent}

      <div className="border-t border-border/40" />

      {/* More filters collapsible (Rated, Opponent Type) */}
      <Collapsible open={moreFiltersOpen} onOpenChange={setMoreFiltersOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-between px-2 text-sm font-medium bg-muted/50 hover:bg-muted! border border-border/40 rounded min-h-11 sm:min-h-0"
            data-testid="section-more-filters"
          >
            More filters
            {moreFiltersOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="pt-2">
            {moreFilterContent}
          </div>
        </CollapsibleContent>
      </Collapsible>
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
          <div className="min-w-0">{desktopSidebar}</div>
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
                {mainFilterContent}
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* More filters collapsible */}
          <Collapsible open={moreFiltersMobileOpen} onOpenChange={setMoreFiltersMobileOpen}>
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-between px-2 text-sm font-medium bg-muted/50 hover:bg-muted! border border-border/40 rounded min-h-11 sm:min-h-0"
                data-testid="section-more-filters-mobile"
              >
                More filters
                {moreFiltersMobileOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="pt-2">
                {moreFilterContent}
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
