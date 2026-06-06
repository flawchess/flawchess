/**
 * Human-readable labels and metadata for FlawTags.
 *
 * TAG_DEFINITIONS was removed in Phase 108 Plan 08 (D-05): TagChip is now a
 * navigation trigger rather than a popover info chip, so the definition text
 * is no longer displayed. TAG_LABELS is retained for FlawFilterControl buttons.
 */

import type { FlawTag } from '@/types/library';

// ─── Tag display labels ───────────────────────────────────────────────────────

/**
 * Human-readable bold label for each FlawTag (title-cased, hyphen as space).
 * Used in the popover heading.
 */
export const TAG_LABELS: Record<FlawTag, string> = {
  'low-clock': 'Low clock',
  'impatient': 'Impatient',
  'considered': 'Considered',
  'miss': 'Miss',
  'lucky-escape': 'Lucky escape',
  'while-ahead': 'While ahead',
  'result-changing': 'Result changing',
  'opening': 'Opening',
  'middlegame': 'Middlegame',
  'endgame': 'Endgame',
};
