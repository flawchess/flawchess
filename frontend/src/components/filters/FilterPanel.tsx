import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { MatchSide, TimeControl, Recency, Color, Platform, OpponentType, OpponentStrength } from '@/types/api';
import { cn } from '@/lib/utils';
import { InfoPopover } from '@/components/ui/info-popover';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { TimeControlIcon } from '@/components/icons/TimeControlIcon';
import { Button } from '@/components/ui/button';

export interface FilterState {
  matchSide: MatchSide;
  timeControls: TimeControl[] | null; // null = all
  platforms: Platform[] | null; // null = all
  rated: boolean | null; // null = all
  opponentType: OpponentType; // default human = computer games excluded
  opponentStrength: OpponentStrength; // default any = no strength filter
  recency: Recency | null; // null = all time
  color: Color;
}

// eslint-disable-next-line react-refresh/only-export-components
export const DEFAULT_FILTERS: FilterState = {
  matchSide: 'both',
  timeControls: null,
  platforms: null,
  rated: null,
  opponentType: 'human',
  opponentStrength: 'any',
  recency: null,
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
          <Select
            value={filters.recency ?? 'all'}
            onValueChange={(v) => update({ recency: v === 'all' ? null : (v as Recency) })}
          >
            <SelectTrigger size="sm" data-testid="filter-recency" className="min-h-11 sm:min-h-0 w-full">
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
        <div>
          <p className="mb-1 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              Opponent Strength
              <InfoPopover ariaLabel="Opponent strength filter info" testId="filter-opponent-strength-info" side="bottom">
                <div className="space-y-1">
                  <p><strong>Stronger:</strong> Rated 50+ ELO above you</p>
                  <p><strong>Similar:</strong> Within &plusmn;50 ELO</p>
                  <p><strong>Weaker:</strong> Rated 50+ ELO below you</p>
                </div>
              </InfoPopover>
            </span>
          </p>
          <ToggleGroup
            type="single"
            value={filters.opponentStrength}
            onValueChange={(v) => {
              if (!v) return;
              update({ opponentStrength: v as OpponentStrength });
            }}
            variant="outline"
            size="sm"
            data-testid="filter-opponent-strength"
            className="w-full"
          >
            <ToggleGroupItem value="any" data-testid="filter-opponent-strength-any" className="min-h-11 sm:min-h-0 flex-1">Any</ToggleGroupItem>
            <ToggleGroupItem value="stronger" data-testid="filter-opponent-strength-stronger" className="min-h-11 sm:min-h-0 flex-1">Stronger</ToggleGroupItem>
            <ToggleGroupItem value="similar" data-testid="filter-opponent-strength-similar" className="min-h-11 sm:min-h-0 flex-1">Similar</ToggleGroupItem>
            <ToggleGroupItem value="weaker" data-testid="filter-opponent-strength-weaker" className="min-h-11 sm:min-h-0 flex-1">Weaker</ToggleGroupItem>
          </ToggleGroup>
        </div>
      )}

      {/* Opponent Type */}
      {show('opponent') && (
        <div>
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
          size="sm"
          className="w-full min-h-11 sm:min-h-0"
          data-testid="btn-reset-filters"
          onClick={() => {
            onChange({ ...DEFAULT_FILTERS, color: filters.color });
          }}
        >
          Reset Filters
        </Button>
        {showDeferredApplyHint && (
          <p
            className="mt-2 text-[11px] leading-tight text-muted-foreground"
            data-testid="filter-deferred-apply-hint"
          >
            Filter changes apply on closing the filters panel.
          </p>
        )}
      </div>
    </div>
  );
}
