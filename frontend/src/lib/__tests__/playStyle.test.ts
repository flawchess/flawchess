import { describe, it, expect } from 'vitest';
import {
  HUMAN_BLEND,
  ENGINE_BLEND,
  PLAY_STYLE_MIN,
  PLAY_STYLE_MAX,
  PLAY_STYLE_STEP,
  PLAY_STYLE_DEFAULT_BLEND,
  deriveActivePlayStylePreset,
  formatPlayStyleSummary,
} from '../playStyle';

describe('constants', () => {
  it('PLAY_STYLE_MIN is strictly greater than HUMAN_BLEND — the D-01 "slider cannot reach 0" pin', () => {
    expect(PLAY_STYLE_MIN).toBeGreaterThan(HUMAN_BLEND);
    expect(PLAY_STYLE_MIN).toBe(0.05);
  });

  it('pins the remaining domain constants', () => {
    expect(HUMAN_BLEND).toBe(0);
    expect(ENGINE_BLEND).toBe(1);
    expect(PLAY_STYLE_STEP).toBe(0.05);
    expect(PLAY_STYLE_MAX).toBe(1);
    expect(PLAY_STYLE_DEFAULT_BLEND).toBe(0.5);
  });
});

describe('deriveActivePlayStylePreset', () => {
  it('returns "human" at blend 0', () => {
    expect(deriveActivePlayStylePreset(0)).toBe('human');
  });

  it('returns "engine" at blend 1', () => {
    expect(deriveActivePlayStylePreset(1)).toBe('engine');
  });

  it('returns null at blend 0.5 (custom value, no preset active)', () => {
    expect(deriveActivePlayStylePreset(0.5)).toBeNull();
  });

  it('returns null at the slider floor 0.05 (distinct from the Human regime)', () => {
    expect(deriveActivePlayStylePreset(0.05)).toBeNull();
  });
});

describe('formatPlayStyleSummary', () => {
  it('returns the Human summary line with no numeric blend value at blend 0', () => {
    const summary = formatPlayStyleSummary(0);
    expect(summary).toBe('Human — plays on instinct, no calculation');
    expect(summary).not.toMatch(/\d/);
  });

  it('returns a numeric-first summary containing 0.50 and 50% at blend 0.5', () => {
    const summary = formatPlayStyleSummary(0.5);
    expect(summary).toContain('0.50');
    expect(summary).toContain('50%');
  });

  it('rounds the search percentage for a non-round blend', () => {
    expect(formatPlayStyleSummary(0.05)).toContain('5%');
    expect(formatPlayStyleSummary(1)).toContain('100%');
  });
});
