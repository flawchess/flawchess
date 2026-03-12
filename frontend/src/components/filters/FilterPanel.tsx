import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { MatchSide, TimeControl, Recency, Color } from '@/types/api';
import { cn } from '@/lib/utils';

export interface FilterState {
  matchSide: MatchSide;
  timeControls: TimeControl[] | null; // null = all
  rated: boolean | null; // null = all
  recency: Recency | null; // null = all time
  color: Color | null; // null = any
}

export const DEFAULT_FILTERS: FilterState = {
  matchSide: 'full',
  timeControls: null,
  rated: null,
  recency: null,
  color: null,
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

export function FilterPanel({ filters, onChange }: FilterPanelProps) {
  const [moreOpen, setMoreOpen] = useState(false);

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

  const content = (
    <div className="space-y-3">
      {/* Played as + Match side — always visible, on the same row */}
      <div className="flex flex-wrap gap-x-4 gap-y-3">
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Played as</p>
          <ToggleGroup
            type="single"
            value={filters.color ?? 'any'}
            onValueChange={(v) => {
              if (!v) return;
              update({ color: v === 'any' ? null : (v as Color) });
            }}
            variant="outline"
            size="sm"
          >
            <ToggleGroupItem value="any">Any</ToggleGroupItem>
            <ToggleGroupItem value="white">White</ToggleGroupItem>
            <ToggleGroupItem value="black">Black</ToggleGroupItem>
          </ToggleGroup>
        </div>

        <div>
          <p className="mb-1 text-xs text-muted-foreground">Match side</p>
          <ToggleGroup
            type="single"
            value={filters.matchSide}
            onValueChange={(v) => v && update({ matchSide: v as MatchSide })}
            variant="outline"
            size="sm"
          >
            <ToggleGroupItem value="white">White</ToggleGroupItem>
            <ToggleGroupItem value="black">Black</ToggleGroupItem>
            <ToggleGroupItem value="full">Both</ToggleGroupItem>
          </ToggleGroup>
        </div>
      </div>

      {/* More filters — collapsible, collapsed by default */}
      <Collapsible open={moreOpen} onOpenChange={setMoreOpen}>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs text-muted-foreground hover:text-foreground">
            More filters
            {moreOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="mt-2 space-y-3">
            {/* Time controls */}
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Time control</p>
              <div className="flex flex-wrap gap-1">
                {TIME_CONTROLS.map((tc) => (
                  <button
                    key={tc}
                    onClick={() => toggleTimeControl(tc)}
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
              >
                <ToggleGroupItem value="all">All</ToggleGroupItem>
                <ToggleGroupItem value="rated">Rated</ToggleGroupItem>
                <ToggleGroupItem value="casual">Casual</ToggleGroupItem>
              </ToggleGroup>
            </div>

            {/* Recency */}
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Recency</p>
              <Select
                value={filters.recency ?? 'all'}
                onValueChange={(v) => update({ recency: v === 'all' ? null : (v as Recency) })}
              >
                <SelectTrigger size="sm">
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
        </CollapsibleContent>
      </Collapsible>
    </div>
  );

  return content;
}
