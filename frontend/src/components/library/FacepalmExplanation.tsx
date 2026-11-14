/**
 * The Facepalm score explanation, shared by every surface that shows the score:
 * the Flaws card chip popover (FacepalmBadgePopover) and the analysis move-list
 * mini-chip (FacepalmMoveChip). One copy, so the wording never drifts.
 */

import { TreePalm } from 'lucide-react';
import { toFacepalmPct } from '@/lib/facepalm';

interface FacepalmExplanationProps {
  /** Raw 0..1 facepalm score. */
  score: number;
  /** True when the opponent (not the user) played the blunder: switches "your" to "their". */
  byOpponent?: boolean;
}

export function FacepalmExplanation({ score, byOpponent = false }: FacepalmExplanationProps) {
  return (
    <>
      <p className="flex items-center gap-1 font-bold">
        <TreePalm className="h-3 w-3 shrink-0" aria-hidden="true" />
        Facepalm {toFacepalmPct(score)}%
      </p>
      <p>
        How easy it is to see for a player at {byOpponent ? 'their' : 'your'} level that the move
        is a blunder, as estimated by our model. A high facepalm score means it should be easy to
        see, low means it's probably hard to see.
      </p>
    </>
  );
}
