import { useState } from 'react';
import type { ReactElement } from 'react';
import { ChevronLeft, ChevronRight, Flag, Repeat2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { BOT_ACTION_BUTTON_CLASS } from '@/components/bots/chipStyles';
import { trackFeature } from '@/lib/analytics';
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
  onBack: () => void;
  onForward: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
}

/**
 * BotGameMobileBar: the mobile bot game's
 * fixed four-action bottom bar (Resign / Back / Forward / Flip), published
 * through the `usePublishMobileBoardControls` seam in place of the main nav.
 *
 * A new component rather than a prop on the shared `BoardControls` row, so the
 * bot-only branches stay out of that shared row.
 *
 * The Resign trigger and its two-step confirm dialog mirror `GameControls.tsx`
 * (same three testids: `board-btn-resign`, `resign-confirm-dialog`,
 * `board-btn-resign-confirm`). Back/Forward/Flip reuse the
 * `board-btn-back` / `board-btn-forward` / `board-btn-flip` testids from
 * `BoardControls`.
 *
 * All four actions render in the MAIN NAV's shape — icon over label, `flex-1`
 * columns across the bar — so the bar the bot game swaps in reads as the same
 * furniture as the bar it replaces. Resign is the only action whose glyph is
 * new (`Flag`, the universal resign affordance); the labels stay at the
 * project's `text-sm` floor rather than copying the main nav's `text-xs`
 * (frontend/CLAUDE.md typography rule).
 */

/** Icon-over-label column, matching `MobileBottomBar`'s main-nav items. */
const BOT_BAR_BUTTON_CLASS = 'h-auto flex-1 flex-col gap-1 px-1 py-2';

export function BotGameMobileBar({
  onResign,
  onBack,
  onForward,
  onFlip,
  canGoBack,
  canGoForward,
}: BotGameMobileBarProps): ReactElement {
  const [resignDialogOpen, setResignDialogOpen] = useState(false);

  const handleConfirmResign = (): void => {
    setResignDialogOpen(false);
    onResign();
  };

  return (
    // `pb-2`: on phones without a bottom safe-area inset the
    // bar's own `pb-safe` is 0, so Resign sat flush against the browser's
    // bottom toolbar; this keeps a small gap under the buttons.
    <div data-testid="bot-game-mobile-bar" className="flex flex-1 items-center gap-1 pb-2">
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
        onClick={() => {
          onFlip();
          trackFeature('board-tool', { target: 'flip' });
        }}
        data-testid="board-btn-flip"
      >
        <Repeat2 className="size-5" aria-hidden="true" />
        <span className="text-sm">Flip</span>
      </Button>
    </div>
  );
}
