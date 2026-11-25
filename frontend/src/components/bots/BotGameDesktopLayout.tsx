import type { ReactElement } from 'react';
import { PlayerBar } from '@/components/board/PlayerBar';
import { BotGameBubble } from '@/components/bots/BotGameBubble';
import { BotDrawOfferActions } from '@/components/bots/BotDrawOfferActions';
import { resolvePlayerRow, type BotPlayerRowInputs } from '@/components/bots/botPlayerRow';
import type { BotLineKey } from '@/lib/botGameCopy';

/** Grid columns of the board and the side column. The board takes its height-fitted width
 * first, capped so the side column (gap included) keeps its floor:
 * desktop: a fixed 320px side column. Below `lg` (unfolded foldables and phones in landscape):
 * the width the board leaves, between 272px and 448px like the Train drills' side column. */
function gridColumns(boardPx: number, isDesktop: boolean): string {
  return isDesktop
    ? `min(${boardPx}px, 100% - 20.5rem) 20rem`
    : `min(${boardPx}px, 100% - 17.5rem) minmax(0, 28rem)`;
}

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
  /** True while the bot has a live outgoing draw offer. */
  drawOfferLive: boolean;
  onAcceptDraw: () => void;
  onDeclineDraw: () => void;
  board: ReactElement;
  moveList: ReactElement;
  /** The row under the board (board controls, resign). `null` below `lg`, where the fixed
   * bottom bar carries those actions. */
  inPageControls: { boardControls: ReactElement; resign: ReactElement } | null;
  boardPx: number;
}

/**
 * BotGameDesktopLayout: desktop, and any landscape screen below `lg` that is wide enough for
 * two columns (unfolded foldables). The left column is the board between its two `PlayerBar`s,
 * ordered by board orientation so the side facing away from the user is on top. The side
 * column holds the avatar-and-bubble row over the move list and sits in the board's own grid
 * row: the avatar starts at the board's top edge and the move-list box ends at its bottom
 * edge. On desktop a last row puts the shared board controls under the board and the
 * resign-only control row under the side column; below `lg` there is none, see
 * `inPageControls`.
 *
 * Bug fix: the side column's content is absolutely positioned. In flow, a very long move list
 * stretched the row instead of scrolling, and the height fit then shrank the board to its floor.
 *
 * This component owns every branch the layout needs (orientation ordering,
 * the bubble/draw-offer construction; the guest gate on the user's rating
 * label lives in `resolvePlayerRow`) so `BotsGame` gains none of them.
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
  moveList,
  inPageControls,
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
    <div
      className="grid justify-center gap-x-2 gap-y-1"
      style={{ gridTemplateColumns: gridColumns(boardPx, inPageControls !== null) }}
    >
      <div className="col-start-1 row-start-1 min-w-0">
        <PlayerBar {...topRow} rating={null} fen={fen} />
      </div>
      <div className="col-start-1 row-start-2 min-w-0">{board}</div>
      <div className="relative col-start-2 row-start-2 min-w-0" data-testid="bot-game-side-column">
        <div className="absolute inset-0 flex flex-col gap-3">
          <BotGameBubble persona={persona} line={botLine} actions={drawOfferActions} />
          {moveList}
        </div>
      </div>
      <div className="col-start-1 row-start-3 min-w-0">
        <PlayerBar {...bottomRow} rating={null} fen={fen} />
      </div>
      {inPageControls !== null && (
        <>
          <div className="col-start-1 row-start-4 mt-1 min-w-0">{inPageControls.boardControls}</div>
          <div className="col-start-2 row-start-4 mt-1 min-w-0">{inPageControls.resign}</div>
        </>
      )}
    </div>
  );
}
