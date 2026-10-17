/**
 * deviceClass.ts — the project's UA-based mobile definition, shared by the
 * install prompt (useInstallPrompt) and the Train telemetry.
 */

import type { TelemetryClient } from '@/types/train';

/**
 * This UA device-class gate is kept verbatim from useInstallPrompt, and
 * is deliberately NOT the project's viewport-based desktop-detection hook (a
 * matchMedia width check answering a different question) — a desktop browser
 * resized narrow must never show the install drawer.
 */
export function isMobileUserAgent(): boolean {
  return typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

// A real Mac reports 0 touch points (1 with some trackpad drivers); an iPad reports 5.
const IPAD_MIN_TOUCH_POINTS = 2;

/**
 * Since iPadOS 13, iPad Safari and Chrome send a desktop "Macintosh" UA, so the
 * regex above never sees them. Touch points tell an iPad apart from a Mac.
 */
function isIpadOsDesktopUserAgent(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    /Macintosh/i.test(navigator.userAgent) &&
    navigator.maxTouchPoints >= IPAD_MIN_TOUCH_POINTS
  );
}

/**
 * Only this two-value class leaves the device, never the raw
 * user-agent string. iPadOS is counted as mobile here,
 * otherwise every modern iPad was stored as "desktop" and the data could not be
 * re-derived. The install prompt keeps the bare isMobileUserAgent gate.
 */
export function telemetryClient(): TelemetryClient {
  return isMobileUserAgent() || isIpadOsDesktopUserAgent() ? 'mobile' : 'desktop';
}
