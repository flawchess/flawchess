/**
 * TrainReminderButton — the score-screen reminder opt-in slot's state
 * machine, consumed by `TrainScoreScreen` via `useTrainReminderSlot` below
 * (this file's only export that renders anything — there is no component
 * export here to mount directly, see the hook's own docstring for why).
 * Phase 202 (D-01..D-05/D-13) built the single confirmed/unsubscribed
 * shape; Phase 203 Plan 03 (OFFER-01..04) replaced the old eight-condition
 * early-return null cascade with a single pure `lib/reminderSlotState`
 * resolver, one ordered pass naming five explicit platform states, and
 * turns the confirmed state into the phase's real upsell surface: an
 * install offer on Android tabbed, a QR handoff to a phone on desktop, and
 * deliberately nothing on standalone (OFFER-04). Visibility is still
 * derived from LIVE state only — never `localStorage` or decline history
 * (Phase 202 D-01, extended here). See `lib/push.ts` for the single call
 * site of `Notification.requestPermission()`.
 *
 * D-05 (intended asymmetry, unchanged): a user with reminders enabled on
 * another device still sees this slot until THIS device subscribes —
 * visibility never falls back to `reminder_enabled` from the server.
 *
 * `ReminderButtonState` (this file's local `state`) and
 * `ReminderSlotState` (the resolver's output) are two different axes that
 * compose, not duplicate each other: the slot state picks WHICH content
 * renders (platform capability), the interaction state picks a label and
 * disabled attribute (transient interaction) — and, for the confirmed
 * branch specifically, `state === 'confirmed'` (set synchronously by
 * `handleClick` below, before any re-fetch of `getDeviceSubscription()`)
 * and the resolver's live `subscribed` state (a pre-existing subscription
 * found at mount) are two different roads to the same rendered branch.
 *
 * The iOS-tabbed branch below was NAMED by the resolver in Plan 03 but
 * rendered `null` until Phase 203 Plan 04 (OFFER-03/D-14/D-15) filled it in:
 * a control in the same shape as the others, whose tap writes
 * `reminder_intent_at` synchronously — before any UI transition, since the
 * user is about to background the tab to open the Share sheet. See the
 * branch itself for why it never reaches for the subscribe/permission
 * helpers `lib/push.ts` owns.
 *
 * Plan 04 UAT rounds 1-3 (post-checkpoint fixes, each a recorded DEVIATION
 * from D-13/D-15/D-03/UI-SPEC-E2 on direct user instruction — see the
 * plan's SUMMARY.md): `TrainScoreScreen` places this slot's content in a
 * `flex-1` cell beside "Done" in a narrow `max-w-sm` row. Three rounds of
 * feedback converged on ONE invariant, stated plainly rather than as a list
 * of exceptions:
 *
 *   THE ROW ONLY EVER HOLDS A PRESSABLE REMINDER CONTROL. Every
 *   non-interactive or overflow element renders below it.
 *
 * Concretely: `control` is the "Remind me" / "Get reminders" button while
 * there is something to press, and `null` once subscribed (nothing left to
 * press) or hidden. `belowRow` carries everything else — the confirmed
 * "Reminders on…" line, the error copy, the iOS Add-to-Home-Screen
 * instructions, the Android install offer, the desktop QR block — as
 * full-width content under the row, never crammed into that one flex cell.
 * `useTrainReminderSlot` returns both pieces from ONE hook call so
 * `TrainScoreScreen` can lay them out in a `flex-col` wrapper with exactly
 * one state instance backing both rows.
 *
 * Phase 222 UAT round 5 (desktop install-first): desktop web push only fires
 * while the browser is running, so on desktop (not mobile, not standalone)
 * there is NO "Remind me" button on the score screen at all — desktop push
 * stays reachable from Train settings only. The row holds just "Done" and
 * `belowRow` is decided by the ACCOUNT-level `has_mobile_subscription` fact
 * from the settings response (a per-device probe cannot know about the
 * phone): reminders on a phone → a "Reminders on … on your phone" line;
 * otherwise → the phone QR handoff, in every desktop state including
 * `hidden` (push unsupported or unconfigured, e.g. desktop Safari). A
 * desktop device that already subscribed before this round keeps its
 * confirmed line. Android and iOS are unchanged: Android tabbed push works
 * without an install, and iOS is already install-first.
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
 * `useTrainReminderSlot` below does NOT do this (Plan 04 UAT round 1
 * deviation from D-13): the button keeps its "Remind me" label and this
 * string renders on its own line below the row instead, because
 * `TrainScoreScreen`'s `max-w-sm` two-cell row has no room for a full
 * sentence without colliding with "Done".
 */
