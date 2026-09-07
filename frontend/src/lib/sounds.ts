/**
 * Client-side sound-effect module for bot play (Phase 169, PLAY-08).
 *
 * Plays the vendored, license-correct AGPLv3+ lila `sfx` clips (see README.md
 * "## Sound Assets" and RESEARCH.md Pitfall 1 — NOT the non-free "standard"
 * set D-08 originally named). No new npm dependency.
 *
 * Playback goes through the Web Audio API wherever it exists: each clip is
 * decoded ONCE into an `AudioBuffer` (eagerly, at module load) and every play
 * is a fresh, throwaway `AudioBufferSourceNode`. A per-event
 * `HTMLAudioElement` path remains ONLY for environments without Web Audio
 * (jsdom, ancient browsers) — the two are never mixed on one page.
 *
 * Bug fix (iPhone 14): the module used to be element-only, restarting one
 * shared element per event via `currentTime = 0; play()`. iOS Safari drops
 * most of those retriggers when they arrive faster than the element's own
 * async seek/play pipeline turns around, so the 200ms fast-forward cadence
 * (and quick taps on Next) produced roughly one audible move sound in four. A
 * buffer source has no such pipeline: overlapping one-shots are its designed
 * use, and lila plays its sfx the same way.
 *
 * The iOS half of the fix is the audio-session category (see
 * `requestPlaybackAudioSession`): on the phone every Web Audio play was silent
 * — even a bare oscillator on a fresh context created inside a tap — while a
 * media element stayed audible, because a page that only uses Web Audio is
 * put in the "ambient" category. Asking for "playback" made it audible.
 *
 * Why the element path is not kept as a fallback when Web Audio exists: the
 * first attempt at this fix routed the plays that arrived before decoding
 * finished through the elements, which muddled the iPhone diagnosis (element
 * plays audible, buffer plays silent looked like a broken context rather than
 * a session category). Decoding now starts at module load instead, so the
 * buffers are ready long before the first click and one page uses exactly one
 * playback mechanism.
 *
 * Quick 260723-tqn: added `game-win`/`game-loss`/`game-draw`, which play
 * outcome-specific clips instead of the single undiscriminated `game-end`
 * (Checkmate) fired for every outcome. `game-end` itself is kept (still
 * iterated by `unlockAudio`) since callers may still reference it.
 *
 * Mute persistence (D-10) deliberately does NOT reuse `useUserFlag.ts` — that
 * hook is a one-shot, per-user-email-scoped, set-only-to-true flag (used for
 * "has seen X" nav dots). This module needs real two-way toggle semantics and
 * a flat, non-email-scoped key so guests (no account) still get a persisted
 * mute preference. It mirrors useUserFlag's `useSyncExternalStore` + listener
 * shape but inverts the storage sense: `'1'` = muted, absence/`'0'` = unmuted
 * (default ON per D-10), and `setMuted` accepts both `true` and `false`.
 *
 * `useBotGame` (plan 04) fires these events on game state transitions;
 * `GameControls` (plan 05) renders the mute toggle via `useMuted`/`setMuted`.
 */

import { useSyncExternalStore } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

/** Every event this module can render a sound for. The `game-end` and
 * `low-time`/`draw-declined` (D-09) events are single, undiscriminated
 * members — callers do not get separate win/loss/draw variants here. */
export type SoundEvent =
  | 'move'
  | 'capture'
  | 'check'
  | 'game-end'
  | 'low-time'
  | 'draw-declined'
  | 'game-win'
  | 'game-loss'
  | 'game-draw'
  | 'game-start'
  | 'score-partial'
  | 'score-full';

// ─── Named constants ─────────────────────────────────────────────────────────

/** localStorage key for the mute preference. Flat (non-email-scoped) so
 * guests without an account still get a persisted mute across reloads. */
export const MUTE_KEY = 'flawchess_bot_sound_muted';

/** Value written to localStorage when muted. Absence or any other value
 * (including the never-written `'0'`) reads as unmuted (default ON, D-10). */
