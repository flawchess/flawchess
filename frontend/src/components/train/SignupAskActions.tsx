import type { ReactElement } from 'react';
import { useNavigate } from 'react-router';
import { Button } from '@/components/ui/button';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { useAuth } from '@/hooks/useAuth';

/**
 * SignupAskActions: Phase 224 (S-4, D-05, D-07; GUESTACT-05, GUESTACT-07,
 * GUESTACT-11). The shared "What changes?" + "Sign up free" action pair rendered into
 * `TrainBotBubble`'s existing `actions` slot on three surfaces: the guest
 * branch of the Train score screen (`source="train-score"`), the Import
 * page's guest promo bubble (`source="import-promo"`) and, since the 224 UAT
 * (round 2), the guest Train landing bubble (`source="train-landing"`, which
 * replaced the "Warm-up session" info card). Each surface carries
 * its own `data-umami-event-source` so lever B is attributable per surface
 * (S-7, ROADMAP SC 9).
 *
 * Shape copied verbatim from `BotDrawOfferActions` (bare two-`Button`
 * fragment, no wrapper element; the host bubble supplies the row layout).
 * Two deliberate deltas from that analog: `TRAIN_BUTTON_CLASS` (not the
 * bots-scoped `BOT_ACTION_BUTTON_CLASS`), and the emphasis order is reversed:
 * "What changes?" (`brand-outline`, secondary) first, "Sign up free"
 * (`default`, primary) second, per S-4. The secondary label was "Why?" until
 * the 224 UAT (round 1) asked for "What changes?", which matches the /welcome
 * heading it opens; the `btn-signup-why-*` testids are kept as-is.
 */

export type SignupAskSource = 'train-score' | 'import-promo' | 'train-landing';

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
          // Lifted verbatim from Import.tsx's promotion handoff (D-07): clear
          // the auth session and mark the intent BEFORE the hard navigation,
          // never re-authored, never gated on guest_token presence (the
          // documented 2026-06-23 regression).
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
