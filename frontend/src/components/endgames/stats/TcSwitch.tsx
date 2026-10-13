import { TcSwitchButtons } from '@/components/stats/TcSwitchButtons';
import { useEndgameStatsTc } from '@/hooks/useEndgameStatsTc';
import { trackFeature } from '@/lib/analytics';
import type { RankedTcStats, TimeControlBucket } from '@/types/endgames';

interface TcSwitchProps {
  /** Prefix of the switch testids. */
  sectionId: string;
  /** The payload's TC list (D-14): exactly these TCs are offered, in payload order. */
  tcs: readonly RankedTcStats[];
}

/**
 * Time-control switch (D-00h), bound to the one shared selection store every
 * section reads. The Stats tab mounts it once, in its StickyTcBar. Tracking
 * fires from the click only, never from restore or fallback.
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
