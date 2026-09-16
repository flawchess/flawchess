import { useState } from 'react';
import type { ReactElement } from 'react';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
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

interface GameControlsProps {
  /** Net disabled state of the Draw button: an offer already pending (either
   * direction), the game over, or the D-04 cooldown. */
  offerDrawDisabled: boolean;
  /** True ONLY while the D-04 post-decline cooldown is the reason the button
   * is disabled — gates the explanatory tooltip. */
  drawCooldownActive: boolean;
  onOfferDrawConfirmed: () => void;
  onResignConfirmed: () => void;
}

/** Tooltip copy for the cooldown-disabled Draw button. */
const DRAW_COOLDOWN_TOOLTIP = 'Wait a few more moves before offering again';

/**
 * Draw / Resign control row for the bot-game board (Phase 169 Plan 05).
 * Phase 223 BOTVOICE-05 reduced it to Resign-only; quick 260916 brings the
 * user-side Draw offer back, now behind the same two-step confirm dialog
 * shape Resign uses (`DrawOfferConfirmDialog`, shared with
 * `BotGameMobileBar`). The in-game mute toggle stays retired: sounds always
 * play for now, and a proper disable option is a later phase (`sounds.ts`
 * keeps the mute plumbing for it). On mobile this component isn't rendered
 * at all — the same two triggers + dialogs live in `BotGameMobileBar`,
 * reusing the same testids.
 *
 * Both triggers are brand-outline; only the actual Resign confirm action is
 * destructive-colored, per CLAUDE.md's primary/secondary button rule.
 */
export function GameControls({
  offerDrawDisabled,
  drawCooldownActive,
  onOfferDrawConfirmed,
  onResignConfirmed,
}: GameControlsProps): ReactElement {
  const [resignDialogOpen, setResignDialogOpen] = useState(false);
  const [drawDialogOpen, setDrawDialogOpen] = useState(false);

  const handleConfirmResign = (): void => {
    setResignDialogOpen(false);
    onResignConfirmed();
  };

  const drawButton = (
    <Button
      variant="brand-outline"
      className={cn(BOT_ACTION_BUTTON_CLASS, drawCooldownActive ? 'w-full' : 'flex-1')}
      disabled={offerDrawDisabled}
      onClick={() => setDrawDialogOpen(true)}
      data-testid="board-btn-offer-draw"
    >
      Draw
    </Button>
  );

  return (
    <div className="flex items-center gap-2">
      {/* The tooltip wraps ONLY in the cooldown branch (WR-04 lesson from
          Phase 169): a disabled button swallows pointer events, so the
          wrapping `<span>` is what receives the hover, and it carries the
          `flex-1` the button inside stretches into with `w-full`. */}
      {drawCooldownActive ? (
        <Tooltip content={DRAW_COOLDOWN_TOOLTIP}>
          <span className="flex-1">{drawButton}</span>
        </Tooltip>
      ) : (
        drawButton
      )}
      <DrawOfferConfirmDialog
        open={drawDialogOpen}
        onOpenChange={setDrawDialogOpen}
        onConfirm={onOfferDrawConfirmed}
      />
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
