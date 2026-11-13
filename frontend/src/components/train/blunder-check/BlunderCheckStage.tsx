/**
 * BlunderCheckStage: the board layout every blunder-check screen shares (Phase 249 UAT).
 *
 * The personalized-puzzle solve screen's layout (TrainSolveScreen), so both Train drills
 * look the same: the progress row on top of the board, the board with the eval-bar slot
 * beside it, an optional action bar under the board (tablets only; desktop puts it at the
 * foot of the side column), then the bot bubble. On phones the
 * progress row and board pin to the top while the rest scrolls underneath; from `lg` up a
 * side column right of the board is ALWAYS there: it holds the bot bubble during the drill
 * and the solution panel after it, so the board sits in the same place on every screen.
 *
 * No Umami event is added for blunder check (D-19); the settings cog tracks its own open.
 */

import { useRef } from 'react';
import type { CSSProperties, ReactElement, ReactNode, RefObject } from 'react';
import { SettingsSheetButton } from '@/components/settings/SettingsSheetButton';
import { BlunderCheckScore } from '@/components/train/blunder-check/BlunderCheckScore';
import { useFitBoardToViewport } from '@/hooks/useFitBoardToViewport';
import { useIsDesktop } from '@/hooks/useIsDesktop';
import { BLUNDER_CHECK_BOARD_MAX_WIDTH_PX } from '@/lib/blunderCheckDrill';
import type { DrillProgress } from '@/lib/blunderCheckDrill';

/** Floor of the short-window board shrink; below it the page scrolls (TrainSolveScreen's value). */
const BOARD_MIN_WIDTH_PX = 240;
/** Space kept free below the board column on a short desktop window. */
const BOARD_BOTTOM_GUTTER_PX = 40;
/** The eval-bar slot (20px `w-5`) plus its 8px `gap-2`, taken out of the board row. */
const EVAL_BAR_CHROME_PX = 28;
const PERCENT = 100;
/** The desktop game-info slot under the board: one `text-sm` line (20px). */
const GAME_INFO_SLOT_CLASS = 'min-h-5 w-full';
/**
 * The side column's footer (the solution's Next). The column stretches to the board
 * column's full height, which ends with the game-info slot (20px) and its 12px gap, so
 * this bottom margin puts the footer back on the board's bottom edge.
 */
export const BLUNDER_CHECK_SIDE_FOOTER_CLASS = 'mt-auto mb-8';
/**
 * The desktop side column, right of the board. `lg:mt-[34px]` top-aligns its content with
 * the top of the board: the progress row is 22px tall here (the pot badge, 26px less its
 * `-my-0.5`) plus the pinned block's 12px `gap-3`. Bug fix (Phase 249 UAT): it was 46px
 * and sat the bubble about 12px low. TrainReveal's row has no badge, so it uses 32px.
 * `lg:self-stretch` makes it as tall as the board column, so a footer with
 * BLUNDER_CHECK_SIDE_FOOTER_CLASS (the solution's Next) lands on the board's bottom edge.
 */
export const BLUNDER_CHECK_SIDE_CLASS =
  'flex w-full flex-col gap-4 lg:mt-[34px] lg:max-w-sm lg:self-stretch';

/**
 * The compact progress row: "n of m", the bar, the pot at risk and the banked points
 * (BlunderCheckScore). On phones the mobile
 * header is hidden during the drill, so the settings cog takes the corner above the
 * eval-bar slot.
 */
function BlunderCheckProgress({ progress }: { progress: DrillProgress }): ReactElement {
  const { position, windowCount } = progress;
  const fraction = windowCount > 0 ? Math.min(1, Math.max(0, position / windowCount)) : 0;
  return (
    <div className="flex w-full items-center gap-2" data-testid="blunder-check-header">
      <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
        <p className="shrink-0 text-sm font-semibold" data-testid="blunder-check-window-counter">
          {position + 1} of {windowCount}
        </p>
        <div
          className="h-1.5 min-w-0 flex-1 rounded-full bg-muted"
          data-testid="blunder-check-progress-bar"
        >
          <div
            className="h-1.5 rounded-full bg-brand-brown"
            style={{ width: `${fraction * PERCENT}%` }}
          />
        </div>
        {/* Re-keyed as Next starts banking the pot: the total's count-up belongs to a mount. */}
        <BlunderCheckScore
          key={progress.potEvent?.kind === 'bank' ? 'banking' : 'open'}
          progress={progress}
        />
      </div>
      <div className="flex w-5 shrink-0 justify-center sm:hidden">
        <SettingsSheetButton
          testId="btn-blunder-check-settings"
          className="-my-1.5 h-8 w-8 shrink-0 text-muted-foreground"
        />
      </div>
    </div>
  );
}

