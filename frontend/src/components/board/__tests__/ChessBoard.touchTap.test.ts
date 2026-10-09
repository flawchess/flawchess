import { describe, it, expect } from 'vitest';
import { isDuplicateTouchTap } from '../ChessBoard';

describe('isDuplicateTouchTap (Phase 237 UAT tap-to-select)', () => {
  const tap = { square: 'e2', at: 1000 };

  it('swallows the library echo of the same tap', () => {
    expect(isDuplicateTouchTap(tap, 'e2', 1050)).toBe(true);
  });

  it('lets a click through when no touch tap was recorded (mouse)', () => {
    expect(isDuplicateTouchTap(null, 'e2', 1050)).toBe(false);
  });

  it('lets a click on a different square through', () => {
    expect(isDuplicateTouchTap(tap, 'e4', 1050)).toBe(false);
  });

  it('lets a later deliberate second tap on the same square through', () => {
    expect(isDuplicateTouchTap(tap, 'e2', 2000)).toBe(false);
  });
});
