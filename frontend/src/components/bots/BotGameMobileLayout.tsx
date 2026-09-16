import type { ReactElement } from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PlayerBar } from '@/components/board/PlayerBar';
import { resolvePlayerRow, type BotPlayerRowInputs } from '@/components/bots/botPlayerRow';
import { usePublishMobileBoardControls } from '@/lib/mobileBoardControls';

export interface BotGameMobileLayoutProps extends BotPlayerRowInputs {
  /** Navigates to the roster WITHOUT clearing the in-progress snapshot — a
   * live game stays in the existing pending store and `ResumeGate` handles
   * the return (223-CONTEXT discretion note). */
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
  onOfferDraw: () => void;
  offerDrawDisabled: boolean;
  onBack: () => void;
  onForward: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
  /** Caps the stack at the board's width and centers it — exactly the
   * helper this component replaces (`renderMobileLayout` in `Bots.tsx`). */
  boardPx: number;
}

/**
 * BotGameMobileLayout — Phase 223 (BOTVOICE-05, D-10/D-11): replaces the
 * page's old mobile render helper. Top to bottom: a top bar holding only a
 * back arrow (the gear is dropped per CONTEXT's discretion note — an icon
 * with no sheet behind it is worse than no icon), the avatar-and-bubble row,
 * then the board flanked by the same two `PlayerBar` rows the desktop layout
 * and the analysis board use (name + rating label left, clock right).
 *
 * Phase 223 UAT: those player rows REPLACE the earlier nameless clock strip
 * (D-11's "no bot identity on mobile" was reversed at UAT — the strips are
 * the same ones the analysis board shows, so the bot's name and calibrated
 * label are on screen on every breakpoint).
 *
 * Publishes the four-action payload itself via
 * `usePublishMobileBoardControls`, so the takeover is scoped to this
 * component's own mount — the store is cleared automatically on unmount
 * when the game ends or the breakpoint flips. This is also what keeps that
 * branch out of `BotsGame`'s own pinned complexity budget.
 *
 * The in-page shared control row and the game-controls row are NOT rendered
 * here — they are exactly the chrome whose removal buys the board its extra
 * width (RESEARCH Pitfall 5, SC4).
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
  onOfferDraw,
  offerDrawDisabled,
  onBack,
  onForward,
  onFlip,
  canGoBack,
  canGoForward,
  boardPx,
}: BotGameMobileLayoutProps): ReactElement {
  usePublishMobileBoardControls({
    onResign,
    onOfferDraw,
    offerDrawDisabled,
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
