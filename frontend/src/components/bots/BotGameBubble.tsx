/**
 * BotGameBubble — Phase 223 (BOTVOICE-01/02): the in-game speech bubble
 * beside the bot's avatar. Purely presentational: no data fetching, no bot-
 * game domain logic — `useBotGameVoice` (the caller's job) decides WHICH
 * line is live; this component only renders it. Shares its border token
 * with `TrainBotBubble` (`TRAIN_BUBBLE_BORDER`) so the two bubble surfaces
 * read as one system, but is otherwise a sibling, not a variant: this
 * bubble keeps the avatar BESIDE the copy on every breakpoint (D-07's fixed
 * two-line height needs a stable, non-stacking layout), carries no name
 * anywhere (both breakpoints show it in their player rows), and has no
 * timer, transition, animation or nonce-remount key of any kind (D-07).
 *
 * Phase 223 UAT: while there is nothing to say (no live line, no actions)
 * the bubble box is `invisible` — hidden, but still laid out at its full
 * fixed height, so the avatar keeps its place and the board's fit-to-
 * viewport measurement (D-07) still sees a constant slot. Only the box hides;
 * the avatar stays as the bot's presence beside the board.
 *
 * Phase 223 (BOTVOICE-05, D-12): also renders in a PERSONA-LESS form when
 * `persona` is `null` but `actions` is supplied — a Custom game has no
 * persona to key copy off, but its bot can still offer a draw. That form
 * omits the avatar entirely and shows `BOT_DRAW_OFFER_FALLBACK_COPY`
 * (ignoring `line`, since there is no copy table to look it up in). This is
 * the ONLY persona-less copy in the phase; no other trigger gets a generic
 * voice.
 */

import type { ReactElement, ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { placeholderAvatarFor, resolveAvatarSrc } from '@/lib/personas/personaAvatars';
import type { Persona } from '@/lib/personas/personaRegistry';
import { TRAIN_BUBBLE_BORDER } from '@/lib/theme';
import { botLineCopy, type BotLineKey } from '@/lib/botGameCopy';

/**
 * Avatar size for the in-game bubble — deliberately its own size, not
 * shared with `TrainBotBubble`'s Train-specific sizes; each surface picks
 * its own.
 *
 * Phase 223 UAT: scaled up 50% from the 48/56px the phase shipped with
 * (`size-12 sm:size-14`) — the bot's face is the whole point of the
 * immersive layout and read as an afterthought at the smaller size. 72px on
 * phones, 84px on `sm` and above. The mobile cost is real and accepted
 * (RESEARCH Pitfall 11: every px here is a px the copy box and the board
 * width do not get), and it stays a CONSTANT height either way, so D-07's
 * fixed bubble slot still measures the same on every render.
 */
export const BOT_GAME_AVATAR_CLASS = 'size-18 sm:size-21';

/**
 * The copy node's fixed-height + type-size classes (D-07): the min-height
 * is exactly two `text-sm` lines, so the slot never collapses when `line` is
 * `null` and never grows when it is set — the board's fit-to-viewport
 * measurement (`useFitBoardToViewport`) sees a constant height either way.
 *
 * Bug fix (Phase 223 UAT): `index.css` lifts `.text-sm` to 1rem/1.5rem below
 * the `sm` breakpoint (the mobile typography bump), so two lines are 48px on
 * phones, not Tailwind's default 40px. A single `min-h-10` let the slot grow
 * from 60px to 68px the moment a line landed and pushed the board down 8px,
 * exactly the resize D-07 forbids. `min-h-12` below `sm` and `min-h-10` at
 * `sm+` track the same 639.98px boundary the stylesheet uses.
 */
export const BOT_GAME_BUBBLE_COPY_CLASS = 'flex min-h-12 items-center text-sm sm:min-h-10';

/**
 * Phase 223 (BOTVOICE-05, D-12): the generic offer sentence, preserved
 * verbatim from the retired draw-offer banner component's
 * `personaName == null` fallback — used ONLY by the persona-less bubble
 * form below.
 */
export const BOT_DRAW_OFFER_FALLBACK_COPY = 'The bot offers a draw';

export interface BotGameBubbleProps {
  /** `null` renders nothing UNLESS `actions` is supplied (see the
   * persona-less form in this file's header comment) — the copy tables are
   * keyed by `PersonaId` (D-08), and a Custom game has no persona. */
  persona: Persona | null;
  line: BotLineKey | null;
  /** Optional action row (e.g. a live draw offer's Accept/Decline),
   * rendered inside the bubble, below the copy. */
  actions?: ReactNode;
}

export function BotGameBubble({ persona, line, actions }: BotGameBubbleProps): ReactElement | null {
  if (persona === null && actions === undefined) return null;

  const avatar = persona !== null ? placeholderAvatarFor(persona) : null;
  const avatarSrc = persona !== null ? resolveAvatarSrc(persona) : undefined;
  const copy =
    persona !== null ? (line !== null ? botLineCopy(line, persona.id) : '') : BOT_DRAW_OFFER_FALLBACK_COPY;
  const silent = copy === '' && actions === undefined;

  return (
    <div className="flex w-full items-start gap-2" data-testid="bot-game-bubble">
      {avatar !== null && (
        <span
          aria-hidden="true"
          className={cn(
            'flex shrink-0 items-center justify-center overflow-hidden rounded-full text-3xl',
            BOT_GAME_AVATAR_CLASS,
          )}
          style={{ backgroundColor: avatar.tint }}
          data-testid="bot-game-avatar"
        >
          {avatarSrc !== undefined ? (
            <img src={avatarSrc} alt="" loading="lazy" className="h-full w-full object-cover" />
          ) : (
            avatar.emoji
          )}
        </span>
      )}
      <div
        className={cn(
          'relative min-w-0 flex-1 rounded-2xl border-2 bg-background px-4 py-2',
          silent && 'invisible',
        )}
        style={{ borderColor: TRAIN_BUBBLE_BORDER }}
        data-testid="bot-game-bubble-box"
      >
        {/* Tail — a rotated square clipped to two of its borders, pointing
            left at the avatar (mirrors TrainBotBubble's `sm+` tail, applied
            unconditionally here since this bubble never stacks). */}
        <div
          aria-hidden="true"
          className="absolute -left-[7px] top-3 h-3 w-3 rotate-45 border-b-2 border-l-2 bg-background"
          style={{ borderColor: TRAIN_BUBBLE_BORDER }}
        />
        <div
          className={BOT_GAME_BUBBLE_COPY_CLASS}
          aria-live="polite"
          data-testid="bot-game-bubble-copy"
        >
          {copy}
        </div>
        {actions !== undefined && (
          <div className="mt-2 flex flex-wrap justify-end gap-2">{actions}</div>
        )}
      </div>
    </div>
  );
}
