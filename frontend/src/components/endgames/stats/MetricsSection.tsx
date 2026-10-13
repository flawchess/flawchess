import type { ReactNode } from 'react';
import { useEndgameStatsTc } from '@/hooks/useEndgameStatsTc';
import type { MaterialBucket, RankedTcStats } from '@/types/endgames';
import { MetricsCard } from './MetricsCard';
import { TC_LABELS } from '@/lib/timeControlLabels';
import { SECTION_ID_METRICS } from './rankedMetrics';

const BUCKET_ORDER: readonly MaterialBucket[] = ['conversion', 'parity', 'recovery'];

interface MetricsSectionProps {
  tcs: readonly RankedTcStats[];
  /** Rendered under the section question, above the cards: the narration slot. */
  children?: ReactNode;
}

/**
 * Endgame Metrics (D-00d, D-00h): one card per material bucket for the selected
 * time control, every number from the ranked sample. The TC comes from the
 * shared selection store, so the switch here also switches every other section.
 */
export function MetricsSection({ tcs, children }: MetricsSectionProps) {
  const [selectedTc] = useEndgameStatsTc(tcs);
  const tcStats = tcs.find((t) => t.tc === selectedTc);
  if (!tcStats) return null;

  return (
    <section
      id={SECTION_ID_METRICS}
      className="flex scroll-mt-16 flex-col gap-4"
      data-testid="endgame-metrics-tc-section"
      aria-label={`Endgame Metrics, ${TC_LABELS[tcStats.tc]}`}
    >
      <h2 className="font-brand text-lg font-semibold text-foreground">Endgame Metrics</h2>
      <p className="text-sm text-muted-foreground">
        How do you score from winning, balanced, and losing endgames?
      </p>
      {children}
      <div className="grid grid-cols-1 items-stretch gap-4 lg:grid-cols-3">
        {BUCKET_ORDER.map((bucket) => (
          <MetricsCard key={bucket} tcStats={tcStats} bucket={bucket} />
        ))}
      </div>
    </section>
  );
}
