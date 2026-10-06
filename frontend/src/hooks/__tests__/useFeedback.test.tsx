// @vitest-environment jsdom
/**
 * useFeedback.test.tsx — Phase 234 plan 02 (SEED-191 #8): any successful feedback
 * submission invalidates the cached profile so the milestone ask can end; a
 * failed submission leaves it untouched.
 */
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { useFeedback } from '@/hooks/useFeedback';
import { USER_PROFILE_QUERY_KEY } from '@/hooks/useUserProfile';
import type { FeedbackRequest } from '@/types/feedback';

const REQUEST: FeedbackRequest = { text: 'An idea', page_url: '/library/import' };

let postSpy: ReturnType<typeof vi.spyOn>;
let queryClient: QueryClient;

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  queryClient.setQueryData(USER_PROFILE_QUERY_KEY, { feedback_ask: { active: true } });
  postSpy = vi.spyOn(apiClient, 'post');
});

afterEach(() => {
  cleanup();
  postSpy.mockRestore();
});

describe('useFeedback', () => {
  it('invalidates the cached profile after a successful submission', async () => {
    postSpy.mockResolvedValue({ data: { id: 1, created_at: '2026-10-05T00:00:00Z' } });
    const { result } = renderHook(() => useFeedback(), { wrapper });
    expect(queryClient.getQueryState(USER_PROFILE_QUERY_KEY)?.isInvalidated).toBe(false);

    await act(async () => {
      result.current.mutate(REQUEST);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(queryClient.getQueryState(USER_PROFILE_QUERY_KEY)?.isInvalidated).toBe(true);
  });

  it('leaves the cached profile untouched when the submission fails', async () => {
    postSpy.mockRejectedValue(new Error('boom'));
    const { result } = renderHook(() => useFeedback(), { wrapper });

    await act(async () => {
      result.current.mutate(REQUEST);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(queryClient.getQueryState(USER_PROFILE_QUERY_KEY)?.isInvalidated).toBe(false);
  });
});
