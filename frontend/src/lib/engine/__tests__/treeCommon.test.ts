/**
 * treeCommon.ts unit tests (Phase 159 Pitfall 2/T-159-07).
 *
 * Covers the `sideMatchesMover` truth table: the four combinations of the
 * `Side` ('w'|'b') and `MoverColor` ('white'|'black') literal-type domains.
 * Dedicated test so the Phase 159 temperature call sites (`mctsSearch.ts`,
 * `fallbackExpectimax.ts`) can rely on ONE verified comparison instead of
 * two independently hand-rolled inline checks.
 */

import { describe, it, expect } from 'vitest';
import { sideMatchesMover } from '../treeCommon';

describe('sideMatchesMover', () => {
  it("'w' matches 'white'", () => {
    expect(sideMatchesMover('w', 'white')).toBe(true);
  });

  it("'b' matches 'black'", () => {
    expect(sideMatchesMover('b', 'black')).toBe(true);
  });

  it("'b' does NOT match 'white'", () => {
    expect(sideMatchesMover('b', 'white')).toBe(false);
  });

  it("'w' does NOT match 'black'", () => {
    expect(sideMatchesMover('w', 'black')).toBe(false);
  });
});
