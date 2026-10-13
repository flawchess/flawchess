import { TC_LABELS } from '@/components/endgames/stats/rankedMetrics';
import { TimeControlIcon } from '@/components/icons/TimeControlIcon';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { TimeControlBucket } from '@/types/endgames';

interface TcSwitchButtonsProps {
  /** Distinguishes the testids of the several switches on a page (one per section). */
  sectionId: string;
  /** Exactly these TCs are offered, in this order. */
  tcs: readonly TimeControlBucket[];
  selected: TimeControlBucket | null;
  onSelect: (tc: TimeControlBucket) => void;
  /** Drop the TC icons on narrow phones, so four TCs fit next to another control. */
  compact?: boolean;
}

/**
 * The presentational time-control switch shared by the Endgame and Library Stats tabs.
 * State, persistence and analytics belong to the wrapper (TcSwitch and its Library
 * counterpart); this only draws the buttons.
 */
export function TcSwitchButtons({
  sectionId,
  tcs,
  selected,
  onSelect,
  compact = false,
}: TcSwitchButtonsProps) {
  return (
    <div
      role="group"
      aria-label="Time control"
      className="inline-flex gap-1"
      data-testid={`tc-switch-${sectionId}`}
    >
      {tcs.map((tc) => {
        const isSelected = tc === selected;
        return (
          <Button
            key={tc}
            type="button"
            variant={isSelected ? 'default' : 'brand-outline'}
            aria-pressed={isSelected}
            // Tighter padding and icon gap on mobile so all four TCs fit on one row
            // at 360px (238 UAT); desktop keeps the stock button spacing.
            className="min-h-11 gap-1 px-2 sm:min-h-0 sm:gap-1.5 sm:px-2.5"
            onClick={() => onSelect(tc)}
            data-testid={`tc-switch-${sectionId}-${tc}`}
          >
            <TimeControlIcon
              timeControl={tc}
              className={cn('h-3.5 w-3.5', compact && 'max-[419px]:hidden')}
            />
            {TC_LABELS[tc]}
          </Button>
        );
      })}
    </div>
  );
}
