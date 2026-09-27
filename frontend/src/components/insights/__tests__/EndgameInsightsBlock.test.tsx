// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import type { UseMutationResult } from '@tanstack/react-query';
import { DEFAULT_FILTERS, type FilterState } from '@/components/filters/FilterPanel';
import type {
  EndgameInsightsResponse,
  InsightsAxiosError,
} from '@/types/insights';
import { EndgameInsightsBlock } from '../EndgameInsightsBlock';
import {
  BLOCKED_REASON_BUBBLE_COPY,
  INSIGHTS_BUBBLE_COPY,
} from '../endgameInsightsCopy';
import { useActiveJobs } from '@/hooks/useImport';

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

// FLAWCHESS-AG: the unblocked baseline IS DEFAULT_FILTERS — getBlockedReason
// compares against it field by field, so a hand-written literal silently
// drifts into "blocked" the moment a default changes (SEED-163 2a flipped
// `rated` null -> true) and every gating assertion below stops testing the
// state real users are actually in.
const BASE_FILTERS: FilterState = DEFAULT_FILTERS;

/** DEFAULT_FILTERS with one field pushed off its default → button blocked. */
const RATED_FILTERED: FilterState = { ...DEFAULT_FILTERS, rated: false };

/** Default filters with a custom (non-preset) opponent-strength range. */
const CUSTOM_STRENGTH: FilterState = {
  ...DEFAULT_FILTERS,
  opponentStrength: { min: -37, max: 142 },
};

const PROVIDER_ERROR = {
  isAxiosError: true,
  response: { data: { error: 'provider_error' } },
} as InsightsAxiosError;

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
};

