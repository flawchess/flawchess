import { describe, expect, it } from 'vitest';
import { platformPlyUrl, gamePlatformUrl, supportsPlyDeepLink } from '@/lib/platformLinks';

describe('platformPlyUrl', () => {
  // The link lands on the position AFTER the flawed move (the blunder), so the
  // 0-indexed flaw ply maps to ply + 1 half-moves on both platforms.
  it('appends the (ply + 1) fragment for lichess, white POV (no orientation suffix)', () => {
    expect(platformPlyUrl('lichess', 'https://lichess.org/abcd1234', 41, 'white')).toBe(
      'https://lichess.org/abcd1234#42',
    );
  });

  it('flips lichess to black POV via the /black suffix when the user played black', () => {
    expect(platformPlyUrl('lichess', 'https://lichess.org/abcd1234', 41, 'black')).toBe(
      'https://lichess.org/abcd1234/black#42',
    );
  });

  it('is case-insensitive on the platform name', () => {
    expect(platformPlyUrl('Lichess', 'https://lichess.org/abcd1234', 7, 'white')).toBe(
      'https://lichess.org/abcd1234#8',
    );
  });

  it('rewrites chess.com live games to the analysis board (move = ply + 1)', () => {
    expect(platformPlyUrl('chess.com', 'https://www.chess.com/game/live/123', 41, 'white')).toBe(
      'https://www.chess.com/analysis/game/live/123?tab=details-tab&move=42',
    );
  });

  it('does not flip chess.com (no orientation param) when the user played black', () => {
    expect(platformPlyUrl('chess.com', 'https://www.chess.com/game/live/123', 41, 'black')).toBe(
      'https://www.chess.com/analysis/game/live/123?tab=details-tab&move=42',
    );
  });

  it('handles chess.com daily games', () => {
    expect(platformPlyUrl('chess.com', 'https://www.chess.com/game/daily/555', 10, 'white')).toBe(
      'https://www.chess.com/analysis/game/daily/555?tab=details-tab&move=11',
    );
  });

  it('falls back to the plain URL for an unexpected chess.com URL shape', () => {
    expect(platformPlyUrl('chess.com', 'https://www.chess.com/game/12345', 41, 'white')).toBe(
      'https://www.chess.com/game/12345',
    );
  });

  it('returns the plain URL for unknown platforms', () => {
    expect(platformPlyUrl('unknown', 'https://example.com/game/9', 12, 'white')).toBe(
      'https://example.com/game/9',
    );
  });

  it('returns null when no platform URL is available', () => {
    expect(platformPlyUrl('lichess', null, 41, 'white')).toBeNull();
    expect(platformPlyUrl('chess.com', null, 41, 'black')).toBeNull();
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

describe('flawchess bot games (quick-260714-qaj)', () => {
  // games.platform_url IS populated for bot games, but it is self-referential
  // (the in-app /analysis board). Both builders must return null so the cards
  // render no "Open game on platform" external link duplicating the in-app
  // Analyze / View game button. A regression here would put a new-tab link back
  // onto every bot game card.
  const SELF_URL = 'https://flawchess.com/analysis?game_id=693117';

  it('gamePlatformUrl returns null even though platform_url is populated', () => {
    expect(gamePlatformUrl('flawchess', SELF_URL, 'white')).toBeNull();
    expect(gamePlatformUrl('flawchess', SELF_URL, 'black')).toBeNull();
  });

  it('platformPlyUrl returns null even though platform_url is populated', () => {
    expect(platformPlyUrl('flawchess', SELF_URL, 12, 'black')).toBeNull();
  });

  it('supportsPlyDeepLink is false', () => {
    expect(supportsPlyDeepLink('flawchess')).toBe(false);
  });
});
