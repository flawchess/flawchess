/**
 * botSetupSettings — the THIRD, separate owner-scoped localStorage key for
 * the Bots setup screen's last-used settings (Phase 171 D-10/D-12, PLAY-02).
 *
 * Phase 170's `botGameSnapshot.ts` (in-progress game) and `botPendingStore.ts`
 * (finished-game upload queue) already own two distinct keys — this module
 * adds a third, mirroring their shape VERBATIM (SSR guard -> try/catch ->
 * JSON.parse -> shape validator -> Sentry-once-on-corruption -> silent-no-op
 * write) but under its OWN key prefix. Reuse of either existing key/validator
 * is forbidden: `botGameSnapshot.ts`'s `isValidSnapshotShape` requires
 * `pgn`/`whiteClockMs`, so a settings-shaped object written under that key
 * would fail its validator and get wrongly Sentry-flagged as corrupt on the
 * next `/bots` visit (RESEARCH.md's explicit anti-pattern warning). A settings
 * write here also must never overwrite or clear either sibling key — each
 * lives under a physically separate localStorage key, so this is structural,
 * not merely convention-enforced (T-171-04-03).
 */

import * as Sentry from '@sentry/react';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';
import { HUMAN_BLEND, BLEND_MAX, PLAY_STYLE_DEFAULT_BLEND } from '@/lib/playStyle';
import { DEFAULT_TC_PRESET_LABEL, findPresetByLabel } from '@/lib/botTimeControlPresets';

export const BOT_SETUP_SETTINGS_KEY_PREFIX = 'flawchess_bot_setup_settings:';

/** UI-DEFAULT-ONLY fallback ELO (D-07 midpoint) when a normalized rating is
 * unavailable (guests, no blitz-bucket anchor). */
export const BOT_SETUP_DEFAULT_ELO = 1500;

/** The ladder's outer rungs — the ONLY legal bounds for a persisted `botElo`
 * (WR-01) and the clamp bounds for `resolveDefaultBotElo`. Derived from
 * `MAIA_ELO_LADDER` rather than literals so a ladder revision cannot leave
 * either consumer behind. */
const LADDER_MIN_ELO = MAIA_ELO_LADDER[0] ?? BOT_SETUP_DEFAULT_ELO;
const LADDER_MAX_ELO = MAIA_ELO_LADDER[MAIA_ELO_LADDER.length - 1] ?? BOT_SETUP_DEFAULT_ELO;

function setupSettingsKey(ownerKey: string | null | undefined): string {
  return `${BOT_SETUP_SETTINGS_KEY_PREFIX}${ownerKey ?? 'anon'}`;
}

/**
 * The setup screen's own last-used preferences. `colorPreference` deliberately
 * includes `'random'` — this is a SETUP-screen preference, not
 * `BotGameSettings.userColor`. D-12 requires Random to be resolved to a
 * concrete color at Start, BEFORE `useBotGame` mounts, so the snapshot and
 * the exported PGN carry the actual color played and never "random".
 */
export interface BotSetupSettings {
  botElo: number;
  blend: number;
  baseSeconds: number;
  incrementSeconds: number;
  colorPreference: 'white' | 'black' | 'random';
}

/** In-range numeric check — `typeof x === 'number'` alone also admits NaN and
 * Infinity, which the `>= min && <= max` comparisons below reject. */
function isNumberInRange(value: unknown, min: number, max: number): boolean {
  return typeof value === 'number' && value >= min && value <= max;
}

/**
 * Bug fix (Phase 171 code review, WR-01): this used to type-check `botElo` /
 * `blend` (`typeof === 'number'`) WITHOUT range-checking them, so a stale or
 * tampered blob (`botElo: 40000`, `blend: 5`) validated clean and flowed all
 * the way through: the setup screen seeded its state from it, `blend` reached
 * `selectBotMove` (where `tau = TAU_MAX * (1 - blend)` goes NEGATIVE above 1),
 * and at store time the backend's `bot_elo` / `play_style_blend` Field bounds
 * rejected it with a 422 — which `useDrainPendingStore` treats as "remove the
 * entry", SILENTLY DISCARDING the finished game. Out-of-range values are now
 * corruption, and take the existing clear-and-Sentry path.
 *
 * The TC fields need no bound here: `SetupScreen.labelForSeconds` already
 * re-resolves them against `TIME_CONTROL_PRESETS` and falls back to
 * `DEFAULT_TC_PRESET_LABEL` for anything unrecognized.
 */
function isValidSetupSettingsShape(value: unknown): value is BotSetupSettings {
  if (typeof value !== 'object' || value === null) return false;
  const s = value as Record<string, unknown>;
  return (
    isNumberInRange(s.botElo, LADDER_MIN_ELO, LADDER_MAX_ELO) &&
    isNumberInRange(s.blend, HUMAN_BLEND, BLEND_MAX) &&
    typeof s.baseSeconds === 'number' &&
    typeof s.incrementSeconds === 'number' &&
    (s.colorPreference === 'white' || s.colorPreference === 'black' || s.colorPreference === 'random')
  );
}

