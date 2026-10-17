/**
 * useMaiaEloDefault — encapsulates the "you are here" ELO default
 * derivation for the Maia surfaces (ELO selector + chart + bar), kept out of
 * Analysis.tsx's already-large render (CLAUDE.md "refactor bloated code on sight").
 *
 * Default rules:
 *   - Game mode: the SIDE-TO-MOVE's color rating-AT-GAME-TIME, preferring the
 *     Lichess-blitz-normalized rating (`gameData.white_rating_lichess_blitz` /
 *     `.black_rating_lichess_blitz`) when present, else the raw
 *     `gameData.white_rating` / `.black_rating` — so on the opponent's move the ELO
 *     defaults to the opponent's (normalized) rating, matching who is actually choosing
 *     the move. `sideToMove` omitted → falls back to `gameData.user_color`.
 *     Never the frozen current-rating snapshot.
 *   - Free play: the user's
 *     `profile.current_strength.rating` — a current-strength estimate read through
 *     `apply_game_filters`, with the blitz-bucket anchor as its own server-side
 *     fallback — else the FREE_PLAY_DEFAULT_ELO (1500) midpoint fallback. Deliberately
 *     NOT a raw platform rating from the user's most recent game — that is inflated for
 *     chess.com users relative to the Maia/Lichess-blitz scale this slider is on
 *     (see the `MaiaEloProfile` docblock below).
 *   - The resolved default is clamped to the MAIA_ELO_LADDER's [min, max] bounds
 *     (NOT snapped to its 100-ELO steps — a rating like 1720 stays 1720; only the
 *     ladder's outer bounds are enforced. useMaiaEngine's own `nearestByElo` picks
 *     the closest ladder rung for inference regardless of the exact selectedElo).
 *   - Once the user picks a value via the ELO selector, that pick wins permanently
 *     (user-override precedence) — a later gameData/profile load does not clobber it.
 *
 * `deriveRawDefault` and `clampToLadderBounds` are exported so the background
 * gem sweep can pin each ply's gem rung to the MOVER's own rating-at-game-time
 * without re-deriving the fallback chain a second time. The slider still owns
 * the live exploration overlay; only the gem rung ignores it.
 */

import { useEffect, useRef, useState } from 'react';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';
import type { MoverColor } from '@/lib/liveFlaw';

/** Free-play fallback ELO when the profile has no `current_strength` rating (midpoint). */
export const FREE_PLAY_DEFAULT_ELO = 1500;

/** Minimal game-data shape this hook needs (structurally satisfied by GameFlawCard). */
export interface MaiaEloGameData {
  user_color: string;
  white_rating: number | null;
  black_rating: number | null;
  // Lichess-blitz-normalized ratings; optional + nullable so a
  // missing value falls back to the raw rating.
  white_rating_lichess_blitz?: number | null;
  black_rating_lichess_blitz?: number | null;
}

/**
 * Minimal profile shape this hook needs (structurally satisfied by UserProfile).
 *
 * `current_strength.rating` is a value derived through `apply_game_filters`
 * (rated=True, opponent_type="human", platform=None) — the filtering that excludes
 * FlawChess's OWN bot-game rating stamps and unrated/pasted games, with the
 * blitz-bucket anchor fallback resolved SERVER-SIDE inside `current_strength`.
 * Don't add a "rating from the most recent game" field here (or read one from
 * UserProfile) without that filtering: an unfiltered version once reported 1340
 * for a prod user, an echo of a stale rapid anchor read back as the user's own
 * rating.
 */
export interface MaiaEloProfile {
  // The rating the free-play branch actually reads.
  current_strength: { rating: number } | null;
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
  /**
   * The players' derived default ELO (clamped to the ladder bounds) — the value
   * `resetToDefault` restores to. Used by the EloSelector to show its inline reset
   * control only while `selectedElo` differs from this.
   */
  defaultElo: number;
  /**
   * Clears the user-override flag and snaps `selectedElo` back to the derived
   * default (the slider's way back to the players' rating without a
   * page reload). After a reset, re-derivation resumes, so a later gameData/profile
   * change tracks again — same as a fresh mount.
   */
  resetToDefault: () => void;
}

/** Clamps `rating` into the ladder's [min, max] bounds (no step-snapping — see doc comment above). */
export function clampToLadderBounds(rating: number, ladder: readonly number[] = MAIA_ELO_LADDER): number {
  const min = ladder[0] ?? rating;
  const max = ladder[ladder.length - 1] ?? rating;
  return Math.min(max, Math.max(min, rating));
}

/**
 * Raw (pre-clamp) default, or null while game-mode data hasn't arrived yet
 * (the caller falls back to FREE_PLAY_DEFAULT_ELO for the initial render only).
 *
 * Exported so the background gem sweep pins each
 * ply's gem rung to the MOVER's own rating-at-game-time, independent of the
 * live Elo slider (`selectedElo`). Re-deriving the `*_lichess_blitz ?? raw`
 * fallback chain a second time in the sweep would drift the moment the
 * normalization edge cases change — this export is the single source of truth
 * both the live selector and the sweep read from.
 */
export function deriveRawDefault(
  isGameMode: boolean,
  gameData: MaiaEloGameData | undefined,
  profile: MaiaEloProfile | undefined,
  sideToMove: MoverColor | undefined,
): number | null {
  if (isGameMode) {
    if (gameData == null) return null;
    const moverColor = sideToMove ?? gameData.user_color;
    if (moverColor === 'white') {
      return gameData.white_rating_lichess_blitz ?? gameData.white_rating;
    }
    return gameData.black_rating_lichess_blitz ?? gameData.black_rating;
  }
  return profile?.current_strength?.rating ?? FREE_PLAY_DEFAULT_ELO;
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

  // The clamped players' default (rawDefault is null only while game-mode data is
  // still loading — fall back to the same midpoint the initial useState uses).
  const defaultElo = clampToLadderBounds(rawDefault ?? FREE_PLAY_DEFAULT_ELO);

  const resetToDefault = (): void => {
    userOverrodeRef.current = false;
    setSelectedEloState(defaultElo);
  };

  return { selectedElo, setSelectedElo, defaultElo, resetToDefault };
}
