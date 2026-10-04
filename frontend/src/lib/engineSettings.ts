/**
 * Display settings store (Phase 228, SEED-175): how many lines and arrows each
 * engine (FlawChess, Stockfish) shows, persisted in localStorage.
 *
 * This module plus `useMuted` / `setMuted` in `lib/sounds.ts` (the Sound
 * setting, key `flawchess_bot_sound_muted`, `'1'` = muted) are the account-sync
 * seam: a later move to server-side settings swaps these two modules only.
 *
 * Shape mirrors `lib/sounds.ts` (module-level listener Set plus
 * `useSyncExternalStore`). One flat, non-email-scoped key per setting so guests
 * persist too. One primitive per key (not one JSON blob) so each
 * `getSnapshot` returns a stable number and React never sees a fresh object
 * per read.
 *
 * localStorage is user- and extension-writable and these values reach Stockfish
 * MultiPV, so every read accepts only an integer inside the setting's range and
 * falls back to the default otherwise (never a clamp).
 *
 * Quick 261004-nxn: the store also persists the three analysis-board engine
 * on/off switches (Stockfish, Maia, FlawChess), same flat-key pattern, default
 * ON. They are not panel settings, so `resetAllSettings` deliberately leaves
 * them alone: a reset that silently re-enabled heavy engines would surprise users.
 */

import { useSyncExternalStore } from 'react';
import { setMuted } from '@/lib/sounds';

// ─── Types and constants ────────────────────────────────────────────────────

export type LineCount = 1 | 2 | 3 | 4 | 5;
export type ArrowCount = 0 | 1 | 2 | 3;
export type CountSettingId = 'fcLines' | 'fcArrows' | 'sfLines' | 'sfArrows';
export type SettingId = CountSettingId | 'sound';

export const LINE_COUNT_OPTIONS: readonly LineCount[] = [1, 2, 3, 4, 5];
export const ARROW_COUNT_OPTIONS: readonly ArrowCount[] = [0, 1, 2, 3];

export const DEFAULT_LINES: LineCount = 2;
export const DEFAULT_ARROWS: ArrowCount = 1;

export const SETTINGS_STORAGE_KEYS: Readonly<Record<CountSettingId, string>> = {
  fcLines: 'flawchess_settings_fc_lines',
  fcArrows: 'flawchess_settings_fc_arrows',
  sfLines: 'flawchess_settings_sf_lines',
  sfArrows: 'flawchess_settings_sf_arrows',
};

export interface EngineDisplaySettings {
  fcLines: LineCount;
  fcArrows: ArrowCount;
  sfLines: LineCount;
  sfArrows: ArrowCount;
}

const COUNT_SETTING_IDS: readonly CountSettingId[] = ['fcLines', 'fcArrows', 'sfLines', 'sfArrows'];

export type EngineToggleId = 'stockfish' | 'maia' | 'flawChess';

export interface EngineToggles {
  stockfish: boolean;
  maia: boolean;
  flawChess: boolean;
}

export const ENGINE_TOGGLE_STORAGE_KEYS: Readonly<Record<EngineToggleId, string>> = {
  stockfish: 'flawchess_settings_engine_stockfish',
  maia: 'flawchess_settings_engine_maia',
  flawChess: 'flawchess_settings_engine_flawchess',
};

/** Same '1'/'0' format as the sound mute key in `lib/sounds.ts`. */
const TOGGLE_ON = '1';
const TOGGLE_OFF = '0';
const DEFAULT_ENGINE_TOGGLE = true;

// ─── Validation (type guards, no casts) ─────────────────────────────────────

function isLineCount(value: number): value is LineCount {
  return LINE_COUNT_OPTIONS.some((option) => option === value);
}

function isArrowCount(value: number): value is ArrowCount {
  return ARROW_COUNT_OPTIONS.some((option) => option === value);
}

function isLineSetting(id: CountSettingId): id is 'fcLines' | 'sfLines' {
  return id === 'fcLines' || id === 'sfLines';
}

function isValidForSetting(id: CountSettingId, value: number): boolean {
  return isLineSetting(id) ? isLineCount(value) : isArrowCount(value);
}

function defaultFor(id: CountSettingId): number {
  return isLineSetting(id) ? DEFAULT_LINES : DEFAULT_ARROWS;
}

// ─── Store ──────────────────────────────────────────────────────────────────

const listeners = new Set<() => void>();

