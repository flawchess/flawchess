/**
 * Phase 88 — Section orchestrator for the Time Pressure cards.
 * Renders full-width stacked EndgameTimePressureCard rows inside a controlled
 * Accordion (type="multiple"), matching the EndgameMetricsByTcSection pattern.
 *
 * The most-active TC (time-weighted via computePrimaryTc) starts expanded;
 * all others start collapsed. A filterKey prop resets the accordion to the
 * recomputed primary TC on filter change, matching the sibling section (D-12).
 *
 * Replaces the legacy dynamic 2×2 grid layout (GRID_ONE_CARD / GRID_TWO_CARDS /
 * GRID_THREE_CARDS / GRID_FOUR_CARDS constants deleted in this refactor).
 */

import { useState, useEffect } from 'react';

import { Accordion } from '@/components/ui/accordion';
import { MIN_GAMES_PER_TC_CARD } from '@/generated/endgameZones';
import { computePrimaryTc } from '@/lib/primaryTc';
import { EndgameTimePressureCard } from '@/components/charts/EndgameTimePressureCard';
import type { RatingAnchorsByTc } from '@/lib/percentileAnchor';
import type { TimePressureCardsResponse } from '@/types/endgames';

/** Build the per-TC totals map required by computePrimaryTc from the flat
 *  cards array. Each card contributes a single-element array with { total }. */
function buildByTcForPrimary(
  cards: TimePressureCardsResponse['cards'],
): Record<string, { total: number }[]> {
  const byTc: Record<string, { total: number }[]> = {};
  for (const card of cards) {
    byTc[card.tc] = [{ total: card.total }];
  }
  return byTc;
}

export function EndgameTimePressureSection({
  data,
  ratingAnchors,
  filterKey,
}: {
  data: TimePressureCardsResponse;
  /** Phase 94.4 Plan 07: per-TC rating anchors from
   *  EndgameOverviewResponse.rating_anchors. Threaded into per-TC chip slots
   *  on each EndgameTimePressureCard. Cards without a matching anchor (TC
   *  below the inclusion floor) suppress their chip silently. Defaults to
   *  an empty object so legacy fixtures and pre-94.4 server responses still
   *  render the section (chips just don't appear). */
  ratingAnchors?: RatingAnchorsByTc;
  /** Serialised string of the active filter params. Changing this value resets
   *  the accordion to the recomputed primary TC, matching the
   *  EndgameMetricsByTcSection pattern (D-12). The parent (Endgames.tsx) must
   *  pass a stable string that changes whenever appliedFilters changes. */
  filterKey?: string;
}) {
  const anchors = ratingAnchors ?? {};
  const grandTotal = data.cards.reduce((acc, c) => acc + c.total, 0);

  // Primary TC: time-weighted argmax over eligible cards.
  // Used to seed the initial expanded set and reset on filterKey change.
  const [expandedTcs, setExpandedTcs] = useState<string[]>(() => {
    const primary = computePrimaryTc(buildByTcForPrimary(data.cards), MIN_GAMES_PER_TC_CARD);
    return primary ? [primary] : [];
  });

  // Reset accordion to the recomputed primary TC on filter change (D-12).
  useEffect(() => {
    const newByTc = buildByTcForPrimary(data.cards);
    const newPrimary = computePrimaryTc(newByTc, MIN_GAMES_PER_TC_CARD);
    setExpandedTcs(newPrimary ? [newPrimary] : []);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

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
        <Accordion
          type="multiple"
          value={expandedTcs}
          onValueChange={setExpandedTcs}
          className="flex flex-col gap-4 mt-2"
        >
          {data.cards.map((card) => (
            <EndgameTimePressureCard
              key={card.tc}
              card={card}
              grandTotal={grandTotal}
              ratingAnchor={anchors[card.tc]}
            />
          ))}
        </Accordion>
      )}
    </section>
  );
}
