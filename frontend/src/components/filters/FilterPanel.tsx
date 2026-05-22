import { useState, useEffect, useRef } from 'react';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Popover, PopoverAnchor } from '@/components/ui/popover';
import type { MatchSide, TimeControl, RecencyPreset, Color, Platform, OpponentType, OpponentStrengthRange } from '@/types/api';
import { cn } from '@/lib/utils';
import { ANY_RANGE } from '@/lib/opponentStrength';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { TimeControlIcon } from '@/components/icons/TimeControlIcon';
import { Button } from '@/components/ui/button';
import { OpponentStrengthFilter } from './OpponentStrengthFilter';
import { CustomRangePopover, formatCustomRangeLabel } from './CustomRangePopover';
import { CustomRangeDrawer } from './CustomRangeDrawer';

// ─── Mobile breakpoint detection ──────────────────────────────────────────────
// Same threshold as ScoreChart.tsx (768px = Tailwind `md`).
const MOBILE_BREAKPOINT_PX = 768;

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined'
      && window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

export interface FilterState {
  matchSide: MatchSide;
  timeControls: TimeControl[] | null; // null = all
  platforms: Platform[] | null; // null = all
  rated: boolean | null; // null = all
  opponentType: OpponentType; // default human = computer games excluded
  /**
   * Opponent strength as a (gap_min, gap_max) range over opponent_rating - user_rating.
   * Default `{ min: null, max: null }` = no filter (Any preset).
   */
  opponentStrength: OpponentStrengthRange;
  recency: RecencyPreset | 'custom' | null; // null = all time; 'custom' = look at customRange
  /** Custom date range set by the user. Non-null only when recency === 'custom'. */
  customRange: { from?: Date; to?: Date } | null;
  color: Color;
}

// eslint-disable-next-line react-refresh/only-export-components
export const DEFAULT_FILTERS: FilterState = {
  matchSide: 'both',
  timeControls: null,
  platforms: null,
  rated: null,
  opponentType: 'human',
  opponentStrength: ANY_RANGE,
  recency: null,
  customRange: null,
  color: 'white',
};

/**
 * FilterState keys used to compute the "modified filters" dot across all three pages
 * (Openings, Endgames, GlobalStats). Intentionally EXCLUDES `color` — changing
 * Played-as does not light the dot because the user's current piece color is not
 * considered part of "the filter query" for indicator purposes, and Reset preserves
 * it for the same reason.
 */
export const FILTER_DOT_FIELDS: ReadonlyArray<keyof FilterState> = [
  'matchSide',
  'timeControls',
  'platforms',
  'rated',
  'opponentType',
  'opponentStrength',
  'recency',
  'customRange',
] as const;

/**
 * Compare two FilterState values for equality, treating array fields (timeControls, platforms)
 * as set-equal regardless of order. Used to detect "filters are modified from defaults" for
 * the sidebar modified-indicator dot.
 *
 * If `fields` is provided, only those FilterState keys are compared — used by GlobalStats
 * which only exposes platform + recency (other fields must be ignored even if non-default).
 */
// eslint-disable-next-line react-refresh/only-export-components
export function areFiltersEqual(
  a: FilterState,
  b: FilterState,
  fields?: ReadonlyArray<keyof FilterState>,
): boolean {
  const keys = fields ?? (Object.keys(a) as (keyof FilterState)[]);
  for (const key of keys) {
    const av = a[key];
    const bv = b[key];
    if (av === bv) continue;
    // Both null already handled by === above; handle array set-equality
    if (Array.isArray(av) && Array.isArray(bv)) {
      if (av.length !== bv.length) return false;
      const setB = new Set<string>(bv as readonly string[]);
      if (!(av as readonly string[]).every((v) => setB.has(v))) return false;
      continue;
    }
    // opponentStrength is an object-shaped field; compare structurally.
    if (key === 'opponentStrength') {
      const ar = av as OpponentStrengthRange;
      const br = bv as OpponentStrengthRange;
      if (ar.min === br.min && ar.max === br.max) continue;
      return false;
    }
    // customRange is an object-shaped field; compare by Date.getTime() to avoid
    // reference-equality mismatches when the same range is reconstructed.
    if (key === 'customRange') {
      const ar = av as FilterState['customRange'];
      const br = bv as FilterState['customRange'];
      if (ar === null && br === null) continue;
      if (ar === null || br === null) return false;
      if (ar.from?.getTime() === br.from?.getTime() && ar.to?.getTime() === br.to?.getTime()) continue;
      return false;
    }
    return false;
  }
  return true;
}

