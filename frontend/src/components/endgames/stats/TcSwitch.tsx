import { TimeControlIcon } from '@/components/icons/TimeControlIcon';
import { Button } from '@/components/ui/button';
import { useEndgameStatsTc } from '@/hooks/useEndgameStatsTc';
import { trackFeature } from '@/lib/analytics';
import type { RankedTcStats, TimeControlBucket } from '@/types/endgames';
import { TC_LABELS } from './rankedMetrics';

interface TcSwitchProps {
  /** Distinguishes the testids of the several switches on the page (one per section). */
  sectionId: string;
  /** The payload's TC list (D-14): exactly these TCs are offered, in payload order. */
  tcs: readonly RankedTcStats[];
}

/**
 * Time-control switch (D-00h). Every section mounts its own, all bound to the
 * one shared selection store, so choosing a TC in any section switches every
 * section. Tracking fires from the click only, never from restore or fallback.
 */
export function TcSwitch({ sectionId, tcs }: TcSwitchProps) {
  const [selectedTc, setSelectedTc] = useEndgameStatsTc(tcs);

  const handleSelect = (tc: TimeControlBucket): void => {
    if (tc === selectedTc) return;
    setSelectedTc(tc);
    trackFeature('option-change', { target: 'endgame-stats-tc', value: tc });
  };

  return (
    <div
      role="group"
      aria-label="Time control"
      className="inline-flex gap-1"
      data-testid={`tc-switch-${sectionId}`}
    >
      {tcs.map(({ tc }) => {
        const selected = tc === selectedTc;
        return (
          <Button
            key={tc}
            type="button"
            variant={selected ? 'default' : 'brand-outline'}
            aria-pressed={selected}
            // Tighter padding and icon gap on mobile so all four TCs fit on one row
            // at 360px (238 UAT); desktop keeps the stock button spacing.
            className="min-h-11 gap-1 px-2 sm:min-h-0 sm:gap-1.5 sm:px-2.5"
            onClick={() => handleSelect(tc)}
            data-testid={`tc-switch-${sectionId}-${tc}`}
          >
            <TimeControlIcon timeControl={tc} className="h-3.5 w-3.5" />
            {TC_LABELS[tc]}
          </Button>
        );
      })}
    </div>
  );
}
