/**
 * TrainBotBubble — the ONE chat-row slot under the board.
 * Purely presentational: no data fetching, no Train domain logic. A speech bubble
 * carrying whatever copy/actions the caller passes, plus the persona's avatar —
 * `resolveBubbleState` (the caller's job, via `trainBubbleState.ts`) decides WHAT
 * state is active; this component only renders it.
 *
 * Two layouts, mounted exclusively through `useIsSmUp` (one placement in the DOM, the
 * convention the reveal action bar uses): from `sm` up, an avatar + name column BESIDE the
 * bubble with a left-pointing tail. On phones, the avatar is floated top-left INSIDE the
 * bubble (no name row, no tail), so the bubble costs far less height. The landscape band
 * (`useIsTrainSideBand`: 640-1023px wide in landscape) uses the same compact layout, since
 * the Train side column there is narrow and the screen is short, and so does the portrait
 * band (`useIsPortraitSmBand`: 640-767px wide, unfolded foldables and small tablets). A CSS-only single node
 * is not clean here: on phones the avatar must sit inside the bubble's border, while from
 * `sm` up it lives in a column whose width comes from the name and which sets the row's
 * minimum height; absolute positioning on `sm+` would lose both.
 *
 * Bug fix (Galaxy Z Fold8 cover screen): the old phone header row (55px avatar plus the name
 * above the bubble, with an up-pointing tail) cost about 63px and pushed the blunder-check
 * Ready button behind the bottom tab bar.
 */

import type { ReactElement, ReactNode } from 'react';
import { useIsPortraitSmBand, useIsSmUp, useIsTrainSideBand } from '@/hooks/useIsDesktop';
import { cn } from '@/lib/utils';
import { placeholderAvatarFor, resolveAvatarSrc } from '@/lib/personas/personaAvatars';
import type { Persona } from '@/lib/personas/personaRegistry';
import { prefersReducedMotion } from '@/lib/confetti';
import { TRAIN_BUBBLE_BORDER, TRAIN_BUBBLE_NUDGE_BORDER } from '@/lib/theme';
import type { TrainBubbleState } from '@/components/train/trainBubbleState';

/**
 * Avatar size for the Train chat row's `sm+` column, deliberately its own size; each
 * surface picks what fits its layout. 80px (`size-20`), which must not change.
 */
const TRAIN_BOT_AVATAR_CLASS = 'size-20 text-3xl';

/**
 * The /train landing's host bubble: one size step larger than the solve loop's avatar
 * (which must not move).
 */
const TRAIN_BOT_AVATAR_LARGE_CLASS = 'size-24 text-3xl';

/**
 * The phone avatar floated inside the bubble. Default is 40px (`size-10`), the height of
 * two `text-sm` lines (2 x 20px), so the first two copy lines wrap beside it.
 */
const TRAIN_BOT_FLOAT_AVATAR_CLASS = 'size-10 text-xl';

/** The large step's floated avatar: the 96/80 column ratio applied to 40px, about 48px, on the 4px grid. */
const TRAIN_BOT_FLOAT_AVATAR_LARGE_CLASS = 'size-12 text-2xl';

export type TrainBotAvatarSize = 'default' | 'large';

const AVATAR_SIZE_CLASS: Record<TrainBotAvatarSize, string> = {
  default: TRAIN_BOT_AVATAR_CLASS,
  large: TRAIN_BOT_AVATAR_LARGE_CLASS,
};

const FLOAT_AVATAR_SIZE_CLASS: Record<TrainBotAvatarSize, string> = {
  default: TRAIN_BOT_FLOAT_AVATAR_CLASS,
  large: TRAIN_BOT_FLOAT_AVATAR_LARGE_CLASS,
};

export interface TrainBotBubbleProps {
  persona: Persona;
  /** Drives the `data-state` attribute and the nudge border/pulse styling. */
  state: TrainBubbleState['kind'];
  /**
   * Bumped by the caller on every drop-before-guess nudge. Used as the
   * bubble's own React `key` so a REPEATED nudge remounts the element and
   * replays the pulse animation — a class toggle alone cannot restart an
   * already-running CSS animation on a node that never unmounts.
   */
  nudgeNonce?: number;
  /** The bubble's copy for the current state. */
  children: ReactNode;
  /** Optional action row (guess buttons, or Next/Solution/Analyze), rendered
   * as its own row INSIDE the bubble, below `children`. */
  actions?: ReactNode;
  /** Avatar size step (column on `sm+`, floated avatar on phones); only the /train landing page uses `'large'`. */
  avatarSize?: TrainBotAvatarSize;
  /**
   * Replaces the avatar (the blunder-check countdown ring). It sits BESIDE the bubble on
   * every breakpoint, phones included, with the left-pointing tail, so it costs no extra row
   * under the board. The compact floated-avatar layout does not apply to it.
   */
  leading?: ReactNode;
}

