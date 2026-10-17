/**
 * TrainReminderResurfaceBanner — the standalone re-surface prompt that
 * closes the iOS install→reminder two-session cliff. A user who
 * tapped the iOS install affordance (`useTrainReminderSlot`'s `ios-tabbed`
 * branch) recorded `reminder_intent_at` server-side and left
 * the tab; on their next standalone launch, `App.tsx`'s `ProtectedLayout`
 * (via `useReminderResurfaceRedirect`) has already routed them to `/train`,
 * and this banner is the visible prompt that greets them there.
 *
 * Self-contained: computes its own mount decision via `useReminderResurface`
 * and renders nothing until every gating signal has resolved to the
 * qualifying combination — never a placeholder, never a skeleton (fail-safe:
 * an unresolved or unavailable iOS signal degrades to rendering nothing, not
 * a broken or half-rendered state).
 *
 * Reuses `ensureDeviceSubscribed` — the ONE call site for the browser
 * permission APIs (`lib/push.ts`) — and `useTrainReminderSlot`'s existing
 * `ERROR_COPY` string, so this app has one subscribe code path and one error
 * string for this exact failure, never two of either.
 *
 * Inline and non-blocking by construction: a plain `Card` in the page flow,
 * never an overlay or a popup surface that traps focus — a user who wants
 * to leave it alone can start a Train session with it still on screen.
 */
import { useState, type ReactElement } from 'react';
import { Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ERROR_COPY } from '@/components/train/useTrainReminderSlot';
import { usePushCapability } from '@/hooks/usePushCapability';
import { useReminderResurface } from '@/hooks/useReminderResurface';
import { trackFeature } from '@/lib/analytics';
import { ensureDeviceSubscribed } from '@/lib/push';
import type { DeviceSubscribeResult } from '@/lib/push';

type ResurfaceStatus = 'idle' | 'pending' | 'error';

export function TrainReminderResurfaceBanner(): ReactElement | null {
  const { shouldResurface, dismiss, markSubscribed } = useReminderResurface();
  const capability = usePushCapability();
  const [status, setStatus] = useState<ResurfaceStatus>('idle');

  // Gating on `shouldResurface` alone would render the CTA while
  // `usePushCapability`'s VAPID-key lookup — a real network round-trip — is
  // still in flight, and a user who tapped inside that window would get the
  // permanent-looking ERROR_COPY even though push is about to be available.
  // Gate on the capability probe too, mirroring `reminderSlotState`'s
  // `hidden` gate: structural absence until push is known to be usable (the
  // fail-safe contract in the docstring above).
  if (!shouldResurface || !capability.isResolved || !capability.available) return null;

  // The dismiss flag is a per-device localStorage key
  // (useReminderResurface), never a backend write, so the click is not DB-known.
  const handleDismiss = (): void => {
    dismiss();
    trackFeature('action', { target: 'reminder-banner-dismiss' });
  };

  const handleTurnOn = async (): Promise<void> => {
    const { vapidPublicKey } = capability;
    if (vapidPublicKey === null) {
      // Unreachable in practice — the `available` gate above already implies a
      // non-empty key — but keeps TypeScript's narrowing honest below. Same
      // idiom as useTrainReminderSlot's equivalent guard.
      setStatus('error');
      return;
    }
    setStatus('pending');
    // Same backstop as useTrainReminderSlot: `ensureDeviceSubscribed`
    // catches everything internally, but a rejection escaping it would skip
    // every branch below and leave this button disabled forever.
    const result = await ensureDeviceSubscribed(vapidPublicKey).catch(
      (error: unknown): DeviceSubscribeResult => ({ status: 'error', error }),
    );
    trackFeature('action', {
      target: 'reminder-enable',
      source: 'resurface-banner',
      outcome: result.status,
    });
    if (result.status === 'subscribed') {
      markSubscribed();
      return;
    }
    if (result.status === 'dismissed') {
      // Not an error, nothing written — the banner stays standing, same as
      // the score-screen button's own dismissed path.
      setStatus('idle');
      return;
    }
    // 'denied' | 'unsupported' | 'error'
    setStatus('error');
  };

  return (
    <Card
      accentColor="var(--brand-brown)"
      className="w-full p-4"
      data-testid="resurface-banner"
    >
      <div className="flex items-center gap-2">
        <Bell className="size-4 shrink-0" aria-hidden="true" />
        <p className="text-sm font-semibold" data-testid="resurface-banner-headline">
          Turn on reminders
        </p>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        You added FlawChess to your home screen — turn on reminders so you don&apos;t miss a Train
        session.
      </p>
      <div className="mt-3 flex gap-2">
        <Button
          variant="default"
          size="sm"
          data-testid="btn-resurface-turn-on"
          disabled={status === 'pending'}
          onClick={() => void handleTurnOn()}
        >
          {status === 'error' ? ERROR_COPY : 'Turn on reminders'}
        </Button>
        <Button variant="ghost" size="sm" data-testid="btn-resurface-dismiss" onClick={handleDismiss}>
          Not now
        </Button>
      </div>
    </Card>
  );
}
