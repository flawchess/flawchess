/**
 * botPlayerRow — the pure resolver behind both bot-game player rows
 * (`BotGameDesktopLayout` and, since the Phase 223 UAT round,
 * `BotGameMobileLayout` — the mobile clock strip was retired in favour of
 * the same name-left / clock-right rows the analysis board uses). No React,
 * no side effects: a total function of already-computed values, so the
 * bot-vs-user / guest-gate branching lives in ONE place rather than in each
 * layout's JSX.
 */

import { isLowTime } from '@/lib/chessClock';
import type { Persona } from '@/lib/personas/personaRegistry';
import type { CurrentStrength } from '@/types/users';

export interface BotPlayerRowInputs {
  /** `null` for a Custom game — no persona to source a name/label from. */
  persona: Persona | null;
  /** Resolved player display name (`BotsPage`'s single `resolvePlayerName`). */
  playerName: string;
  /** The player's own current-strength estimate; `null` (guest / no
   * qualifying estimate) renders NO rating label at all. */
  currentStrength: CurrentStrength | null;
  /** The user's own side — the bot's side is always the other one. */
  userColor: 'white' | 'black';
  /** The side currently to move — only its row carries the clock icon. */
  activeColor: 'white' | 'black';
  whiteClockMs: number;
  blackClockMs: number;
}

/** One player row's already-resolved props. */
export interface ResolvedPlayerRow {
  isWhite: boolean;
  name: string;
  ratingLabel: string | undefined;
  clockSeconds: number;
  clockActive: boolean;
  clockUrgent: boolean;
  testId: 'clock-bot' | 'clock-user';
}

export function resolvePlayerRow(
  color: 'white' | 'black',
  {
    persona,
    playerName,
    currentStrength,
    userColor,
    activeColor,
    whiteClockMs,
    blackClockMs,
  }: BotPlayerRowInputs,
): ResolvedPlayerRow {
  const clockMs = color === 'white' ? whiteClockMs : blackClockMs;
  const shared = {
    isWhite: color === 'white',
    clockSeconds: clockMs / 1000,
    clockActive: color === activeColor,
    clockUrgent: isLowTime(clockMs),
  };
  if (color !== userColor) {
    return {
      ...shared,
      name: persona?.name ?? 'FlawChess Bot',
      // D-11 (Phase 184 calibration-honesty rule): the honest tilde-prefixed
      // calibrated label, never a numeric rating — a null persona (Custom
      // game) renders no rating label at all, matching a Custom bot's
      // pre-existing no-rating treatment.
      ratingLabel: persona?.calibratedLabel,
      testId: 'clock-bot',
    };
  }
  return {
    ...shared,
    name: playerName,
    // The guest gate: no currentStrength -> no rating label, never an empty
    // parenthetical. Matches the roster row's own `~${Math.round(...)}`
    // expression verbatim (PersonaGrid.tsx).
    ratingLabel: currentStrength !== null ? `~${Math.round(currentStrength.rating)}` : undefined,
    testId: 'clock-user',
  };
}
