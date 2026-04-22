import type { UseMutationResult } from '@tanstack/react-query';
import { Info, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { areFiltersEqual, type FilterState } from '@/components/filters/FilterPanel';
import { useUserProfile } from '@/hooks/useUserProfile';
import type {
  EndgameInsightsResponse,
  InsightsAxiosError,
} from '@/types/insights';

/**
 * Top-of-tab Insights card for beta-flagged users (BETA-01).
 *
 * Parent owns the mutation + rendered state (Plan 04) — this component receives
 * the slice it needs and renders the hero / skeleton / overview-with-regenerate /
 * error states per 66-UI-SPEC.md.
 *
 * Beta gate: reads profile.beta_enabled from useUserProfile(); returns null both
 * while loading and when beta_enabled !== true (D-17). Single source of truth —
 * Plan 04's per-section slots observe the same mutation state and conditionally
 * render inside each H2.
 */
export interface EndgameInsightsBlockProps {
  appliedFilters: FilterState;
  rendered: EndgameInsightsResponse | null;
  reportFilters: FilterState | null;
  mutation: UseMutationResult<EndgameInsightsResponse, InsightsAxiosError, FilterState>;
  onGenerate: () => void;
}

/** Minute rounding — 66-UI-SPEC D-14. */
function roundMinutes(retryAfterSeconds: number): number {
  return Math.max(1, Math.ceil(retryAfterSeconds / 60));
}

export function EndgameInsightsBlock({
  appliedFilters,
  rendered,
  reportFilters,
  mutation,
  onGenerate,
}: EndgameInsightsBlockProps) {
  const { data: profile } = useUserProfile();
  // D-17: gate returns null both while profile is loading (undefined) and when flag false.
  if (!profile?.beta_enabled) return null;

  const isPending = mutation.isPending;
  const isError = mutation.isError;
  const hasRendered = rendered !== null;
  const isOutdated =
    hasRendered &&
    reportFilters !== null &&
    !areFiltersEqual(reportFilters, appliedFilters);

  // Error-state: extract retry_after_seconds from AxiosError response body.
  const errorBody = mutation.error?.response?.data;
  const is429 = errorBody?.error === 'rate_limit_exceeded';
  const errorRetrySeconds = is429 ? errorBody?.retry_after_seconds ?? null : null;
  const errorRetryMinutes =
    errorRetrySeconds !== null ? roundMinutes(errorRetrySeconds) : null;

  // Stale-rate-limited: Phase 65 200-envelope does not expose retry_after_seconds,
  // so the "in ~{N} min" branch is unreachable today; fall back to "in a moment".
  const isStale = hasRendered && rendered.status === 'stale_rate_limited';
  const staleMinutes: number | null = null;

  return (
    <div
      data-testid="insights-block"
      className="charcoal-texture rounded-md p-4"
    >
      {/* H2 row with optional outdated indicator (inline-right on desktop, wraps on narrow viewports) */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <h2 className="text-lg font-semibold text-foreground mt-2">Insights</h2>
        {isOutdated && !isError && (
          <div
            data-testid="insights-outdated-indicator"
            role="status"
            className="flex items-center gap-2 text-xs text-muted-foreground font-medium"
          >
            <span className="size-1.5 rounded-full bg-brand-brown" aria-hidden="true" />
            <span>Filters changed — click Regenerate to update</span>
          </div>
        )}
      </div>

      {/* Body — state machine */}
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
          onRegenerate={onGenerate}
        />
      ) : (
        <HeroState
          isPending={isPending}
          onGenerate={onGenerate}
        />
      )}
    </div>
  );
}

// ─── State components ──────────────────────────────────────────────────

function HeroState({
  isPending,
  onGenerate,
}: {
  isPending: boolean;
  onGenerate: () => void;
}) {
  return (
    <>
      <p className="text-sm text-muted-foreground mb-3">
        Generate a short written summary of your endgame performance based on the current filters.
      </p>
      <Button
        variant="default"
        onClick={onGenerate}
        disabled={isPending}
        data-testid="btn-generate-insights"
      >
        Generate insights
      </Button>
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
  onRegenerate,
}: {
  response: EndgameInsightsResponse;
  isStale: boolean;
  staleMinutes: number | null;
  isPending: boolean;
  onRegenerate: () => void;
}) {
  const overview = response.report.overview;
  // BETA-02: empty overview string = hide paragraph, keep Regenerate row.
  const showOverview = overview !== '';
  const staleCopy =
    staleMinutes !== null
      ? `Showing your most recent insights. You've hit the hourly limit; try again in ~${staleMinutes} min.`
      : "Showing your most recent insights. You've hit the hourly limit; try again in a moment.";

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
      {showOverview && (
        <p
          data-testid="insights-overview"
          className="text-sm text-foreground leading-relaxed mb-3"
        >
          {overview}
        </p>
      )}
      <div className="flex items-center gap-2">
        <Button
          variant="default"
          onClick={onRegenerate}
          disabled={isPending}
          aria-busy={isPending}
          data-testid="btn-regenerate-insights"
        >
          Regenerate
        </Button>
        {isPending && (
          <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
        )}
      </div>
    </>
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
