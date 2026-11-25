import type { ReactElement } from 'react';
import { PlayerBar } from '@/components/board/PlayerBar';
import { resolvePlayerRow, type BotPlayerRowInputs } from '@/components/bots/botPlayerRow';

export interface BotGameMobileLayoutProps extends BotPlayerRowInputs {
  bubble: ReactElement;
  board: ReactElement;
  /** Same `ChessBoard` semantics as the desktop layout: `false` = white at
   * the bottom. The row for the side at the top of the board is the top row. */
  flipped: boolean;
  /** The viewed-ply FEN — both rows' material tracks the board during
   * scroll-back. */
  fen: string;
  /** Caps the stack at the board's width and centers it. */
  boardPx: number;
}

/**
 * BotGameMobileLayout, the stacked layout (phones, and foldables and tablets in portrait
 * below 1024px). Top to bottom: the avatar-and-bubble row,
 * then the board flanked by the same two `PlayerBar` rows the desktop layout
 * and the analysis board use (name + rating label left, clock right), so the
 * bot's name and calibrated label are on screen on every breakpoint.
 *
 * No control row of any kind: `BotsGame` publishes the actions to the fixed bottom bar, and
 * the way back and the settings sit in that bar's More menu. The chrome this layout leaves
 * out is exactly what buys the board its extra width.
 */
export function BotGameMobileLayout({
  persona,
  playerName,
  currentStrength,
  userColor,
  activeColor,
  whiteClockMs,
  blackClockMs,
  bubble,
  board,
  flipped,
  fen,
  boardPx,
}: BotGameMobileLayoutProps): ReactElement {
  const rowInputs: BotPlayerRowInputs = {
    persona,
    playerName,
    currentStrength,
    userColor,
    activeColor,
    whiteClockMs,
    blackClockMs,
  };
  const topRow = resolvePlayerRow(flipped ? 'white' : 'black', rowInputs);
  const bottomRow = resolvePlayerRow(flipped ? 'black' : 'white', rowInputs);

  return (
    <div className="mx-auto flex w-full flex-col gap-2" style={{ maxWidth: boardPx }}>
      {bubble}
      <div className="flex flex-col gap-1">
        <PlayerBar {...topRow} rating={null} fen={fen} />
        {board}
        <PlayerBar {...bottomRow} rating={null} fen={fen} />
      </div>
    </div>
  );
}
