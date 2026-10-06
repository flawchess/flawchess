// @vitest-environment jsdom
/**
 * Phase 234 plan 02 (FBASK-07, D-03): the Import page shows Hilda's feedback ask
 * instead of the ImportBotBubble whenever the server says the ask is active,
 * for both the welcome and the explore variants.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TooltipProvider } from '@/components/ui/tooltip';

vi.mock('@/hooks/useReadiness', () => ({
  useReadiness: () => ({
    tier1: false,
    tier2: false,
    pendingCount: 0,
    totalCount: 0,
    isLoading: false,
  }),
}));

const COMPLETED_IMPORT_PROFILE = {
  chess_com_username: 'testuser',
  lichess_username: null,
  chess_com_game_count: 100,
  lichess_game_count: 0,
  chess_com_last_sync_at: '2026-01-01T00:00:00Z',
  lichess_last_sync_at: null,
  is_guest: false,
  is_superuser: false,
  email: 'test@example.com',
  active_days: 7,
};

const profileState: { data: Record<string, unknown> } = { data: COMPLETED_IMPORT_PROFILE };

vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: () => ({ data: profileState.data, isLoading: false }),
}));

// The real bubble is covered by FeedbackAskBubble.test.tsx; a stub keeps this a page-level switch test.
vi.mock('@/components/feedback/FeedbackAskBubble', () => ({
  FeedbackAskBubble: ({ surface, activeDays }: { surface: string; activeDays: number }) => (
    <div data-testid={`feedback-ask-${surface}`} data-active-days={String(activeDays)} />
  ),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    token: 'test-token',
    logoutForPromotion: vi.fn(),
  }),
}));

vi.mock('@/hooks/useImport', () => ({
  useImportTrigger: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useImportPolling: () => ({ data: null }),
}));

vi.mock('@/hooks/useImportSettings', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useImportSettings')>(
    '@/hooks/useImportSettings',
  );
  return {
    ...actual,
    useImportSettings: () => ({
      data: {
        tc_bullet: false,
        tc_blitz: true,
        tc_rapid: true,
        tc_classical: true,
        game_cap: 1000,
        imported_counts: {},
      },
      isLoading: false,
      isError: false,
    }),
    useUpdateImportSettings: () => ({ mutate: vi.fn() }),
  };
});

vi.mock('@/hooks/useEvalCoverage', () => ({
  useEvalCoverage: () => ({
    pendingCount: 0,
    totalCount: 0,
    pct: 100,
    isPending: false,
    isLoading: false,
  }),
}));

const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/api/client', () => ({
  apiClient: { delete: vi.fn(), post: vi.fn() },
}));

afterEach(() => {
  cleanup();
  profileState.data = COMPLETED_IMPORT_PROFILE;
  mockNavigate.mockReset();
});

import { ImportPage } from '../Import';

// ImportPage mounts PasteModal, whose useSavePastedGame needs a real QueryClientProvider
// (see Import.queuedState.test.tsx).
function renderImport() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TooltipProvider>
          <ImportPage onImportStarted={vi.fn()} activeJobIds={[]} onJobDismissed={vi.fn()} />
        </TooltipProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const ASK_ACTIVE = { feedback_ask: { active: true } };
const ASK_INACTIVE = { feedback_ask: { active: false } };

describe('Import page feedback ask (FBASK-07, D-03)', () => {
  it('shows the ask instead of the explore bubble after a completed import', () => {
    profileState.data = { ...COMPLETED_IMPORT_PROFILE, ...ASK_ACTIVE };

    renderImport();

    const ask = screen.getByTestId('feedback-ask-import');
    expect(ask.getAttribute('data-active-days')).toBe('7');
    expect(screen.queryByTestId('import-bot-bubble')).toBeNull();
  });

  it('shows the ask instead of the welcome bubble before any completed import', () => {
    profileState.data = {
      ...COMPLETED_IMPORT_PROFILE,
      chess_com_last_sync_at: null,
      ...ASK_ACTIVE,
    };

    renderImport();

    expect(screen.getByTestId('feedback-ask-import')).not.toBeNull();
    expect(screen.queryByTestId('import-bot-bubble')).toBeNull();
  });

  it('renders the explore bubble when the ask is inactive', () => {
    profileState.data = { ...COMPLETED_IMPORT_PROFILE, ...ASK_INACTIVE };

    renderImport();

    expect(screen.getByTestId('import-bot-bubble').getAttribute('data-variant')).toBe('explore');
    expect(screen.queryByTestId('feedback-ask-import')).toBeNull();
  });

  it('renders the bot bubble for a profile without the feedback_ask field', () => {
    profileState.data = COMPLETED_IMPORT_PROFILE;

    renderImport();

    expect(screen.getByTestId('import-bot-bubble')).not.toBeNull();
    expect(screen.queryByTestId('feedback-ask-import')).toBeNull();
  });
});
