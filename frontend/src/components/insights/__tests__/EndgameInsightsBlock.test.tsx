// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import type { UseMutationResult } from '@tanstack/react-query';
import type { FilterState } from '@/components/filters/FilterPanel';
import type {
  EndgameInsightsResponse,
  InsightsAxiosError,
} from '@/types/insights';
import { EndgameInsightsBlock } from '../EndgameInsightsBlock';

// Vitest 4 does not auto-cleanup RTL mounts — rendered DOM from a previous
// test bleeds into the next one's screen queries if we don't explicitly unmount.
afterEach(() => {
  cleanup();
});

// Mock useActiveJobs — v8 button gating reads active imports. Default: no
// active jobs so the block renders its enabled happy path.
vi.mock('@/hooks/useImport', () => ({
  useActiveJobs: vi.fn(() => ({ data: [] })),
}));

// Mock useUserProfile — block reads the email to scope the per-user
// "Generate Insights used" flag. Tests don't care about the value, just that
// the component doesn't crash without a QueryClientProvider.
vi.mock('@/hooks/useUserProfile', () => ({
  useUserProfile: vi.fn(() => ({ data: { email: 'test@example.com' } })),
}));

// Stub the Tooltip primitive so blocked-state renders don't need a
// TooltipProvider wrapper in tests. The component under test only uses
// Tooltip for accessibility hints; the wrapper's internal Radix context is
// not relevant to rendering assertions.
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: ReactNode }) => children,
}));
import type { ReactNode } from 'react';

const BASE_FILTERS: FilterState = {
  matchSide: 'both',
  timeControls: null,
  platforms: null,
  rated: null,
  opponentType: 'human',
  opponentStrength: { min: null, max: null },
  recency: null,
  color: 'white',
};

function makeMutation(
  overrides: Partial<{
    isPending: boolean;
    isError: boolean;
    error: InsightsAxiosError | null;
  }> = {},
): UseMutationResult<EndgameInsightsResponse, InsightsAxiosError, FilterState> {
  return {
    isPending: overrides.isPending ?? false,
    isError: overrides.isError ?? false,
    error: overrides.error ?? null,
    // Stub the rest of the UseMutationResult surface — component only reads the three above.
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    reset: vi.fn(),
    data: undefined,
    variables: undefined,
    status: 'idle',
    isIdle: true,
    isSuccess: false,
    isPaused: false,
    failureCount: 0,
    failureReason: null,
    submittedAt: 0,
    context: undefined,
  } as unknown as UseMutationResult<EndgameInsightsResponse, InsightsAxiosError, FilterState>;
}

const RESPONSE_FRESH: EndgameInsightsResponse = {
  report: {
    player_profile:
      'Active rapid player around 1500 Elo, range 1200-1600 over the last two years.',
    overview: 'You converted winning endgames at 62% in the last 90 days.',
    recommendations: [
      'Try drilling pawn endgames against an engine.',
      'Review your last few losses on time.',
    ],
    sections: [
      { section_id: 'overall', headline: 'Strong headline', bullets: ['bullet one'] },
    ],
    model_used: 'anthropic:claude-haiku-4-5-20251001',
    prompt_version: 'endgame_v9',
  },
  status: 'fresh',
  stale_filters: null,
};

