/**
 * Phase 88 — Section orchestrator for the Time Pressure cards grid.
 * Renders a responsive 4-column grid (xl) / 2-column (lg) / 1-column (base)
 * of per-TC EndgameTimePressureCard instances.
 *
 * Replaces the legacy line-chart EndgameTimePressureSection and the
 * EndgameClockPressureSection (both deleted in Phase 88 Plan 07).
 * Answers: "How does your score change as your clock runs down?"
 */

import { EndgameTimePressureCard } from '@/components/charts/EndgameTimePressureCard';
import type { TimePressureCardsResponse } from '@/types/endgames';

export function EndgameTimePressureSection({
  data,
}: {
  data: TimePressureCardsResponse;
}) {
  return (
    <section
      data-testid="time-pressure-cards-section"
      aria-label="Time pressure analysis"
    >
      <p className="text-sm text-muted-foreground">
        How does your score change as your clock runs down?
      </p>
      {data.cards.length === 0 ? (
        <div
          className="mt-2 text-sm text-muted-foreground"
          data-testid="time-pressure-cards-empty"
        >
          No time-pressure data yet. Import more games to see this section.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-4 mt-2">
          {data.cards.map((card) => (
            <EndgameTimePressureCard key={card.tc} card={card} />
          ))}
        </div>
      )}
    </section>
  );
}
