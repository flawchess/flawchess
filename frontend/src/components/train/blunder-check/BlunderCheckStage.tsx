/**
 * BlunderCheckStage: the board layout every blunder-check screen shares (Phase 249 UAT).
 *
 * The personalized-puzzle solve screen's layout (TrainSolveScreen), so both Train drills
 * look the same: the progress row on top of the board, the board with the eval-bar slot
 * beside it, an optional action bar under the board (tablets only; desktop puts it at the
 * foot of the side column), then the bot bubble. In the stacked layout the
 * progress row and board pin to the top while the rest scrolls underneath; in the side
 * layout (1024px and up, or 768px and up in landscape; see lib/trainSideLayout.ts) a
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
import {
  useIsTrainBandBar,
  useIsTrainShortSide,
  useIsTrainSideLayout,
  useTrainBoardGutter,
} from '@/hooks/useIsDesktop';
import { BLUNDER_CHECK_BOARD_MAX_WIDTH_PX } from '@/lib/blunderCheckDrill';
import type { DrillProgress } from '@/lib/blunderCheckDrill';
import {
  SHORT_SIDE_FOOTER_RESET_CLASS,
  SIDE_SCROLL_FRAME_CLASS,
  SHORT_SIDE_STICKY_FOOTER_CLASS,
  SHORT_SIDE_TOP_RESET_CLASS,
  STACKED_BOARD_ROW_CAP_CLASS,
  TRAIN_SIDE_COLUMN_WIDTH_CLASS,
  TRAIN_SIDE_ROW_GAP_CLASS,
} from '@/lib/trainSideLayout';

/** Floor of the short-window board shrink; below it the page scrolls (TrainSolveScreen's value). */
const BOARD_MIN_WIDTH_PX = 240;
/** Space kept free below the board column on a short desktop window. */
const BOARD_BOTTOM_GUTTER_PX = 40;
/** The eval-bar slot (20px `w-5`) plus its 8px `gap-2`, taken out of the board row. */
const EVAL_BAR_CHROME_PX = 28;
const PERCENT = 100;
/** The side layout's game-info slot under the board: one `text-sm` line (20px). */
const GAME_INFO_SLOT_CLASS = 'min-h-5 w-full';
/**
 * The side column's footer (the solution's Next). The column stretches to the board
 * column's full height, which ends with the game-info slot (20px) and its 12px gap, so
 * this bottom margin puts the footer back on the board's bottom edge.
 */
export const BLUNDER_CHECK_SIDE_FOOTER_CLASS = `mt-auto mb-8 ${SHORT_SIDE_FOOTER_RESET_CLASS} ${SHORT_SIDE_STICKY_FOOTER_CLASS}`;
/**
 * The side column, right of the board. `trainside:mt-[34px]` top-aligns its content with
 * the top of the board: the progress row is 22px tall here (the pot badge, 26px less its
 * `-my-0.5`) plus the pinned block's 12px `gap-3`. Bug fix (Phase 249 UAT): it was 46px
 * and sat the bubble about 12px low. TrainReveal's row has no badge, so it uses 32px.
 * `trainside:self-stretch` makes it as tall as the board column, so a footer with
 * BLUNDER_CHECK_SIDE_FOOTER_CLASS (the solution's Next) lands on the board's bottom edge.
 */
export const BLUNDER_CHECK_SIDE_CLASS = `flex w-full flex-col gap-4 trainside:mt-[34px] trainside:self-stretch ${SHORT_SIDE_TOP_RESET_CLASS} trainside:short:flex-1 ${TRAIN_SIDE_COLUMN_WIDTH_CLASS}`;

/** Short side layout: the scroller that stacks the progress row over the side panel, inside a
 * SIDE_SCROLL_FRAME_CLASS frame as tall as the board column. `overflow-x-hidden`: bug fix
 * (816x528): the settings button (32px, centred in its 20px slot) stuck out 6px past the right
 * edge and gave the scroller a horizontal scrollbar. Only its transparent tap area is clipped. */
const SHORT_SIDE_STACK_CLASS = 'absolute inset-0 flex flex-col gap-3 overflow-y-auto overflow-x-hidden';

