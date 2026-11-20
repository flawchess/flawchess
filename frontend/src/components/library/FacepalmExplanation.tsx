/**
 * The Facepalm score explanation, shared by every surface that shows the score:
 * the Flaws card chip popover (FacepalmBadgePopover) and the analysis move-list
 * mini-chip (FacepalmMoveChip). One copy, so the wording never drifts.
 * 257 D-10: one line names the facepalm type in words, so the chip tint is never the only signal.
 */

import { Gauge } from 'lucide-react';
import { FACEPALM_TYPE_LABEL, FACEPALM_TYPE_SENTENCE, toFacepalmPct } from '@/lib/facepalm';
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
      <p data-testid="facepalm-explanation-type">
        <span className="font-bold">{FACEPALM_TYPE_LABEL[type]}</span>: {FACEPALM_TYPE_SENTENCE[type]}
      </p>
      <p>
        How easy it is to see for a player at {byOpponent ? 'their' : 'your'} level that the move
        is a blunder, as estimated by our model. A high facepalm score means it should be easy to
        see, low means it's probably hard to see.
      </p>
    </>
  );
}
