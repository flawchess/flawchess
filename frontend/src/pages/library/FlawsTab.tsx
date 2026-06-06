import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ExternalLink, SlidersHorizontal, Tags, X } from 'lucide-react';
import { SidebarLayout } from '@/components/layout/SidebarLayout';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import {
  DEFAULT_FILTERS,
  areFiltersEqual,
  FILTER_DOT_FIELDS,
} from '@/components/filters/FilterPanel';
import { LibraryFilterPanel } from '@/components/filters/LibraryFilterPanel';
import { FlawFilterControl } from '@/components/filters/FlawFilterControl';
import { usePulseOnChange, ModifiedDot } from '@/components/filters/FilterModifiedDot';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { SeverityBadge } from '@/components/library/SeverityBadge';
import { TagChip } from '@/components/library/TagChip';
import { Pagination } from '@/components/results/Pagination';
import { useFilterStore } from '@/hooks/useFilterStore';
import {
  useFlawFilterStore,
  DEFAULT_FLAW_FILTER,
  isFlawFilterNonDefault,
} from '@/hooks/useFlawFilterStore';
import { useLibraryFlaws } from '@/hooks/useLibrary';
import { useUserProfile } from '@/hooks/useUserProfile';
import { sanToSquares } from '@/lib/sanToSquares';
import { flawPlyUrl, supportsPlyDeepLink } from '@/lib/platformLinks';
import { SEV_BLUNDER } from '@/lib/theme';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';
import type { FlawListItem, FlawTag } from '@/types/library';

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;
const MINI_BOARD_SIZE = 80;

// ─── Flaw Row ─────────────────────────────────────────────────────────────────

/**
 * One row in the flaw list: miniboard + severity badge + tags + game metadata.
 */
