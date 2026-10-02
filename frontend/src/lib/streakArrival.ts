/**
 * streakArrival — decides which one-shot animation the Train landing plays
 * for the streak flame and freeze meter (SEED-181).
 *
 * The page remembers the last `{streak, freezes}` it showed (per account, per
 * device, in localStorage) and diffs it against the fresh `/train/progress`
 * on arrival. Animations only play when something changed, so they read as a
 * reward rather than wallpaper:
 *
 * - streak went up                 -> the flame ignites, number counts up
 * - freezes went down, streak held -> the spent freezes crack, frost sweeps the flame
 * - freezes went up                -> the new freezes pop in
 * - streak went DOWN (reset)       -> the lit flame goes out, leaving the grey outline
 * - nothing stored yet             -> nothing (first visit, new device, private window)
 *
 * Per-device replay on a second device is accepted: this is cosmetic, so it
 * does not earn a server-side "last seen" field.
 */

/** Mirrors `app.services.train_scheduler.SHIELD_CAP`. */
export const FREEZE_CAP = 7;

/** One freeze crack's length; the next spent freeze cracks after this, and
 * the flame's frost sweep waits for the last one. */
export const FREEZE_CRACK_STAGGER_MS = 550;

const STREAK_LAST_SEEN_KEY_PREFIX = 'flawchess_train_streak_last_seen:';

export interface StreakSnapshot {
  streak: number;
  freezes: number;
}

export type StreakArrival =
  | { kind: 'none' }
  | {
      kind: 'changed';
      /** What the page showed last time — the animation's starting frame. */
      prev: StreakSnapshot;
      ignite: boolean;
      extinguish: boolean;
      freezesUsed: number;
      freezesEarned: number;
    };

const NO_ARRIVAL: StreakArrival = { kind: 'none' };

export function resolveStreakArrival(
  prev: StreakSnapshot | null,
  next: StreakSnapshot,
): StreakArrival {
  if (prev === null) return NO_ARRIVAL;
  const ignite = next.streak > prev.streak;
  // The streak only ever goes down by resetting to 0.
  const extinguish = next.streak < prev.streak;
  const freezesUsed = Math.max(0, prev.freezes - next.freezes);
  const freezesEarned = Math.max(0, next.freezes - prev.freezes);
  if (!ignite && !extinguish && freezesUsed === 0 && freezesEarned === 0) return NO_ARRIVAL;
  return { kind: 'changed', prev, ignite, extinguish, freezesUsed, freezesEarned };
}

function lastSeenKey(ownerKey: string | null): string {
  return `${STREAK_LAST_SEEN_KEY_PREFIX}${ownerKey ?? 'anon'}`;
}

function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0;
}

/** Reads the last-shown snapshot. Any failure (no storage, blocked storage,
 * corrupt JSON) reads as "nothing stored", which plays no animation. */
export function readStreakLastSeen(ownerKey: string | null): StreakSnapshot | null {
  try {
    const raw = localStorage.getItem(lastSeenKey(ownerKey));
    if (raw === null) return null;
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null) return null;
    const { streak, freezes } = parsed as Record<string, unknown>;
    if (!isCount(streak) || !isCount(freezes)) return null;
    return { streak, freezes };
  } catch {
    return null;
  }
}

/** Silently no-ops when storage is unavailable or throws. */
export function writeStreakLastSeen(ownerKey: string | null, snapshot: StreakSnapshot): void {
  try {
    localStorage.setItem(lastSeenKey(ownerKey), JSON.stringify(snapshot));
  } catch {
    // Cosmetic state only: a blocked write just means no animation next time.
  }
}
