/**
 * Eval-chart flaw dot colour, keyed by the display category (Phase 260 D-17).
 *
 * A facepalm blunder is drawn in SEV_FACEPALM, for either side and in every dot state
 * (normal, highlighted, dimmed); every other blunder stays SEV_BLUNDER. This reverses the
 * 257 D-22 exclusion of chart dots from the facepalm treatment. The category comes from
 * `flawMoveCategory` (D-07), the one classifier shared with the move quality table, so the
 * chart, the table and the board agree on which moves are facepalms. No new theme constant.
 *
 * A plain module, not EvalChart.tsx, so the colour binding is unit-testable without mounting
 * recharts (same rationale as bestMoveDot.ts).
 */

import { flawMoveCategory, type FlawMoveCategory } from '@/lib/moveStatsCounts';
import { SEV_BLUNDER, SEV_FACEPALM, SEV_INACCURACY, SEV_MISTAKE } from '@/lib/theme';
import type { FlawMarker } from '@/types/library';

const FLAW_CATEGORY_COLOR: Record<FlawMoveCategory, string> = {
  facepalm: SEV_FACEPALM,
  blunder: SEV_BLUNDER,
  mistake: SEV_MISTAKE,
  inaccuracy: SEV_INACCURACY,
};

/** Colour of a flaw marker's chart dot and tooltip verdict; independent of `is_user`. */
export function flawMarkerColor(marker: Pick<FlawMarker, 'severity' | 'facepalm_score'>): string {
  return FLAW_CATEGORY_COLOR[flawMoveCategory(marker)];
}
