import type { ReactElement } from 'react';
import { Button } from '@/components/ui/button';
import { BOT_ACTION_BUTTON_CLASS } from '@/components/bots/chipStyles';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export interface DrawOfferConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Fires once the user confirms; the dialog closes itself first. */
  onConfirm: () => void;
}

/**
 * DrawOfferConfirmDialog — the two-step confirmation for the USER's own
 * draw offer (quick 260916: brings the Phase 169 D-01 user offer back after
 * Phase 223 removed it from every breakpoint). One component shared by the
 * desktop `GameControls` row and the mobile `BotGameMobileBar`, so both
 * breakpoints carry the same copy and the same three testids
 * (`draw-offer-confirm-dialog`, `board-btn-offer-draw-cancel`,
 * `board-btn-offer-draw-confirm`), mirroring the resign dialog those two
 * bars already duplicate.
 *
 * The confirm action is the primary (`default`) variant, not destructive:
 * offering a draw costs nothing beyond the D-04 cooldown if it is declined.
 */
export function DrawOfferConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
}: DrawOfferConfirmDialogProps): ReactElement {
  const handleConfirm = (): void => {
    onOpenChange(false);
    onConfirm();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="draw-offer-confirm-dialog">
        <DialogHeader>
          <DialogTitle>Offer a draw?</DialogTitle>
          <DialogDescription>
            The bot accepts only when it judges the position level. If it declines, you can offer
            again after a few more moves.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            className={BOT_ACTION_BUTTON_CLASS}
            data-testid="board-btn-offer-draw-cancel"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            variant="default"
            className={BOT_ACTION_BUTTON_CLASS}
            onClick={handleConfirm}
            data-testid="board-btn-offer-draw-confirm"
          >
            Offer draw
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
