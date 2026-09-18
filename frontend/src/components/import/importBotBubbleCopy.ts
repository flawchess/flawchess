/**
 * Copy for `ImportBotBubble`, kept out of the component file so the exported
 * full-sentence strings do not trip `react-refresh/only-export-components`.
 */

export type ImportBotBubbleVariant = 'welcome' | 'explore' | 'signup-ask';

/**
 * Bubble copy as a sequence of plain strings and in-sentence links, so the
 * linked fragments render as real react-router `<Link>`s while the full
 * sentence stays available as one string (`copyText`) for tests and copy
 * review.
 */
export interface BubbleLinkPart {
  text: string;
  to: '/library/games' | '/train' | '/bots' | '/openings' | '/endgames';
  /** Suffix for `data-testid="import-bot-bubble-link-<slug>"`. */
  slug: string;
}
export type BubblePart = string | BubbleLinkPart;

const WELCOME_PARTS: readonly BubblePart[] = [
  "Welcome! First, let's import your games. Or ",
  { text: 'challenge me to a game', to: '/bots', slug: 'challenge' },
  ' if you dare!',
];

// Shown to registered accounts after their first import; the guest variant
// appends the sign-up payoff to the same sentence.
const EXPLORE_PARTS: readonly BubblePart[] = [
  { text: 'Analyze your games', to: '/library/games', slug: 'games' },
  ', try ',
  { text: 'a training session', to: '/train', slug: 'train' },
  ', ',
  { text: 'challenge me to a game', to: '/bots', slug: 'challenge' },
  ', or explore your ',
  { text: 'openings', to: '/openings', slug: 'openings' },
  ' and ',
  { text: 'endgames', to: '/endgames', slug: 'endgames' },
  '.',
];

const SIGNUP_ASK_PARTS: readonly BubblePart[] = [
  ...EXPLORE_PARTS,
  ' If you sign up free, we start analyzing all your games in the background.',
];

function copyText(parts: readonly BubblePart[]): string {
  return parts.map((part) => (typeof part === 'string' ? part : part.text)).join('');
}

export const IMPORT_WELCOME_COPY = copyText(WELCOME_PARTS);
export const IMPORT_EXPLORE_COPY = copyText(EXPLORE_PARTS);
export const IMPORT_GUEST_SIGNUP_COPY = copyText(SIGNUP_ASK_PARTS);

export const PARTS_BY_VARIANT: Record<ImportBotBubbleVariant, readonly BubblePart[]> = {
  welcome: WELCOME_PARTS,
  explore: EXPLORE_PARTS,
  'signup-ask': SIGNUP_ASK_PARTS,
};