/**
 * The compact progress row: "n of m", the bar, the pot at risk and the banked points
 * (BlunderCheckScore). On phones the mobile
 * header is hidden during the drill, so the settings cog takes the corner above the
 * eval-bar slot. From sm up, the landscape side-layout band included, the desktop nav
 * header's cog is the settings entry, so this one stays hidden.
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
      <div className="flex w-5 shrink-0 justify-center lg:hidden">
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
   * Side layout only: under the board (the solution's game info). Its slot is held on every
   * side-layout screen, so the fitted board width never changes. Not on a short screen nor
   * where the solution uses the bottom bar (`useIsTrainBandBar`): there the caller puts it in
   * the side column and the board gets the slot's height.
   */
  underBoard?: ReactNode;
  /** The bot bubble: under the board when stacked, in the side column in the side layout. */
  children?: ReactNode;
  /**
   * The right column in the side layout, stacked under the board otherwise (the solution panel,
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
  // Bug fix (Galaxy Z Fold8 landscape, 816x616 / 933x704): below 1024px the drill fell into
  // the phone stack under the desktop nav header, the width-bound 600px board overflowed the
  // viewport bottom and the bubble sat below the fold; the side column and the height fit now
  // engage on the trainside gate (1024px and up, or 768px and up in landscape).
  const isSideLayout = useIsTrainSideLayout();
  const isShortSide = useIsTrainShortSide();
  // The landscape band's solutions use the bottom bar; its height is kept free on every screen.
  const isBandBar = useIsTrainBandBar();
  const gutterPx = useTrainBoardGutter(BOARD_BOTTOM_GUTTER_PX);
  const columnMaxWidthPx = useFitBoardToViewport({
    columnRef,
    boardRef: boardRowRef,
    maxPx: BLUNDER_CHECK_BOARD_MAX_WIDTH_PX,
    minPx: BOARD_MIN_WIDTH_PX,
    gutterPx,
    enabled: isSideLayout,
  });

  // Bug fix (Phase 249 UAT): the side column used to exist on the solution screen only, so
  // the board sat centred during the drill and jumped left when the solution opened. On
  // the side layout the column is now always there (the bubble moves into it). Nothing sits
  // under the board on any side-layout screen (the solution's action bar is in the side
  // column), so the fitted board width is the same on every screen.
  const bubbleInSide = isSideLayout && side === undefined;
  const sidePanel = bubbleInSide ? (
    <div className={BLUNDER_CHECK_SIDE_CLASS} data-testid="blunder-check-side-panel">
      {children}
    </div>
  ) : (
    side
  );
  // Short side layout (a phone in landscape): the progress row tops the side column instead of
  // the board column, so the board gets the screen's full height.
  const progressRow = <BlunderCheckProgress progress={progress} />;

  return (
    <div
      // Published as a custom property so the phone stack caps itself with a class that
      // `trainside:max-w-none` can still override (same device as TrainSolveScreen).
      style={{ '--train-col-max': `${columnMaxWidthPx}px` } as CSSProperties}
      className={`mx-auto flex w-full max-w-[var(--train-col-max)] flex-col items-center gap-4 trainside:mx-0 trainside:max-w-none trainside:flex-row trainside:items-start trainside:justify-center ${TRAIN_SIDE_ROW_GAP_CLASS}`}
      data-testid={testId}
    >
      <div
        ref={columnRef}
        // Stacked, the column is `display: contents`, so the pinned block is a direct
        // child of the page-long container and stays pinned while the panel scrolls.
        // `min-w-0`: the board sizes from this column's width, so the column must be able to
        // shrink below the board's current size. Bug fix (near-square foldables, e.g. 820x791): with
        // the default `min-width: auto` the board kept its height-fitted size and the row
        // overflowed by up to 44px next to the side column's floor (then 272px).
        className="contents trainside:flex trainside:w-full trainside:min-w-0 trainside:flex-col trainside:items-center trainside:gap-3"
        style={{ maxWidth: columnMaxWidthPx }}
      >
        <div
          className="sticky top-0 z-10 flex w-full flex-col items-center gap-3 bg-background trainside:static trainside:z-auto trainside:bg-transparent"
          data-testid="blunder-check-pinned-board"
        >
          {!isShortSide && progressRow}
          <div
            ref={boardRowRef}
            className={`flex w-full flex-row items-stretch gap-2 ${STACKED_BOARD_ROW_CAP_CLASS}`}
          >
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
          {isSideLayout && !isShortSide && !isBandBar && (
            <div className={GAME_INFO_SLOT_CLASS} data-testid="blunder-check-game-info-slot">
              {underBoard}
            </div>
          )}
        </div>
        {!bubbleInSide && children}
      </div>
      {isShortSide ? (
        <div className={SIDE_SCROLL_FRAME_CLASS} data-testid="blunder-check-short-side">
          <div className={SHORT_SIDE_STACK_CLASS}>
            {progressRow}
            {sidePanel}
          </div>
        </div>
      ) : (
        sidePanel
      )}
    </div>
  );
}
