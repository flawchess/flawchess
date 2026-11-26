/**
 * BlunderCheckNotice: the Blunder Check launch notice (Phase 251 D-21), above the mode cards.
 *
 * It introduces blunder check to existing streak holders and tells them it now counts toward the
 * streak, with the amount set in the mode's settings (on the Blunder Check card, so the copy names
 * the settings, not a direction). The server decides when it shows (`blunder_check_notice`:
 * existing streak users, 14-day window, hidden after a blunder-check completion or amount change);
 * dismissing hides it at once and tells the server. Renders nothing while the flag is off or the
 * progress has not loaded.
 */
import type { ReactElement } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useDismissBlunderCheckNotice, useTrainProgress } from '@/hooks/useTrainProgress';
import { trackFeature } from '@/lib/analytics';
import { LAUNCH_NOTICE_TINT_CLASS } from '@/lib/theme';
import { cn } from '@/lib/utils';

export function BlunderCheckNotice(): ReactElement | null {
  const { data } = useTrainProgress();
  if (data?.blunder_check_notice !== true) return null;
  return <NoticeBody />;
}

/** The dismiss mutation lives here, so it only exists while the notice shows. */
function NoticeBody(): ReactElement {
  const dismiss = useDismissBlunderCheckNotice();
  return (
    <div
      className={cn('flex w-full items-start gap-2 rounded-md py-2 pl-3 pr-1', LAUNCH_NOTICE_TINT_CLASS)}
      data-testid="train-blunder-check-notice"
    >
      <p className="flex-1 self-center text-sm">
        New: Blunder Check. Call each move of a real game before it is played: good or blunder? It
        now counts toward your streak, and you can set the amount or turn it off in the Blunder Check settings.
      </p>
      <Button
        variant="ghost"
        size="icon"
        className="flex-shrink-0"
        aria-label="Dismiss"
        data-testid="btn-train-blunder-check-notice-dismiss"
        onClick={() => {
          trackFeature('action', { target: 'train-blunder-check-notice-dismiss' });
          dismiss.mutate();
        }}
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </Button>
    </div>
  );
}
