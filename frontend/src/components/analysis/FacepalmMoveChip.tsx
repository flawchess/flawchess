/**
 * FacepalmMoveChip: the move-list mini-chip "<gauge> 95%" shown after the blunder
 * glyph when the blunder carries a facepalm score. Hover/tap opens the shared
 * Facepalm explanation. 257 D-08: tinted by the facepalm type (teal missed win, crimson allowed
 * loss); D-10: the popover and the aria-label name the type.
 *
 * FacepalmGlyphBadge: the "???" facepalm-blunder glyph itself, opening the same explanation
 * (257 D-22: a non-standard glyph gets a popover, like the gem/great badges).
 *
 * Mirrors GemMoveBadge: the shared InfoPopover shell (a span trigger, so no nested
 * <button> inside the mobile move chip) and a wrapper that stops click/pointer
 * propagation so a tap opens the popover instead of navigating to the move.
 */

import type { ReactNode } from 'react';
import { Gauge } from 'lucide-react';
import { InfoPopover } from '@/components/ui/info-popover';
import { FacepalmExplanation } from '@/components/library/FacepalmExplanation';
import { FacepalmBlunderIcon } from '@/components/icons/SeverityGlyphIcon';
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

/** The click-swallowing wrapper plus the popover shell shared by the chip and the glyph. */
function FacepalmPopover({
  score,
  type,
  byOpponent = false,
  ariaLabel,
  testId,
  className,
  trigger,
}: FacepalmMoveChipProps & { ariaLabel: string; testId: string; className: string; trigger: ReactNode }) {
  return (
    <span className={className} onClick={(e) => e.stopPropagation()} onPointerDown={(e) => e.stopPropagation()}>
      <InfoPopover ariaLabel={ariaLabel} testId={testId} triggerContent={trigger}>
        <div className="space-y-1">
          <FacepalmExplanation score={score} type={type} audience={byOpponent ? 'opponent' : 'self'} />
        </div>
      </InfoPopover>
    </span>
  );
}

export function FacepalmMoveChip({ score, type, byOpponent = false }: FacepalmMoveChipProps) {
  const pct = toFacepalmPct(score);
  const style = FACEPALM_TYPE_STYLE[type];
  return (
    <FacepalmPopover
      score={score}
      type={type}
      byOpponent={byOpponent}
      ariaLabel={`Facepalm ${pct}%, ${FACEPALM_TYPE_LABEL[type].toLowerCase()}, what the score means`}
      testId="facepalm-move-popover"
      className="inline-flex ml-0.5 align-middle"
      trigger={
        <span
          className="inline-flex items-center gap-0.5 rounded-full border px-1 font-sans text-sm font-bold leading-tight tabular-nums whitespace-nowrap"
          style={{ color: style.color, backgroundColor: style.bg, borderColor: style.border }}
        >
          <Gauge className="h-3 w-3" aria-hidden="true" />
          {pct}%
        </span>
      }
    />
  );
}

/** The "???" glyph of a facepalm blunder, sized by the move list's marker class. */
export function FacepalmGlyphBadge({
  score,
  type,
  byOpponent = false,
  className,
}: FacepalmMoveChipProps & { className: string }) {
  return (
    <FacepalmPopover
      score={score}
      type={type}
      byOpponent={byOpponent}
      ariaLabel="Facepalm blunder, what the ??? means"
      testId="facepalm-glyph-popover"
      className="inline-flex align-middle"
      trigger={<FacepalmBlunderIcon className={className} />}
    />
  );
}