describe('EndgameInsightsBlock', () => {
  it('renders hero state with Generate button when idle and no report', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={null}
        mutation={makeMutation()}
        onGenerate={vi.fn()}
      />,
    );
    const generate = screen.getByTestId('btn-generate-insights');
    expect(generate.textContent).toContain('Generate Insights');
    expect(
      screen.queryByText(/Generate a player profile, endgame data analysis, and recommendations/),
    ).not.toBeNull();
    expect(screen.queryByTestId('insights-skeleton')).toBeNull();
    expect(screen.queryByTestId('insights-overview')).toBeNull();
  });

  it('renders skeleton while pending with no prior report', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={null}
        mutation={makeMutation({ isPending: true })}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('insights-skeleton')).not.toBeNull();
    expect(screen.queryByTestId('btn-generate-insights')).toBeNull();
  });

  it('renders overview + Generate Insights button when report landed', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={RESPONSE_FRESH}
        mutation={makeMutation()}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.getByTestId('insights-overview').textContent).toContain(
      'You converted winning endgames at 62% in the last 90 days.',
    );
    expect(screen.getByTestId('btn-generate-insights').textContent).toContain('Generate Insights');
    expect(screen.queryByTestId('insights-stale-banner')).toBeNull();
  });

  it('v9: renders player profile, data analysis, and recommendations as stacked cards', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={RESPONSE_FRESH}
        mutation={makeMutation()}
        onGenerate={vi.fn()}
      />,
    );
    const profile = screen.getByTestId('insights-player-profile');
    expect(profile.textContent).toContain('Player Profile');
    expect(profile.textContent).toContain('Active rapid player around 1500 Elo');
    const overview = screen.getByTestId('insights-overview');
    expect(overview.textContent).toContain('Data Analysis');
    expect(overview.textContent).toContain('You converted winning endgames at 62%');
    const recs = screen.getByTestId('insights-recommendations');
    expect(recs.textContent).toContain('Recommendations');
    expect(recs.textContent).toContain('Try drilling pawn endgames against an engine.');
    expect(recs.textContent).toContain('Review your last few losses on time.');
  });

  it('hides overview paragraph when empty string (BETA-02)', () => {
    const response: EndgameInsightsResponse = {
      ...RESPONSE_FRESH,
      report: { ...RESPONSE_FRESH.report, overview: '' },
    };
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={response}
        mutation={makeMutation()}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('insights-overview')).toBeNull();
    expect(screen.queryByTestId('btn-generate-insights')).not.toBeNull();
  });

  it('renders stale banner on stale_rate_limited', () => {
    const stale: EndgameInsightsResponse = { ...RESPONSE_FRESH, status: 'stale_rate_limited' };
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={stale}
        mutation={makeMutation()}
        onGenerate={vi.fn()}
      />,
    );
    const banner = screen.getByTestId('insights-stale-banner');
    expect(banner.textContent).toMatch(/Showing your most recent insights/);
    // Fallback copy — retry_after_seconds not surfaced in 200 envelope.
    expect(banner.textContent).toMatch(/try again in a moment/);
  });

  it('does NOT render a cache-mismatch indicator (parent gates the rendered prop)', () => {
    // Filter-mismatch gating now lives in the parent (Endgames.tsx) — it only
    // passes `rendered` when the cached report matches current filters. The
    // component therefore has no notion of "outdated" and never shows that
    // indicator.
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={RESPONSE_FRESH}
        mutation={makeMutation()}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('insights-outdated-indicator')).toBeNull();
  });

  it('renders error state with locked copy and Try again button', () => {
    const axiosError = {
      isAxiosError: true,
      response: { data: { error: 'provider_error', retry_after_seconds: null } },
    } as InsightsAxiosError;
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={null}
        mutation={makeMutation({ isError: true, error: axiosError })}
        onGenerate={vi.fn()}
      />,
    );
    const errorBlock = screen.getByTestId('insights-error');
    expect(errorBlock.textContent).toContain("Couldn't generate insights.");
    expect(errorBlock.textContent).toContain('Please try again in a moment.');
    expect(screen.getByTestId('btn-insights-retry').textContent).toContain('Try again');
    expect(errorBlock.textContent).not.toMatch(/Try again in ~/);
  });

  it('renders "Try again in ~N min." on 429 with retry_after_seconds', () => {
    const axiosError = {
      isAxiosError: true,
      response: { data: { error: 'rate_limit_exceeded', retry_after_seconds: 180 } },
    } as InsightsAxiosError;
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={null}
        mutation={makeMutation({ isError: true, error: axiosError })}
        onGenerate={vi.fn()}
      />,
    );
    // 180 / 60 = 3 min
    expect(screen.getByTestId('insights-error').textContent).toContain('Try again in ~3 min.');
  });

  it('minute rounding: 0s → 1 min; 45s → 1 min; 60s → 1 min; 61s → 2 min', () => {
    for (const [seconds, expected] of [
      [0, 1],
      [45, 1],
      [60, 1],
      [61, 2],
    ] as const) {
      const axiosError = {
        isAxiosError: true,
        response: { data: { error: 'rate_limit_exceeded', retry_after_seconds: seconds } },
      } as InsightsAxiosError;
      const { unmount } = render(
        <EndgameInsightsBlock
          appliedFilters={BASE_FILTERS}
          rendered={null}
            mutation={makeMutation({ isError: true, error: axiosError })}
          onGenerate={vi.fn()}
        />,
      );
      expect(screen.getByTestId('insights-error').textContent).toContain(
        `Try again in ~${expected} min.`,
      );
      unmount();
    }
  });
});
