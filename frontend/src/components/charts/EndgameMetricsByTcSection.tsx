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
 *
 * 260530-pll: upgraded from a plain <div> list to a controlled Accordion
 * (type="multiple"), matching the EndgameTypeBreakdownSection pattern. The
 * primary TC is expanded by default; filter-key changes reset the accordion.
 */

import { useState, useEffect } from 'react';

import { Accordion } from '@/components/ui/accordion';
import { MIN_GAMES_PER_TC_CARD } from '@/generated/endgameZones';
import { computePrimaryTc } from '@/lib/primaryTc';
import { EndgameMetricsByTcCard } from '@/components/charts/EndgameMetricsByTcCard';
import type { RatingAnchorsByTc } from '@/lib/percentileAnchor';
import type { EndgameMetricsCardsResponse } from '@/types/endgames';

interface EndgameMetricsByTcSectionProps {
  data: EndgameMetricsCardsResponse;
  /** Per-TC rating anchors from EndgameOverviewResponse.rating_anchors. Threaded
   *  into each card's percentile chip tooltip ("…of ~{anchor}-rated players in
   *  {tc}"). Cards whose TC has no anchor self-suppress their chips. */
  ratingAnchors?: RatingAnchorsByTc;
  /** Serialised string of the active filter params. Changing this value resets
   *  the accordion to the recomputed primary TC, matching the
   *  EndgameTypeBreakdownSection pattern (D-12). The parent (Endgames.tsx) must
   *  pass a stable string that changes whenever appliedFilters changes. */
  filterKey?: string;
}

/** Build the per-TC totals map required by computePrimaryTc from the flat
 *  cards array. Each card contributes a single-element array with { total }. */
function buildByTcForPrimary(
  cards: EndgameMetricsCardsResponse['cards'],
): Record<string, { total: number }[]> {
  const byTc: Record<string, { total: number }[]> = {};
  for (const card of cards) {
    byTc[card.tc] = [{ total: card.total }];
  }
  return byTc;
}

export function EndgameMetricsByTcSection({
  data,
  ratingAnchors,
  filterKey,
}: EndgameMetricsByTcSectionProps) {
  const anchors = ratingAnchors ?? {};
  // Denominator for each card header's "Games: x%" share — sum across cards so
  // the per-TC card percentages add up to 100%.
  const grandTotal = data.cards.reduce((sum, card) => sum + card.total, 0);

  // Primary TC: time-weighted argmax over eligible cards.
  // Used to seed the initial expanded set and reset on filterKey change.
  const byTc = buildByTcForPrimary(data.cards);
  const [expandedTcs, setExpandedTcs] = useState<string[]>(() => {
    const primary = computePrimaryTc(byTc, MIN_GAMES_PER_TC_CARD);
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
        <Accordion
          type="multiple"
          value={expandedTcs}
          onValueChange={setExpandedTcs}
          className="flex flex-col gap-4 mt-2"
        >
          {data.cards.map((card) => (
            <EndgameMetricsByTcCard
              key={card.tc}
              card={card}
              ratingAnchor={anchors[card.tc]}
              grandTotal={grandTotal}
            />
          ))}
        </Accordion>
      )}
    </section>
  );
}
