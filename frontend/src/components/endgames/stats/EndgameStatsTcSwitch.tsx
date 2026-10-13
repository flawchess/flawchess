import { TcSwitch } from '@/components/stats/TcSwitch';
import { useEndgameStatsTc } from '@/hooks/useEndgameStatsTc';
import type { RankedTcStats } from '@/types/endgames';

/**
 * The Endgame Stats time-control switch (D-00h), bound to the one shared selection store
 * every section reads. The tab mounts it once, in its StickyTcBar. `tcs` is the payload's
 * TC list (238 D-14): exactly these TCs are offered, in payload order.
 */
export function EndgameStatsTcSwitch({ tcs }: { tcs: readonly RankedTcStats[] }) {
  const [selectedTc, setSelectedTc] = useEndgameStatsTc(tcs);
  return (
    <TcSwitch
      idPrefix="endgame-stats"
      tcs={tcs.map((t) => t.tc)}
      selected={selectedTc}
      onSelect={setSelectedTc}
      trackTarget="endgame-stats-tc"
    />
  );
}
