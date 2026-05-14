/**
 * Phase 87 — Orchestrator for the 5-card Endgame Type Breakdown section.
 * Replaces both legacy EndgameWDLChart (per-type WDL table) and
 * EndgameConvRecovChart (gauge-only mini cards) per SEC3-06 / SEC3-07.
 *
 * Layout: 3-column grid on lg+, 2-column on sm, single column on mobile.
 * `pawnless` is filtered upstream via HIDDEN_ENDGAME_CLASSES; with all 6
 * classes present the section renders exactly 5 cards. Per-card sharePct uses
 * the parent's `totalGames` (all filtered games) as the denominator, NOT the
 * sum of per-type totals: a single game can count toward multiple Endgame
 * Types, so summing per-type totals over-counts the population.
 *
 * v1.17 single-bullet doctrine: each EndgameTypeCard carries one peer bullet
 * (vs 0) per metric (Conv + Recov). Section-level h3 / InfoPopover were
 * dropped (D-12); the page-level "Endgame Type Breakdown" h2 in Endgames.tsx
 * carries the taxonomy + Conv/Recov metric definitions + per-type
 * descriptions + peer-bullet explainer.
 */

import { ENDGAME_CLASS_TO_SLUG, HIDDEN_ENDGAME_CLASSES } from '@/lib/endgameMetrics';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';

import { EndgameTypeCard } from './EndgameTypeCard';

export interface EndgameTypeBreakdownSectionProps {
  categories: EndgameCategoryStats[];
  // Total endgame games used as the sharePct denominator. Per REVIEW WR-01
  // (Phase 87 follow-up) callers pass the count of games that reached an
  // endgame phase (EndgameStatsResponse.endgame_games), not all filtered
  // games — so each card's "Games: X%" reads as the share of the user's
  // endgames, not the share of all their games. A single game can still
  // contribute to multiple Endgame Types, so the sum across cards can
  // exceed 100%.
  totalGames: number;
  onCategorySelect: (cls: EndgameClass) => void;
}

export function EndgameTypeBreakdownSection({
  categories,
  totalGames,
  onCategorySelect,
}: EndgameTypeBreakdownSectionProps) {
  const visibleCategories = categories.filter(
    (cat) => !HIDDEN_ENDGAME_CLASSES.has(cat.endgame_class),
  );

  return (
    <section
      data-testid="endgame-type-breakdown-section"
      aria-labelledby="endgame-type-breakdown-heading"
    >
      <p className="text-sm text-muted-foreground">
        Which Endgame Types do you convert best and defend best, and how does
        each compare to your opponents?
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
        {visibleCategories.map((cat) => {
          const slug = ENDGAME_CLASS_TO_SLUG[cat.endgame_class];
          const sharePct =
            totalGames > 0 ? (cat.total / totalGames) * 100 : 0;
          return (
            <EndgameTypeCard
              key={cat.endgame_class}
              category={cat}
              sharePct={sharePct}
              onCategorySelect={onCategorySelect}
              tileTestId={`type-card-${slug}`}
            />
          );
        })}
      </div>
    </section>
  );
}
