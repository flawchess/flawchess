import { describe, it, expect } from 'vitest';
import { formatTimeControl } from '../formatTimeControl';

describe('formatTimeControl', () => {
  it('renders daily/correspondence as Nd', () => {
    expect(formatTimeControl('1/259200')).toBe('3d');
    expect(formatTimeControl('1/86400')).toBe('1d');
  });

  it('renders minute+ base with increment as min+inc', () => {
    expect(formatTimeControl('180+2')).toBe('3+2');
    expect(formatTimeControl('600+0')).toBe('10+0');
  });

  it('renders hyperbullet base (with increment) in seconds, not "0"', () => {
    expect(formatTimeControl('30+0')).toBe('30s');
    expect(formatTimeControl('15+1')).toBe('15s+1');
  });

  it('renders minute+ base without increment as minutes', () => {
    expect(formatTimeControl('600')).toBe('10');
    expect(formatTimeControl('60')).toBe('1');
  });

  it('renders sub-minute base without increment in seconds', () => {
    expect(formatTimeControl('30')).toBe('30s');
    expect(formatTimeControl('45')).toBe('45s');
  });
});