function subscribe(callback: () => void): () => void {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

function notify(): void {
  listeners.forEach((listener) => listener());
}

/** Reads one count as a validated primitive; anything unusable is the default. */
function readCount(id: CountSettingId): number {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEYS[id]);
    // Empty string would coerce to 0, a valid arrow count: treat it as absent.
    if (raw === null || raw.trim() === '') return defaultFor(id);
    const parsed = Number(raw);
    return Number.isInteger(parsed) && isValidForSetting(id, parsed) ? parsed : defaultFor(id);
  } catch {
    return defaultFor(id);
  }
}

function readLines(id: 'fcLines' | 'sfLines'): LineCount {
  const value = readCount(id);
  return isLineCount(value) ? value : DEFAULT_LINES;
}

function readArrows(id: 'fcArrows' | 'sfArrows'): ArrowCount {
  const value = readCount(id);
  return isArrowCount(value) ? value : DEFAULT_ARROWS;
}

const getFcLines = (): LineCount => readLines('fcLines');
const getSfLines = (): LineCount => readLines('sfLines');
const getFcArrows = (): ArrowCount => readArrows('fcArrows');
const getSfArrows = (): ArrowCount => readArrows('sfArrows');

/** Subscription to all four engine display counts. Defaults with no stored value. */
export function useEngineDisplaySettings(): EngineDisplaySettings {
  const fcLines = useSyncExternalStore(subscribe, getFcLines, () => DEFAULT_LINES);
  const fcArrows = useSyncExternalStore(subscribe, getFcArrows, () => DEFAULT_ARROWS);
  const sfLines = useSyncExternalStore(subscribe, getSfLines, () => DEFAULT_LINES);
  const sfArrows = useSyncExternalStore(subscribe, getSfArrows, () => DEFAULT_ARROWS);
  return { fcLines, fcArrows, sfLines, sfArrows };
}

/** Persists one count. Invalid values are ignored without writing. A storage
 * failure (private mode, quota) degrades to the default rather than throwing. */
export function setCountSetting(id: CountSettingId, value: number): void {
  if (!Number.isInteger(value) || !isValidForSetting(id, value)) return;
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEYS[id], String(value));
  } catch {
    return;
  }
  notify();
}

/** Restores all five settings: the four counts to their defaults and sound on. */
export function resetAllSettings(): void {
  try {
    COUNT_SETTING_IDS.forEach((id) => localStorage.removeItem(SETTINGS_STORAGE_KEYS[id]));
  } catch {
    // Nothing to remove if storage is unavailable; reads already yield defaults.
  }
  setMuted(false);
  notify();
}

// ─── Engine on/off switches ─────────────────────────────────────────────────

/**
 * In-session values for switches whose storage write failed (private mode,
 * quota). Unlike a count setting, which may simply not apply, an engine switch
 * that ignored the click would be inert, so the failed value is kept in memory
 * for the rest of the session. A successful write clears the override, so
 * storage stays the source of truth whenever it works.
 */
const sessionToggleOverrides: Partial<Record<EngineToggleId, boolean>> = {};

/** Only the exact off value disables an engine; absent or tampered reads as ON. */
function readEngineToggle(id: EngineToggleId): boolean {
  const override = sessionToggleOverrides[id];
  if (override !== undefined) return override;
  try {
    return localStorage.getItem(ENGINE_TOGGLE_STORAGE_KEYS[id]) !== TOGGLE_OFF;
  } catch {
    return DEFAULT_ENGINE_TOGGLE;
  }
}

const getStockfishToggle = (): boolean => readEngineToggle('stockfish');
const getMaiaToggle = (): boolean => readEngineToggle('maia');
const getFlawChessToggle = (): boolean => readEngineToggle('flawChess');
const getEngineToggleServerSnapshot = (): boolean => DEFAULT_ENGINE_TOGGLE;

/** Subscription to the three engine switches. Defaults ON with no stored value. */
export function useEngineToggles(): EngineToggles {
  const stockfish = useSyncExternalStore(subscribe, getStockfishToggle, getEngineToggleServerSnapshot);
  const maia = useSyncExternalStore(subscribe, getMaiaToggle, getEngineToggleServerSnapshot);
  const flawChess = useSyncExternalStore(subscribe, getFlawChessToggle, getEngineToggleServerSnapshot);
  return { stockfish, maia, flawChess };
}

/** Persists one engine switch and notifies subscribers. */
export function setEngineToggle(id: EngineToggleId, on: boolean): void {
  try {
    localStorage.setItem(ENGINE_TOGGLE_STORAGE_KEYS[id], on ? TOGGLE_ON : TOGGLE_OFF);
    delete sessionToggleOverrides[id];
  } catch {
    sessionToggleOverrides[id] = on;
  }
  notify();
}
