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
import { lazy, Suspense, type ReactElement } from 'react';

const QRCodeSVG = lazy(() =>
  import('qrcode.react').then((module) => ({ default: module.QRCodeSVG })),
);

/** No credential, no token — a plain path appended to the
 * current origin at render time. */
export const HANDOFF_QR_PATH = '/train?src=handoff';

/** Names the whole handoff (install + reminders), since on desktop this
 * block is the primary ask, not a post-subscribe upsell. Shared by both
 * mount points. */
export const QR_CAPTION = 'Scan to install FlawChess on your phone and turn on reminders there.';

/** 128x128, matching `qrcode.react`'s own default render size. */
export const QR_SIZE_PX = 128;

export interface TrainInstallQrProps {
  /** The mount-site test id — REQUIRED, never hardcoded inside this
   * component (see module docstring). */
  testId: string;
}

export function TrainInstallQr({ testId }: TrainInstallQrProps): ReactElement {
  const payload = `${window.location.origin}${HANDOFF_QR_PATH}`;

  return (
    <div className="w-full text-center" data-testid={testId}>
      {/*
        A non-token colour surface — fixed (#FFFFFF background / #000000
        modules) precisely because it must NOT follow the app theme. A
        theme-tinted or inverted QR is a scan-reliability risk. Do not
        replace bg-white with a theme.ts token.
      */}
      <div className="inline-block rounded-md bg-white p-2">
        <Suspense fallback={null}>
          <QRCodeSVG value={payload} size={QR_SIZE_PX} />
        </Suspense>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{QR_CAPTION}</p>
    </div>
  );
}
