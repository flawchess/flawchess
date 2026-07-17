import { describe, it, expect } from 'vitest';
import {
  HUMAN_BLEND,
  LIGHT_BLEND,
  DEEP_BLEND,
  BLEND_MAX,
  PLAY_STYLE_DEFAULT_BLEND,
  deriveActivePlayStylePreset,
  formatPlayStyleSummary,
} from '../playStyle';

describe('constants', () => {
  it('pins the three preset blends and the valid-range ceiling', () => {
    expect(HUMAN_BLEND).toBe(0);
    expect(LIGHT_BLEND).toBe(0.05);
    expect(DEEP_BLEND).toBe(0.5);
    expect(BLEND_MAX).toBe(1);
  });

  it('defaults to the Light preset', () => {
    expect(PLAY_STYLE_DEFAULT_BLEND).toBe(LIGHT_BLEND);
    expect(PLAY_STYLE_DEFAULT_BLEND).toBe(0.05);
  });
});

describe('deriveActivePlayStylePreset', () => {
  it('returns "human" at blend 0', () => {
    expect(deriveActivePlayStylePreset(0)).toBe('human');
  });

  it('returns "light" at the Light blend 0.05', () => {
    expect(deriveActivePlayStylePreset(0.05)).toBe('light');
  });

  it('returns "deep" at the Deep blend 0.5', () => {
    expect(deriveActivePlayStylePreset(0.5)).toBe('deep');
  });

  it('returns null for a non-preset blend (legacy stored value)', () => {
    expect(deriveActivePlayStylePreset(1)).toBeNull();
    expect(deriveActivePlayStylePreset(0.35)).toBeNull();
  });
});

describe('formatPlayStyleSummary', () => {
  it('returns behavior prose per preset with no numeric blend or ELO', () => {
    expect(formatPlayStyleSummary(0)).toBe('Human — instinct, no calculation');
    expect(formatPlayStyleSummary(0.05)).toBe('Light — calculates a little');
    expect(formatPlayStyleSummary(0.5)).toBe('Deep — calculates hard');
  });

  it('never leaks a blend number or percentage', () => {
    for (const blend of [0, 0.05, 0.5]) {
      expect(formatPlayStyleSummary(blend)).not.toMatch(/\d/);
    }
  });

  it('falls back to a neutral line for a non-preset legacy blend', () => {
    expect(formatPlayStyleSummary(1)).toBe('Custom calculation depth');
  });
});