function FlawRow({ flaw }: { flaw: FlawListItem }) {
  const flipped = flaw.user_color === 'black';

  // Mark the flawed move on the miniboard. `flaw.fen` is the pre-move position as
  // board_fen() (piece placement only — no side-to-move/castling, per CLAUDE.md).
  // chess.js needs a full FEN, so augment with the side to move (the flaw is the
  // user's move → user_color) and unknown castling/en-passant ("-"). Normal moves
  // resolve to from/to squares; castling/en-passant fall back to null (no arrow).
  // Blunder-red from theme.ts (never hard-code semantic colors).
  const sideToMove = flaw.user_color === 'black' ? 'b' : 'w';
  const moveSquares = flaw.move_san
    ? sanToSquares(`${flaw.fen} ${sideToMove} - - 0 1`, flaw.move_san)
    : null;

  // Format date as YYYY-MM-DD
  const dateLabel = flaw.played_at
    ? new Date(flaw.played_at).toLocaleDateString('en-CA')
    : null;

  // Opponent label
  const opponent = flipped
    ? (flaw.white_username ?? 'Unknown')
    : (flaw.black_username ?? 'Unknown');

  // Platform icon + external link to the flaw position, mirroring LibraryGameCard.
  // Both platforms deep-link to the exact ply — lichess via a #{ply} fragment,
  // chess.com via the analysis board's ?move= param (see lib/platformLinks.ts).
  const flawUrl = flawPlyUrl(flaw.platform, flaw.platform_url, flaw.ply, flaw.user_color);
  const linkTooltip = supportsPlyDeepLink(flaw.platform)
    ? 'Open at this move on platform'
    : 'Open game on platform';
  const platformIconAndLink = (
    <span className="inline-flex items-center gap-1.5 text-muted-foreground">
      <PlatformIcon platform={flaw.platform} className="h-4 w-4" />
      {flawUrl ? (
        <Tooltip content={linkTooltip}>
          <a
            href={flawUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
            aria-label={linkTooltip}
            data-testid={`flaw-card-link-${flaw.game_id}-${flaw.ply}`}
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </Tooltip>
      ) : null}
    </span>
  );

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-3 rounded-lg border border-border/60 bg-card/40">
      {/* Miniboard */}
      <LazyMiniBoard
        fen={flaw.fen}
        flipped={flipped}
        size={MINI_BOARD_SIZE}
        arrows={
          moveSquares
            ? [{ from: moveSquares.from, to: moveSquares.to, color: SEV_BLUNDER }]
            : undefined
        }
      />

      {/* Main content */}
      <div className="flex flex-col gap-1.5 min-w-0 flex-1">
        {/* Severity badge + tags row */}
        <div className="flex flex-wrap items-center gap-1.5">
          <SeverityBadge severity={flaw.severity} count={1} gameId={flaw.game_id} />
          {flaw.tags.map((tag) => (
            <TagChip key={tag} tag={tag} gameId={flaw.game_id} />
          ))}
        </div>

        {/* Move SAN if available */}
        {flaw.move_san && (
          <p className="text-sm font-bold text-foreground">
            Move {Math.ceil(flaw.ply / 2)}: {flaw.move_san}
          </p>
        )}

        {/* Game metadata */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm text-muted-foreground">
          <span>vs {opponent}</span>
          {dateLabel && <span>{dateLabel}</span>}
          {flaw.time_control_bucket && <span>{flaw.time_control_bucket}</span>}
          <span className="capitalize">{flaw.user_result}</span>
          {platformIconAndLink}
        </div>
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * FlawsTab — the Library Flaws subtab root.
 *
 * Composes two separate filter panels — "Filters" (game metadata, LibraryFilterPanel
 * with showFlawFilter=false) and "Flaw filters" (severity + tags, FlawFilterControl) —
 * + per-flaw miniboard list + Pagination, wiring useLibraryFlaws to the shared stores.
 *
 * URL sync (D-04): on mount, reads ?tag=&severity= from URL and initializes the
 * flaw filter store from them (only when params are present). On store change,
 * updates URL via replace-state (no history pollution).
 *
 * Desktop layout: SidebarLayout with two strip panels (game filters + flaw filters),
 * both applying live on change.
 * Mobile layout: two sticky buttons, each opening its own right Drawer; both apply on
 * close (the flaw filter buffers edits in pendingFlawFilter until its drawer closes).
 */
export function FlawsTab() {
  // ── URL sync setup ───────────────────────────────────────────────────────────
  const [searchParams, setSearchParams] = useSearchParams();

  // ── Filter state ─────────────────────────────────────────────────────────────
  const [appliedFilters, setAppliedFilters] = useFilterStore();
  const [pendingFilters, setPendingFilters] = useState<FilterState>(appliedFilters);

  // Sync pending -> applied when the filter store changes from another page/tab
  useEffect(() => {
    setPendingFilters(appliedFilters);
  }, [appliedFilters]);

  // ── Flaw filter (shared, URL-synced on this tab) ──────────────────────────────
  const [flawFilter, setFlawFilter] = useFlawFilterStore();

  // Mount: read URL params → initialize store (only when URL has params — D-04/OQ3)
  // Do not overwrite existing in-memory selection on plain navigation without params.
  // Using ref to capture the initial URL params at mount time only, so we don't
  // re-run on every searchParams change (which would fight with the URL-sync effect below).
  const didInitFromUrl = useRef(false);
  const initialSearchParams = useRef(searchParams);
  useEffect(() => {
    if (didInitFromUrl.current) return;
    didInitFromUrl.current = true;

    const urlTags = initialSearchParams.current.getAll('tag') as FlawTag[];
    const urlSeverity = initialSearchParams.current.getAll('severity') as ('blunder' | 'mistake')[];

    if (urlTags.length > 0 || urlSeverity.length > 0) {
      setFlawFilter({
        tags: urlTags,
        severity: urlSeverity.length > 0 ? urlSeverity : ['blunder', 'mistake'],
      });
    }
  }, [setFlawFilter]);

  // Store change → update URL (replace, not push — avoids polluting history)
  useEffect(() => {
    const params = new URLSearchParams();
    flawFilter.tags.forEach((t) => params.append('tag', t));
    // Only include severity in URL when not both (clean URL for default state)
    if (flawFilter.severity.length < 2) {
      flawFilter.severity.forEach((s) => params.append('severity', s));
    }
    setSearchParams(params, { replace: true });
  }, [flawFilter, setSearchParams]);

  // ── Pending flaw filter (mobile drawer buffer) ────────────────────────────────
  // Desktop applies the flaw filter live (writes the store on each toggle); the
  // mobile drawer instead buffers edits here and commits them to the store when the
  // drawer closes (apply-on-close), matching the game-metadata drawer behavior.
  const [pendingFlawFilter, setPendingFlawFilter] = useState<FlawFilterState>(flawFilter);

  // Keep the pending buffer fresh whenever the committed store changes (desktop live
  // edits, URL deep-link init, cross-tab sync) so the next mobile drawer open starts
  // from the current selection.
  useEffect(() => {
    setPendingFlawFilter(flawFilter);
  }, [flawFilter]);

  // ── Pagination state ─────────────────────────────────────────────────────────
  const [offset, setOffset] = useState(0);

  // Desktop (live) clear — commits default to the store immediately.
  const handleFlawFilterClear = useCallback(() => {
    setFlawFilter(DEFAULT_FLAW_FILTER);
    setOffset(0);
  }, [setFlawFilter]);

  // ── Mobile drawer state ──────────────────────────────────────────────────────
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [mobileFlawFiltersOpen, setMobileFlawFiltersOpen] = useState(false);

  // ── Desktop sidebar state ────────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState<string | null>(null);

  // ── Modified-filters indicators (one per panel) ───────────────────────────────
  const isGameModified = useMemo(
    () => !areFiltersEqual(appliedFilters, DEFAULT_FILTERS, FILTER_DOT_FIELDS),
    [appliedFilters],
  );
  const isFlawModified = useMemo(() => isFlawFilterNonDefault(flawFilter), [flawFilter]);

  const gamePulsing = usePulseOnChange(appliedFilters);
  const flawPulsing = usePulseOnChange(flawFilter);

  const gameDotNode = (
    <ModifiedDot active={isGameModified} pulsing={gamePulsing} testId="filters-modified-dot-flaws" />
  );
  const flawDotNode = (
    <ModifiedDot active={isFlawModified} pulsing={flawPulsing} testId="flaw-filters-modified-dot" />
  );

  // ── Handlers for game-metadata filters ───────────────────────────────────────

  // Desktop sidebar: defers game-metadata apply until the panel closes. The flaw
  // panel applies live, so it needs no pending-buffer handling here.
  const handleSidebarOpenChange = useCallback(
    (panelId: string | null) => {
      if (sidebarOpen === 'filters' && panelId !== 'filters') {
        setAppliedFilters(pendingFilters);
        setOffset(0);
      }
      if (sidebarOpen !== 'filters' && panelId === 'filters') {
        setPendingFilters(appliedFilters);
      }
      setSidebarOpen(panelId);
    },
    [sidebarOpen, pendingFilters, appliedFilters, setAppliedFilters],
  );

  // Mobile game-filters drawer: defers apply until the drawer closes.
  const handleMobileFiltersOpenChange = useCallback(
    (open: boolean) => {
      if (!open && mobileFiltersOpen) {
        setAppliedFilters(pendingFilters);
        setOffset(0);
      }
      if (open && !mobileFiltersOpen) {
        setPendingFilters(appliedFilters);
      }
      setMobileFiltersOpen(open);
    },
    [mobileFiltersOpen, pendingFilters, appliedFilters, setAppliedFilters],
  );

  // Mobile flaw-filters drawer: buffers edits in pendingFlawFilter and commits them
  // to the store on close (apply-on-close), so tag/severity selections take effect
  // when the panel closes rather than mid-edit.
  const handleMobileFlawFiltersOpenChange = useCallback(
    (open: boolean) => {
      if (!open && mobileFlawFiltersOpen) {
        setFlawFilter(pendingFlawFilter);
        setOffset(0);
      }
      if (open && !mobileFlawFiltersOpen) {
        setPendingFlawFilter(flawFilter);
      }
      setMobileFlawFiltersOpen(open);
    },
    [mobileFlawFiltersOpen, pendingFlawFilter, flawFilter, setFlawFilter],
  );

  // ── Data queries ─────────────────────────────────────────────────────────────
  const {
    data: flawsData,
    isLoading: flawsLoading,
    isError: flawsError,
  } = useLibraryFlaws(appliedFilters, flawFilter, offset, PAGE_SIZE);

  // User's total imported games
  const { data: profile } = useUserProfile();
  const totalImported =
    profile != null ? profile.chess_com_game_count + profile.lichess_game_count : 0;

  // ── Derived state ────────────────────────────────────────────────────────────
  const totalGames = totalImported;
  const matchedCount = flawsData?.matched_count ?? 0;
  const flaws = flawsData?.flaws ?? [];

  // No games at all for this user
  const noGamesImported = !flawsLoading && !flawsError && totalGames === 0;
  // Games exist but none are analyzed (no flaws in DB at all — inferred from matched_count=0 + no error)
  const noAnalyzedGames = !flawsLoading && !flawsError && totalGames > 0 && matchedCount === 0 && flawsData != null;
  // Filter matched nothing (we cannot distinguish "no analyzed games" from "filter matched nothing"
  // without an extra endpoint, so we use the simpler copy as the primary empty state)
  const noMatchedFlaws = noAnalyzedGames;

  // ── Filter panel content ─────────────────────────────────────────────────────

  // Game-metadata panel (no flaw control — it lives in its own panel below).
  const gameFilterPanelContent = (
    <div className="p-4">
      <LibraryFilterPanel
        filters={pendingFilters}
        onChange={(filters) => {
          setPendingFilters(filters);
          // Desktop live apply
          setAppliedFilters(filters);
          setOffset(0);
        }}
        showFlawFilter={false}
      />
    </div>
  );

  // Flaw-filter panel (severity + tags). Desktop applies live to the store.
  const flawFilterPanelContent = (
    <div className="p-4">
      <FlawFilterControl
        severity={flawFilter.severity}
        tags={flawFilter.tags}
        onSeverityChange={(severity) => {
          setFlawFilter({ ...flawFilter, severity });
          setOffset(0);
        }}
        onTagChange={(tags) => {
          setFlawFilter({ ...flawFilter, tags });
          setOffset(0);
        }}
        onClear={handleFlawFilterClear}
      />
    </div>
  );

  const sidebarPanels = [
    {
      id: 'filters',
      label: 'Filters',
      icon: <SlidersHorizontal className="h-4 w-4" />,
      content: gameFilterPanelContent,
      notificationDot: gameDotNode,
    },
    {
      id: 'flaw-filters',
      label: 'Flaw filters',
      icon: <Tags className="h-4 w-4" />,
      content: flawFilterPanelContent,
      notificationDot: flawDotNode,
    },
  ];

  // ── Main content ─────────────────────────────────────────────────────────────

  const mainContent = (
    <div className="flex flex-col gap-6">
      {/* Error state — MANDATORY isError branch (CLAUDE.md) */}
      {flawsError && (
        <p className="text-sm text-muted-foreground">
          Failed to load flaws. Something went wrong. Please try again in a moment.
        </p>
      )}

      {/* No games imported empty state */}
      {noGamesImported && (
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <p className="text-base font-bold">No games imported yet</p>
          <p className="text-sm text-muted-foreground">
            Import your games from chess.com or lichess to start analyzing.
          </p>
          <Button asChild variant="default" size="sm">
            <Link to="/library/import">Import Games</Link>
          </Button>
        </div>
      )}

      {/* Flaw list — only when not errored */}
      {!flawsError && (
        <section aria-label="Flaw results" data-testid="flaw-list">
          {/* Matched count row */}
          {flawsData != null && (
            <p className="text-sm text-muted-foreground mb-4">
              {matchedCount} flaw{matchedCount === 1 ? '' : 's'} matched
            </p>
          )}

          {/* Empty: no flaws matched */}
          {noMatchedFlaws && (
            <div className="flex flex-col items-center gap-2 py-8 text-center">
              <p className="text-base font-bold">No flaws matched</p>
              <p className="text-sm text-muted-foreground">
                Try adjusting the flaw filter or game filters.
              </p>
            </div>
          )}

          {/* Flaw rows */}
          {matchedCount > 0 && (
            <div className="flex flex-col gap-3">
              {flaws.map((flaw) => (
                <FlawRow key={`${flaw.game_id}-${flaw.ply}`} flaw={flaw} />
              ))}
            </div>
          )}

          {/* Pagination */}
          {matchedCount > PAGE_SIZE && (
            <div className="mt-6">
              <Pagination
                currentPage={Math.floor(offset / PAGE_SIZE) + 1}
                totalPages={Math.ceil(matchedCount / PAGE_SIZE)}
                onPageChange={(page) => {
                  setOffset((page - 1) * PAGE_SIZE);
                  window.scrollTo({ top: 0 });
                }}
              />
            </div>
          )}
        </section>
      )}
    </div>
  );

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div data-testid="flaws-tab-content">
      {/* Desktop layout: SidebarLayout */}
      <SidebarLayout
        panels={sidebarPanels}
        activePanel={sidebarOpen}
        onActivePanelChange={handleSidebarOpenChange}
      >
        {mainContent}
      </SidebarLayout>

      {/* Mobile layout: sticky filter buttons + Drawers + stacked content */}
      <div className="md:hidden flex flex-col gap-4">
        {/* Sticky row with separate Filters + Flaw filters buttons */}
        <div className="sticky top-0 z-20 flex justify-end gap-2 py-2 bg-background/80 backdrop-blur-sm">
          <Button
            variant="brand-outline"
            className="relative"
            onClick={() => setMobileFiltersOpen(true)}
            aria-label="Open game filters"
            data-testid="btn-game-filters"
          >
            <SlidersHorizontal className="mr-2 h-4 w-4" />
            Filters
            {gameDotNode}
          </Button>
          <Button
            variant="brand-outline"
            className="relative"
            onClick={() => setMobileFlawFiltersOpen(true)}
            aria-label="Open flaw filters"
            data-testid="btn-flaw-filters"
          >
            <Tags className="mr-2 h-4 w-4" />
            Flaw filters
            {flawDotNode}
          </Button>
        </div>

        {/* Game-filters drawer */}
        <Drawer
          open={mobileFiltersOpen}
          onOpenChange={handleMobileFiltersOpenChange}
          direction="right"
        >
          <DrawerContent
            className="!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[85vh]"
            data-testid="drawer-game-filter-sidebar"
          >
            <DrawerHeader className="flex flex-row items-center justify-between">
              <DrawerTitle>Filters</DrawerTitle>
              <DrawerClose asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Close game filters"
                  data-testid="btn-close-game-filter-drawer"
                >
                  <X className="h-4 w-4" />
                </Button>
              </DrawerClose>
            </DrawerHeader>
            <div className="overflow-y-auto flex-1 p-4">
              <LibraryFilterPanel
                filters={pendingFilters}
                onChange={setPendingFilters}
                showFlawFilter={false}
                showDeferredApplyHint
              />
            </div>
          </DrawerContent>
        </Drawer>

        {/* Flaw-filters drawer — applies on close (apply-on-close buffer) */}
        <Drawer
          open={mobileFlawFiltersOpen}
          onOpenChange={handleMobileFlawFiltersOpenChange}
          direction="right"
        >
          <DrawerContent
            className="!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[85vh]"
            data-testid="drawer-flaw-filter-sidebar"
          >
            <DrawerHeader className="flex flex-row items-center justify-between">
              <DrawerTitle>Flaw filters</DrawerTitle>
              <DrawerClose asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Close flaw filters"
                  data-testid="btn-close-flaw-filter-drawer"
                >
                  <X className="h-4 w-4" />
                </Button>
              </DrawerClose>
            </DrawerHeader>
            <div className="overflow-y-auto flex-1 p-4 space-y-3">
              <FlawFilterControl
                severity={pendingFlawFilter.severity}
                tags={pendingFlawFilter.tags}
                onSeverityChange={(severity) =>
                  setPendingFlawFilter({ ...pendingFlawFilter, severity })
                }
                onTagChange={(tags) => setPendingFlawFilter({ ...pendingFlawFilter, tags })}
                onClear={() => setPendingFlawFilter(DEFAULT_FLAW_FILTER)}
              />
              <p
                className="text-sm italic leading-tight text-muted-foreground"
                data-testid="flaw-filter-deferred-apply-hint"
              >
                <span className="font-semibold text-foreground/80">Tip:</span> Filter changes apply
                on closing the filters panel.
              </p>
            </div>
          </DrawerContent>
        </Drawer>

        {/* Stacked main content (mobile) */}
        {mainContent}
      </div>
    </div>
  );
}
