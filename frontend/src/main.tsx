import "./instrument"; // MUST be first import — Sentry initializes before anything else
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import "./index.css";
import App from "./App.tsx";

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
