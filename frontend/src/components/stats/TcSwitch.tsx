import { TimeControlIcon } from '@/components/icons/TimeControlIcon';
import { Button } from '@/components/ui/button';
import { trackFeature, type OptionChangeProps } from '@/lib/analytics';
import { TC_LABELS } from '@/lib/timeControlLabels';
import { cn } from '@/lib/utils';
import type { TimeControlBucket } from '@/types/endgames';

/** The option-change targets of the stats pages' TC switches (endgame-stats-tc, library-stats-tc). */
type TcSwitchTrackTarget = Extract<OptionChangeProps, { value: TimeControlBucket }>['target'];

interface TcSwitchProps {
  /** Testid prefix: `tc-switch-{idPrefix}` on the group, `tc-switch-{idPrefix}-{tc}` per button. */
  idPrefix: string;
  /** Exactly these TCs are offered, in this order. */
  tcs: readonly TimeControlBucket[];
  selected: TimeControlBucket | null;
  onSelect: (tc: TimeControlBucket) => void;
  /** The Umami option-change target a click reports. */
  trackTarget: TcSwitchTrackTarget;
}

// Above this many TCs the buttons drop their icons on narrow phones: four labelled TCs are
// ~345px wide, more than the 328px a 360px phone leaves inside the page gutters.
const MAX_TCS_WITH_ICONS_ON_NARROW = 3;

/**
 * The time-control switch shared by the Endgame and Library Stats tabs. Each tab binds it
 * to its own selection store (EndgameStatsTcSwitch, LibraryStatsTcSwitch). Tracking fires
 * from a click on another TC only, never from restore or fallback.
 */
export function TcSwitch({ idPrefix, tcs, selected, onSelect, trackTarget }: TcSwitchProps) {
  const compact = tcs.length > MAX_TCS_WITH_ICONS_ON_NARROW;

  const handleClick = (tc: TimeControlBucket): void => {
    if (tc === selected) return;
    onSelect(tc);
    trackFeature('option-change', { target: trackTarget, value: tc });
  };

  return (
    <div
      role="group"
      aria-label="Time control"
      className="inline-flex gap-1"
      data-testid={`tc-switch-${idPrefix}`}
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
            // at 360px; desktop keeps the stock button spacing.
            className="min-h-11 gap-1 px-2 sm:min-h-0 sm:gap-1.5 sm:px-2.5"
            onClick={() => handleClick(tc)}
            data-testid={`tc-switch-${idPrefix}-${tc}`}
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
