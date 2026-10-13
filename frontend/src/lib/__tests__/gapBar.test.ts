/** Phase 239 D-00a / D-00b / D-11 / D-14: the gap-bar math, words and the significance gate. */

import { describe, expect, it } from 'vitest';
import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import {
  GAP_CENTRE,
  GAP_EDGE_POS,
  bandRange,
  cellPosition,
  effectiveVerdict,
  formatGapNumber,
  formatSignedGap,
  gapPosition,
  gapVerdict,
  gapVerdictColor,
  gapWords,
  isChanceGap,
  type GapCell,
} from '../gapBar';

const LO = -0.31;
const HI = 0.25;

function cell(overrides: Partial<GapCell> = {}): GapCell {
  return {
    delta: -0.66,
    zoneLo: LO,
    zoneHi: HI,
    hasZone: true,
    significant: true,
    youRate: 5.46,
    oppRate: 6.12,
    ciLow: -1.0,
    ciHigh: -0.32,
    pValue: 0.0002,
    youEvents: 1916,
    oppEvents: 1982,
    ...overrides,
  };
}

describe('gapPosition (D-00a)', () => {
  it('puts a zero gap at the centre', () => {
    expect(gapPosition(0, LO, HI)).toBe(GAP_CENTRE);
  });

  it('draws the better (lower) edge of the band to the left (25% from the centre)', () => {
    expect(gapPosition(LO, LO, HI)).toBeCloseTo(25, 10);
  });

  it('draws the worse edge of an off-centre band inside the right half', () => {
    expect(gapPosition(HI, LO, HI)).toBeCloseTo(50 + (25 * 0.25) / 0.31, 10);
  });

  it('is monotonic outside the band and never reaches the edge', () => {
    const gaps = [-0.4, -0.7, -1, -3, -10, -100];
    const positions = gaps.map((g) => gapPosition(g, LO, HI));
    for (let i = 1; i < positions.length; i++) {
      expect(positions[i]!).toBeLessThan(positions[i - 1]!);
    }
    expect(gapPosition(-100, LO, HI)).toBeLessThan(gapPosition(-1, LO, HI));
    expect(gapPosition(-100, LO, HI)).toBeGreaterThanOrEqual(GAP_EDGE_POS);
    expect(gapPosition(100, LO, HI)).toBeLessThanOrEqual(100 - GAP_EDGE_POS);
  });

  it('saturates on the matching side for worse gaps', () => {
    expect(gapPosition(1, LO, HI)).toBeGreaterThan(75);
  });

  describe('guards', () => {
    it('centres a zero gap on a zero-width zero band', () => {
      expect(gapPosition(0, 0, 0)).toBe(GAP_CENTRE);
    });

    it('sends a non-zero gap on a zero band to the saturated edge of its side', () => {
      const worse = gapPosition(1, 0, 0);
      expect(Number.isFinite(worse)).toBe(true);
      expect(worse).toBeGreaterThan(GAP_CENTRE);
      expect(worse).toBe(100 - GAP_EDGE_POS);
      expect(gapPosition(-1, 0, 0)).toBe(GAP_EDGE_POS);
    });

    it('stays finite when the band has zero width but a non-zero scale', () => {
      const position = gapPosition(0.2, 0.05, 0.05);
      expect(Number.isFinite(position)).toBe(true);
      expect(position).toBeGreaterThan(GAP_CENTRE);
    });
  });
});

describe('gapVerdict (D-00b)', () => {
  it.each([
    [-0.66, 'better'],
    [0.3, 'worse'],
    [0, 'typical'],
    [LO, 'typical'],
    [HI, 'typical'],
  ] as const)('classifies %f as %s', (delta, expected) => {
    expect(gapVerdict(delta, LO, HI)).toBe(expected);
  });
});

