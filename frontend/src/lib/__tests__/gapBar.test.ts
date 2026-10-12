/** Phase 239 D-00a / D-00b / D-11 / D-12 / D-13: the gap-bar math, words and ranking. */

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
  pickStandouts,
  standoutDistance,
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
    lowSample: false,
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

  it('draws the better edge of the band to the right (25% from the centre)', () => {
    expect(gapPosition(LO, LO, HI)).toBeCloseTo(75, 10);
  });

  it('draws the worse edge of an off-centre band inside the left half', () => {
    expect(gapPosition(HI, LO, HI)).toBeCloseTo(50 - (25 * 0.25) / 0.31, 10);
  });

  it('is monotonic outside the band and never reaches the edge', () => {
    const gaps = [-0.4, -0.7, -1, -3, -10, -100];
    const positions = gaps.map((g) => gapPosition(g, LO, HI));
    for (let i = 1; i < positions.length; i++) {
      expect(positions[i]!).toBeGreaterThan(positions[i - 1]!);
    }
    expect(gapPosition(-100, LO, HI)).toBeGreaterThan(gapPosition(-1, LO, HI));
    expect(gapPosition(-100, LO, HI)).toBeLessThanOrEqual(100 - GAP_EDGE_POS);
    expect(gapPosition(100, LO, HI)).toBeGreaterThanOrEqual(GAP_EDGE_POS);
  });

  it('saturates on the matching side for worse gaps', () => {
    expect(gapPosition(1, LO, HI)).toBeLessThan(25);
  });

  describe('guards', () => {
    it('centres a zero gap on a zero-width zero band', () => {
      expect(gapPosition(0, 0, 0)).toBe(GAP_CENTRE);
    });

    it('sends a non-zero gap on a zero band to the saturated edge of its side', () => {
      const worse = gapPosition(1, 0, 0);
      expect(Number.isFinite(worse)).toBe(true);
      expect(worse).toBeLessThan(GAP_CENTRE);
      expect(worse).toBe(GAP_EDGE_POS);
      expect(gapPosition(-1, 0, 0)).toBe(100 - GAP_EDGE_POS);
    });

    it('stays finite when the band has zero width but a non-zero scale', () => {
      const position = gapPosition(0.2, 0.05, 0.05);
      expect(Number.isFinite(position)).toBe(true);
      expect(position).toBeLessThan(GAP_CENTRE);
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

describe('effectiveVerdict (D-11, D-12)', () => {
  it('returns the verdict for a zoned, normal cell', () => {
    expect(effectiveVerdict(cell())).toBe('better');
    expect(effectiveVerdict(cell({ delta: 0.5 }))).toBe('worse');
    expect(effectiveVerdict(cell({ delta: 0 }))).toBe('typical');
  });

  it.each([
    ['zoneless', { hasZone: false }],
    ['low-sample', { lowSample: true }],
    ['gap-less', { delta: null }],
  ])('returns null for a %s cell', (_name, overrides) => {
    expect(effectiveVerdict(cell(overrides))).toBeNull();
  });
});

describe('cellPosition and bandRange', () => {
  it('positions a zoned cell on its band scale', () => {
    expect(cellPosition(cell({ delta: LO }))).toBeCloseTo(75, 10);
  });

  it('positions a zoneless cell against a virtual band of max(you, opponents)', () => {
    const zoneless = cell({ hasZone: false, delta: -2, youRate: 3, oppRate: 5 });
    expect(cellPosition(zoneless)).toBeCloseTo(gapPosition(-2, -5, 5), 10);
  });

  it('centres a gap-less cell', () => {
    expect(cellPosition(cell({ delta: null }))).toBe(GAP_CENTRE);
  });

  it('draws the band from the worse edge to the better edge', () => {
    const band = bandRange(cell());
    expect(band).not.toBeNull();
    expect(band!.leftPct).toBeCloseTo(50 - (25 * 0.25) / 0.31, 10);
    expect(band!.leftPct + band!.widthPct).toBeCloseTo(75, 10);
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

describe('standoutDistance (D-00g)', () => {
  it('measures the distance outside the band in band widths', () => {
    expect(standoutDistance(-0.87, LO, HI)).toBeCloseTo((LO - -0.87) / (HI - LO), 10);
    expect(standoutDistance(0.81, LO, HI)).toBeCloseTo((0.81 - HI) / (HI - LO), 10);
  });

  it('is 0 inside the band', () => {
    expect(standoutDistance(0, LO, HI)).toBe(0);
  });

  it('is null for a degenerate band', () => {
    expect(standoutDistance(-1, 0.1, 0.1)).toBeNull();
    expect(standoutDistance(-1, 0.2, 0.1)).toBeNull();
  });
});

describe('pickStandouts (D-00g, D-13)', () => {
  const row = (key: string, overrides: Partial<GapCell>) => ({ key, cell: cell(overrides) });

  it('drops low-sample, zoneless and gap-less rows entirely', () => {
    const result = pickStandouts([
      row('low', { lowSample: true }),
      row('zoneless', { hasZone: false }),
      row('empty', { delta: null }),
    ]);
    expect(result.strengths).toEqual([]);
    expect(result.weaknesses).toEqual([]);
    expect(result.typical).toEqual([]);
  });

  it('ranks strengths and weaknesses by distance and keeps the top N per side', () => {
    const result = pickStandouts(
      [
        row('s1', { delta: -0.4 }),
        row('s2', { delta: -2 }),
        row('s3', { delta: -0.9 }),
        row('s4', { delta: -1.5 }),
        row('w1', { delta: 0.4 }),
        row('w2', { delta: 3 }),
        row('t1', { delta: 0 }),
        row('t2', { delta: 0.1 }),
      ],
      3,
    );
    expect(result.strengths.map((r) => r.key)).toEqual(['s2', 's4', 's3']);
    expect(result.weaknesses.map((r) => r.key)).toEqual(['w2', 'w1']);
    expect(result.typical.map((r) => r.key)).toEqual(['t1', 't2']);
    expect(result.strengths[0]!.distance).toBeCloseTo((LO - -2) / (HI - LO), 10);
  });

  it('defaults to the top three per side', () => {
    const rows = ['a', 'b', 'c', 'd'].map((key, i) => row(key, { delta: -1 - i }));
    expect(pickStandouts(rows).strengths).toHaveLength(3);
  });
});
