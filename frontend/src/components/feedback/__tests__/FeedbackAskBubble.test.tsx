// @vitest-environment jsdom
/**
 * FeedbackAskBubble.test.tsx — Phase 234 plan 02. Real QueryClientProvider,
 * bubble + useFeedbackAsk + a host that mounts the bubble only while
 * feedbackAskDays(profile) is non-null (exactly how the surfaces use it).
 * The network is stubbed through apiClient.post. Plan 03 adds the app-level
 * FeedbackAskModalHost beside the bubble host: "Sure!" opens it, and it must
 * outlive the bubble.
 */
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';

const trackFeature = vi.fn();
vi.mock('@/lib/analytics', async () => {
  const actual = await vi.importActual<typeof import('@/lib/analytics')>('@/lib/analytics');
  return {
    ...actual,
    trackFeature: (...args: unknown[]) => trackFeature(...args),
  };
});

import { apiClient } from '@/api/client';
import { FeedbackAskBubble } from '@/components/feedback/FeedbackAskBubble';
import { FeedbackAskModalHost } from '@/components/feedback/FeedbackAskModalHost';
import { USER_PROFILE_QUERY_KEY, useUserProfile } from '@/hooks/useUserProfile';
import {
  FEEDBACK_ASK_PLACEHOLDER,
  closeFeedbackAskModal,
  feedbackAskCopy,
  feedbackAskDays,
} from '@/lib/feedbackAsk';
import type { UserProfile } from '@/types/users';

const ACTIVE_DAYS = 7;

function makeProfile(active: boolean): UserProfile {
  return {
    email: 'a@b.c',
    is_superuser: false,
    is_guest: false,
    chess_com_username: null,
    lichess_username: null,
    created_at: '2026-01-01T00:00:00Z',
    last_login: null,
    chess_com_game_count: 0,
    lichess_game_count: 0,
    chess_com_last_sync_at: null,
    lichess_last_sync_at: null,
    impersonation: null,
    beta_enabled: false,
    leaderboard_hidden: false,
    current_strength: null,
    active_days: ACTIVE_DAYS,
    feedback_ask: { active },
  };
}

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

function Host(): ReactNode {
  const { data: profile } = useUserProfile();
  const days = feedbackAskDays(profile);
  return days === null ? null : <FeedbackAskBubble surface="import" activeDays={days} />;
}

let postSpy: ReturnType<typeof vi.spyOn>;
let lastClient: QueryClient;

/** Resolves view with active:true and snooze/done with active:false unless a test overrides it. */
function stubPost(overrides: Partial<Record<string, Promise<{ data: { active: boolean } }>>> = {}): void {
  postSpy.mockImplementation(async (url: string, body?: unknown) => {
    // The feedback modal's own submission (POST /feedback carries no `action`).
    if (url === '/feedback') return { data: { id: 1, created_at: '2026-10-06T00:00:00Z' } };
    const action = (body as { action: string }).action;
    const override = overrides[action];
    if (override) return override;
    return { data: { active: action === 'view' } };
  });
}

function renderHost(profile: UserProfile = makeProfile(true)): QueryClient {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  queryClient.setQueryData(USER_PROFILE_QUERY_KEY, profile);
  lastClient = queryClient;
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }
  render(
    <>
      <Host />
      <FeedbackAskModalHost />
    </>,
    { wrapper: Wrapper },
  );
  return queryClient;
}

function cachedAsk(): { active: boolean } | undefined {
  return lastClient.getQueryData<UserProfile>(USER_PROFILE_QUERY_KEY)?.feedback_ask;
}

function actionsPosted(): string[] {
  return postSpy.mock.calls.map((call: unknown[]) => (call[1] as { action: string }).action);
}

beforeEach(() => {
  postSpy = vi.spyOn(apiClient, 'post');
  stubPost();
});

afterEach(() => {
  cleanup();
  // Module store: reset so one test's open modal cannot leak into the next.
  closeFeedbackAskModal();
  postSpy.mockRestore();
  trackFeature.mockReset();
});

