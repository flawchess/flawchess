// @vitest-environment jsdom
/**
 * Creating or deleting a bookmark must refetch the most-played list: the backend drops the
 * rows that duplicate a bookmark (twin drop, D-06), so a stale list shows a duplicate or hides
 * an opening until the next filter change.
 */

import { describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    positionBookmarksApi: {
      ...actual.positionBookmarksApi,
      create: vi.fn(async () => ({ id: 1 })),
      remove: vi.fn(async () => undefined),
    },
  };
});

import {
  useCreatePositionBookmark,
  useDeletePositionBookmark,
} from '../usePositionBookmarks';

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidate = vi.spyOn(client, 'invalidateQueries');
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { invalidate, wrapper };
}

function invalidatedKeys(spy: ReturnType<typeof setup>['invalidate']): unknown[] {
  return spy.mock.calls.map(([filters]) => (filters as { queryKey: unknown[] }).queryKey[0]);
}

describe('bookmark mutations refresh the most-played list', () => {
  it('create invalidates position-bookmarks and mostPlayedOpenings', async () => {
    const { invalidate, wrapper } = setup();
    const { result } = renderHook(() => useCreatePositionBookmark(), { wrapper });
    await act(async () => {
      result.current.mutate({
        label: 'x',
        target_hash: '1',
        fen: 'f',
        moves: ['e4'],
        color: 'white',
        match_side: 'both',
        is_flipped: false,
      });
    });
    await waitFor(() => expect(invalidatedKeys(invalidate)).toContain('mostPlayedOpenings'));
    expect(invalidatedKeys(invalidate)).toContain('position-bookmarks');
  });

  it('delete invalidates position-bookmarks and mostPlayedOpenings', async () => {
    const { invalidate, wrapper } = setup();
    const { result } = renderHook(() => useDeletePositionBookmark(), { wrapper });
    await act(async () => {
      result.current.mutate(1);
    });
    await waitFor(() => expect(invalidatedKeys(invalidate)).toContain('mostPlayedOpenings'));
    expect(invalidatedKeys(invalidate)).toContain('position-bookmarks');
  });
});
