import { useState } from 'react';
import type { ReactElement } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { BOT_ACTION_BUTTON_CLASS } from '@/components/bots/chipStyles';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface GameControlsProps {
  onResignConfirmed: () => void;
}

/**
 * Resign control row for the bot-game board (desktop only; on mobile
 * `BotGameMobileBar` renders the same trigger and confirm dialog with the
 * same three testids).
 *
 * Resign uses a two-step confirmation via the existing `Dialog`
 * primitive (the trigger stays brand-outline; only the actual confirm action
 * is destructive-colored, per CLAUDE.md's primary/secondary button rule).
 */
export function GameControls({ onResignConfirmed }: GameControlsProps): ReactElement {
  const [resignDialogOpen, setResignDialogOpen] = useState(false);

  const handleConfirmResign = (): void => {
    setResignDialogOpen(false);
    onResignConfirmed();
  };

  return (
    <div className="flex items-center gap-2">
      <Button
        variant="brand-outline"
        className={cn(BOT_ACTION_BUTTON_CLASS, 'flex-1')}
        onClick={() => setResignDialogOpen(true)}
        data-testid="board-btn-resign"
      >
        Resign
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
    </div>
  );
}
