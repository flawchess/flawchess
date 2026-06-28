/**
 * tacticArrows — shared board-arrow builders for the /analysis page.
 *
 * Relocated from the deleted TacticModeOverlay.tsx (Quick 260627-l2z, item 1).
 * `buildPvArrow` drives the depth-countdown overlay arrow shown while navigating a
 * tactic PV sideline in game mode.
 */

import type { BoardArrow } from '@/components/board/ChessBoard';
import type { TacticDepthOrientation } from '@/lib/tacticDepth';
import {
  PAYOFF_MOVE_ARROW,
  TAC_MISSED,
  TAC_ALLOWED,
  TAC_MISSED_LABEL,
  TAC_ALLOWED_LABEL,
} from '@/lib/theme';

/** Arrow stroke width — matches the analysis-board overlay arrows. */
const ARROW_WIDTH = 0.5;

/**
 * Build the single engine-PV arrow for a PV-sideline move.
 *
 * Quick 260628-ojq UAT: every countdown arrow up to and including the punchline (depth 1)
 * is painted in the line's orientation color — crimson for an allowed tactic, teal for a
 * missed one — so the arrows match the orientation-colored sideline move list. At depth 0
 * (the move after the tactic resolves) the caller passes isPayoff, and the arrow drops to
 * the lighter neutral payoff color with no label (Quick 260628-pu2 UAT).
 */
export function buildPvArrow(
  lastMove: { from: string; to: string } | null,
  displayDepth: number,
  isPayoff: boolean,
  orientation: TacticDepthOrientation,
): BoardArrow[] {
  if (!lastMove) return [];
  const tacticColor = orientation === 'missed' ? TAC_MISSED : TAC_ALLOWED;
  const tacticLabelColor = orientation === 'missed' ? TAC_MISSED_LABEL : TAC_ALLOWED_LABEL;
  return [
    {
      startSquare: lastMove.from,
      endSquare: lastMove.to,
      color: isPayoff ? PAYOFF_MOVE_ARROW : tacticColor,
      width: ARROW_WIDTH,
      label: isPayoff ? undefined : String(displayDepth),
      labelColor: isPayoff ? undefined : tacticLabelColor,
    },
  ];
}
