/**
 * botPersonaSetupSettings — the persona detail surface's own owner-scoped
 * localStorage key for last-used color/TC preferences (Phase 183, D-05).
 *
 * Mirrors `botSetupSettings.ts`'s control flow VERBATIM (SSR guard ->
 * try/catch -> JSON.parse -> shape validator with range checks -> Sentry-once
 * clearCorrupt -> silent-no-op write) but under a NEW, distinct key prefix —
 * never `botSetupSettings.ts`'s `BOT_SETUP_SETTINGS_KEY_PREFIX` nor
 * `botGameSnapshot.ts`'s snapshot key. Per `botSetupSettings.ts`'s own header
 * note (T-171-04-03): reusing a sibling key means a settings-shaped object
 * written there fails ITS validator and gets wrongly Sentry-flagged as
 * corrupt on the next visit — every new owner-scoped settings key must be
 * physically separate, not merely convention-enforced.
 *
 * The persisted shape here is deliberately narrower than
 * `BotSetupSettings`: ELO/blend/style are pinned by the persona itself
 * (`PERSONA_REGISTRY`) and are NEVER persisted here — only the SESSION
 * preferences the persona detail surface still lets the user pick (D-05):
 * color and time control.
 */

import * as Sentry from '@sentry/react';
import { DEFAULT_TC_PRESET_LABEL } from '@/lib/botTimeControlPresets';

export const BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX = 'flawchess_bot_persona_settings:';

function personaSetupSettingsKey(ownerKey: string | null | undefined): string {
  return `${BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX}${ownerKey ?? 'anon'}`;
}

/**
 * The persona detail surface's own last-used preferences. `colorPreference`
 * mirrors `BotSetupSettings`'s Random-inclusive contract (D-12: Random is
 * resolved to a concrete color at Play time, BEFORE `useBotGame` mounts, so
 * the snapshot/PGN always carry the actual color played).
 */
export interface BotPersonaSetupSettings {
  colorPreference: 'white' | 'black' | 'random';
  tcLabel: string;
}

/**
 * Shape validator. `colorPreference` is STRICTLY enum-checked (an
 * out-of-enum value is corruption, same discipline as `botSetupSettings.ts`'s
 * WR-01 fix for `botElo`/`blend`). `tcLabel` is intentionally NOT
 * strictly validated here — mirroring `botSetupSettings.ts`'s own TC-field
 * note, an unrecognized label is tolerated at this layer and re-resolved by
 * the caller (`findPresetByLabel(...) ?? DEFAULT_TC_PRESET_LABEL`), since a
 * removed/renamed preset should degrade gracefully rather than nuking the
 * user's saved color preference too.
 */
function isValidPersonaSetupSettingsShape(value: unknown): value is BotPersonaSetupSettings {
  if (typeof value !== 'object' || value === null) return false;
  const s = value as Record<string, unknown>;
  return (
    (s.colorPreference === 'white' || s.colorPreference === 'black' || s.colorPreference === 'random') &&
    typeof s.tcLabel === 'string'
  );
}

/** Sentry-once-on-corruption (mirrors `botSetupSettings.ts`'s
 * `clearCorruptSetupSettings` — clears the bad key immediately so a
 * subsequent read on the same visit sees clean "no settings" state, and
 * captures exactly ONCE at that point, tagged with this module's own
 * `source` so it's distinguishable from the sibling settings key). */
function clearCorruptPersonaSetupSettings(key: string, err: unknown): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // best-effort — nothing more to do if removal itself fails
  }
  Sentry.captureException(err, { tags: { source: 'bot-persona-setup-settings' } });
}

/**
 * Reads and validates the last-used persona settings for `ownerKey`. Any
 * failure (SSR, storage throw, JSON.parse failure, or a missing/mistyped
 * field) degrades to `null` — "no prefill, fall back to defaults" — never a
 * throw. A parse or shape-validation failure additionally clears the bad key
 * and captures to Sentry once.
 */
export function readPersonaSetupSettings(
  ownerKey: string | null | undefined,
): BotPersonaSetupSettings | null {
  if (typeof localStorage === 'undefined') return null;

  const key = personaSetupSettingsKey(ownerKey);
  let raw: string | null;
  try {
    raw = localStorage.getItem(key);
  } catch {
    return null;
  }
  if (raw === null) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    clearCorruptPersonaSetupSettings(key, err);
    return null;
  }

  if (!isValidPersonaSetupSettingsShape(parsed)) {
    clearCorruptPersonaSetupSettings(key, new Error('bot persona setup settings has an invalid shape'));
    return null;
  }

  return parsed;
}

/** Writes the last-used persona settings for `ownerKey`. Silently no-ops on
 * an SSR environment or a storage throw (QuotaExceeded / Safari private
 * mode) — degrade, never crash the persona detail surface. Only ever
 * touches this module's own key — never `botSetupSettings.ts`'s,
 * `botGameSnapshot.ts`'s, or `botPendingStore.ts`'s. */
export function writePersonaSetupSettings(
  ownerKey: string | null | undefined,
  settings: BotPersonaSetupSettings,
): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(personaSetupSettingsKey(ownerKey), JSON.stringify(settings));
  } catch {
    // QuotaExceededError / Safari private mode — degrade to no-prefill
  }
}

/** The persona detail surface's out-of-the-box defaults, before any
 * localStorage prefill or user override. */
export const DEFAULT_PERSONA_SETUP_SETTINGS: BotPersonaSetupSettings = {
  colorPreference: 'random',
  tcLabel: DEFAULT_TC_PRESET_LABEL,
};