type FilterField = 'timeControl' | 'platform' | 'rated' | 'opponent' | 'opponentStrength' | 'recency';

interface FilterPanelProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  /** Which filter sections to show. Defaults to all. */
  visibleFilters?: FilterField[];
  /** When true, shows a muted helper line below the Reset button explaining deferred apply. */
  showDeferredApplyHint?: boolean;
}

const ALL_FILTERS: FilterField[] = ['timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency'];

const TIME_CONTROLS: TimeControl[] = ['bullet', 'blitz', 'rapid', 'classical'];
const TIME_CONTROL_LABELS: Record<TimeControl, string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classic',
};

const PLATFORMS: Platform[] = ['chess.com', 'lichess'];
const PLATFORM_LABELS: Record<Platform, string> = {
  'chess.com': 'Chess.com',
  lichess: 'Lichess',
};

export function FilterPanel({
  filters,
  onChange,
  visibleFilters = ALL_FILTERS,
  showDeferredApplyHint = false,
}: FilterPanelProps) {
  const update = (partial: Partial<FilterState>) => {
    onChange({ ...filters, ...partial });
  };

  // Custom range popover/drawer state.
  const [customOpen, setCustomOpen] = useState(false);
  // Tracks a pending "custom" pick so we can suppress Select's restore-focus on
  // close — otherwise focus snaps back to the SelectTrigger right after the
  // popover opens, and the popover's focusOutside dismiss closes it (UAT bug:
  // calendar flashed open then disappeared).
  const pendingCustomRef = useRef(false);
  // In-progress custom-range edits live here while the popover is open; they
  // are committed to the filter only when the popover closes (Done button,
  // outside click, or Escape).
  const [pendingCustomRange, setPendingCustomRange] = useState<{ from?: Date; to?: Date } | null>(
    filters.customRange,
  );
  // Sync pending → committed each time the popover opens (and on external
  // changes like Reset Filters). Derive-during-render avoids the useEffect
  // cascade.
  const [prevCustomOpen, setPrevCustomOpen] = useState(customOpen);
  if (prevCustomOpen !== customOpen) {
    setPrevCustomOpen(customOpen);
    if (customOpen) setPendingCustomRange(filters.customRange);
  }
  // Single handler for both Radix-driven dismiss (outside click, Escape) and
  // explicit Done click. Radix Popover only fires onOpenChange on internal
  // dismisses; setting `open=false` externally would skip the commit, so we
  // route Done through here too.
  const handleCustomOpenChange = (open: boolean) => {
    if (!open && customOpen) {
      // Closing — commit pendingCustomRange. Empty edit reverts recency.
      if (pendingCustomRange?.from || pendingCustomRange?.to) {
        update({ recency: 'custom', customRange: pendingCustomRange });
      } else {
        update({ recency: null, customRange: null });
      }
    }
    setCustomOpen(open);
  };
  const isMobile = useIsMobile();

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

  const show = (field: FilterField) => visibleFilters.includes(field);

  return (
    <div className="space-y-3">
      {/* Recency */}
      {show('recency') && (
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Recency</p>
          {/*
            Desktop: Popover anchored to the Select trigger via PopoverAnchor asChild (D-03).
            Mobile:  Popover is never open; CustomRangeDrawer handles the nested sheet (D-06).
            queueMicrotask defers setCustomOpen so the Select close animation completes
            before the popover/drawer open animation begins (RESEARCH.md §Pitfall 6).
          */}
          <Popover
            open={customOpen && !isMobile}
            onOpenChange={handleCustomOpenChange}
          >
            <Select
              value={filters.recency === 'custom' ? 'custom' : (filters.recency ?? 'all')}
              onValueChange={(v) => {
                // 'custom' is handled by the SelectItem's onClick below so that
                // re-clicking "custom" while it's already the active value
                // still reopens the calendar (Radix Select doesn't fire
                // onValueChange when the value is unchanged).
                if (v !== 'custom') {
                  // Any preset clears the custom range (D-08).
                  update({ recency: v === 'all' ? null : (v as RecencyPreset), customRange: null });
                }
              }}
            >
              {/*
                PopoverAnchor must wrap a real DOM element. Select Root is a virtual
                Radix primitive (no DOM) — wrapping it leaves the anchor ref null and
                the popover gets no positioning reference (off-screen/zero-rect).
                Anchor the SelectTrigger (<button>) instead.
              */}
              <PopoverAnchor asChild>
                <SelectTrigger size="sm" data-testid="filter-recency" className="min-h-11 sm:min-h-0 w-full">
                  {/* Render resolved range label when custom is active (D-04); preset label otherwise. */}
                  {filters.recency === 'custom'
                    ? formatCustomRangeLabel(filters.customRange)
                    : <SelectValue />}
                </SelectTrigger>
              </PopoverAnchor>
              <SelectContent
                // position="popper" anchors the menu below the trigger. The
                // default "item-aligned" mode aligns the *selected* item with
                // the trigger, so once "custom" (last item) is selected the
                // menu opens upward and shifted left next time.
                position="popper"
                onCloseAutoFocus={(e) => {
                  // When the user picked "custom", suppress Select's focus
                  // restore so it doesn't steal focus from the about-to-open
                  // popover and trigger Radix's focusOutside dismiss.
                  if (pendingCustomRef.current) {
                    e.preventDefault();
                    pendingCustomRef.current = false;
                  }
                }}
              >
                <SelectItem value="all">All time</SelectItem>
                <SelectItem value="week">Past week</SelectItem>
                <SelectItem value="month">Past month</SelectItem>
                <SelectItem value="3months">3 months</SelectItem>
                <SelectItem value="6months">6 months</SelectItem>
                <SelectItem value="year">1 year</SelectItem>
                <SelectItem value="3years">3 years</SelectItem>
                <SelectItem value="5years">5 years</SelectItem>
                <SelectItem
                  value="custom"
                  data-testid="filter-recency-custom"
                  // Radix triggers selection on pointerup for mouse and on
                  // click for keyboard/touch — and unmounts the item once
                  // selection runs, so onClick alone misses mouse clicks.
                  // Hook both to cover every input type. Idempotent: setting
                  // the same state twice is a no-op.
                  onPointerUp={() => {
                    pendingCustomRef.current = true;
                    queueMicrotask(() => setCustomOpen(true));
                  }}
                  onClick={() => {
                    pendingCustomRef.current = true;
                    queueMicrotask(() => setCustomOpen(true));
                  }}
                >
                  Custom range…
                </SelectItem>
              </SelectContent>
            </Select>

            {/* Desktop: Calendar in a Popover anchored to the Select trigger.
                Edits pendingCustomRange only; commit happens via
                handleCustomOpenChange — used for both Radix dismiss paths and
                the Done button below. */}
            <CustomRangePopover
              value={pendingCustomRange}
              onChange={setPendingCustomRange}
              onOpenChange={handleCustomOpenChange}
            />
          </Popover>

          {/* Mobile: Calendar in a nested Drawer layered over the FilterPanel drawer.
              The drawer handles its own close via onOpenChange after Apply. */}
          <CustomRangeDrawer
            value={filters.customRange}
            onChange={(range) => {
              if (range) update({ recency: 'custom', customRange: range });
            }}
            open={customOpen && isMobile}
            onOpenChange={setCustomOpen}
          />
        </div>
      )}

      {/* Time controls */}
      {show('timeControl') && (
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Time control</p>
          <div className="grid grid-cols-4 gap-1">
            {TIME_CONTROLS.map((tc) => (
              <button
                key={tc}
                onClick={() => toggleTimeControl(tc)}
                data-testid={`filter-time-control-${tc}`}
                aria-label={`${TIME_CONTROL_LABELS[tc]} time control`}
                aria-pressed={isTimeControlActive(tc)}
                className={cn(
                  'rounded border h-11 sm:h-7 text-xs transition-colors',
                  isTimeControlActive(tc)
                    ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
                    : 'border-border bg-inactive-bg text-muted-foreground hover:bg-inactive-bg-hover hover:text-foreground',
                )}
              >
                <span className="flex items-center justify-center gap-1">
                  <TimeControlIcon timeControl={tc} className="h-3.5 w-3.5" />
                  {TIME_CONTROL_LABELS[tc]}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Platform */}
      {show('platform') && (
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Platform</p>
          <div className="grid grid-cols-2 gap-1">
            {PLATFORMS.map((p) => (
              <button
                key={p}
                onClick={() => togglePlatform(p)}
                data-testid={`filter-platform-${p === 'chess.com' ? 'chess-com' : p}`}
                aria-label={`${PLATFORM_LABELS[p]} platform`}
                aria-pressed={isPlatformActive(p)}
                className={cn(
                  'rounded border h-11 sm:h-7 text-xs transition-colors',
                  isPlatformActive(p)
                    ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
                    : 'border-border bg-inactive-bg text-muted-foreground hover:bg-inactive-bg-hover hover:text-foreground',
                )}
              >
                <span className="flex items-center justify-center gap-1">
                  <PlatformIcon platform={p} className="h-3.5 w-3.5" />
                  {PLATFORM_LABELS[p]}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Opponent Strength */}
      {show('opponentStrength') && (
        <OpponentStrengthFilter
          value={filters.opponentStrength}
          onChange={(opponentStrength) => update({ opponentStrength })}
        />
      )}

      {/* Opponent Type */}
      {show('opponent') && (
        <div className="pt-3 border-t border-border/40">
          <p className="mb-1 text-xs text-muted-foreground">Opponent Type</p>
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
            className="w-full"
          >
            <ToggleGroupItem value="human" data-testid="filter-opponent-human" className="min-h-11 sm:min-h-0 flex-1">Human</ToggleGroupItem>
            <ToggleGroupItem value="bot" data-testid="filter-opponent-bot" className="min-h-11 sm:min-h-0 flex-1">Bot</ToggleGroupItem>
            <ToggleGroupItem value="both" data-testid="filter-opponent-both" className="min-h-11 sm:min-h-0 flex-1">Both</ToggleGroupItem>
          </ToggleGroup>
        </div>
      )}

      {/* Rated */}
      {show('rated') && (
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
            className="w-full"
          >
            <ToggleGroupItem value="all" data-testid="filter-rated-all" className="min-h-11 sm:min-h-0 flex-1">All</ToggleGroupItem>
            <ToggleGroupItem value="rated" data-testid="filter-rated-rated" className="min-h-11 sm:min-h-0 flex-1">Rated</ToggleGroupItem>
            <ToggleGroupItem value="casual" data-testid="filter-rated-casual" className="min-h-11 sm:min-h-0 flex-1">Casual</ToggleGroupItem>
          </ToggleGroup>
        </div>
      )}

      {/* Reset Filters — full panel width, below the last filter row.
          GLOBAL RESET: clears every FilterState field to DEFAULT_FILTERS EXCEPT `color`
          (Played-as), which is preserved at its current value. This uniform behavior applies
          on every consumer (Openings, Endgames, GlobalStats) and every form factor (desktop
          sidebar, mobile drawer). Because the modified-dot also ignores `color` (see
          FILTER_DOT_FIELDS), Reset is guaranteed to drop the dot on every page. */}
      <div className="pt-2 border-t border-border/40">
        <Button
          type="button"
          variant="brand-outline"
          size="lg"
          className="w-full min-h-11 sm:min-h-0"
          data-testid="btn-reset-filters"
          onClick={() => {
            onChange({ ...DEFAULT_FILTERS, color: filters.color, customRange: null });
          }}
        >
          Reset Filters
        </Button>
        {showDeferredApplyHint && (
          <p
            className="mt-2 text-sm italic leading-tight text-muted-foreground"
            data-testid="filter-deferred-apply-hint"
          >
            <span className="font-semibold text-foreground/80">Tip:</span> Filter changes apply on closing the filters panel.
          </p>
        )}
      </div>
    </div>
  );
}
