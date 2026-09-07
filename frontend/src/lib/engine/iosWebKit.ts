/**
 * iosWebKit — a synchronous "is this iOS/iPadOS WebKit?" probe, consulted by
 * `maiaWorkerHost.ts` in `spawn()` to pick the iOS Maia worker shape.
 *
 * SEED-158 (2026-09-07, final): iOS/iPadOS runs Maia on the CPU wasm backend
 * (`spawnOnIosWebKit()`: no WebGPU probe, no asyncify download), the backend
 * maiachess.com ships to the same phone. Measured on the reference iPhone 14
 * Pro (iOS 26.6.1, Safari) on the real /analysis page with Stockfish and the
 * FlawChess Engine on: every WebGPU shape (onnxruntime-web 1.27.0 and 1.23.0,
 * one or two wasm threads, idle or stepping) was killed by WebKit seconds
 * after `ready` (FLAWCHESS-AW), while the wasm backend survived full sessions
 * at one AND two wasm threads on both versions. Neither the ORT version nor
 * the page footprint was the lever; the thread count is left to
 * `chooseWasmThreadCount()`. Earlier readings (the 2026-09-06 blanket gate,
 * "wasm inference kills the page") were taken next to the pre-260906-p54 4 GB
 * memory reservation and are superseded; the seed file keeps the history.
 * Reopen only on an iOS `maia_failure:page-killed` Sentry event with
 * `backend:wasm` (see `maiaPageKillSentinel.ts`).
 *
 * Every browser on iOS/iPadOS is WebKit (Chrome, Firefox and Brave for iOS
 * wrap WKWebView), so "iOS" is the whole population; there is no
 * per-browser split to make. Two tells are needed because iPadOS 13+
 * requests desktop sites with a macOS Safari user agent — its only
 * remaining giveaway is a touch-capable `MacIntel` platform, which no real
 * Mac has. Chrome/Brave for iOS carry `iPhone`/`iPad` in the UA like Safari.
 */

/** Matches the classic iOS UA token; iPadOS 13+ desktop-mode UAs do NOT carry it. */
const IOS_UA_PATTERN = /iPhone|iPad|iPod/;
/** `navigator.platform` reported by iPadOS in desktop-site mode and by every Intel/Apple-silicon Mac. */
const MAC_PLATFORM = 'MacIntel';
/** Macs report 0 touch points; an iPad reports 5 — anything above one is a touch device. */
const MIN_TOUCH_POINTS_FOR_IPAD = 1;

/** Minimal local shape so tests can pass a fake without stubbing the global `navigator`. */
export type NavigatorPlatformInfo = Pick<Navigator, 'userAgent' | 'platform' | 'maxTouchPoints'>;

/**
 * Returns `true` on iOS and iPadOS (any browser, all WebKit), `false`
 * everywhere else. Never throws — a missing/garbage `navigator` field reads
 * as "not iOS", so a non-browser test environment takes the normal
 * (WebGPU-probing) spawn path.
 */
export function isIosWebKit(nav: NavigatorPlatformInfo = navigator): boolean {
  try {
    if (IOS_UA_PATTERN.test(nav.userAgent)) return true;
    return nav.platform === MAC_PLATFORM && nav.maxTouchPoints > MIN_TOUCH_POINTS_FOR_IPAD;
  } catch {
    return false;
  }
}
