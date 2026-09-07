/**
 * devEngineSwitches — dev-server-only bisect switches for on-device engine
 * UAT (SEED-158, 2026-09-06/07). Production bundles compile every export here
 * to a constant `false`/no-op because each one is guarded by
 * `import.meta.env.DEV`.
 *
 * Why: iOS Safari has no reachable console without a Mac, the mobile layout
 * of /analysis has no Stockfish toggle, and the Maia worker's chosen backend
 * and wasm thread count are only ever printed to the console. Bisecting
 * "which engine kills the page" on a phone therefore needs (a) a way to keep
 * Stockfish off entirely, (b) a way past the blanket iOS Maia gate without
 * editing it, (c) one switch per remaining suspect, and (d) an on-screen
 * readout of what Maia is running.
 *
 * Usage on the device (dev server via the tunnel) — each value persists in
 * localStorage across SPA navigation and reloads until switched back:
 *   /analysis?dev-stockfish=off|on         — inert Stockfish workers (no wasm fetch, no Blob)
 *   /analysis?dev-ios-gate=off|on          — bypass the blanket iOS Maia gate in maiaWorkerHost
 *   /analysis?dev-maia-runtime=worker|main — Suspect A: worker fetches the ORT runtime itself
 *                                            (no main-thread byte copy / transfer)
 *   /analysis?dev-maia-ladder=single|full  — Suspect B: one 21-rung batch per position
 *                                            (no exact rung, no prefetch, no coarse/fill split)
 * Several switches can be combined in one URL. The badge in the page corner
 * lists every switch that is currently active.
 */

const STORAGE_KEY_PREFIX = 'flawchess:dev:';
const QUERY_PARAM_PREFIX = 'dev-';
const BADGE_ID = 'flawchess-dev-engine-badge';

/** Every switch, with the value that means "back to production behaviour" (clears the key). */
const SWITCH_DEFAULTS = {
  stockfish: 'on',
  'ios-gate': 'on',
  'maia-runtime': 'main',
  'maia-ladder': 'full',
} as const;

type DevSwitchName = keyof typeof SWITCH_DEFAULTS;

const SWITCH_NAMES = Object.keys(SWITCH_DEFAULTS) as DevSwitchName[];

/** Copies every `?dev-<name>=<value>` from the URL into localStorage once per page load. */
function syncSwitchesFromUrl(): void {
  if (!import.meta.env.DEV || typeof window === 'undefined') return;
  try {
    const params = new URLSearchParams(window.location.search);
    for (const name of SWITCH_NAMES) {
      const value = params.get(`${QUERY_PARAM_PREFIX}${name}`);
      if (value === null) continue;
      if (value === SWITCH_DEFAULTS[name]) localStorage.removeItem(`${STORAGE_KEY_PREFIX}${name}`);
      else localStorage.setItem(`${STORAGE_KEY_PREFIX}${name}`, value);
    }
  } catch {
    // localStorage unavailable (private mode / blocked storage): switches stay off.
  }
}

syncSwitchesFromUrl();

/** The persisted value of one switch, or its default — always the default outside the dev server. */
function readSwitch(name: DevSwitchName): string {
  if (!import.meta.env.DEV) return SWITCH_DEFAULTS[name];
  try {
    return localStorage.getItem(`${STORAGE_KEY_PREFIX}${name}`) ?? SWITCH_DEFAULTS[name];
  } catch {
    return SWITCH_DEFAULTS[name];
  }
}

/** True only on the dev server AND after visiting `?dev-stockfish=off`. */
export function isDevStockfishDisabled(): boolean {
  return readSwitch('stockfish') === 'off';
}

/**
 * True only on the dev server AND after visiting `?dev-ios-gate=off`: lets
 * `maiaWorkerHost.ts` spawn Maia on iOS/iPadOS for a phone run. The wasm
 * terminals stay in force (a `'wasm'` probe answer still gates off) — only
 * the blanket "never spawn on iOS" rule is bypassed.
 */
export function isDevIosGateBypassed(): boolean {
  return readSwitch('ios-gate') === 'off';
}

/**
 * True only on the dev server AND after visiting `?dev-maia-runtime=worker`
 * (Suspect A): the host spawns with no runtime buffer, so onnxruntime-web
 * resolves the runtime `.wasm` from `wasmPaths` inside the worker — no
 * main-thread cache read, no `ArrayBuffer` transfer. Same as the degraded
 * path a failed runtime fetch already takes.
 */
export function isDevMaiaRuntimeWorkerFetched(): boolean {
  return readSwitch('maia-runtime') === 'worker';
}

/**
 * True only on the dev server AND after visiting `?dev-maia-ladder=single`
 * (Suspect B): `useMaiaEngine` requests the whole ladder as ONE batch per
 * position (the pre-Phase-219 shape) — no exact-rung phase, no next-ply
 * prefetch, no coarse/fill split.
 */
export function isDevMaiaSinglePassLadder(): boolean {
  return readSwitch('maia-ladder') === 'single';
}

/** `name=value` for every switch that is NOT at its default, joined for the badge. */
function activeSwitchesLabel(): string {
  const active = SWITCH_NAMES.filter((name) => readSwitch(name) !== SWITCH_DEFAULTS[name]).map(
    (name) => `${name}=${readSwitch(name)}`,
  );
  return active.length === 0 ? 'switches: none' : `switches: ${active.join(' ')}`;
}

/**
 * An inert Worker that never answers: every Stockfish consumer just sits in
 * its "loading" state, spawns nothing wasm-shaped, and reserves no memory.
 * `blob:` URLs are same-origin, so COEP `require-corp` does not block them.
 */
export function createInertWorker(): Worker {
  const url = URL.createObjectURL(new Blob(['self.onmessage=()=>{}'], { type: 'text/javascript' }));
  return new Worker(url);
}

/**
 * Dev-only fixed badge in the page corner, so the Maia `ready` line
 * (`backend`, `numThreads`), the active switches, and a page-kill report from
 * the previous session are readable on a phone. Idempotent: one element,
 * text replaced on every call.
 */
export function showDevEngineBadge(text: string): void {
  if (!import.meta.env.DEV || typeof document === 'undefined') return;
  let el = document.getElementById(BADGE_ID);
  if (!el) {
    el = document.createElement('div');
    el.id = BADGE_ID;
    el.style.cssText =
      'position:fixed;bottom:4px;left:4px;z-index:2147483647;padding:2px 6px;max-width:95vw;' +
      'font:11px monospace;color:#fff;background:rgba(0,0,0,.75);border-radius:4px;pointer-events:none';
    document.body.appendChild(el);
  }
  el.textContent = `${text} | ${activeSwitchesLabel()}`;
}
