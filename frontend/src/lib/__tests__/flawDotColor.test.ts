import { describe, expect, it } from 'vitest';
import { flawMarkerColor } from '../flawDotColor';
import { FACEPALM_HIGH_CUTOFF } from '../facepalm';
import { SEV_BLUNDER, SEV_FACEPALM, SEV_INACCURACY, SEV_MISTAKE } from '../theme';

// Local test constant: facepalm scores are 0..1 on the wire, the cut is a percent (D-21).
const PCT_SCALE = 100;
const ABOVE_CUT = (FACEPALM_HIGH_CUTOFF + 1) / PCT_SCALE;
const BELOW_CUT = (FACEPALM_HIGH_CUTOFF - 1) / PCT_SCALE;

describe('flawMarkerColor (260 D-17)', () => {
  it('draws a blunder above the cut in the facepalm colour', () => {
    expect(flawMarkerColor({ severity: 'blunder', facepalm_score: ABOVE_CUT })).toBe(SEV_FACEPALM);
  });

  it('keeps a blunder below the cut in the blunder colour', () => {
    expect(flawMarkerColor({ severity: 'blunder', facepalm_score: BELOW_CUT })).toBe(SEV_BLUNDER);
  });

  it('keeps an unscored blunder in the blunder colour', () => {
    expect(flawMarkerColor({ severity: 'blunder', facepalm_score: null })).toBe(SEV_BLUNDER);
    expect(flawMarkerColor({ severity: 'blunder' })).toBe(SEV_BLUNDER);
  });

  it('keeps a mistake with an above-cut score in the mistake colour', () => {
    expect(flawMarkerColor({ severity: 'mistake', facepalm_score: ABOVE_CUT })).toBe(SEV_MISTAKE);
  });

  it('keeps an inaccuracy in the inaccuracy colour', () => {
    expect(flawMarkerColor({ severity: 'inaccuracy', facepalm_score: null })).toBe(SEV_INACCURACY);
  });
});
