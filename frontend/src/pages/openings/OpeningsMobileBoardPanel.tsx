import { useRef, type ReactNode } from 'react';
import { SlidersHorizontal, Bookmark, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { RouteDot } from '@/components/feature-route/RouteDot';
import { InfoPopover } from '@/components/ui/info-popover';
import { ChessBoard, type BoardArrow } from '@/components/board/ChessBoard';
import { MoveList } from '@/components/board/MoveList';
import { BoardControls } from '@/components/board/BoardControls';
import { ChessboardInfoCopy } from './ChessboardInfoCopy';
import { useFitBoardToViewport } from '@/hooks/useFitBoardToViewport';
import { useIsTrainSideBand } from '@/hooks/useIsDesktop';
import {
  OPENINGS_BOARD_ROW_CHROME_PX,
  OPENINGS_MOBILE_BOARD_COLUMN_CLASS,
  OPENINGS_SIDE_BOARD_GUTTER_PX,
  OPENINGS_SIDE_BOARD_MAX_PX,
  OPENINGS_SIDE_BOARD_MIN_PX,
  OPENINGS_STACKED_BOARD_MAX_PX,
} from '@/lib/openingsBoardLayout';
import type { Opening } from '@/lib/openings';
import type { Color } from '@/types/api';
import type { OpeningsTab } from '@/types/openingsTab';

export type OpeningsMobileBoardPanelProps = {
  /** Board block is only rendered on the Moves + Games subtabs. */
  activeTab: OpeningsTab;

  // Board
  mobileBoardRef: (el: HTMLDivElement | null) => void;
  position: string;
  onPieceDrop: (sourceSquare: string, targetSquare: string) => boolean;
  flipped: boolean;
  lastMove: { from: string; to: string } | null;
  arrows: BoardArrow[];
  onBack: () => void;
  onForward: () => void;
  onReset: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;

  // Settings column
  onOpenFilterDrawer: () => void;
  filtersNotificationDot: ReactNode;
  filterColor: Color;
  onTogglePlayedAs: () => void;
  showPlayedAsDot: boolean;
  onOpenBookmarkDrawer: () => void;
  showAnalyzeButton: boolean;
  onAnalyzePosition: () => void;
};

export type OpeningsMobileOpeningLineProps = {
  /** Rendered only on the Moves + Games subtabs, like the board. */
  activeTab: OpeningsTab;
  opening: Opening | null;
  moveHistory: string[];
  currentPly: number;
  onMoveClick: (ply: number) => void;
};

function isBoardTab(activeTab: OpeningsTab): boolean {
  return activeTab === 'explorer' || activeTab === 'games';
}

/**
 * Mobile board column (chessboard, settings column, controls) — visible only
 * on the Moves/Games subtabs. The opening name and move list live in
 * OpeningsMobileOpeningLine below, so the landscape side layout can put them
 * in the content column (see lib/openingsBoardLayout.ts). Extracted as the
 * plan's fallback "desktop and mobile layout" seam once useOpeningsChartData
 * left OpeningsPage's own complexity still above the (relaxed) target; this
 * is the single largest remaining JSX-return cluster (~40+ LOC of logic:
 * four button conditionals, an opening-name ternary, and the mobile-only
 * settings column). `filtersNotificationDot` stays a prop rather than an
 * internally-owned branch because the SAME ternary is also used by the
 * sticky Filters button on Stats, which this component doesn't own.
 */
export function OpeningsMobileBoardPanel({
  activeTab,
  mobileBoardRef,
  position,
  onPieceDrop,
  flipped,
  lastMove,
  arrows,
  onBack,
  onForward,
  onReset,
  onFlip,
  canGoBack,
  canGoForward,
  onOpenFilterDrawer,
  filtersNotificationDot,
  filterColor,
  onTogglePlayedAs,
  showPlayedAsDot,
  onOpenBookmarkDrawer,
  showAnalyzeButton,
  onAnalyzePosition,
}: OpeningsMobileBoardPanelProps) {
  const columnRef = useRef<HTMLDivElement>(null);
  const boardRef = useRef<HTMLDivElement>(null);
  const isSideBand = useIsTrainSideBand();
  const showBoard = isBoardTab(activeTab);
  // Landscape side layout: the board is height-fitted so it and the board controls under it
  // end above the bottom tab bar. The "column" is the board row: the board's non-board height
  // is the controls plus their gap. (The settings column beside the board only outgrows that
  // for a board under 190px, below OPENINGS_SIDE_BOARD_MIN_PX, so it never feeds back into
  // the fit.) Portrait keeps the 400px cap (the fit is off there and returns maxPx).
  const boardMaxPx = useFitBoardToViewport({
    columnRef,
    boardRef,
    maxPx: isSideBand ? OPENINGS_SIDE_BOARD_MAX_PX : OPENINGS_STACKED_BOARD_MAX_PX,
    minPx: OPENINGS_SIDE_BOARD_MIN_PX,
    gutterPx: OPENINGS_SIDE_BOARD_GUTTER_PX,
    enabled: isSideBand && showBoard,
  });

  if (!showBoard) return null;

  return (
    <div
      ref={columnRef}
      className={OPENINGS_MOBILE_BOARD_COLUMN_CLASS}
      // The board measures its container for its width, so as a flex-row item the column needs
      // an explicit width (it would otherwise size to the not-yet-measured board). `min-w-0` in
      // the class lets it shrink below this when the content column needs its floor.
      style={isSideBand ? { width: boardMaxPx + OPENINGS_BOARD_ROW_CHROME_PX } : undefined}
      data-testid="openings-mobile-board-column"
    >
      {/* Cap the board column at the board's max render width (400px in portrait,
          the ChessBoard default maxWidth — same value the desktop container uses; the
          fitted width in landscape). Without this, `flex-1` stretched the column past
          the (capped) board on tablet/narrow-desktop widths below `lg`, so BoardControls
          rendered wider than the board and the settings column was pushed far to the
          right. */}
      <div className="flex-1 min-w-0 flex flex-col gap-1" style={{ maxWidth: boardMaxPx }}>
        {/* Same board-only wheel scoping as the desktop layout above. Both
            layouts stay mounted (one is CSS-hidden), hence a ref each. The outer
            wrapper is the height fit's measured board (a callback ref cannot be). */}
        <div ref={boardRef}>
          <div ref={mobileBoardRef}>
            <ChessBoard
              position={position}
              onPieceDrop={onPieceDrop}
              flipped={flipped}
              lastMove={lastMove}
              arrows={arrows}
              maxWidth={boardMaxPx}
            />
          </div>
        </div>
        {/* Board controls aligned to chessboard width (excludes settings column) */}
        <BoardControls
          onBack={onBack}
          onForward={onForward}
          onReset={onReset}
          onFlip={onFlip}
          canGoBack={canGoBack}
          canGoForward={canGoForward}
          size="wide"
        />
      </div>
      {/* Settings column: stacked 44px buttons — filters, played-as, bookmarks,
          analyze (Moves + Games subtabs), info */}
      <div className="flex flex-col gap-1 w-11" data-testid="openings-mobile-settings-column">
        <Tooltip content="Open filters" side="left">
          <Button
            variant="ghost"
            size="icon"
            className="h-11 w-11 shrink-0 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80 relative"
            onClick={onOpenFilterDrawer}
            data-testid="subnav-filter-button"
            aria-label="Open filters"
          >
            <SlidersHorizontal className="h-4 w-4" />
            {filtersNotificationDot}
          </Button>
        </Tooltip>
        <Tooltip content={`Playing as ${filterColor}`} side="left">
          <Button
            variant="ghost"
            size="icon"
            className="relative h-11 w-11 shrink-0 !bg-toggle-active text-toggle-active-foreground hover:!bg-toggle-active"
            onClick={onTogglePlayedAs}
            data-testid="btn-toggle-played-as"
            aria-label={`Playing as ${filterColor}, tap to switch`}
          >
            <span className={`inline-block h-4 w-4 rounded-xs border border-muted-foreground ${filterColor === 'white' ? 'bg-white' : 'bg-zinc-900'}`} />
            {showPlayedAsDot && <RouteDot testid="played-as-notification-dot-mobile" variant="corner" />}
          </Button>
        </Tooltip>
        <Tooltip content="Open bookmarks" side="left">
          <Button
            variant="ghost"
            size="icon"
            className="h-11 w-11 shrink-0 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80 relative"
            onClick={onOpenBookmarkDrawer}
            data-testid="btn-open-bookmark-sidebar"
            aria-label="Open bookmarks"
          >
            <Bookmark className="h-4 w-4" />
          </Button>
        </Tooltip>
        {showAnalyzeButton && (
          <Tooltip content="Analyze position" side="left">
            <Button
              variant="ghost"
              size="icon"
              className="h-11 w-11 shrink-0 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80"
              onClick={onAnalyzePosition}
              data-testid="btn-analyze-position-mobile"
              aria-label="Analyze position"
            >
              <Search className="h-4 w-4" />
            </Button>
          </Tooltip>
        )}
        <div className="flex h-11 w-11 items-center justify-center">
          <InfoPopover ariaLabel="Chessboard info" testId="chessboard-info-mobile" side="left">
            <ChessboardInfoCopy />
          </InfoPopover>
        </div>
      </div>
    </div>
  );
}

/** Opening name line and move list under the board (portrait) or at the top of the content
 * column (landscape side layout). */
export function OpeningsMobileOpeningLine({
  activeTab,
  opening,
  moveHistory,
  currentPly,
  onMoveClick,
}: OpeningsMobileOpeningLineProps) {
  if (!isBoardTab(activeTab)) return null;

  return (
    <>
      {/* Opening name line (always visible on Moves/Games subtabs) */}
      <div className="flex items-center gap-2 px-1 text-sm min-h-[1.25rem]">
        {opening ? (
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-xs text-muted-foreground">{opening.eco}</span>
            <span className="text-foreground">{opening.name}</span>
          </div>
        ) : (
          <span className="text-muted-foreground italic">Play some moves</span>
        )}
      </div>
      <MoveList
        moveHistory={moveHistory}
        currentPly={currentPly}
        onMoveClick={onMoveClick}
      />
    </>
  );
}