/** Sentry-once-on-corruption (mirrors botGameSnapshot.ts's clearCorruptSnapshot
 * — clears the bad key immediately so a subsequent read on the same visit
 * sees clean "no settings" state, and captures exactly ONCE at that point). */
function clearCorruptSetupSettings(key: string, err: unknown): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // best-effort — nothing more to do if removal itself fails
  }
  Sentry.captureException(err, { tags: { source: 'bot-setup-settings' } });
}

/**
 * Reads and validates the last-used setup settings for `ownerKey`. Any
 * failure (SSR, storage throw, JSON.parse failure, or a missing/mistyped
 * field) degrades to `null` — "no prefill, fall back to defaults" — never a
 * throw. A parse or shape-validation failure additionally clears the bad key
 * and captures to Sentry once.
 */
export function readSetupSettings(ownerKey: string | null | undefined): BotSetupSettings | null {
  if (typeof localStorage === 'undefined') return null;

  const key = setupSettingsKey(ownerKey);
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
    clearCorruptSetupSettings(key, err);
    return null;
  }

  if (!isValidSetupSettingsShape(parsed)) {
    clearCorruptSetupSettings(key, new Error('bot setup settings has an invalid shape'));
    return null;
  }

  return parsed;
}

/** Writes the last-used setup settings for `ownerKey`. Silently no-ops on an
 * SSR environment or a storage throw (QuotaExceeded / Safari private mode) —
 * degrade, never crash the setup screen. Only ever touches this module's own
 * key — never `botGameSnapshot`'s or `botPendingStore`'s (T-171-04-03). */
export function writeSetupSettings(
  ownerKey: string | null | undefined,
  settings: BotSetupSettings,
): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(setupSettingsKey(ownerKey), JSON.stringify(settings));
  } catch {
    // QuotaExceededError / Safari private mode — degrade to no-prefill
  }
}

/**
 * Resolves the setup screen's default bot ELO from the user's normalized
 * (lichess-blitz-equivalent) rating: clamps into `MAIA_ELO_LADDER`'s bounds
 * and snaps to the nearest ACTUAL ladder rung, falling back to
 * `BOT_SETUP_DEFAULT_ELO` when the input is null/undefined/non-finite.
 *
 * Bug fix (Phase 171 code review, WR-02): the snap used to be
 * `Math.round((clamped - min) / 100) * 100 + min` — a bare `100` literal,
 * decoupled from the ladder whose min/max the same function derives. A ladder
 * revision (a 50- or 200-Elo step, or a non-uniform ladder) would have left it
 * emitting values that are NOT rungs, which `EloSelector`'s prop contract
 * explicitly forbids ("`value` must be a value present in `ladder`"). Snapping
 * by nearest-rung SEARCH over `MAIA_ELO_LADDER` cannot drift: it needs no step
 * constant at all and is correct for a non-uniform ladder too. Ties resolve
 * UPWARD (`<=`), preserving the old round-half-up behaviour (1650 -> 1700).
 *
 * BOT-03 (recorded here per the plan's requirement, not just in a commit
 * message): this rating is a **UI DEFAULT ONLY** — user-visible,
 * user-overridable, fixed for the game once chosen. It is never fed into
 * the bot's own move selection (`selectBotMove`'s `settings.elo` is always
 * the BOT's own configured strength, symmetric and non-adaptive) — a future
 * reviewer must not read this function as an adaptivity violation.
 *
 * D-06 (also recorded here): this function does NOT map the displayed ELO
 * to a "corrected" Maia rung using the 2026-07-12 calibration-harness table —
 * every cell in that table is a clamped bound, not an inversion; building
 * that inversion table is SEED-104's job, not this plan's.
 */
export function resolveDefaultBotElo(normalizedRating: number | null | undefined): number {
  if (normalizedRating == null || !Number.isFinite(normalizedRating)) {
    return BOT_SETUP_DEFAULT_ELO;
  }
  const clamped = Math.min(LADDER_MAX_ELO, Math.max(LADDER_MIN_ELO, normalizedRating));
  return MAIA_ELO_LADDER.reduce(
    (nearest, rung) =>
      Math.abs(rung - clamped) <= Math.abs(nearest - clamped) ? rung : nearest,
    LADDER_MIN_ELO,
  );
}

const DEFAULT_TC_PRESET = findPresetByLabel(DEFAULT_TC_PRESET_LABEL);

/** The setup screen's out-of-the-box defaults, before any localStorage
 * prefill or user override. */
export const DEFAULT_BOT_SETUP_SETTINGS: BotSetupSettings = {
  botElo: BOT_SETUP_DEFAULT_ELO,
  blend: PLAY_STYLE_DEFAULT_BLEND,
  baseSeconds: DEFAULT_TC_PRESET?.baseSeconds ?? 600,
  incrementSeconds: DEFAULT_TC_PRESET?.incrementSeconds ?? 0,
  colorPreference: 'random',
};
