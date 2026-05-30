/**
 * Phase 98 — Controlled-accordion orchestrator for the Endgame Type Breakdown.
 *
 * Replaces the Phase 87 3-column grid
 * with full-width vertically-stacked collapsible per-TC cards (SC-1, mode-3
 * disclosure pattern). The user's primary TC is expanded by default (SC-2);
 * other TCs are collapsed. The accordion resets to the recomputed primary TC
 * whenever the filter state changes (D-12).
 *
 * Props:
 *   - categoriesByTc: the new per-(class × TC) breakdown from EndgameStatsResponse.
 *     Optional for back-compat; section returns null when not present (Pitfall 6).
 *   - filterKey: a stable serialised string of the active filter params. Changing
 *     this value resets the accordion to the recomputed primary TC (D-12).
 *   - onCategorySelect: deep-link handler forwarded to each tile.
 *
 * Games-floor suppression: TCs with summed total < MIN_GAMES_PER_TC_CARD are
 * excluded from `eligibleTcs` (SC-7). When no TC is eligible, an empty-state
 * message is shown.
 */

import { useState, useEffect } from 'react';

import { Accordion } from '@/components/ui/accordion';
import { MIN_GAMES_PER_TC_CARD } from '@/generated/endgameZones';
import { computePrimaryTc } from '@/lib/primaryTc';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';

import { EndgameTypeTcCard } from './EndgameTypeTcCard';

// Fixed TC render order (SC-3, same as other per-TC sections).
const TC_ORDER = ['bullet', 'blitz', 'rapid', 'classical'] as const;
type Tc = (typeof TC_ORDER)[number];

export interface EndgameTypeBreakdownSectionProps {
  // Phase 98: per-(class × TC) rates keyed by TC. Optional for back-compat.
  categoriesByTc?: Record<Tc, EndgameCategoryStats[]>;
  // Serialised string of the active filter params (TC filter, recency, color,
  // platform, etc.). Changing this value resets the accordion to the
  // recomputed primary TC (D-12). The parent (Endgames.tsx) must pass a
  // stable string that changes whenever appliedFilters changes.
  filterKey?: string;
  onCategorySelect: (cls: EndgameClass) => void;
}

export function EndgameTypeBreakdownSection({
  categoriesByTc,
  filterKey,
  onCategorySelect,
}: EndgameTypeBreakdownSectionProps) {
  // Gate: section only renders when the backend field is present (Pitfall 6).
  if (!categoriesByTc) return null;

  return (
    <EndgameTypeBreakdownSectionInner
      categoriesByTc={categoriesByTc}
      filterKey={filterKey}
      onCategorySelect={onCategorySelect}
    />
  );
}

// Inner component: separated from the outer guard to keep hook calls
// unconditional (React rules of hooks require no conditional hook calls).
function EndgameTypeBreakdownSectionInner({
  categoriesByTc,
  filterKey,
  onCategorySelect,
}: Required<Pick<EndgameTypeBreakdownSectionProps, 'categoriesByTc' | 'onCategorySelect'>> &
  Pick<EndgameTypeBreakdownSectionProps, 'filterKey'>) {
  // Compute eligible TCs (summed total >= MIN_GAMES_PER_TC_CARD) in fixed order.
  const eligibleTcs = TC_ORDER.filter((tc) => {
    const tcTotal = (categoriesByTc[tc] ?? []).reduce(
      (sum, c) => sum + c.total,
      0,
    );
    return tcTotal >= MIN_GAMES_PER_TC_CARD;
  });

  const grandTotal = eligibleTcs.reduce((sum, tc) => {
    return (
      sum +
      (categoriesByTc[tc] ?? []).reduce((s, c) => s + c.total, 0)
    );
  }, 0);

  // Primary TC: argmax of summed_games × NOMINAL_DURATION over eligible TCs.
  // Initialize accordion to primary TC expanded (D-09).
  const [expandedTc, setExpandedTc] = useState<string>(
    () => computePrimaryTc(categoriesByTc, MIN_GAMES_PER_TC_CARD) ?? '',
  );

  // Reset accordion to recomputed primary on filter change (D-12).
  useEffect(() => {
    const newPrimary =
      computePrimaryTc(categoriesByTc, MIN_GAMES_PER_TC_CARD) ?? '';
    setExpandedTc(newPrimary);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

  return (
    <section
      data-testid="endgame-type-breakdown-section"
      aria-labelledby="endgame-type-breakdown-heading"
    >
      <p className="text-sm text-muted-foreground">
        Which Endgame Types did you convert or defend poorly against your opponents?
      </p>

      {eligibleTcs.length === 0 ? (
        <div
          className="mt-2 text-sm text-muted-foreground"
          data-testid="endgame-type-breakdown-empty"
        >
          No endgame type data yet. Import more games to see this section.
        </div>
      ) : (
        <Accordion
          type="single"
          collapsible
          value={expandedTc}
          onValueChange={setExpandedTc}
          className="flex flex-col gap-2 mt-2"
        >
          {eligibleTcs.map((tc) => (
            <EndgameTypeTcCard
              key={tc}
              tc={tc}
              categories={categoriesByTc[tc] ?? []}
              grandTotal={grandTotal}
              onCategorySelect={onCategorySelect}
            />
          ))}
        </Accordion>
      )}
    </section>
  );
}
