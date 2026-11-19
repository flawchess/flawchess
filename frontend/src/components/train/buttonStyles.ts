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

/**
 * One underline tab, for a `ToggleGroupItem` in a row that carries a bottom rule
 * (Leaderboard game switch). Text only with a 2px active underline, so it does not
 * read like the filter pills or the segmented control below it. `-mb-px` lays the
 * underline over the row's rule; h-11 is the mobile touch height.
 */
export const TRAIN_UNDERLINE_TAB_CLASS =
  '-mb-px h-11 rounded-none! border-0 border-b-2 border-transparent bg-transparent px-3 text-sm text-muted-foreground hover:bg-transparent hover:text-foreground data-[state=on]:border-primary data-[state=on]:bg-transparent data-[state=on]:text-foreground sm:h-9';

/**
 * One segment of a joined segmented control, for a `ToggleGroupItem` in a
 * `spacing={0}` group (Leaderboard board switch in the card header). Same 32px
 * draw height and ::before tap area as the filter pill, without its full rounding
 * (the group rounds the outer corners).
 */
export const TRAIN_SEGMENT_CLASS =
  'relative h-8 px-3 text-sm before:absolute before:inset-x-0 before:-inset-y-2 sm:h-7 sm:before:hidden';
