/**
 * GemMoveBadge — the move-list gem icon with a hover/tap info popover that
 * explains the gem-move rule (Phase 163, SEED-092 follow-on).
 *
 * A gem is a played move that is BOTH the only good move in the position AND
 * one a human at the selected rating almost never finds (Maia policy
 * probability ≤ GEM_MAIA_MAX_PROB). The popover restates that rule and cites
 * the two numbers behind THIS gem: the ELO rung it was detected at and the
 * Maia probability of the move at that rung.
 *
 * Copy uses "this level"/the explicit ELO, never "your rating" (163-REVIEW
 * IN-01): the probability is evaluated at the draggable ELO-slider value, which
 * may sit far from the user's own rating.
 *
 * Reuses the shared `InfoPopover` interaction shell (hover-intent + tap-toggle
 * via Radix) with `GemIcon` as the custom trigger glyph. The wrapper span stops
 * click/pointer propagation so tapping the badge on mobile — where the move list
 * renders each marker INSIDE its clickable move chip (HorizontalMoveList) —
 * reveals the popover instead of navigating to the move.
 */

import { GemIcon } from '@/components/icons/GemIcon';
import { InfoPopover } from '@/components/ui/info-popover';

/** Maia probability (0..1) as a percent — one decimal below 1% so a sub-percent
 *  gem (common: gems are ≤5%) never reads as a misleading "0%". */
function formatGemProbability(probability: number): string {
  const pct = probability * 100;
  return `${pct < 1 ? pct.toFixed(1) : Math.round(pct)}%`;
}

export interface GemMoveBadgeProps {
  /** Sizing/positioning classes forwarded to the GemIcon (matches the severity glyphs). */
  className?: string;
  /** Maia policy probability (0..1) of the gem move at its detection rung; null hides the stat line. */
  maiaProbability?: number | null;
  /** ELO rung the gem was detected at (the ELO-slider value at detection time); null hides the stat line. */
  elo?: number | null;
  /** True when the OPPONENT (not the user) played the gem — switches the heading.
   *  Only meaningful in game mode; free play always reads as the user's own move. */
  byOpponent?: boolean;
}

export function GemMoveBadge({ className, maiaProbability, elo, byOpponent = false }: GemMoveBadgeProps) {
  const showStat = maiaProbability != null && elo != null;
  return (
    <span
      className="inline-flex"
      // Stop the tap/click from bubbling to the enclosing move chip button on
      // mobile (HorizontalMoveList) so tapping the badge opens the popover
      // instead of navigating. Harmless on desktop (badge is a sibling there).
      onClick={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <InfoPopover
        ariaLabel="Gem move — why this move is a gem"
        testId="gem-move-popover"
        triggerContent={<GemIcon className={className} />}
      >
        <div className="space-y-1">
          <p className="font-semibold">
            {byOpponent ? 'Your opponent found a gem move!' : 'Nice, you found a gem move!'}
          </p>
          <p>The only good move here — and one players at this level almost never find.</p>
          {showStat && (
            <p>
              At {elo} ELO, Maia gives it a {formatGemProbability(maiaProbability)} chance of being
              played.
            </p>
          )}
        </div>
      </InfoPopover>
    </span>
  );
}
