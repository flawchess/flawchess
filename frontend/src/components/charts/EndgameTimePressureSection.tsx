/**
 * Phase 88 — Section orchestrator for the Time Pressure cards grid.
 * Renders a responsive grid of per-TC EndgameTimePressureCard instances.
 * Grid layout is driven by the visible card count (SC-1):
 *   1 card  → half width
 *   2 cards → 2-column full width
 *   3 cards → 3-column full width
 *   4 cards → 2×2 on md+ (never more than 2 per row)
 *
 * Replaces the legacy line-chart EndgameTimePressureSection and the
 * EndgameClockPressureSection (both deleted in Phase 88 Plan 07).
 * Answers: "How does your score change under time pressure?"
 */

import { EndgameTimePressureCard } from '@/components/charts/EndgameTimePressureCard';
import type { TimePressureCardsResponse } from '@/types/endgames';

// SC-1: Named grid class constants — no magic strings in the ternary.
// Mobile-first: every layout collapses to a single stacked column below the
// multi-col breakpoint so TC cards stack on phones AND tablets. Breakpoints
// raised two steps from the Phase 88 originals (sm→lg / md→xl) so the
// single-column layout holds well into desktop widths before flipping.
const GRID_ONE_CARD = 'w-full lg:w-1/2 mt-2';
const GRID_TWO_CARDS = 'grid grid-cols-1 lg:grid-cols-2 gap-4 mt-2';
const GRID_THREE_CARDS = 'grid grid-cols-1 lg:grid-cols-3 gap-4 mt-2';
const GRID_FOUR_CARDS = 'grid grid-cols-1 xl:grid-cols-2 gap-4 mt-2';

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
        How does your score change under time pressure?
      </p>
      {data.cards.length === 0 ? (
        <div
          className="mt-2 text-sm text-muted-foreground"
          data-testid="time-pressure-cards-empty"
        >
          No time-pressure data yet. Import more games to see this section.
        </div>
      ) : (
        (() => {
          // Sum across ALL cards (backend pre-filters by MIN_GAMES_PER_TC_CARD,
          // so data.cards.length is the visible count — do not inspect
          // null-returning children). grandTotal propagates to every card so the
          // per-card percentage stays honest under filter changes.
          const visibleCount = data.cards.length;
          const grandTotal = data.cards.reduce((acc, c) => acc + c.total, 0);

          // SC-1: select grid class by visible card count (1/2/3 are layout breakpoints).
          const gridClass =
            visibleCount === 1
              ? GRID_ONE_CARD
              : visibleCount === 2
                ? GRID_TWO_CARDS
                : visibleCount === 3
                  ? GRID_THREE_CARDS
                  : GRID_FOUR_CARDS;

          return (
            <div className={gridClass}>
              {data.cards.map((card) => (
                <EndgameTimePressureCard
                  key={card.tc}
                  card={card}
                  grandTotal={grandTotal}
                />
              ))}
            </div>
          );
        })()
      )}
    </section>
  );
}
