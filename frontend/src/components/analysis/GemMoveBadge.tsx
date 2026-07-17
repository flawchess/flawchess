/**
 * GemMoveBadge — the move-list gem/great icon with a hover/tap info popover
 * that explains the gem or great-move rule (Phase 163, SEED-092; extended
 * Phase 175, SEED-108 with the `tier` prop rather than a sibling
 * GreatMoveBadge component, to avoid drift between two near-identical badges
 * — PATTERNS.md's recommended approach).
 *
 * A gem is a played move that is BOTH the only good move in the position AND
 * one a human at the selected rating almost never finds (Maia policy
 * probability ≤ GEM_MAIA_MAX_PROB). A great move is the same only-good-move
 * rule but a step less rare (Maia probability in (GEM_MAIA_MAX_PROB,
 * GREAT_MAIA_MAX_PROB]). The popover restates the relevant rule and cites the
 * two numbers behind THIS badge: the ELO rung it was detected at and the
 * Maia probability of the move at that rung.
 *
 * Copy uses "this level"/the explicit ELO, never "your rating" (163-REVIEW
 * IN-01): the probability is evaluated at the draggable ELO-slider value, which
 * may sit far from the user's own rating.
 *
 * Reuses the shared `InfoPopover` interaction shell (hover-intent + tap-toggle
 * via Radix) with `GemIcon`/`GreatMoveIcon` as the custom trigger glyph. The
 * wrapper span stops click/pointer propagation so tapping the badge on mobile —
 * where the move list renders each marker INSIDE its clickable move chip
 * (HorizontalMoveList) — reveals the popover instead of navigating to the move.
 */

import { GemIcon } from '@/components/icons/GemIcon';
import { GreatMoveIcon } from '@/components/icons/GreatMoveIcon';
import { InfoPopover } from '@/components/ui/info-popover';

/** Maia probability (0..1) as a percent — one decimal below 1% so a sub-percent
 *  gem (common: gems are ≤5%) never reads as a misleading "0%". */
function formatGemProbability(probability: number): string {
  const pct = probability * 100;
  return `${pct < 1 ? pct.toFixed(1) : Math.round(pct)}%`;
}

/** Per-tier popover copy — heading (by-opponent aware) + rule sentence. */
const TIER_COPY = {
  gem: {
    heading: (byOpponent: boolean) =>
      byOpponent ? 'Your opponent found a gem move!' : 'Nice, you found a gem move!',
    rule: 'The only good move here — and one players at this level almost never find.',
    ariaLabel: 'Gem move — why this move is a gem',
    testId: 'gem-move-popover',
  },
  great: {
    heading: (byOpponent: boolean) =>
      byOpponent ? 'Your opponent found a great move!' : 'Nice, you found a great move!',
    rule: 'The only good move here — and one players at this level rarely find.',
    ariaLabel: 'Great move — why this move is great',
    testId: 'great-move-popover',
  },
} as const;

export interface GemMoveBadgeProps {
  /** Sizing/positioning classes forwarded to the icon (matches the severity glyphs). */
  className?: string;
  /** Maia policy probability (0..1) of the move at its detection rung; null hides the stat line. */
  maiaProbability?: number | null;
  /** ELO rung the move was detected at (the ELO-slider value at detection time); null hides the stat line. */
  elo?: number | null;
  /** True when the OPPONENT (not the user) played the move — switches the heading.
   *  Only meaningful in game mode; free play always reads as the user's own move. */
  byOpponent?: boolean;
  /** Which badge/copy set to render. Defaults to 'gem' so existing call sites are unchanged. */
  tier?: 'gem' | 'great';
}

export function GemMoveBadge({
  className,
  maiaProbability,
  elo,
  byOpponent = false,
  tier = 'gem',
}: GemMoveBadgeProps) {
  const showStat = maiaProbability != null && elo != null;
  const copy = TIER_COPY[tier];
  const Icon = tier === 'great' ? GreatMoveIcon : GemIcon;
  return (
    <span
      className="inline-flex"
      // Stop the tap/click from bubbling to the enclosing move chip button on
      // mobile (HorizontalMoveList) so tapping the badge opens the popover
      // instead of navigating. Harmless on desktop (badge is a sibling there).
      onClick={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <InfoPopover ariaLabel={copy.ariaLabel} testId={copy.testId} triggerContent={<Icon className={className} />}>
        <div className="space-y-1">
          <p className="font-semibold">{copy.heading(byOpponent)}</p>
          <p>{copy.rule}</p>
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