export const ERROR_COPY = "Couldn't turn on reminders. Try again.";

export interface TrainReminderSlotResult {
  /** The row-cell control — a pressable button that belongs beside "Done"
   * in `TrainScoreScreen`'s two-cell row. `null` whenever there is nothing
   * to press: the slot is `hidden`, OR the device is already subscribed
   * (Plan 04 UAT round 3 — the confirmed line is non-interactive, so it
   * moved to `belowRow`; a `null` control here means the row's only child
   * is "Done", which correctly spans the full row width on its own). */
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
  // effect below never re-runs, matching D-05's "derived live, never cached"
  // rule for the render but avoiding a poll loop.
  const [deviceSubscribed, setDeviceSubscribed] = useState<boolean | null>(null);
  const [state, setState] = useState<ReminderButtonState>('idle');
  // A fresh denial must hide the control immediately, without waiting for
  // another mount to re-read `capability.permission`.
  const [deniedNow, setDeniedNow] = useState(false);
  // The brief disabled window between the iOS tap and the settings write
  // settling — no spinner, no skeleton, the same disabled-button treatment
  // the other four states already use. Reset once the write settles (UAT
  // round 1): the button now stays on screen afterward, so leaving it
  // disabled forever would be a dead control with no explanation.
  const [iosPending, setIosPending] = useState(false);
  // Once true, the below-row instructions render permanently for this
  // mount — the write's outcome never flips it back (D-15: the reveal is
  // unconditional). UAT round 1: the button itself is no longer replaced
  // when this flips; it just gains a sibling line below the row.
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
      if (data === undefined) {
        // OFFER-03 empty edge: the settings GET hasn't resolved, so there is
        // nothing to echo and nothing to write. Reveal immediately rather
        // than block the instructions on a fetch that may not finish before
        // the user backgrounds the tab.
        setIosRevealed(true);
        return;
      }
      setIosPending(true);
      // D-15: a direct, IMMEDIATE save fired on the tap — never folded into
      // TrainScheduleSettings's 600ms debounced draft path. The user is
      // about to background the tab to open the Share sheet; a debounced
      // write would be lost, which is exactly the failure D-15 exists to
      // prevent (mirrors the toggle-ON precedent in TrainScheduleSettings).
      save(
        {
          weekdayMask: data.weekday_mask,
          puzzlesPerSession: data.puzzles_per_session,
          reminderEnabled: data.reminder_enabled,
          reminderHour: data.reminder_hour,
          reminderIntentAt: new Date().toISOString(),
        },
        {
          // Fires on BOTH success and failure (D-15, UI-SPEC row 33): the
          // write's outcome must never gate the reveal. A lost intent write
          // costs at most one ignorable prompt later; withholding the
          // instructions on a write failure would defeat the whole point of
          // the tap. Also re-enables the button (UAT round 1) — re-tapping
          // just writes a fresh `reminder_intent_at`, which is harmless.
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

  // UAT round 5: desktop never renders "Remind me" here (see module
  // docstring). The phone block does not depend on push at all, so a desktop
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
    // CR-01 backstop: `ensureDeviceSubscribed` catches everything internally,
    // but a rejection escaping it would skip every setState below and leave
    // this button disabled forever with no retry. Never let that happen.
    const result = await ensureDeviceSubscribed(vapidPublicKey).catch(
      (error: unknown): DeviceSubscribeResult => ({ status: 'error', error }),
    );
    if (result.status === 'subscribed') {
      // The 201 scheduler gates fan-out on reminder_enabled and the account
      // default is false — without this write the D-03 confirmation would
      // claim something untrue.
      save(
        {
          weekdayMask: data.weekday_mask,
          puzzlesPerSession: data.puzzles_per_session,
          reminderEnabled: true,
          reminderHour: data.reminder_hour,
          // Echo the current server value (Phase 203, D-02) — this call
          // never writes a new intent, only the iOS install-affordance tap
          // (Plan 04) does.
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
      // Not an error, nothing written — the offer stays standing (PERM-02).
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
  /** Not mobile at all, not standalone (UAT round 5: gets the phone block
   * in every state, never "Remind me"). */
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
 * neither the QR nor the install offer (OFFER-04 — deliberate, not an
 * oversight). */
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

/** Plan 04 UAT round 3: the confirmed line is non-interactive (nothing left
 * to press), so per the "row only ever holds a pressable control" invariant
 * it lives below the row — `control` is `null`, leaving "Done" as the row's
 * sole (full-width) child. Reading order: confirmation line first, then its
 * platform upsell. */
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
