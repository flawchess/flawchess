import { describe, it, expect } from 'vitest';
import { resolveMatchSide } from './api';

describe('resolveMatchSide', () => {
  // ── mine ──────────────────────────────────────────────────────────────────
  it('mine + white => white', () => {
    expect(resolveMatchSide('mine', 'white')).toBe('white');
  });

  it('mine + black => black', () => {
    expect(resolveMatchSide('mine', 'black')).toBe('black');
  });

  // ── opponent ──────────────────────────────────────────────────────────────
  it('opponent + white => black (opponent pieces when user plays white)', () => {
    expect(resolveMatchSide('opponent', 'white')).toBe('black');
  });

  it('opponent + black => white (opponent pieces when user plays black)', () => {
    expect(resolveMatchSide('opponent', 'black')).toBe('white');
  });

  // ── both ──────────────────────────────────────────────────────────────────
  it('both + white => full', () => {
    expect(resolveMatchSide('both', 'white')).toBe('full');
  });

  it('both + black => full', () => {
    expect(resolveMatchSide('both', 'black')).toBe('full');
  });
});
