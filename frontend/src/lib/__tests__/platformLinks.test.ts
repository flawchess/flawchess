import { describe, expect, it } from 'vitest';
import { flawPlyUrl, gamePlatformUrl, supportsPlyDeepLink } from '@/lib/platformLinks';

describe('flawPlyUrl', () => {
  // The link lands on the position AFTER the flawed move (the blunder), so the
  // 0-indexed flaw ply maps to ply + 1 half-moves on both platforms.
  it('appends the (ply + 1) fragment for lichess, white POV (no orientation suffix)', () => {
    expect(flawPlyUrl('lichess', 'https://lichess.org/abcd1234', 41, 'white')).toBe(
      'https://lichess.org/abcd1234#42',
    );
  });

  it('flips lichess to black POV via the /black suffix when the user played black', () => {
    expect(flawPlyUrl('lichess', 'https://lichess.org/abcd1234', 41, 'black')).toBe(
      'https://lichess.org/abcd1234/black#42',
    );
  });

  it('is case-insensitive on the platform name', () => {
    expect(flawPlyUrl('Lichess', 'https://lichess.org/abcd1234', 7, 'white')).toBe(
      'https://lichess.org/abcd1234#8',
    );
  });

  it('rewrites chess.com live games to the analysis board (move = ply + 1)', () => {
    expect(flawPlyUrl('chess.com', 'https://www.chess.com/game/live/123', 41, 'white')).toBe(
      'https://www.chess.com/analysis/game/live/123?tab=details-tab&move=42',
    );
  });

  it('does not flip chess.com (no orientation param) when the user played black', () => {
    expect(flawPlyUrl('chess.com', 'https://www.chess.com/game/live/123', 41, 'black')).toBe(
      'https://www.chess.com/analysis/game/live/123?tab=details-tab&move=42',
    );
  });

  it('handles chess.com daily games', () => {
    expect(flawPlyUrl('chess.com', 'https://www.chess.com/game/daily/555', 10, 'white')).toBe(
      'https://www.chess.com/analysis/game/daily/555?tab=details-tab&move=11',
    );
  });

  it('falls back to the plain URL for an unexpected chess.com URL shape', () => {
    expect(flawPlyUrl('chess.com', 'https://www.chess.com/game/12345', 41, 'white')).toBe(
      'https://www.chess.com/game/12345',
    );
  });

  it('returns the plain URL for unknown platforms', () => {
    expect(flawPlyUrl('unknown', 'https://example.com/game/9', 12, 'white')).toBe(
      'https://example.com/game/9',
    );
  });

  it('returns null when no platform URL is available', () => {
    expect(flawPlyUrl('lichess', null, 41, 'white')).toBeNull();
    expect(flawPlyUrl('chess.com', null, 41, 'black')).toBeNull();
  });
});

describe('gamePlatformUrl', () => {
  it('flips lichess to black POV via /black when the user played black', () => {
    expect(gamePlatformUrl('lichess', 'https://lichess.org/abcd1234', 'black')).toBe(
      'https://lichess.org/abcd1234/black',
    );
  });

  it('leaves lichess unchanged (white default POV) when the user played white', () => {
    expect(gamePlatformUrl('lichess', 'https://lichess.org/abcd1234', 'white')).toBe(
      'https://lichess.org/abcd1234',
    );
  });

  it('leaves chess.com unchanged regardless of color (no orientation param)', () => {
    expect(gamePlatformUrl('chess.com', 'https://www.chess.com/game/live/123', 'black')).toBe(
      'https://www.chess.com/game/live/123',
    );
  });

  it('returns null when no platform URL is available', () => {
    expect(gamePlatformUrl('lichess', null, 'black')).toBeNull();
  });
});

describe('supportsPlyDeepLink', () => {
  it('is true for lichess and chess.com', () => {
    expect(supportsPlyDeepLink('lichess')).toBe(true);
    expect(supportsPlyDeepLink('Lichess')).toBe(true);
    expect(supportsPlyDeepLink('chess.com')).toBe(true);
  });

  it('is false for unknown platforms', () => {
    expect(supportsPlyDeepLink('unknown')).toBe(false);
  });
});
