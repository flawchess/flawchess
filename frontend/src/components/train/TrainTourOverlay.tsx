/**
 * TrainTourOverlay — Phase 237 UAT (G-01): Hilda's first-reveal tour, drawn ON
 * the board instead of in the page flow. On phones the strip and the chips it
 * talks about fit under the board without scrolling; on desktop it keeps Hilda
 * from stacking a second avatar on top of the verdict bubble.
 *
 * The panel is `pointer-events-none`: a touch on it reaches the board, and the
 * board owner hides the panel on that touch (and on every other reveal
 * interaction), so the arrows and moves it covers become readable. While
 * hidden, Hilda's badge in the board corner brings the current step back. The
 * tour itself only advances through the reveal bar's Next.
 */
import { Fragment } from 'react';
import type { ReactElement } from 'react';
import { ChevronLeft, ChevronRight, SkipBack } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { TrainBotAvatar } from '@/components/train/TrainBotBubble';
import type { Persona } from '@/lib/personas/personaRegistry';
import { TOUR_ICON_TOKEN } from '@/lib/trainBotCopy';
import type { TourIcon } from '@/lib/trainBotCopy';
import { TRAIN_BUBBLE_BORDER } from '@/lib/theme';

/** The bar's own icons (BoardControls), so the copy shows exactly what the bar does. */
const TOUR_ICONS: Record<TourIcon, { Icon: LucideIcon; label: string }> = {
  rewind: { Icon: SkipBack, label: 'Rewind' },
  back: { Icon: ChevronLeft, label: 'Back' },
  forward: { Icon: ChevronRight, label: 'Forward' },
};

const TOKEN_TO_ICON = new Map<string, TourIcon>(
  (Object.keys(TOUR_ICON_TOKEN) as TourIcon[]).map((icon) => [TOUR_ICON_TOKEN[icon], icon]),
);

/** Splits on the tokens, keeping them (a capture group keeps the separators). */
const TOKEN_SPLIT = new RegExp(
  `(${[...TOKEN_TO_ICON.keys()].map((token) => token.replace(/[{}]/g, '\\$&')).join('|')})`,
);

/** A tour step's copy with each icon token drawn as the bar's icon. */
function TourCopy({ copy }: { copy: string }): ReactElement {
  return (
    <>
      {copy.split(TOKEN_SPLIT).map((part, index) => {
        const icon = TOKEN_TO_ICON.get(part);
        if (icon === undefined) return <Fragment key={index}>{part}</Fragment>;
        const { Icon, label } = TOUR_ICONS[icon];
        return (
          <Icon
            key={index}
            role="img"
            aria-label={label}
            className="inline size-4 align-text-bottom"
            data-testid={`train-tour-icon-${icon}`}
          />
        );
      })}
    </>
  );
}

/** "2 / 6": where the user is in the tour, since its Next lives in the bar. */
function TourStepCount({ step, stepCount }: { step: number; stepCount: number }): ReactElement {
  return (
    <span className="text-sm text-muted-foreground" data-testid="train-tour-step-count">
      {step + 1} / {stepCount}
    </span>
  );
}

export interface TrainTourOverlayProps {
  persona: Persona;
  copy: string;
  step: number;
  stepCount: number;
  /** After an interaction: only Hilda's badge shows, until Next or a badge tap. */
  hidden: boolean;
  onReopen: () => void;
}

export function TrainTourOverlay({
  persona,
  copy,
  step,
  stepCount,
  hidden,
  onReopen,
}: TrainTourOverlayProps): ReactElement {
  if (hidden) {
    // The avatar's style tint is only 14% opaque, so on its own the board
    // showed through the badge; the solid backing keeps it readable.
    return (
      <button
        type="button"
        className="absolute bottom-2 left-2 z-10 cursor-pointer rounded-full bg-background shadow-lg ring-2 ring-brand-brown"
        aria-label="Show Hilda's tip"
        data-testid="btn-train-tour-reopen"
        onClick={onReopen}
      >
        <TrainBotAvatar persona={persona} className="size-10 text-xl" />
      </button>
    );
  }
  return (
    <div
      className="pointer-events-none absolute inset-x-2 bottom-2 z-10 flex items-start gap-3 rounded-xl border-2 bg-background/85 px-3 py-2 backdrop-blur-sm"
      style={{ borderColor: TRAIN_BUBBLE_BORDER }}
      data-testid="train-tour-overlay"
    >
      <div className="flex shrink-0 flex-col items-center gap-1">
        <TrainBotAvatar persona={persona} className="size-10 text-xl" />
        <TourStepCount step={step} stepCount={stepCount} />
      </div>
      <p className="min-w-0 flex-1 text-sm" data-testid="train-bot-walkthrough">
        <TourCopy copy={copy} />
      </p>
    </div>
  );
}
