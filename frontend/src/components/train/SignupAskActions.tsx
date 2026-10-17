import type { ReactElement } from 'react';
import { useNavigate } from 'react-router';
import { Button } from '@/components/ui/button';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { useAuth } from '@/hooks/useAuth';

/**
 * SignupAskActions: the shared "What changes?" + "Sign up free" action pair
 * rendered into `TrainBotBubble`'s `actions` slot on four surfaces: the guest
 * Train score screen (`source="train-score"`), the Import page's guest promo
 * bubble (`source="import-promo"`), the guest Train landing bubble
 * (`source="train-landing"`) and the guest weekly-leaderboard card
 * (`source="train-leaderboard"`). Each surface carries its own
 * `data-umami-event-source` so the sign-up funnel is attributable per
 * surface.
 *
 * Shape copied verbatim from `BotDrawOfferActions` (bare two-`Button`
 * fragment, no wrapper element; the host bubble supplies the row layout).
 * Two deliberate deltas from that analog: `TRAIN_BUTTON_CLASS` (not the
 * bots-scoped `BOT_ACTION_BUTTON_CLASS`), and the emphasis order is reversed:
 * "What changes?" (`brand-outline`, secondary) first, "Sign up free"
 * (`default`, primary) second. The secondary label matches the /welcome
 * heading it opens; the `btn-signup-why-*` testids predate the "What
 * changes?" label and keep that name.
 */

export type SignupAskSource =
  | 'train-score'
  | 'import-promo'
  | 'train-landing'
  | 'train-leaderboard';

export interface SignupAskActionsProps {
  source: SignupAskSource;
}

export function SignupAskActions({ source }: SignupAskActionsProps): ReactElement {
  const navigate = useNavigate();
  const { logoutForPromotion } = useAuth();

  return (
    <>
      <Button
        variant="brand-outline"
        className={TRAIN_BUTTON_CLASS}
        onClick={() => navigate('/welcome')}
        data-testid={`btn-signup-why-${source}`}
        // No data-umami-event here, deliberately: this is internal
        // react-router navigation, and frontend/CLAUDE.md documents that
        // data-umami-event on an internal route control downgrades the click
        // into a full page reload (the tracker preventDefault()s the click
        // and assigns location.href itself). Don't "fix" this omission.
      >
        What changes?
      </Button>
      <Button
        variant="default"
        className={TRAIN_BUTTON_CLASS}
        onClick={() => {
          // Lifted verbatim from Import.tsx's promotion handoff: clear the
          // auth session BEFORE the hard navigation; guest_token is kept so
          // sign-up promotes the saved guest in place. Never gate this on
          // guest_token presence (the 2026-06-23 regression).
          logoutForPromotion();
          window.location.href = '/login?tab=register';
        }}
        data-testid={`btn-signup-free-${source}`}
        data-umami-event="signup-cta"
        data-umami-event-source={source}
      >
        Sign up free
      </Button>
    </>
  );
}