/** A boardless screen of a running session (loading a window, finishing the session): progress plus a message. */
export function BlunderCheckStageMessage({
  progress,
  children,
}: {
  progress: DrillProgress;
  children: ReactNode;
}): ReactElement {
  return (
    <div
      className="mx-auto flex w-full flex-col items-center gap-4"
      style={{ maxWidth: BLUNDER_CHECK_BOARD_MAX_WIDTH_PX }}
    >
      <BlunderCheckProgress progress={progress} />
      {children}
    </div>
  );
}

interface BlunderCheckStageProps {
  progress: DrillProgress;
  /** The board and its overlays, given the width the board may take. */
  renderBoard: (boardMaxWidthPx: number) => ReactNode;
  /** The eval bar; an empty frame fills the slot when absent, so the board never resizes. */
  evalBar?: ReactNode;
  /** Under the board, inside the pinned block (the solution's action bar on tablets). */
  actionBar?: ReactNode;
  /**
   * Desktop only: under the board (the solution's game info). Its slot is held on every
   * desktop screen, so the fitted board width never changes.
   */
  underBoard?: ReactNode;
  /** The bot bubble: under the board below `lg`, in the side column from `lg` up. */
  children?: ReactNode;
  /**
   * The right column from `lg` up, stacked under the board below it (the solution panel,
   * wrapped in BLUNDER_CHECK_SIDE_CLASS by the caller). Takes the column instead of `children`.
   */
  side?: ReactNode;
  /** The board row, for a caller that binds keyboard navigation to it. */
  boardRef?: RefObject<HTMLDivElement | null>;
  testId: string;
}

export function BlunderCheckStage({
  progress,
  renderBoard,
  evalBar,
  actionBar,
  underBoard,
  children,
  side,
  boardRef,
  testId,
}: BlunderCheckStageProps): ReactElement {
  const columnRef = useRef<HTMLDivElement>(null);
  const ownBoardRef = useRef<HTMLDivElement>(null);
  const boardRowRef = boardRef ?? ownBoardRef;
  const isDesktop = useIsDesktop();
  const columnMaxWidthPx = useFitBoardToViewport({
    columnRef,
    boardRef: boardRowRef,
    maxPx: BLUNDER_CHECK_BOARD_MAX_WIDTH_PX,
    minPx: BOARD_MIN_WIDTH_PX,
    gutterPx: BOARD_BOTTOM_GUTTER_PX,
    enabled: isDesktop,
  });

  // Bug fix (Phase 249 UAT): the side column used to exist on the solution screen only, so
  // the board sat centred during the drill and jumped left when the solution opened. On
  // desktop the column is now always there (the bubble moves into it). Nothing sits under
  // the desktop board on any screen (the solution's action bar is in the side column), so
  // the fitted board width is the same on every screen.
  const bubbleInSide = isDesktop && side === undefined;

  return (
    <div
      // Published as a custom property so the phone stack caps itself with a class that
      // `lg:max-w-none` can still override (same device as TrainSolveScreen).
      style={{ '--train-col-max': `${columnMaxWidthPx}px` } as CSSProperties}
      className="mx-auto flex w-full max-w-[var(--train-col-max)] flex-col items-center gap-4 lg:mx-0 lg:max-w-none lg:flex-row lg:items-start lg:justify-center lg:gap-8"
      data-testid={testId}
    >
      <div
        ref={columnRef}
        // Below `lg` the column is `display: contents`, so the pinned block is a direct
        // child of the page-long container and stays pinned while the panel scrolls.
        className="max-lg:contents lg:flex lg:w-full lg:flex-col lg:items-center lg:gap-3"
        style={{ maxWidth: columnMaxWidthPx }}
      >
        <div
          className="flex w-full flex-col items-center gap-3 max-lg:sticky max-lg:top-0 max-lg:z-10 max-lg:bg-background"
          data-testid="blunder-check-pinned-board"
        >
          <BlunderCheckProgress progress={progress} />
          <div ref={boardRowRef} className="flex w-full flex-row items-stretch gap-2">
            <div className="relative min-w-0 flex-1">
              {renderBoard(columnMaxWidthPx - EVAL_BAR_CHROME_PX)}
            </div>
            <div className="w-5 shrink-0">
              {evalBar ?? (
                <div
                  aria-hidden="true"
                  className="h-full w-full rounded border border-border bg-muted"
                  data-testid="blunder-check-eval-bar-placeholder"
                />
              )}
            </div>
          </div>
          {actionBar}
          {isDesktop && (
            <div className={GAME_INFO_SLOT_CLASS} data-testid="blunder-check-game-info-slot">
              {underBoard}
            </div>
          )}
        </div>
        {!bubbleInSide && children}
      </div>
      {bubbleInSide ? (
        <div className={BLUNDER_CHECK_SIDE_CLASS} data-testid="blunder-check-side-panel">
          {children}
        </div>
      ) : (
        side
      )}
    </div>
  );
}
