import type { ReactElement } from 'react';
import { PlayerBar } from '@/components/board/PlayerBar';
import { BotGameBubble } from '@/components/bots/BotGameBubble';
import { BotDrawOfferActions } from '@/components/bots/BotDrawOfferActions';
import { resolvePlayerRow, type BotPlayerRowInputs } from '@/components/bots/botPlayerRow';
import type { BotLineKey } from '@/lib/botGameCopy';

/** Fixed width of the desktop right column (clocks + move list + controls) —
 * moved here from Bots.tsx (Phase 223, BOTVOICE-05) now that this component
 * owns the whole desktop layout; the page keeps none of this layout math. */
const DESKTOP_SIDE_COLUMN_PX = 320;

export interface BotGameDesktopLayoutProps extends BotPlayerRowInputs {
  /** Current board-orientation toggle (mirrors `ChessBoard`'s own `flipped`
   * prop: `false` = white at the bottom, `true` = black at the bottom).
   * Drives which player row renders above vs. below the board — the row for
   * the side facing away from the user (the top of the board) is always the
   * TOP row, regardless of who that side belongs to. */
  flipped: boolean;
  /** The viewed-ply FEN (not necessarily the live position) — both rows'
   * material tracks the board during scroll-back. */
  fen: string;
  botLine: BotLineKey | null;
  /** True while the bot has a live outgoing draw offer (Phase 183, D-07). */
  drawOfferLive: boolean;
  onAcceptDraw: () => void;
  onDeclineDraw: () => void;
  board: ReactElement;
  boardControls: ReactElement;
  moveList: ReactElement;
  controls: ReactElement;
  boardPx: number;
}

/**
 * BotGameDesktopLayout — Phase 223 (BOTVOICE-05, D-11/D-12): replaces the
 * page's old `renderDesktopLayout` helper. Two stacked rows sharing the same
 * board-column + side-column widths. The top row is the board (flanked
 * above and below by a `PlayerBar`, ordered by board orientation so the side
 * facing away from the user is on top) beside the avatar-and-bubble row over
 * a move list that flex-fills the remaining height — `items-stretch` makes
 * the side column exactly the board's height, so the move-list box bottom
 * lines up with the board's bottom. The bottom row puts the shared board
 * controls under the board and the resign-only control row under the side
 * column.
 *
 * This component owns every branch the layout needs (orientation ordering,
 * the bubble/draw-offer construction; the guest gate on the user's rating
 * label lives in `resolvePlayerRow`) so `BotsGame` — pinned at its own
 * eslint complexity ceiling — gains none of them.
 */
export function BotGameDesktopLayout({
  persona,
  playerName,
  currentStrength,
  userColor,
  activeColor,
  flipped,
  whiteClockMs,
  blackClockMs,
  fen,
  botLine,
  drawOfferLive,
  onAcceptDraw,
  onDeclineDraw,
  board,
  boardControls,
  moveList,
  controls,
  boardPx,
}: BotGameDesktopLayoutProps): ReactElement {
  const rowInputs: BotPlayerRowInputs = {
    persona,
    playerName,
    currentStrength,
    userColor,
    activeColor,
    whiteClockMs,
    blackClockMs,
  };
  // ChessBoard's own `flipped` semantics: false = white at the bottom, true
  // = black at the bottom. The TOP row is always the side NOT at the bottom.
  const topRow = resolvePlayerRow(flipped ? 'white' : 'black', rowInputs);
  const bottomRow = resolvePlayerRow(flipped ? 'black' : 'white', rowInputs);

  const drawOfferActions = drawOfferLive ? (
    <BotDrawOfferActions offerLive onAccept={onAcceptDraw} onDecline={onDeclineDraw} />
  ) : undefined;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-row items-stretch justify-center gap-2">
        <div className="flex min-w-0 flex-1 flex-col gap-1" style={{ maxWidth: boardPx }}>
          <PlayerBar {...topRow} rating={null} fen={fen} />
          {board}
          <PlayerBar {...bottomRow} rating={null} fen={fen} />
        </div>
        <div className="flex shrink-0 flex-col gap-3" style={{ width: DESKTOP_SIDE_COLUMN_PX }}>
          <BotGameBubble persona={persona} line={botLine} actions={drawOfferActions} />
          {moveList}
        </div>
      </div>
      <div className="flex flex-row justify-center gap-2">
        <div className="min-w-0 flex-1" style={{ maxWidth: boardPx }}>
          {boardControls}
        </div>
        <div className="shrink-0" style={{ width: DESKTOP_SIDE_COLUMN_PX }}>
          {controls}
        </div>
      </div>
    </div>
  );
}
