import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { MatchSide, TimeControl, Recency, Color, Platform, OpponentType } from '@/types/api';
import { cn } from '@/lib/utils';

export interface FilterState {
  matchSide: MatchSide;
  timeControls: TimeControl[] | null; // null = all
  platforms: Platform[] | null; // null = all
  rated: boolean | null; // null = all
  opponentType: OpponentType; // default human = computer games excluded
  recency: Recency | null; // null = all time
  color: Color;
}

export const DEFAULT_FILTERS: FilterState = {
  matchSide: 'full',
  timeControls: null,
  platforms: null,
  rated: null,
  opponentType: 'human',
  recency: null,
  color: 'white',
};

interface FilterPanelProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
}

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

export function FilterPanel({ filters, onChange }: FilterPanelProps) {
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

  return (
    <div className="space-y-3">
      {/* Time controls */}
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
              data-testid={`filter-platform-${p === 'chess.com' ? 'chess-com' : p}`}
              aria-label={`${PLATFORM_LABELS[p]} platform`}
              aria-pressed={isPlatformActive(p)}
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
          data-testid="filter-rated"
        >
          <ToggleGroupItem value="all" data-testid="filter-rated-all">All</ToggleGroupItem>
          <ToggleGroupItem value="rated" data-testid="filter-rated-rated">Rated</ToggleGroupItem>
          <ToggleGroupItem value="casual" data-testid="filter-rated-casual">Casual</ToggleGroupItem>
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
          <ToggleGroupItem value="human" data-testid="filter-opponent-human">Human</ToggleGroupItem>
          <ToggleGroupItem value="bot" data-testid="filter-opponent-bot">Bot</ToggleGroupItem>
          <ToggleGroupItem value="both" data-testid="filter-opponent-both">Both</ToggleGroupItem>
        </ToggleGroup>
      </div>

      {/* Recency */}
      <div>
        <p className="mb-1 text-xs text-muted-foreground">Recency</p>
        <Select
          value={filters.recency ?? 'all'}
          onValueChange={(v) => update({ recency: v === 'all' ? null : (v as Recency) })}
        >
          <SelectTrigger size="sm" data-testid="filter-recency">
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
}
