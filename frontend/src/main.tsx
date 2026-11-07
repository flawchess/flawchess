import "./instrument"; // MUST be first import — Sentry initializes before anything else
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import "./index.css";
import App from "./App.tsx";
import { createSwUpdateChecker, installSwControllerReload, SW_UPDATE_INTERVAL_MS } from "@/lib/swUpdate";
import { reportMaiaPageKillFromPreviousSession } from "@/lib/engine/maiaPageKillSentinel";
import { installStalePreloadReload } from "@/lib/stalePreloadReload";
import { installBuildVersionCheck } from "@/lib/buildVersionCheck";
import { installDomMutationGuard } from "@/lib/domMutationGuard";
import { captureFirstTouch } from "@/lib/firstTouch";
import { identifyFromStoredToken, installUmamiBeforeSend } from "@/lib/analytics";

// A page killed while Maia was running (iOS Safari's silent
// per-page memory-limit termination) leaves a record in localStorage — report
// it now that Sentry is initialised.
reportMaiaPageKillFromPreviousSession();

// FLAWCHESS-C0: reload once when a lazy chunk from the previous deploy is gone.
installStalePreloadReload();

// Compare the compiled-in build ID with /version.json at startup and on every
// resume. Deliberately outside the serviceWorker branch below: when the
// service worker is already current, reg.update() finds nothing, so an old
// bundle could otherwise keep running indefinitely.
installBuildVersionCheck();

// FLAWCHESS-BV: keep Google Translate's DOM edits from crashing React. Must run
// before createRoot below.
installDomMutationGuard();

// Remember where this browser first arrived from (referrer host,
// utm tags, landing path) before the router rewrites the URL.
captureFirstTouch();

// Scrub credentials and the Google OAuth referrer from every Umami payload,
// and drop the duplicate pageview of an automatic post-deploy reload.
// The deferred tracker sends its first pageview only once the document is
// complete, so registering the hook here always precedes it.
installUmamiBeforeSend();
// Identify before the deferred tracker's first pageview (it waits for
// readyState complete) so the landing pageview carries the id on Umami 3.4+,
// where the distinct id is part of the session hash. Memory-only: a reload or
// logout wipes it.
identifyFromStoredToken();

// ── Service Worker update handling ────────────────────────────────────────
// When a new service worker takes over (after deploy), reload the page so the
// browser picks up the new precached assets (see installSwControllerReload).
if ("serviceWorker" in navigator) {
  installSwControllerReload();

  // Check for SW updates on a slow hourly safety net AND opportunistically when
  // the app is resumed. Android freezes backgrounded PWAs, so a resumed app fires
  // no fresh `load` and the interval is unreliable while suspended — that's how an
  // installed PWA kept showing a many-deploys-old layout. visibilitychange/focus
  // are the events that actually fire on resume, so we re-check the SW there too.
  const checkForSwUpdate = createSwUpdateChecker();

  setInterval(checkForSwUpdate, SW_UPDATE_INTERVAL_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") checkForSwUpdate();
  });
  window.addEventListener("focus", checkForSwUpdate);
}

createRoot(document.getElementById("root")!, {
  // React 19 error hooks — report uncaught/caught/recoverable errors to Sentry
  onUncaughtError: Sentry.reactErrorHandler(),
  onCaughtError: Sentry.reactErrorHandler(),
  onRecoverableError: Sentry.reactErrorHandler(),
}).render(
  <StrictMode>
    <App />
  </StrictMode>
);
