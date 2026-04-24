import type { UseMutationResult } from '@tanstack/react-query';
import { Info, Lightbulb, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { DEFAULT_FILTERS, type FilterState } from '@/components/filters/FilterPanel';
import { useUserProfile } from '@/hooks/useUserProfile';
import { useActiveJobs } from '@/hooks/useImport';
import type {
  EndgameInsightsResponse,
  InsightsAxiosError,
} from '@/types/insights';

/**
 * Top-of-tab Insights card for beta-flagged users.
 *
 * Parent owns the mutation + rendered state and only passes `rendered` when
 * the cached report matches current filters — so this component never has to
 * reason about "outdated" reports. When filters drift away from what the
 * report was generated against, the parent clears it and we fall back to the
 * hero state with a single "Generate Insights" CTA.
 *
 * Beta gate: reads profile.beta_enabled from useUserProfile(); returns null
 * while loading and when beta_enabled !== true.
 *
 * Button gating: the Generate Insights button is disabled whenever any
 * non-default filter other than opponent_strength is set, or an import is
 * running. The tooltip surfaces the first-blocking reason.
 */
export interface EndgameInsightsBlockProps {
  appliedFilters: FilterState;
  rendered: EndgameInsightsResponse | null;
  mutation: UseMutationResult<EndgameInsightsResponse, InsightsAxiosError, FilterState>;
  onGenerate: () => void;
}

function roundMinutes(retryAfterSeconds: number): number {
  return Math.max(1, Math.ceil(retryAfterSeconds / 60));
}

/**
 * Returns the first-blocking reason that prevents generating an insights
 * report, or null when the button should be enabled. opponent_strength is
 * intentionally allowed (it's a valid cross-section the prompt scopes to).
 */
function getBlockedReason(
  filters: FilterState,
  hasActiveImport: boolean,
): string | null {
  if (hasActiveImport) return 'Wait for import to finish';
  if (
    filters.recency !== DEFAULT_FILTERS.recency ||
    filters.timeControls !== DEFAULT_FILTERS.timeControls ||
    filters.platforms !== DEFAULT_FILTERS.platforms ||
    filters.rated !== DEFAULT_FILTERS.rated ||
    filters.opponentType !== DEFAULT_FILTERS.opponentType ||
    filters.matchSide !== DEFAULT_FILTERS.matchSide
  ) {
    return 'Reset the filters before generating insights';
  }
  return null;
}

export function EndgameInsightsBlock({
  appliedFilters,
  rendered,
  mutation,
  onGenerate,
}: EndgameInsightsBlockProps) {
  const { data: profile } = useUserProfile();
  const { data: activeJobs } = useActiveJobs(!!profile?.beta_enabled);
  if (!profile?.beta_enabled) return null;

  const isPending = mutation.isPending;
  const isError = mutation.isError;
  const hasRendered = rendered !== null;

  const hasActiveImport = (activeJobs?.length ?? 0) > 0;
  const blockedReason = getBlockedReason(appliedFilters, hasActiveImport);

  const errorBody = mutation.error?.response?.data;
  const is429 = errorBody?.error === 'rate_limit_exceeded';
  const errorRetrySeconds = is429 ? errorBody?.retry_after_seconds ?? null : null;
  const errorRetryMinutes =
    errorRetrySeconds !== null ? roundMinutes(errorRetrySeconds) : null;

  const isStale = hasRendered && rendered.status === 'stale_rate_limited';
  const staleMinutes: number | null = null;

  return (
    <div
      data-testid="insights-block"
      className="charcoal-texture rounded-md p-4"
    >
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <h2 className="text-lg font-semibold text-foreground mt-2 flex items-center gap-2">
          <span className="insight-lightbulb" aria-hidden="true">
            <Lightbulb className="size-5" />
          </span>
          Insights
        </h2>
      </div>

      {isError ? (
        <ErrorState
          retryMinutes={errorRetryMinutes}
          onRetry={onGenerate}
        />
      ) : isPending && !hasRendered ? (
        <SkeletonBlock />
      ) : hasRendered ? (
        <RenderedState
          response={rendered}
          isStale={isStale}
          staleMinutes={staleMinutes}
          isPending={isPending}
          blockedReason={blockedReason}
          onRegenerate={onGenerate}
        />
      ) : (
        <HeroState
          isPending={isPending}
          blockedReason={blockedReason}
          onGenerate={onGenerate}
        />
      )}
    </div>
  );
}

// ─── State components ──────────────────────────────────────────────────

/** Wrap a disabled button in a Tooltip that explains the blocking reason. */
function MaybeBlockedTooltip({
  reason,
  children,
}: {
  reason: string | null;
  children: React.ReactNode;
}) {
  if (reason === null) return <>{children}</>;
  return (
    <Tooltip content={reason} delayDuration={0}>
      <span className="inline-block">{children}</span>
    </Tooltip>
  );
}

function HeroState({
  isPending,
  blockedReason,
  onGenerate,
}: {
  isPending: boolean;
  blockedReason: string | null;
  onGenerate: () => void;
}) {
  const disabled = isPending || blockedReason !== null;
  return (
    <>
      <p className="text-sm text-muted-foreground mb-3">
        Generate a short written summary and insights for each section for your endgame performance based on the current filters.
      </p>
      <MaybeBlockedTooltip reason={blockedReason}>
        <Button
          variant="brand-outline"
          onClick={onGenerate}
          disabled={disabled}
          data-testid="btn-generate-insights"
        >
          <Sparkles className="h-4 w-4" />
          Generate Insights
        </Button>
      </MaybeBlockedTooltip>
    </>
  );
}

function SkeletonBlock() {
  return (
    <div data-testid="insights-skeleton" className="animate-pulse">
      <div className="h-4 w-full bg-muted/30 rounded mb-2" />
      <div className="h-4 w-11/12 bg-muted/30 rounded mb-2" />
      <div className="h-4 w-3/4 bg-muted/30 rounded mb-3" />
      <div className="h-8 w-32 bg-muted/30 rounded" />
    </div>
  );
}

function RenderedState({
  response,
  isStale,
  staleMinutes,
  isPending,
  blockedReason,
  onRegenerate,
}: {
  response: EndgameInsightsResponse;
  isStale: boolean;
  staleMinutes: number | null;
  isPending: boolean;
  blockedReason: string | null;
  onRegenerate: () => void;
}) {
  const { player_profile: playerProfile, overview, recommendations } = response.report;
  const showOverview = overview !== '';
  const showPlayerProfile = playerProfile !== '';
  const showRecommendations = recommendations.length > 0;
  const staleCopy =
    staleMinutes !== null
      ? `Showing your most recent insights. You've hit the hourly limit; try again in ~${staleMinutes} min.`
      : "Showing your most recent insights. You've hit the hourly limit; try again in a moment.";

  const disabled = isPending || blockedReason !== null;

  return (
    <>
      {isStale && (
        <div
          data-testid="insights-stale-banner"
          role="status"
          className="flex items-center gap-2 text-xs text-muted-foreground mb-3"
        >
          <Info className="size-3.5 shrink-0" aria-hidden="true" />
          <span>{staleCopy}</span>
        </div>
      )}
      <div className="space-y-3 mb-3">
        {showPlayerProfile && (
          <InsightsCard
            testId="insights-player-profile"
            title="Player Profile"
          >
            <div className="text-sm text-foreground leading-relaxed space-y-3">
              {playerProfile.split(/\n\n+/).map((paragraph, idx) => (
                <p key={idx}>{paragraph}</p>
              ))}
            </div>
          </InsightsCard>
        )}
        {showOverview && (
          <InsightsCard
            testId="insights-overview"
            title="Data Analysis"
          >
            <div className="text-sm text-foreground leading-relaxed space-y-3">
              {overview.split(/\n\n+/).map((paragraph, idx) => (
                <p key={idx}>{paragraph}</p>
              ))}
            </div>
          </InsightsCard>
        )}
        {showRecommendations && (
          <InsightsCard
            testId="insights-recommendations"
            title="Recommendations"
          >
            <ul className="text-sm text-foreground leading-relaxed list-disc pl-5 space-y-1">
              {recommendations.map((rec, idx) => (
                <li key={idx}>{rec}</li>
              ))}
            </ul>
          </InsightsCard>
        )}
      </div>
      <div className="flex items-center gap-2">
        <MaybeBlockedTooltip reason={blockedReason}>
          <Button
            variant="brand-outline"
            onClick={onRegenerate}
            disabled={disabled}
            aria-busy={isPending}
            data-testid="btn-generate-insights"
          >
            <Sparkles className="h-4 w-4" />
            Generate Insights
          </Button>
        </MaybeBlockedTooltip>
        {isPending && (
          <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
        )}
      </div>
    </>
  );
}

function InsightsCard({
  testId,
  title,
  children,
}: {
  testId: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      data-testid={testId}
      className="rounded-md border border-border/40 bg-background/40 p-3"
    >
      <h3 className="text-sm font-semibold text-foreground mb-2">{title}</h3>
      {children}
    </div>
  );
}

function ErrorState({
  retryMinutes,
  onRetry,
}: {
  retryMinutes: number | null;
  onRetry: () => void;
}) {
  return (
    <div data-testid="insights-error" role="alert">
      <p className="mb-2 text-base font-medium text-foreground">
        {"Couldn't generate insights."}
      </p>
      <p className="text-sm text-muted-foreground">
        Please try again in a moment.
      </p>
      {retryMinutes !== null && (
        <p className="text-sm text-muted-foreground">
          Try again in ~{retryMinutes} min.
        </p>
      )}
      <Button
        variant="brand-outline"
        onClick={onRetry}
        data-testid="btn-insights-retry"
        className="mt-3"
      >
        Try again
      </Button>
    </div>
  );
}
