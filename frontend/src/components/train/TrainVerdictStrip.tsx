/**
 * TrainVerdictStrip — the phone's one-line verdict after the reveal: bot
 * avatar + total-points pill + one clause ("Right call, best move"). Tapping
 * it expands the full feedback (`TrainVerdictDetails`, passed as children)
 * below the line.
 *
 * Starts collapsed on every reveal: TrainReveal remounts per reveal, so
 * the initial `useState(false)` is the whole contract. The Umami `panel-open`
 * event fires from the click handler on the collapsed -> open transition only,
 * never on mount, restore or collapse (frontend/CLAUDE.md feature events).
 */

import { useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { TrainScoreChip } from '@/components/train/TrainVerdictDetails';
import { trackFeature } from '@/lib/analytics';
import { placeholderAvatarFor, resolveAvatarSrc } from '@/lib/personas/personaAvatars';
import type { Persona } from '@/lib/personas/personaRegistry';
import { TOUR_SPOTLIGHT_CLASS, TRAIN_BUBBLE_BORDER } from '@/lib/theme';
import { cn } from '@/lib/utils';

/** The strip's avatar is smaller than the 40px points-flash face. */
const STRIP_AVATAR_CLASS = 'size-8';

export interface TrainVerdictStripProps {
  persona: Persona;
  /** The total for the puzzle, from `scorePuzzle` (never summed here). */
  points: number;
  /** The one-line clause, from `verdictStripLine`. */
  line: string;
  /** Called once per collapsed -> open transition (the board owner's telemetry). */
  onExpand?: () => void;
  /** The reveal tour spotlights the strip with the shared glow. */
  spotlight?: boolean;
  /** The expansion body (`TrainVerdictDetails`). */
  children: ReactNode;
}

export function TrainVerdictStrip({
  persona,
  points,
  line,
  onExpand,
  spotlight = false,
  children,
}: TrainVerdictStripProps): ReactElement {
  const [expanded, setExpanded] = useState(false);
  const avatar = placeholderAvatarFor(persona);
  const avatarSrc = resolveAvatarSrc(persona);

  function handleToggle(): void {
    if (!expanded) {
      trackFeature('panel-open', { target: 'train-verdict-strip' });
      onExpand?.();
    }
    setExpanded(!expanded);
  }

  return (
    <div
      className={cn('w-full rounded-2xl border-2 bg-background', spotlight && TOUR_SPOTLIGHT_CLASS)}
      style={{ borderColor: TRAIN_BUBBLE_BORDER }}
      data-testid="train-verdict-strip-root"
    >
      <button
        type="button"
        aria-expanded={expanded}
        aria-label={`${persona.name}: ${line}. ${expanded ? 'Hide' : 'Show'} details`}
        onClick={handleToggle}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
        data-testid="train-verdict-strip"
      >
        <span
          aria-hidden="true"
          className={cn(
            'flex shrink-0 items-center justify-center overflow-hidden rounded-full text-lg',
            STRIP_AVATAR_CLASS,
          )}
          style={{ backgroundColor: avatar.tint }}
          data-testid="train-verdict-strip-avatar"
          data-persona-id={persona.id}
          data-persona-name={persona.name}
        >
          {avatarSrc !== undefined ? (
            <img src={avatarSrc} alt="" className="h-full w-full object-cover" />
          ) : (
            avatar.emoji
          )}
        </span>
        <TrainScoreChip points={points} testid="train-verdict-strip-points" />
        <span className="min-w-0 flex-1 truncate text-sm font-medium" data-testid="train-verdict-strip-line">
          {line}
        </span>
        <ChevronDown
          aria-hidden="true"
          className={cn('size-4 shrink-0 text-muted-foreground transition-transform', expanded && 'rotate-180')}
        />
      </button>
      {expanded && (
        <div className="px-3 pb-3 text-sm" data-testid="train-verdict-strip-details">
          {children}
        </div>
      )}
    </div>
  );
}

/**
 * Desktop's avatar size inside the verdict card, about three text-sm lines
 * (3 x 20px), so the verdict paragraph wraps beside it.
 */
const CARD_AVATAR_CLASS = 'size-15 text-3xl';

export interface TrainVerdictCardProps {
  persona: Persona;
  /** The reveal tour spotlights the card with the shared glow. */
  spotlight?: boolean;
  /** Renders the verdict body with the floated avatar as its `leading` slot. */
  renderDetails: (avatar: ReactNode) => ReactNode;
}

/**
 * TrainVerdictCard — the desktop verdict surface. The phone strip's card (same
 * border, avatar inside, no name) but always open: the avatar floats left of
 * the verdict paragraph, and the Your-call block below the separator uses the
 * whole width.
 */
export function TrainVerdictCard({ persona, spotlight = false, renderDetails }: TrainVerdictCardProps): ReactElement {
  const avatar = placeholderAvatarFor(persona);
  const avatarSrc = resolveAvatarSrc(persona);
  const avatarNode = (
    <span
      aria-hidden="true"
      className={cn(
        'float-left mr-3 flex items-center justify-center overflow-hidden rounded-full',
        CARD_AVATAR_CLASS,
      )}
      style={{ backgroundColor: avatar.tint }}
      data-testid="train-verdict-card-avatar"
      data-persona-id={persona.id}
      data-persona-name={persona.name}
    >
      {avatarSrc !== undefined ? <img src={avatarSrc} alt="" className="h-full w-full object-cover" /> : avatar.emoji}
    </span>
  );
  return (
    <div
      role="group"
      aria-label={persona.name}
      className={cn('w-full rounded-2xl border-2 bg-background px-4 py-3 text-sm', spotlight && TOUR_SPOTLIGHT_CLASS)}
      style={{ borderColor: TRAIN_BUBBLE_BORDER }}
      data-testid="train-verdict-card"
    >
      {renderDetails(avatarNode)}
    </div>
  );
}
