/**
 * FacepalmMoveChip: the move-list mini-chip "<palm> 95%" shown after the blunder
 * glyph when the blunder carries a facepalm score. Hover/tap opens the shared
 * Facepalm explanation.
 *
 * Mirrors GemMoveBadge: the shared InfoPopover shell (a span trigger, so no nested
 * <button> inside the mobile move chip) and a wrapper that stops click/pointer
 * propagation so a tap opens the popover instead of navigating to the move.
 */

import { TreePalm } from 'lucide-react';
import { InfoPopover } from '@/components/ui/info-popover';
import { FacepalmExplanation } from '@/components/library/FacepalmExplanation';
import { FACEPALM_CHIP, FACEPALM_CHIP_BG } from '@/lib/theme';
import { toFacepalmPct } from '@/lib/facepalm';

interface FacepalmMoveChipProps {
  /** Raw 0..1 facepalm score. */
  score: number;
  /** True when the opponent played the blunder: switches the explanation wording. */
  byOpponent?: boolean;
}

export function FacepalmMoveChip({ score, byOpponent = false }: FacepalmMoveChipProps) {
  const pct = toFacepalmPct(score);
  return (
    <span
      className="inline-flex ml-0.5 align-middle"
      onClick={(e) => e.stopPropagation()}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <InfoPopover
        ariaLabel={`Facepalm ${pct}%, what the score means`}
        testId="facepalm-move-popover"
        triggerContent={
          <span
            className="inline-flex items-center gap-0.5 rounded-full border px-1 font-sans text-sm font-bold leading-tight tabular-nums whitespace-nowrap"
            style={{ color: FACEPALM_CHIP, backgroundColor: FACEPALM_CHIP_BG, borderColor: FACEPALM_CHIP }}
          >
            <TreePalm className="h-3 w-3" aria-hidden="true" />
            {pct}%
          </span>
        }
      >
        <div className="space-y-1">
          <FacepalmExplanation score={score} byOpponent={byOpponent} />
        </div>
      </InfoPopover>
    </span>
  );
}
