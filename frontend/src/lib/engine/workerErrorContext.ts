/**
 * workerErrorContext — Sentry context for a Worker `error` event.
 *
 * A Worker's `onerror` fires both when its script fails to load (404, CSP,
 * network) and when code inside the worker throws uncaught (e.g. a wasm
 * `RangeError: Out of memory`). The four engine-worker handlers used to report
 * a fixed "worker load failure" message and drop the event, so a cluster like
 * FLAWCHESS-C2/C3/C4/9H (every engine worker dying at once on iOS) could not
 * be told apart from a missing asset. The message stays fixed for grouping;
 * the event details go into `contexts.worker_error`.
 */

// `ErrorEvent` is missing in non-DOM environments (node-env unit tests), so
// guard the global rather than using a bare `instanceof`.
function isErrorEvent(event: Event): event is ErrorEvent {
  return typeof ErrorEvent !== 'undefined' && event instanceof ErrorEvent;
}

export function workerErrorContext(event: Event): Record<string, string | number | boolean> {
  const context: Record<string, string | number | boolean> = {
    eventType: event.type,
    isErrorEvent: isErrorEvent(event),
  };
  if (isErrorEvent(event)) {
    // A load failure usually arrives with an empty message and no location;
    // an uncaught in-worker error carries all of these.
    if (event.message) context.message = event.message;
    if (event.filename) context.filename = event.filename;
    if (event.lineno) context.lineno = event.lineno;
    if (event.colno) context.colno = event.colno;
    if (event.error instanceof Error) context.errorName = event.error.name;
  }
  // Discriminate "tab resumed from background" and "device offline" from a
  // genuine asset or in-worker failure.
  try {
    if (typeof document !== 'undefined') context.visibilityState = document.visibilityState;
    if (typeof navigator !== 'undefined') context.online = navigator.onLine;
  } catch {
    // best-effort only
  }
  return context;
}
