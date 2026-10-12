import { TcSwitchButtons } from '@/components/stats/TcSwitchButtons';
import { useEndgameStatsTc } from '@/hooks/useEndgameStatsTc';
import { trackFeature } from '@/lib/analytics';
import type { RankedTcStats, TimeControlBucket } from '@/types/endgames';

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
    <TcSwitchButtons
      sectionId={sectionId}
      tcs={tcs.map((t) => t.tc)}
      selected={selectedTc}
      onSelect={handleSelect}
    />
  );
}
