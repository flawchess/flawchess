import type { ReactElement } from 'react';
import { Button } from '@/components/ui/button';
import { BOT_ACTION_BUTTON_CLASS } from '@/components/bots/chipStyles';

export interface BotDrawOfferActionsProps {
  /** True while the bot has a live outgoing draw offer (Phase 183, D-07 —
   * `useBotGame`'s `botDrawOffer`). Renders nothing while false. */
  offerLive: boolean;
  onAccept: () => void;
  onDecline: () => void;
}

/**
 * BotDrawOfferActions — Phase 223 (BOTVOICE-05, D-12): the Accept/Decline
 * pair lifted out of the retired draw-offer banner component, now rendered inside
 * `BotGameBubble`'s actions slot. It is deliberately not a Dialog and does
 * not block the board — play continues underneath it, and the hook
 * auto-expires the offer on the user's next committed move (no extra logic
 * needed here). Both testids are preserved verbatim from the banner so every
 * existing assertion against them keeps matching after the move.
 */
export function BotDrawOfferActions({
  offerLive,
  onAccept,
  onDecline,
}: BotDrawOfferActionsProps): ReactElement | null {
  if (!offerLive) return null;

  return (
    <>
      <Button
        variant="default"
        className={BOT_ACTION_BUTTON_CLASS}
        onClick={onAccept}
        data-testid="btn-accept-bot-draw"
      >
        Accept
      </Button>
      <Button
        variant="brand-outline"
        className={BOT_ACTION_BUTTON_CLASS}
        onClick={onDecline}
        data-testid="btn-decline-bot-draw"
      >
        Decline
      </Button>
    </>
  );
}
