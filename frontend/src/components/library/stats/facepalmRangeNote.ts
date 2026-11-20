import { COPY_CHANCE } from '@/components/endgames/stats/rankedMetrics';
import { GAP_SAME_WORD, gapWords, type GapCell } from '@/lib/gapBar';

/** 257 D-16 / orchestrator decision 3: no benchmark band exists yet, so no range is shown. */
const COPY_NO_RANGE = 'There is no typical range for facepalm blunders yet.';

/**
 * 257 D-13: significance may be stated, it drives no colour. These two sentences (this one and
 * COPY_CHANCE) describe the gap, not the score, so they sit outside D-05's probability ban;
 * the owner confirms this reading at UAT.
 */
const COPY_GAP_SIGNIFICANT = 'The gap is too large to be chance.';

/**
 * The popover's first list item: the no-range sentence plus what the significance says. Shared
 * with the Facepalm blunders tile of Flaw Stats.
 */
export function facepalmRangeNote(cell: GapCell): string {
  if (cell.significant) return `${COPY_NO_RANGE} ${COPY_GAP_SIGNIFICANT}`;
  const isSame = cell.delta === null || gapWords(cell.delta) === GAP_SAME_WORD;
  return isSame ? COPY_NO_RANGE : `${COPY_NO_RANGE} ${COPY_CHANCE}`;
}
