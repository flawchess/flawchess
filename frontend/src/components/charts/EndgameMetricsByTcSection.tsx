/**
 * Phase 97 Plan 03 — Section orchestrator for per-TC Endgame Metrics cards.
 *
 * Renders one full-width EndgameMetricsByTcCard per eligible time control in
 * bullet -> blitz -> rapid -> classical order (order is determined by the
 * backend which pre-filters cards to include only TCs with sufficient games).
 * No frontend filtering by selected TCs: the backend returns the already
 * (selected ∩ eligible) set (D-14).
 *
 * Layout: full-width vertical stacking (D-02) — each card is one row, unlike
 * the Time Pressure staircase grid. Use `w-full mt-2` wrapper.
 *
 * Empty state mirrors EndgameTimePressureSection: show descriptive text with
 * a distinct testid when cards is empty.
 */

import { EndgameMetricsByTcCard } from '@/components/charts/EndgameMetricsByTcCard';
import type { EndgameMetricsCardsResponse } from '@/types/endgames';

interface EndgameMetricsByTcSectionProps {
  data: EndgameMetricsCardsResponse;
}

export function EndgameMetricsByTcSection({ data }: EndgameMetricsByTcSectionProps) {
  return (
    <section
      data-testid="endgame-metrics-tc-section"
      aria-label="Endgame metrics by time control"
    >
      <p className="text-sm text-muted-foreground">
        How do you score from winning, balanced, and losing endgames, by time control?
      </p>
      {data.cards.length === 0 ? (
        <div
          className="mt-2 text-sm text-muted-foreground"
          data-testid="endgame-metrics-tc-section-empty"
        >
          No endgame data yet. Import more games to see this section.
        </div>
      ) : (
        <div className="w-full mt-2 flex flex-col gap-4">
          {data.cards.map((card) => (
            <EndgameMetricsByTcCard key={card.tc} card={card} />
          ))}
        </div>
      )}
    </section>
  );
}
