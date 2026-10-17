/**
 * useTrainReminderSlot — the score-screen reminder opt-in slot's state
 * machine, consumed by `TrainScoreScreen` via `useTrainReminderSlot` below
 * (this file's only export that renders anything — there is no component
 * export here to mount directly, see the hook's own docstring for why).
 * See `lib/push.ts` for the single call site of
 * `Notification.requestPermission()`.
 *
 * Invariants:
 *
 * 1. `lib/reminderSlotState`'s `resolveReminderSlotState` picks the platform
 *    branch from LIVE device state only, never `localStorage`, decline
 *    history, or the server's `reminder_enabled`. A user with reminders
 *    enabled on another device still sees this slot until THIS device
 *    subscribes. Standalone gets neither the QR nor the install offer.
 *
 * 2. The slot state (`ReminderSlotState`, the resolver's output) and the
 *    interaction state (`ReminderButtonState`, this file's local `state`) are
 *    two axes that compose, not duplicates: the slot state picks WHICH
 *    content renders (platform capability), the interaction state picks a
 *    label and disabled attribute (transient interaction). For the confirmed
 *    branch, `state === 'confirmed'` (set by `handleClick` once the save
 *    succeeds) and the resolver's live `subscribed` state (a pre-existing
 *    subscription found at mount) are two roads to the same rendered branch.
 *
 * 3. THE ROW BESIDE "DONE" ONLY EVER HOLDS A PRESSABLE REMINDER CONTROL.
 *    `TrainScoreScreen` places `control` in a `flex-1` cell beside "Done" in
 *    a narrow `max-w-sm` row, so every non-interactive or overflow element
 *    renders below it. `control` is the "Remind me" / "Get reminders" button
 *    while there is something to press, and `null` once subscribed or hidden.
 *    `belowRow` carries everything else (the confirmed "Reminders on…" line,
 *    the error copy, the iOS Add-to-Home-Screen instructions, the Android
 *    install offer, the desktop QR block) as full-width content under the
 *    row. `useTrainReminderSlot` returns both pieces from ONE hook call so
 *    `TrainScoreScreen` lays them out with exactly one state instance
 *    backing both.
 *
 * 4. The iOS-tabbed tap writes `reminder_intent_at` synchronously, before any
 *    UI transition, since the user is about to background the tab to open the
 *    Share sheet. It never reaches for the subscribe/permission helpers
 *    `lib/push.ts` owns (iOS has no `PushManager` in a tab).
 *
 * 5. Desktop (not mobile, not standalone) gets no "Remind me" button on the
 *    score screen, because desktop web push only fires while the browser is
 *    running; desktop push stays reachable from Train settings. The row holds
 *    just "Done", and `belowRow` follows the ACCOUNT-level
 *    `has_mobile_subscription` fact from the settings response (a per-device
 *    probe cannot know about the phone): reminders on a phone → a "Reminders
 *    on … on your phone" line; otherwise → the phone QR handoff, in every
 *    desktop state including `hidden` (push unsupported or unconfigured,
 *    e.g. desktop Safari). A desktop device that already subscribed keeps
 *    its confirmed line. Android tabbed push works without an install, and
 *    iOS is install-first.
 */
