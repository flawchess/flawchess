import { useState } from 'react';
import type { ReactElement } from 'react';
import { ChevronLeft, ChevronRight, Flag, Handshake, Repeat2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { BOT_ACTION_BUTTON_CLASS } from '@/components/bots/chipStyles';
import { DrawOfferConfirmDialog } from '@/components/bots/DrawOfferConfirmDialog';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export interface BotGameMobileBarProps {
  onResign: () => void;
  onOfferDraw: () => void;
  /** Net disabled state of the Draw action (offer pending, game over, or
   * the D-04 cooldown). No tooltip on touch — disabled is the whole signal. */
  offerDrawDisabled: boolean;
  onBack: () => void;
  onForward: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
}

/**
 * BotGameMobileBar — Phase 223 (BOTVOICE-05, D-10): the mobile bot game's
 * fixed bottom action bar (Draw / Resign / Back / Forward / Flip), published
 * through the `usePublishMobileBoardControls` seam in place of the main nav.
 * Draw (quick 260916) is the user's own draw offer, brought back after Phase
 * 223 removed it; it opens the same `DrawOfferConfirmDialog` the desktop
 * `GameControls` row uses.
 *
 * A NEW component, never a prop on the shared `BoardControls` row — that row
 * measures cyclomatic complexity 16 against its own pinned ceiling of 16
 * (`frontend/eslint.config.js`), so one more branch there would fail lint.
 *
 * The Resign trigger and its two-step confirm dialog are copied verbatim
 * from `GameControls.tsx` (same three testids: `board-btn-resign`,
 * `resign-confirm-dialog`, `board-btn-resign-confirm`), so every existing
 * assertion against them keeps matching after the move. Back/Forward/Flip
 * reuse the shipped `board-btn-back` / `board-btn-forward` / `board-btn-flip`
 * testids from `BoardControls` for the same reason.
 *
 * Phase 223 UAT: all four actions now render in the MAIN NAV's shape —
 * icon over label, `flex-1` columns across the bar — so the bar the bot game
 * swaps in reads as the same furniture as the bar it replaced, instead of one
 * worded outline button beside three bare glyphs. Resign is the only action
 * whose glyph is new (`Flag`, the universal resign affordance); the labels
 * stay at the project's `text-sm` floor rather than copying the main nav's
 * pre-existing `text-xs` (frontend/CLAUDE.md typography rule).
 */

/** Icon-over-label column, matching `MobileBottomBar`'s main-nav items. */
const BOT_BAR_BUTTON_CLASS = 'h-auto flex-1 flex-col gap-1 px-1 py-2';

export function BotGameMobileBar({
  onResign,
  onOfferDraw,
  offerDrawDisabled,
  onBack,
  onForward,
  onFlip,
  canGoBack,
  canGoForward,
}: BotGameMobileBarProps): ReactElement {
  const [resignDialogOpen, setResignDialogOpen] = useState(false);
  const [drawDialogOpen, setDrawDialogOpen] = useState(false);

  const handleConfirmResign = (): void => {
    setResignDialogOpen(false);
    onResign();
  };

  return (
    // `pb-2` (Phase 223 UAT): on phones without a bottom safe-area inset the
    // bar's own `pb-safe` is 0, so Resign sat flush against the browser's
    // bottom toolbar; this keeps a small gap under the buttons.
    <div data-testid="bot-game-mobile-bar" className="flex flex-1 items-center gap-1 pb-2">
      <Button
        variant="ghost"
        className={BOT_BAR_BUTTON_CLASS}
        onClick={() => setDrawDialogOpen(true)}
        disabled={offerDrawDisabled}
        data-testid="board-btn-offer-draw"
      >
        <Handshake className="size-5" aria-hidden="true" />
        <span className="text-sm">Draw</span>
      </Button>
      <DrawOfferConfirmDialog
        open={drawDialogOpen}
        onOpenChange={setDrawDialogOpen}
        onConfirm={onOfferDraw}
      />
      <Button
        variant="ghost"
        className={BOT_BAR_BUTTON_CLASS}
        onClick={() => setResignDialogOpen(true)}
        data-testid="board-btn-resign"
      >
        <Flag className="size-5" aria-hidden="true" />
        <span className="text-sm">Resign</span>
      </Button>
      <Dialog open={resignDialogOpen} onOpenChange={setResignDialogOpen}>
        <DialogContent data-testid="resign-confirm-dialog">
          <DialogHeader>
            <DialogTitle>Resign this game?</DialogTitle>
            <DialogDescription>You&apos;ll lose this game against the bot.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              className={BOT_ACTION_BUTTON_CLASS}
              data-testid="board-btn-resign-cancel"
              onClick={() => setResignDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              className={BOT_ACTION_BUTTON_CLASS}
              onClick={handleConfirmResign}
              data-testid="board-btn-resign-confirm"
            >
              Resign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Button
        variant="ghost"
        className={BOT_BAR_BUTTON_CLASS}
        onClick={onBack}
        disabled={!canGoBack}
        data-testid="board-btn-back"
      >
        <ChevronLeft className="size-5" aria-hidden="true" />
        <span className="text-sm">Back</span>
      </Button>
      <Button
        variant="ghost"
        className={BOT_BAR_BUTTON_CLASS}
        onClick={onForward}
        disabled={!canGoForward}
        data-testid="board-btn-forward"
      >
        <ChevronRight className="size-5" aria-hidden="true" />
        <span className="text-sm">Next</span>
      </Button>
      <Button
        variant="ghost"
        className={BOT_BAR_BUTTON_CLASS}
        onClick={onFlip}
        data-testid="board-btn-flip"
      >
        <Repeat2 className="size-5" aria-hidden="true" />
        <span className="text-sm">Flip</span>
      </Button>
    </div>
  );
}