const MUTED_VALUE = '1';

/** Maps each SoundEvent to its clip filename (without extension) under
 * `frontend/public/sound/`. `game-end` still uses `Checkmate` (kept for any
 * remaining undiscriminated caller); `game-loss` uses a ~1.5s sad cello phrase
 * (sounddino, not lila — see README "## Sound Assets"). `game-win` uses
 * `WinChime` — a
 * gentle, self-authored (CC0, no attribution) chime chosen over lila's
 * `Victory` fanfare, which read as too aggressive for bot games (and, per
 * 190.1 UAT round 7, for the Train reveal's perfect-score moment too — the
 * short-lived `victory` event was removed again, and `Victory.mp3` has since
 * been deleted from `public/sound/`). Quick 260814-b narrowed `game-win` to
 * the two end-of-everything wins (a bot-game win, and a green Train SESSION);
 * the per-puzzle full score moved to `score-full`. */
const SOUND_FILES: Record<SoundEvent, string> = {
  move: 'Move',
  capture: 'Capture',
  check: 'Check',
  'game-end': 'Checkmate',
  'low-time': 'LowTime',
  // Quick 260814-b: `draw-declined` and `game-draw` share one clip. Both are
  // "the game did not resolve" moments, and the two lila clips they used to
  // play (GenericNotify, Draw) were deleted — Draw peaked above full scale and
  // was the loudest asset in the set. The replacement is a two-note sounddino
  // chime, level-matched to the outgoing GenericNotify. Keep the two events
  // separate (not one merged event) so either can be re-pointed on its own.
  'draw-declined': 'Notify',
  'game-win': 'WinChime',
  'game-loss': 'Defeat',
  'game-draw': 'Notify',
  // Quick 260813-oae: fired from `BotsPage`'s `handleStart` (the single start
  // path). Deliberately a longer clip (~0.78s of pieces being set out) than the
  // sub-100ms one-shots above — it marks a one-time event, not a per-move tick.
  'game-start': 'GameStart',
  // Quick 260814: the "mixed result" sound — a partial per-puzzle Train score
  // and the yellow session-verdict band. This is the lila clip that used to be
  // `LowTime.mp3` (renamed, byte-identical); `low-time` now plays an actual
  // ticking clock, which reads as a clock warning and made no sense on a Train
  // score. Keep them separate if either is re-cut.
  'score-partial': 'PartialScore',
  // Quick 260814-b: the per-puzzle FULL score. This used to play `game-win`
  // (WinChime), which made the reward for solving one puzzle sound identical
  // to the reward for the whole session. WinChime is now reserved for the two
  // end-of-everything wins — a green (>=75%) Train session and a bot-game win
  // — and a solved puzzle gets its own shorter phrase, level-matched to the
  // WinChime it took over from so the reveal does not jump in loudness.
  'score-full': 'FullScore',
};

const SOUND_EVENTS = Object.keys(SOUND_FILES) as SoundEvent[];

// ─── Audio instance cache ────────────────────────────────────────────────────

const audioCache = new Map<SoundEvent, HTMLAudioElement>();

function getAudio(event: SoundEvent): HTMLAudioElement {
  let audio = audioCache.get(event);
  if (!audio) {
    audio = new Audio(`/sound/${SOUND_FILES[event]}.mp3`);
    audioCache.set(event, audio);
  }
  return audio;
}

/** Plays from the start, swallowing autoplay-blocked rejections (e.g. before
 * `unlockAudio` has run on iOS Safari — Pitfall 4) rather than surfacing an
 * unhandled promise rejection. */
function safePlay(audio: HTMLAudioElement): void {
  try {
    audio.currentTime = 0;
  } catch {
    // Some environments (or a not-yet-loaded clip) reject currentTime resets.
  }
  const playResult: unknown = audio.play();
  if (
    playResult &&
    typeof (playResult as Promise<void>).catch === 'function'
  ) {
    (playResult as Promise<void>).catch(() => {
      // Autoplay blocked or playback interrupted — not actionable here.
    });
  }
}

