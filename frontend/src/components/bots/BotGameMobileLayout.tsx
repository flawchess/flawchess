import type { ReactElement } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SettingsSheetButton } from '@/components/settings/SettingsSheetButton';
import { PlayerBar } from '@/components/board/PlayerBar';
import { resolvePlayerRow, type BotPlayerRowInputs } from '@/components/bots/botPlayerRow';
import { usePublishMobileBoardControls } from '@/lib/mobileBoardControls';

export interface BotGameMobileLayoutProps extends BotPlayerRowInputs {
  /** Navigates to the roster WITHOUT clearing the in-progress snapshot — a
   * live game stays in the existing pending store and `ResumeGate` handles
   * the return. */
  onBackToRoster: () => void;
  bubble: ReactElement;
  board: ReactElement;
  /** Same `ChessBoard` semantics as the desktop layout: `false` = white at
   * the bottom. The row for the side at the top of the board is the top row. */
  flipped: boolean;
  /** The viewed-ply FEN — both rows' material tracks the board during
   * scroll-back. */
  fen: string;
  onResign: () => void;
  onBack: () => void;
  onForward: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
  /** Caps the stack at the board's width and centers it. */
  boardPx: number;
}

/**
 * BotGameMobileLayout. Top to bottom: a top bar holding a back
 * arrow and, at the far end, a settings cogwheel that opens the settings sheet
 * in place (sound can be switched off mid-game without
 * navigating away, which would trigger the ResumeGate overlay on return),
 * the avatar-and-bubble row,
 * then the board flanked by the same two `PlayerBar` rows the desktop layout
 * and the analysis board use (name + rating label left, clock right), so the
 * bot's name and calibrated label are on screen on every breakpoint.
 *
 * Publishes the four-action payload itself via
 * `usePublishMobileBoardControls`, so the takeover is scoped to this
 * component's own mount — the store is cleared automatically on unmount
 * when the game ends or the breakpoint flips.
 *
 * The in-page shared control row and the game-controls row are NOT rendered
 * here — they are exactly the chrome whose removal buys the board its extra
 * width.
 */
export function BotGameMobileLayout({
  persona,
  playerName,
  currentStrength,
  userColor,
  activeColor,
  whiteClockMs,
  blackClockMs,
  onBackToRoster,
  bubble,
  board,
  flipped,
  fen,
  onResign,
  onBack,
  onForward,
  onFlip,
  canGoBack,
  canGoForward,
  boardPx,
}: BotGameMobileLayoutProps): ReactElement {
  usePublishMobileBoardControls({
    onResign,
    onBack,
    onForward,
    onFlip,
    canGoBack,
    canGoForward,
  });

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
      <div className="flex items-center">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Back to bot roster"
          data-testid="bots-back"
          onClick={onBackToRoster}
        >
          <ArrowLeft className="size-5" aria-hidden="true" />
        </Button>
        <SettingsSheetButton testId="btn-bots-settings" className="ml-auto" />
      </div>
      {bubble}
      <div className="flex flex-col gap-1">
        <PlayerBar {...topRow} rating={null} fen={fen} />
        {board}
        <PlayerBar {...bottomRow} rating={null} fen={fen} />
      </div>
    </div>
  );
}
