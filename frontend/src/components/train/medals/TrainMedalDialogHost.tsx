/**
 * TrainMedalDialogHost — fetches the user's unclaimed weekly medals and shows
 * the claim dialog on the Train landing (Phase 231).
 *
 * D-10: mounted by TrainStartScreen's empty, completed and fresh/resume/warmup
 * branches only (never loading or error; Train.tsx renders the landing outside
 * the solve loop and the score screen is separate), and never for guests. It
 * opens once per mount, when the list fetched AFTER this mount is non-empty:
 * `isFetchedAfterMount` rules out a stale cache entry showing medals that were
 * already claimed. Claim and dismiss both close it for the visit and POST the
 * shown keys once; a failed POST leaves the medals unclaimed, so they come back
 * next visit (D-13).
 *
 * Impersonation guard (RESEARCH Pitfall 6, T-231-16): under an admin
 * impersonation session the host neither fetches nor opens, so an admin cannot
 * consume the user's celebration.
 *
 * D-04: leaderboard_hidden is deliberately not consulted; a viewer hidden now
 * still gets their own dialog.
 *
 * No isError UI: a failed read must not put an error on the landing, and the
 * global QueryCache/MutationCache onError already reports it to Sentry. No
 * analytics call either (locked): the celebrated_at row is the record.
 */
import { useState } from 'react';
import type { ReactElement } from 'react';
import { MedalClaimDialog } from '@/components/train/medals/MedalClaimDialog';
import { useClaimMedals, useUnclaimedMedals } from '@/hooks/useTrainMedals';
import { useUserProfile } from '@/hooks/useUserProfile';
import { prefersReducedMotion } from '@/lib/confetti';
import { useMuted } from '@/lib/sounds';
import type { MedalKey, UnclaimedMedal } from '@/types/train';

export function TrainMedalDialogHost({ isGuest }: { isGuest: boolean }): ReactElement {
  const { data: profile } = useUserProfile();
  const impersonating = (profile?.impersonation ?? null) !== null;
  const enabled = !isGuest && profile !== undefined && !impersonating;
  const unclaimed = useUnclaimedMedals({ enabled });
  const claim = useClaimMedals();
  const muted = useMuted();
  const [closed, setClosed] = useState(false);

  const medals = unclaimed.data?.medals ?? [];
  const open = !closed && unclaimed.isFetchedAfterMount && medals.length > 0;

  // Bug fix: a successful claim prunes the claimed keys from the cached list
  // (useClaimMedals.onSuccess), so the live `medals` turns [] while the dialog is
  // still fading out. Radix keeps the content mounted for the exit animation,
  // which flashed "You won 0 medals!" and an empty list. Keep the medals shown
  // while open and render those frozen ones once closed. Adjusting state during
  // render (not an effect) so there is never a frame with stale content.
  const [shown, setShown] = useState<readonly UnclaimedMedal[]>([]);
  if (open && shown !== medals) setShown(medals);

  function finish(keys: MedalKey[]): void {
    setClosed(true);
    claim.mutate(keys);
  }

  return (
    <MedalClaimDialog
      open={open}
      medals={open ? medals : shown}
      muted={muted}
      reducedMotion={prefersReducedMotion()}
      onClaim={finish}
      onDismiss={finish}
    />
  );
}
