/**
 * MedalClaimDialog — the claim-and-celebrate dialog listing every unclaimed
 * weekly medal (Phase 231, D-11/D-13). Presentational: the host owns fetching
 * and the claim POST, the admin demo renders it from fixtures.
 *
 * Claim and dismiss (close button, Escape, outside click) each call exactly one
 * of onClaim / onDismiss with the shown keys; a settled ref keeps one open
 * cycle to one callback even if Radix reports a close after a Claim. Names
 * never appear here, only the viewer's own medals.
 *
 * Claim path (D-12, D-13), in this order inside the tap: unlockAudio() (iOS
 * only allows Web Audio after a gesture), then the existing 'game-win' chime
 * once per tap whatever the medal count (unless muted), then confetti (unless
 * reduced motion; the canvas outlives the dialog), then the guarded onClaim.
 * Dismiss stays silent. No new audio asset or SoundEvent.
 *
 * `muted` and `reducedMotion` arrive as props (not read from hooks here) so the
 * demo can simulate them; playSound also checks the persisted mute preference
 * itself. No analytics event fires for Claim or dismiss (locked): the
 * celebrated_at row is the record.
 */
import { useEffect, useRef } from 'react';
import type { ReactElement } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { MedalIcon } from '@/components/train/medals/MedalIcon';
import { fireWinConfetti } from '@/lib/confetti';
import { playSound, unlockAudio } from '@/lib/sounds';
import { boardValueLabel } from '@/lib/trainLeaderboard';
import {
  CLAIM_BUTTON_LABEL,
  MEDAL_POP_STAGGER_MS,
  medalDialogTitle,
  medalEntryLabel,
  medalKeys,
  weekOfLabel,
} from '@/lib/trainMedals';
import type { MedalKey, UnclaimedMedal } from '@/types/train';

export interface MedalClaimDialogProps {
  open: boolean;
  /** Server order: newest week first, Points before Accuracy. */
  medals: readonly UnclaimedMedal[];
  /** Simulated or real mute state; a muted Claim stays silent. */
  muted: boolean;
  /** Simulated or real reduced-motion preference; suppresses confetti and the pop. */
  reducedMotion: boolean;
  onClaim: (keys: MedalKey[]) => void;
  onDismiss: (keys: MedalKey[]) => void;
}

export function MedalClaimDialog({
  open,
  medals,
  muted,
  reducedMotion,
  onClaim,
  onDismiss,
}: MedalClaimDialogProps): ReactElement {
  // One callback per open cycle; reset whenever the dialog opens again.
  const settledRef = useRef(false);
  useEffect(() => {
    if (open) settledRef.current = false;
  }, [open]);

  function settle(callback: (keys: MedalKey[]) => void): void {
    if (settledRef.current) return;
    settledRef.current = true;
    callback(medalKeys(medals));
  }

  function handleClaim(): void {
    // A second tap before the container closes the dialog must not replay the chime.
    if (settledRef.current) return;
    // Order matters: unlock inside the tap before anything plays (iOS).
    unlockAudio();
    if (!muted) playSound('game-win');
    if (!reducedMotion) fireWinConfetti();
    settle(onClaim);
  }

  function handleDismiss(): void {
    settle(onDismiss);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) handleDismiss();
      }}
    >
      <DialogContent
        showCloseButton={false}
        aria-describedby={undefined}
        data-testid="train-medal-dialog"
      >
        <DialogHeader>
          <DialogTitle>{medalDialogTitle(medals.length)}</DialogTitle>
        </DialogHeader>
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-2 right-2"
          aria-label="Close"
          data-testid="btn-train-medal-dialog-close"
          onClick={handleDismiss}
        >
          <X />
        </Button>
        <ul className="flex flex-col gap-3" data-testid="train-medal-dialog-list">
          {medals.map((entry, index) => (
            <li
              key={`${entry.week_start}-${entry.board}`}
              className="flex items-center gap-3"
              data-testid={`train-medal-dialog-entry-${index}`}
            >
              <span
                className={reducedMotion ? 'inline-flex' : 'inline-flex animate-medal-pop'}
                style={reducedMotion ? undefined : { animationDelay: `${index * MEDAL_POP_STAGGER_MS}ms` }}
              >
                <MedalIcon kind={entry.medal} className="size-10" />
              </span>
              <div className="flex min-w-0 flex-col">
                <span className="font-medium">{medalEntryLabel(entry.medal, entry.board, entry.shared)}</span>
                <span className="text-sm text-muted-foreground">
                  {`${weekOfLabel(entry.week_start)} · ${boardValueLabel(entry.board, entry.value)}`}
                </span>
              </div>
            </li>
          ))}
        </ul>
        {/* Last child: the footer bleeds to the dialog edges. */}
        <DialogFooter>
          <Button variant="default" data-testid="btn-train-medal-claim" onClick={handleClaim}>
            {CLAIM_BUTTON_LABEL}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
