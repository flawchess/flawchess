// @vitest-environment jsdom
/**
 * useMaiaEloDefault unit tests (151-06-PLAN.md Task 1).
 *
 * Behaviors verified:
 * 1. Game mode, white user, white_rating=1720 -> resolved default 1720 (clamped to ladder bounds).
 * 2. Game mode, black user -> resolves from black_rating.
 * 3. Free play, profile.current_rating=1850 -> resolved default 1850.
 * 4. Free play, current_rating null -> resolved default FREE_PLAY_DEFAULT_ELO (1500).
 * 5. User-override precedence: a later gameData/profile load does not clobber a user pick.
 * 6. Re-derivation happens when gameData/profile FIRST load (not on every re-render).
 */

import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMaiaEloDefault, FREE_PLAY_DEFAULT_ELO } from '../useMaiaEloDefault';
import type { MaiaEloGameData, MaiaEloProfile } from '../useMaiaEloDefault';

function gameData(overrides: Partial<MaiaEloGameData>): MaiaEloGameData {
  return { user_color: 'white', white_rating: null, black_rating: null, ...overrides };
}

function profile(currentRating: number | null): MaiaEloProfile {
  return { current_rating: currentRating };
}

describe('useMaiaEloDefault', () => {
  it('game mode, white user: resolves from white_rating, clamped to ladder bounds (not step-snapped)', () => {
    const { result } = renderHook(() =>
      useMaiaEloDefault({
        isGameMode: true,
        gameData: gameData({ user_color: 'white', white_rating: 1720, black_rating: 1600 }),
        profile: undefined,
      }),
    );
    expect(result.current.selectedElo).toBe(1720);
  });

  it('game mode, black user: resolves from black_rating', () => {
    const { result } = renderHook(() =>
      useMaiaEloDefault({
        isGameMode: true,
        gameData: gameData({ user_color: 'black', white_rating: 1720, black_rating: 1350 }),
        profile: undefined,
      }),
    );
    expect(result.current.selectedElo).toBe(1350);
  });

  it('game mode: defaults to the SIDE-TO-MOVE rating (opponent on their move), not always the user', () => {
    const { result } = renderHook(() =>
      useMaiaEloDefault({
        isGameMode: true,
        gameData: gameData({ user_color: 'white', white_rating: 1720, black_rating: 1350 }),
        profile: undefined,
        // White user, but it's Black (the opponent) to move → default to Black's rating.
        sideToMove: 'black',
      }),
    );
    expect(result.current.selectedElo).toBe(1350);
  });

  it('game mode: sideToMove on the user\'s own move resolves from the user\'s rating', () => {
    const { result } = renderHook(() =>
      useMaiaEloDefault({
        isGameMode: true,
        gameData: gameData({ user_color: 'white', white_rating: 1720, black_rating: 1350 }),
        profile: undefined,
        sideToMove: 'white',
      }),
    );
    expect(result.current.selectedElo).toBe(1720);
  });

  it('free play: resolves from profile.current_rating', () => {
    const { result } = renderHook(() =>
      useMaiaEloDefault({
        isGameMode: false,
        gameData: undefined,
        profile: profile(1850),
      }),
    );
    expect(result.current.selectedElo).toBe(1850);
  });

  it('free play, current_rating null: falls back to FREE_PLAY_DEFAULT_ELO (1500)', () => {
    const { result } = renderHook(() =>
      useMaiaEloDefault({
        isGameMode: false,
        gameData: undefined,
        profile: profile(null),
      }),
    );
    expect(result.current.selectedElo).toBe(FREE_PLAY_DEFAULT_ELO);
    expect(FREE_PLAY_DEFAULT_ELO).toBe(1500);
  });

  it('user-override precedence: a user pick wins over a LATER gameData load', () => {
    const { result, rerender } = renderHook(
      (props: { gd: MaiaEloGameData | undefined }) =>
        useMaiaEloDefault({ isGameMode: true, gameData: props.gd, profile: undefined }),
      { initialProps: { gd: undefined } },
    );

    // Data hasn't loaded yet — falls back to the free-play default as a placeholder.
    expect(result.current.selectedElo).toBe(FREE_PLAY_DEFAULT_ELO);

    // User picks a value before gameData arrives.
    act(() => result.current.setSelectedElo(1900));
    expect(result.current.selectedElo).toBe(1900);

    // gameData arrives late — must NOT clobber the user's pick.
    rerender({ gd: gameData({ user_color: 'white', white_rating: 1720, black_rating: 1600 }) });
    expect(result.current.selectedElo).toBe(1900);
  });

  it('re-derives once when gameData/profile first load, before any user pick', () => {
    const { result, rerender } = renderHook(
      (props: { gd: MaiaEloGameData | undefined }) =>
        useMaiaEloDefault({ isGameMode: true, gameData: props.gd, profile: undefined }),
      { initialProps: { gd: undefined } },
    );

    expect(result.current.selectedElo).toBe(FREE_PLAY_DEFAULT_ELO);

    // Data arrives — no user pick yet, so the default IS re-derived.
    rerender({ gd: gameData({ user_color: 'white', white_rating: 1720, black_rating: 1600 }) });
    expect(result.current.selectedElo).toBe(1720);

    // A subsequent re-render with the SAME resolved rating is a no-op (still 1720),
    // proving the effect keys off the derived value, not "every render".
    rerender({ gd: gameData({ user_color: 'white', white_rating: 1720, black_rating: 1600 }) });
    expect(result.current.selectedElo).toBe(1720);
  });
});
