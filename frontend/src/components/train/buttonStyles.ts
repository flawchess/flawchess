/**
 * buttonStyles — the ONE definition of the Train page's button sizing, shared
 * by every primary (`default`) / secondary (`brand-outline`) button on /train
 * (start screen, solve screen, reveal, score screen).
 *
 * Mobile matches the Bots Play/Start CTA's 48px touch height (the Button
 * component's default `h-8`, 32px, is far below the 44px touch minimum);
 * `sm:h-8` keeps the compact desktop default.
 *
 * These are sizing utilities over the existing Button variants, not new colors,
 * so they live here (mirroring `components/bots/chipStyles.ts`) rather than in
 * `theme.ts`.
 */

/** Height only, for buttons that already get their width from a flex row or
 * sit inline. */
export const TRAIN_BUTTON_CLASS = 'h-12 sm:h-8';

/** Height + mobile full width — for standalone CTAs, the direct analog of the
 * Bots Play button. */
export const TRAIN_CTA_BUTTON_CLASS = 'h-12 w-full sm:h-8 sm:w-auto';

/**
 * One filter pill, for a `ToggleGroupItem` (Archive lists, Leaderboard boards).
 *
 * A plain min-h-11 made the pills visibly too tall on mobile. The pill is drawn at
 * 32px and the transparent ::before keeps its tap area above 44px (46px: the inset
 * is measured from inside the 1px border, so -inset-y-1.5 only reached 42px).
 */
export const TRAIN_FILTER_PILL_CLASS =
  'relative h-8 rounded-full px-3 text-sm before:absolute before:inset-x-0 before:-inset-y-2 sm:h-7 sm:before:hidden';

/** Gap between filter pills, for `ToggleGroup`'s `spacing` prop (Tailwind units). */
export const TRAIN_FILTER_PILL_SPACING = 2;
