/**
 * useMaiaEloDefault — encapsulates the D-06/D-07 "you are here" ELO default
 * derivation for the Maia surfaces (ELO selector + chart + bar), kept out of
 * Analysis.tsx's already-large render (CLAUDE.md "refactor bloated code on sight").
 *
 * D-07 default rules:
 *   - Game mode: the SIDE-TO-MOVE's color rating-AT-GAME-TIME (`gameData.white_rating`
 *     / `gameData.black_rating` by `sideToMove`) — so on the opponent's move the ELO
 *     defaults to the opponent's rating, matching who is actually choosing the move
 *     (quick 260705-m3z). `sideToMove` omitted → falls back to `gameData.user_color`.
 *     Never the frozen current-rating snapshot.
 *   - Free play: the user's current platform rating (`profile.current_rating`),
 *     else the FREE_PLAY_DEFAULT_ELO (1500) midpoint fallback.
 *   - The resolved default is clamped to the MAIA_ELO_LADDER's [min, max] bounds
 *     (NOT snapped to its 100-ELO steps — a rating like 1720 stays 1720; only the
 *     ladder's outer bounds are enforced. useMaiaEngine's own `nearestByElo` picks
 *     the closest ladder rung for inference regardless of the exact selectedElo).
 *   - Once the user picks a value via the ELO selector, that pick wins permanently
 *     (user-override precedence) — a later gameData/profile load does not clobber it.
 */

import { useEffect, useRef, useState } from 'react';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';
import type { MoverColor } from '@/lib/liveFlaw';

/** Free-play fallback ELO when the user has no `current_rating` (D-07 midpoint). */
export const FREE_PLAY_DEFAULT_ELO = 1500;

/** Minimal game-data shape this hook needs (structurally satisfied by GameFlawCard). */
export interface MaiaEloGameData {
  user_color: string;
  white_rating: number | null;
  black_rating: number | null;
}

/** Minimal profile shape this hook needs (structurally satisfied by UserProfile). */
export interface MaiaEloProfile {
  current_rating: number | null;
}

export interface UseMaiaEloDefaultOptions {
  isGameMode: boolean;
  gameData: MaiaEloGameData | undefined;
  profile: MaiaEloProfile | undefined;
  /**
   * Color to move in the analysed position. In game mode the default ELO tracks
   * this color's rating (the opponent's on their moves) rather than always the
   * user's. Omit → falls back to `gameData.user_color`.
   */
  sideToMove?: MoverColor;
}

export interface UseMaiaEloDefaultState {
  selectedElo: number;
  setSelectedElo: (elo: number) => void;
}

/** Clamps `rating` into the ladder's [min, max] bounds (no step-snapping — see doc comment above). */
function clampToLadderBounds(rating: number, ladder: readonly number[] = MAIA_ELO_LADDER): number {
  const min = ladder[0] ?? rating;
  const max = ladder[ladder.length - 1] ?? rating;
  return Math.min(max, Math.max(min, rating));
}

/**
 * Raw (pre-clamp) D-07 default, or null while game-mode data hasn't arrived yet
 * (the caller falls back to FREE_PLAY_DEFAULT_ELO for the initial render only).
 */
function deriveRawDefault(
  isGameMode: boolean,
  gameData: MaiaEloGameData | undefined,
  profile: MaiaEloProfile | undefined,
  sideToMove: MoverColor | undefined,
): number | null {
  if (isGameMode) {
    if (gameData == null) return null;
    const moverColor = sideToMove ?? gameData.user_color;
    return moverColor === 'white' ? gameData.white_rating : gameData.black_rating;
  }
  return profile?.current_rating ?? FREE_PLAY_DEFAULT_ELO;
}

export function useMaiaEloDefault({
  isGameMode,
  gameData,
  profile,
  sideToMove,
}: UseMaiaEloDefaultOptions): UseMaiaEloDefaultState {
  const [selectedElo, setSelectedEloState] = useState<number>(() =>
    clampToLadderBounds(deriveRawDefault(isGameMode, gameData, profile, sideToMove) ?? FREE_PLAY_DEFAULT_ELO),
  );

  /** Flips true the first time the user picks a value — permanently wins over re-derivation. */
  const userOverrodeRef = useRef(false);

  const rawDefault = deriveRawDefault(isGameMode, gameData, profile, sideToMove);

  // Re-derive only while the user hasn't overridden yet, and only when the derived
  // value itself changes (e.g. gameData/profile arriving after mount) — not on every
  // render (the effect dependency is the derived value, not the raw props).
  useEffect(() => {
    if (userOverrodeRef.current || rawDefault == null) return;
    setSelectedEloState(clampToLadderBounds(rawDefault));
  }, [rawDefault]);

  const setSelectedElo = (elo: number): void => {
    userOverrodeRef.current = true;
    setSelectedEloState(elo);
  };

  return { selectedElo, setSelectedElo };
}
