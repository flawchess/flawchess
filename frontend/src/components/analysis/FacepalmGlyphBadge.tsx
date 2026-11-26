/**
 * FacepalmGlyphBadge: the move-list glyph of a scored blunder, "??" or "???", opening the shared
 * Facepalm explanation (260-G2: the icon carries the score, there is no chip next to it). A
 * facepalm (score at or above the cut) shows "???" and any other scored blunder "??". 257 D-10:
 * the popover names the type in words.
 *
 * Mirrors GemMoveBadge: the shared InfoPopover shell (a span trigger, so no nested
 * <button> inside the mobile move chip) and a wrapper that stops click/pointer
 * propagation so a tap opens the popover instead of navigating to the move.
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { FacepalmExplanation } from '@/components/library/FacepalmExplanation';
import { BlunderIcon, FacepalmBlunderIcon } from '@/components/icons/SeverityGlyphIcon';
import { facepalmScoreLabel, isFacepalmBlunder } from '@/lib/facepalm';
import type { FacepalmType } from '@/types/library';

interface FacepalmGlyphBadgeProps {
  /** Raw 0..1 facepalm score. */
  score: number;
  /** Facepalm type of the blunder; named in the popover. */
  type: FacepalmType;
  /** True when the opponent played the blunder: switches the explanation wording. */
  byOpponent?: boolean;
  /** Size class of the move list's marker glyph. */
  className: string;
}

/** The "??" / "???" glyph of a scored blunder as the trigger of the facepalm score popover. */
export function FacepalmGlyphBadge({ score, type, byOpponent = false, className }: FacepalmGlyphBadgeProps) {
  // Same predicate as the move list's plain-glyph choice (severityIcon), so the two never disagree.
  const Icon = isFacepalmBlunder(score) ? FacepalmBlunderIcon : BlunderIcon;
  return (
    <span className="inline-flex align-middle" onClick={(e) => e.stopPropagation()} onPointerDown={(e) => e.stopPropagation()}>
      <InfoPopover
        ariaLabel={`${facepalmScoreLabel(score, type)}, what the score means`}
        testId="facepalm-glyph-popover"
        triggerContent={<Icon className={className} />}
        closeOnScroll
      >
        <div className="space-y-1">
          <FacepalmExplanation score={score} type={type} audience={byOpponent ? 'opponent' : 'self'} />
        </div>
      </InfoPopover>
    </span>
  );
}
