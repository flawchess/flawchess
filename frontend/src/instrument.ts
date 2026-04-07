import * as Sentry from "@sentry/react";

// Duck-typed interface for Axios errors — avoids importing axios in the Sentry
// instrumentation file which loads before the app bundle is ready.
interface AxiosLikeError {
  isAxiosError: true;
  response?: { status: number };
  code?: string;
}

function isAxiosLikeError(err: unknown): err is AxiosLikeError {
  return (
    typeof err === "object" &&
    err !== null &&
    (err as Record<string, unknown>)["isAxiosError"] === true
  );
}

function sentryBeforeSend(
  event: Sentry.ErrorEvent,
  hint: Sentry.EventHint,
): Sentry.ErrorEvent {
  const error = hint.originalException;
  if (isAxiosLikeError(error)) {
    // 401 Unauthorized is never a bug — it's a normal auth failure (expired session,
    // wrong credentials). Drop it to avoid noise in Sentry.
    if (error.response?.status === 401) {
      return null as unknown as Sentry.ErrorEvent;
    }
    if (error.response?.status === 500) {
      event.fingerprint = ["api-server-error"];
    } else if (error.code === "ECONNABORTED") {
      event.fingerprint = ["api-timeout"];
    } else if (error.code === "ERR_NETWORK") {
      event.fingerprint = ["api-network-error"];
    }
  }
  return event;
}

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE, // "production" or "development" — set by Vite automatically
  integrations: [Sentry.browserTracingIntegration()],
  tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE) || 0,
  beforeSend: sentryBeforeSend,
  // Suppress DOM errors caused by browser extensions (e.g. Google Translate)
  // mutating nodes that React expects to control.
  ignoreErrors: [
    /Failed to execute 'removeChild' on 'Node'/,
    /Failed to execute 'insertBefore' on 'Node'/,
  ],
});
