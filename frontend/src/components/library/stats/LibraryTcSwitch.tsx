import { TcSwitchButtons } from '@/components/stats/TcSwitchButtons';
import { useLibraryStatsTc, type LibraryTcCount } from '@/hooks/useLibraryStatsTc';
import { trackFeature } from '@/lib/analytics';
import type { TimeControlBucket } from '@/types/endgames';

interface LibraryTcSwitchProps {
  /** Prefix of the switch testids. */
  sectionId: string;
  /** The payload's offered TCs (D-02): exactly these are listed, in payload order. */
  tcs: readonly LibraryTcCount[];
}

// Above this many TCs the switch drops its icons on narrow phones: four labelled TCs are
// ~345px wide, more than a 360px phone has once the sticky bar's Filters button sits beside it.
const MAX_TCS_WITH_ICONS_ON_NARROW = 3;

/**
 * The Library Stats time-control switch (D-02), bound to the one Library TC store that
 * every section reads. The page mounts it once per layout, in a sticky bar. Tracking
 * fires from the click only, never from restore or fallback.
 */
export function LibraryTcSwitch({ sectionId, tcs }: LibraryTcSwitchProps) {
  const [selectedTc, setSelectedTc] = useLibraryStatsTc(tcs);

  const handleSelect = (tc: TimeControlBucket): void => {
    if (tc === selectedTc) return;
    setSelectedTc(tc);
    trackFeature('option-change', { target: 'library-stats-tc', value: tc });
  };

  return (
    <TcSwitchButtons
      sectionId={sectionId}
      tcs={tcs.map((t) => t.tc)}
      selected={selectedTc}
      onSelect={handleSelect}
      compact={tcs.length > MAX_TCS_WITH_ICONS_ON_NARROW}
    />
  );
}