describe('gap words', () => {
  it.each([
    [-1.7, '1.7 fewer'],
    [0.42, '0.42 more'],
    [0.004, 'same'],
    [-0.004, 'same'],
    [12.3, '12 more'],
    [-0.66, '0.66 fewer'],
  ])('writes %f as "%s"', (delta, expected) => {
    expect(gapWords(delta)).toBe(expected);
  });

  it('formats numbers by magnitude', () => {
    expect(formatGapNumber(12.3)).toBe('12');
    expect(formatGapNumber(1.74)).toBe('1.7');
    expect(formatGapNumber(0.419)).toBe('0.42');
  });

  it('signs footer numbers with a typographic minus', () => {
    expect(formatSignedGap(-0.66)).toBe('−0.66');
    expect(formatSignedGap(0.25)).toBe('+0.25');
    expect(formatSignedGap(0)).toBe('0.00');
    expect(formatSignedGap(-1.0028)).toBe('\u22121.00');
    expect(formatSignedGap(12.3)).toBe('+12');
  });
});

describe('effectiveVerdict (D-11, D-14)', () => {
  it('returns the verdict for a zoned, significant cell', () => {
    expect(effectiveVerdict(cell())).toBe('better');
    expect(effectiveVerdict(cell({ delta: 0.5 }))).toBe('worse');
    expect(effectiveVerdict(cell({ delta: 0 }))).toBe('typical');
  });

  it('reads an out-of-band gap that is not significant as typical', () => {
    expect(effectiveVerdict(cell({ significant: false }))).toBe('typical');
    expect(effectiveVerdict(cell({ delta: 0.5, significant: false }))).toBe('typical');
  });

  it.each([
    ['zoneless not-significant', { hasZone: false, significant: false }],
    ['gap-less', { delta: null }],
  ])('returns null for a %s cell', (_name, overrides) => {
    expect(effectiveVerdict(cell(overrides))).toBeNull();
  });

  it('judges a zoneless cell on significance alone (D-16)', () => {
    expect(effectiveVerdict(cell({ hasZone: false, delta: -0.66 }))).toBe('better');
    expect(effectiveVerdict(cell({ hasZone: false, delta: 0.5 }))).toBe('worse');
  });
});

describe('isChanceGap (D-14)', () => {
  it('is true only for an out-of-band gap that is not significant', () => {
    expect(isChanceGap(cell({ significant: false }))).toBe(true);
    expect(isChanceGap(cell())).toBe(false);
    expect(isChanceGap(cell({ delta: 0, significant: false }))).toBe(false);
    expect(isChanceGap(cell({ hasZone: false, significant: false }))).toBe(false);
    expect(isChanceGap(cell({ delta: null, significant: false }))).toBe(false);
  });
});

describe('cellPosition and bandRange', () => {
  it('positions a zoned cell on its band scale', () => {
    expect(cellPosition(cell({ delta: LO }))).toBeCloseTo(25, 10);
  });

  it('positions a zoneless cell against a virtual band of max(you, opponents)', () => {
    const zoneless = cell({ hasZone: false, delta: -2, youRate: 3, oppRate: 5 });
    expect(cellPosition(zoneless)).toBeCloseTo(gapPosition(-2, -5, 5), 10);
  });

  it('centres a gap-less cell', () => {
    expect(cellPosition(cell({ delta: null }))).toBe(GAP_CENTRE);
  });

  it('draws the band from the better (lower) edge to the worse edge', () => {
    const band = bandRange(cell());
    expect(band).not.toBeNull();
    expect(band!.leftPct).toBeCloseTo(25, 10);
    expect(band!.leftPct + band!.widthPct).toBeCloseTo(50 + (25 * 0.25) / 0.31, 10);
  });

  it('draws no band for a zoneless cell', () => {
    expect(bandRange(cell({ hasZone: false }))).toBeNull();
  });
});

describe('gapVerdictColor', () => {
  it('maps verdicts to the theme colours', () => {
    expect(gapVerdictColor('better')).toBe(ZONE_SUCCESS);
    expect(gapVerdictColor('worse')).toBe(ZONE_DANGER);
    expect(gapVerdictColor('typical')).toBe(GAUGE_NEUTRAL);
    expect(gapVerdictColor(null)).toBe(GAUGE_NEUTRAL);
  });
});
