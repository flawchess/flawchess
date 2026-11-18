// @vitest-environment jsdom
/**
 * useBlunderCheckSession.test.ts: composing and finishing a blunder-check session refresh the
 * shared train progress query, so the Today card row (pending, in progress, done) and the nav
 * badge update without a reload (Phase 251 plan 13).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactNode } from 'react';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...actual,
    blunderCheckApi: {
      ...actual.blunderCheckApi,
      getOpenSession: vi.fn().mockResolvedValue(null),
      composeOrResumeSession: vi.fn().mockResolvedValue({ session_id: 1 }),
      finishSession: vi.fn().mockResolvedValue({ session_id: 1 }),
    },
  };
});

import { useBlunderCheckSession } from '@/hooks/useBlunderCheckSession';
import { TRAIN_PROGRESS_QUERY_KEY } from '@/hooks/useTrainProgress';

afterEach(() => {
  vi.clearAllMocks();
});

function setup() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const invalidate = vi.spyOn(client, 'invalidateQueries');
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client }, children);
  const hook = renderHook(() => useBlunderCheckSession(), { wrapper });
  return { hook, invalidate };
}

function invalidatedProgress(invalidate: ReturnType<typeof setup>['invalidate']): boolean {
  return invalidate.mock.calls.some(
    ([filters]) => JSON.stringify(filters?.queryKey) === JSON.stringify(TRAIN_PROGRESS_QUERY_KEY),
  );
}

describe('useBlunderCheckSession progress refresh', () => {
  it('compose invalidates the train progress query', async () => {
    const { hook, invalidate } = setup();
    expect(invalidatedProgress(invalidate)).toBe(false);

    await act(async () => {
      await hook.result.current.compose.mutateAsync();
    });

    await waitFor(() => expect(invalidatedProgress(invalidate)).toBe(true));
  });

  it('finish invalidates the train progress query', async () => {
    const { hook, invalidate } = setup();

    await act(async () => {
      await hook.result.current.finish.mutateAsync(1);
    });

    await waitFor(() => expect(invalidatedProgress(invalidate)).toBe(true));
  });
});