describe('FeedbackAskBubble', () => {
  it('renders Hilda with the day-count copy and both buttons', () => {
    renderHost();

    expect(screen.getByTestId('feedback-ask-import')).not.toBeNull();
    expect(screen.getByText('Hilda the Hippo')).not.toBeNull();
    const copy = screen.getByTestId('feedback-ask-copy');
    expect(copy.textContent).toBe(feedbackAskCopy(ACTIVE_DAYS));
    expect(copy.textContent).toContain('for 7 days now');
    expect(screen.getByTestId('btn-feedback-ask-later-import').textContent).toBe('Maybe later');
    expect(screen.getByTestId('btn-feedback-ask-sure-import').textContent).toBe('Sure!');
  });

  it('posts one view on mount, tracks nothing, and does not repost on rerender', async () => {
    const client = renderHost();

    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));
    expect(postSpy).toHaveBeenCalledWith('/users/me/feedback-ask', { action: 'view' });
    expect(trackFeature).not.toHaveBeenCalled();

    // A profile re-render (poll tick, cache write) must not report a second view.
    await act(async () => {
      client.setQueryData(USER_PROFILE_QUERY_KEY, makeProfile(true));
    });
    expect(postSpy).toHaveBeenCalledTimes(1);
    // The view response never patches the cache.
    expect(cachedAsk()).toEqual({ active: true });
  });

  it('Maybe later tracks, hides the bubble before the snooze resolves, then keeps the server answer', async () => {
    const snooze = deferred<{ data: { active: boolean } }>();
    stubPost({ snooze: snooze.promise });
    renderHost();
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByTestId('btn-feedback-ask-later-import'));

    expect(trackFeature).toHaveBeenCalledWith('action', { target: 'feedback-ask-later' });
    // Optimistic hide: gone while the snooze request is still in flight.
    await waitFor(() => expect(screen.queryByTestId('feedback-ask-import')).toBeNull());
    await waitFor(() => expect(actionsPosted()).toEqual(['view', 'snooze']));

    await act(async () => {
      snooze.resolve({ data: { active: false } });
    });
    expect(cachedAsk()).toEqual({ active: false });
    expect(screen.queryByTestId('feedback-ask-import')).toBeNull();
  });

  it('Sure tracks, posts done and removes the bubble', async () => {
    renderHost();
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByTestId('btn-feedback-ask-sure-import'));

    expect(trackFeature).toHaveBeenCalledWith('action', { target: 'feedback-ask-sure' });
    await waitFor(() => expect(actionsPosted()).toEqual(['view', 'done']));
    await waitFor(() => expect(screen.queryByTestId('feedback-ask-import')).toBeNull());
    expect(cachedAsk()).toEqual({ active: false });
  });

  it('a view that resolves active after Maybe later does not bring the bubble back', async () => {
    const view = deferred<{ data: { active: boolean } }>();
    const snooze = deferred<{ data: { active: boolean } }>();
    stubPost({ view: view.promise, snooze: snooze.promise });
    renderHost();
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));

    // The view is still in flight; the user dismisses immediately.
    fireEvent.click(screen.getByTestId('btn-feedback-ask-later-import'));
    await waitFor(() => expect(screen.queryByTestId('feedback-ask-import')).toBeNull());

    await act(async () => {
      view.resolve({ data: { active: true } });
    });
    // The snooze request is now in flight (and still unresolved), so only the
    // view response could have touched the cache: it must not have.
    await waitFor(() => expect(actionsPosted()).toEqual(['view', 'snooze']));
    expect(screen.queryByTestId('feedback-ask-import')).toBeNull();
    expect(cachedAsk()).toEqual({ active: false });

    await act(async () => {
      snooze.resolve({ data: { active: false } });
    });
    expect(cachedAsk()).toEqual({ active: false });
  });
});

describe('FeedbackAskBubble "Sure!" modal (app-level host)', () => {
  it('Sure opens the feedback modal with the ask placeholder', async () => {
    renderHost();
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));
    expect(screen.queryByTestId('feedback-modal')).toBeNull();

    fireEvent.click(screen.getByTestId('btn-feedback-ask-sure-import'));

    const textarea = await screen.findByTestId('feedback-text');
    expect(screen.getByTestId('feedback-modal')).not.toBeNull();
    expect(textarea.getAttribute('placeholder')).toBe(FEEDBACK_ASK_PLACEHOLDER);
    expect(FEEDBACK_ASK_PLACEHOLDER).toBe("What's one thing you'd change or add?");
  });

  it('the modal and a typed draft survive the bubble unmounting on the done response', async () => {
    const done = deferred<{ data: { active: boolean } }>();
    stubPost({ done: done.promise });
    renderHost();
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByTestId('btn-feedback-ask-sure-import'));
    const textarea = await screen.findByTestId('feedback-text');
    fireEvent.change(textarea, { target: { value: 'Add a puzzle rush mode' } });

    // The done response patches the cached profile to inactive: the bubble unmounts.
    await act(async () => {
      done.resolve({ data: { active: false } });
    });
    await waitFor(() => expect(screen.queryByTestId('feedback-ask-import')).toBeNull());

    expect(screen.getByTestId('feedback-modal')).not.toBeNull();
    expect((screen.getByTestId('feedback-text') as HTMLTextAreaElement).value).toBe(
      'Add a puzzle rush mode',
    );
  });

  it('submitting POSTs /feedback with source milestone_ask', async () => {
    renderHost();
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByTestId('btn-feedback-ask-sure-import'));
    fireEvent.change(await screen.findByTestId('feedback-text'), {
      target: { value: 'Add a puzzle rush mode' },
    });
    fireEvent.click(screen.getByTestId('btn-feedback-submit'));

    await waitFor(() =>
      expect(postSpy).toHaveBeenCalledWith(
        '/feedback',
        expect.objectContaining({ text: 'Add a puzzle rush mode', source: 'milestone_ask' }),
      ),
    );
  });

  it('Cancel closes the modal', async () => {
    renderHost();
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByTestId('btn-feedback-ask-sure-import'));
    await screen.findByTestId('feedback-modal');
    fireEvent.click(screen.getByTestId('btn-feedback-cancel'));

    await waitFor(() => expect(screen.queryByTestId('feedback-modal')).toBeNull());
  });
});
