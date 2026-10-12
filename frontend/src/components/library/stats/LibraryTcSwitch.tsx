import { TcSwitchButtons } from '@/components/stats/TcSwitchButtons';
import { useLibraryStatsTc, type LibraryTcCount } from '@/hooks/useLibraryStatsTc';
import { trackFeature } from '@/lib/analytics';
import type { TimeControlBucket } from '@/types/endgames';

interface LibraryTcSwitchProps {
  /** Distinguishes the testids of the several switches on the page (one per section). */
  sectionId: string;
  /** The payload's offered TCs (D-02): exactly these are listed, in payload order. */
  tcs: readonly LibraryTcCount[];
}

/**
 * Section time-control switch for the Library Stats tab (D-02). Every section mounts its
 * own, all bound to the one Library TC store, so choosing a TC in any section switches
 * every section. Tracking fires from the click only, never from restore or fallback.
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
    />
  );
}
