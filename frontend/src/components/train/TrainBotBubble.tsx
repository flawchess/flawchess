/**
 * TrainBotBubble — the ONE chat-row slot under the board.
 * Purely presentational: no data fetching, no Train domain logic. A left
 * avatar column (persona art + name) and a right speech bubble carrying
 * whatever copy/actions the caller passes — `resolveBubbleState` (the
 * caller's job, via `trainBubbleState.ts`) decides WHAT state is active;
 * this component only renders it.
 */

import type { ReactElement, ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { placeholderAvatarFor, resolveAvatarSrc } from '@/lib/personas/personaAvatars';
import type { Persona } from '@/lib/personas/personaRegistry';
import { prefersReducedMotion } from '@/lib/confetti';
import { TRAIN_BUBBLE_BORDER, TRAIN_BUBBLE_NUDGE_BORDER } from '@/lib/theme';
import type { TrainBubbleState } from '@/components/train/trainBubbleState';

/**
 * Avatar size for the Train chat row, deliberately its own size; each surface
 * picks what fits its layout. 80px (`size-20`) on `sm+`, which must not
 * change.
 *
 * On phones (`max-sm`) the avatar column collapses into a compact avatar +
 * name header (55px) ABOVE the bubble instead of a column BESIDE it, so the
 * copy gets the whole bubble width.
 */
const TRAIN_BOT_AVATAR_CLASS = 'size-[55px] sm:size-20';

/**
 * The /train landing's host bubble: one size step larger on both breakpoints
 * than the solve loop's avatar (which must not move).
 */
const TRAIN_BOT_AVATAR_LARGE_CLASS = 'size-14 sm:size-24';

export type TrainBotAvatarSize = 'default' | 'large';

const AVATAR_SIZE_CLASS: Record<TrainBotAvatarSize, string> = {
  default: TRAIN_BOT_AVATAR_CLASS,
  large: TRAIN_BOT_AVATAR_LARGE_CLASS,
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
  /** Avatar size step; only the /train landing page uses `'large'`. */
  avatarSize?: TrainBotAvatarSize;
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
}: TrainBotBubbleProps): ReactElement {
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
      className="flex w-full flex-col gap-2 sm:flex-row sm:items-start sm:gap-3"
      data-testid="train-bot-bubble"
      data-state={state}
      data-nudge={isNudge ? 'true' : undefined}
    >
      <div className="flex shrink-0 flex-row items-center gap-2 sm:flex-col sm:gap-1">
        <TrainBotAvatar
          persona={persona}
          className={cn('text-xl sm:text-3xl', AVATAR_SIZE_CLASS[avatarSize])}
        />
        <span className="text-sm font-medium text-foreground" data-testid="train-bot-name">
          {persona.name}
        </span>
      </div>
      <div
        key={nudgeNonce}
        className={cn(
          'relative min-w-0 flex-1 rounded-2xl border-2 bg-background px-4 py-3',
          !prefersReducedMotion() && pulses && 'animate-train-bubble-nudge',
        )}
        style={{ borderColor }}
      >
        {/* Tail — a rotated square clipped to two of its borders, the classic
            CSS speech-bubble triangle, so it always tracks the bubble's
            current border color. Points left at the avatar column on `sm+`;
            on phones the avatar header sits ABOVE the bubble, so the tail
            points up from the top-left corner instead. */}
        <div
          aria-hidden="true"
          className="absolute h-3 w-3 rotate-45 bg-background max-sm:-top-[7px] max-sm:left-4 max-sm:border-l-2 max-sm:border-t-2 sm:-left-[7px] sm:top-4 sm:border-b-2 sm:border-l-2"
          style={{ borderColor }}
        />
        <div className="text-sm" data-testid="train-bot-copy">
          {children}
        </div>
        {/* The action row sits bottom-RIGHT inside the bubble, where a phone
            thumb reaches it. */}
        {actions !== undefined && (
          <div className="mt-2 flex flex-wrap justify-end gap-2">{actions}</div>
        )}
      </div>
    </div>
  );
}
