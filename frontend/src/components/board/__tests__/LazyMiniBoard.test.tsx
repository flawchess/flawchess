// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { LazyMiniBoard } from '../LazyMiniBoard';

describe('LazyMiniBoard', () => {
  it('exports LazyMiniBoard as a named export', () => {
    expect(typeof LazyMiniBoard).toBe('function');
  });
});
