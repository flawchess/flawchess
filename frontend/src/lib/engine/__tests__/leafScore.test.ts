/**
 * leafScore unit tests — the Root-Relative Frame Fixture (153-RESEARCH.md
 * "Root-Relative Frame Fixture", Pattern 3 / Pitfall 2).
 *
 * Proves `leafExpectedScore` treats `rootMover` as the driver of the sign
 * frame, NOT the leaf's own side to move: the SAME white-POV eval must
 * produce MIRRORED (not identical) results depending on which color is the
 * root player. Each `it` documents the frame-correctness property it proves:
 * - white-root +200 (White is better) reads as good for White (>0.5).
 * - black-root +200 (same white-POV eval, unmoved) reads as bad for Black
 *   (<0.5) — proving the conversion is root-relative, not leaf-relative.
 * - mate handling mirrors the same root-relative behavior at the extremes.
 * - a null/null grade (no eval available) is neutral (exactly 0.5).
 */

import { describe, it, expect } from 'vitest';
import type { MoverColor } from '@/lib/liveFlaw';
import { leafExpectedScore } from '../leafScore';
import type { MoveGrade } from '../types';

const WHITE: MoverColor = 'white';
const BLACK: MoverColor = 'black';

describe('leafExpectedScore', () => {
  it('white root + white-POV +200cp (good for White) reads above neutral', () => {
    const grade: MoveGrade = { evalCp: 200, evalMate: null, depth: 12 };
    expect(leafExpectedScore(grade, WHITE)).toBeGreaterThan(0.5);
  });

  it('black root + the SAME white-POV +200cp reads below neutral (mirrored, not identical)', () => {
    const grade: MoveGrade = { evalCp: 200, evalMate: null, depth: 12 };
    const white = leafExpectedScore(grade, WHITE);
    const black = leafExpectedScore(grade, BLACK);
    expect(black).toBeLessThan(0.5);
    // Proves `rootMover` alone drives the frame: mirrored around 0.5, not equal.
    expect(black).not.toBeCloseTo(white, 5);
    expect(black).toBeCloseTo(1 - white, 10);
  });

  it('mate-in-3 (white-POV, good for White) reads near 1.0 for a White root', () => {
    const grade: MoveGrade = { evalCp: null, evalMate: 3, depth: 12 };
    expect(leafExpectedScore(grade, WHITE)).toBeGreaterThan(0.95);
  });

  it('the SAME mate-in-3 grade reads near 0.0 for a Black root', () => {
    const grade: MoveGrade = { evalCp: null, evalMate: 3, depth: 12 };
    expect(leafExpectedScore(grade, BLACK)).toBeLessThan(0.05);
  });

  it('a null/null grade (no eval available) is exactly neutral regardless of root color', () => {
    const grade: MoveGrade = { evalCp: null, evalMate: null, depth: 0 };
    expect(leafExpectedScore(grade, WHITE)).toBe(0.5);
    expect(leafExpectedScore(grade, BLACK)).toBe(0.5);
  });
});
