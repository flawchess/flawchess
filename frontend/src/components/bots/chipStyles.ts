/**
 * chipStyles — the ONE definition of the Bots setup screen's toggle-chip look,
 * shared by every chip grid on that screen (`SetupScreen`'s color + time-control
 * chips, `PlayStyleControl`'s Human/Light/Deep preset chips).
 *
 * These are layout/state utility classes over existing semantic theme tokens
 * (`toggle-active`, `inactive-bg`), not new color values, so they live here
 * rather than in `theme.ts` (which owns the token VALUES these classes
 * reference). Don't re-type them inline.
 */

/** Shape + type + transition. `h-10` on touch, `sm:h-7` on desktop — a
 * DELIBERATE MILD DEVIATION from the 44px WCAG 2.5.5 / Apple HIG minimum
 * (`h-11`), taken specifically to lift the Bots setup screen's primary Start
 * CTA above the fold. 40px is the FLOOR — do not go
 * lower than `h-10` for any chip on this screen. This one constant covers
 * every chip here (TC, colour, and `PlayStyleControl`'s Human/Light/Deep
 * presets), so this is the only place the chip height is expressed. */
export const CHIP_BASE_CLASS = 'rounded border h-10 sm:h-7 text-sm transition-colors';

/** Selected state. */
export const CHIP_ACTIVE_CLASS =
  'border-toggle-active bg-toggle-active text-toggle-active-foreground';

/** Unselected state. Hover affordances are `pointer-fine:`-gated so they never
 * latch on touch devices. */
export const CHIP_INACTIVE_CLASS =
  'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground';

/** The ONE height for every bot-play action button — the in-game
 * Resign control, the resume + discard + resign confirmations,
 * and the game-result actions. `h-12` (48px) matches the roster's "Custom"
 * and the detail surface's "Play" CTA; `size="sm"`'s 28px would be far
 * under the 44px WCAG 2.5.5 / Apple HIG touch minimum. `px-4` keeps the
 * horizontal padding proportionate to the taller box. Applied via
 * `className` (tailwind-merge lets it win over the size variant's `h-*`). */
export const BOT_ACTION_BUTTON_CLASS = 'h-12 px-4';