import { useEffect, useState, type ReactElement } from 'react';
import { Bell, Check, Share, Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { TrainInstallQr } from '@/components/train/TrainInstallQr';
import { usePushCapability } from '@/hooks/usePushCapability';
import { useTrainSettings } from '@/hooks/useTrainSettings';
import { useInstallPrompt } from '@/hooks/useInstallPrompt';
import { trackFeature } from '@/lib/analytics';
import { resolveReminderSlotState } from '@/lib/reminderSlotState';
import { ensureDeviceSubscribed, formatReminderHour, getDeviceSubscription } from '@/lib/push';
import type { DeviceSubscribeResult } from '@/lib/push';
import type { TrainSettingsResponse } from '@/types/train';

type ReminderButtonState = 'idle' | 'pending' | 'confirmed' | 'error';

/**
 * The shared "couldn't subscribe" error copy.
 *
 * `TrainReminderResurfaceBanner` replaces its own CTA's label with this
 * string in place — that banner is a full-width `Card`, not a cramped
 * `flex-1` row cell, so in-place replacement has no layout cost there.
 *
 * `useTrainReminderSlot` below does NOT do this: the button keeps its
 * "Remind me" label and this string renders on its own line below the row
 * instead, because `TrainScoreScreen`'s `max-w-sm` two-cell row has no room
 * for a full sentence without colliding with "Done".
 */
export const ERROR_COPY = "Couldn't turn on reminders. Try again.";

export interface TrainReminderSlotResult {
  /** The row-cell control — a pressable button that belongs beside "Done"
   * in `TrainScoreScreen`'s two-cell row. `null` whenever there is nothing
   * to press: the slot is `hidden`, OR the device is already subscribed
   * (the confirmed line is non-interactive, so it lives in `belowRow`; a
   * `null` control here means the row's only child is "Done", which
   * correctly spans the full row width on its own). */
  control: ReactElement | null;
  /** Full-width content that belongs on its own line BELOW the row: the
   * confirmed "Reminders on…" line (plus its platform upsell), the error
   * copy, the iOS Add-to-Home-Screen instructions, the Android install
   * offer, or the desktop QR block. `null` when there is nothing to show
   * below the row. */
  belowRow: ReactElement | null;
}

/**
 * The whole reminder-slot state machine, called ONCE by `TrainScoreScreen`
 * so the row control and the below-row overflow content share exactly one
 * state instance instead of two independent copies. See the module
 * docstring for the "row only ever holds a pressable control" invariant
 * this hook's return shape encodes.
 */
export function useTrainReminderSlot(): TrainReminderSlotResult {
  const capability = usePushCapability();
  const { data, save } = useTrainSettings();
  const { isIOS, isStandalone, isMobile, canInstall, triggerInstall } = useInstallPrompt();

  // null = probe not yet resolved. Resolved once, on mount — the mount
  // effect below never re-runs, so visibility is derived live from the device
  // (never cached) without a poll loop.
  const [deviceSubscribed, setDeviceSubscribed] = useState<boolean | null>(null);
  const [state, setState] = useState<ReminderButtonState>('idle');
  // A fresh denial must hide the control immediately, without waiting for
  // another mount to re-read `capability.permission`.
  const [deniedNow, setDeniedNow] = useState(false);
  // The brief disabled window between the iOS tap and the settings write
  // settling — no spinner, no skeleton, the same disabled-button treatment
  // the other four states already use. Reset once the write settles: the
  // button stays on screen afterward, so leaving it disabled forever would
  // be a dead control with no explanation.
  const [iosPending, setIosPending] = useState(false);
  // Once true, the below-row instructions render permanently for this
  // mount — the write's outcome never flips it back (the reveal is
  // unconditional). The button itself is not replaced when this flips; it
  // just gains a sibling line below the row.
  const [iosRevealed, setIosRevealed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void getDeviceSubscription().then((subscription) => {
      if (!cancelled) setDeviceSubscribed(subscription !== null);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const slotState = resolveReminderSlotState({
    isResolved: capability.isResolved,
    available: capability.available,
    permission: capability.permission,
    deniedNow,
    subscribed: deviceSubscribed,
    settingsLoaded: data !== undefined,
    vapidPublicKey: capability.vapidPublicKey,
    isIOS,
    isStandalone,
    isMobile,
  });

  const isConfirmed = state === 'confirmed' || slotState === 'subscribed';
  const platform = resolvePlatformFlags({ isMobile, isIOS, isStandalone, canInstall, data });

  if (isConfirmed && data !== undefined) {
    return {
      control: null,
      belowRow: confirmedBelowRow({ reminderHour: data.reminder_hour, platform, triggerInstall }),
    };
  }

  if (slotState === 'ios-tabbed') {
    const handleIosTap = (): void => {
      // The iOS tap never prompts: the install instructions reveal either way,
      // so that is the outcome. Counted before the early return so both paths do.
      trackFeature('action', {
        target: 'reminder-enable',
        source: 'score-screen',
        outcome: 'install-instructions',
      });
      if (data === undefined) {
        // Empty edge: the settings GET hasn't resolved, so there is
        // nothing to echo and nothing to write. Reveal immediately rather
        // than block the instructions on a fetch that may not finish before
        // the user backgrounds the tab.
        setIosRevealed(true);
        return;
      }
      setIosPending(true);
      // A direct, IMMEDIATE save fired on the tap — never folded into
      // TrainScheduleSettings's 600ms debounced draft path. The user is
      // about to background the tab to open the Share sheet; a debounced
      // write would be lost (mirrors the toggle-ON precedent in
      // TrainScheduleSettings).
      save(
        {
          weekdayMask: data.weekday_mask,
          puzzlesPerSession: data.puzzles_per_session,
          reminderEnabled: data.reminder_enabled,
          reminderHour: data.reminder_hour,
          reminderIntentAt: new Date().toISOString(),
        },
        {
          // Fires on BOTH success and failure: the write's outcome must
          // never gate the reveal. A lost intent write costs at most one
          // ignorable prompt later; withholding the instructions on a write
          // failure would defeat the whole point of the tap. Also re-enables
          // the button — re-tapping just writes a fresh
          // `reminder_intent_at`, which is harmless.
          onSettled: () => {
            setIosPending(false);
            setIosRevealed(true);
          },
        },
      );
    };

    const control = (
      <Button
        variant="brand-outline"
        className={cn('flex-1 min-w-0', TRAIN_BUTTON_CLASS)}
        data-testid="btn-train-ios-reminders"
        disabled={iosPending}
        onClick={handleIosTap}
      >
        <Bell className="size-4" aria-hidden="true" />
        Get reminders
      </Button>
    );

    const belowRow = iosRevealed ? (
      <p
        data-testid="train-ios-reminder-instructions"
        className="flex w-full items-start gap-2 text-sm text-muted-foreground"
      >
        <Share className="size-4 shrink-0 mt-0.5" aria-hidden="true" />
        <span>
          Install: tap <strong>Share</strong> then <strong>Add to Home Screen</strong>, then open it
          and turn on reminders.
        </span>
      </p>
    ) : null;

    return { control, belowRow };
  }

  // Desktop never renders "Remind me" here (see module
  // docstring invariant 5). The phone block does not depend on push at all, so a desktop
  // with no usable push (denied, unsupported, VAPID unconfigured) still gets
  // it — the only reminder path such a browser has.
  if (platform.isDesktop) {
    return { control: null, belowRow: desktopPhoneBlock({ platform, data }) };
  }

  if (slotState === 'hidden') {
    return { control: null, belowRow: null };
  }

  const { vapidPublicKey } = capability;
  if (data === undefined || vapidPublicKey === null) {
    // Unreachable in practice — the resolver's hidden gate already covers
    // both cases above — but keeps TypeScript's narrowing honest below.
    return { control: null, belowRow: null };
  }

  const handleClick = async (): Promise<void> => {
    // The double-press guard: disabled for the whole promise lifetime below.
    setState('pending');
    // Backstop: `ensureDeviceSubscribed` catches everything internally,
    // but a rejection escaping it would skip every setState below and leave
    // this button disabled forever with no retry. Never let that happen.
    const result = await ensureDeviceSubscribed(vapidPublicKey).catch(
      (error: unknown): DeviceSubscribeResult => ({ status: 'error', error }),
    );
    // The later save() success or failure is not part of the outcome (save errors
    // already reach Sentry through the global MutationCache handler).
    trackFeature('action', {
      target: 'reminder-enable',
      source: 'score-screen',
      outcome: result.status,
    });
    if (result.status === 'subscribed') {
      // The scheduler gates fan-out on reminder_enabled and the account
      // default is false — without this write the confirmation would claim
      // something untrue.
      save(
        {
          weekdayMask: data.weekday_mask,
          puzzlesPerSession: data.puzzles_per_session,
          reminderEnabled: true,
          reminderHour: data.reminder_hour,
          // Echo the current server value — this call never writes a new
          // intent, only the iOS install-affordance tap does.
          reminderIntentAt: data.reminder_intent_at,
        },
        {
          onSuccess: () => setState('confirmed'),
          onError: () => setState('error'),
        },
      );
      return;
    }
    if (result.status === 'denied') {
      setDeniedNow(true);
      setState('idle');
      return;
    }
    if (result.status === 'dismissed') {
      // Not an error, nothing written — the offer stays standing.
      setState('idle');
      return;
    }
    // 'unsupported' or 'error'
    setState('error');
  };

  const control = (
    <Button
      variant="brand-outline"
      className={cn('flex-1 min-w-0', TRAIN_BUTTON_CLASS)}
      data-testid="btn-train-remind-me"
      disabled={state === 'pending'}
      onClick={() => void handleClick()}
    >
      <Bell className="size-4" aria-hidden="true" />
      Remind me
    </Button>
  );

  const belowRow =
    state === 'error' ? (
      <p className="w-full text-sm text-muted-foreground" data-testid="train-reminder-error-line">
        {ERROR_COPY}
      </p>
    ) : null;

  return { control, belowRow };
}

interface PlatformFlags {
  /** Not mobile at all, not standalone (gets the phone block in every
   * state, never "Remind me"). */
  isDesktop: boolean;
  /** Android tabbed (mobile, not iOS, not standalone) with a live captured
   * `beforeinstallprompt` — the only platform that gets the install offer. */
  showAndroidOffer: boolean;
  /** Desktop and the account has no phone reminders yet — the QR handoff
   * only makes sense until it does. */
  showDesktopQr: boolean;
  /** Account-level fact from the settings response (server-side User-Agent
   * check), unknown-as-false until settings resolve. */
  hasMobileSubscription: boolean;
}

/** The platform-only inputs, resolved once per render. Standalone gets
 * neither the QR nor the install offer, deliberately. */
function resolvePlatformFlags({
  isMobile,
  isIOS,
  isStandalone,
  canInstall,
  data,
}: {
  isMobile: boolean;
  isIOS: boolean;
  isStandalone: boolean;
  canInstall: boolean;
  data: TrainSettingsResponse | undefined;
}): PlatformFlags {
  const isDesktop = !isMobile && !isStandalone;
  const hasMobileSubscription = data?.has_mobile_subscription ?? false;
  return {
    isDesktop,
    showAndroidOffer: isMobile && !isIOS && !isStandalone && canInstall,
    showDesktopQr: isDesktop && !hasMobileSubscription,
    hasMobileSubscription,
  };
}

/** The confirmed line is non-interactive (nothing left to press), so per the
 * "row only ever holds a pressable control" invariant it lives below the
 * row — `control` is `null`, leaving "Done" as the row's sole (full-width)
 * child. Reading order: confirmation line first, then its platform upsell. */
function confirmedBelowRow({
  reminderHour,
  platform,
  triggerInstall,
}: {
  reminderHour: number;
  platform: PlatformFlags;
  triggerInstall: () => Promise<void>;
}): ReactElement {
  return (
    <div className="flex w-full flex-col items-center gap-2">
      <span
        data-testid="train-reminder-confirmed"
        className="flex items-center justify-center gap-1 text-sm text-muted-foreground"
      >
        <Check className="size-4" aria-hidden="true" />
        Reminders on — {formatReminderHour(reminderHour)} on your training days
      </span>
      {confirmedUpsell({
        showAndroidOffer: platform.showAndroidOffer,
        showDesktopQr: platform.showDesktopQr,
        triggerInstall,
      })}
    </div>
  );
}

/** Desktop below-row content while this device has no subscription of its
 * own: the account already has reminders on a phone → say so (the bubble's
 * "yours are already on" line points here); otherwise → the QR handoff, the
 * primary desktop ask (the bubble's "scan the code below" points here). */
function desktopPhoneBlock({
  platform,
  data,
}: {
  platform: PlatformFlags;
  data: TrainSettingsResponse | undefined;
}): ReactElement {
  if (!platform.hasMobileSubscription) return <TrainInstallQr testId="qr-handoff-score" />;
  const hour = data === undefined ? '' : ` — ${formatReminderHour(data.reminder_hour)}`;
  return (
    <span
      data-testid="train-reminder-phone-confirmed"
      className="flex w-full items-center justify-center gap-1 text-sm text-muted-foreground"
    >
      <Check className="size-4" aria-hidden="true" />
      Reminders on{hour} on your phone
    </span>
  );
}

/** The confirmed state's platform upsell: the Android install offer, the
 * desktop QR, or nothing (standalone / Android with no live event). */
function confirmedUpsell({
  showAndroidOffer,
  showDesktopQr,
  triggerInstall,
}: {
  showAndroidOffer: boolean;
  showDesktopQr: boolean;
  triggerInstall: () => Promise<void>;
}): ReactElement | null {
  if (showAndroidOffer) {
    return (
      <Button
        variant="ghost"
        size="sm"
        data-testid="btn-install-android-offer"
        onClick={() => void triggerInstall()}
      >
        <Smartphone className="size-4" aria-hidden="true" />
        Install FlawChess
      </Button>
    );
  }
  if (showDesktopQr) return <TrainInstallQr testId="qr-handoff-score" />;
  return null;
}
