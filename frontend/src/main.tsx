import "./instrument"; // MUST be first import — Sentry initializes before anything else
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import "./index.css";
import App from "./App.tsx";

// ── Service Worker update handling ────────────────────────────────────────
// When a new service worker activates (after deploy), reload the page so the
// browser picks up the new precached assets. Without this, the PWA can serve
// stale JS indefinitely — causing API route mismatches when endpoints are renamed.
// Bug fix: PWA on mobile kept serving old frontend calling /api/analysis/* after
// backend was deployed with renamed /api/openings/* routes, causing 404 errors.
if ("serviceWorker" in navigator) {
  // Only add reload listener when a SW already controls this page (not first visit)
  if (navigator.serviceWorker.controller) {
    let refreshing = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    });
  }

  // Periodically check for SW updates (every 60 min). In a standalone PWA,
  // the browser's default 24-hour SW check may be too infrequent.
  const SW_UPDATE_INTERVAL_MS = 60 * 60 * 1000;
  setInterval(async () => {
    const reg = await navigator.serviceWorker.getRegistration();
    await reg?.update();
  }, SW_UPDATE_INTERVAL_MS);
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
