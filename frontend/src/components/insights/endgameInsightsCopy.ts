/**
 * Copy for the Endgames Insights host bubble (quick 260927-b05).
 *
 * Shelly the Turtle is the page's FIXED host: Endgames is a data page, not a
 * social one, so it gets one stable character instead of the /train and
 * /bots daily rotation. She is a Wall persona (patience, trading down), which
 * is the register of every line below.
 */

import type { PersonaId } from '@/lib/personas/personaRegistry';

export const INSIGHTS_HOST_ID: PersonaId = 'wall-1200';

/** Why the Generate / Try again action is disabled, or null when it isn't. */
export type BlockedReason = 'import-running' | 'filters-not-default' | 'custom-opponent-strength';

export const INSIGHTS_BUBBLE_COPY = {
  idle:
    'Want me to help you interpret your game data? ' +
    "I'll create your player profile, analyze your endgame data, and suggest what to work on.",
  pending: 'Reading through your endgames now, slow and steady. This takes around 30 seconds.',
  error: "Something went wrong on my end and I couldn't finish your report. Try again in a moment.",
} as const;

/** Shelly's explanation for a blocked action, shown inside the bubble. */
export const BLOCKED_REASON_BUBBLE_COPY: Record<BlockedReason, string> = {
  'import-running': "Your games are still importing. Let the import finish and I'll read everything at once.",
  'filters-not-default':
    "I only read your endgames with the default filters (opponent strength can stay). Reset the others and I'll get started.",
  'custom-opponent-strength':
    "Set opponent strength to one of the presets (Any, Stronger, Similar or Weaker) and I'll get started.",
};

/** Terse tooltip on the report card's Regenerate button (the bubble is hidden there). */
export const BLOCKED_REASON_TOOLTIP: Record<BlockedReason, string> = {
  'import-running': 'Wait for import to finish',
  'filters-not-default': 'Reset the filters before generating insights',
  'custom-opponent-strength': 'Snap opponent strength to a preset (Any / Stronger / Similar / Weaker)',
};
