/**
 * TrainRevealActionBar — Phase 237 plan 07 (ROADMAP items 5 and 6): the one
 * action bar of the Train reveal. Rewind (the old Solution, keeps sidelines),
 * back, forward and flip, then Analyze and Next.
 *
 * One component, three hosts (RESEARCH Pattern 7): the fixed phone bottom bar
 * (`MobileBottomBar` renders it from the published `mobileBoardControls`
 * payload), and an in-flow instance under the board from `sm` up (tablet and
 * desktop).
 *
 * Analyze is an internal router Link: its analytics event fires from the
 * click handler (`onAnalyzeClick`), never through `data-umami-event`, which
 * would downgrade the client-side navigation to a full page reload
 * (frontend/CLAUDE.md).
 */
import type { ReactElement } from 'react';
import { Link } from 'react-router';
import { Search } from 'lucide-react';
import { BoardControls, LABELLED_BUTTON_CLASS } from '@/components/board/BoardControls';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export interface TrainRevealActionBarProps {
  onRewind: () => void;
  onBack: () => void;
  onForward: () => void;
  onFlip: () => void;
  canRewind: boolean;
  canGoBack: boolean;
  canGoForward: boolean;
  /** The Analyze target (own source game or the puzzle position); null renders no Analyze. */
  analyzeTo: string | null;
  onAnalyzeClick: () => void;
  onNext: () => void;
  /**
   * Phase 237 UAT: wrap the board controls in the analysis board's charcoal
   * container, as tall as Analyze and Next beside it. The in-flow `sm`-up host
   * sets it; the phone bottom bar instead renders the /analysis mobile footer's
   * icon-over-label columns, with Analyze as one more column.
   */
  framed?: boolean;
  className?: string;
}

/** Tap target for the two labelled buttons: 48px on phones, compact from `sm`. */
const ACTION_BUTTON_CLASS = 'h-12 shrink-0 px-3 sm:h-8';

/** The framed container matches the `sm:h-8` action buttons; the controls fill its inner height. */
const FRAMED_CONTAINER_CLASS = 'h-8 min-w-0 flex-1 px-1';
const FRAMED_CONTROL_BUTTON_CLASS = 'h-full w-8';

export function TrainRevealActionBar({
  onRewind,
  onBack,
  onForward,
  onFlip,
  canRewind,
  canGoBack,
  canGoForward,
  analyzeTo,
  onAnalyzeClick,
  onNext,
  framed = false,
  className,
}: TrainRevealActionBarProps): ReactElement {
  // Phone bottom bar: Analyze reads as one more board-control column, the same
  // ghost icon-over-label shape as Start/Back/Next/Flip. It rides in the
  // controls' own row (infoSlot) so all five columns share the width equally.
  const labelledAnalyze = !framed && analyzeTo !== null && (
    <Button asChild variant="ghost" className={cn(LABELLED_BUTTON_CLASS, 'hover:bg-accent')}>
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
  const controls = (
    <BoardControls
      flat
      labels={!framed}
      forwardLabel="Fwd"
      onReset={onRewind}
      onBack={onBack}
      onForward={onForward}
      onFlip={onFlip}
      canReset={canRewind}
      canGoBack={canGoBack}
      canGoForward={canGoForward}
      infoSlot={labelledAnalyze}
      buttonClassName={framed ? FRAMED_CONTROL_BUTTON_CLASS : undefined}
      className={framed ? 'h-full w-full' : 'min-w-0 flex-1'}
    />
  );
  return (
    <div
      data-testid="train-reveal-action-bar"
      // Phase 237 UAT: the walkthrough's last step used to ring this bar; the
      // ring was clipped by the fixed mobile bottom bar and added little, so
      // the tour bubble alone points at it now.
      className={cn('flex items-center gap-2', className)}
    >
      {framed ? (
        <Card data-testid="train-reveal-controls-frame" className={FRAMED_CONTAINER_CLASS}>
          {controls}
        </Card>
      ) : (
        controls
      )}
      {framed && analyzeTo !== null && (
        <Button asChild variant="brand-outline" className={ACTION_BUTTON_CLASS}>
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
      )}
      <Button
        variant="default"
        className={ACTION_BUTTON_CLASS}
        data-testid="btn-train-next"
        onClick={onNext}
      >
        Next
      </Button>
    </div>
  );
}
