/**
 * The Facepalm score explanation, shared by every surface that shows the score:
 * the Flaws card chip popover (FacepalmBadgePopover) and the analysis move-list
 * mini-chip and "???" glyph (FacepalmMoveChip). One copy, so the wording never drifts.
 * 257 D-10: one line names the facepalm type in words, so the chip tint is never the only signal.
 */

import { Gauge } from 'lucide-react';
import { FacepalmBlunderIcon } from '@/components/icons/SeverityGlyphIcon';
import {
  FACEPALM_HIGH_CUTOFF,
  FACEPALM_TYPE_LABEL,
  FACEPALM_TYPE_SENTENCE,
  facepalmScoreMeaning,
  isFacepalmBlunder,
  toFacepalmPct,
} from '@/lib/facepalm';
import type { FacepalmType } from '@/types/library';

interface FacepalmExplanationProps {
  /** Raw 0..1 facepalm score. */
  score: number;
  /** Facepalm type of the blunder; named in the first line. */
  type: FacepalmType;
  /** True when the opponent (not the user) played the blunder: switches "your" to "their". */
  byOpponent?: boolean;
}

export function FacepalmExplanation({ score, type, byOpponent = false }: FacepalmExplanationProps) {
  return (
    <>
      <p className="flex items-center gap-1 font-bold">
        <Gauge className="h-3 w-3 shrink-0" aria-hidden="true" />
        Facepalm {toFacepalmPct(score)}%
      </p>
      {/* 257 D-22: ties the non-standard "???" badge to the 70% cut, on every surface showing the score. */}
      <p className="flex items-center gap-1" data-testid="facepalm-explanation-blunder">
        <FacepalmBlunderIcon className="h-3 w-3 shrink-0" />
        {isFacepalmBlunder(score)
          ? `Facepalm blunder: a facepalm score of ${FACEPALM_HIGH_CUTOFF}% or more.`
          : `${FACEPALM_HIGH_CUTOFF}% or more counts as a facepalm blunder.`}
      </p>
      <p data-testid="facepalm-explanation-type">
        <span className="font-bold">{FACEPALM_TYPE_LABEL[type]}</span>: {FACEPALM_TYPE_SENTENCE[type]}
      </p>
      <p>{facepalmScoreMeaning(byOpponent)}</p>
    </>
  );
}
