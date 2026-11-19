/**
 * TrainScheduleSettings — the inline, auto-saving weekly schedule block on
 * the Train start screen (days and reminders; each mode's session size lives in
 * `TrainModeSettings`). No Save button anywhere: every change goes through the
 * shared settings draft (`useTrainSettingsDraft`, owned by `TrainStartScreen`), which
 * debounces into exactly one `PUT /train/settings`, with an inline
 * "Saved"/"Couldn't save. Try again." indicator.
 *
 * Renders below the Today card and the mode rows, deliberately quiet, `text-sm` labels.
 * It is boxed in the standard `Card`/`CardHeader` ("Train schedule"),
 * always open, and the completed state's
 * "Next session" line lives in here: it describes the schedule, so it
 * belongs with the pickers that determine it rather than floating above
 * them as loose page text.
 *
 * The picker matches the game filter panel's own: "Train on" reuses
 * `ToggleChipButton` (FilterPanel's multi-select "Time control"/"Platform"
 * pattern, in `@/components/ui/toggle-chip-button` so both call sites share
 * one source of truth), with FilterPanel's own `text-sm text-muted-foreground`
 * label treatment (not `font-semibold`) so this block reads as part of the same
 * design language.
 *
 * A second sibling block adds a master "Remind me to train" `Switch` and a
 * 24-hour `Select`. Toggle-OFF and hour changes ride the SAME
 * shared draft as the weekday chips — one `PUT`, one indicator.
 * Toggle-ON is a DELIBERATE, DOCUMENTED EXCEPTION to that pattern: writing
 * `reminderEnabled: true` into the draft synchronously (the way every other
 * control does) risks the debounced `PUT` landing before
 * `Notification.requestPermission()`/`PushManager.subscribe()` resolve,
 * persisting `reminder_enabled = true` server-side with no live subscription
 * — a silent-lie state. So toggle-ON instead calls `ensureDeviceSubscribed()`
 * (the same routine `useTrainReminderSlot` calls: one code path, two entry
 * points) and only writes the draft, and therefore only enters the debounce,
 * on `status === 'subscribed'`. Do not "fix" this into synchronous
 * consistency with the other controls — that reintroduces the exact bug this
 * design avoids.
 *
 * A third sibling block is the QR handoff's PERMANENT home in this card —
 * never gated on `reminderEnabled`/`showReminderBlock`. It is the one thing
 * in this component that does NOT ride any save/debounce path at all (it is a
 * pure client-side transform, no settings field involved). It is three
 * mutually exclusive branches on `isMobile`/`isStandalone`/`canInstall` (all
 * from `useInstallPrompt`): desktop gets the QR, a mobile browser that can
 * actually install gets a primary "Install FlawChess" button instead, and
 * everything else (standalone, or mobile with no live `beforeinstallprompt`,
 * e.g. iOS) renders NOTHING — structural absence rather than a dead button.
 * A phone showing a QR that asks the user to scan their own screen, or an
 * installed PWA offering to install itself again, would be nonsense.
 * `TrainInstallQr` itself only ever mounts on the desktop branch (see that
 * component's own docstring), where the reminder block renders inside it (above
 * the QR on a narrow window, beside it from `sm` up); everywhere else the
 * reminder block stands alone above this section.
 *
 * Both the reminder block and the phone section are hidden from guest
 * accounts. `app.repositories.train_reminder_repository`'s fan-out filters
 * `User.is_guest.is_(False)` — a guest is never sent a reminder no matter
 * what this card shows — so an enabled toggle or a QR code promising
 * reminders would be a silent lie (the UI must never promise something the
 * backend cannot keep). The rule (no reminder slot, QR block or push prompt
 * for a guest) therefore extends to this landing card, not only the score
 * screen. `resolveScheduleCardVisibility` is the single place both `isGuest`
 * terms live.
 */
import { useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { format, parseISO } from 'date-fns';
import { Check, Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { ToggleChipButton } from '@/components/ui/toggle-chip-button';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LoadError } from '@/components/ui/load-error';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { TrainInstallQr } from '@/components/train/TrainInstallQr';
import { useInstallPrompt } from '@/hooks/useInstallPrompt';
import { usePushCapability } from '@/hooks/usePushCapability';
import { ensureDeviceSubscribed, formatReminderHour, REMINDER_HOUR_OPTIONS } from '@/lib/push';
import type { DeviceSubscribeResult } from '@/lib/push';
import {
  enumeratedValue,
  onOff,
  REMINDER_HOUR_VALUES,
  trackFeature,
  type TrainDayToggleTarget,
} from '@/lib/analytics';
import type { SettingsSaveIndicator, TrainSettingsDraftApi } from '@/hooks/useTrainSettingsDraft';

const PHONE_SECTION_HEADING = 'Reminders work better with FlawChess on your phone';

interface WeekdayChip {
  /** Matches `date.weekday()` (Monday=0..Sunday=6) — the IDENTICAL bit
   * convention `next_scheduled_day`/`week_start` use server-side. A
   * Sunday-first chip order here would silently corrupt schedule matching. */
  bit: number;
  label: string;
  testId: string;
  /** Umami toggle target; set explicitly per chip so a reorder cannot mislabel one. */
  toggleTarget: TrainDayToggleTarget;
}

// eslint-disable-next-line react-refresh/only-export-components -- named constant shared with tests, not a component
export const WEEKDAY_CHIPS: readonly WeekdayChip[] = [
  { bit: 0, label: 'Mo', testId: 'filter-weekday-mo', toggleTarget: 'train-day-mon' },
  { bit: 1, label: 'Tu', testId: 'filter-weekday-tu', toggleTarget: 'train-day-tue' },
  { bit: 2, label: 'We', testId: 'filter-weekday-we', toggleTarget: 'train-day-wed' },
  { bit: 3, label: 'Th', testId: 'filter-weekday-th', toggleTarget: 'train-day-thu' },
  { bit: 4, label: 'Fr', testId: 'filter-weekday-fr', toggleTarget: 'train-day-fri' },
  { bit: 5, label: 'Sa', testId: 'filter-weekday-sa', toggleTarget: 'train-day-sat' },
  { bit: 6, label: 'Su', testId: 'filter-weekday-su', toggleTarget: 'train-day-sun' },
];

function isWeekdayBitSet(mask: number, bit: number): boolean {
  return (mask & (1 << bit)) !== 0;
}

export interface TrainScheduleSettingsProps {
  /** The one shared settings draft (`useTrainSettingsDraft`, owned by `TrainStartScreen`). */
  settingsDraft: TrainSettingsDraftApi;
  /**
   * The next scheduled session day (an ISO date), rendered as the card's
   * first line. Only the 'completed' landing state passes it — while a
   * session is still startable, "next session" is today, and stating that
   * as a future date would be actively misleading.
   */
  nextSessionDate?: string;
  /**
   * From `useUserProfile().data` via `TrainStartScreen`,
   * never `useAuth().user` (FLAWCHESS-64). Hides the reminder block and the
   * phone/QR section for a guest: `train_reminder_repository`'s fan-out
   * filters `User.is_guest.is_(False)`, so an enabled toggle would be a
   * promise the backend never keeps.
   */
  isGuest: boolean;
}

/**
 * The card shell, shared by the error and populated bodies so a failed
 * settings fetch still reads as the same "Train schedule" box.
 *
 * The save indicator lives in the header's right slot (the `RightControls`
 * composition the `Card` docstring sanctions), not at the bottom of the card
 * body: down there it would need a permanently reserved `min-h-5` slot plus
 * the wrapper's own `gap-4`, ~36px of dead space under the last picker in the
 * idle state. In the header it costs no vertical space at all and still
 * can't shift the layout when it appears.
 */
interface ScheduleCardShellProps {
  indicator: SettingsSaveIndicator;
  children: ReactNode;
}

function SaveIndicator({ indicator }: { indicator: SettingsSaveIndicator }): ReactElement | null {
  if (indicator === 'saved') {
    return (
      <span
        data-testid="train-settings-saved"
        className="ml-auto flex items-center gap-1 text-sm font-normal text-muted-foreground"
      >
        <Check className="size-4" aria-hidden="true" />
        Saved
      </span>
    );
  }
  if (indicator === 'error') {
    return (
      <span data-testid="train-settings-save-error" className="ml-auto text-sm font-normal text-muted-foreground">
        Couldn&apos;t save. Try again.
      </span>
    );
  }
  if (indicator === 'reminder-error') {
    return (
      <span data-testid="train-reminder-error" className="ml-auto text-sm font-normal text-muted-foreground">
        Couldn&apos;t turn on reminders. Try again.
      </span>
    );
  }
  return null;
}

function ScheduleCardShell({ indicator, children }: ScheduleCardShellProps): ReactElement {
  return (
    <Card as="section" className="w-full" data-testid="train-schedule-settings">
      <CardHeader size="compact">
        Train schedule
        <SaveIndicator indicator={indicator} />
      </CardHeader>
      <CardBody className="flex w-full flex-col gap-4">{children}</CardBody>
    </Card>
  );
}

interface ReminderControlsProps {
  draft: TrainSettingsDraftApi['draft'];
  /** The component's existing `isPending || draft === null` gate. */
  disabled: boolean;
  /** True while `ensureDeviceSubscribed()` is in flight for this toggle. */
  subscribing: boolean;
  /** `deniedNow || capability.permission === 'denied'`. */
  blocked: boolean;
  onToggle: (checked: boolean) => void;
  onHourChange: (hour: number) => void;
}

/**
 * The master reminder toggle + hour picker, extracted like
 * `ScheduleCardShell` above. Purely presentational — all async orchestration
 * (the toggle-ON exception in the module docstring) lives in the parent.
 */
function ReminderControls({
  draft,
  disabled,
  subscribing,
  blocked,
  onToggle,
  onHourChange,
}: ReminderControlsProps): ReactElement {
  const checked = !blocked && draft?.reminderEnabled === true;
  const showHourPicker = checked && draft !== null;

  return (
    <div className="w-full">
      {/* The Switch sits to the LEFT of its label: every other
          switch/checkbox control in the codebase reads control-then-label. */}
      <div className="flex items-center gap-2">
        <Switch
          data-testid="filter-reminder-enabled"
          aria-label="Remind me to train"
          checked={checked}
          disabled={disabled || subscribing || blocked}
          onCheckedChange={onToggle}
        />
        <p className="min-w-0 text-sm text-muted-foreground">
          Remind me to train{showHourPicker && ' at'}
        </p>
        {showHourPicker && (
          <Select
            value={String(draft.reminderHour)}
            disabled={disabled}
            onValueChange={(value: string) => onHourChange(Number(value))}
          >
            <SelectTrigger
              className="w-fit shrink-0"
              aria-label="Reminder time"
              data-testid="filter-reminder-hour"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {REMINDER_HOUR_OPTIONS.map((hour) => (
                <SelectItem key={hour} value={String(hour)} data-testid={`filter-reminder-hour-${hour}`}>
                  {formatReminderHour(hour)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      {blocked && (
        <p className="mt-1 text-sm text-muted-foreground" data-testid="train-reminder-blocked">
          Reminders are blocked in your browser settings.
        </p>
      )}
    </div>
  );
}

/** Resolver inputs — the same signals the component already
 * reads (`usePushCapability`'s resolved/available flags, `useInstallPrompt`'s
 * mobile/standalone/canInstall) plus `isGuest`. */
interface ScheduleCardVisibilityInput {
  isGuest: boolean;
  capabilityResolved: boolean;
  capabilityAvailable: boolean;
  isMobile: boolean;
  isStandalone: boolean;
  canInstall: boolean;
}

interface ScheduleCardVisibility {
  showReminderBlock: boolean;
  showQr: boolean;
  showMobileInstallButton: boolean;
  showPhoneSection: boolean;
}

/**
 * The four visibility booleans this card renders on, kept in one
 * module-level function so the guest gate lives in one place.
 *
 * `showReminderBlock` and `showPhoneSection` are each false whenever
 * `isGuest` is true: a guest is never sent a reminder
 * (`train_reminder_repository`'s fan-out filter), so neither the toggle nor
 * the phone/QR install ask may render for one. `showQr` and
 * `showMobileInstallButton` are unchanged — they only ever matter once
 * `showPhoneSection` has already let the section through.
 */
function resolveScheduleCardVisibility({
  isGuest,
  capabilityResolved,
  capabilityAvailable,
  isMobile,
  isStandalone,
  canInstall,
}: ScheduleCardVisibilityInput): ScheduleCardVisibility {
  // A clean structural absence, not a disabled placeholder, until
  // both feature detection and the VAPID-key query have resolved.
  const showReminderBlock = !isGuest && capabilityResolved && capabilityAvailable;
  // Three mutually exclusive branches, never
  // more than one rendered. `showQr` and `showMobileInstallButton` decide
  // WHICH content fills the "Reminders work better with FlawChess on your
  // phone" section; `showPhoneSection` decides whether the section (heading
  // included) renders at ALL — a standalone launch, or a mobile browser with
  // no live `beforeinstallprompt` (iOS has none), gets nothing rather than an
  // orphaned heading over a dead control.
  const showQr = !isMobile && !isStandalone;
  const showMobileInstallButton = isMobile && !isStandalone && canInstall;
  const showPhoneSection = !isGuest && (showQr || showMobileInstallButton);
  return { showReminderBlock, showQr, showMobileInstallButton, showPhoneSection };
}

export function TrainScheduleSettings({
  settingsDraft,
  nextSessionDate,
  isGuest,
}: TrainScheduleSettingsProps): ReactElement {
  const { draft, update, indicator, setIndicator, isPending, isError } = settingsDraft;
  const capability = usePushCapability();
  const { isMobile, isStandalone, canInstall, triggerInstall } = useInstallPrompt();

  // True while ensureDeviceSubscribed() is in flight for the master toggle.
  const [subscribing, setSubscribing] = useState(false);
  // A denial that happens during THIS mount must take effect immediately,
  // without waiting for a remount to re-read capability.permission.
  const [deniedNow, setDeniedNow] = useState(false);

  // A per-device block never mutates the account-wide reminder_enabled (see
  // the toggle handler below and the module docstring's toggle-ON note).
  const blocked = deniedNow || capability.permission === 'denied';

  // The one deliberate exception to this file's debounced-draft
  // pattern; see the module docstring for why. Toggle-OFF and hour changes
  // ride the debounce unmodified via the two handlers that follow.
  const handleReminderToggle = (checked: boolean): void => {
    // The user's requested state, sent before any gating so switch-offs are kept.
    trackFeature('toggle', { target: 'train-reminder', value: onOff(checked) });
    setIndicator((prev) => (prev === 'reminder-error' ? 'idle' : prev));
    if (!checked) {
      update({ reminderEnabled: false });
      return;
    }
    const { vapidPublicKey } = capability;
    if (vapidPublicKey === null) return;
    setSubscribing(true);
    // Backstop: `ensureDeviceSubscribed` catches everything internally,
    // but a rejection escaping it would skip `setSubscribing(false)` and leave
    // every control in this card disabled forever.
    void ensureDeviceSubscribed(vapidPublicKey)
      .catch((error: unknown): DeviceSubscribeResult => ({ status: 'error', error }))
      .then((result) => {
        setSubscribing(false);
        // Desktop has no score-screen "Remind me" button, so this switch is its only
        // opt-in path; without this event the reminder funnel would be blind to desktop.
        trackFeature('action', {
          target: 'reminder-enable',
          source: 'train-settings',
          outcome: result.status,
        });
        if (result.status === 'subscribed') {
          update({ reminderEnabled: true });
          return;
        }
        if (result.status === 'denied') {
          setDeniedNow(true);
          return;
        }
        if (result.status === 'dismissed') return; // offer stays standing
        setIndicator('reminder-error'); // 'error' or 'unsupported'
      });
  };

  const handleReminderHourChange = (hour: number): void => {
    update({ reminderHour: hour });
    const trackedHour = enumeratedValue(REMINDER_HOUR_VALUES, hour);
    if (trackedHour !== null) trackFeature('option-change', { target: 'train-reminder-hour', value: trackedHour });
  };

  const handleWeekdayToggle = (chip: WeekdayChip): void => {
    const currentlyOn = draft !== null && isWeekdayBitSet(draft.weekdayMask, chip.bit);
    update((prev) => ({ weekdayMask: prev.weekdayMask ^ (1 << chip.bit) }));
    trackFeature('toggle', { target: chip.toggleTarget, value: onOff(!currentlyOn) });
  };

  if (isError) {
    return (
      <ScheduleCardShell indicator="idle">
        <LoadError resource="your training schedule" />
      </ScheduleCardShell>
    );
  }

  const disabled = isPending || draft === null;

  const { showReminderBlock, showQr, showMobileInstallButton, showPhoneSection } =
    resolveScheduleCardVisibility({
      isGuest,
      capabilityResolved: capability.isResolved,
      capabilityAvailable: capability.available,
      isMobile,
      isStandalone,
      canInstall,
    });

  const nextSessionLine =
    nextSessionDate !== undefined ? (
      <p className="text-sm" data-testid="train-next-session">
        Next session: {format(parseISO(nextSessionDate), 'MMM d, yyyy')}
      </p>
    ) : undefined;

  const reminderControls = showReminderBlock ? (
    <ReminderControls
      draft={draft}
      disabled={disabled}
      subscribing={subscribing}
      blocked={blocked}
      onToggle={handleReminderToggle}
      onHourChange={handleReminderHourChange}
    />
  ) : null;
  // With a QR on screen the reminder row lives inside its block, so
  // TrainInstallQr can place it responsively around the QR and caption.
  const reminderBesideQr = showPhoneSection && showQr;

  return (
    <ScheduleCardShell indicator={indicator}>
      {nextSessionLine}
      <div className="flex w-full flex-col gap-4">
        {/*
          Matches the game filter panel exactly: "Train on" mirrors FilterPanel's
          multi-select "Time control" — the hand-rolled ToggleChipButton grid, not the
          Radix ToggleGroup — with FilterPanel's own `text-sm text-muted-foreground`
          label (not font-semibold) at the top-left of a full-width block.
        */}
        <div className="w-full">
          <p className="mb-1 text-sm text-muted-foreground">Train on</p>
          <div className="grid grid-cols-7 gap-1">
            {WEEKDAY_CHIPS.map((chip) => (
              <ToggleChipButton
                key={chip.bit}
                onClick={() => handleWeekdayToggle(chip)}
                testId={chip.testId}
                ariaLabel={`Train on ${chip.label}`}
                active={draft !== null && isWeekdayBitSet(draft.weekdayMask, chip.bit)}
                disabled={disabled}
              >
                {chip.label}
              </ToggleChipButton>
            ))}
          </div>
        </div>
        {!reminderBesideQr && reminderControls}
        {/* This section's permanent home in the card — never gated on the
            reminder toggle state or push capability, but gated on device
            platform: see the three-branch comment above `showQr`/
            `showMobileInstallButton`/`showPhoneSection`. */}
        {reminderBesideQr && (
          <TrainInstallQr testId="qr-handoff-settings">{reminderControls}</TrainInstallQr>
        )}
        {showPhoneSection && showMobileInstallButton && (
          <div className="flex w-full flex-col gap-2">
            <p className="text-sm font-semibold">{PHONE_SECTION_HEADING}</p>
            <Button
              variant="default"
              className={`${TRAIN_BUTTON_CLASS} w-full`}
              data-testid="btn-install-mobile-settings"
              onClick={() => void triggerInstall()}
            >
              <Smartphone className="size-4" aria-hidden="true" />
              Install FlawChess App
            </Button>
          </div>
        )}
      </div>
    </ScheduleCardShell>
  );
}