// ─── Mute persistence (useSyncExternalStore, guest-usable) ──────────────────

const listeners = new Set<() => void>();

function subscribe(callback: () => void): () => void {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

function readMuted(): boolean {
  try {
    return localStorage.getItem(MUTE_KEY) === MUTED_VALUE;
  } catch {
    return false;
  }
}

/** Default-ON (unmuted) subscription to the persisted mute preference. Works
 * for guests — the key is flat, not scoped to a user email. */
export function useMuted(): boolean {
  return useSyncExternalStore(subscribe, readMuted, () => false);
}

/** Toggles and persists the mute preference (real two-way semantics, unlike
 * `useUserFlag`'s set-only-to-true design). Wrapped in try/catch so a
 * localStorage failure (private mode, quota) degrades to default-unmuted
 * rather than crashing playback (T-169-02). */
export function setMuted(muted: boolean): void {
  try {
    localStorage.setItem(MUTE_KEY, muted ? MUTED_VALUE : '0');
  } catch {
    return;
  }
  listeners.forEach((listener) => listener());
}

// ─── Web Audio one-shot playback ────────────────────────────────────────────

/** Created at module load (see the bottom of this file) so decoding can start
 * immediately. A context constructed outside a gesture starts suspended;
 * `unlockAudio`, called from the first real gesture, resumes it. `null` only
 * in environments without Web Audio, where every play takes the element path.
 * Browsers log a one-line "not allowed to start" warning for the early
 * construction — expected and harmless. */
let audioContext: AudioContext | null = null;

/** Decoded clips, keyed by event (not filename) for the same reason
 * `audioCache` is: the two Notify-sharing events stay independent. */
const bufferCache = new Map<SoundEvent, AudioBuffer>();

/** Events whose fetch+decode is in flight — guards against a second unlock
 * (each `useAnalysisBoard` instance unlocks once) re-fetching every clip. */
const decodePending = new Set<SoundEvent>();

function clipUrl(event: SoundEvent): string {
  return `/sound/${SOUND_FILES[event]}.mp3`;
}

/** Audio Session API (WebKit, iOS 17+; not in lib.dom yet). */
interface NavigatorWithAudioSession extends Navigator {
  audioSession?: { type: string };
}

/**
 * Bug fix (iPhone 14, third round): with media elements gone, EVERY Web Audio
 * sound was silent on the phone — even a bare oscillator on a fresh context
 * created inside a tap — while a `new Audio(...).play()` control was audible.
 * That is iOS's audio-session category: media elements play in the "playback"
 * category, but a page that only uses Web Audio is put in "ambient", which
 * iOS silences under the ring/silent switch and in several Focus / routing
 * states. Asking for "playback" ourselves makes Web Audio behave exactly as
 * the old element path did (audible on silent too, and it pauses other apps'
 * audio while a clip plays, as the elements already did). iOS 16 and earlier
 * lack the API and keep the ambient behaviour.
 */
const AUDIO_SESSION_TYPE = 'playback';

function requestPlaybackAudioSession(): void {
  const session = (navigator as NavigatorWithAudioSession).audioSession;
  if (session === undefined) return;
  try {
    session.type = AUDIO_SESSION_TYPE;
  } catch {
    // Not settable here: ambient behaviour remains.
  }
}

function createAudioContext(): AudioContext | null {
  if (typeof AudioContext !== 'function') return null;
  requestPlaybackAudioSession();
  try {
    return new AudioContext();
  } catch {
    return null;
  }
}

/** Best-effort: the context starts `suspended` and iOS parks it there again
 * (or in the non-standard `interrupted`) after a phone call / backgrounding;
 * only a `resume()` brings it back. Rejections are not actionable: a source
 * started on a suspended context simply plays once the context resumes. */
function resumeAudioContext(context: AudioContext): void {
  if (context.state === 'running') return;
  context.resume().catch(() => {
    // Not resumable right now (no gesture yet).
  });
}

function preloadBuffer(context: AudioContext, event: SoundEvent): void {
  if (bufferCache.has(event) || decodePending.has(event)) return;
  decodePending.add(event);
  fetch(clipUrl(event))
    .then((response) => response.arrayBuffer())
    .then((bytes) => context.decodeAudioData(bytes))
    .then((buffer) => {
      bufferCache.set(event, buffer);
    })
    .catch(() => {
      // Fetch/decode failure: this event stays silent (the element path is
      // deliberately never mixed in, see the module comment).
    })
    .finally(() => {
      decodePending.delete(event);
    });
}

/** One throwaway source per play — that is what lets rapid, overlapping
 * one-shots all sound instead of restarting a single element. The node
 * garbage-collects itself once it has finished. */
function playBuffer(context: AudioContext, buffer: AudioBuffer): void {
  resumeAudioContext(context);
  const source = context.createBufferSource();
  source.buffer = buffer;
  source.connect(context.destination);
  source.start();
}

/** Belt-and-braces iOS unlock: older WebKit only treated a context as
 * user-started once a source had actually been STARTED inside the gesture,
 * `resume()` alone not counting. One sample of silence costs nothing. */
function kickAudioContext(context: AudioContext): void {
  try {
    playBuffer(context, context.createBuffer(1, 1, context.sampleRate));
  } catch {
    // A context that cannot even allocate a one-sample buffer is unusable;
    // nothing to do.
  }
}

// ─── Playback ────────────────────────────────────────────────────────────────

/** Plays the clip for `event` unless muted. No-ops silently when muted.
 *
 * Web Audio when it exists (a play that arrives before its clip is decoded —
 * only possible in the first instants after page load — is dropped rather
 * than routed through a media element, see the module comment); the element
 * path otherwise. */
export function playSound(event: SoundEvent): void {
  if (readMuted()) return;
  if (audioContext !== null) {
    const buffer = bufferCache.get(event);
    if (buffer !== undefined) playBuffer(audioContext, buffer);
    return;
  }
  safePlay(getAudio(event));
}

/**
 * iOS Safari (and mobile Chrome) block `audio.play()` calls that aren't
 * triggered by a user gesture, until the page has received at least one
 * (Pitfall 4). Call this once from the first user gesture (e.g. the user's
 * own first move, or a "Start game" tap) to unlock playback for the rest of
 * the session — plays then immediately pauses each preloaded clip.
 */
export function unlockAudio(): void {
  // Web Audio: resume the (load-time) context inside the gesture and start a
  // silent source through it. NO media element is touched on this path — see
  // the module comment for the iOS sample-rate trap that rules that out.
  const context = audioContext;
  if (context !== null) {
    requestPlaybackAudioSession();
    resumeAudioContext(context);
    kickAudioContext(context);
    return;
  }
  for (const event of SOUND_EVENTS) {
    const audio = getAudio(event);
    // Never interrupt a clip that is already sounding. `game-start` (Quick
    // 260813-oae) is ~0.78s and fires from the Start click, so a pointerdown
    // inside the game view moments later would otherwise reach this loop and
    // pause it mid-clip. Tested `=== false`, not `!audio.paused`, so an
    // environment where `paused` is undefined still gets unlocked — failing to
    // unlock is far worse than clipping one sound.
    if (audio.paused === false) continue;
    safePlay(audio);
    audio.pause();
  }
}

// ─── Module-load initialisation ─────────────────────────────────────────────

/** Decoding starts now, not at the first gesture, so the buffers are ready by
 * the time a user can click anything. Exported for tests only: it lets a test
 * that stubs `AudioContext` AFTER importing the module re-run the load-time
 * step (a real page never calls it). */
export function initWebAudio(): void {
  audioContext ??= createAudioContext();
  const context = audioContext;
  if (context === null) return;
  for (const event of SOUND_EVENTS) preloadBuffer(context, event);
}

initWebAudio();
