/**
 * FacepalmMoveChip: the move-list mini-chip "<palm> 95%" shown after the blunder
 * glyph when the blunder carries a facepalm score. Hover/tap opens the shared
 * Facepalm explanation. 257 D-08: tinted by the facepalm type (teal missed win, crimson allowed
 * loss); D-10: the popover and the aria-label name the type.
 *
 * Mirrors GemMoveBadge: the shared InfoPopover shell (a span trigger, so no nested
 * <button> inside the mobile move chip) and a wrapper that stops click/pointer
 * propagation so a tap opens the popover instead of navigating to the move.
 */

import { TreePalm } from 'lucide-react';
import { InfoPopover } from '@/components/ui/info-popover';
import { FacepalmExplanation } from '@/components/library/FacepalmExplanation';
import { FACEPALM_TYPE_LABEL, FACEPALM_TYPE_STYLE, toFacepalmPct } from '@/lib/facepalm';
import type { FacepalmType } from '@/types/library';

interface FacepalmMoveChipProps {
  /** Raw 0..1 facepalm score. */
  score: number;
  /** Facepalm type of the blunder; picks the tint and is named in the popover. */
  type: FacepalmType;
  /** True when the opponent played the blunder: switches the explanation wording. */
  byOpponent?: boolean;
}

export function FacepalmMoveChip({ score, type, byOpponent = false }: FacepalmMoveChipProps) {
  const pct = toFacepalmPct(score);
  const style = FACEPALM_TYPE_STYLE[type];
  return (
    <span
      className="inline-flex ml-0.5 align-middle"
      onClick={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <InfoPopover
        ariaLabel={`Facepalm ${pct}%, ${FACEPALM_TYPE_LABEL[type].toLowerCase()}, what the score means`}
        testId="facepalm-move-popover"
        triggerContent={
          <span
            className="inline-flex items-center gap-0.5 rounded-full border px-1 font-sans text-sm font-bold leading-tight tabular-nums whitespace-nowrap"
            style={{ color: style.color, backgroundColor: style.bg, borderColor: style.border }}
          >
            <TreePalm className="h-3 w-3" aria-hidden="true" />
            {pct}%
          </span>
        }
      >
        <div className="space-y-1">
          <FacepalmExplanation score={score} type={type} byOpponent={byOpponent} />
        </div>
      </InfoPopover>
    </span>
  );
}
