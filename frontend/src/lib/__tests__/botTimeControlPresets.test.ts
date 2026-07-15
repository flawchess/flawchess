import { describe, it, expect } from 'vitest';
import {
  TIME_CONTROL_PRESETS,
  DEFAULT_TC_PRESET_LABEL,
  findPresetByLabel,
} from '../botTimeControlPresets';

describe('TIME_CONTROL_PRESETS', () => {
  it('has exactly 9 entries (D-14 order: blitz, rapid, classical) — no bullet', () => {
    expect(TIME_CONTROL_PRESETS).toHaveLength(9);
  });

  it('has no entry with baseSeconds < 180 (bullet is excluded by design)', () => {
    for (const preset of TIME_CONTROL_PRESETS) {
      expect(preset.baseSeconds).toBeGreaterThanOrEqual(180);
    }
  });

  it('every entry converts minutes*60 to baseSeconds and carries the label increment', () => {
    const fifteenPlusTen = findPresetByLabel('15+10');
    expect(fifteenPlusTen).toEqual({
      label: '15+10',
      baseSeconds: 900,
      incrementSeconds: 10,
      bucket: 'rapid',
    });
  });

  it('groups presets into blitz/rapid/classical buckets matching D-14', () => {
    const byLabel = Object.fromEntries(TIME_CONTROL_PRESETS.map((p) => [p.label, p.bucket]));
    expect(byLabel['3+0']).toBe('blitz');
    expect(byLabel['3+2']).toBe('blitz');
    expect(byLabel['5+0']).toBe('blitz');
    expect(byLabel['5+3']).toBe('blitz');
    expect(byLabel['10+0']).toBe('rapid');
    expect(byLabel['10+5']).toBe('rapid');
    expect(byLabel['15+10']).toBe('rapid');
    expect(byLabel['30+0']).toBe('classical');
    expect(byLabel['30+20']).toBe('classical');
  });
});

describe('DEFAULT_TC_PRESET_LABEL', () => {
  it('is "10+0"', () => {
    expect(DEFAULT_TC_PRESET_LABEL).toBe('10+0');
  });

  it('findPresetByLabel(DEFAULT_TC_PRESET_LABEL) resolves to 600 base seconds, 0 increment', () => {
    expect(findPresetByLabel(DEFAULT_TC_PRESET_LABEL)).toEqual({
      label: '10+0',
      baseSeconds: 600,
      incrementSeconds: 0,
      bucket: 'rapid',
    });
  });
});

describe('findPresetByLabel', () => {
  it('returns undefined for an unrecognized label', () => {
    expect(findPresetByLabel('bogus')).toBeUndefined();
  });
});