describe('EndgameInsightsBlock', () => {
  it('renders Shelly bubble with Generate button when idle and no report', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={null}
        mutation={makeMutation()}
        onGenerate={vi.fn()}
      />,
    );
    const bubble = screen.getByTestId('insights-bubble');
    expect(bubble.getAttribute('data-status')).toBe('idle');
    expect(screen.getByTestId('train-bot-name').textContent).toBe('Shelly the Turtle');
    expect(screen.getByTestId('insights-bubble-copy').textContent).toBe(INSIGHTS_BUBBLE_COPY.idle);
    const generate = screen.getByTestId<HTMLButtonElement>('btn-generate-insights');
    expect(generate.textContent).toContain('Generate Insights');
    expect(generate.disabled).toBe(false);
    expect(screen.queryByTestId('insights-blocked-reason')).toBeNull();
    // No report card while there is no report.
    expect(screen.queryByTestId('insights-block')).toBeNull();
  });

  it('pending with no prior report: bubble shows progress copy and a disabled busy button', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={null}
        mutation={makeMutation({ isPending: true })}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.getByTestId('insights-bubble').getAttribute('data-status')).toBe('pending');
    expect(screen.getByTestId('insights-bubble-copy').textContent).toBe(
      INSIGHTS_BUBBLE_COPY.pending,
    );
    const generate = screen.getByTestId<HTMLButtonElement>('btn-generate-insights');
    expect(generate.disabled).toBe(true);
    expect(generate.getAttribute('aria-busy')).toBe('true');
    expect(screen.queryByTestId('generate-insights-notification-dot')).toBeNull();
  });

  it.each([
    ['filters-not-default', RATED_FILTERED],
    ['custom-opponent-strength', CUSTOM_STRENGTH],
  ] as const)('blocked (%s): Shelly says why and Generate is disabled', (reason, filters) => {
    const onGenerate = vi.fn();
    render(
      <EndgameInsightsBlock
        appliedFilters={filters}
        rendered={null}
        mutation={makeMutation()}
        onGenerate={onGenerate}
      />,
    );
    expect(screen.getByTestId('insights-blocked-reason').textContent).toBe(
      BLOCKED_REASON_BUBBLE_COPY[reason],
    );
    const generate = screen.getByTestId<HTMLButtonElement>('btn-generate-insights');
    expect(generate.disabled).toBe(true);
    fireEvent.click(generate);
    expect(onGenerate).not.toHaveBeenCalled();
  });

  it('blocked by a running import: Shelly asks to wait', () => {
    vi.mocked(useActiveJobs).mockReturnValueOnce({ data: [{}] } as ReturnType<typeof useActiveJobs>);
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={null}
        mutation={makeMutation()}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.getByTestId('insights-blocked-reason').textContent).toBe(
      BLOCKED_REASON_BUBBLE_COPY['import-running'],
    );
    expect(screen.getByTestId<HTMLButtonElement>('btn-generate-insights').disabled).toBe(true);
  });

  it('hides the bubble once a report is rendered', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={RESPONSE_FRESH}
        mutation={makeMutation()}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('insights-bubble')).toBeNull();
    expect(screen.queryByTestId('insights-block')).not.toBeNull();
  });

  it('regenerating keeps the report card with its inline spinner (no bubble)', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={RESPONSE_FRESH}
        mutation={makeMutation({ isPending: true })}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('insights-bubble')).toBeNull();
    expect(screen.queryByTestId('insights-overview')).not.toBeNull();
    expect(screen.getByTestId('btn-generate-insights').getAttribute('aria-busy')).toBe('true');
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
    const studyLink = screen.getByTestId('insights-rec-endgame-study-link');
    expect(studyLink.getAttribute('href')).toBe('https://lichess.org/study/mtiahamI');
    expect(studyLink.getAttribute('target')).toBe('_blank');
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

  it('renders error state in the bubble with Try again', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={null}
        mutation={makeMutation({ isError: true, error: PROVIDER_ERROR })}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.getByTestId('insights-bubble').getAttribute('data-status')).toBe('error');
    const errorBlock = screen.getByTestId('insights-error');
    expect(errorBlock.getAttribute('role')).toBe('alert');
    expect(errorBlock.textContent).toContain(INSIGHTS_BUBBLE_COPY.error);
    const retry = screen.getByTestId<HTMLButtonElement>('btn-insights-retry');
    expect(retry.textContent).toContain('Try again');
    expect(retry.disabled).toBe(false);
    expect(screen.queryByTestId('btn-generate-insights')).toBeNull();
  });

  it('error outranks a rendered report (failed regenerate falls back to the bubble)', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={BASE_FILTERS}
        rendered={RESPONSE_FRESH}
        mutation={makeMutation({ isError: true, error: PROVIDER_ERROR })}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('insights-error')).not.toBeNull();
    expect(screen.queryByTestId('insights-overview')).toBeNull();
  });

  it('FLAWCHESS-AG: Try again is disabled while a filter blocks generation', () => {
    // The error state was the one path around getBlockedReason: once any
    // failure rendered it, Try again stayed enabled and kept POSTing requests
    // the router rejects with 400 filters_not_supported.
    const onGenerate = vi.fn();
    render(
      <EndgameInsightsBlock
        appliedFilters={RATED_FILTERED}
        rendered={null}
        mutation={makeMutation({ isError: true, error: PROVIDER_ERROR })}
        onGenerate={onGenerate}
      />,
    );
    const retry = screen.getByTestId<HTMLButtonElement>('btn-insights-retry');
    expect(retry.disabled).toBe(true);
    fireEvent.click(retry);
    expect(onGenerate).not.toHaveBeenCalled();
    // Shelly says why, instead of a hover tooltip phones never show.
    expect(screen.getByTestId('insights-blocked-reason').textContent).toBe(
      BLOCKED_REASON_BUBBLE_COPY['filters-not-default'],
    );
  });

  it('enables Generate Insights on the default filter state (FLAWCHESS-AG)', () => {
    render(
      <EndgameInsightsBlock
        appliedFilters={DEFAULT_FILTERS}
        rendered={null}
        mutation={makeMutation()}
        onGenerate={vi.fn()}
      />,
    );
    expect(screen.getByTestId<HTMLButtonElement>('btn-generate-insights').disabled).toBe(false);
  });
});