/** The persona's round avatar (art, or the emoji placeholder on its tint). */
export function TrainBotAvatar({
  persona,
  className,
}: {
  persona: Persona;
  className: string;
}): ReactElement {
  const avatar = placeholderAvatarFor(persona);
  const avatarSrc = resolveAvatarSrc(persona);
  return (
    <span
      aria-hidden="true"
      className={cn('flex items-center justify-center overflow-hidden rounded-full', className)}
      style={{ backgroundColor: avatar.tint }}
      data-testid="train-bot-avatar"
    >
      {avatarSrc !== undefined ? (
        <img src={avatarSrc} alt="" loading="lazy" className="h-full w-full object-cover" />
      ) : (
        avatar.emoji
      )}
    </span>
  );
}

export function TrainBotBubble({
  persona,
  state,
  nudgeNonce,
  children,
  actions,
  avatarSize = 'default',
  leading,
}: TrainBotBubbleProps): ReactElement {
  const isSmUp = useIsSmUp();
  const isSideBand = useIsTrainSideBand();
  const sideBySide = leading !== undefined;
  // Phones without a leading slot: the avatar floats inside the bubble. Also the landscape
  // band (640-1023px wide in landscape), where the Train side column is narrow and
  // an avatar + name column beside the bubble wrapped short copy onto four lines.
  // And a portrait foldable (640-767px wide in portrait), which reads like a phone.
  const isPortraitSmBand = useIsPortraitSmBand();
  const compact = !sideBySide && (!isSmUp || isSideBand || isPortraitSmBand);
  const isNudge = state === 'drop-nudge';
  // `resolveBubbleState` ranks `intro` above `drop-nudge`, so a piece dropped
  // while Hilda's guess step is up keeps the intro copy: a nudge must not
  // destroy the current intro step. The pulse therefore also replays on
  // an intro-state nudge (the `nudgeNonce` remount key restarts it); only the
  // copy swap and the nudge border stay exclusive to the `drop-nudge` state.
  const pulses = isNudge || (state === 'intro' && (nudgeNonce ?? 0) > 0);
  const borderColor = isNudge ? TRAIN_BUBBLE_NUDGE_BORDER : TRAIN_BUBBLE_BORDER;

  return (
    <div
      className={cn('flex w-full', !compact && 'flex-row items-start gap-3')}
      role={compact ? 'group' : undefined}
      aria-label={compact ? persona.name : undefined}
      data-testid="train-bot-bubble"
      data-state={state}
      data-nudge={isNudge ? 'true' : undefined}
    >
      {sideBySide && leading}
      {!sideBySide && !compact && (
        <div className="flex shrink-0 flex-col items-center gap-1">
          <TrainBotAvatar persona={persona} className={AVATAR_SIZE_CLASS[avatarSize]} />
          <span className="text-sm font-medium text-foreground" data-testid="train-bot-name">
            {persona.name}
          </span>
        </div>
      )}
      <div
        key={nudgeNonce}
        className={cn(
          'relative min-w-0 flex-1 rounded-2xl border-2 bg-background px-4 py-3',
          // Contains the floated avatar.
          compact && 'flow-root',
          !prefersReducedMotion() && pulses && 'animate-train-bubble-nudge',
        )}
        style={{ borderColor }}
      >
        {/* Tail — a rotated square clipped to two of its borders, the classic
            CSS speech-bubble triangle, so it always tracks the bubble's
            current border color. Points left at the avatar column; the compact
            phone layout has the avatar inside the bubble, so it has no tail. */}
        {!compact && (
          <div
            aria-hidden="true"
            className="absolute -left-[7px] top-4 h-3 w-3 rotate-45 border-b-2 border-l-2 bg-background"
            style={{ borderColor }}
          />
        )}
        {compact && (
          <TrainBotAvatar
            persona={persona}
            className={cn('float-left mr-3', FLOAT_AVATAR_SIZE_CLASS[avatarSize])}
          />
        )}
        <div className="text-sm" data-testid="train-bot-copy">
          {children}
        </div>
        {/* The action row sits bottom-RIGHT inside the bubble, where a phone
            thumb reaches it. On phones it is NOT cleared past the floated avatar:
            a flex container establishes its own formatting context, so it is laid
            out beside the float (narrowed) with `justify-end` putting the buttons
            at the bottom right next to the avatar. It drops below the avatar only
            when the copy is taller than the avatar or the buttons do not fit beside it. */}
        {actions !== undefined && (
          <div className="mt-2 flex flex-wrap justify-end gap-2">{actions}</div>
        )}
      </div>
    </div>
  );
}
