// @vitest-environment jsdom
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useIsTrainSideLayout } from '@/hooks/useIsDesktop';
import {
  DESKTOP_FRAME_QUERY,
  PORTRAIT_FOLDABLE_QUERY,
  TRAIN_SIDE_LAYOUT_QUERY,
} from '@/lib/trainSideLayout';

// jsdom's import.meta.url is not a file URL, so resolve from the vitest cwd (the frontend root).
const INDEX_CSS = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf-8');

const originalMatchMedia = window.matchMedia;

function stubMatchMedia(matchingQuery: string | null): ReturnType<typeof vi.fn> {
  const stub = vi.fn((query: string) => ({
    matches: query === matchingQuery,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  Object.defineProperty(window, 'matchMedia', { value: stub, writable: true, configurable: true });
  return stub;
}

afterEach(() => {
  Object.defineProperty(window, 'matchMedia', {
    value: originalMatchMedia,
    writable: true,
    configurable: true,
  });
});

describe('trainside layout gate', () => {
  it('index.css declares the trainside variant with the exact shared query', () => {
    expect(INDEX_CSS).toContain('@custom-variant trainside {');
    expect(INDEX_CSS).toContain(`@media ${TRAIN_SIDE_LAYOUT_QUERY} {`);
  });

  it('index.css declares the foldportrait variant with the shared query', () => {
    expect(INDEX_CSS).toContain(`@custom-variant foldportrait (@media ${PORTRAIT_FOLDABLE_QUERY});`);
  });

  it('index.css declares the deskframe variant with the shared query, the complement of the phone type scale', () => {
    expect(INDEX_CSS).toContain('@custom-variant deskframe {');
    expect(INDEX_CSS).toContain(`@media ${DESKTOP_FRAME_QUERY} {`);
    expect(INDEX_CSS).toContain(
      '@media (max-width: 639.98px), (max-width: 767.98px) and (orientation: portrait) {',
    );
  });

  it('pins the approved breakpoints', () => {
    expect(TRAIN_SIDE_LAYOUT_QUERY).toBe(
      '(min-width: 1024px), (min-width: 640px) and (orientation: landscape)',
    );
  });

  it('useIsTrainSideLayout reads the shared query and returns true when it matches', () => {
    const stub = stubMatchMedia(TRAIN_SIDE_LAYOUT_QUERY);
    const { result } = renderHook(() => useIsTrainSideLayout());
    expect(result.current).toBe(true);
    expect(stub).toHaveBeenCalledWith(TRAIN_SIDE_LAYOUT_QUERY);
  });

  it('useIsTrainSideLayout is false when the query does not match', () => {
    stubMatchMedia(null);
    const { result } = renderHook(() => useIsTrainSideLayout());
    expect(result.current).toBe(false);
  });
});
