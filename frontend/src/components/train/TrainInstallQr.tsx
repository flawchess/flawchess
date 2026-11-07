/**
 * TrainInstallQr — the desktop→phone QR handoff block, shared by the score
 * screen's desktop phone block (`testId="qr-handoff-score"`, mounted through
 * `useTrainReminderSlot`) and `TrainScheduleSettings`' phone section
 * (`testId="qr-handoff-settings"`).
 *
 * The mount-site `testId` is a REQUIRED PROP, never hardcoded inside this
 * component — that is what keeps the two mount points independently
 * queryable instead of colliding on one selector.
 *
 * The payload (`HANDOFF_QR_PATH`) is a plain URL with no token, session id,
 * user id or email of any kind. A signed one-time credential is deliberately
 * not used, because a scannable credential rendered on a monitor is account
 * takeover by screen-share, shoulder-surf, or photograph.
 *
 * `qrcode.react`'s `QRCodeSVG` is lazy-loaded via `React.lazy` + `Suspense`
 * (fallback `null` — the structural-absence rule forbids a skeleton) so its
 * bundle stays off the mobile critical path. The chunk is fetched on demand,
 * never eagerly.
 *
 * Mounted on desktop only (`!isMobile && !isStandalone`) at both call sites:
 * a phone rendering a QR that asks the user to scan their own screen with
 * the same phone is nonsense. The mobile equivalent is a live "Install
 * FlawChess" button (or nothing without a live `beforeinstallprompt`), never
 * this component.
 *
 * No dismiss control anywhere: do not add one.
 */
import { lazy, Suspense, type ReactElement, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

const QRCodeSVG = lazy(() =>
  import('qrcode.react').then((module) => ({ default: module.QRCodeSVG })),
);

/** No credential, no token — a plain path appended to the
 * current origin at render time. */
export const HANDOFF_QR_PATH = '/train?src=handoff';

/** Names the whole handoff (install + reminders), since on desktop this
 * block is the primary ask, not a post-subscribe upsell. Shared by both
 * mount points. */
export const QR_CAPTION = 'Scan to install FlawChess on your phone, where reminders work better.';

/** Small enough to sit beside its text as a row rather than dominate the card,
 * while the 39-byte production URL (29x29 modules) keeps over 3px per module. */
export const QR_SIZE_PX = 96;

export interface TrainInstallQrProps {
  /** The mount-site test id — REQUIRED, never hardcoded inside this
   * component (see module docstring). */
  testId: string;
  /** Optional line above the caption, in the text column beside the QR. */
  /** Optional content (the reminder row): above the QR and caption on a narrow
   * viewport, above the caption and beside the QR from `sm` up. */
  children?: ReactNode;
}

export function TrainInstallQr({ testId, children }: TrainInstallQrProps): ReactElement {
  const payload = `${window.location.origin}${HANDOFF_QR_PATH}`;
  const hasChildren = Boolean(children);

  return (
    <div
      className="grid w-full grid-cols-[auto_minmax(0,1fr)] items-center gap-x-4 gap-y-3 text-left"
      data-testid={testId}
    >
      {hasChildren && (
        <div className="col-span-2 sm:col-span-1 sm:col-start-2 sm:self-end">{children}</div>
      )}
      {/*
        A non-token colour surface — fixed (#FFFFFF background / #000000
        modules) precisely because it must NOT follow the app theme. A
        theme-tinted or inverted QR is a scan-reliability risk. Do not
        replace bg-white with a theme.ts token.
      */}
      <div
        className={cn(
          'rounded-md bg-white p-2',
          hasChildren && 'sm:col-start-1 sm:row-span-2 sm:row-start-1',
        )}
      >
        <Suspense fallback={null}>
          <QRCodeSVG value={payload} size={QR_SIZE_PX} />
        </Suspense>
      </div>
      <p className={cn('text-sm text-muted-foreground', hasChildren && 'sm:col-start-2 sm:self-start')}>
        {QR_CAPTION}
      </p>
    </div>
  );
}
