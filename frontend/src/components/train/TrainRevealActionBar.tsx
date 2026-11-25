/**
 * TrainRevealActionBar — the action controls of the Train reveal. Rewind
 * (keeps sidelines), back and forward, then Analyze and Next. Flip is in the
 * desktop controls row only: on phones and tablets the board always faces the
 * user's side on a solution screen (Phase 249 UAT).
 *
 * Phones, foldables and tablets get one bar (`TrainRevealActionBar`) in the fixed
 * bottom bar (`MobileBottomBar` renders it from the published
 * `mobileBoardControls` payload). Desktop splits it across the sidebar:
 * `TrainRevealControlsRow` (the board controls with flip) between the line chips and the
 * move list, and `TrainRevealFooter` (Analyze left of Next, half the column
 * each) at the foot of the column.
 *
 * Analyze is an internal router Link: its analytics event fires from the
 * click handler (`onAnalyzeClick`), never through `data-umami-event`, which
 * would downgrade the client-side navigation to a full page reload
 * (frontend/CLAUDE.md).
 */
import type { ReactElement } from 'react';
import { Link } from 'react-router';
import { ArrowRight, Search } from 'lucide-react';
import { BoardControls, LABELLED_BUTTON_CLASS } from '@/components/board/BoardControls';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { TOUR_SPOTLIGHT_CLASS } from '@/lib/theme';
import { cn } from '@/lib/utils';

interface RevealControlsProps {
  onRewind: () => void;
  onBack: () => void;
  onForward: () => void;
  canRewind: boolean;
  canGoBack: boolean;
  canGoForward: boolean;
  /** Flips the board. Desktop controls row only: the button renders when this is supplied. */
  onFlip?: () => void;
  className?: string;
}

interface RevealNavProps extends RevealControlsProps {
  /** The Analyze target (own source game or the puzzle position); null renders no Analyze. */
  analyzeTo: string | null;
  onAnalyzeClick: () => void;
  /** The reveal tour's Analyze step spotlights the Analyze
   * button alone, not the whole bar, in the page flow and the fixed phone bar. */
  spotlightAnalyze?: boolean;
}

export interface TrainRevealActionBarProps extends Omit<RevealNavProps, 'onFlip'> {
  onNext: () => void;
}

/** The framed container matches the `h-8` footer buttons; the controls fill its inner height. */
const FRAMED_CONTAINER_CLASS = 'h-8 min-w-0 flex-1 px-1';
/** Framed controls share the container's width, for a wide hit area. */
const FRAMED_CONTROL_BUTTON_CLASS = 'h-full flex-1';

type AnalyzeLinkProps = Pick<RevealNavProps, 'analyzeTo' | 'onAnalyzeClick' | 'spotlightAnalyze'> & {
  className?: string;
};

/** The outline Analyze button (desktop footer). */
function FramedAnalyze({
  analyzeTo,
  onAnalyzeClick,
  spotlightAnalyze = false,
  className,
}: AnalyzeLinkProps): ReactElement | null {
  if (analyzeTo === null) return null;
  return (
    <Button
      asChild
      variant="brand-outline"
      className={cn(className, spotlightAnalyze && TOUR_SPOTLIGHT_CLASS)}
    >
      <Link
        to={analyzeTo}
        data-testid="btn-train-analyze"
        aria-label="Analyze this position"
        onClick={onAnalyzeClick}
      >
        <Search className="mr-1 h-4 w-4" />
        Analyze
      </Link>
    </Button>
  );
}

/** The three board controls in the charcoal frame. */
function FramedControls({
  onRewind,
  onBack,
  onForward,
  canRewind,
  canGoBack,
  canGoForward,
  onFlip,
}: RevealControlsProps): ReactElement {
  return (
    <Card data-testid="train-reveal-controls-frame" className={FRAMED_CONTAINER_CLASS}>
      <BoardControls
        flat
        onReset={onRewind}
        onBack={onBack}
        onForward={onForward}
        canReset={canRewind}
        canGoBack={canGoBack}
        canGoForward={canGoForward}
        onFlip={onFlip}
        buttonClassName={FRAMED_CONTROL_BUTTON_CLASS}
        className="h-full w-full"
      />
    </Card>
  );
}

/** Desktop sidebar: the board controls with flip, between the line chips and the move list they step. */
export function TrainRevealControlsRow(props: RevealControlsProps): ReactElement {
  return (
    <div
      data-testid="train-reveal-controls-row"
      className={cn('flex items-center gap-2', props.className)}
    >
      <FramedControls {...props} />
    </div>
  );
}

/** One half of the desktop footer: `basis-0` keeps the two buttons equally wide. */
const FOOTER_BUTTON_CLASS = 'h-8 min-w-0 flex-1 basis-0';

/**
 * Desktop sidebar: Analyze left of Next at the foot of the column, half its
 * width each. Without an Analyze target Next takes the whole row.
 */
export function TrainRevealFooter({
  onNext,
  className,
  ...analyze
}: AnalyzeLinkProps & { onNext: () => void }): ReactElement {
  return (
    <div
      data-testid="train-reveal-actions-footer"
      className={cn('flex w-full items-center gap-2', className)}
    >
      <FramedAnalyze {...analyze} className={FOOTER_BUTTON_CLASS} />
      <Button
        variant="default"
        className={FOOTER_BUTTON_CLASS}
        data-testid="btn-train-next"
        onClick={onNext}
      >
        Next
      </Button>
    </div>
  );
}

export function TrainRevealActionBar(props: TrainRevealActionBarProps): ReactElement {
  const {
    onRewind,
    onBack,
    onForward,
    canRewind,
    canGoBack,
    canGoForward,
    analyzeTo,
    onAnalyzeClick,
    onNext,
    spotlightAnalyze = false,
    className,
  } = props;
  // Phone bottom bar: Analyze reads as one more board-control column, the same
  // ghost icon-over-label shape as Start/Back/Fwd. It rides in the controls'
  // own row (infoSlot) so all columns share the width equally.
  const labelledAnalyze = analyzeTo !== null && (
    <Button
      asChild
      variant="ghost"
      className={cn(LABELLED_BUTTON_CLASS, 'hover:bg-accent', spotlightAnalyze && TOUR_SPOTLIGHT_CLASS)}
    >
      <Link
        to={analyzeTo}
        data-testid="btn-train-analyze"
        aria-label="Analyze this position"
        onClick={onAnalyzeClick}
      >
        <Search className="h-5 w-5" />
        <span className="text-sm">Analyze</span>
      </Link>
    </Button>
  );
  // Next is the last column in the same shape, filled as the bar's one primary action.
  const labelledNext = (
    <Button
      variant="default"
      className={LABELLED_BUTTON_CLASS}
      data-testid="btn-train-next"
      onClick={onNext}
    >
      <ArrowRight className="h-5 w-5" aria-hidden="true" />
      <span className="text-sm">Next</span>
    </Button>
  );
  return (
    <div
      data-testid="train-reveal-action-bar"
      className={cn('flex items-center', className)}
    >
      <BoardControls
        flat
        labels
        forwardLabel="Fwd"
        onReset={onRewind}
        onBack={onBack}
        onForward={onForward}
        canReset={canRewind}
        canGoBack={canGoBack}
        canGoForward={canGoForward}
        infoSlot={
          <>
            {labelledAnalyze}
            {labelledNext}
          </>
        }
        className="min-w-0 flex-1"
      />
    </div>
  );
}
